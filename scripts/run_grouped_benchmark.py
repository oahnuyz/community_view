"""Run the full benchmark once, then summarize existing QA results by category."""

import argparse
import os
import subprocess
import sys
from datetime import datetime

from community_wiki.experiments.config import BenchmarkConfig
from community_wiki.experiments.dataset import load_dataset, write_json
from community_wiki.experiments.results import load_results, summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--settings", required=True)
    parser.add_argument(
        "--stages", nargs="+", choices=["all", "cluster", "ask", "judge"], default=["all"]
    )
    args = parser.parse_args()
    settings = BenchmarkConfig.load(args.settings)
    output = settings.output_dir
    output.mkdir(parents=True, exist_ok=True)
    status = {
        "pid": os.getpid(),
        "started_at": datetime.now().astimezone().isoformat(),
        "status": "running",
    }
    write_json(output / "run_status.json", status)
    code = 1
    try:
        codes = []
        for stage in args.stages:
            status["stage"] = stage
            write_json(output / "run_status.json", status)
            codes.append(
                subprocess.call(
                    [
                        sys.executable,
                        "-m",
                        "community_wiki.cli",
                        "--config",
                        args.config,
                        "benchmark",
                        "--settings",
                        args.settings,
                        "--stage",
                        stage,
                    ]
                )
            )
            if stage == "cluster" and codes[-1]:
                break
        code = int(any(codes))
        status["stage_exit_codes"] = dict(zip(args.stages[: len(codes)], codes, strict=True))
        if (output / "results.jsonl").exists():
            dataset = load_dataset(settings)
            latest = load_results(settings)
            if "all" in args.stages or "judge" in args.stages:
                incomplete = sum(
                    latest.get((mode, q["id"]), {}).get("status") != "complete"
                    or latest.get((mode, q["id"]), {}).get("evaluation", {}).get("status")
                    != "complete"
                    for mode in settings.modes
                    for q in dataset.questions
                )
                status["incomplete_qa_or_judge"] = incomplete
                code = int(bool(code or incomplete))
            categories = list(
                dict.fromkeys(q.get("category", "uncategorized") for q in dataset.questions)
            )
            grouped = {
                category: summarize(
                    [
                        q
                        for q in dataset.questions
                        if q.get("category", "uncategorized") == category
                    ],
                    settings.modes,
                    latest,
                )
                for category in categories
            }
            write_json(output / "summary_by_category.json", grouped)
    except BaseException as exc:
        code = 1
        status["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        status.update(
            exit_code=code,
            status="complete" if code == 0 else "failed",
            finished_at=datetime.now().astimezone().isoformat(),
        )
        write_json(output / "run_status.json", status)
        (output / "exit_code.txt").write_text(f"{code}\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
