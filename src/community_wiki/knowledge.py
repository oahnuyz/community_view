"""Refine historical questions and answer each one into a community view."""

import asyncio
import json
import logging
import time
import uuid

from .agent import Agent
from .experiments.dataset import write_json
from .ingest import embedding_signature
from .knowledge_store import (
    fingerprint,
    historical_questions,
    load_job,
    publish_view,
    save_job,
)
from .metrics import measure
from .retrieval import Retriever

log = logging.getLogger(__name__)


def initial_context(retriever, community):
    return {
        "communities": [
            {
                "community_id": community.community_id,
                "name": community.name,
                "overview": community.overview,
                "doc_ids": community.doc_ids,
            }
        ],
        "document_overviews": [
            {"doc_id": d, **retriever.documents[d].overview.model_dump()} for d in community.doc_ids
        ],
    }


def validate_plan(value, sources):
    if not isinstance(value, dict) or set(value) != {"questions"}:
        raise ValueError("Expected exactly questions")
    if not isinstance(value["questions"], list):
        raise ValueError("questions must be a list")
    seen = set()
    for i, item in enumerate(value["questions"], 1):
        if not isinstance(item, dict) or set(item) != {"question", "source_question_ids"}:
            raise ValueError(f"Question {i}: expected question and source_question_ids")
        question = item["question"]
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"Question {i}: question cannot be blank")
        normalized = " ".join(question.split()).casefold()
        if normalized in seen:
            raise ValueError(f"Question {i}: duplicate question; merge its source_question_ids")
        seen.add(normalized)
        ids = item["source_question_ids"]
        if not isinstance(ids, list) or not ids or any(not isinstance(x, str) for x in ids):
            raise ValueError(f"Question {i}: source_question_ids must be a nonempty string list")
        if len(set(ids)) != len(ids):
            raise ValueError(f"Question {i}: duplicate source_question_ids")
        unknown = set(ids) - sources
        if unknown:
            raise ValueError(f"Question {i}: unknown source_question_ids {sorted(unknown)}")


