import asyncio

import numpy as np
import pytest

from community_wiki.communities import build_communities, community_links, partition
from community_wiki.graph import build_edges
from community_wiki.models import Community, Document, Edge, Overview


def doc(identity, vector, keywords):
    vector = np.asarray(vector, dtype=np.float32)
    vector /= np.linalg.norm(vector)
    return Document(
        identity,
        identity,
        "hash",
        "signature",
        Overview(title=identity, summary=identity, keywords=keywords),
        vector,
    )


@pytest.mark.parametrize(
    "mode,expected",
    [("vector", {("a", "b")}), ("keyword", {("a", "c")}), ("hybrid", {("a", "b"), ("a", "c")})],
)
def test_candidate_union_and_modes(config, mode, expected):
    config.graph.mode = mode
    config.graph.neighbor_k = 1
    docs = [
        doc("a", [1, 0, 0], [" ML "]),
        doc("b", [1, 0, 0], ["other"]),
        doc("c", [0, 1, 0], ["ml"]),
    ]
    edges = build_edges(docs, config.graph)
    assert {(e.source, e.target) for e in edges} == expected
    if mode == "hybrid":
        assert [e.weight for e in edges] == pytest.approx([0.7, 0.3])
    assert all(e.weight > 0 for e in edges)


def test_no_zero_or_negative_edges(config):
    config.graph.mode = "vector"
    docs = [doc("a", [1, 0], ["x"]), doc("b", [-1, 0], ["y"])]
    assert build_edges(docs, config.graph) == []


def test_real_leiden_isolates_and_complete_graph():
    edges = [Edge("a", "b", 0.8, 0.8, None)]
    assert partition(["a", "b", "c"], edges, 1, 42, -1) == [["a", "b"], ["c"]]
    assert partition(["z"], [], 1, 42, -1) == [["z"]]


async def test_recursive_concurrency_all_document_overviews(config, client, caplog):
    config.community.max_documents = 1
    docs = [doc(str(i), [1, 0], ["topic"]) for i in range(8)]
    active, peak = 0, 0

    async def splitter(ids, edges):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        if len(ids) >= 4:
            return [ids[: len(ids) // 2], ids[len(ids) // 2 :]]
        return [ids]

    communities = await build_communities(docs, [], config, client, splitter)
    assert len(communities) == 6
    roots = [c for c in communities if c.parent_id is None]
    assert len(roots) == 2
    assert all(len(c.doc_ids) == 4 and len(c.child_ids) == 2 for c in roots)
    assert sum(c.split_status == "unsplittable" for c in communities) == 4
    assert "split failed" in caplog.text
    assert peak >= 2 and client.peak >= 2
    assert sorted(len(p["document_overviews"]) for _, p in client.calls) == [2, 2, 2, 2, 4, 4]
    leaves = [c for c in communities if c.is_leaf]
    assert sorted(d for c in leaves for d in c.doc_ids) == [str(i) for i in range(8)]


def test_all_cross_edges_retained_for_links():
    communities = [
        Community("p", 0, None, ["a", "b"], ["a", "b"]),
        Community("a", 1, "p", ["a"]),
        Community("b", 1, "p", ["b"]),
        Community("c", 0, None, ["c"]),
    ]
    edges = [Edge("a", "c", 0.8, 0.8, None), Edge("b", "c", 0.7, 0.7, None)]
    links = community_links(communities, edges)
    parent = next(link for link in links if {link["source"], link["target"]} == {"p", "c"})
    assert len(parent["edges"]) == 2
    assert parent["weight_sum"] == 1.5
    assert len(links) == 3
