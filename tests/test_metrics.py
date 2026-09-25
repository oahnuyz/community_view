import asyncio
import json

import httpx
import pytest

from community_view.llm import ModelClient
from community_view.metrics import measure, record_usage


async def test_concurrent_scopes_and_child_tasks_are_isolated():
    async def one(label, size):
        with measure(label) as totals:

            async def child():
                await asyncio.sleep(0.001)
                record_usage(
                    {"prompt_tokens": size, "completion_tokens": 2, "total_tokens": size + 2},
                    "agent",
                )

            await asyncio.gather(child(), child())
            record_usage({"total_tokens": size}, "embedding")
        return totals.as_dict()

    first, second = await asyncio.gather(one("first", 10), one("second", 30))
    assert first["total_tokens"] == 34
    assert second["total_tokens"] == 94


async def test_missing_usage_is_zero_and_never_retried(config, store, text, caplog):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"finish_reason": "stop", "message": {"role": "assistant", "content": "answer"}}
                ]
            },
        )

    client = ModelClient(config, store, text, httpx.MockTransport(respond))
    try:
        with measure("qa:test") as totals:
            message = await client.chat([])
        assert message["content"] == "answer" and len(calls) == 1
        assert totals.as_dict()["total_tokens"] == 0
        assert "Missing usage" in caplog.text and "tokens=0" in caplog.text
        assert "qa:test" in caplog.text
    finally:
        await client.close()


@pytest.mark.parametrize("status", [400, 401, 429, 500])
async def test_failed_api_requests_retry_twice(config, store, text, caplog, status):
    config.model.retry_delay_seconds = 0
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(status, json={"error": "test"})

    client = ModelClient(config, store, text, httpx.MockTransport(respond))
    try:
        with pytest.raises(RuntimeError, match="after 3 attempt"):
            await client.chat([])
        assert len(calls) == 3
        assert "retry=1/2" in caplog.text and "retry=2/2" in caplog.text
        assert "retries exhausted" in caplog.text
    finally:
        await client.close()


async def test_keys_loaded_from_separate_file(config, store, text):
    headers = []

    def respond(request):
        headers.append(request.headers["authorization"])
        if request.url.path.endswith("embeddings"):
            return httpx.Response(
                200,
                json={"usage": {"total_tokens": 1}, "data": [{"index": 0, "embedding": [1, 0]}]},
            )
        return httpx.Response(
            200,
            json={
                "usage": {"total_tokens": 1},
                "choices": [
                    {"finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}
                ],
            },
        )

    client = ModelClient(config, store, text, httpx.MockTransport(respond))
    try:
        await client.chat([])
        await client.embed(["query"])
        assert headers == ["Bearer test-only", "Bearer test-embedding"]
        snapshot = json.dumps(config.model_dump(mode="json"))
        assert "test-only" not in snapshot and "test-embedding" not in snapshot
    finally:
        await client.close()
