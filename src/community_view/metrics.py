"""Task-local aggregate counters; no per-request usage database or export."""

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass

log = logging.getLogger(__name__)


@dataclass
class Totals:
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_total_tokens: int = 0
    embedding_tokens: int = 0
    rounds: int = 0

    def as_dict(self):
        values = asdict(self)
        values["total_tokens"] = self.llm_total_tokens + self.embedding_tokens
        return values


@dataclass
class Scope:
    label: str
    totals: Totals


current_scope: ContextVar[Scope | None] = ContextVar("metrics_scope", default=None)


@contextmanager
def measure(label):
    scope = Scope(label, Totals())
    token = current_scope.set(scope)
    try:
        yield scope.totals
    finally:
        current_scope.reset(token)


def context_label():
    scope = current_scope.get()
    return scope.label if scope else "interactive"


def count_round():
    scope = current_scope.get()
    if scope:
        scope.totals.rounds += 1


def record_usage(usage, purpose):
    def integer(value):
        return (
            value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
        )

    values = usage if isinstance(usage, dict) else {}
    incoming = integer(values.get("prompt_tokens", values.get("input_tokens")))
    outgoing = integer(values.get("completion_tokens", values.get("output_tokens")))
    total = integer(values.get("total_tokens"))
    if total is None and incoming is None and outgoing is None:
        log.warning(
            "Missing usage: scope=%s purpose=%s; tokens=0; continuing without retry",
            context_label(),
            purpose,
        )
        return
    total = total if total is not None else (incoming or 0) + (outgoing or 0)
    scope = current_scope.get()
    if not scope:
        return
    if purpose == "embedding":
        scope.totals.embedding_tokens += total
    else:
        scope.totals.llm_input_tokens += incoming or 0
        scope.totals.llm_output_tokens += outgoing or 0
        scope.totals.llm_total_tokens += total
