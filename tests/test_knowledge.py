import json
import runpy
import sqlite3
from pathlib import Path

import pytest
from test_retrieval import populate

from community_view.agent import Agent
from community_view.config import Config
from community_view.ingest import embedding_signature
from community_view.knowledge import build_knowledge, validate_plan
from community_view.knowledge_store import (
    historical_questions,
    publish_view,
    published_views,
    record_question,
)
from community_view.knowledge_views import ViewReader
from community_view.models import QuestionState, SearchHit
from community_view.retrieval import Retriever
from community_view.store import Store


@pytest.mark.parametrize("mode", ["naive", "community"])
async def test_disabled_views_keep_original_tools_prompts_and_lazy_graph(
    config, store, client, tmp_path, mode
):
    assert not config.knowledge.record_questions and not config.knowledge.use_compiled
    # Configurations predating knowledge support also default to ordinary QA.
    legacy = config.model_dump()
    legacy.pop("knowledge")
    loaded = Config.model_validate(legacy)
    assert not loaded.knowledge.record_questions and not loaded.knowledge.use_compiled
    config.knowledge.plan_prompt = tmp_path / "absent-plan.txt"
    config.knowledge.context_prompt = tmp_path / "absent-context.txt"
    populate(config, store)
    retriever = Retriever(config, store, client, mode)
    await Agent(config, store, client, retriever).ask("alpha")
    assert "graph_key" not in vars(retriever)
    for messages, options in client.chat_calls:
        assert [t["function"]["name"] for t in options["tools"]] == ["search_chunks"]
        serialized = json.dumps(messages)
        assert "view_catalog" not in serialized and "read_view_answers" not in serialized
        assert messages[1]["content"] == config.prompts.question.read_text().replace(
            "{question}", "alpha"
        )
    assert store.db.execute("select count(*) from question_communities").fetchone()[0] == 0


def test_open_legacy_database_adds_knowledge_tables_without_changing_index(config, client):
    with_store = Store(config.storage.database)
    try:
        populate(config, with_store)
        tables = ["documents", "chunks", "communities", "edges", "meta"]
        before = {t: with_store.db.execute(f"SELECT * FROM {t}").fetchall() for t in tables}
        for table in [
            "question_communities", "question_sources", "knowledge_compilations",
            "knowledge_views", "knowledge_answers",
        ]:
            with_store.db.execute(f"DROP TABLE {table}")
        with_store.db.commit()
    finally:
        with_store.close()
    reopened = Store(config.storage.database)
    try:
        assert before == {t: reopened.db.execute(f"SELECT * FROM {t}").fetchall() for t in tables}
        assert reopened.db.execute("SELECT count(*) FROM knowledge_answers").fetchone()[0] == 0
        assert Retriever(config, reopened, client, "community").documents
    finally:
        reopened.close()


def test_pipeline_resume_rejects_stale_compiled_copy(config, store, client, tmp_path):
    verify = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "scripts" / "run_compiled_benchmark.py")
    )["verify_view_snapshot"]
    populate(config, store)
    retriever = Retriever(config, store, client, "community")
    seed(store, config, retriever)
    target = tmp_path / "frozen.sqlite3"
    with sqlite3.connect(target) as copy:
        store.db.backup(copy)
    verify(config.storage.database, target)
    with store.db:
        store.db.execute("UPDATE knowledge_answers SET answer='new answer'")
    with pytest.raises(ValueError, match="fresh final database"):
        verify(config.storage.database, target)


