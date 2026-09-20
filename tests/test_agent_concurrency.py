import asyncio
import json

import pytest
from test_retrieval import populate

from community_wiki.agent import Agent
from community_wiki.metrics import measure, record_usage
from community_wiki.retrieval import Retriever


def tool_call(identity, name="search_chunks", **arguments):
    if name == "search_chunks":
        arguments = {"query": identity, "search_mode": "vector", "doc_ids": ["a"], **arguments}
    return {
        "id": identity,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


@pytest.mark.parametrize("concurrency", [1, 2])
async def test_parallel_tools_order_dedup_limits_and_usage(config, store, client, concurrency):
    populate(config, store)
    config.agent.tool_concurrency = concurrency
    config.agent.max_identical_tool_calls = 1
    retriever = Retriever(config, store, client, "community")
    original_embed = client.embed
    second_finished = asyncio.Event()
    active, peak = 0, 0
    completed = []

    async def embed(texts):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            if texts == ["first"] and concurrency > 1:
                await asyncio.wait_for(second_finished.wait(), timeout=2)
            record_usage({"total_tokens": 7}, "embedding")
            result = await original_embed(texts)
            completed.append(texts[0])
            if texts == ["second"]:
                second_finished.set()
            return result
        finally:
            active -= 1

    calls = [
        tool_call("first"),
        tool_call("second"),
        tool_call("read", "read_chunks", doc_id="a", ordinals=[1]),
        tool_call("bad", "read_chunks", doc_id="missing", ordinals=[0]),
        tool_call("repeat", query="first"),
    ]
    model_inputs = []

    async def chat(messages, **kwargs):
        model_inputs.append(list(messages))
        if len(model_inputs) == 1:
            return {"role": "assistant", "content": None, "tool_calls": calls}
        return {"role": "assistant", "content": "answer"}

    client.embed, client.chat = embed, chat
    with measure("parallel-question") as totals:
        answer = await Agent(config, store, client, retriever).ask("question")
    assert answer.rounds == 2 and totals.rounds == 2
    assert totals.embedding_tokens == 14
    assert peak == concurrency and active == 0
    assert completed == (["first", "second"] if concurrency == 1 else ["second", "first"])
    messages = [m for m in model_inputs[1] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in messages] == [c["id"] for c in calls]
    results = [json.loads(m["content"]) for m in messages]
    # Even when the second search completes first, metadata belongs to the first call.
    assert {c["community_id"] for c in results[0]["communities"]} == {"A", "B"}
    assert {d["doc_id"] for d in results[0]["document_overviews"]} == {"a", "b"}
    for result in results[1:3]:
        assert result["chunks"]
        assert result["communities"] == [] and result["document_overviews"] == []
    assert "Unknown doc_id" in results[3]["error"]
    assert "Repeated identical tool call" in results[4]["error"]


async def test_fatal_tool_failure_drains_siblings_and_records_failed_run(config, store, client):
    populate(config, store)
    config.agent.tool_concurrency = 2
    retriever = Retriever(config, store, client, "community")
    started, drained = asyncio.Event(), asyncio.Event()

    async def search_hits(query, **kwargs):
        if query == "fail":
            await asyncio.wait_for(started.wait(), timeout=2)
            raise RuntimeError("API retries exhausted")
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            drained.set()

    async def chat(messages, **kwargs):
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [tool_call("fail"), tool_call("pending")],
        }

    retriever.search_hits, client.chat = search_hits, chat
    with pytest.raises(ExceptionGroup) as error:
        await Agent(config, store, client, retriever).ask("question", run_id="failed-tools")
    assert "API retries exhausted" in str(error.value.exceptions[0])
    assert drained.is_set()
    row = store.db.execute(
        "SELECT status,messages FROM runs WHERE run_id=?", ("failed-tools",)
    ).fetchone()
    assert row[0] == "failed"
    assert len(json.loads(row[1])[-1]["tool_calls"]) == 2
