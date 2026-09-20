import pytest

from community_wiki.ingest import ingest
from community_wiki.overviews import document_overview
from community_wiki.retrieval import Retriever


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