async def test_plan_compile_and_view_qa_usage_are_separate(config, store, client):
    from community_view.metrics import measure, record_usage

    populate(config, store)
    retriever = Retriever(config, store, client, "community")
    record_question(store, "historical", retriever.graph_key, "alpha?", {"A"}, "complete")

    async def plan(system, payload, schema, retries, validate, purpose):
        record_usage({"prompt_tokens": 10, "completion_tokens": 2}, purpose)
        return {"questions": [{"question": "alpha?", "source_question_ids": ["H0001"]}]}

    original_embed = client.embed

    async def embed(texts):
        record_usage({"total_tokens": 7}, "embedding")
        return await original_embed(texts)

    async def answer(messages, **kwargs):
        record_usage({"prompt_tokens": 20, "completion_tokens": 3}, "agent")
        return {"role": "assistant", "content": "alpha"}

    client.json_completion, client.chat, client.embed = plan, answer, embed
    summary = await build_knowledge(config, store, client)
    assert summary["metrics"]["plan"]["total_tokens"] == 12
    assert summary["metrics"]["compile"]["total_tokens"] == 30
    assert summary["metrics"]["compile"]["embedding_tokens"] == 7
    assert summary["metrics"]["compile"]["rounds"] == 1
    traces = list((config.storage.database.parent / "knowledge" / "traces").glob("*.json"))
    assert len(traces) == 1 and json.loads(traces[0].read_text())["status"] == "complete"
    config.knowledge.use_compiled = True
    with measure("qa") as totals:
        await Agent(config, store, client, retriever).ask("alpha?")
    assert totals.as_dict()["total_tokens"] == 30
    assert totals.embedding_tokens == 7 and totals.rounds == 1


def seed(store, config, retriever, cid="A", questions=None, signature="test"):
    questions = questions or ["alpha details", "beta conditions"]
    entries = [
        {
            "question_id": f"{cid}-Q{i:04d}",
            "question": q,
            "answer": f"ANSWER_SECRET_{i}",
            "source_questions": [
                {
                    "source_question_id": "H0001",
                    "question": "original",
                    "run_ids": ["external-run"],
                    "external_question_ids": ["qa-1"],
                }
            ],
        }
        for i, q in enumerate(questions, 1)
    ]
    publish_view(
        store,
        {"graph_key": retriever.graph_key, "community_id": cid, "signature": signature},
        {
            "community_id": cid,
            "name": cid,
            "embedding_signature": embedding_signature(config),
            "entries": entries,
            "vectors": {e["question_id"]: [1.0, 0.0, 0.0] for e in entries},
        },
    )


def test_plan_validates_sources_and_duplicates():
    item = {"question": "What works?", "source_question_ids": ["H0001", "H0002"]}
    validate_plan({"questions": [item]}, {"H0001", "H0002"})
    validate_plan({"questions": []}, {"H0001"})
    with pytest.raises(ValueError, match="unknown source"):
        validate_plan({"questions": [item]}, {"H0001"})
    with pytest.raises(ValueError, match="duplicate question"):
        validate_plan(
            {"questions": [item, {**item, "question": " WHAT works? "}]}, {"H0001", "H0002"}
        )
    with pytest.raises(ValueError, match="duplicate source"):
        validate_plan(
            {"questions": [{**item, "source_question_ids": ["H0001", "H0001"]}]}, {"H0001"}
        )


async def test_mapping_independent_and_keeps_external_ids(config, store, client):
    populate(config, store)
    config.knowledge.record_questions = True
    retriever = Retriever(config, store, client, "community")
    for identity in ["qa-1", "qa-2"]:
        await Agent(config, store, client, retriever).ask(
            "alpha question", external_question_id=identity
        )
    history = historical_questions(store, retriever.graph_key)
    assert set(history) == {"A", "B"}
    assert len(history["A"]) == 1
    assert set(history["A"][0]["external_question_ids"]) == {"qa-1", "qa-2"}
    assert len(history["A"][0]["run_ids"]) == 2
    assert all("read_view_answers" not in json.dumps(call) for call in client.chat_calls)
    assert all("view_catalog" not in json.dumps(call) for call in client.chat_calls)


