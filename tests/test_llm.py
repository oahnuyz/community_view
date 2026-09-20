import json

import httpx
import numpy as np
import pytest

from community_wiki.llm import ModelClient
from community_wiki.metrics import measure
from community_wiki.overviews import object_schema, string_schema, validate_object


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
