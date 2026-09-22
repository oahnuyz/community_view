import json

import pytest

from community_wiki.experiments import (
    load_dataset,
    predict,
    prepare,
    read_jsonl,
    verify_index,
)
from community_wiki.ingest import ingest


def test_benchmark_file_order_checksums_and_separate_references(benchmark_settings):
    dataset = load_dataset(benchmark_settings)
    assert [q["id"] for q in dataset.questions] == ["z", "a"]
    assert (
        len(dataset.paths) == 2
    )  # Use complete corpus, not QA gold document_ids as a retrieval filter.
    prepare(benchmark_settings, dataset)
    assert (benchmark_settings.output_dir / "selection.json").exists()
    dataset.paths[0].write_text("tampered")
    with pytest.raises(ValueError, match="checksum"):
        load_dataset(benchmark_settings)


def test_benchmark_selection_not_silently_shortened(benchmark_settings):
    benchmark_settings.count = 4
    with pytest.raises(ValueError, match="fewer questions"):
        load_dataset(benchmark_settings)


async def test_benchmark_resumes_and_does_not_leak_gold(
    benchmark_settings, config, store, client, text
):
    dataset = load_dataset(benchmark_settings)
    prepare(benchmark_settings, dataset)
    with pytest.raises(ValueError, match="incomplete"):
        verify_index(dataset, config, store, complete=True)
    assert not (await ingest(dataset.paths, config, store, client, text)).errors
    summary = await predict(dataset, benchmark_settings, config, store, client)
    assert summary["modes"]["naive"]["successful"] == 2
    calls = len(client.chat_calls)
    seen = json.dumps(client.chat_calls)
    assert "GOLD_MUST_NOT_LEAK" not in seen and "EVIDENCE_MUST_NOT_LEAK" not in seen
    await predict(dataset, benchmark_settings, config, store, client)
    assert len(client.chat_calls) == calls
    answers = read_jsonl(benchmark_settings.output_dir / "results.jsonl")
    assert [row["id"] for row in answers] == ["z", "a"]
    config.agent.max_rounds += 1
    with pytest.raises(ValueError, match="configuration/index changed"):
        await predict(dataset, benchmark_settings, config, store, client)


async def test_benchmark_retries_only_failed_questions(
    benchmark_settings, config, store, client, text
):
    dataset = load_dataset(benchmark_settings)
    prepare(benchmark_settings, dataset)
    await ingest(dataset.paths, config, store, client, text)
    original = client.chat

    async def fail_one(messages, *args, **kwargs):
        if any("Question: alpha question a" in (m.get("content") or "") for m in messages):
            raise RuntimeError("Temporary service failure")
        return await original(messages, *args, **kwargs)

    client.chat = fail_one
    summary = await predict(dataset, benchmark_settings, config, store, client)
    assert summary["modes"]["naive"]["failed"] == 1
    old_calls = len(client.chat_calls)
    client.chat = original
    summary = await predict(dataset, benchmark_settings, config, store, client)
    assert summary["modes"]["naive"]["successful"] == 2
    assert len(client.chat_calls) - old_calls == 3
    assert len(read_jsonl(benchmark_settings.output_dir / "results.jsonl")) == 2