async def test_per_question_compilation_resume_provenance_and_no_length_limit(
    config, store, client
):
    populate(config, store)
    r = Retriever(config, store, client, "community")
    record_question(store, "1", r.graph_key, "alpha long question", {"A"}, "complete", "external-1")
    record_question(
        store, "2", r.graph_key, "alpha similar question", {"A"}, "complete", "external-2"
    )
    record_question(store, "3", r.graph_key, "unrelated", {"A"}, "complete")
    record_question(store, "bad", r.graph_key, "FAILED_MUST_NOT_LEAK", {"A"}, "failed")
    plans, chats = [], []

    async def plan(system, payload, schema, retries, validate, purpose):
        plans.append(payload)
        assert "FAILED_MUST_NOT_LEAK" not in json.dumps(payload)
        assert all("keywords" in d for d in payload["document_overviews"])
        ids = [
            q["source_question_id"]
            for q in payload["historical_questions"]
            if q["question"].startswith("alpha")
        ]
        value = {
            "questions": [
                {"question": "alpha?", "source_question_ids": ids},
                {"question": "beta?", "source_question_ids": ids[:1]},
            ]
        }
        validate(value)
        return value

    fail = True

    async def chat(messages, **kwargs):
        chats.append(list(messages))
        assert kwargs["tools"][0]["function"]["name"] == "search_chunks"
        assert len(kwargs["tools"]) == 1
        assert "as briefly as possible" in messages[1]["content"]
        assert "read_view_answers" not in json.dumps(messages)
        if "beta?" in messages[1]["content"] and fail:
            raise RuntimeError("temporary error")
        return {"role": "assistant", "content": "a" * 12000}

    client.json_completion, client.chat = plan, chat
    result = await build_knowledge(config, store, client, "plan")
    assert result["planned"] == 1 and not chats
    result = await build_knowledge(config, store, client, "compile")
    assert result["failed"] == 1 and result["answered_questions"] == 1
    assert not published_views(store, r.graph_key)
    fail = False
    result = await build_knowledge(config, store, client, "compile")
    assert result["complete"] == 1 and result["answered_questions"] == 2
    assert len(plans) == 1 and len(chats) == 3
    assert "beta?" in chats[2][1]["content"] and "alpha?" not in chats[2][1]["content"]
    view = published_views(store, r.graph_key)["A"]
    assert len(view["entries"]) == 2
    assert [e["question_id"] for e in view["entries"]] == ["A-Q0001", "A-Q0002"]
    assert len(view["entries"][0]["answer"]) == 12000
    assert {
        q for s in view["entries"][0]["source_questions"] for q in s["external_question_ids"]
    } == {"external-1", "external-2"}
    assert store.db.execute("select count(*) from question_communities").fetchone()[0] == 4
    assert store.db.execute("select count(*) from knowledge_views").fetchone()[0] == 1
    await build_knowledge(config, store, client)
    assert len(chats) == 3
    assert result["metrics"]["compile"]["rounds"] == 3


@pytest.mark.parametrize("mode", ["naive", "community"])
async def test_catalog_then_selective_read_then_search_with_isolated_dedup(
    config, store, client, mode
):
    populate(config, store)
    config.knowledge.use_compiled = True
    config.knowledge.question_k = 1
    retriever = Retriever(config, store, client, mode)
    seed(store, config, retriever)
    inputs = []

    async def chat(messages, **kwargs):
        inputs.append(list(messages))
        names = {t["function"]["name"] for t in kwargs["tools"]}
        assert names == {"search_chunks", "read_view_answers"}
        tool_messages = [m for m in messages if m["role"] == "tool"]
        if not tool_messages:
            catalog = json.loads(messages[-1]["content"])["view_catalog"]
            assert len(catalog) == 1 and len(catalog[0]["questions"]) == 2
            assert "ANSWER_SECRET" not in json.dumps(messages)
            assert "original" not in messages[-1]["content"]  # external questions are not injected
            calls = [
                ("read_view_answers", {"question_ids": ["A-Q0002"]}),
                ("search_chunks", {"query": "alpha", "search_mode": "keyword", "doc_ids": None}),
                ("read_view_answers", {"question_ids": ["A-Q0002"]}),
            ]
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": str(i),
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)},
                    }
                    for i, (name, args) in enumerate(calls)
                ],
            }
        first, search, again = [json.loads(m["content"]) for m in tool_messages]
        assert first["answers"][0]["answer"] == "ANSWER_SECRET_2"
        assert "ANSWER_SECRET_1" not in json.dumps(messages)
        assert search["chunks"]
        assert again["answers"] == [] and again["already_read"] == ["A-Q0002"]
        return {"role": "assistant", "content": "done"}

    client.chat = chat
    agent = Agent(config, store, client, retriever)
    for _ in range(2):
        result = await agent.ask("alpha")
        assert result.rounds == 2
    assert not store.db.execute("select count(*) from question_communities").fetchone()[0]


