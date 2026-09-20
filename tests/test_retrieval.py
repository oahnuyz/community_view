import json

import numpy as np
import pytest

from community_wiki.agent import Agent, SearchArguments, tool_definitions
from community_wiki.cli import parser
from community_wiki.communities import cluster
from community_wiki.ingest import embedding_signature, ingest
from community_wiki.models import (
    Chunk,
    Community,
    Document,
    Edge,
    Overview,
    QuestionState,
    SearchHit,
)
from community_wiki.retrieval import Retriever


def populate(config, store):
    for identity, title, contents in [
        ("a", "Title A", ["alpha alpha", "alpha"]),
        ("b", "Title B", ["beta"]),
        ("c", "Title C", ["gamma"]),
        ("d", "Title D", ["delta"]),
        ("e", "Title E", ["epsilon"]),
    ]:
        vector = np.array([1, 0, 0], dtype=np.float32)
        document = Document(
            identity,
            identity,
            "hash",
            "signature",
            Overview(title=title, keywords=[identity], summary=title),
            vector,
        )
        store.save_document(
            document,
            [Chunk(identity, i, value, vector) for i, value in enumerate(contents)],
            embedding_signature(config),
        )
    communities = [
        Community("root", 0, None, ["a", "b"], ["A", "B"]),
        Community("A", 1, "root", ["a"], name="A", overview="A overview"),
        Community("B", 1, "root", ["b"], name="B", overview="B overview"),
        Community("C", 0, None, ["c"], name="C", overview="C overview"),
        Community("D", 0, None, ["d"], name="D", overview="D overview"),
        Community("E", 0, None, ["e"], name="E", overview="E overview"),
    ]
    edges = [
        Edge("a", "b", 0.99, 0.99, None),
        Edge("a", "c", 0.9, 0.9, None),
        Edge("a", "d", 0.8, 0.8, None),
        Edge("b", "e", 0.7, 0.7, None),
    ]
    store.publish_graph(edges, communities, store.revision, "test")


def test_selected_doc_edges_exclude_both_endpoints_and_cross_depth(config, store, client):
    populate(config, store)
    config.retrieval.doc_k = 2
    retriever = Retriever(config, store, client, "community")
    hits = [
        SearchHit("a", 0, "alpha", 1),
        SearchHit("a", 1, "alpha", 0.9),
        SearchHit("b", 0, "beta", 0.8),
    ]
    assert retriever.selected_communities(hits) == ["A", "B", "C", "E"]
    state = QuestionState()
    context = retriever.context(hits, state)
    assert {c["community_id"] for c in context["communities"]} == {"A", "B", "C", "E"}
    assert {d["doc_id"] for d in context["document_overviews"]} == {"a", "b", "c", "e"}
    repeat = retriever.context(hits, state)
    assert repeat["communities"] == [] and repeat["document_overviews"] == []
    assert "D" not in state.seen_communities  # No runner-up when C already seen.
    assert retriever.context(hits, QuestionState())["communities"]


@pytest.mark.parametrize("mode", ["vector", "keyword", "hybrid"])
async def test_doc_ids_scope_chunks_but_not_expansion(config, store, client, mode):
    populate(config, store)
    retriever = Retriever(config, store, client, "community")
    result = await retriever.search("alpha", QuestionState(), doc_ids=["a"], search_mode=mode)
    assert result["chunks"] and all(hit["doc_id"] == "a" for hit in result["chunks"])
    assert {c["community_id"] for c in result["communities"]} == {"A", "B"}
    assert {d["doc_id"] for d in result["document_overviews"]} == {"a", "b"}
    empty = await retriever.search("alpha", QuestionState(), doc_ids=[], search_mode=mode)
    assert not empty["chunks"] and not empty["communities"]
    multiple = await retriever.search(
        "alpha beta", QuestionState(), doc_ids=["a", "b"], search_mode=mode
    )
    assert {hit["doc_id"] for hit in multiple["chunks"]} == {"a", "b"}
    with pytest.raises(ValueError, match="Unknown doc_ids"):
        await retriever.search("alpha", QuestionState(), doc_ids=["a", "missing"], search_mode=mode)


@pytest.mark.parametrize("mode", ["naive", "community"])
async def test_document_titles_always_include_ids(config, store, client, mode):
    populate(config, store)
    retriever = Retriever(config, store, client, mode)
    result = await retriever.search("alpha", QuestionState(), search_mode="keyword")
    expected = {"a"} if mode == "naive" else {"a", "b"}
    assert {doc["doc_id"] for doc in result["document_overviews"]} == expected

    def check(value):
        if isinstance(value, dict):
            if "title" in value:
                assert value["title"] == retriever.documents[value["doc_id"]].overview.title
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(result)


