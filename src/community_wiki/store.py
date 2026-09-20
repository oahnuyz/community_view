"""SQLite persistence. Documents and complete graph snapshots publish atomically."""

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .models import Chunk, Community, Document, Edge, Overview


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT OR IGNORE INTO meta VALUES ('revision','0');
        CREATE TABLE IF NOT EXISTS documents(
            doc_id TEXT PRIMARY KEY, source TEXT UNIQUE NOT NULL, content_hash TEXT NOT NULL,
            signature TEXT NOT NULL, overview TEXT NOT NULL, vector BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS chunks(
            doc_id TEXT REFERENCES documents(doc_id) ON DELETE CASCADE,
            ordinal INTEGER, text TEXT NOT NULL, vector BLOB NOT NULL,
            PRIMARY KEY(doc_id, ordinal));
        CREATE TABLE IF NOT EXISTS edges(
            source TEXT, target TEXT, weight REAL, vector_score REAL, keyword_score REAL,
            PRIMARY KEY(source,target));
        CREATE TABLE IF NOT EXISTS communities(community_id TEXT PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS community_links(source TEXT, target TEXT, body TEXT, PRIMARY KEY(source,target));
        CREATE TABLE IF NOT EXISTS runs(
            run_id TEXT PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP,
            mode TEXT, status TEXT, messages TEXT);
        """)

    def close(self):
        self.db.close()

    def meta(self, key: str) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def _set_meta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, str(value)))

    @property
    def revision(self):
        return int(self.meta("revision"))

    def documents(self) -> list[Document]:
        return [
            Document(
                a,
                b,
                c,
                d,
                Overview.model_validate_json(e),
                np.frombuffer(f, dtype=np.float32).copy(),
            )
            for a, b, c, d, e, f in self.db.execute("SELECT * FROM documents ORDER BY doc_id")
        ]

    def chunks(self) -> list[Chunk]:
        return [
            Chunk(a, b, c, np.frombuffer(d, dtype=np.float32).copy())
            for a, b, c, d in self.db.execute("SELECT * FROM chunks ORDER BY doc_id,ordinal")
        ]

    def edges(self) -> list[Edge]:
        return [Edge(*row) for row in self.db.execute("SELECT * FROM edges ORDER BY source,target")]

    def communities(self) -> list[Community]:
        return [
            Community(**json.loads(row[0]))
            for row in self.db.execute("SELECT body FROM communities ORDER BY community_id")
        ]

    def save_document(self, doc: Document, chunks: list[Chunk], embedding_signature: str):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            previous = self.meta("embedding_signature")
            if previous and previous != embedding_signature:
                raise ValueError("Embedding configuration changed; use a new database and rebuild")
            dimensions = self.meta("embedding_dimensions")
            if dimensions and int(dimensions) != len(doc.vector):
                raise ValueError("Embedding dimension changed; use a new database")
            if any(len(c.vector) != len(doc.vector) or c.doc_id != doc.doc_id for c in chunks):
                raise ValueError("Inconsistent document/chunk embeddings or identifiers")
            self.db.execute(
                "INSERT INTO documents VALUES (?,?,?,?,?,?) ON CONFLICT(doc_id) "
                "DO UPDATE SET source=excluded.source, content_hash=excluded.content_hash, "
                "signature=excluded.signature, overview=excluded.overview, vector=excluded.vector",
                (
                    doc.doc_id,
                    doc.source,
                    doc.content_hash,
                    doc.signature,
                    doc.overview.model_dump_json(),
                    doc.vector.astype(np.float32).tobytes(),
                ),
            )
            self.db.execute("DELETE FROM chunks WHERE doc_id=?", (doc.doc_id,))
            self.db.executemany(
                "INSERT INTO chunks VALUES (?,?,?,?)",
                [
                    (c.doc_id, c.ordinal, c.text, c.vector.astype(np.float32).tobytes())
                    for c in chunks
                ],
            )
            self._set_meta("embedding_signature", embedding_signature)
            self._set_meta("embedding_dimensions", len(doc.vector))
            self._set_meta("revision", self.revision + 1)

    def publish_graph(
        self,
        edges: list[Edge],
        communities: list[Community],
        revision: int,
        signature: str,
        links=(),
    ):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if self.revision != revision:
                raise ValueError("Documents changed while clustering; retry clustering")
            self.db.execute("DELETE FROM edges")
            self.db.execute("DELETE FROM communities")
            self.db.execute("DELETE FROM community_links")
            self.db.executemany(
                "INSERT INTO community_links VALUES (?,?,?)",
                [(link["source"], link["target"], dumps(link)) for link in links],
            )
            self.db.executemany(
                "INSERT INTO edges VALUES (?,?,?,?,?)",
                [(e.source, e.target, e.weight, e.vector_score, e.keyword_score) for e in edges],
            )
            self.db.executemany(
                "INSERT INTO communities VALUES (?,?)",
                [(c.community_id, dumps(asdict(c))) for c in communities],
            )
            self._set_meta("graph_revision", revision)
            self._set_meta("graph_signature", signature)

    def links(self):
        return [
            json.loads(row[0])
            for row in self.db.execute("SELECT body FROM community_links ORDER BY source,target")
        ]

    def snapshot(self):
        # A single read transaction avoids mixing documents and a concurrently published graph.
        with self.db:
            self.db.execute("BEGIN")
            return (
                self.documents(),
                self.chunks(),
                self.edges(),
                self.communities(),
                self.revision,
                self.meta("graph_revision"),
            )

    def save_run(self, run_id, mode, status, messages):
        with self.db:
            self.db.execute(
                "INSERT INTO runs(run_id,mode,status,messages) VALUES (?,?,?,?) "
                "ON CONFLICT(run_id) DO UPDATE SET status=excluded.status,messages=excluded.messages",
                (run_id, mode, status, dumps(messages)),
            )
