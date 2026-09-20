"""Load, validate and select any prepared dataset without leaking answer labels."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ..ingest import digest, ingestion_signature
from ..store import dumps


def read_jsonl(path):
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def write_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


@dataclass
class Dataset:
    questions: list[dict]
    documents: list[dict]
    paths: list[Path]
    manifest: dict


def load_dataset(settings):
    root = settings.dataset_dir
    questions = read_jsonl(root / "qa.jsonl")
    documents = read_jsonl(root / "documents.jsonl")
    end = len(questions) if settings.count is None else settings.start + settings.count
    if settings.start >= len(questions) or end > len(questions):
        raise ValueError("Dataset has fewer questions than requested start + count")
    selected = questions[settings.start : end]
    for records, label in ((questions, "QA"), (documents, "document")):
        if not records or any(not isinstance(r.get("id"), str) or not r["id"] for r in records):
            raise ValueError(f"Missing {label} records/IDs")
        if len({r["id"] for r in records}) != len(records):
            raise ValueError(f"Duplicate {label} IDs")
    if any(not isinstance(q.get("question"), str) or not q["question"].strip() for q in selected):
        raise ValueError("Empty or invalid question")
    required = {doc_id for question in selected for doc_id in question.get("document_ids", [])}
    if required - {doc["id"] for doc in documents}:
        raise ValueError("Question references documents missing from the manifest")
    paths = []
    hashes = []
    for document in documents:
        path = (root / document["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f"Invalid corpus path: {document['path']}")
        content = path.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != document["sha256"] or len(content) != document["size_bytes"]:
            raise ValueError(f"Corpus checksum/size mismatch: {document['id']}")
        paths.append(path)
        hashes.append((document["id"], document["path"], actual_hash))
    if len(set(paths)) != len(paths):
        raise ValueError("Different document IDs point to the same corpus file")
    manifest = {
        "dataset_dir": str(root),
        "start": settings.start,
        "count": len(selected),
        "question_ids": [q["id"] for q in selected],
        "document_count": len(documents),
        "referenced_document_count": len(required),
        "corpus_scope": "all_documents_in_prepared_manifest",
        "dataset_signature": digest(dumps({"questions": selected, "documents": hashes})),
        "source_info": json.loads((root / "dataset_info.json").read_text(encoding="utf-8")),
    }
    return Dataset(selected, documents, paths, manifest)


def prepare(settings, dataset):
    output = settings.output_dir
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "selection.json"
    if (
        manifest_path.exists()
        and json.loads(manifest_path.read_text())["dataset_signature"]
        != dataset.manifest["dataset_signature"]
    ):
        raise ValueError("Dataset/selection changed; choose a new benchmark output_dir")
    write_json(manifest_path, dataset.manifest)
    return dataset.manifest


def verify_index(dataset, config, store, *, complete):
    expected = {
        digest(str(path)): doc for doc, path in zip(dataset.documents, dataset.paths, strict=True)
    }
    actual = {doc.doc_id: doc for doc in store.documents()}
    if actual.keys() - expected.keys():
        raise ValueError("Benchmark database contains documents outside the prepared corpus")
    if complete and actual.keys() != expected.keys():
        raise ValueError("Benchmark index is incomplete; run benchmark --stage index first")
    if complete:
        signature = ingestion_signature(config)
        for identity, doc in actual.items():
            if doc.content_hash != expected[identity]["sha256"] or doc.signature != signature:
                raise ValueError("Benchmark document/config changed; run benchmark --stage index")