async def test_indexing_and_per_qa_totals_trace_and_prompt(
    benchmark_settings, config, store, client, text
):
    from community_wiki.experiments.runner import index
    from community_wiki.metrics import record_usage

    dataset = load_dataset(benchmark_settings)
    prepare(benchmark_settings, dataset)
    original_json, original_embed, original_chat = client.json_completion, client.embed, client.chat

    async def json_call(*args, **kwargs):
        record_usage({"prompt_tokens": 100, "completion_tokens": 10}, "document_overview")
        return await original_json(*args, **kwargs)

    async def embed(texts):
        record_usage({"total_tokens": 7 * len(texts)}, "embedding")
        return await original_embed(texts)

    async def chat(*args, **kwargs):
        record_usage({"prompt_tokens": 100, "completion_tokens": 10}, "agent")
        message = await original_chat(*args, **kwargs)
        for call in message.get("tool_calls", []):
            arguments = json.loads(call["function"]["arguments"])
            arguments["search_mode"] = "hybrid"
            call["function"]["arguments"] = json.dumps(arguments)
        return message

    client.json_completion, client.embed, client.chat = json_call, embed, chat
    indexed = await index(dataset, benchmark_settings, config, store, client, text)
    assert indexed["total_tokens"] == 248  # 2 overviews * 110 + 4 document/chunk embeddings * 7
    assert indexed["embedding_tokens"] == 28
    summary = await predict(dataset, benchmark_settings, config, store, client)
    rows = read_jsonl(benchmark_settings.output_dir / "results.jsonl")
    assert len(rows) == 2
    assert all(row["total_tokens"] == 344 and row["embedding_tokens"] == 14 for row in rows)
    assert all(row["rounds"] == 3 for row in rows)
    assert (
        summary["modes"]["naive"]["mean_elapsed_seconds"]
        == sum(r["elapsed_seconds"] for r in rows) / 2
    )
    assert summary["modes"]["naive"]["mean_total_tokens"] == 344
    for row in rows:
        assert row["answer"] and row["gold_answers"] == ["GOLD_MUST_NOT_LEAK"]
        trace = json.loads((benchmark_settings.output_dir / row["trace_file"]).read_text())
        user_message = next(m["content"] for m in trace["messages"] if m["role"] == "user")
        assert (
            user_message
            == f"Answer this question as briefly as possible. Use only the information in the context. Do not use any external source.\n\nQuestion: {row['question']}\n"
        )
        assert trace["messages"][-1]["content"] == row["answer"]
        assert "GOLD_MUST_NOT_LEAK" not in json.dumps(trace)
    assert not (benchmark_settings.output_dir / "api_calls.jsonl").exists()
    assert not (benchmark_settings.output_dir / "references.jsonl").exists()


def test_all_questions_option(benchmark_settings):
    benchmark_settings.count = None
    assert len(load_dataset(benchmark_settings).questions) == 3


async def test_separate_ingest_and_cluster_stages(benchmark_settings, config, store, client, text):
    from community_wiki.experiments.indexing import index

    benchmark_settings.modes = ["community"]
    dataset = load_dataset(benchmark_settings)
    prepare(benchmark_settings, dataset)
    await index(dataset, benchmark_settings, config, store, client, text, stage="ingest")
    assert len(store.documents()) == 2 and not store.communities()
    assert all(purpose == "document_overview" for purpose, _ in client.calls)
    before = len(client.calls)

    async def forbidden(*args):
        raise AssertionError("Cluster stage must not regenerate embeddings")

    client.embed = forbidden
    metrics = await index(dataset, benchmark_settings, config, store, client, None, stage="cluster")
    assert store.communities()
    assert all(purpose == "community_overview" for purpose, _ in client.calls[before:])
    assert set(metrics["stages"]) == {"documents", "communities"}
    assert metrics["elapsed_seconds"] == sum(
        row["elapsed_seconds"] for row in metrics["stages"].values()
    )


async def test_all_stage_runs_qa_then_judge(benchmark_settings, config, client, monkeypatch):
    import community_wiki.experiments.runner as runner

    original = client.json_completion
    judged = []

    async def generate(*args, **kwargs):
        if args[-1] == "judge":
            judged.append(args[1])
            return {"score": 3, "reasoning": "Mostly correct."}
        return await original(*args, **kwargs)

    async def close():
        pass

    client.json_completion, client.close = generate, close
    monkeypatch.setattr(runner, "ModelClient", lambda *args: client)
    summary = await runner.run_benchmark(config, benchmark_settings, "all")
    assert len(judged) == 2
    assert summary["modes"]["naive"]["evaluation"]["accuracy"] == 3
    assert (benchmark_settings.output_dir / "indexing_metrics.json").exists()
    assert len(list((benchmark_settings.output_dir / "traces").glob("*.json"))) == 2


async def test_judge_prompt_change_does_not_rerun_qa(
    benchmark_settings, config, store, client, text, tmp_path
):
    dataset = load_dataset(benchmark_settings)
    prepare(benchmark_settings, dataset)
    await ingest(dataset.paths, config, store, client, text)
    await predict(dataset, benchmark_settings, config, store, client)
    calls = len(client.chat_calls)
    prompt = tmp_path / "different_judge.txt"
    prompt.write_text(config.prompts.judge.read_text() + "\n")
    config.prompts.judge = prompt
    await predict(dataset, benchmark_settings, config, store, client)
    assert len(client.chat_calls) == calls
