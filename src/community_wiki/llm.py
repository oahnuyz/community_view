"""Small OpenAI-compatible HTTP adapter with bounded concurrency and audited retries."""

import asyncio
import json
import logging
from collections.abc import Callable

import httpx
import numpy as np

from .config import Config
from .credentials import Credentials
from .metrics import context_label, record_usage
from .store import Store
from .text import TextProcessor

log = logging.getLogger(__name__)


class ModelClient:
    def __init__(
        self,
        config: Config,
        store: Store | None,
        text: TextProcessor | None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.config, self.store, self.text = config, store, text
        self.http = httpx.AsyncClient(timeout=config.model.timeout_seconds, transport=transport)
        self.credentials = None
        self.chat_slots = asyncio.Semaphore(config.model.concurrency)
        self.embed_slots = asyncio.Semaphore(config.embedding.concurrency)

    async def close(self):
        await self.http.aclose()

    async def _post(self, base, route, body, slots, purpose):
        if self.credentials is None:
            self.credentials = Credentials.load(self.config.keys_file)
        key = self.credentials.key(purpose)
        attempts = self.config.model.retries + 1
        for attempt in range(attempts):
            try:
                async with slots:
                    response = await self.http.post(
                        f"{base.rstrip('/')}/{route}",
                        json=body,
                        headers={"Authorization": f"Bearer {key}"},
                    )
                    response.raise_for_status()
                    result = response.json()
                    if not isinstance(result, dict):
                        raise ValueError("Expected JSON object")
                record_usage(result.get("usage"), purpose)
                return result
            except (httpx.HTTPError, ValueError) as exc:
                status = (
                    exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                )
                error = f"{type(exc).__name__}: HTTP {status}" if status else type(exc).__name__
                if isinstance(exc, httpx.HTTPStatusError):
                    try:
                        failure = exc.response.json()
                    except ValueError:
                        failure = {}
                    if isinstance(failure, dict) and failure.get("usage") is not None:
                        record_usage(failure["usage"], purpose)
                retry = attempt + 1 < attempts
                log.warning(
                    "API request failed: scope=%s purpose=%s attempt=%s/%s error=%s %s",
                    context_label(),
                    purpose,
                    attempt + 1,
                    attempts,
                    error,
                    f"retry={attempt + 1}/{self.config.model.retries}"
                    if retry
                    else "retries exhausted",
                )
                if not retry:
                    raise RuntimeError(
                        f"{purpose} failed ({error}) after {attempts} attempt(s)"
                    ) from exc
                await asyncio.sleep(self.config.model.retry_delay_seconds * 2**attempt)

    async def chat(
        self,
        messages,
        *,
        tools=None,
        response_format=None,
        purpose="agent",
        force_final=False,
    ):
        c = self.config.model
        body = {
            "model": c.chat_model,
            "messages": messages,
            "temperature": c.temperature,
            **c.extra_body,
        }
        if tools:
            body.update(tools=tools, tool_choice="none" if force_final else "auto")
        if response_format:
            body["response_format"] = response_format
        result = await self._post(c.base_url, "chat/completions", body, self.chat_slots, purpose)
        choice = result["choices"][0]
        if choice.get("finish_reason") not in ("stop", "tool_calls"):
            raise ValueError(f"{purpose}: incomplete model output ({choice.get('finish_reason')})")
        message = choice["message"]
        if message.get("refusal"):
            raise ValueError(f"{purpose}: model refused structured output")
        return {k: message[k] for k in ("role", "content", "tool_calls") if k in message}

    async def json_completion(
        self,
        system: str,
        payload: dict | str,
        schema: dict,
        retries: int,
        validate: Callable,
        purpose: str,
    ):
        fmt = {"type": "json_object"}
        if self.config.model.structured_output == "json_schema":
            fmt = {
                "type": "json_schema",
                "json_schema": {"name": "result", "strict": True, "schema": schema},
            }
        messages = [{"role": "system", "content": system}] if system else []
        messages.append(
            {
                "role": "user",
                "content": payload
                if isinstance(payload, str)
                else json.dumps(payload, ensure_ascii=False),
            }
        )
        for attempt in range(retries + 1):
            message = await self.chat(messages, response_format=fmt, purpose=purpose)
            try:
                value = json.loads(message.get("content") or "")
                validate(value)
                return value
            except (ValueError, TypeError, KeyError) as exc:
                log.warning("Invalid %s output: %s", purpose, exc)
                if attempt == retries:
                    raise ValueError(f"{purpose}: output validation failed: {exc}") from exc
                messages.extend(
                    [
                        message,
                        {
                            "role": "user",
                            "content": f"Return corrected JSON only. Validation error: {exc}",
                        },
                    ]
                )
        raise AssertionError("unreachable")

    async def embed(self, texts: list[str]) -> list[np.ndarray]:
        if not texts:
            return []
        c = self.config.embedding
        multimodal = c.api_format == "multimodal"
        batch_size = 1 if multimodal else c.batch_size

        async def batch(items):
            body = {"model": c.model, "input": items, "encoding_format": "float"}
            if multimodal:
                # Multimodal inputs describe one sample, not independent batch items.
                body["input"] = [{"type": "text", "text": items[0]}]
            if c.dimensions is not None:
                body["dimensions"] = c.dimensions
            result = await self._post(c.base_url, "embeddings", body, self.embed_slots, "embedding")
            data = (
                [{"index": 0, "embedding": result["data"]["embedding"]}]
                if multimodal
                else sorted(result["data"], key=lambda v: v["index"])
            )
            if [v["index"] for v in data] != list(range(len(items))):
                raise ValueError("Embedding response has missing/duplicate indexes")
            vectors = []
            for item in data:
                vector = np.asarray(item["embedding"], dtype=np.float32)
                if vector.ndim != 1 or not vector.size or not np.isfinite(vector).all():
                    raise ValueError("Invalid embedding vector")
                norm = np.linalg.norm(vector)
                if not norm or (c.dimensions and len(vector) != c.dimensions):
                    raise ValueError("Zero or unexpected embedding dimension")
                vectors.append(vector / norm)
            return vectors

        # Drain every batch before returning even when one fails: no unaccounted background calls.
        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(batch(texts[i : i + batch_size]))
                for i in range(0, len(texts), batch_size)
            ]
        vectors = [vector for task in tasks for vector in task.result()]
        if len({len(v) for v in vectors}) != 1:
            raise ValueError("Embedding dimensions differ between batches")
        return vectors
