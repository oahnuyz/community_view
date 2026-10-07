import json

import pytest
from test_knowledge import seed
from test_retrieval import populate

from community_view.agent import Agent
from community_view.retrieval import Retriever


@pytest.mark.parametrize("has_views", [True, False])
async def test_first_round_blocks_search_execution_then_restores_it(
    config, store, client, has_views
):
    populate(config, store)
    config.knowledge.use_compiled = True
    config.agent.max_identical_tool_calls = 1
    retriever = Retriever(config, store, client, "community")
    if has_views:
        seed(store, config, retriever)
    searches = []
    original_search = retriever.search_hits

    async def search_hits(**kwargs):
        searches.append(kwargs)
        return await original_search(**kwargs)

    def call(identity, name, arguments):
        return {
            "id": identity,
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)},
        }

    search_args = {"query": "alpha", "search_mode": "keyword", "doc_ids": None}
    requests = 0

    async def chat(messages, **kwargs):
        nonlocal requests
        requests += 1
        names = {t["function"]["name"] for t in kwargs["tools"]}
        results = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        if requests == 1:
            assert names == {"read_view_answers"}
            assert not kwargs["force_final"]
            calls = [call("forbidden-search", "search_chunks", search_args)]
            if has_views:
                calls.append(call("valid-read", "read_view_answers", {"question_ids": ["A-Q0001"]}))
            return {"role": "assistant", "content": None, "tool_calls": calls}
        assert names == {"search_chunks", "read_view_answers"}
        if requests == 2:
            assert not searches
            assert results[0] == {"error": "Tool is unavailable in this round"}
            if has_views:
                assert results[1]["answers"][0]["answer"] == "ANSWER_SECRET_1"
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [call("allowed-search", "search_chunks", search_args)],
            }
        assert len(searches) == 1 and results[-1]["chunks"]
        return {"role": "assistant", "content": "answer"}

    retriever.search_hits = search_hits
    client.chat = chat
    result = await Agent(config, store, client, retriever).ask("alpha")
    assert result.rounds == 3


async def test_first_round_view_restriction_keeps_auto_final_answer(config, store, client):
    populate(config, store)
    config.knowledge.use_compiled = True
    retriever = Retriever(config, store, client, "community")
    seed(store, config, retriever)

    async def chat(messages, **kwargs):
        assert {t["function"]["name"] for t in kwargs["tools"]} == {"read_view_answers"}
        assert not kwargs["force_final"]
        return {"role": "assistant", "content": "No relevant evidence."}

    client.chat = chat
    assert (await Agent(config, store, client, retriever).ask("alpha")).rounds == 1


async def test_last_round_still_forces_final_with_view_enabled(config, store, client):
    populate(config, store)
    config.knowledge.use_compiled = True
    config.agent.max_rounds = 1
    retriever = Retriever(config, store, client, "community")
    seed(store, config, retriever)

    async def chat(messages, **kwargs):
        assert kwargs["force_final"] is True
        assert {t["function"]["name"] for t in kwargs["tools"]} == {"read_view_answers"}
        return {"role": "assistant", "content": "No evidence was read."}

    client.chat = chat
    assert (await Agent(config, store, client, retriever).ask("alpha")).rounds == 1
