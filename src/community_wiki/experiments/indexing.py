"""Separately executable document ingestion and community construction stages."""

import json
import time

from ..communities import cluster, graph_signature
from ..ingest import ingest
from ..metrics import measure
from .dataset import verify_index, write_json

COST_FIELDS = (
    "elapsed_seconds",
    "llm_input_tokens",
    "llm_output_tokens",
    "llm_total_tokens",
    "embedding_tokens",
    "total_tokens",
)


async def index(dataset, settings, config, store, client, text, stage="index"):
    if stage not in {"ingest", "cluster", "index"}:
        raise ValueError("Expected ingest, cluster or index")
    path = settings.output_dir / "indexing_metrics.json"
    previous = json.loads(path.read_text()) if path.exists() else {}
    if previous and "stages" not in previous:
        raise ValueError(
            "Legacy indexing metrics lack stage breakdown; use a new experiment directory"
        )
    stages = previous.get("stages", {})
    required = ["documents"] if stage in {"ingest", "index"} else []
    if stage == "cluster" or (stage == "index" and "community" in settings.modes):
        required.append("communities")

    def save():
        result = {
            "status": "failed"
            if any(s["status"] == "failed" for s in stages.values())
            else "complete",
            "document_count": len(dataset.documents),
            "stages": stages,
        }
        for field in COST_FIELDS:
            result[field] = sum(value[field] for value in stages.values())
        write_json(path, result)
        return result

    for name in required:
        started = time.monotonic()
        result = {"status": "complete"}
        with measure(f"indexing:{name}") as totals:
            try:
                if name == "documents":
                    ingested = await ingest(dataset.paths, config, store, client, text)
                    if ingested.errors:
                        raise ValueError(
                            f"{len(ingested.errors)} document(s) failed; inspect {settings.log_file}"
                        )
                else:
                    verify_index(dataset, config, store, complete=True)
                    if store.meta("graph_revision") != str(store.revision) or store.meta(
                        "graph_signature"
                    ) != graph_signature(config):
                        await cluster(config, store, client)
            except BaseException:
                result["status"] = "failed"
                raise
            finally:
                result.update(totals.as_dict())
                result.pop("rounds")
                result["elapsed_seconds"] = time.monotonic() - started
                if name in stages:
                    for field in COST_FIELDS:
                        result[field] += stages[name][field]
                stages[name] = result
                save()
    return save()
