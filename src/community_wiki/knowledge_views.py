"""Question-vector lookup and selective reading of frozen community views."""

import json

import numpy as np

from .ingest import embedding_signature


class ViewReader:
    def __init__(self, config, store, client, retriever):
        self.config, self.client, self.retriever = config, client, retriever
        self.store = store
        self.views = {
            cid: {**json.loads(body), "signature": signature}
            for cid, signature, body in store.db.execute(
                "SELECT community_id,signature,body FROM knowledge_views WHERE graph_key=?",
                (retriever.graph_key,),
            )
        }
        self.entries = []
        for identity, view in self.views.items():
            if view["embedding_signature"] != embedding_signature(config):
                raise ValueError("View question embeddings changed; rebuild knowledge views")
        for identity, qid, question, vector in store.db.execute(
            "SELECT community_id,question_id,question,vector FROM knowledge_answers "
            "WHERE graph_key=? ORDER BY community_id,ordinal",
            (retriever.graph_key,),
        ):
            self.entries.append(
                (identity, {"question_id": qid, "question": question}, json.loads(vector))
            )

    async def catalog(self, question, state):
        if not self.entries:
            return {"view_catalog": []}
        vector = np.asarray((await self.client.embed([question]))[0])
        matrix = np.asarray([entry[2] for entry in self.entries])
        if matrix.shape[1] != len(vector):
            raise ValueError("View question embedding dimension does not match query")
        scores = matrix @ vector
        c = self.config.knowledge
        ranked = sorted(
            (
                i
                for i, score in enumerate(scores)
                if score > 0 and score >= c.min_question_similarity
            ),
            key=lambda i: (
                -float(scores[i]),
                self.entries[i][0],
                self.entries[i][1]["question_id"],
            ),
        )[: c.question_k]
        communities = list(dict.fromkeys(self.entries[i][0] for i in ranked))
        catalog = []
        for identity in communities:
            view = self.views[identity]
            questions = [entry for cid, entry, _ in self.entries if cid == identity]
            catalog.append({"community_id": identity, "name": view["name"], "questions": questions})
            state.offered_answers.update((identity, q["question_id"]) for q in questions)
            # The view directory displays this leaf; do not mark its overview as delivered.
        return {"view_catalog": catalog}

    def read(self, question_ids, state):
        if not question_ids or len(question_ids) > self.config.knowledge.read_answer_limit:
            raise ValueError("Invalid number of selected view answers")
        selected = list(dict.fromkeys(question_ids))
        offered = {qid: cid for cid, qid in state.offered_answers}
        if any(qid not in offered for qid in selected):
            raise ValueError("Select question_ids from the supplied view_catalog")
        keys = [(offered[qid], qid) for qid in selected]
        result = {"answers": [], "already_read": []}
        loaded = {}
        for cid, qid in keys:
            row = self.store.db.execute(
                "SELECT question,answer FROM knowledge_answers WHERE graph_key=? "
                "AND question_id=? AND signature=?",
                (self.retriever.graph_key, qid, self.views[cid]["signature"]),
            ).fetchone()
            if row is None:
                raise ValueError("View changed during this question; start a new question")
            loaded[qid] = row
        for key in keys:
            if key in state.seen_answers:
                result["already_read"].append(key[1])
            else:
                question, answer = loaded[key[1]]
                result["answers"].append(
                    {
                        "community_id": key[0],
                        "question_id": key[1],
                        "question": question,
                        "answer": answer,
                    }
                )
                state.seen_answers.add(key)
        return result
