import json

from test_retrieval import populate

from community_view.agent import Agent
from community_view.config import KnowledgeConfig
from community_view.knowledge import build_knowledge
from community_view.knowledge_store import record_question
from community_view.retrieval import Retriever


async def test_compile_uses_ordinary_community_search_without_initial_context(
    config, store, client, monkeypatch
):
    populate(config, store)
    r = Retriever(config, store, client, "community")
    record_question(store, "history", r.graph_key, "beta?", {"A"}, "complete")
    config.knowledge.use_compiled = True
    original_search = Retriever.search_hits
    searches = []

    async def search(self, **args):
        assert self.mode == "community"
        searches.append(args)
        return await original_search(self, **args)

    monkeypatch.setattr(Retriever, "search_hits", search)

    async def plan(system, payload, *args):
        assert payload["communities"][0]["doc_ids"] == ["a"]
        assert payload["document_overviews"]
        assert "Shorten" not in system and "compress" not in system.lower()
        return {"questions": [{"question": "beta?", "source_question_ids": ["H0001"]}]}

    async def chat(messages, **kwargs):
        assert {t["function"]["name"] for t in kwargs["tools"]} == {"search_chunks"}
        assert messages[1]["content"] == config.prompts.question.read_text().replace(
            "{question}", "beta?"
        )
        assert len([m for m in messages if m["role"] == "user"]) == 1
        assert len([m for m in messages if m["role"] == "system"]) == 1
        assert "initial_context" not in json.dumps(messages)
        assert "All chunk searches are restricted" not in json.dumps(messages)
        results = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        if results:
            assert any(c["doc_id"] == "b" for c in results[0]["chunks"])
            assert results[0]["communities"]
            assert results[0]["document_overviews"]
            return {"role": "assistant", "content": "beta"}
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "search",
                    "type": "function",
                    "function": {
                        "name": "search_chunks",
                        "arguments": json.dumps(
                            {"query": "beta", "search_mode": "keyword", "doc_ids": None}
                        ),
                    },
                }
            ],
        }

    client.json_completion, client.chat = plan, chat
    result = await build_knowledge(config, store, client)
    assert result["complete"] == 1 and result["failed"] == 0
    assert searches[0]["doc_ids"] is None
    assert store.db.execute("SELECT mode FROM runs").fetchone()[0] == "community"
    assert store.db.execute("SELECT COUNT(*) FROM question_communities").fetchone()[0] == 1
    assert config.knowledge.use_compiled is True
    assert KnowledgeConfig().question_k == config.knowledge.question_k == 3


async def test_shared_question_prompt_invalidates_compilation_cache(
    config, store, client, tmp_path
):
    populate(config, store)
    r = Retriever(config, store, client, "community")
    record_question(store, "history", r.graph_key, "alpha?", {"A"}, "complete")
    config.prompts.question = tmp_path / "question.txt"
    config.prompts.question.write_text("Answer V1: {question}")
    plans = []

    async def plan(*args):
        plans.append(1)
        return {"questions": [{"question": "alpha?", "source_question_ids": ["H0001"]}]}

    async def chat(messages, **kwargs):
        assert len([m for m in messages if m["role"] == "system"]) == 1
        assert messages[1]["content"] == config.prompts.question.read_text().replace(
            "{question}", "alpha?"
        )
        return {"role": "assistant", "content": "alpha"}

    client.json_completion, client.chat = plan, chat
    await build_knowledge(config, store, client)
    await build_knowledge(config, store, client)
    assert len(plans) == 1
    config.prompts.question.write_text("Answer V2: {question}")
    await build_knowledge(config, store, client)
    assert len(plans) == 2
    for mode in ["naive", "community"]:
        await Agent(config, store, client, Retriever(config, store, client, mode)).ask("alpha?")
