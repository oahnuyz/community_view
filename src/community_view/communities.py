"""Recursive Leiden partitioning with process-parallel branches and async descriptions."""

import asyncio
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

import igraph as ig
import leidenalg

from .community_ids import shorten_community_ids
from .community_split import split_community
from .graph import build_edges
from .ingest import digest
from .models import Community
from .overviews import describe_community
from .store import dumps

log = logging.getLogger(__name__)


def partition(doc_ids, edges, resolution, seed, iterations):
    """Picklable CPU task. Positive weighted RB modularity; no forced size constraints."""
    ids = sorted(doc_ids)
    indexes = {doc_id: i for i, doc_id in enumerate(ids)}
    local = [e for e in edges if e.source in indexes and e.target in indexes]
    if not local:
        return [[doc_id] for doc_id in ids]
    graph = ig.Graph(n=len(ids), edges=[(indexes[e.source], indexes[e.target]) for e in local])
    parts = leidenalg.find_partition(
        graph,
        leidenalg.RBConfigurationVertexPartition,
        weights=[e.weight for e in local],
        resolution_parameter=resolution,
        seed=seed,
        n_iterations=iterations,
    )
    return sorted([sorted(ids[i] for i in group) for group in parts], key=lambda group: group[0])


def graph_signature(config):
    # Disabled fallback preserves v2 graph compatibility, even without the new prompt file.
    community_config = config.community.model_dump(exclude={"llm_split_fallback"})
    optional = {}
    if config.community.llm_split_fallback:
        community_config["llm_split_fallback"] = True
        optional["split_prompt"] = config.prompts.community_split.read_text(encoding="utf-8")
    return digest(
        dumps(
            {
                "graph": config.graph.model_dump(),
                "community": community_config,
                "model": config.model.model_dump(),
                "prompt": config.prompts.community.read_text(encoding="utf-8"),
                **optional,
            }
        )
    )


async def build_communities(documents, edges, config, client, partitioner=None):
    c = config.community
    docs = {d.doc_id: d for d in documents}
    communities = []
    slots = asyncio.Semaphore(c.description_concurrency)
    pool = None
    if partitioner is None:
        pool = ProcessPoolExecutor(
            max_workers=c.cluster_workers, mp_context=multiprocessing.get_context("spawn")
        )

    async def split(ids):
        allowed = set(ids)
        local_edges = [e for e in edges if e.source in allowed and e.target in allowed]
        if partitioner is not None:
            groups = await partitioner(ids, local_edges)
        else:
            groups = await asyncio.get_running_loop().run_in_executor(
                pool, partition, ids, local_edges, c.resolution, c.seed, c.iterations
            )
        flattened = [item for group in groups for item in group]
        if not groups or any(not group for group in groups) or sorted(flattened) != sorted(ids):
            raise ValueError("Partition does not cover every document exactly once")
        return sorted([sorted(g) for g in groups], key=lambda g: g[0])

    async def branch(ids, parent_id, level, *, terminal=False):
        identity = digest(dumps({"parent": parent_id, "documents": sorted(ids)}))
        community = Community(identity, level, parent_id, sorted(ids))
        if terminal and len(ids) > c.max_documents:
            community.split_status = "llm_leaf_oversized"
            log.info(
                "LLM child retained as oversized leaf: id=%s documents=%s threshold=%s",
                identity,
                len(ids),
                c.max_documents,
            )
        communities.append(community)

        async def describe():
            async with slots:
                result = await describe_community(
                    [docs[i] for i in community.doc_ids], config, client
                )
                community.name, community.overview = result["name"], result["overview"]

        async def descendants():
            if terminal or len(ids) <= c.max_documents:
                return
            groups = await split(ids)
            llm_partition = False
            if len(groups) == 1:
                community.split_status = "unsplittable"
                if not c.llm_split_fallback:
                    log.warning(
                        "Community split failed: id=%s documents=%s threshold=%s; "
                        "Leiden returned one partition; retained as leaf",
                        identity,
                        len(ids),
                        c.max_documents,
                    )
                    return
                # Await this branch's description without holding an LLM semaphore slot.
                await description_task
                log.info(
                    "Leiden returned one partition; trying LLM split: id=%s documents=%s threshold=%s",
                    identity,
                    len(ids),
                    c.max_documents,
                )
                try:
                    async with slots:
                        groups = await split_community(
                            community, [docs[i] for i in community.doc_ids], config, client
                        )
                except Exception as exc:
                    # Cancellation still propagates. Only the optional split request is softened;
                    # Leiden errors and required community descriptions keep their normal semantics.
                    community.split_status = "llm_failed"
                    log.warning(
                        "LLM community split failed; retained as leaf: id=%s documents=%s error=%s: %s",
                        identity,
                        len(ids),
                        type(exc).__name__,
                        exc,
                    )
                    return
                if not groups:
                    community.split_status = "llm_declined"
                    log.info("LLM declined community split; retained as leaf: id=%s", identity)
                    return
                llm_partition = True
                log.info(
                    "LLM community split accepted: id=%s group_sizes=%s",
                    identity,
                    [len(group) for group in groups],
                )
            community.split_status = "llm_split" if llm_partition else "split"
            async with asyncio.TaskGroup() as tasks:
                children = [
                    tasks.create_task(branch(group, identity, level + 1, terminal=llm_partition))
                    for group in groups
                ]
            community.child_ids = [task.result() for task in children]

        async with asyncio.TaskGroup() as tasks:
            description_task = tasks.create_task(describe())
            tasks.create_task(descendants())
        return identity

    try:
        if documents:
            roots = await split(list(docs))
            async with asyncio.TaskGroup() as tasks:
                for ids in roots:
                    tasks.create_task(branch(ids, None, 0))
    finally:
        if pool is not None:
            await asyncio.to_thread(pool.shutdown, wait=True, cancel_futures=True)
    return sorted(communities, key=lambda item: (item.level, item.community_id))


