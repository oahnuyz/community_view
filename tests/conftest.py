import asyncio
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from community_wiki.config import Config
from community_wiki.experiments import BenchmarkConfig
from community_wiki.store import Store
from community_wiki.text import TextProcessor

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def config(tmp_path):
    config = Config.load(ROOT / "config.yaml")
    config.keys_file = tmp_path / "keys.yaml"
    config.keys_file.write_text('chat_api_key: "test-only"\nembedding_api_key: "test-embedding"\n')
    config.storage.database = tmp_path / "index.sqlite3"
    config.storage.log_file = tmp_path / "test.log"
    config.embedding.dimensions = None
    config.embedding.api_format = "openai"
    config.graph.min_weight = 0.0
    config.community.max_documents = 2
    return config


@pytest.fixture
def store(config):
    store = Store(config.storage.database)
    yield store
    store.close()


@pytest.fixture
def text():
    return TextProcessor("cl100k_base", ROOT / "data" / "tokenizer_cache")


class FakeClient:
    def __init__(self):
        self.calls = []
        self.chat_calls = []
        self.active = 0
        self.peak = 0

    async def json_completion(self, system, payload, schema, retries, validate, purpose):
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.calls.append((purpose, payload))
        await asyncio.sleep(0.002)
        if purpose == "community_overview":
            result = {"name": "社区", "overview": "成员文档的简短总览"}
        elif payload["is_final"]:
            result = {
                "title": payload["content"][:12],
                "keywords": ["共同主题"],
                "summary": "全文摘要",
            }
        else:
            result = {"stage_summary": f"cumulative-{payload['fragment_index']}"}
        validate(result)
        self.active -= 1
        return result

    async def embed(self, texts):
        vectors = []
        for text in texts:
            vector = np.array(
                [1.0, text.count("alpha") + 0.1, text.count("beta") + 0.1], dtype=np.float32
            )
            vectors.append(vector / np.linalg.norm(vector))
        return vectors

    async def chat(self, messages, **kwargs):
        import json

        self.chat_calls.append((list(messages), kwargs))
        previous = [m for m in messages if m["role"] == "tool"]
        if len(previous) < 2 and not kwargs.get("force_final"):
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"call-{len(previous)}",
                        "type": "function",
                        "function": {
                            "name": "search_chunks",
                            "arguments": json.dumps(
                                {
                                    "query": "alpha",
                                    "search_mode": "keyword",
                                    "doc_ids": None,
                                }
                            ),
                        },
                    }
                ],
            }
        return {"role": "assistant", "content": "已根据检索上下文完成回答。"}


@pytest.fixture
def client():
    return FakeClient()


@pytest.fixture
def benchmark_settings(tmp_path, config):
    root = tmp_path / "prepared"
    (root / "corpus").mkdir(parents=True)
    documents = []
    for index, content in enumerate(["alpha research", "beta research"]):
        path = root / "corpus" / f"{index}.txt"
        path.write_text(content)
        documents.append(
            {
                "id": f"doc-{index}",
                "path": f"corpus/{index}.txt",
                "size_bytes": len(content.encode()),
                "sha256": hashlib.sha256(content.encode()).hexdigest(),
            }
        )
    questions = [
        {
            "id": identity,
            "question": f"alpha question {identity}",
            "document_ids": ["doc-0"],
            "gold_answers": ["GOLD_MUST_NOT_LEAK"],
            "evidence": ["EVIDENCE_MUST_NOT_LEAK"],
        }
        for identity in ["z", "a", "b"]
    ]
    for name, rows in [("qa.jsonl", questions), ("documents.jsonl", documents)]:
        (root / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
    (root / "dataset_info.json").write_text('{"dataset":"test"}')
    return BenchmarkConfig(
        dataset_dir=root,
        output_dir=tmp_path / "results",
        database=config.storage.database,
        log_file=config.storage.log_file,
        start=0,
        count=2,
        modes=["naive"],
        concurrency=2,
    )
