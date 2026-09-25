import json
import shutil

import pytest

from community_view.communities import cluster
from community_view.experiments.dataset import load_dataset
from community_view.experiments.reuse import clone_index
from community_view.ingest import ingest
from community_view.store import Store


async def test_reuse_preserves_source_and_vectors(
    config, benchmark_settings, store, client, text, tmp_path
):
    source_config = config.model_copy(deep=True)
    source_config.overview.summary_validation_max_chars = 350
    data = load_dataset(benchmark_settings)
    await ingest(data.paths, source_config, store, client, text)
    await cluster(source_config, store, client)
    original = store.db.execute("SELECT * FROM documents ORDER BY doc_id").fetchall()
    chunks = store.db.execute("SELECT * FROM chunks ORDER BY doc_id,ordinal").fetchall()
    execution = tmp_path / "execution.json"
    historical = source_config.model_dump(mode="json")
    historical["community"].pop("llm_split_fallback")  # A v2 snapshot predates the option.
    execution.write_text(json.dumps({"config": historical}))
    destination = benchmark_settings.model_copy(deep=True)
    destination.output_dir = tmp_path / "new-run"
    destination.database = destination.output_dir / "index.sqlite3"
    destination.dataset_dir = tmp_path / "relocated-corpus"
    shutil.copytree(benchmark_settings.dataset_dir, destination.dataset_dir)
    calls = len(client.calls)
    record = clone_index(
        config.storage.database, execution, benchmark_settings.dataset_dir, destination, config
    )
    assert record["documents"] == 2 and record["new_indexing_tokens"] == 0
    assert "llm_split_fallback" not in record["historical_config"]["community"]
    assert len(client.calls) == calls
    assert store.db.execute("SELECT * FROM documents ORDER BY doc_id").fetchall() == original
    copied = Store(destination.database)
    try:
        assert (
            copied.db.execute("SELECT * FROM chunks ORDER BY doc_id,ordinal").fetchall() == chunks
        )
        assert all(d.source.startswith(str(destination.dataset_dir)) for d in copied.documents())
        assert all(c.community_id.startswith("C") for c in copied.communities())
        assert copied.meta("revision") == store.meta("revision")
    finally:
        copied.close()
    with pytest.raises(ValueError, match="fresh"):
        clone_index(
            config.storage.database, execution, benchmark_settings.dataset_dir, destination, config
        )
    destination.database = tmp_path / "bad" / "index.sqlite3"
    bad_config = config.model_copy(deep=True)
    bad_config.embedding.model = "different-model"
    with pytest.raises(ValueError, match="embedding"):
        clone_index(
            config.storage.database,
            execution,
            benchmark_settings.dataset_dir,
            destination,
            bad_config,
        )
    assert not destination.database.exists()