def test_only_search_and_read_tools_with_id_scope():
    definitions = {tool["function"]["name"]: tool["function"] for tool in tool_definitions()}
    assert set(definitions) == {"search_chunks", "read_chunks"}
    assert set(definitions["search_chunks"]["parameters"]["properties"]) == {
        "query",
        "search_mode",
        "doc_ids",
    }
    with pytest.raises(ValueError):
        SearchArguments.model_validate(
            {"query": "alpha", "search_mode": None, "doc_ids": None, "title": "Title A"}
        )
    for command in ("search", "ask"):
        args = [command, "alpha"]
        assert parser().parse_args(args + ["--doc-ids", "a", "b"]).doc_ids == ["a", "b"]


async def test_agent_question_scope_intersects_search_and_restricts_reads(config, store, client):
    populate(config, store)
    requests = [
        ("search_chunks", {"query": "alpha beta", "search_mode": "vector", "doc_ids": None}),
        ("search_chunks", {"query": "alpha beta", "search_mode": "vector", "doc_ids": ["b", "c"]}),
        ("search_chunks", {"query": "gamma", "search_mode": "vector", "doc_ids": ["c"]}),
        ("read_chunks", {"doc_id": "c", "ordinals": [0]}),
        ("read_chunks", {"doc_id": "b", "ordinals": [0]}),
    ]

    async def chat(messages, **kwargs):
        if any(message["role"] == "tool" for message in messages):
            return {"role": "assistant", "content": "answer"}
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": str(i),
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }
                for i, (name, arguments) in enumerate(requests)
            ],
        }

    client.chat = chat
    agent = Agent(config, store, client, Retriever(config, store, client, "community"))
    answer = await agent.ask("alpha beta", doc_ids=["a", "b"])
    row = store.db.execute("SELECT messages FROM runs WHERE run_id=?", (answer.run_id,)).fetchone()
    results = [json.loads(m["content"]) for m in json.loads(row[0]) if m["role"] == "tool"]
    assert {hit["doc_id"] for hit in results[0]["chunks"]} == {"a", "b"}
    assert {hit["doc_id"] for hit in results[1]["chunks"]} == {"b"}
    assert results[2]["chunks"] == []
    assert "outside" in results[3]["error"]
    assert {hit["doc_id"] for hit in results[4]["chunks"]} == {"b"}
    with pytest.raises(ValueError, match="Unknown doc_ids"):
        await agent.ask("alpha", doc_ids=["missing"])


async def test_naive_no_communities_overview_once(config, store, client):
    populate(config, store)
    retriever = Retriever(config, store, client, "naive")
    state = QuestionState()
    result = await retriever.search("alpha", state, search_mode="keyword")
    assert len(result["chunks"]) == 2
    assert "communities" not in result and len(result["document_overviews"]) == 1
    assert not (await retriever.search("alpha", state, search_mode="keyword"))["document_overviews"]


async def test_full_pipeline_real_leiden_and_agent(config, store, client, text, tmp_path):
    paths = []
    for i, content in enumerate(["alpha 科学 物理", "alpha 科学 化学", "beta 工程 材料"]):
        path = tmp_path / f"{i}.md"
        path.write_text(content)
        paths.append(path)
    result = await ingest(paths, config, store, client, text)
    assert result.inserted == 3
    summary = await cluster(config, store, client)
    assert summary["documents"] == 3 and summary["communities"] >= 1
    agent = Agent(config, store, client, Retriever(config, store, client, "community"))
    answer = await agent.ask("alpha 有什么信息？")
    assert answer.rounds == 3
    row = store.db.execute(
        "SELECT status,messages FROM runs WHERE run_id=?", (answer.run_id,)
    ).fetchone()
    assert row[0] == "complete"
    messages = json.loads(row[1])
    results = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
    assert results[0]["communities"] and not results[1]["communities"]
    assert not results[1]["document_overviews"]
    assert all(t["function"]["name"] != "community" for t in tool_definitions())
    # Reusing the Agent does not carry messages or deduplication into a new question.
    second = await agent.ask("再次查看 alpha")
    row = store.db.execute("SELECT messages FROM runs WHERE run_id=?", (second.run_id,)).fetchone()
    second_messages = json.loads(row[0])
    assert len([m for m in second_messages if m["role"] == "user"]) == 1
    assert "alpha 有什么信息？" not in row[0]
    assert next(json.loads(m["content"]) for m in second_messages if m["role"] == "tool")[
        "communities"
    ]
    # Updating one document invalidates community search until a new snapshot is published.
    paths[0].write_text("alpha changed")
    await ingest([paths[0]], config, store, client, text)
    with pytest.raises(ValueError, match="stale"):
        Retriever(config, store, client, "community")
    Retriever(config, store, client, "naive")


def test_association_comes_from_selected_document_not_community(config, store, client):
    populate(config, store)
    communities = [
        Community("AB", 0, None, ["a", "b"]),
        Community("C", 0, None, ["c"]),
        Community("D", 0, None, ["d"]),
        Community("E", 0, None, ["e"]),
    ]
    edges = [Edge("a", "c", 0.4, 0.4, None), Edge("b", "d", 0.99, 0.99, None)]
    store.publish_graph(edges, communities, store.revision, "test")
    retriever = Retriever(config, store, client, "community")
    assert retriever.selected_communities([SearchHit("a", 0, "alpha", 1)]) == ["AB", "C"]
