"""Command-line entry point; no database daemon or web service required."""

import argparse
import asyncio
import json
import logging
from dataclasses import asdict
from typing import get_args

from .agent import Agent
from .communities import cluster
from .config import Config, RetrievalMode
from .experiments import BenchmarkConfig, run_benchmark
from .ingest import ingest
from .llm import ModelClient
from .models import QuestionState
from .retrieval import Retriever
from .store import Store
from .text import TextProcessor


def parser():
    p = argparse.ArgumentParser(description="Document community RAG")
    p.add_argument("--config", default="config.yaml")
    commands = p.add_subparsers(dest="command", required=True)
    benchmark = commands.add_parser(
        "benchmark", help="Run a prepared QA dataset with resume support"
    )
    benchmark.add_argument("--settings", required=True, help="Dataset experiment configuration")
    benchmark.add_argument(
        "--stage",
        choices=["prepare", "ingest", "cluster", "index", "ask", "run", "judge", "all"],
        default="prepare",
    )
    commands.add_parser("config-check", help="Validate configuration without contacting models")
    for name in ("ingest", "build"):
        child = commands.add_parser(name)
        child.add_argument("paths", nargs="+")
    commands.add_parser("cluster", help="Rebuild and atomically publish all communities")
    for name in ("ask", "search"):
        child = commands.add_parser(name)
        child.add_argument("query")
        child.add_argument("--mode", choices=get_args(RetrievalMode))
        child.add_argument(
            "--doc-ids",
            nargs="+",
            help="Restrict chunks to these exact document IDs; community expansion is unrestricted",
        )
        if name == "search":
            child.add_argument("--search-mode", choices=["vector", "keyword", "hybrid"])
    inspect = commands.add_parser("inspect")
    inspect.add_argument(
        "kind", choices=["stats", "documents", "communities", "edges", "links", "run"]
    )
    inspect.add_argument("--run-id")
    return p


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


async def run(args):
    config = Config.load(args.config)
    if args.command == "benchmark":
        result = await run_benchmark(config, BenchmarkConfig.load(args.settings), args.stage)
        emit(result)
        return int(
            any(
                row["failed"]
                or row.get("evaluation", {}).get("failed", 0)
                or (
                    args.stage in {"judge", "all"}
                    and (row["evaluation"]["skipped"] or row["evaluation"]["pending"])
                )
                for row in result.get("modes", {}).values()
            )
        )
    if args.command == "config-check":
        emit({"valid": True, "database": str(config.storage.database)})
        return 0
    config.storage.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=config.storage.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(config.storage.log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    store = Store(config.storage.database)
    client = None
    try:
        if args.command == "inspect":
            if args.kind == "stats":
                emit(
                    {
                        "documents": len(store.documents()),
                        "chunks": len(store.chunks()),
                        "edges": len(store.edges()),
                        "communities": len(store.communities()),
                        "revision": store.revision,
                        "graph_revision": store.meta("graph_revision"),
                    }
                )
            elif args.kind == "documents":
                emit(
                    [
                        {"doc_id": d.doc_id, "source": d.source, **d.overview.model_dump()}
                        for d in store.documents()
                    ]
                )
            elif args.kind == "run":
                row = store.db.execute(
                    "SELECT status,messages FROM runs WHERE run_id=?", (args.run_id,)
                ).fetchone()
                if row is None:
                    raise ValueError("Unknown run ID; pass --run-id")
                emit({"status": row[0], "messages": json.loads(row[1])})
            elif args.kind == "links":
                emit(store.links())
            else:
                emit([asdict(item) for item in getattr(store, args.kind)()])
            return 0
        text = TextProcessor(
            config.text.encoding, config.storage.database.parent / "tokenizer_cache"
        )
        client = ModelClient(config, store, text)
        if args.command in ("ingest", "build"):
            result = await ingest(args.paths, config, store, client, text)
            emit(asdict(result))
            if result.errors:
                return 1
            if args.command == "ingest":
                return 0
        if args.command in ("cluster", "build"):
            emit(await cluster(config, store, client))
            return 0
        retriever = Retriever(config, store, client, args.mode)
        if args.command == "search":
            emit(
                await retriever.search(
                    args.query, QuestionState(), doc_ids=args.doc_ids, search_mode=args.search_mode
                )
            )
        elif args.command == "ask":
            emit(
                asdict(
                    await Agent(config, store, client, retriever).ask(
                        args.query, doc_ids=args.doc_ids
                    )
                )
            )
        return 0
    finally:
        if client:
            await client.close()
        store.close()


def main():
    try:
        raise SystemExit(asyncio.run(run(parser().parse_args())))
    except (Exception, KeyboardInterrupt) as exc:
        logging.getLogger(__name__).error("%s: %s", type(exc).__name__, exc)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
