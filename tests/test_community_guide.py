import json

import pytest
from test_retrieval import populate

from community_wiki.agent import Agent
from community_wiki.cli import parser
from community_wiki.metrics import measure, record_usage
from community_wiki.retrieval import Retriever


@pytest.mark.parametrize("mode", ["naive", "community", "community_guide"])
async def test_initial_guide_scope_chunks_dedup_and_usage(config, store, client, mode):
    populate(config, store)
    retriever = Retriever(config, store, client, mode)
    searches = []
    original_search, original_embed = retriever.search_hits, client.embed

    async def search(query, **kwargs):
        searches.append((query, kwargs))
        return await original_search(query, **kwargs)

    async def embed(texts):
        record_usage({"total_tokens": 7}, "embedding")
        return await original_embed(texts)

    retriever.search_hits, client.embed = search, embed
    inputs = []

    async def chat(messages, **kwargs):
        inputs.append(list(messages))
        if len(inputs) == 1:
            guide = [m for m in messages if '"initial_context"' in (m.get("content") or "")]
            assert len(searches) == (1 if mode == "community_guide" else 0)
            if mode == "community_guide":
                assert searches[0] == ("alpha", {"search_mode": None, "doc_ids": ["a"]})
                context = json.loads(guide[0]["content"])["initial_context"]
                assert "chunks" not in context
                assert context["communities"] and context["document_overviews"]
                assert all(
                    set(d) == {"doc_id", "title", "summary"} for d in context["document_overviews"]
                )
                assert "preliminary guide" in " ".join(m["content"] for m in messages)
            else:
                assert not guide
                assert "preliminary guide" not in " ".join(m["content"] for m in messages)
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "read",
                        "type": "function",
                        "function": {
                            "name": "read_chunks",
                            "arguments": json.dumps({"doc_id": "a", "ordinals": [0]}),
                        },
                    }
                ],
            }
        result = json.loads(messages[-1]["content"])
        assert result["chunks"][0]["text"] == "alpha alpha"
        assert "keywords" not in json.dumps(result)
        if mode == "community_guide":
            assert not result["document_overviews"] and not result["communities"]
        return {"role": "assistant", "content": "answer"}

    client.chat = chat
    agent = Agent(config, store, client, retriever)
    for _ in range(2):
        # Reusing the agent for another QA must not reuse its guide or dedup state.
        inputs.clear()
        searches.clear()
        with measure("qa") as metrics:
            answer = await agent.ask("alpha", doc_ids=["a"])
        assert answer.rounds == metrics.rounds == 2
        assert metrics.embedding_tokens == (7 if mode == "community_guide" else 0)
    assert all(d.overview.keywords for d in store.documents())
    assert parser().parse_args(["ask", "alpha", "--mode", mode]).mode == mode


async def test_empty_guide_and_bootstrap_failure_are_recorded(config, store, client):
    populate(config, store)
    retriever = Retriever(config, store, client, "community_guide")

    async def chat(messages, **kwargs):
        context = json.loads(messages[-1]["content"])["initial_context"]
        assert context["communities"] == context["document_overviews"] == []
        assert "chunks" not in context
        return {"role": "assistant", "content": "No evidence in scope"}

    client.chat = chat
    await Agent(config, store, client, retriever).ask("alpha", doc_ids=[])

    async def fail(*args, **kwargs):
        raise RuntimeError("bootstrap failed")

    retriever.search_hits = fail
    with pytest.raises(RuntimeError, match="bootstrap failed"):
        await Agent(config, store, client, retriever).ask("alpha", run_id="failed-guide")
    assert (
        store.db.execute("SELECT status FROM runs WHERE run_id='failed-guide'").fetchone()[0]
        == "failed"
    )


async def test_benchmark_guide_builds_graph_and_keeps_gold_out(
    config, benchmark_settings, store, client, text
):
    from community_wiki.experiments.dataset import load_dataset, prepare
    from community_wiki.experiments.indexing import index
    from community_wiki.experiments.runner import predict

    benchmark_settings.modes = ["community_guide"]
    dataset = load_dataset(benchmark_settings)
    prepare(benchmark_settings, dataset)
    result = await index(dataset, benchmark_settings, config, store, client, text)
    assert result["stages"]["communities"]["status"] == "complete"
    assert store.communities()
    result = await predict(dataset, benchmark_settings, config, store, client)
    assert result["modes"]["community_guide"]["successful"] == 2
    assert "GOLD_MUST_NOT_LEAK" not in json.dumps(client.chat_calls)
    assert "EVIDENCE_MUST_NOT_LEAK" not in json.dumps(client.chat_calls)
    config.community.resolution += 0.1
    with pytest.raises(ValueError, match="Community settings changed"):
        await predict(dataset, benchmark_settings, config, store, client)