async def test_catalog_matches_questions_not_chunk_top_documents(config, store, client):
    populate(config, store)
    r = Retriever(config, store, client, "community")
    seed(store, config, r, "C")
    config.knowledge.use_compiled = True
    reader = ViewReader(config, store, client, r)
    state = QuestionState()
    catalog = await reader.catalog("alpha", state)
    assert catalog["view_catalog"][0]["community_id"] == "C"
    assert state.seen_communities == set()  # normal overview may still be returned later
    result = r.context([SearchHit("a", 0, "alpha", 1)], state)
    assert "compiled_knowledge" not in json.dumps(result)
    assert "ANSWER_SECRET" not in json.dumps(result)
    with pytest.raises(ValueError, match="supplied view_catalog"):
        reader.read(["A-Q0001"], state)
    with pytest.raises(ValueError, match="number"):
        reader.read(["C-Q0001"] * (config.knowledge.read_answer_limit + 1), state)


async def test_view_mapping_and_atomic_failed_read(config, store, client):
    populate(config, store)
    r = Retriever(config, store, client, "community")
    seed(store, config, r)
    reader = ViewReader(config, store, client, r)
    state = QuestionState()
    await reader.catalog("alpha", state)
    seed(store, config, r, signature="replacement")
    with pytest.raises(ValueError, match="changed"):
        reader.read(["A-Q0001", "A-Q0002"], state)
    assert not state.seen_answers


def test_views_never_cross_graph_or_embedding_versions(config, store, client):
    populate(config, store)
    r = Retriever(config, store, client, "community")
    seed(store, config, r)
    config.embedding.model = "different"
    with pytest.raises(ValueError, match="embeddings changed"):
        ViewReader(config, store, client, r)
    communities = store.communities()
    communities[0].overview = "changed"
    store.publish_graph(store.edges(), communities, store.revision, "test")
    from community_view.knowledge_store import graph_key

    assert not published_views(
        store, graph_key(store.documents(), store.edges(), store.communities())
    )


async def test_empty_catalog_and_disabled_feature_have_no_answers(config, store, client):
    populate(config, store)
    r = Retriever(config, store, client, "community")
    with pytest.raises(ValueError, match="No completed"):
        await build_knowledge(config, store, client)
    config.knowledge.use_compiled = True
    await Agent(config, store, client, r).ask("alpha")
    assert any(
        '"view_catalog": []' in json.dumps(call).replace('\\"', '"') for call in client.chat_calls
    )
    config.knowledge.use_compiled = False
    client.chat_calls.clear()
    await Agent(config, store, client, r).ask("alpha")
    assert "view_catalog" not in json.dumps(client.chat_calls)
    assert "read_view_answers" not in json.dumps(client.chat_calls)


