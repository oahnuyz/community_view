"""Execute configured full experiments sequentially in one detached queue."""

import argparse
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

from community_wiki.experiments.config import BenchmarkConfig
from community_wiki.experiments.dataset import write_json


def now():
    return datetime.now().astimezone().isoformat()


def run_queue(path):
    path = Path(path).resolve()
    spec = yaml.safe_load(path.read_text())
    required = {"config", "output_dir", "continue_on_error", "experiments"}
    if not required <= set(spec) or set(spec) - required - {"stages"}:
        raise ValueError("Unexpected queue configuration fields")
    stages = spec.get("stages", ["all"])
    if stages not in (["all"], ["cluster", "ask", "judge"], ["ask", "judge"], ["ask"], ["judge"]):
        raise ValueError("Queue stages must be all, cluster/ask/judge, ask/judge, ask, or judge")
    if not isinstance(spec["continue_on_error"], bool) or not spec["experiments"]:
        raise ValueError("Queue requires a boolean continue_on_error and experiment entries")
    root = path.parent
    config = (root / spec["config"]).resolve()
    entries = [(root / p).resolve() for p in spec["experiments"]]
    settings = [BenchmarkConfig.load(p) for p in entries]
    if len({s.output_dir for s in settings}) != len(settings):
        raise ValueError("Experiments must have distinct output directories")
    output = (root / spec["output_dir"]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".queue.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = {
            "pid": os.getpid(),
            "started_at": now(),
            "status": "running",
            "jobs": [
                {"settings": str(p), "output_dir": str(s.output_dir), "status": "pending"}
                for p, s in zip(entries, settings, strict=True)
            ],
        }
        write_json(output / "queue_status.json", state)
        code = 1
        try:
            for job, entry, setting in zip(state["jobs"], entries, settings, strict=True):
                job.update(status="running", started_at=now())
                write_json(output / "queue_status.json", state)
                setting.output_dir.mkdir(parents=True, exist_ok=True)
                command = [
                    sys.executable,
                    str(Path(__file__).with_name("run_grouped_benchmark.py")),
                    "--config",
                    str(config),
                    "--settings",
                    str(entry),
                    "--stages",
                    *stages,
                ]
                print(f"{now()} Starting {entry.name}", flush=True)
                try:
                    (setting.output_dir / "exit_code.txt").unlink(missing_ok=True)
                    manifest_path = root / "data/deployed_code_manifest.json"
                    manifest = (
                        json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
                    )
                    if manifest:
                        write_json(setting.output_dir / "source_manifest.json", manifest)
                    with (setting.output_dir / "console.log").open("ab", buffering=0) as log:
                        process = subprocess.Popen(
                            command,
                            cwd=root,
                            stdin=subprocess.DEVNULL,
                            stdout=log,
                            stderr=subprocess.STDOUT,
                        )
                        job["pid"] = process.pid
                        write_json(
                            setting.output_dir / "process.json",
                            {
                                "pid": process.pid,
                                "queue_pid": os.getpid(),
                                "started_at": job["started_at"],
                                "command": command,
                                "git_commit": manifest.get("commit"),
                                "uncommitted_changes": manifest.get("uncommitted_changes", []),
                            },
                        )
                        write_json(output / "queue_status.json", state)
                        job["exit_code"] = process.wait()
                except Exception as exc:
                    job.update(exit_code=1, error=f"{type(exc).__name__}: {exc}")
                job.update(
                    status="complete" if job["exit_code"] == 0 else "failed", finished_at=now()
                )
                write_json(output / "queue_status.json", state)
                print(f"{now()} Finished {entry.name}: exit_code={job['exit_code']}", flush=True)
                if job["exit_code"] and not spec["continue_on_error"]:
                    for remaining in state["jobs"]:
                        if remaining["status"] == "pending":
                            remaining["status"] = "skipped"
                    break
            code = int(any(job["status"] != "complete" for job in state["jobs"]))
        finally:
            state.update(
                status="complete" if code == 0 else "failed", exit_code=code, finished_at=now()
            )
            write_json(output / "queue_status.json", state)
            (output / "exit_code.txt").write_text(f"{code}\n")
        return code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", required=True)
    raise SystemExit(run_queue(parser.parse_args().settings))
