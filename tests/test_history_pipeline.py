import importlib.util
import json
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize("filter_fails", [False, True])
def test_history_pipeline_order_relative_paths_and_failure_gate(
    tmp_path, monkeypatch, config, benchmark_settings, filter_fails
):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "history_pipeline", scripts / "run_history_view_benchmark.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mapping = benchmark_settings.model_copy(deep=True)
    mapping.modes = ["community"]
    mapping.output_dir = tmp_path / "mapping"
    mapping.database = tmp_path / "indexes/mapping.sqlite3"
    final = mapping.model_copy(deep=True)
    final.output_dir = tmp_path / "view"
    final.database = tmp_path / "indexes/view.sqlite3"
    before = config.model_copy(deep=True)
    before.storage.database = mapping.database
    before.knowledge.record_questions = True
    before.knowledge.history_results = mapping.output_dir / "results.jsonl"
    after = before.model_copy(deep=True)
    after.storage.database = final.database
    after.knowledge.record_questions = False
    after.knowledge.use_compiled = True
    for directory in [mapping.output_dir, final.output_dir, mapping.database.parent]:
        directory.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        module.Config, "load", lambda p: before if "mapping" in Path(p).name else after
    )
    monkeypatch.setattr(
        module.BenchmarkConfig, "load", lambda p: mapping if "mapping" in Path(p).name else final
    )
    pipeline = tmp_path / "pipeline.yaml"
    pipeline.write_text(
        yaml.safe_dump(
            {
                "mapping_config": "mapping.config.yaml",
                "mapping_settings": "mapping.benchmark.yaml",
                "view_config": "view.config.yaml",
                "view_settings": "view.benchmark.yaml",
                "stage_attempts": 2,
                "stage_retry_delay_seconds": 0,
            }
        )
    )
    summary = {
        "question_count": 1,
        "modes": {"community": {"successful": 1, "evaluation": {"scored": 1}}},
    }
    stages = []

    class Child:
        pid = 123

        def __init__(self, command, **kwargs):
            self.filtering = command[-1] == "knowledge-filter"
            if self.filtering:
                stages.append("filter")
                output = mapping.database.parent / "knowledge"
                output.mkdir(exist_ok=True)
                (output / "filter_summary.json").write_text(
                    json.dumps(
                        {
                            "failed": int(filter_fails),
                            "published": not filter_fails,
                            "complete": int(not filter_fails),
                            "skipped": 0,
                            "mapped_communities": 1,
                        }
                    )
                )
            else:
                settings = Path(command[command.index("--settings") + 1])
                assert settings.parent == tmp_path
                target = mapping if "mapping" in settings.name else final
                stages.append(target.output_dir.name + "_" + command[-1])
                (target.output_dir / "summary.json").write_text(json.dumps(summary))

        def wait(self):
            return int(self.filtering and filter_fails)

    monkeypatch.setattr(module.subprocess, "Popen", Child)
    monkeypatch.setattr(module, "clone_index", lambda *args: stages.append("clone"))
    monkeypatch.setattr(module, "verify_view_snapshot", lambda *args: stages.append("verify"))
    assert module.run(pipeline) == int(filter_fails)
    assert stages == (
        ["mapping_ask", "mapping_judge", "filter", "filter"]
        if filter_fails
        else ["mapping_ask", "mapping_judge", "filter", "clone", "verify", "view_ask", "view_judge"]
    )
    state = json.loads((tmp_path / "pipeline_status.json").read_text())
    assert state["status"] == ("failed" if filter_fails else "complete")
