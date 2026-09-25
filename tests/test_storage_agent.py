import json
from dataclasses import replace

import pytest
from test_retrieval import populate

from community_view.agent import Agent
from community_view.communities import cluster
from community_view.ingest import embedding_signature
from community_view.retrieval import Retriever
from community_view.store import Store


def test_snapshot_revision_guard_and_rollback(config, store):
    populate(config, store)
    old_edges, old_communities = store.edges(), store.communities()
    with pytest.raises(ValueError, match="changed"):
        store.publish_graph([], [], store.revision - 1, "stale")
    assert store.edges() == old_edges
    assert store.communities() == old_communities
    document = store.documents()[0]
    chunks = [c for c in store.chunks() if c.doc_id == document.doc_id]
    revision = store.revision
    # Constraint failure after DELETE must roll the whole document replacement back.
    with pytest.raises(Exception, match="UNIQUE"):
        store.save_document(
            replace(document, content_hash="new"),
            [chunks[0], chunks[0]],
            embedding_signature(config),
        )
    assert store.revision == revision
    assert store.documents()[0].content_hash == document.content_hash
    reopened = Store(config.storage.database)
    assert reopened.revision == revision
    assert len(reopened.chunks()) == len(store.chunks())
    reopened.close()


async def test_failed_description_does_not_publish_partial_graph(config, store, client):
    populate(config, store)
    before = store.communities()

    async def fail(*args, **kwargs):
        raise ValueError("description failure")

    client.json_completion = fail
    with pytest.raises(ExceptionGroup):
        await cluster(config, store, client)
    assert store.communities() == before
    assert store.meta("graph_signature") == "test"


async def test_agent_bad_arguments_and_final_round(config, store, client):
    populate(config, store)
    config.agent.max_rounds = 2
    calls = []

    async def chat(messages, **kwargs):
        calls.append((list(messages), kwargs))
        if len(calls) == 1:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "bad",
                        "type": "function",
                        "function": {"name": "search_chunks", "arguments": '{"query":123}'},
                    }
                ],
            }
        assert kwargs["force_final"]
        assert "error" in json.loads(messages[-1]["content"])
        return {"role": "assistant", "content": "信息不足。"}

    client.chat = chat
    answer = await Agent(config, store, client, Retriever(config, store, client)).ask("question")
    assert answer.rounds == 2
    assert calls[1][0][-1]["tool_call_id"] == "bad"


async def test_agent_identical_tool_call_limit(config, store, client):
    populate(config, store)
    config.agent.max_identical_tool_calls = 1
    agent = Agent(config, store, client, Retriever(config, store, client))
    answer = await agent.ask("alpha")
    row = store.db.execute("SELECT messages FROM runs WHERE run_id=?", (answer.run_id,)).fetchone()
    results = [json.loads(m["content"]) for m in json.loads(row[0]) if m["role"] == "tool"]
    assert "Repeated identical tool call" in results[1]["error"]