async def test_benchmark_view_clone_signature_and_label_isolation(
    config, store, client, text, benchmark_settings, tmp_path
):
    from community_view.communities import cluster
    from community_view.experiments.dataset import load_dataset, prepare
    from community_view.experiments.reuse import clone_index
    from community_view.experiments.runner import predict
    from community_view.ingest import ingest
    from community_view.store import Store

    config.knowledge.record_questions = True
    benchmark_settings.modes = ["community"]
    dataset = load_dataset(benchmark_settings)
    prepare(benchmark_settings, dataset)
    await ingest(dataset.paths, config, store, client, text)
    await cluster(config, store, client)
    await predict(dataset, benchmark_settings, config, store, client)
    original_chat = client.chat

    async def plan(system, payload, schema, retries, validate, purpose):
        assert "GOLD_MUST_NOT_LEAK" not in json.dumps(payload)
        assert "EVIDENCE_MUST_NOT_LEAK" not in json.dumps(payload)
        assert set(payload["historical_questions"][0]) == {"source_question_id", "question"}
        value = {
            "questions": [
                {
                    "question": "alpha?",
                    "source_question_ids": [
                        payload["historical_questions"][0]["source_question_id"]
                    ],
                }
            ]
        }
        validate(value)
        return value

    async def compiler(messages, **kwargs):
        assert len(kwargs["tools"]) == 1
        return {"role": "assistant", "content": "Prepared answer."}

    client.json_completion, client.chat = plan, compiler
    compiled = await build_knowledge(config, store, client)
    assert compiled["complete"] > 0 and not compiled["failed"]
    final = benchmark_settings.model_copy(deep=True)
    final.output_dir = tmp_path / "enriched"
    final.database = final.output_dir / "index.sqlite3"
    final.log_file = final.output_dir / "run.log"
    enriched_config = config.model_copy(deep=True)
    enriched_config.knowledge.use_compiled = True
    enriched_config.knowledge.record_questions = False
    clone_index(
        benchmark_settings.database,
        benchmark_settings.output_dir / "execution.json",
        benchmark_settings.dataset_dir,
        final,
        enriched_config,
    )
    client.chat = original_chat
    client.chat_calls.clear()
    target = Store(final.database)
    try:
        result = await predict(dataset, final, enriched_config, target, client)
        assert result["modes"]["community"]["successful"] == 2
        seen = json.dumps(client.chat_calls)
        assert "view_catalog" in seen and "alpha?" in seen
        assert "Prepared answer." not in seen  # this agent never selected the view answers
        assert "GOLD_MUST_NOT_LEAK" not in seen
        source_ids = target.db.execute("select question_id from question_sources").fetchall()
        assert {x[0] for x in source_ids} == {q["id"] for q in dataset.questions}
        with target.db:
            target.db.execute("update knowledge_answers set answer='modified'")
        with pytest.raises(ValueError, match="configuration/index changed"):
            await predict(dataset, final, enriched_config, target, client)
    finally:
        target.close()


async def test_recording_view_catalog_works_independently(config, store, client):
    populate(config, store)
    config.knowledge.use_compiled = True
    config.knowledge.record_questions = True
    r = Retriever(config, store, client, "community")
    seed(store, config, r, "C")

    async def answer(messages, **kwargs):
        return {"role": "assistant", "content": "I need more evidence."}

    client.chat = answer
    await Agent(config, store, client, r).ask("alpha", external_question_id="test-qa")
    rows = store.db.execute("select community_ids,status from question_communities").fetchall()
    assert rows == [('["C"]', "complete")]


def test_publish_failure_preserves_previous_view(config, store, client):
    populate(config, store)
    r = Retriever(config, store, client, "community")
    seed(store, config, r)
    before = published_views(store, r.graph_key)
    broken = before["A"]
    broken["vectors"] = {}
    with pytest.raises(KeyError):
        publish_view(
            store, {"graph_key": r.graph_key, "community_id": "A", "signature": "bad"}, broken
        )
    after = published_views(store, r.graph_key)
    assert len(after["A"]["entries"]) == 2 and after["A"]["vectors"]


async def test_no_relevant_questions_replaces_view_with_empty_catalog(config, store, client):
    populate(config, store)
    r = Retriever(config, store, client, "community")
    seed(store, config, r)
    record_question(store, "q", r.graph_key, "irrelevant?", {"A"}, "complete")

    async def plan(system, payload, schema, retries, validate, purpose):
        return {"questions": []}

    client.json_completion = plan
    result = await build_knowledge(config, store, client, "plan")
    assert result["skipped"] == 1 and not result["failed"]
    assert not published_views(store, r.graph_key)["A"]["entries"]
    assert await ViewReader(config, store, client, r).catalog("alpha", QuestionState()) == {
        "view_catalog": []
    }
