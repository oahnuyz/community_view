"""Versioned question/community mappings and resumable knowledge compilations."""

import hashlib
import json
from dataclasses import asdict


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def fingerprint(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def graph_key(documents, edges, communities):
    # Content identity, independent of paths/endpoints. Re-clustering invalidates mappings.
    return fingerprint(
        {
            "documents": [(d.doc_id, d.content_hash, d.overview.model_dump()) for d in documents],
            "edges": [asdict(e) for e in edges],
            "communities": [asdict(c) for c in communities],
        }
    )


def initialize(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS question_communities(
        run_id TEXT PRIMARY KEY, graph_key TEXT NOT NULL, question TEXT NOT NULL,
        community_ids TEXT NOT NULL, status TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS knowledge_compilations(
        signature TEXT NOT NULL, community_id TEXT NOT NULL, graph_key TEXT NOT NULL,
        body TEXT NOT NULL, PRIMARY KEY(signature,community_id));
    CREATE TABLE IF NOT EXISTS question_sources(run_id TEXT PRIMARY KEY, question_id TEXT);
    CREATE TABLE IF NOT EXISTS knowledge_views(
        graph_key TEXT NOT NULL, community_id TEXT NOT NULL, signature TEXT NOT NULL,
        body TEXT NOT NULL, PRIMARY KEY(graph_key,community_id));
    CREATE TABLE IF NOT EXISTS knowledge_answers(
        graph_key TEXT NOT NULL, question_id TEXT NOT NULL, community_id TEXT NOT NULL,
        signature TEXT NOT NULL, ordinal INTEGER NOT NULL, question TEXT NOT NULL,
        answer TEXT NOT NULL, source_questions TEXT NOT NULL, vector TEXT NOT NULL,
        PRIMARY KEY(graph_key,question_id));
    """)


def record_question(store, run_id, key, question, community_ids, status, question_id=None):
    with store.db:
        store.db.execute(
            "INSERT OR REPLACE INTO question_communities VALUES (?,?,?,?,?)",
            (run_id, key, question, encoded(sorted(community_ids)), status),
        )
        if question_id is not None:
            store.db.execute(
                "INSERT OR REPLACE INTO question_sources VALUES (?,?)", (run_id, question_id)
            )


def historical_questions(store, key):
    """Question-only provenance; never include gold answers or prior generated answers."""
    rows = store.db.execute(
        "SELECT q.run_id,q.question,q.community_ids,s.question_id FROM question_communities q "
        "LEFT JOIN question_sources s USING(run_id) WHERE q.graph_key=? AND q.status='complete' "
        "ORDER BY q.question,q.run_id",
        (key,),
    ).fetchall()
    ids = {q: f"H{i:04d}" for i, q in enumerate(sorted({r[1] for r in rows}), 1)}
    result = {}
    for run_id, question, communities, external_id in rows:
        for identity in json.loads(communities):
            record = result.setdefault(identity, {}).setdefault(
                ids[question],
                {
                    "source_question_id": ids[question],
                    "question": question,
                    "run_ids": [],
                    "external_question_ids": [],
                },
            )
            record["run_ids"].append(run_id)
            if external_id is not None and external_id not in record["external_question_ids"]:
                record["external_question_ids"].append(external_id)
    return {c: list(questions.values()) for c, questions in result.items()}


def published_views(store, key):
    result = {
        identity: json.loads(body)
        for identity, body in store.db.execute(
            "SELECT community_id,body FROM knowledge_views WHERE graph_key=? ORDER BY community_id",
            (key,),
        )
    }
    for view in result.values():
        view.update(entries=[], vectors={})
    for cid, qid, question, answer, sources, vector in store.db.execute(
        "SELECT community_id,question_id,question,answer,source_questions,vector "
        "FROM knowledge_answers WHERE graph_key=? ORDER BY community_id,ordinal",
        (key,),
    ):
        result[cid]["entries"].append(
            {
                "question_id": qid,
                "question": question,
                "answer": answer,
                "source_questions": json.loads(sources),
            }
        )
        result[cid]["vectors"][qid] = json.loads(vector)
    return result


def publish_view(store, job, view):
    # One complete view per community. A failed replacement cannot destroy prior knowledge.
    with store.db:
        store.db.execute(
            "DELETE FROM knowledge_answers WHERE graph_key=? AND community_id=?",
            (job["graph_key"], job["community_id"]),
        )
        store.db.execute(
            "INSERT OR REPLACE INTO knowledge_views VALUES (?,?,?,?)",
            (
                job["graph_key"],
                job["community_id"],
                job["signature"],
                encoded({k: v for k, v in view.items() if k not in {"entries", "vectors"}}),
            ),
        )
        for ordinal, entry in enumerate(view["entries"], 1):
            store.db.execute(
                "INSERT INTO knowledge_answers VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    job["graph_key"],
                    entry["question_id"],
                    job["community_id"],
                    job["signature"],
                    ordinal,
                    entry["question"],
                    entry["answer"],
                    encoded(entry["source_questions"]),
                    encoded(view["vectors"][entry["question_id"]]),
                ),
            )


def load_job(store, signature, identity):
    row = store.db.execute(
        "SELECT body FROM knowledge_compilations WHERE signature=? AND community_id=?",
        (signature, identity),
    ).fetchone()
    return json.loads(row[0]) if row else None


def save_job(store, job):
    with store.db:
        store.db.execute(
            "INSERT OR REPLACE INTO knowledge_compilations VALUES (?,?,?,?)",
            (job["signature"], job["community_id"], job["graph_key"], encoded(job)),
        )
