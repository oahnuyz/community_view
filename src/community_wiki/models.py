from dataclasses import dataclass, field

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class Overview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    keywords: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)

    def embedding_text(self) -> str:
        return f"Title: {self.title}\nKeywords: {', '.join(self.keywords)}\nSummary: {self.summary}"


@dataclass
class Document:
    doc_id: str
    source: str
    content_hash: str
    signature: str
    overview: Overview
    vector: np.ndarray


@dataclass
class Chunk:
    doc_id: str
    ordinal: int
    text: str
    vector: np.ndarray


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    weight: float
    vector_score: float | None
    keyword_score: float | None


@dataclass
class Community:
    community_id: str
    level: int
    parent_id: str | None
    doc_ids: list[str]
    child_ids: list[str] = field(default_factory=list)
    name: str = ""
    overview: str = ""
    split_status: str = "within_threshold"

    @property
    def is_leaf(self) -> bool:
        return not self.child_ids


@dataclass
class SearchHit:
    doc_id: str
    ordinal: int
    text: str
    score: float


@dataclass
class QuestionState:
    seen_communities: set[str] = field(default_factory=set)
    seen_overviews: set[str] = field(default_factory=set)
