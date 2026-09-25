import asyncio
import json
from collections import Counter

import httpx
import pytest
from test_graph import doc

from community_view.communities import build_communities, graph_signature
from community_view.community_split import validate_partition
from community_view.ingest import digest, ingest
from community_view.llm import ModelClient
from community_view.store import dumps


@pytest.mark.parametrize(
    "value,error",
    [
        ({"split": True, "groups": [["a", "b"], ["a"]]}, "repeated=['a']"),
        ({"split": True, "groups": [["a", "a"], ["b"]]}, "repeated=['a']"),
        ({"split": True, "groups": [["a"], ["c"]]}, "missing=['b']"),
        ({"split": True, "groups": [["a", "b"], ["c"]]}, "unknown=['c']"),
        ({"split": True, "groups": [["a", "b"]]}, "at least two"),
        ({"split": True, "groups": [["a", "b"], []]}, "nonempty array"),
        ({"split": True, "groups": [["a"], [1]]}, "ID strings"),
        ({"split": False, "groups": [["a", "b"]]}, "groups must be []"),
        ({"split": "false", "groups": []}, "must be a boolean"),
        ({"split": False, "groups": [], "reason": "no"}, "exactly fields"),
    ],
)
def test_partition_rejects_invalid_document_assignments(value, error):
    with pytest.raises(ValueError) as caught:
        validate_partition(value, ["a", "b"])
    assert error in str(caught.value)


async def test_fallback_branches_concurrent_and_children_terminal(config, client, caplog):
    config.community.llm_split_fallback = True
    config.community.description_concurrency = 2
    config.community.max_documents = 2
    documents = [doc(i, [1, 0], ["keyword"]) for i in "abcdefgh"]
    partition_calls, split_payloads = [], []
    original = client.json_completion
    active, peak = 0, 0
    both_splits = asyncio.Event()

    async def partitioner(ids, edges):
        partition_calls.append(list(ids))
        return [ids[:4], ids[4:]] if len(ids) == 8 else [ids]

    async def generate(system, payload, schema, retries, validate, purpose):
        nonlocal active, peak
        if purpose != "community_split":
            return await original(system, payload, schema, retries, validate, purpose)
        assert payload["name"] == "社区" and payload["overview"] == "成员文档的简短总览"
        assert payload["max_documents"] == 2
        split_payloads.append(payload)
        for overview in payload["document_overviews"]:
            assert set(overview) == {"doc_id", "title", "keywords", "summary"}
        assert set(schema["properties"]) == {"split", "groups"}
        ids = [d["doc_id"] for d in payload["document_overviews"]]
        active += 1
        peak = max(peak, active)
        if active == 2:
            both_splits.set()
        try:
            await asyncio.wait_for(both_splits.wait(), 2)
            result = {"split": True, "groups": [ids[:3], ids[3:]]}
            validate(result)
            return result
        finally:
            active -= 1

    client.json_completion = generate
    communities = await build_communities(documents, [], config, client, partitioner)
    assert peak == 2 and len(split_payloads) == 2
    assert sorted(map(len, partition_calls)) == [4, 4, 8]  # No Leiden on LLM children.
    parents = [c for c in communities if c.parent_id is None]
    leaves = [c for c in communities if c.is_leaf]
    assert len(parents) == 2 and all(c.split_status == "llm_split" for c in parents)
    assert len(leaves) == 4 and sorted(len(c.doc_ids) for c in leaves) == [1, 1, 3, 3]
    assert all(c.split_status == "llm_leaf_oversized" for c in leaves if len(c.doc_ids) == 3)
    assert all(c.name and c.overview for c in communities)
    assert Counter(i for c in leaves for i in c.doc_ids) == Counter("abcdefgh")
    for parent in parents:
        children = [c for c in leaves if c.parent_id == parent.community_id]
        assert set(parent.child_ids) == {c.community_id for c in children}
        assert all(c.level == parent.level + 1 for c in children)
    assert sorted(len(p["document_overviews"]) for _, p in client.calls) == [1, 1, 3, 3, 4, 4]


@pytest.mark.parametrize("fallback,threshold", [(False, 1), (True, 4)])
async def test_no_optional_requests_when_disabled_or_within_threshold(
    config, client, fallback, threshold
):
    config.community.llm_split_fallback = fallback
    config.community.max_documents = threshold
    config.prompts.community_split = config.prompts.community_split.with_name("missing.txt")

    async def partitioner(ids, edges):
        return [ids]

    communities = await build_communities(
        [doc(i, [1, 0], ["keyword"]) for i in "ab"], [], config, client, partitioner
    )
    assert len(communities) == 1 and communities[0].is_leaf
    assert [purpose for purpose, _ in client.calls] == ["community_overview"]


@pytest.mark.parametrize("invalid", [False, True])
async def test_leiden_success_or_invalid_partition_does_not_trigger_fallback(
    config, client, invalid
):
    config.community.llm_split_fallback = True
    config.community.max_documents = 1

    async def partitioner(ids, edges):
        return [[ids[0]], [ids[0]]] if invalid else [[i] for i in ids]

    operation = build_communities(
        [doc(i, [1, 0], ["keyword"]) for i in "ab"], [], config, client, partitioner
    )
    if invalid:
        with pytest.raises(ValueError, match="exactly once"):
            await operation
    else:
        assert len(await operation) == 2
    assert all(purpose != "community_split" for purpose, _ in client.calls)


