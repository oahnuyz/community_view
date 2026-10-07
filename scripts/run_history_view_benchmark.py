"""Run community QA/judge, filter historical answers, then view QA/judge."""

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
from run_compiled_benchmark import verify_view_snapshot

from community_view.config import Config
from community_view.experiments.config import BenchmarkConfig
from community_view.experiments.dataset import write_json
from community_view.experiments.reuse import clone_index


def now():
    return datetime.now().astimezone().isoformat()


def run(path):
    path = Path(path).resolve()
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    fields = {"mapping_config", "view_config", "mapping_settings", "view_settings"}
    optional = {"stage_attempts", "stage_retry_delay_seconds", "code_sha256"}
    if not isinstance(spec, dict) or not fields <= spec.keys() or spec.keys() - fields - optional:
        raise ValueError("Expected mapping_config/settings and view_config/settings")
    for key in fields:
        spec[key] = str((path.parent / spec[key]).resolve())
    spec["code_sha256"] = {
        str((path.parent / file).resolve()): digest
        for file, digest in spec.get("code_sha256", {}).items()
    }
    if type(spec.get("stage_attempts", 3)) is not int or spec.get("stage_attempts", 3) < 1:
        raise ValueError("stage_attempts must be a positive integer")
    if spec.get("stage_retry_delay_seconds", 30) < 0:
        raise ValueError("stage_retry_delay_seconds must be nonnegative")
    root = Path(__file__).resolve().parents[1]
    configs = {k: Config.load(spec[k]) for k in ["mapping_config", "view_config"]}
    settings = {k: BenchmarkConfig.load(spec[k]) for k in ["mapping_settings", "view_settings"]}
    before, after = configs["mapping_config"], configs["view_config"]
    mapping, final = settings["mapping_settings"], settings["view_settings"]
    if (mapping.dataset_dir, mapping.start, mapping.count, mapping.modes) != (
        final.dataset_dir,
        final.start,
        final.count,
        final.modes,
    ):
        raise ValueError("Mapping and view experiments must use the same QA selection")
    if mapping.modes != ["community"]:
        raise ValueError("Historical-answer experiments require modes: [community]")
    if after.knowledge.record_questions:
        raise ValueError("View QA must disable record_questions to keep source history separate")
    if mapping.database == final.database or mapping.output_dir == final.output_dir:
        raise ValueError("Mapping and view results must use separate paths")
    if before.storage.database != mapping.database or after.storage.database != final.database:
        raise ValueError("Configuration and settings databases differ")
    if (
        not before.knowledge.record_questions
        or before.knowledge.use_compiled
        or not after.knowledge.use_compiled
    ):
        raise ValueError("Invalid mapping/view feature flags")
    if before.knowledge.history_results != mapping.output_dir / "results.jsonl":
        raise ValueError("History must come from this pipeline's mapping experiment")
    state = {"pid": os.getpid(), "status": "running", "started_at": now(), "steps": []}
    with (path.parent / ".pipeline.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

        def save():
            write_json(path.parent / "pipeline_status.json", state)

        def step(label, args):
            state["stage"] = label
            entry = {"stage": label, "started_at": now(), "attempts": []}
            state["steps"].append(entry)
            for attempt in range(1, spec.get("stage_attempts", 3) + 1):
                for file, digest in spec.get("code_sha256", {}).items():
                    if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
                        raise ValueError(f"Experiment file changed: {file}")
                with (path.parent / f"{label}_{attempt}.log").open("ab", buffering=0) as log:
                    child = subprocess.Popen(
                        [sys.executable, *args],
                        cwd=root,
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                    state.update(child_pid=child.pid, attempt=attempt)
                    save()
                    code = child.wait()
                entry["attempts"].append({"attempt": attempt, "exit_code": code})
                save()
                if code == 0:
                    entry["finished_at"] = now()
                    return
                if attempt < spec.get("stage_attempts", 3):
                    time.sleep(spec.get("stage_retry_delay_seconds", 30))
            raise RuntimeError(f"{label} failed after bounded retries")

        def qa(stage, prefix):
            return [
                str(root / "scripts/run_grouped_benchmark.py"),
                "--config",
                spec[f"{prefix}_config"],
                "--settings",
                spec[f"{prefix}_settings"],
                "--stages",
                stage,
            ]

        def require_complete(output):
            summary = json.loads((output / "summary.json").read_text())
            if any(
                m["successful"] != summary["question_count"]
                or m["evaluation"]["scored"] != summary["question_count"]
                for m in summary["modes"].values()
            ):
                raise ValueError("QA or evaluation is incomplete")
            return summary

        try:
            save()
            for stage in ["ask", "judge"]:
                step("mapping_" + stage, qa(stage, "mapping"))
            state["mapping_summary"] = require_complete(mapping.output_dir)
            step(
                "filter",
                [
                    "-m",
                    "community_view.cli",
                    "--config",
                    spec["mapping_config"],
                    "knowledge-filter",
                ],
            )
            knowledge = json.loads(
                (mapping.database.parent / "knowledge/filter_summary.json").read_text()
            )
            if (
                not knowledge["published"]
                or knowledge["failed"]
                or knowledge["complete"] + knowledge["skipped"] != knowledge["mapped_communities"]
            ):
                raise ValueError("Filtered views are incomplete")
            state["filter_summary"] = knowledge
            if not final.database.exists():
                clone_index(
                    mapping.database,
                    mapping.output_dir / "execution.json",
                    mapping.dataset_dir,
                    final,
                    after,
                )
            verify_view_snapshot(mapping.database, final.database)
            for stage in ["ask", "judge"]:
                step("view_" + stage, qa(stage, "view"))
            state["view_summary"] = require_complete(final.output_dir)
            state["status"] = "complete"
        except Exception as exc:
            state.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        finally:
            state["finished_at"] = now()
            save()
    return int(state["status"] != "complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, required=True)
    raise SystemExit(run(parser.parse_args().settings.resolve()))