async def cluster(config, store, client):
    documents, _, _, _, revision, _ = store.snapshot()
    if not documents:
        raise ValueError("No documents; ingest before clustering")
    edges = await asyncio.to_thread(build_edges, documents, config.graph)
    communities = await build_communities(documents, edges, config, client)
    communities, _ = shorten_community_ids(store, communities)
    store.publish_graph(
        edges, communities, revision, graph_signature(config), community_links(communities, edges)
    )
    log.info(
        "Published graph revision=%s edges=%s communities=%s",
        revision,
        len(edges),
        len(communities),
    )
    return {
        "revision": revision,
        "documents": len(documents),
        "edges": len(edges),
        "communities": len(communities),
        "leaves": sum(c.is_leaf for c in communities),
        "unsplittable": sum(
            c.split_status in {"unsplittable", "llm_declined", "llm_failed"} for c in communities
        ),
        "llm_splits": sum(c.split_status == "llm_split" for c in communities),
        "llm_oversized_leaves": sum(c.split_status == "llm_leaf_oversized" for c in communities),
    }


def community_links(communities, edges):
    """All same-level links plus cross-depth leaf links; no document edge is truncated."""
    memberships = {}
    for community in communities:
        for doc_id in community.doc_ids:
            memberships.setdefault(doc_id, []).append(community)
    links = {}
    for edge in edges:
        for left in memberships.get(edge.source, []):
            for right in memberships.get(edge.target, []):
                if left.community_id == right.community_id:
                    continue
                if left.level != right.level and not (left.is_leaf and right.is_leaf):
                    continue
                pair = tuple(sorted((left.community_id, right.community_id)))
                link = links.setdefault(
                    pair,
                    {
                        "source": pair[0],
                        "target": pair[1],
                        "weight_sum": 0.0,
                        "weight_max": 0.0,
                        "edges": [],
                    },
                )
                link["weight_sum"] += edge.weight
                link["weight_max"] = max(link["weight_max"], edge.weight)
                link["edges"].append(
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "weight": edge.weight,
                        "vector_score": edge.vector_score,
                        "keyword_score": edge.keyword_score,
                    }
                )
    return [links[pair] for pair in sorted(links)]
