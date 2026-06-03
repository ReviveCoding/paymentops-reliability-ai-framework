from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class SimpleBM25:
    def __init__(self, docs: list[dict], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(d.get("content", "") + " " + d.get("title", "")) for d in docs]
        self.avgdl = sum(len(t) for t in self.doc_tokens) / max(1, len(self.doc_tokens))
        self.df = defaultdict(int)
        for toks in self.doc_tokens:
            for tok in set(toks):
                self.df[tok] += 1

    def score(self, query: str, idx: int) -> float:
        toks = self.doc_tokens[idx]
        counts = Counter(toks)
        q = tokenize(query)
        score = 0.0
        N = len(self.docs)
        for term in q:
            if term not in self.df:
                continue
            idf = math.log(1 + (N - self.df[term] + 0.5) / (self.df[term] + 0.5))
            tf = counts[term]
            denom = tf + self.k1 * (1 - self.b + self.b * len(toks) / (self.avgdl or 1))
            score += idf * (tf * (self.k1 + 1) / (denom or 1))
        return score

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        scored = [(self.score(query, i), self.docs[i]) for i in range(len(self.docs))]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{**d, "score": s} for s, d in scored[:k]]
