"""Independent LLM-as-judge pass using the same chat configuration and QA concurrency."""

import asyncio
import json
import logging
import re
import time

from pydantic import BaseModel, ConfigDict, Field

from ..ingest import digest
from ..metrics import measure
from ..store import dumps
from .dataset import write_json
from .results import load_results, save_results

log = logging.getLogger(__name__)


class Rating(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    score: int = Field(ge=0, le=4)
    reasoning: str = Field(min_length=1)


def render_prompt(template, question, gold_answers, generated_answer):
    # Single substitution pass: values containing braces/placeholders remain verbatim.
    values = {
        "question": question,
        "gold_answers_joined_by_pipe": " | ".join(gold_answers),
        "generated_answer": generated_answer,
    }
    return re.sub(
        r"\{(question|gold_answers_joined_by_pipe|generated_answer)\}",
        lambda match: values[match.group(1)],
        template,
    )


async def evaluate(dataset, settings, config, client):
    latest = load_results(settings)
    targets = [(mode, q) for mode in settings.modes for q in dataset.questions]
    missing = [(mode, q["id"]) for mode, q in targets if (mode, q["id"]) not in latest]
    if missing:
        raise ValueError(f"Missing {len(missing)} QA result(s); run --stage ask before judge")
    execution_path = settings.output_dir / "execution.json"
    if execution_path.exists():
        execution = json.loads(execution_path.read_text(encoding="utf-8"))
        if (
            execution["config"]["model"] != config.model.model_dump(mode="json")
            or execution["qa_concurrency"] != settings.concurrency
        ):
            raise ValueError("Judge model configuration/concurrency must match the QA execution")
    for mode, question in targets:
        row = latest[(mode, question["id"])]
        if row["question"] != question["question"] or row["gold_answers"] != question.get(
            "gold_answers"
        ):
            raise ValueError(f"Dataset no longer matches QA result {question['id']}")
    template = config.prompts.judge.read_text(encoding="utf-8")
    # No separate judge model, temperature or parallelism setting.
    signature = digest(
        dumps(
            {
                "model": config.model.model_dump(),
                "concurrency": settings.concurrency,
                "prompt": template,
            }
        )
    )
    slots = asyncio.Semaphore(settings.concurrency)
    write_json(
        settings.output_dir / "judge_execution.json",
        {
            "signature": signature,
            "model": config.model.model_dump(),
            "concurrency": settings.concurrency,
            "prompt": template,
        },
    )

    def validate(value):
        rating = Rating.model_validate(value)
        if not rating.reasoning.strip():
            raise ValueError("reasoning must not be blank")

    async def one(mode, question):
        row = latest[(mode, question["id"])]
        answer, gold = row.get("answer"), question.get("gold_answers")
        if row["status"] != "complete" or not isinstance(answer, str) or not answer.strip():
            row["evaluation"] = {
                "status": "skipped",
                "score": None,
                "reasoning": None,
                "error": "QA did not produce a successful nonempty answer",
            }
            save_results(dataset, settings, latest)
            return
        if (
            not isinstance(gold, list)
            or not gold
            or any(not isinstance(g, str) or not g.strip() for g in gold)
        ):
            row["evaluation"] = {
                "status": "skipped",
                "score": None,
                "reasoning": None,
                "error": "Gold answers are missing or invalid",
            }
            save_results(dataset, settings, latest)
            return
        item_signature = digest(
            dumps(
                {
                    "judge": signature,
                    "question": question["question"],
                    "gold": gold,
                    "answer": answer,
                }
            )
        )
        previous = row.get("evaluation", {})
        if previous.get("status") == "complete" and previous.get("signature") == item_signature:
            return
        async with slots:
            started = time.monotonic()
            result = {
                "status": "complete",
                "signature": item_signature,
                "score": None,
                "reasoning": None,
            }
            with measure(f"judge:{mode}:{question['id']}") as totals:
                try:
                    prompt = render_prompt(template, question["question"], gold, answer)
                    value = await client.json_completion(
                        "",
                        prompt,
                        Rating.model_json_schema(),
                        config.model.retries,
                        validate,
                        "judge",
                    )
                    validate(value)
                    result.update(value, normalized_score=value["score"] / 4)
                except Exception as exc:
                    result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                    log.exception("Judge failed: mode=%s id=%s", mode, question["id"])
            result.update(totals.as_dict())
            result.pop("rounds")
            result["elapsed_seconds"] = time.monotonic() - started
            if previous.get("signature") == item_signature:
                for field in (
                    "elapsed_seconds",
                    "llm_input_tokens",
                    "llm_output_tokens",
                    "llm_total_tokens",
                    "embedding_tokens",
                    "total_tokens",
                ):
                    result[field] += previous.get(field, 0)
            row["evaluation"] = result
            save_results(dataset, settings, latest)
            log.info(
                "Judge %s mode=%s id=%s score=%s",
                result["status"],
                mode,
                question["id"],
                result["score"],
            )

    async with asyncio.TaskGroup() as group:
        for mode, question in targets:
            group.create_task(one(mode, question))
    return save_results(dataset, settings, latest)
