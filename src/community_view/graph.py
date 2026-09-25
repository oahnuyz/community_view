"""Sparse candidate graph over documents; retain every accepted undirected edge."""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .models import Edge


def normalize_keyword(value):
    return " ".join(value.casefold().split())


def build_edges(documents, config):
    if len(documents) < 2:
        return []
    documents = sorted(documents, key=lambda d: d.doc_id)
    vectors = None
    if config.mode != "keyword":
        vectors = np.stack([d.vector for d in documents])
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    keywords = None
    if config.mode != "vector":
        keywords = TfidfVectorizer(
            analyzer=lambda words: sorted({normalize_keyword(w) for w in words}),
            norm="l2",
            smooth_idf=True,
        ).fit_transform([d.overview.keywords for d in documents])
    candidates = set()
    scores = {}
    for i, document in enumerate(documents):
        vector_row = np.clip(vectors @ vectors[i], 0, 1) if vectors is not None else None
        keyword_row = (keywords @ keywords[i].T).toarray().ravel() if keywords is not None else None
        neighbors = set()
        for row in (vector_row, keyword_row):
            if row is not None:
                eligible = [j for j in range(len(documents)) if j != i and row[j] > 0]
                eligible.sort(key=lambda j: (-float(row[j]), documents[j].doc_id))
                neighbors.update(eligible[: config.neighbor_k])
        for j in neighbors:
            pair = (min(i, j), max(i, j))
            if pair in candidates:
                continue
            candidates.add(pair)
            v = float(vector_row[j]) if vector_row is not None else None
            k = float(np.clip(keyword_row[j], 0, 1)) if keyword_row is not None else None
            weight = (
                v
                if config.mode == "vector"
                else k
                if config.mode == "keyword"
                else (config.vector_weight * v + (1 - config.vector_weight) * k)
            )
            if weight > 0 and weight >= config.min_weight:
                scores[pair] = Edge(
                    documents[pair[0]].doc_id, documents[pair[1]].doc_id, weight, v, k
                )
    return [scores[pair] for pair in sorted(scores)]
