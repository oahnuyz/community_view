"""Clone an explicitly chosen historical index for a new QA/judge experiment."""

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from ..communities import graph_signature
from ..community_ids import remap_community_links, shorten_community_ids
from ..ingest import embedding_signature, ingestion_signature
from ..store import Store
from .dataset import load_dataset, verify_index, write_json


def clone_index(source_database, source_execution, source_dataset, settings, config):
    """Reuse historical outputs; never call models or mutate the source database.

    Endpoint relocation, operational concurrency and a relaxed summary validator are
    accepted explicitly here. Raw TXT corpora may predate the PDF configuration.
    The old execution config/signatures remain recorded as historical provenance.
    """
    source_database = Path(source_database).resolve()
    source_dataset = Path(source_dataset)
    old = json.loads(Path(source_execution).read_text())["config"]
    new = config.model_dump(mode="json")
    dataset = load_dataset(settings)
    if settings.database.exists() or (settings.output_dir / "execution.json").exists():
        raise ValueError("Reuse requires a fresh destination database and experiment")

    def compatible(section, ignored=()):
        before = {k: v for k, v in old[section].items() if k not in ignored}
        after = {k: v for k, v in new[section].items() if k not in ignored}
        if section == "community":
            before.setdefault("llm_split_fallback", False)
        if before != after:
            raise ValueError(f"Cannot reuse index: {section} configuration changed")

    compatible("embedding", {"base_url", "concurrency", "batch_size"})
    compatible(
        "model", {"base_url", "concurrency", "timeout_seconds", "retries", "retry_delay_seconds"}
    )
    compatible("overview", {"concurrency", "validation_retries", "summary_validation_max_chars"})
    old_limit = old["overview"].get(
        "summary_validation_max_chars", old["overview"]["summary_max_chars"]
    )
    if config.overview.summary_validation_max_chars < old_limit:
        raise ValueError("Reuse cannot tighten the summary validator")
    ignored_text = {"extensions"}
    if all(path.suffix.lower() != ".pdf" for path in dataset.paths):
        ignored_text.add("pdf")
    compatible("text", ignored_text)
    compatible("graph")
    compatible("community", {"cluster_workers", "description_concurrency", "validation_retries"})

    # Validate every document against the prepared corpus before creating the copy.
    expected = {doc["path"]: doc for doc in dataset.documents}
    with sqlite3.connect(f"file:{source_database}?mode=ro", uri=True) as source:
        rows = source.execute(
            "SELECT source,content_hash,signature,overview FROM documents"
        ).fetchall()
        moved = {}
        for path, content_hash, _, overview in rows:
            relative = Path(path).relative_to(source_dataset).as_posix()
            if relative not in expected or expected[relative]["sha256"] != content_hash:
                raise ValueError(f"Historical document differs from dataset: {relative}")
            if len(json.loads(overview)["summary"]) > config.overview.summary_validation_max_chars:
                raise ValueError(f"Historical overview exceeds new limit: {relative}")
            moved[path] = str((settings.dataset_dir / relative).resolve())
        if len(rows) != len(expected) or set(moved.values()) != set(map(str, dataset.paths)):
            raise ValueError("Historical corpus is incomplete or duplicated")
        meta = dict(source.execute("SELECT key,value FROM meta"))
        if meta.get("graph_revision") != meta.get("revision"):
            raise ValueError("Historical community graph is stale")
        if not source.execute("SELECT COUNT(*) FROM communities").fetchone()[0]:
            raise ValueError("Historical index has no communities")
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        settings.database.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(settings.database) as target:
            source.backup(target)

    store = Store(settings.database)
    try:
        before = [
            (d.doc_id, d.content_hash, d.overview.model_dump(), d.vector.tobytes())
            for d in store.documents()
        ]
        chunks_before = store.db.execute("SELECT * FROM chunks ORDER BY doc_id,ordinal").fetchall()
        edges_before = [asdict(e) for e in store.edges()]
        old_communities = store.communities()
        communities, mapping = shorten_community_ids(store, old_communities)
        links = remap_community_links(store.links(), mapping)
        with store.db:
            for previous, current in moved.items():
                store.db.execute(
                    "UPDATE documents SET source=?,signature=? WHERE source=?",
                    (current, ingestion_signature(config), previous),
                )
                store.db.execute(
                    "UPDATE document_ids SET source=? WHERE source=?", (current, previous)
                )
            store._set_meta("embedding_signature", embedding_signature(config))
            # Old model traces belong to the original experiment, not the new run.
            store.db.execute("DELETE FROM runs")
        store.publish_graph(
            store.edges(), communities, store.revision, graph_signature(config), links
        )
        verify_index(dataset, config, store, complete=True)
        assert before == [
            (d.doc_id, d.content_hash, d.overview.model_dump(), d.vector.tobytes())
            for d in store.documents()
        ]
        assert (
            chunks_before
            == store.db.execute("SELECT * FROM chunks ORDER BY doc_id,ordinal").fetchall()
        )
        assert edges_before == [asdict(e) for e in store.edges()]
        record = {
            "source_database": str(source_database),
            "source_database_sha256": hashlib.sha256(source_database.read_bytes()).hexdigest(),
            "source_execution": str(source_execution),
            "historical_config": old,
            "historical_ingestion_signatures": sorted({r[2] for r in rows}),
            "historical_meta": meta,
            "new_ingestion_signature": ingestion_signature(config),
            "source_path_mapping": moved,
            "community_id_mapping": mapping,
            "documents": len(before),
            "chunks": len(chunks_before),
            "communities": len(communities),
            "leaves": sum(c.is_leaf for c in communities),
            "reingested": False,
            "reclustered": False,
            "new_indexing_tokens": 0,
            "reuse_policy": "Explicitly accept historical overview/chunk/graph outputs; rebind validated corpus paths and compatibility signatures. Original model outputs are unchanged, not regenerated under the new config.",
        }
        write_json(settings.output_dir / "reused_index.json", record)
        return record
    finally:
        store.close()