async def build_knowledge(config, store, client, stage="all"):
    if stage not in {"plan", "compile", "all"}:
        raise ValueError("Unknown knowledge stage")
    original = config.model_copy(deep=True)
    original.knowledge.use_compiled = False
    original.knowledge.record_questions = False
    retriever = Retriever(original, store, client, "community")
    histories = historical_questions(store, retriever.graph_key)
    if not histories:
        raise ValueError("No completed question/community mappings for this graph")
    leaves = {c.community_id: c for c in retriever.communities.values() if c.is_leaf}
    if histories.keys() - leaves.keys():
        raise ValueError("Historical mappings contain non-leaf or missing communities")
    c = config.knowledge
    plan_prompt = c.plan_prompt.read_text()
    shared = {
        "format": "question_views_v1",
        "graph": retriever.graph_key,
        "model": config.model.model_dump(),
        "embedding": config.embedding.model_dump(),
        "agent": config.agent.model_dump(),
        "retrieval": config.retrieval.model_dump(),
        "validation_retries": c.validation_retries,
        "plan_prompt": plan_prompt,
        "agent_prompt": config.prompts.agent.read_text(),
        "question_prompt": config.prompts.question.read_text(),
    }
    output = config.storage.database.parent / "knowledge"
    (output / "traces").mkdir(parents=True, exist_ok=True)
    slots = asyncio.Semaphore(c.concurrency)

    async def one(identity, questions):
        signature = fingerprint({**shared, "community_id": identity, "questions": questions})
        job = load_job(store, signature, identity) or {
            "signature": signature,
            "community_id": identity,
            "graph_key": retriever.graph_key,
            "question_count": len(questions),
            "status": "pending",
            "metrics": {},
            "answers": [],
        }
        if job["status"] in {"complete", "skipped"}:
            return job
        context = initial_context(retriever, leaves[identity])
        sources = {q["source_question_id"]: q for q in questions}

        async def measured(label, action):
            started = time.monotonic()
            with measure(f"knowledge:{label}:{identity}") as totals:
                try:
                    return await action()
                finally:
                    values = totals.as_dict()
                    values["elapsed_seconds"] = time.monotonic() - started
                    previous = job["metrics"].get(label, {})
                    job["metrics"][label] = {k: previous.get(k, 0) + v for k, v in values.items()}

        def view():
            return {
                "community_id": identity,
                "name": leaves[identity].name,
                "embedding_signature": embedding_signature(config),
                "entries": job["answers"],
                "vectors": job.get("vectors", {}),
            }

        async with slots:
            try:
                if "plan" not in job:
                    if stage == "compile":
                        raise ValueError(
                            "Missing successful plan; run knowledge --stage plan first"
                        )
                    schema = {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "questions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "question": {"type": "string", "minLength": 1},
                                        "source_question_ids": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "minItems": 1,
                                        },
                                    },
                                    "required": ["question", "source_question_ids"],
                                },
                            }
                        },
                        "required": ["questions"],
                    }
                    job["plan"] = await measured(
                        "plan",
                        lambda: client.json_completion(
                            plan_prompt,
                            {
                                **context,
                                "historical_questions": [
                                    {
                                        "source_question_id": q["source_question_id"],
                                        "question": q["question"],
                                    }
                                    for q in questions
                                ],
                            },
                            schema,
                            c.validation_retries,
                            lambda v: validate_plan(v, set(sources)),
                            "knowledge_plan",
                        ),
                    )
                job.pop("error", None)
                planned = job["plan"]["questions"]
                job["status"] = "planned" if planned else "skipped"
                save_job(store, job)
                if not planned:
                    publish_view(store, job, view())
                    return job
                if stage == "plan":
                    return job
                # Each question has its own loop and history; successful answers survive retries.
                for index, item in enumerate(planned, 1):
                    question_id = f"{identity}-Q{index:04d}"
                    if any(a["question_id"] == question_id for a in job["answers"]):
                        continue
                    run_id = uuid.uuid4().hex
                    try:
                        result = await measured(
                            "compile",
                            lambda: Agent(original, store, client, retriever).ask(
                                item["question"],
                                run_id=run_id,
                                initial_context=context,
                                track_question=False,
                            ),
                        )
                    finally:
                        row = store.db.execute(
                            "SELECT status,messages FROM runs WHERE run_id=?", (run_id,)
                        ).fetchone()
                        if row:
                            write_json(
                                output / "traces" / f"{run_id}.json",
                                {
                                    "community_id": identity,
                                    "question_id": question_id,
                                    "run_id": run_id,
                                    "status": row[0],
                                    "messages": json.loads(row[1]),
                                },
                            )
                    job["answers"].append(
                        {
                            "question_id": question_id,
                            "question": item["question"],
                            "answer": result.answer,
                            "source_questions": [sources[s] for s in item["source_question_ids"]],
                            "run_id": run_id,
                        }
                    )
                    save_job(store, job)
                if "vectors" not in job:
                    vectors = await measured(
                        "compile", lambda: client.embed([a["question"] for a in job["answers"]])
                    )
                    job["vectors"] = {
                        a["question_id"]: v.tolist()
                        for a, v in zip(job["answers"], vectors, strict=True)
                    }
                publish_view(store, job, view())
                job["status"] = "complete"
                log.info("Community view compiled: community=%s answers=%s", identity, len(planned))
            except Exception as exc:
                job.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                log.exception("Community view failed: community=%s", identity)
            finally:
                save_job(store, job)
            return job

    started = time.monotonic()
    jobs = await asyncio.gather(*(one(i, q) for i, q in sorted(histories.items())))
    summary = {
        "stage": stage,
        "graph_key": retriever.graph_key,
        "wall_seconds": time.monotonic() - started,
        "leaf_count": len(leaves),
        "mapped_communities": len(jobs),
        "unmapped_communities": len(leaves) - len(jobs),
        "metrics": {},
    }
    summary.update(
        {
            s: sum(j["status"] == s for j in jobs)
            for s in ["complete", "skipped", "planned", "failed"]
        }
    )
    summary["answered_questions"] = sum(len(j["answers"]) for j in jobs)
    for label in ["plan", "compile"]:
        totals = {}
        for job in jobs:
            for key, value in job["metrics"].get(label, {}).items():
                totals[key] = totals.get(key, 0) + value
        summary["metrics"][label] = totals
    write_json(output / f"{stage}_summary.json", summary)
    write_json(output / "jobs.json", jobs)
    return summary
