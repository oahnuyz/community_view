import pytest

from community_view.ingest import ingest
from community_view.overviews import document_overview
from community_view.retrieval import Retriever


def test_unicode_lossless_windows(text):
    source = "开始🙂汉字混合 café\n" * 80 + "最后必须保留🚀"
    parts = text.split(source, 19)
    assert "".join(parts) == source
    assert all(text.count(p) <= 19 for p in parts)
    chunks = text.split(source, 21, 5)
    assert chunks[-1].endswith("最后必须保留🚀")
    assert all("�" not in p for p in chunks)


async def test_sequential_cumulative_overview(config, text, client):
    config.overview.fragment_tokens = 12
    source = "alpha 文档完整信息🙂" * 30
    result = await document_overview(source, config, text, client)
    calls = [payload for _, payload in client.calls]
    assert "".join(p["content"] for p in calls) == source
    assert len(calls) > 2
    assert calls[0]["previous_synthesis"] is None
    for i, payload in enumerate(calls[1:], 2):
        assert payload["previous_synthesis"] == f"cumulative-{i - 1}"
        assert payload["fragment_index"] == i
        assert payload["fragment_count"] == len(calls)
    assert calls[-1]["is_final"]
    assert result.summary == "全文摘要"
    assert client.peak == 1


async def test_concurrent_ingest_cache_atomic_failure(config, store, client, text, tmp_path):
    paths = []
    for i in range(4):
        path = tmp_path / f"{i}.txt"
        path.write_text(f"alpha 文档 {i} 内容")
        paths.append(path)
    result = await ingest(paths, config, store, client, text)
    assert result.inserted == 4 and not result.errors
    assert 1 < client.peak <= config.overview.concurrency
    assert len(store.documents()) == 4
    assert store.revision == 4
    before = len(client.calls)
    config.overview.concurrency = 2
    config.model.retries = 1
    cached = await ingest(paths, config, store, client, text)
    assert cached.unchanged == 4 and len(client.calls) == before
    paths[0].write_text("new content")
    original_embed = client.embed

    async def fail(_):
        raise ValueError("embedding failure")

    client.embed = fail
    failed = await ingest([paths[0]], config, store, client, text)
    assert failed.errors
    assert store.revision == 4
    assert store.documents()[0].content_hash
    client.embed = original_embed
    with pytest.raises(ValueError, match="stale"):
        Retriever(config, store, client, "community")
    Retriever(config, store, client, "naive")


async def test_empty_file_explicit_error(config, store, client, text, tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("  ")
    result = await ingest([path], config, store, client, text)
    assert "No extractable text" in result.errors[str(path)]
    assert not store.documents()


async def test_prompts_render_configured_length_limits(config, text, client):
    from community_view.overviews import describe_community

    config.overview.summary_max_chars = 321
    config.community.overview_max_chars = 234
    prompts = []
    original = client.json_completion

    async def capture(system, *args, **kwargs):
        prompts.append(system)
        return await original(system, *args, **kwargs)

    client.json_completion = capture
    await document_overview("alpha text", config, text, client)
    await describe_community([], config, client)
    assert "summary: aim for 300–321 characters" in prompts[0]
    assert "overview: aim for 150–234 characters" in prompts[1]
    assert all("${" not in prompt for prompt in prompts)
    assert all("spaces and punctuation" in prompt for prompt in prompts)


@pytest.mark.parametrize(
    "limit,length,accepted",
    [
        (1000, 800, True),
        (1000, 801, True),
        (1000, 1000, True),
        (1000, 1001, False),
        (1100, 1001, True),
        (1100, 1100, True),
        (1100, 1101, False),
        (1200, 1160, True),
        (1200, 1200, True),
        (1200, 1201, False),
        (1500, 1500, True),
        (1500, 1501, False),
    ],
)
async def test_summary_schema_and_local_limit_are_independent(
    config, text, limit, length, accepted
):
    config.overview.summary_max_chars = 800
    config.overview.summary_validation_max_chars = limit

    class Client:
        async def json_completion(self, system, payload, schema, retries, validate, purpose):
            assert schema["properties"]["summary"]["maxLength"] == 800
            assert payload["output_schema"] == schema
            assert "summary: aim for 300–800 characters" in system
            assert str(limit) not in system
            value = {"title": "Title", "keywords": ["keyword"], "summary": "a" * length}
            validate(value)
            return value

    if accepted:
        result = await document_overview("source", config, text, Client())
        assert len(result.summary) == length
    else:
        with pytest.raises(ValueError, match=f"{length} characters; at most {limit}"):
            await document_overview("source", config, text, Client())
