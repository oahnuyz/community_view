import json

import pytest
from test_retrieval import populate

from community_view.historical_views import build_filtered_views, load_history, validate_filter
from community_view.knowledge_store import record_question
from community_view.knowledge_views import ViewReader
from community_view.models import QuestionState
from community_view.retrieval import Retriever


def seed_history(config, store, client, tmp_path):
    populate(config, store)
    r = Retriever(config, store, client, "community")
    rows = []
    for i, (question, answer) in enumerate(
        [
            ("Who was there in August? ", "EXACT_ANSWER_ONE"),
            ("Who was there in August? ", "EXACT_ANSWER_TWO"),
        ],
        1,
    ):
        run, qid = f"run-{i}", f"external-{i}"
        store.save_run(
            run,
            "community",
            "complete",
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ],
        )
        record_question(store, run, r.graph_key, question, {"A", "B"}, "complete", qid)
        rows.append(
            {
                "id": qid,
                "run_id": run,
                "mode": "community",
                "status": "complete",
                "question": question,
                "answer": answer,
                "gold_answers": ["GOLD_SECRET"],
                "evaluation": {"score": 4, "reasoning": "JUDGE_SECRET"},
            }
        )
    config.knowledge.history_results = tmp_path / "results.jsonl"
    config.knowledge.history_results.write_text("".join(json.dumps(x) + "\n" for x in rows))
    return r, rows


async def test_filter_copies_exact_answers_without_compiling_and_reads_existing_views(
    config, store, client, tmp_path
):
    r, rows = seed_history(config, store, client, tmp_path)
    calls = []

    async def select(system, payload, schema, retries, validate, purpose):
        assert purpose == "knowledge_filter"
        text = json.dumps(payload)
        assert all(word not in text for word in ["EXACT_ANSWER", "GOLD_SECRET", "JUDGE_SECRET"])
        assert "fully or partly relevant" in system
        assert set(payload["historical_questions"][0]) == {"source_question_id", "question"}
        cid = payload["communities"][0]["community_id"]
        calls.append(cid)
        result = {"keep_question_ids": ["H0002", "H0001"] if cid == "A" else []}
        validate(result)
        return result

    async def forbidden(*args, **kwargs):
        raise AssertionError("No compilation agent or answer generation is allowed")

    client.json_completion, client.chat = select, forbidden
    summary = await build_filtered_views(config, store, client)
    assert summary["complete"] == 1 and summary["skipped"] == 1 and summary["failed"] == 0
    assert summary["retained_pairs"] == 2 and summary["candidate_pairs"] == 4
    assert set(summary["metrics"]) == {"filter", "embedding"}
    entries = store.db.execute(
        "SELECT question,answer,source_questions FROM knowledge_answers ORDER BY ordinal"
    ).fetchall()
    assert [(r[0], r[1]) for r in entries] == [(x["question"], x["answer"]) for x in rows]
    assert json.loads(entries[0][2])[0]["run_ids"] == ["run-1"]
    assert store.db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 2
    await build_filtered_views(config, store, client)
    assert len(calls) == 2  # Completed work resumes without refiltering.
    reader = ViewReader(config, store, client, r)
    state = QuestionState()
    catalog = await reader.catalog(rows[0]["question"], state)
    ids = [q["question_id"] for c in catalog["view_catalog"] for q in c["questions"]]
    result = reader.read(ids[:1], state)
    assert result["answers"][0]["answer"] == "EXACT_ANSWER_ONE"
    assert reader.read(ids[:1], state)["already_read"] == ids[:1]


@pytest.mark.parametrize("fault", ["missing_run", "wrong_answer", "wrong_graph", "duplicate_id"])
def test_rejects_mismatched_sources(config, store, client, tmp_path, fault):
    r, rows = seed_history(config, store, client, tmp_path)
    if fault == "missing_run":
        store.db.execute("DELETE FROM runs WHERE run_id='run-1'")
    elif fault == "wrong_answer":
        rows[0]["answer"] = "A different attempt's answer"
    elif fault == "wrong_graph":
        store.db.execute("UPDATE question_communities SET graph_key='wrong' WHERE run_id='run-1'")
    else:
        rows.append(rows[0])
    config.knowledge.history_results.write_text("".join(json.dumps(x) + "\n" for x in rows))
    with pytest.raises(ValueError):
        load_history(store, r.graph_key, config.knowledge.history_results, {"A", "B"})


