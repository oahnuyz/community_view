"""Chunk retrieval followed by a fixed, question-scoped community expansion pipeline."""

from dataclasses import asdict
from functools import cached_property

import numpy as np
from rank_bm25 import BM25Okapi

from .ingest import embedding_signature
from .knowledge_store import graph_key
from .models import QuestionState, SearchHit
from .text import lexical_tokens


class Retriever:
    def __init__(self, config, store, client, mode=None):
        self.config, self.client = config, client
        self.mode = mode or config.retrieval.mode
        if self.mode not in ("naive", "community"):
            raise ValueError("Unknown retrieval mode")
        documents, self.chunks, self.edges, communities, revision, graph_revision = store.snapshot()
        if not documents or not self.chunks:
            raise ValueError("No indexed documents")
        if store.meta("embedding_signature") != embedding_signature(config):
            raise ValueError("Embedding configuration does not match stored index")
        if self.mode == "community" and str(revision) != graph_revision:
            raise ValueError("Community graph is missing or stale; run cluster after ingestion")
        self.documents = {d.doc_id: d for d in documents}
        self.communities = {c.community_id: c for c in communities}
        self.leaves = {
            doc_id: c.community_id for c in communities if c.is_leaf for doc_id in c.doc_ids
        }
        if self.mode == "community" and set(self.leaves) != set(self.documents):
            raise ValueError("Community leaves do not cover the indexed documents")
        self.incident = {doc_id: [] for doc_id in self.documents}
        for edge in self.edges:
            self.incident[edge.source].append((edge.target, edge.weight))
            self.incident[edge.target].append((edge.source, edge.weight))
        self.matrix = np.stack([c.vector for c in self.chunks])
        self.tokens = [lexical_tokens(c.text) for c in self.chunks]
        self.token_sets = [set(tokens) for tokens in self.tokens]
        c = config.retrieval
        self.bm25 = (
            BM25Okapi(self.tokens, k1=c.bm25_k1, b=c.bm25_b, epsilon=c.bm25_epsilon)
            if any(self.tokens)
            else None
        )

    @cached_property
    def graph_key(self):
        # Only knowledge recording/reading needs a content fingerprint of the graph.
        return graph_key(list(self.documents.values()), self.edges, list(self.communities.values()))

    async def search(self, query: str, state: QuestionState, *, search_mode=None, doc_ids=None):
        hits = await self.search_hits(query, search_mode=search_mode, doc_ids=doc_ids)
        return self.context(hits, state)

    async def search_hits(self, query: str, *, search_mode=None, doc_ids=None):
        """Retrieve without modifying question state; safe for concurrent tool calls."""
        if not query.strip():
            raise ValueError("Search query cannot be blank")
        c = self.config.retrieval
        search_mode = search_mode or c.search_mode
        if search_mode not in ("vector", "keyword", "hybrid"):
            raise ValueError("Unknown search mode")
        allowed = set(self.documents) if doc_ids is None else set(doc_ids)
        unknown = allowed - self.documents.keys()
        if unknown:
            raise ValueError("Unknown doc_ids; use IDs from retrieved document overviews")
        eligible = [i for i, chunk in enumerate(self.chunks) if chunk.doc_id in allowed]
        if not eligible:
            return []
        rankings = []
        size = max(c.fusion_candidates, c.chunk_k) if search_mode == "hybrid" else c.chunk_k
        if search_mode != "keyword":
            vector = (await self.client.embed([query]))[0]
            if len(vector) != self.matrix.shape[1]:
                raise ValueError("Query embedding dimension does not match index")
            scores = self.matrix @ vector
            indices = [i for i in eligible if scores[i] >= c.min_vector_similarity]
            indices.sort(
                key=lambda i: (-float(scores[i]), self.chunks[i].doc_id, self.chunks[i].ordinal)
            )
            rankings.append([(i, float(scores[i])) for i in indices[:size]])
        if search_mode != "vector":
            tokens = lexical_tokens(query)
            scores = self.bm25.get_scores(tokens) if self.bm25 else np.zeros(len(self.chunks))
            # Common terms can have zero/negative BM25 scores in tiny corpora; keep actual matches.
            indices = [i for i in eligible if self.token_sets[i].intersection(tokens)]
            indices.sort(
                key=lambda i: (-float(scores[i]), self.chunks[i].doc_id, self.chunks[i].ordinal)
            )
            rankings.append([(i, float(scores[i])) for i in indices[:size]])
        if search_mode == "hybrid":
            fused = {}
            for ranking in rankings:
                for rank, (i, _) in enumerate(ranking, 1):
                    fused[i] = fused.get(i, 0.0) + 1 / (c.rrf_constant + rank)
            ranking = sorted(
                fused.items(),
                key=lambda item: (
                    -item[1],
                    self.chunks[item[0]].doc_id,
                    self.chunks[item[0]].ordinal,
                ),
            )
        else:
            ranking = rankings[0]
        return [
            SearchHit(self.chunks[i].doc_id, self.chunks[i].ordinal, self.chunks[i].text, score)
            for i, score in ranking[: c.chunk_k]
        ]

    def read_chunks(self, doc_id, ordinals, state):
        return self.context(self.read_hits(doc_id, ordinals), state)

    def read_hits(self, doc_id, ordinals):
        if doc_id not in self.documents:
            raise ValueError("Unknown doc_id")
        if not ordinals or len(ordinals) > self.config.retrieval.read_chunk_limit:
            raise ValueError("Invalid number of chunk ordinals")
        by_ordinal = {c.ordinal: c for c in self.chunks if c.doc_id == doc_id}
        if not set(ordinals) <= by_ordinal.keys():
            raise ValueError("Unknown chunk ordinal")
        return [SearchHit(doc_id, i, by_ordinal[i].text, 1.0) for i in dict.fromkeys(ordinals)]

    def selected_communities(self, hits):
        selected = list(dict.fromkeys(hit.doc_id for hit in hits))[: self.config.retrieval.doc_k]
        selected_set = set(selected)
        result = [self.leaves[doc_id] for doc_id in selected]
        for doc_id in selected:
            eligible = [
                (other, weight)
                for other, weight in self.incident[doc_id]
                if other not in selected_set and self.leaves[other] != self.leaves[doc_id]
            ]
            if eligible:
                other, _ = min(eligible, key=lambda pair: (-pair[1], pair[0]))
                result.append(self.leaves[other])
        return list(dict.fromkeys(result))

    def context(self, hits, state):
        document_ids = list(dict.fromkeys(hit.doc_id for hit in hits))
        result = {"chunks": [asdict(hit) for hit in hits], "document_overviews": []}
        community_ids = []
        if self.mode == "community":
            # Select strongest incident edges before applying deduplication: no fallback to runner-up.
            community_ids = [
                i for i in self.selected_communities(hits) if i not in state.seen_communities
            ]
            result["communities"] = []
            for identity in community_ids:
                community = self.communities[identity]
                result["communities"].append(
                    {
                        "community_id": identity,
                        "name": community.name,
                        "overview": community.overview,
                        "doc_ids": community.doc_ids,
                    }
                )
                document_ids.extend(community.doc_ids)
        for doc_id in dict.fromkeys(document_ids):
            if doc_id not in state.seen_overviews:
                result["document_overviews"].append(
                    {
                        "doc_id": doc_id,
                        **self.documents[doc_id].overview.model_dump(exclude={"keywords"}),
                    }
                )
        state.seen_overviews.update(document_ids)
        state.seen_communities.update(community_ids)
        result["note"] = (
            "Document overviews and communities already delivered in this question are referenced by ID."
        )
        return result
