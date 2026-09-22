import importlib.util
import json
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize("stages", [["all"], ["ask", "judge"], ["cluster", "ask", "judge"]])
@pytest.mark.parametrize(
    "continue_on_error,expected", [(True, ["failed", "complete"]), (False, ["failed", "skipped"])]
)
def test_queue_waits_for_each_job_and_records_failures(
    tmp_path, monkeypatch, continue_on_error, expected, stages
):
    spec = importlib.util.spec_from_file_location(
        "benchmark_queue", Path(__file__).resolve().parents[1] / "scripts/run_benchmark_queue.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    files = []
    for i in range(2):
        p = tmp_path / f"experiment{i}.yaml"
        p.write_text(
            yaml.safe_dump(
                {
                    "dataset_dir": "dataset",
                    "output_dir": f"run{i}",
                    "database": f"run{i}/db.sqlite3",
                    "log_file": f"run{i}/run.log",
                    "start": 0,
                    "count": 1,
                    "modes": ["naive"],
                    "concurrency": 5,
                }
            )
        )
        files.append(p.name)
    queue = tmp_path / "queue.yaml"
    queue.write_text(
        yaml.safe_dump(
            {
                "config": "config.yaml",
                "output_dir": "queue",
                "experiments": files,
                "continue_on_error": continue_on_error,
                "stages": stages,
            }
        )
    )
    events = []

    class Process:
        def __init__(self, command, **kwargs):
            assert command[command.index("--stages") + 1 :] == stages
            self.index = len(events) // 2
            assert len(events) % 2 == 0  # No next launch before previous wait completed.
            assert kwargs["stdin"] == module.subprocess.DEVNULL
            self.pid = 100 + self.index
            events.append("start")

        def wait(self):
            events.append("wait")
            return 1 if self.index == 0 else 0

    monkeypatch.setattr(module.subprocess, "Popen", Process)
    assert module.run_queue(queue) == 1
    state = json.loads((tmp_path / "queue/queue_status.json").read_text())
    assert [j["status"] for j in state["jobs"]] == expected
    assert state["status"] == "failed" and state["exit_code"] == 1
    assert events == ["start", "wait"] * (2 if continue_on_error else 1)
