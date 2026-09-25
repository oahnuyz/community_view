import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from community_view.experiments import load_dataset, prepare, read_jsonl
from community_view.experiments.judge import Rating, evaluate, render_prompt
from community_view.llm import ModelClient
from community_view.metrics import record_usage


def seed_answers(settings):
    dataset = load_dataset(settings)
    prepare(settings, dataset)
    rows = [
        {
            "id": q["id"],
            "question": q["question"],
            "gold_answers": q["gold_answers"],
            "mode": "naive",
            "status": "complete",
            "answer": "Actual generated answer",
            "elapsed_seconds": 1.5,
            "total_tokens": 17,
            "rounds": 2,
        }
        for q in dataset.questions
    ]
    (settings.output_dir / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return dataset


async def test_judge_concurrency_scores_resume_and_cost_isolation(
    benchmark_settings, config, client
):
    dataset = seed_answers(benchmark_settings)
    calls, active, peak = [], 0, 0

    async def rate(system, payload, schema, retries, validate, purpose):
        nonlocal active, peak
        assert system == "" and purpose == "judge"
        assert retries == config.model.retries
        assert "Gold Answers: GOLD_MUST_NOT_LEAK" in payload
        assert "Generated Answer: Actual generated answer" in payload
        calls.append(payload)
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        record_usage({"prompt_tokens": 30, "completion_tokens": 10}, "judge")
        value = {
            "score": 4 if "Question: alpha question z" in payload else 2,
            "reasoning": "The answer matches.",
        }
        validate(value)
        return value

    client.json_completion = rate
    summary = await evaluate(dataset, benchmark_settings, config, client)
    result = summary["modes"]["naive"]
    assert peak == benchmark_settings.concurrency == 2
    assert result["evaluation"]["accuracy"] == 3
    assert result["evaluation"]["normalized_accuracy"] == 0.75
    assert result["evaluation"]["scored"] == 2
    assert result["evaluation"]["total_tokens"] == 80
    assert result["total_tokens"] == 34  # Judge usage never changes QA usage.
    rows = read_jsonl(benchmark_settings.output_dir / "results.jsonl")
    assert all(row["evaluation"]["reasoning"] and row["answer"] for row in rows)
    await evaluate(dataset, benchmark_settings, config, client)
    assert len(calls) == 2
    rows[0]["answer"] = "Changed generated answer"
    (benchmark_settings.output_dir / "results.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )

    # Changed answer requires re-evaluation; unchanged rows retain their grade.
    async def rerate(*args):
        calls.append(args[1])
        return {"score": 0, "reasoning": "The changed answer is incorrect."}

    client.json_completion = rerate
    summary = await evaluate(dataset, benchmark_settings, config, client)
    assert len(calls) == 3 and summary["modes"]["naive"]["evaluation"]["accuracy"] == 1


async def test_judge_failures_are_not_zero_scores(benchmark_settings, config, client):
    dataset = seed_answers(benchmark_settings)

    async def rate(*args):
        if "Question: alpha question z" in args[1]:
            return {"score": 0, "reasoning": "Incorrect answer."}
        raise RuntimeError("Service unavailable")

    client.json_completion = rate
    summary = await evaluate(dataset, benchmark_settings, config, client)
    rating = summary["modes"]["naive"]["evaluation"]
    assert rating["scored"] == 1 and rating["failed"] == 1
    assert rating["accuracy"] == 0 and rating["normalized_accuracy"] == 0
    rows = read_jsonl(benchmark_settings.output_dir / "results.jsonl")
    assert rows[1]["evaluation"]["score"] is None

    async def retry(*args):
        return {"score": 4, "reasoning": "Correct answer."}

    client.json_completion = retry
    summary = await evaluate(dataset, benchmark_settings, config, client)
    assert summary["modes"]["naive"]["evaluation"]["accuracy"] == 2


@pytest.mark.parametrize("score", [-1, 5, True, 2.5, "4"])
def test_judge_rejects_invalid_scores(score):
    with pytest.raises(ValidationError):
        Rating.model_validate({"score": score, "reasoning": "Explanation"})


def test_prompt_is_single_pass_and_gold_joined_by_pipe(config):
    template = config.prompts.judge.read_text()
    prompt = render_prompt(
        template, "Question containing {generated_answer}", ["one", "two"], "actual {question}"
    )
    assert "Gold Answers: one | two" in prompt
    assert "Question: Question containing {generated_answer}" in prompt
    assert "Generated Answer: actual {question}" in prompt
    assert '{"score": 0 to 4, "reasoning": "string"}' in prompt


async def test_judge_stage_needs_no_index_or_embedding_key(
    benchmark_settings, config, client, monkeypatch
):
    import community_view.experiments.runner as runner

    seed_answers(benchmark_settings)
    config.keys_file.write_text('chat_api_key: test\nembedding_api_key: ""\n')

    async def rate(*args):
        return {"score": 4, "reasoning": "Correct."}

    async def close():
        pass

    client.json_completion, client.close = rate, close
    monkeypatch.setattr(runner, "ModelClient", lambda *args: client)

    def forbidden(*args, **kwargs):
        raise AssertionError("Judge must not open an index or initialize embeddings")

    monkeypatch.setattr(runner, "Store", forbidden)
    monkeypatch.setattr(runner, "TextProcessor", forbidden)
    summary = await runner.run_benchmark(config, benchmark_settings, "judge")
    assert summary["modes"]["naive"]["evaluation"]["normalized_accuracy"] == 1


async def test_judge_exact_http_prompt_and_validation_retry(config, store, text):
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        value = {"score": 9 if len(requests) == 1 else 4, "reasoning": "It matches."}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(value)},
                    }
                ],
                "usage": {"total_tokens": 10},
            },
        )

    client = ModelClient(config, store, text, httpx.MockTransport(respond))
    prompt = render_prompt(config.prompts.judge.read_text(), "q", ["gold1", "gold2"], "answer")
    try:
        value = await client.json_completion(
            "",
            prompt,
            Rating.model_json_schema(),
            config.model.retries,
            Rating.model_validate,
            "judge",
        )
        assert value["score"] == 4 and len(requests) == 2
        assert requests[0]["model"] == config.model.chat_model
        assert requests[0]["messages"] == [{"role": "user", "content": prompt}]
        assert "max_tokens" not in requests[0] and "max_completion_tokens" not in requests[0]
    finally:
        await client.close()


async def test_judge_rejects_model_drift_from_qa_execution(benchmark_settings, config, client):
    dataset = seed_answers(benchmark_settings)
    execution = {
        "config": config.model_dump(mode="json"),
        "qa_concurrency": benchmark_settings.concurrency,
    }
    (benchmark_settings.output_dir / "execution.json").write_text(json.dumps(execution))
    config.model.chat_model = "different-model"
    with pytest.raises(ValueError, match="must match"):
        await evaluate(dataset, benchmark_settings, config, client)


async def test_failed_answer_is_skipped_not_graded(benchmark_settings, config, client):
    dataset = seed_answers(benchmark_settings)
    rows = read_jsonl(benchmark_settings.output_dir / "results.jsonl")
    rows[0].update(status="failed", answer=None)
    (benchmark_settings.output_dir / "results.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )
    calls = []

    async def rate(*args):
        calls.append(args)
        return {"score": 4, "reasoning": "Correct."}

    client.json_completion = rate
    summary = await evaluate(dataset, benchmark_settings, config, client)
    stats = summary["modes"]["naive"]["evaluation"]
    assert len(calls) == 1 and stats["skipped"] == 1
    assert stats["scored"] == 1 and stats["accuracy"] == 4
