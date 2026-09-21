from concurrent.futures import ThreadPoolExecutor

from community_wiki.experiments import load_dataset, verify_index
from community_wiki.ingest import digest, ingest
from community_wiki.store import Store


async def test_ids_follow_source_order_and_survive_retry_update_restart(
    config, store, client, text, tmp_path
):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("")
    b.write_text("beta")
    result = await ingest([b, a], config, store, client, text)
    assert result.inserted == 1 and str(a) in result.errors
    assert store.documents()[0].doc_id == "D0002"
    a.write_text("alpha")
    b.write_text("updated beta")
    reopened = Store(config.storage.database)
    try:
        result = await ingest([b, a], config, reopened, client, text)
        assert result.inserted == 2 and not result.errors
        assert {d.source: d.doc_id for d in reopened.documents()} == {
            str(a): "D0001",
            str(b): "D0002",
        }
        assert {c.doc_id for c in reopened.chunks()} == {"D0001", "D0002"}
        assert (await ingest([a, b], config, reopened, client, text)).unchanged == 2
    finally:
        reopened.close()


def test_sequence_is_shared_across_connections_and_never_recycles(config, store):
    assert store.allocate_document_ids(["c", "b", "a"]) == {
        "a": "D0001",
        "b": "D0002",
        "c": "D0003",
    }

    def reserve(sources):
        other = Store(config.storage.database)
        try:
            return other.allocate_document_ids(sources)
        finally:
            other.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(reserve, [["shared", "d"], ["shared", "e"]]))
    assert first["shared"] == second["shared"]
    assert len({first["shared"], first["d"], second["e"]}) == 3
    assert store.allocate_document_ids(["z"])["z"] == "D0007"
    with store.db:
        store.db.execute("DELETE FROM document_ids WHERE source='z'")
    assert store.allocate_document_ids(["after_deleted"])["after_deleted"] == "D0008"
    with store.db:
        store._set_meta("document_id_sequence", 9999)
    assert store.allocate_document_ids(["overflow"])["overflow"] == "D10000"


async def test_legacy_ids_and_benchmark_validation_stay_compatible(
    benchmark_settings, config, store, client, text, monkeypatch
):
    dataset = load_dataset(benchmark_settings)
    with monkeypatch.context() as patch:
        patch.setattr(
            store, "allocate_document_ids", lambda sources: {s: digest(s) for s in sources}
        )
        assert not (await ingest(dataset.paths, config, store, client, text)).errors
    expected = {d.source: d.doc_id for d in store.documents()}
    assert all(len(v) == 64 for v in expected.values())
    assert (await ingest(dataset.paths, config, store, client, text)).unchanged == 2
    assert {d.source: d.doc_id for d in store.documents()} == expected
    verify_index(dataset, config, store, complete=True)
    assert store.allocate_document_ids(["new"])["new"] == "D0001"
