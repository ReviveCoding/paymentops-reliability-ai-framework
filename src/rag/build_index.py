from __future__ import annotations
from src.baselines.vanilla_bm25_rag import SimpleBM25


def build_bm25_index(docs: list[dict]) -> SimpleBM25:
    return SimpleBM25(docs)
