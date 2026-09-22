"""Concurrent QA execution, compact aggregate metrics, and per-QA agent traces."""

import asyncio
import fcntl
import json
import logging
import time
import uuid
from dataclasses import asdict

from ..agent import Agent
from ..communities import graph_signature
from ..config import COMMUNITY_MODES
from ..credentials import Credentials
from ..ingest import digest
from ..llm import ModelClient
from ..metrics import measure
from ..retrieval import Retriever
from ..store import Store, dumps
from ..text import TextProcessor
from .dataset import load_dataset, prepare, verify_index, write_json
from .indexing import index
from .judge import evaluate
from .results import load_results, save_results, summarize

log = logging.getLogger(__name__)


async def predict(dataset, settings, config, store, client):
    verify_index(dataset, config, store, complete=True)
    if any(mode in COMMUNITY_MODES for mode in settings.modes) and store.meta(
        "graph_signature"
    ) != graph_signature(config):
        raise ValueError("Community settings changed; run benchmark --stage index")
    signature = digest(
        dumps(
            {
                "dataset": dataset.manifest["dataset_signature"],
                "config": config.model_dump(mode="json", exclude={"prompts": {"judge"}}),
                "prompts": {
                    key: path.read_text(encoding="utf-8")
                    for key, path in config.prompts
                    if key != "judge"
                },
                "qa_concurrency": settings.concurrency,
                "revision": store.revision,
                "communities": [asdict(c) for c in store.communities()],
            }
        )
    )
    execution_path = settings.output_dir / "execution.json"
    if execution_path.exists():
        if json.loads(execution_path.read_text())["signature"] != signature:
            raise ValueError(
                "Run configuration/index changed; use a new output_dir for comparable results"
            )
    else:
        write_json(
            execution_path,
            {
                "signature": signature,
                "config": config.model_dump(mode="json", exclude={"prompts": {"judge"}}),
                "dataset_signature": dataset.manifest["dataset_signature"],
                "qa_concurrency": settings.concurrency,
            },
        )
    latest = load_results(settings)
    slots = asyncio.Semaphore(settings.concurrency)
    agents = {
        mode: Agent(config, store, client, Retriever(config, store, client, mode))
        for mode in settings.modes
    }
    traces = settings.output_dir / "traces"
    traces.mkdir(exist_ok=True)

    async def one(mode, question):
        key = (mode, question["id"])
        previous = latest.get(key)
        if previous and previous["status"] == "complete":
            return
        async with slots:
            started = time.monotonic()
            run_id = uuid.uuid4().hex
            result = {
                "id": question["id"],
                "mode": mode,
                "question": question["question"],
                "gold_answers": question.get("gold_answers", []),
                "answer": None,
                "status": "complete",
                "run_id": run_id,
            }
            with measure(f"qa:{mode}:{question['id']}") as totals:
                try:
                    answer = await agents[mode].ask(question["question"], run_id=run_id)
                    result["answer"] = answer.answer
                except Exception as exc:
                    result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                    log.exception("QA failed: mode=%s id=%s", mode, question["id"])
                finally:
                    row = store.db.execute(
                        "SELECT status,messages FROM runs WHERE run_id=?", (run_id,)
                    ).fetchone()
                    trace_path = traces / f"{run_id}.json"
                    write_json(
                        trace_path,
                        {
                            "qa_id": question["id"],
                            "mode": mode,
                            "run_id": run_id,
                            "status": row[0] if row else "failed",
                            "messages": json.loads(row[1]) if row else [],
                        },
                    )
                    result["trace_file"] = str(trace_path.relative_to(settings.output_dir))
            result.update(totals.as_dict())
            result["elapsed_seconds"] = time.monotonic() - started
            # Rerun failed QA: accumulate actual work across attempts, excluding time between runs.
            if previous:
                result["prior_attempts"] = [
                    *previous.get("prior_attempts", []),
                    {k: previous[k] for k in ("run_id", "status", "trace_file")},
                ]
                for field in (*totals.as_dict(), "elapsed_seconds"):
                    result[field] += previous[field]
            latest[key] = result
            save_results(dataset, settings, latest)
            log.info(
                "QA %s mode=%s id=%s elapsed=%.3fs tokens=%s rounds=%s",
                result["status"],
                mode,
                question["id"],
                result["elapsed_seconds"],
                result["total_tokens"],
                result["rounds"],
            )

    await asyncio.gather(*(one(mode, q) for mode in settings.modes for q in dataset.questions))
    save_results(dataset, settings, latest)
    return summarize(dataset.questions, settings.modes, latest)


async def run_benchmark(config, settings, stage):
    aliases = {"run": "ask"}
    stage = aliases.get(stage, stage)
    if stage not in {"prepare", "ingest", "cluster", "index", "ask", "judge", "all"}:
        raise ValueError(f"Unknown experiment stage: {stage}")
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    with (settings.output_dir / ".run.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("This experiment directory is already running") from None
        dataset = load_dataset(settings)
        prepare(settings, dataset)
        if stage == "prepare":
            return dataset.manifest
        credentials = Credentials.load(config.keys_file)
        credentials.key("agent")
        if stage in {"ingest", "index", "ask", "all"}:
            credentials.key("embedding")
        config = config.model_copy(deep=True)
        config.storage.database, config.storage.log_file = settings.database, settings.log_file
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=config.storage.log_level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            handlers=[
                logging.FileHandler(settings.log_file, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        # Judge needs saved answers and the chat service only: no index or embedding initialization.
        if stage == "judge":
            client = ModelClient(config, None, None)
            try:
                return await evaluate(dataset, settings, config, client)
            finally:
                await client.close()
        store, client = Store(settings.database), None
        try:
            verify_index(dataset, config, store, complete=False)
            text = (
                TextProcessor(config.text.encoding, settings.database.parent / "tokenizer_cache")
                if stage != "cluster"
                else None
            )
            client = ModelClient(config, store, text)
            if stage in {"ingest", "cluster", "index", "all"}:
                result = await index(
                    dataset,
                    settings,
                    config,
                    store,
                    client,
                    text,
                    stage="index" if stage == "all" else stage,
                )
                if stage != "all":
                    return result
            result = await predict(dataset, settings, config, store, client)
            if stage == "all":
                result = await evaluate(dataset, settings, config, client)
            return result
        finally:
            if client:
                await client.close()
            store.close()
