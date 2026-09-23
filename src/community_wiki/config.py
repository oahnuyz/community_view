"""Typed external configuration; no hidden runtime tuning constants."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StorageConfig(Section):
    database: Path
    log_file: Path
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class ModelConfig(Section):
    base_url: str
    chat_model: str
    timeout_seconds: float = Field(gt=0)
    concurrency: int = Field(gt=0)
    retries: int = Field(ge=0, le=2)
    retry_delay_seconds: float = Field(ge=0)
    temperature: float = Field(ge=0, le=2)
    structured_output: Literal["json_schema", "json_object"]
    extra_body: dict[str, Any]

    @model_validator(mode="after")
    def reserved_fields(self):
        reserved = {
            "model",
            "messages",
            "tools",
            "tool_choice",
            "response_format",
            "max_tokens",
            "max_completion_tokens",
            "temperature",
            "stream",
        }
        if reserved.intersection(self.extra_body):
            raise ValueError("model.extra_body cannot override protocol or configured fields")
        return self


class EmbeddingConfig(Section):
    base_url: str
    model: str
    api_format: Literal["openai", "multimodal"] = "openai"
    dimensions: int | None = Field(gt=0)
    batch_size: int = Field(gt=0)
    concurrency: int = Field(gt=0)


class PDFConfig(Section):
    strategy: Literal["auto", "pdfplumber"] = "auto"
    max_heading_level: int = Field(default=4, ge=1, le=4)
    heading_min_size_ratio: float = Field(default=1.1, gt=1)
    heading_max_chars: int = Field(default=160, gt=0)
    extract_tables: bool = True
    table_settings: dict[str, Any] = Field(default_factory=dict)


class TextConfig(Section):
    encoding: str
    extensions: list[str]
    chunk_tokens: int = Field(gt=0)
    chunk_overlap_tokens: int = Field(ge=0)
    pdf: PDFConfig = Field(default_factory=PDFConfig)

    @model_validator(mode="after")
    def overlap(self):
        if self.chunk_overlap_tokens >= self.chunk_tokens:
            raise ValueError("chunk_overlap_tokens must be smaller than chunk_tokens")
        return self


class OverviewConfig(Section):
    concurrency: int = Field(gt=0)
    fragment_tokens: int = Field(gt=0)
    title_max_chars: int = Field(gt=0)
    summary_max_chars: int = Field(gt=0)
    summary_target_min_chars: int = Field(default=300, gt=0)
    summary_validation_max_chars: int = Field(default=450, gt=0)
    keyword_count: int = Field(gt=0)
    keyword_max_chars: int = Field(gt=0)
    stage_max_chars: int = Field(gt=0)
    validation_retries: int = Field(ge=0, le=2)

    @model_validator(mode="after")
    def summary_lengths(self):
        if (
            not self.summary_target_min_chars
            <= self.summary_max_chars
            <= self.summary_validation_max_chars
        ):
            raise ValueError("Summary target range must fit within the local validation limit")
        return self


class GraphConfig(Section):
    mode: Literal["vector", "keyword", "hybrid"]
    neighbor_k: int = Field(gt=0)
    min_weight: float = Field(ge=0, le=1)
    vector_weight: float = Field(ge=0, le=1)


class CommunityConfig(Section):
    max_documents: int = Field(gt=0)
    llm_split_fallback: bool = False
    cluster_workers: int = Field(gt=0)
    resolution: float = Field(gt=0)
    seed: int = Field(ge=0, le=2147483647)
    iterations: int = Field(ge=-1)
    description_concurrency: int = Field(gt=0)
    name_max_chars: int = Field(gt=0)
    overview_max_chars: int = Field(gt=0)
    overview_target_min_chars: int = Field(default=150, gt=0)
    overview_validation_max_chars: int = Field(default=250, gt=0)
    validation_retries: int = Field(ge=0, le=2)

    @model_validator(mode="after")
    def iterations_valid(self):
        if self.iterations == 0:
            raise ValueError("iterations must be -1 or positive")
        if (
            not self.overview_target_min_chars
            <= self.overview_max_chars
            <= self.overview_validation_max_chars
        ):
            raise ValueError(
                "Community overview target range must fit within the local validation limit"
            )
        return self


RetrievalMode = Literal["naive", "community", "community_guide"]
COMMUNITY_MODES = ("community", "community_guide")


class RetrievalConfig(Section):
    mode: RetrievalMode
    search_mode: Literal["vector", "keyword", "hybrid"]
    chunk_k: int = Field(gt=0)
    doc_k: int = Field(gt=0)
    fusion_candidates: int = Field(gt=0)
    rrf_constant: int = Field(gt=0)
    min_vector_similarity: float = Field(ge=-1, le=1)
    bm25_k1: float = Field(gt=0)
    bm25_b: float = Field(ge=0, le=1)
    bm25_epsilon: float = Field(ge=0)
    read_chunk_limit: int = Field(gt=0)


class AgentConfig(Section):
    max_rounds: int = Field(gt=0)
    tool_concurrency: int = Field(gt=0)
    max_identical_tool_calls: int = Field(gt=0)


class PromptConfig(Section):
    document: Path
    community: Path
    agent: Path
    question: Path
    judge: Path
    community_guide: Path = Path("prompts/community_guide.txt")
    community_split: Path = Path("prompts/community_split.txt")


class Config(Section):
    keys_file: Path
    storage: StorageConfig
    model: ModelConfig
    embedding: EmbeddingConfig
    text: TextConfig
    overview: OverviewConfig
    graph: GraphConfig
    community: CommunityConfig
    retrieval: RetrievalConfig
    agent: AgentConfig
    prompts: PromptConfig

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        path = Path(path).resolve()
        config = cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        for section, names in (
            (config.storage, ("database", "log_file")),
            (
                config.prompts,
                (
                    "document",
                    "community",
                    "agent",
                    "question",
                    "judge",
                    "community_guide",
                    "community_split",
                ),
            ),
        ):
            for name in names:
                setattr(section, name, (path.parent / getattr(section, name)).resolve())
        config.keys_file = (path.parent / config.keys_file).resolve()
        return config
