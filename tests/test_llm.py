import json

import httpx
import numpy as np
import pytest

from community_view.llm import ModelClient
from community_view.metrics import measure
from community_view.overviews import (
    describe_community,
    document_overview,
    object_schema,
    string_schema,
    validate_object,
)


@pytest.mark.parametrize("kind,target,limit", [("document", 350, 450), ("community", 200, 250)])
@pytest.mark.parametrize("corrected", [True, False])
async def test_overview_length_feedback_and_retry_limit(
    config, store, text, caplog, kind, target, limit, corrected
):
    calls = []
    field = "summary" if kind == "document" else "overview"

    def respond(request):
        body = json.loads(request.content)
        calls.append(body)
        schema = body["response_format"]["json_schema"]["schema"]
        assert schema["properties"][field]["maxLength"] == target
        length = limit if corrected and len(calls) > 1 else limit + 1
        value = (
            {"title": "Title", "keywords": ["keyword"], "summary": "字" * length}
            if kind == "document"
            else {"name": "Community", "overview": "字" * length}
        )
        return httpx.Response(
            200,
            json={
                "usage": {"total_tokens": 2},
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(value, ensure_ascii=False),
                        },
                    }
                ],
            },
        )

    client = ModelClient(config, store, text, httpx.MockTransport(respond))
    try:
        operation = (
            document_overview("source", config, text, client)
            if kind == "document"
            else describe_community([], config, client)
        )
        if corrected:
            value = await operation
            assert len(value.summary if kind == "document" else value["overview"]) == limit
            assert len(calls) == 2
        else:
            with pytest.raises(ValueError, match="output validation failed"):
                await operation
            assert len(calls) == 3  # First attempt plus two correction attempts.
        error = f"{field}: {limit + 1} characters; at most {limit} characters required"
        assert error in caplog.text
        for attempt in calls[1:]:
            assert attempt["messages"][-2]["role"] == "assistant"
            assert error in attempt["messages"][-1]["content"]
    finally:
        await client.close()


async def test_http_retries_embedding_order_normalization(config, store, text, caplog):
    config.model.retry_delay_seconds = 0
    config.embedding.batch_size = 2
    calls = []

    def respond(request):
        body = json.loads(request.content)
        calls.append(body)
        if len(calls) == 1:
            return httpx.Response(429)
        assert request.url.path == "/v1/embeddings"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": i, "embedding": [i + 1, 1]}
                    for i in reversed(range(len(body["input"])))
                ],
                "usage": {"total_tokens": 4},
            },
        )

    client = ModelClient(config, store, text, httpx.MockTransport(respond))
    try:
        with measure("test") as metrics:
            vectors = await client.embed(["one", "two", "three"])
        assert metrics.embedding_tokens == 8
        assert len(vectors) == 3
        assert np.allclose(vectors[0], [1 / 2**0.5, 1 / 2**0.5])
        assert vectors[1][0] > vectors[1][1]
        assert all(np.isclose(np.linalg.norm(v), 1) for v in vectors)
        assert "retry=1/2" in caplog.text

    finally:
        await client.close()


async def test_json_validation_retry_and_protocol(config, store, text):
    calls = []

    def respond(request):
        body = json.loads(request.content)
        calls.append(body)
        content = '{"name":"too long"}' if len(calls) == 1 else '{"name":"ok"}'
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"finish_reason": "stop", "message": {"role": "assistant", "content": content}}
                ]
            },
        )

    client = ModelClient(config, store, text, httpx.MockTransport(respond))
    schema = object_schema({"name": string_schema(3)})
    try:
        result = await client.json_completion(
            "system",
            {"data": "doc"},
            schema,
            1,
            lambda value: validate_object(value, schema),
            "test",
        )
        assert result == {"name": "ok"}
        assert len(calls[1]["messages"]) == 4
        assert calls[0]["response_format"]["json_schema"]["strict"]
    finally:
        await client.close()


async def test_truncated_model_response_rejected(config, store, text):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"role": "assistant", "content": "partial"},
                    }
                ]
            },
        )
    )
    client = ModelClient(config, store, text, transport)
    try:
        with pytest.raises(ValueError, match="incomplete"):
            await client.chat([])
    finally:
        await client.close()


async def test_embedding_input_sent_without_local_token_limit(config, store):
    value = "far more than the old 8192 token limit " * 3000
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"usage": {"total_tokens": 30000}, "data": [{"index": 0, "embedding": [1, 0]}]},
        )

    # No tokenizer is needed: actual model input limits are handled by the server.
    client = ModelClient(config, store, None, httpx.MockTransport(respond))
    try:
        await client.embed([value])
        assert requests[0]["input"] == [value]
    finally:
        await client.close()


async def test_chat_and_structured_output_use_server_token_defaults(config, store):
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(
            200,
            json={
                "usage": {"total_tokens": 2},
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": '{"name":"ok"}'},
                    }
                ],
            },
        )

    client = ModelClient(config, store, None, httpx.MockTransport(respond))
    try:
        await client.chat([{"role": "user", "content": "question"}])
        schema = object_schema({"name": string_schema(3)})
        await client.json_completion(
            "system",
            {"text": "document"},
            schema,
            0,
            lambda value: validate_object(value, schema),
            "overview",
        )
        assert len(requests) == 2
        for request in requests:
            assert "max_tokens" not in request and "max_completion_tokens" not in request
            assert "max_output_tokens" not in request
    finally:
        await client.close()


async def test_multimodal_independent_texts_order_concurrency_and_usage(config, store):
    import asyncio

    config.embedding.api_format = "multimodal"
    config.embedding.dimensions = 2
    config.embedding.concurrency = 2
    active, peak = 0, 0
    second_done = asyncio.Event()

    async def respond(request):
        nonlocal active, peak
        body = json.loads(request.content)
        assert request.url.path == "/v1/embeddings"
        assert body["dimensions"] == 2
        assert len(body["input"]) == 1 and body["input"][0]["type"] == "text"
        value = int(body["input"][0]["text"])
        active += 1
        peak = max(peak, active)
        try:
            if value == 1:
                await asyncio.wait_for(second_done.wait(), 2)
            if value == 2:
                second_done.set()
            return httpx.Response(
                200,
                json={
                    "data": {"embedding": [value, 1], "object": "embedding"},
                    "usage": {"prompt_tokens": 5, "total_tokens": 5},
                },
            )
        finally:
            active -= 1

    client = ModelClient(config, store, None, httpx.MockTransport(respond))
    try:
        with measure("multimodal") as totals:
            vectors = await client.embed(["1", "2", "3"])
        assert peak == 2 and totals.embedding_tokens == 15
        assert len(vectors) == 3
        for i, vector in enumerate(vectors, 1):
            assert np.allclose(vector, np.array([i, 1]) / np.linalg.norm([i, 1]))
    finally:
        await client.close()
