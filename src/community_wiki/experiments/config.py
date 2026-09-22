"""Shared settings for every prepared-format dataset."""

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from ..config import RetrievalMode, Section


class BenchmarkConfig(Section):
    dataset_dir: Path
    output_dir: Path
    database: Path
    log_file: Path
    start: int = Field(ge=0)
    count: int | None = Field(gt=0)
    modes: list[RetrievalMode] = Field(min_length=1)
    concurrency: int = Field(gt=0)

    @model_validator(mode="after")
    def distinct_modes(self):
        if len(set(self.modes)) != len(self.modes):
            raise ValueError("Benchmark modes must be unique")
        return self

    @classmethod
    def load(cls, path):
        path = Path(path).resolve()
        config = cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        for key in ("dataset_dir", "output_dir", "database", "log_file"):
            setattr(config, key, (path.parent / getattr(config, key)).resolve())
        return config
