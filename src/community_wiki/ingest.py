"""Concurrent per-document ingestion with atomic replacement and content/config caching."""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .models import Chunk, Document
from .overviews import document_overview
from .pdf import PARSER_VERSION
from .store import dumps
from .text import read_document

log = logging.getLogger(__name__)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def embedding_signature(config):
    c = config.embedding
    return digest(
        dumps(
            {
                "base_url": c.base_url,
                "model": c.model,
                "dimensions": c.dimensions,
                "api_format": c.api_format,
            }
        )
    )


def ingestion_signature(config):
    return digest(
        dumps(
            {
                "overview": config.overview.model_dump(
                    exclude={"concurrency", "validation_retries"}
                ),
                "text": config.text.model_dump(exclude={"extensions"}),
                "pdf_parser_version": PARSER_VERSION,
                "model": config.model.model_dump(
                    exclude={
                        "timeout_seconds",
                        "concurrency",
                        "retries",
                        "retry_delay_seconds",
                    }
                ),
                "embedding": embedding_signature(config),
                "prompt": config.prompts.document.read_text(encoding="utf-8"),
            }
        )
    )


@dataclass
class IngestResult:
    inserted: int = 0
    unchanged: int = 0
    errors: dict[str, str] = field(default_factory=dict)


async def ingest(paths, config, store, client, text):
    files = set()
    for source in paths:
        path = Path(source).resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_dir():
            files.update(
                p
                for p in path.rglob("*")
                if p.is_file() and p.suffix.lower() in config.text.extensions
            )
        elif path.suffix.lower() in config.text.extensions:
            files.add(path)
        else:
            raise ValueError(f"Unsupported file type: {path}")
    if not files:
        raise ValueError("No supported documents found")
    signature = ingestion_signature(config)
    embed_signature = embedding_signature(config)
    if store.meta("embedding_signature") not in (None, embed_signature):
        raise ValueError("Embedding configuration changed; use a new database and rebuild")
    existing = {d.source: d for d in store.documents()}
    identities = store.allocate_document_ids([str(path) for path in sorted(files)])
    slots = asyncio.Semaphore(config.overview.concurrency)
    result = IngestResult()

    async def one(path):
        async with slots:
            try:
                content_hash = hashlib.sha256(await asyncio.to_thread(path.read_bytes)).hexdigest()
                doc_id = identities[str(path)]
                previous = existing.get(str(path))
                if (
                    previous
                    and previous.content_hash == content_hash
                    and previous.signature == signature
                ):
                    result.unchanged += 1
                    return
                content = await asyncio.to_thread(read_document, path, config.text.pdf)
                overview = await document_overview(content, config, text, client)
                pieces = text.split(
                    content, config.text.chunk_tokens, config.text.chunk_overlap_tokens
                )
                vectors = await client.embed([overview.embedding_text(), *pieces])
                document = Document(
                    doc_id, str(path), content_hash, signature, overview, vectors[0]
                )
                chunks = [
                    Chunk(doc_id, i, piece, vector)
                    for i, (piece, vector) in enumerate(zip(pieces, vectors[1:], strict=True))
                ]
                store.save_document(document, chunks, embed_signature)
                result.inserted += 1
                log.info("Ingested %s chunks=%s", path, len(chunks))
            except Exception as exc:
                result.errors[str(path)] = str(exc)
                log.exception("Document failed: %s", path)

    await asyncio.gather(*(one(path) for path in sorted(files)))
    return result
