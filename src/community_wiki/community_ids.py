"""Deterministic short names for a graph, preserving its hierarchy and descriptions."""

from dataclasses import replace

from .ingest import digest
from .store import dumps


def shorten_community_ids(store, communities):
    # Reconstruct the same structural fingerprints whether input IDs are hashes or C0001.
    ordered = sorted(communities, key=lambda c: (c.level, sorted(c.doc_ids)))
    fingerprints = {}
    for community in ordered:
        fingerprints[community.community_id] = digest(
            dumps(
                {
                    "parent": fingerprints[community.parent_id] if community.parent_id else None,
                    "documents": sorted(community.doc_ids),
                }
            )
        )
    allocated = store.allocate_community_ids(list(fingerprints.values()))
    mapping = {old: allocated[value] for old, value in fingerprints.items()}
    return [
        replace(
            c,
            community_id=mapping[c.community_id],
            parent_id=mapping[c.parent_id] if c.parent_id else None,
            child_ids=[mapping[child] for child in c.child_ids],
        )
        for c in ordered
    ], mapping


def remap_community_links(links, mapping):
    result = []
    for link in links:
        source, target = sorted((mapping[link["source"]], mapping[link["target"]]))
        result.append({**link, "source": source, "target": target})
    return result
