"""Lightweight FAQ retrieval using TF-IDF + cosine similarity.

No embeddings API required - keeps the POC dependency-light while still doing
real semantic-ish retrieval over the FAQ corpus.
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.db import get_session
from app.models import Faq


@dataclass
class FAQHit:
    topic: str
    question: str
    answer: str
    score: float


class FAQIndex:
    def __init__(self) -> None:
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._faqs: list[FAQHit] = []

    def build(self) -> "FAQIndex":
        with get_session() as db:
            rows = db.query(Faq).all()
            self._faqs = [
                FAQHit(topic=r.topic, question=r.question, answer=r.answer, score=0.0)
                for r in rows
            ]
        if not self._faqs:
            self._vectorizer = None
            self._matrix = None
            return self
        corpus = [f"{f.topic} {f.question} {f.answer}" for f in self._faqs]
        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self._matrix = self._vectorizer.fit_transform(corpus)
        return self

    def search(self, query: str, top_k: int = 3, min_score: float = 0.05) -> list[FAQHit]:
        if not self._vectorizer or self._matrix is None or not query.strip():
            return []
        q_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._matrix)[0]
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        hits: list[FAQHit] = []
        for i in ranked:
            if scores[i] >= min_score:
                f = self._faqs[i]
                hits.append(FAQHit(topic=f.topic, question=f.question, answer=f.answer, score=float(scores[i])))
        return hits


_index: FAQIndex | None = None


def get_index() -> FAQIndex:
    global _index
    if _index is None:
        _index = FAQIndex().build()
    return _index


def refresh_index() -> FAQIndex:
    global _index
    _index = FAQIndex().build()
    return _index