@pytest.mark.parametrize(
    "value",
    [
        {"keep_question_ids": ["H0001", "H0001"]},
        {"keep_question_ids": ["unknown"]},
        {"keep_question_ids": "H0001"},
        {"keep_question_ids": [], "answer": "illegal"},
    ],
)
def test_filter_rejects_invalid_selection(value):
    with pytest.raises(ValueError):
        validate_filter(value, {"H0001"})


async def test_embedding_failure_resumes_saved_selection(config, store, client, tmp_path):
    seed_history(config, store, client, tmp_path)
    count = 0

    async def select(system, payload, schema, retries, validate, purpose):
        nonlocal count
        count += 1
        return {"keep_question_ids": ["H0001"]}

    embed = client.embed

    async def fail(*args):
        raise RuntimeError("temporary embedding failure")

    client.json_completion, client.embed = select, fail
    result = await build_filtered_views(config, store, client)
    assert result["failed"] == 2
    assert store.db.execute("SELECT COUNT(*) FROM knowledge_answers").fetchone()[0] == 0
    client.embed = embed
    result = await build_filtered_views(config, store, client)
    assert result["complete"] == 2 and count == 2


async def test_atomic_workload_publication_and_cached_republication(
    config, store, client, tmp_path
):
    from test_knowledge import seed

    from community_view.knowledge_store import published_views

    retriever, rows = seed_history(config, store, client, tmp_path)
    seed(store, config, retriever, cid="C")
    old = published_views(store, retriever.graph_key)
    fail = True
    calls = []

    async def select(system, payload, schema, retries, validate, purpose):
        cid = payload["communities"][0]["community_id"]
        calls.append(cid)
        if fail and cid == "B":
            raise RuntimeError("temporary filter failure")
        return {"keep_question_ids": ["H0001"]}

    client.json_completion = select
    result = await build_filtered_views(config, store, client)
    assert result["failed"] == 1 and not result["published"]
    assert published_views(store, retriever.graph_key) == old
    fail = False
    result = await build_filtered_views(config, store, client)
    assert result["published"] and result["failed"] == 0
    assert calls.count("A") == 1 and calls.count("B") == 2
    original = published_views(store, retriever.graph_key)
    assert set(original) == {"A", "B"}  # Unmapped C must no longer be offered.

    # Publish a different source workload, then restore the first from cached jobs.
    config.knowledge.history_results.write_text(json.dumps(rows[1]) + "\n")
    await build_filtered_views(config, store, client)
    assert (
        published_views(store, retriever.graph_key)["A"]["entries"][0]["answer"]
        == "EXACT_ANSWER_TWO"
    )
    count = len(calls)
    config.knowledge.history_results.write_text("".join(json.dumps(r) + "\n" for r in rows))
    await build_filtered_views(config, store, client)
    assert len(calls) == count
    assert published_views(store, retriever.graph_key) == original


def test_publication_transaction_rolls_back_and_preserves_other_graph(
    config, store, client, tmp_path
):
    from test_knowledge import seed

    from community_view.knowledge_store import published_views, replace_views

    retriever, _ = seed_history(config, store, client, tmp_path)
    seed(store, config, retriever)
    old = published_views(store, retriever.graph_key)
    job = {"graph_key": retriever.graph_key, "community_id": "B", "signature": "bad"}
    # An error after DELETE and INSERT must restore the previous publication.
    with pytest.raises(KeyError):
        replace_views(store, retriever.graph_key, [(job, {"entries": [{"question_id": "B-Q1"}]})])
    assert published_views(store, retriever.graph_key) == old
    replace_views(store, "different-graph", [])
    assert published_views(store, retriever.graph_key) == old


def test_filter_cli_and_config_relative_paths(tmp_path):
    import yaml
    from conftest import ROOT

    from community_view.cli import parser
    from community_view.config import Config

    data = yaml.safe_load((ROOT / "config.yaml").read_text())
    data["knowledge"]["history_results"] = "runs/source/results.jsonl"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(data))
    config = Config.load(config_path)
    assert config.knowledge.history_results == tmp_path / "runs/source/results.jsonl"
    assert config.knowledge.filter_prompt == tmp_path / "prompts/knowledge_filter.txt"
    assert parser().parse_args(["knowledge-filter"]).command == "knowledge-filter"