@pytest.mark.parametrize("outcome", ["corrected", "invalid", "api_error", "declined"])
async def test_fallback_http_retry_retention_and_indexing_metrics(
    config, store, client, text, benchmark_settings, monkeypatch, caplog, outcome
):
    import community_view.communities as module
    from community_view.experiments.dataset import load_dataset, prepare
    from community_view.experiments.indexing import index

    config.community.llm_split_fallback = True
    config.community.max_documents = 1
    config.community.description_concurrency = 1  # Awaiting description must not deadlock.
    config.model.retry_delay_seconds = 0
    benchmark_settings.modes = ["community"]
    dataset = load_dataset(benchmark_settings)
    prepare(benchmark_settings, dataset)
    await ingest(dataset.paths, config, store, client, text)
    original = module.build_communities

    async def one_partition(ids, edges):
        return [ids]

    async def build(documents, edges, config, client):
        return await original(documents, edges, config, client, one_partition)

    monkeypatch.setattr(module, "build_communities", build)
    split_calls, descriptions = [], []

    async def respond(request):
        await asyncio.sleep(0.001)
        body = json.loads(request.content)
        payload = json.loads(body["messages"][1]["content"])
        if "max_documents" in payload:
            split_calls.append(body)
            assert payload["name"] == "Name" and payload["overview"] == "Overview"
            assert all(d["keywords"] for d in payload["document_overviews"])
            if outcome == "api_error":
                return httpx.Response(503, json={"usage": {"total_tokens": 12}})
            ids = [d["doc_id"] for d in payload["document_overviews"]]
            if outcome == "declined":
                result = {"split": False, "groups": []}
            elif outcome == "corrected" and len(split_calls) > 1:
                result = {"split": True, "groups": [[i] for i in ids]}
            else:
                result = {"split": True, "groups": [[ids[0]], [ids[0]]]}
        else:
            descriptions.append(payload)
            result = {"name": "Name", "overview": "Overview"}
        return httpx.Response(
            200,
            json={
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(result)},
                    }
                ],
            },
        )

    real_client = ModelClient(config, store, text, httpx.MockTransport(respond))
    try:
        result = await asyncio.wait_for(
            index(dataset, benchmark_settings, config, store, real_client, text, stage="cluster"),
            3,
        )
    finally:
        await real_client.close()
    assert (
        len(split_calls) == {"corrected": 2, "invalid": 3, "api_error": 3, "declined": 1}[outcome]
    )
    assert len(descriptions) == (3 if outcome == "corrected" else 1)
    stage = result["stages"]["communities"]
    assert stage["status"] == "complete" and stage["elapsed_seconds"] > 0
    assert stage["total_tokens"] == 12 * (len(descriptions) + len(split_calls))
    assert result["total_tokens"] == stage["total_tokens"] and stage["embedding_tokens"] == 0
    communities = store.communities()
    parent = next(c for c in communities if c.parent_id is None)
    assert (
        parent.split_status
        == {
            "corrected": "llm_split",
            "invalid": "llm_failed",
            "api_error": "llm_failed",
            "declined": "llm_declined",
        }[outcome]
    )
    assert parent.is_leaf == (outcome != "corrected")
    assert all(c.community_id.startswith("C") and c.name and c.overview for c in communities)
    if outcome in {"invalid", "corrected"}:
        assert "missing=" in split_calls[1]["messages"][-1]["content"]
        assert "repeated=" in split_calls[1]["messages"][-1]["content"]
        assert split_calls[1]["messages"][-2]["role"] == "assistant"
    if outcome in {"invalid", "api_error"}:
        assert "retained as leaf" in caplog.text
    if outcome == "api_error":
        assert "retry=1/2" in caplog.text and "retry=2/2" in caplog.text


async def test_split_cancellation_is_not_swallowed(config, client):
    config.community.llm_split_fallback = True
    config.community.max_documents = 1
    requested = asyncio.Event()
    original = client.json_completion

    async def generate(*args):
        if args[-1] == "community_split":
            requested.set()
            await asyncio.Event().wait()
        return await original(*args)

    async def one_partition(ids, edges):
        return [ids]

    client.json_completion = generate
    task = asyncio.create_task(
        build_communities(
            [doc(i, [1, 0], ["keyword"]) for i in "ab"], [], config, client, one_partition
        )
    )
    await asyncio.wait_for(requested.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def test_graph_signature_preserves_v2_when_disabled_and_tracks_split_prompt(config, tmp_path):
    v2_signature = digest(
        dumps(
            {
                "graph": config.graph.model_dump(),
                "community": config.community.model_dump(exclude={"llm_split_fallback"}),
                "model": config.model.model_dump(),
                "prompt": config.prompts.community.read_text(),
            }
        )
    )
    config.prompts.community_split = tmp_path / "split.txt"
    assert graph_signature(config) == v2_signature  # No file required when disabled.
    config.prompts.community_split.write_text("split prompt")
    config.community.llm_split_fallback = True
    enabled = graph_signature(config)
    assert enabled != v2_signature
    config.prompts.community_split.write_text("changed split prompt")
    assert graph_signature(config) != enabled
