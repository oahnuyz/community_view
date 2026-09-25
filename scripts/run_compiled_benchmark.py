"""Detached/resumable mapping QA -> planning -> compilation -> enriched QA -> judge."""

import argparse
import fcntl
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

from community_wiki.config import Config
from community_wiki.experiments.config import BenchmarkConfig
from community_wiki.experiments.dataset import write_json
from community_wiki.experiments.reuse import clone_index


def verify_view_snapshot(source, destination):
    """Do not silently reuse an enriched index after its compiled answers changed."""
    with (
        sqlite3.connect(f"file:{source}?mode=ro", uri=True) as current,
        sqlite3.connect(f"file:{destination}?mode=ro", uri=True) as frozen,
    ):
        for table, order in [
            ("knowledge_views", "graph_key,community_id"),
            ("knowledge_answers", "graph_key,question_id"),
        ]:
            sql = f"SELECT * FROM {table} ORDER BY {order}"
            if current.execute(sql).fetchall() != frozen.execute(sql).fetchall():
                raise ValueError("Compiled views changed; use a fresh final database/output_dir")


def run_pipeline(path):
    path = Path(path).resolve()
    spec = yaml.safe_load(path.read_text())
    fields = {"mapping_config", "mapping_settings", "compiled_config", "compiled_settings"}
    if set(spec) != fields:
        raise ValueError(f"Expected pipeline fields: {sorted(fields)}")
    paths = {k: (path.parent / v).resolve() for k, v in spec.items()}
    mapping = BenchmarkConfig.load(paths["mapping_settings"])
    final = BenchmarkConfig.load(paths["compiled_settings"])
    before = Config.load(paths["mapping_config"])
    after = Config.load(paths["compiled_config"])
    if before.storage.database != mapping.database:
        raise ValueError("Mapping config and settings must point to the same knowledge database")
    if mapping.database == final.database or mapping.output_dir == final.output_dir:
        raise ValueError("Mapping and enriched QA require independent databases/output directories")
    if not before.knowledge.record_questions or before.knowledge.use_compiled:
        raise ValueError("Mapping QA must record questions without compiled knowledge")
    if not after.knowledge.use_compiled:
        raise ValueError("Final QA must enable compiled knowledge")
    if (mapping.dataset_dir, mapping.start, mapping.count, mapping.modes) != (
        final.dataset_dir,
        final.start,
        final.count,
        final.modes,
    ):
        raise ValueError("Mapping and final QA must select the same questions and modes")
    path.parent.mkdir(parents=True, exist_ok=True)
    with (path.parent / ".pipeline.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = {
            "pid": os.getpid(),
            "status": "running",
            "started_at": datetime.now().astimezone().isoformat(),
            "steps": [],
        }

        def step(name, command, *, partial_summary=None):
            state["stage"] = name
            write_json(path.parent / "pipeline_status.json", state)
            print(f"Starting {name}", flush=True)
            code = subprocess.call(command)
            entry = {"stage": name, "exit_code": code}
            state["steps"].append(entry)
            if code and partial_summary is not None and partial_summary.exists():
                summary = json.loads(partial_summary.read_text())
                if (
                    summary["failed"]
                    and sum(summary.get(k, 0) for k in ["failed", "complete", "planned", "skipped"])
                    == summary["mapped_communities"]
                ):
                    entry["partial_knowledge_failures"] = summary["failed"]
                    print(
                        f"{name}: {summary['failed']} communities failed; unpublished answers remain unavailable and QA can search original chunks",
                        flush=True,
                    )
                    return
            if code:
                raise RuntimeError(f"{name} failed with exit code {code}")

        grouped = str(Path(__file__).with_name("run_grouped_benchmark.py"))
        try:
            step(
                "mapping_ask",
                [
                    sys.executable,
                    grouped,
                    "--config",
                    str(paths["mapping_config"]),
                    "--settings",
                    str(paths["mapping_settings"]),
                    "--stages",
                    "ask",
                ],
            )
            # Freeze this workload: only original successful QA question text reaches planning.
            for phase in ["plan", "compile"]:
                step(
                    phase,
                    [
                        sys.executable,
                        "-m",
                        "community_wiki.cli",
                        "--config",
                        str(paths["mapping_config"]),
                        "knowledge",
                        "--stage",
                        phase,
                    ],
                    partial_summary=mapping.database.parent / "knowledge" / f"{phase}_summary.json",
                )
            if not final.database.exists():
                clone_index(
                    mapping.database,
                    mapping.output_dir / "execution.json",
                    mapping.dataset_dir,
                    final,
                    after,
                )
                shutil.copy2(
                    mapping.output_dir / "summary.json", final.output_dir / "mapping_summary.json"
                )
            else:
                verify_view_snapshot(mapping.database, final.database)
            # predict() also fingerprints published knowledge, preventing resume under changed notes.
            step(
                "compiled_ask_and_judge",
                [
                    sys.executable,
                    grouped,
                    "--config",
                    str(paths["compiled_config"]),
                    "--settings",
                    str(paths["compiled_settings"]),
                    "--stages",
                    "ask",
                    "judge",
                ],
            )
            state["status"] = "complete"
        except Exception as exc:
            state.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            print(state["error"], flush=True)
        finally:
            state["finished_at"] = datetime.now().astimezone().isoformat()
            write_json(path.parent / "pipeline_status.json", state)
        return int(state["status"] != "complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", required=True)
    raise SystemExit(run_pipeline(parser.parse_args().settings))
