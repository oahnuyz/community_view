"""One answer/gold/score record per QA and mode, with atomically refreshed summaries."""

from ..store import dumps
from .dataset import read_jsonl, write_json


def load_results(settings):
    return {
        (row["mode"], row["id"]): row for row in read_jsonl(settings.output_dir / "results.jsonl")
    }


def summarize(questions, modes, latest):
    summary = {"question_count": len(questions), "modes": {}}
    for mode in modes:
        rows = [latest[(mode, q["id"])] for q in questions if (mode, q["id"]) in latest]
        count = len(rows)
        scored = [
            r["evaluation"] for r in rows if r.get("evaluation", {}).get("status") == "complete"
        ]
        evaluations = [r["evaluation"] for r in rows if "evaluation" in r]
        accuracy = sum(r["score"] for r in scored) / len(scored) if scored else None
        summary["modes"][mode] = {
            "completed_qa_count": count,
            "successful": sum(row["status"] == "complete" for row in rows),
            "failed": sum(row["status"] == "failed" for row in rows),
            "mean_elapsed_seconds": sum(r["elapsed_seconds"] for r in rows) / count
            if count
            else None,
            "mean_total_tokens": sum(r["total_tokens"] for r in rows) / count if count else None,
            "mean_rounds": sum(r["rounds"] for r in rows) / count if count else None,
            "total_tokens": sum(r["total_tokens"] for r in rows),
            "evaluation": {
                "scored": len(scored),
                "total": len(questions),
                "failed": sum(e["status"] == "failed" for e in evaluations),
                "skipped": sum(e["status"] == "skipped" for e in evaluations),
                "pending": len(questions) - len(evaluations),
                "accuracy": accuracy,
                "normalized_accuracy": accuracy / 4 if accuracy is not None else None,
                "total_tokens": sum(e.get("total_tokens", 0) for e in evaluations),
            },
        }
    return summary


def save_results(dataset, settings, latest):
    modes = list(dict.fromkeys([*settings.modes, *[key[0] for key in latest]]))
    ordered = [
        latest[(mode, q["id"])]
        for mode in modes
        for q in dataset.questions
        if (mode, q["id"]) in latest
    ]
    path = settings.output_dir / "results.jsonl"
    temporary = path.with_suffix(".jsonl.tmp")
    temporary.write_text("".join(dumps(row) + "\n" for row in ordered), encoding="utf-8")
    temporary.replace(path)
    summary = summarize(dataset.questions, modes, latest)
    write_json(settings.output_dir / "summary.json", summary)
    return summary
