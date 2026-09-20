from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.rag.knowledge_base import KnowledgeBase, PolicyDocument


DEFAULT_TOP_K = 3
DEFAULT_THRESHOLD = 0.08


@dataclass
class RetrievedPolicy:
    policy_id: str
    title: str
    content: str
    source: str
    similarity_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "similarity_score": round(float(self.similarity_score), 6),
        }


class PolicyRetriever:
    def __init__(
        self,
        knowledge_base: KnowledgeBase | None = None,
        top_k: int = DEFAULT_TOP_K,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        self.kb = knowledge_base or KnowledgeBase()
        self.top_k = int(top_k)
        self.threshold = float(threshold)

        if self.kb.count() == 0:
            raise ValueError("Knowledge base has no policies; cannot build retriever.")

        self._documents = self.kb.all_documents()
        self._corpus = [doc.searchable_text() for doc in self._documents]

        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(self._corpus)

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> Dict[str, Any]:
        k = int(top_k) if top_k is not None else self.top_k
        thr = float(threshold) if threshold is not None else self.threshold

        if query is None:
            raise ValueError("query must be a string, got None")
        if not isinstance(query, str):
            raise ValueError("query must be a string")
        if not query.strip():
            return {"found": False, "results": []}

        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        if len(sims) == 0 or np.all(sims <= 0):
            return {"found": False, "results": []}

        ordered_idx = np.argsort(sims)[::-1]
        results: List[RetrievedPolicy] = []
        for rank_idx in ordered_idx:
            score = float(sims[rank_idx])
            if score < thr:
                continue
            doc: PolicyDocument = self._documents[int(rank_idx)]
            results.append(
                RetrievedPolicy(
                    policy_id=doc.policy_id,
                    title=doc.title,
                    content=doc.content,
                    source=doc.source,
                    similarity_score=score,
                )
            )
            if len(results) >= k:
                break

        if not results:
            return {"found": False, "results": []}

        return {
            "found": True,
            "results": [r.to_dict() for r in results],
        }
