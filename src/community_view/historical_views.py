"""Filter mapped original questions and publish their exact historical answers."""

import asyncio
import json
import logging
import time

from .experiments.dataset import write_json
from .ingest import embedding_signature
from .knowledge import planning_context
from .knowledge_store import fingerprint, load_job, replace_views, save_job
from .metrics import measure
from .retrieval import Retriever

log = logging.getLogger(__name__)


def load_history(store, graph_key, results_path, leaves):
    """Join one explicit experiment's results to the exact mapping and completed run."""
    rows = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError("Historical results are empty")
    seen_ids, seen_runs, histories = set(), set(), {}
    for index, row in enumerate(rows, 1):
        qid, run_id = row["id"], row["run_id"]
        if qid in seen_ids or run_id in seen_runs:
            raise ValueError("Historical results must contain one attempt per question ID")
        seen_ids.add(qid)
        seen_runs.add(run_id)
        if row["mode"] != "community" or row["status"] != "complete":
            raise ValueError(f"Historical QA is not a successful community answer: {qid}")
        if not isinstance(row["answer"], str) or not row["answer"].strip():
            raise ValueError(f"Historical answer is missing: {qid}")
        mapping = store.db.execute(
            "SELECT q.graph_key,q.question,q.community_ids,q.status,s.question_id "
            "FROM question_communities q LEFT JOIN question_sources s USING(run_id) "
            "WHERE q.run_id=?",
            (run_id,),
        ).fetchone()
        if mapping is None or (mapping[0], mapping[1], mapping[3], mapping[4]) != (
            graph_key,
            row["question"],
            "complete",
            qid,
        ):
            raise ValueError(f"Historical mapping does not match this graph/question/run: {qid}")
        run = store.db.execute(
            "SELECT mode,status,messages FROM runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if run is None or run[:2] != ("community", "complete"):
            raise ValueError(f"Completed source run is unavailable: {qid}")
        messages = json.loads(run[2])
        final = messages[-1] if messages else {}
        if (
            final.get("role") != "assistant"
            or final.get("tool_calls")
            or final.get("content") != row["answer"]
        ):
            raise ValueError(f"Historical answer differs from the mapped run: {qid}")
        community_ids = json.loads(mapping[2])
        if not set(community_ids) <= leaves:
            raise ValueError(f"Historical mapping contains missing or non-leaf communities: {qid}")
        item = {
            "source_question_id": f"H{index:04d}",
            "question": row["question"],
            "answer": row["answer"],
            "run_id": run_id,
            "external_question_id": qid,
        }
        for cid in dict.fromkeys(community_ids):
            histories.setdefault(cid, []).append(item)
    return histories, len(rows)


def validate_filter(value, allowed):
    if not isinstance(value, dict) or set(value) != {"keep_question_ids"}:
        raise ValueError("Expected exactly keep_question_ids")
    ids = value["keep_question_ids"]
    if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids):
        raise ValueError("keep_question_ids must be a string list")
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate keep_question_ids")
    unknown = set(ids) - allowed
    if unknown:
        raise ValueError(f"Unknown keep_question_ids: {sorted(unknown)}")


