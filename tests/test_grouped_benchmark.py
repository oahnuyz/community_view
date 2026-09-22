import importlib.util
import json
from pathlib import Path

import pytest


def test_ask_failure_still_runs_judge(tmp_path, monkeypatch, benchmark_settings):
    spec = importlib.util.spec_from_file_location(
        "grouped", Path(__file__).resolve().parents[1] / "scripts/run_grouped_benchmark.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.BenchmarkConfig, "load", lambda _: benchmark_settings)
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["run", "--config", "config.yaml", "--settings", "test.yaml", "--stages", "ask", "judge"],
    )
    stages = []

    def run(command):
        stages.append(command[-1])
        return 1 if command[-1] == "ask" else 0

    monkeypatch.setattr(module.subprocess, "call", run)
    assert module.main() == 1
    assert stages == ["ask", "judge"]
    status = json.loads((benchmark_settings.output_dir / "run_status.json").read_text())
    assert status["status"] == "failed"
    assert status["stage_exit_codes"] == {"ask": 1, "judge": 0}


@pytest.mark.parametrize("cluster_code", [0, 1])
def test_cluster_only_rebuild_and_failure_gate(monkeypatch, benchmark_settings, cluster_code):
    spec = importlib.util.spec_from_file_location(
        "grouped", Path(__file__).resolve().parents[1] / "scripts/run_grouped_benchmark.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.BenchmarkConfig, "load", lambda _: benchmark_settings)
    monkeypatch.setattr(
        module.sys,
        "argv",
        [
            "run",
            "--config",
            "config.yaml",
            "--settings",
            "test.yaml",
            "--stages",
            "cluster",
            "ask",
            "judge",
        ],
    )
    stages = []

    def run(command):
        stages.append(command[-1])
        return cluster_code if command[-1] == "cluster" else 0

    monkeypatch.setattr(module.subprocess, "call", run)
    assert module.main() == cluster_code
    assert stages == (["cluster"] if cluster_code else ["cluster", "ask", "judge"])
    status = json.loads((benchmark_settings.output_dir / "run_status.json").read_text())
    assert status["stage_exit_codes"] == {
        stage: cluster_code if stage == "cluster" else 0 for stage in stages
    }
