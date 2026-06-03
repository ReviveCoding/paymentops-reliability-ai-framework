from __future__ import annotations
from src.rag.build_index import build_bm25_index


def retrieve_evidence(query: str, docs: list[dict], k: int = 3) -> list[dict]:
    return build_bm25_index(docs).retrieve(query, k=k)