async def build_filtered_views(config, store, client):
    if config.knowledge.history_results is None:
        raise ValueError("Set knowledge.history_results to one experiment's results.jsonl")
    retriever = Retriever(config, store, client, "community")
    leaves = {c.community_id: c for c in retriever.communities.values() if c.is_leaf}
    histories, source_count = load_history(
        store, retriever.graph_key, config.knowledge.history_results, set(leaves)
    )
    if not histories:
        raise ValueError("The selected historical experiment has no leaf-community mappings")
    prompt = config.knowledge.filter_prompt.read_text(encoding="utf-8")
    workload = fingerprint(histories)
    shared = {
        "format": "filtered_historical_answers_v1",
        "graph": retriever.graph_key,
        "workload": workload,
        "prompt": prompt,
        "model": config.model.model_dump(),
        "embedding": config.embedding.model_dump(),
        "validation_retries": config.knowledge.validation_retries,
    }
    output = config.storage.database.parent / "knowledge"
    output.mkdir(parents=True, exist_ok=True)
    slots = asyncio.Semaphore(config.knowledge.concurrency)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"keep_question_ids": {"type": "array", "items": {"type": "string"}}},
        "required": ["keep_question_ids"],
    }

    async def one(identity, questions):
        signature = fingerprint({**shared, "community_id": identity, "questions": questions})
        job = load_job(store, signature, identity) or {
            "signature": signature,
            "community_id": identity,
            "graph_key": retriever.graph_key,
            "method": "history_answers",
            "question_count": len(questions),
            "status": "pending",
            "metrics": {},
            "answers": [],
        }
        if job["status"] in {"complete", "skipped"}:
            return job

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

        async with slots:
            try:
                if "selection" not in job:
                    job["selection"] = await measured(
                        "filter",
                        lambda: client.json_completion(
                            prompt,
                            {
                                **planning_context(retriever, leaves[identity]),
                                "historical_questions": [
                                    {
                                        "source_question_id": q["source_question_id"],
                                        "question": q["question"],
                                    }
                                    for q in questions
                                ],
                            },
                            schema,
                            config.knowledge.validation_retries,
                            lambda v: validate_filter(
                                v, {q["source_question_id"] for q in questions}
                            ),
                            "knowledge_filter",
                        ),
                    )
                    save_job(store, job)
                kept = set(job["selection"]["keep_question_ids"])
                selected = [q for q in questions if q["source_question_id"] in kept]
                job["answers"] = [
                    {
                        "question_id": f"{identity}-Q{i:04d}",
                        "question": q["question"],
                        "answer": q["answer"],
                        "run_id": q["run_id"],
                        "source_questions": [
                            {
                                "source_question_id": q["source_question_id"],
                                "question": q["question"],
                                "run_ids": [q["run_id"]],
                                "external_question_ids": [q["external_question_id"]],
                            }
                        ],
                    }
                    for i, q in enumerate(selected, 1)
                ]
                if "vectors" not in job:
                    vectors = (
                        await measured(
                            "embedding", lambda: client.embed([q["question"] for q in selected])
                        )
                        if selected
                        else []
                    )
                    job["vectors"] = {
                        a["question_id"]: v.tolist()
                        for a, v in zip(job["answers"], vectors, strict=True)
                    }
                job.pop("error", None)
                job["status"] = "complete" if selected else "skipped"
                log.info(
                    "Historical view prepared: community=%s kept=%s/%s",
                    identity,
                    len(selected),
                    len(questions),
                )
            except Exception as exc:
                job.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                log.exception("Historical view failed: community=%s", identity)
            finally:
                save_job(store, job)
        return job

    started = time.monotonic()
    jobs = await asyncio.gather(*(one(cid, qs) for cid, qs in sorted(histories.items())))
    published = not any(job["status"] == "failed" for job in jobs)
    if published:
        replace_views(
            store,
            retriever.graph_key,
            [
                (
                    job,
                    {
                        "community_id": job["community_id"],
                        "name": leaves[job["community_id"]].name,
                        "method": "history_answers",
                        "workload_signature": workload,
                        "embedding_signature": embedding_signature(config),
                        "entries": job["answers"],
                        "vectors": job["vectors"],
                    },
                )
                for job in jobs
            ],
        )
    else:
        log.warning("Historical views not published: incomplete workload; previous views retained")
    summary = {
        "published": published,
        "stage": "filter",
        "method": "history_answers",
        "graph_key": retriever.graph_key,
        "source_results": str(config.knowledge.history_results),
        "workload_signature": workload,
        "source_qa_count": source_count,
        "leaf_count": len(leaves),
        "mapped_communities": len(jobs),
        "unmapped_communities": len(leaves) - len(jobs),
        "wall_seconds": time.monotonic() - started,
        "candidate_pairs": sum(len(qs) for qs in histories.values()),
        "retained_pairs": sum(
            len(j["answers"]) for j in jobs if j["status"] in {"complete", "skipped"}
        ),
        "metrics": {},
    }
    summary.update(
        {s: sum(j["status"] == s for j in jobs) for s in ["complete", "skipped", "failed"]}
    )
    for label in ["filter", "embedding"]:
        totals = {}
        for job in jobs:
            for key, value in job["metrics"].get(label, {}).items():
                totals[key] = totals.get(key, 0) + value
        summary["metrics"][label] = totals
    write_json(output / "filter_summary.json", summary)
    write_json(output / "filter_jobs.json", jobs)
    return summary
