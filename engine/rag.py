import json
import os
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from .normalize import normalize_arabic

log = logging.getLogger("ppu.rag")

_INDEX = None
_CHUNKS = None
_MODEL = None

INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "faiss_index.bin")
CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ppu_chunks.json")


def _load():
    global _INDEX, _CHUNKS, _MODEL
    if _INDEX is not None:
        return
    if not os.path.exists(INDEX_PATH) or not os.path.exists(CHUNKS_PATH):
        log.warning("FAISS index or chunks not found. Run preload/build_index.py first.")
        _INDEX = False
        return
    import faiss
    _INDEX = faiss.read_index(INDEX_PATH)
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        _CHUNKS = json.load(f)
    _MODEL = SentenceTransformer("intfloat/multilingual-e5-small")
    log.info("RAG loaded: %d chunks", len(_CHUNKS))


def search(query: str, top_k: int = 3) -> list[dict]:
    _load()
    if _INDEX is False or _CHUNKS is None:
        return []

    q_emb = _MODEL.encode("query: " + normalize_arabic(query), normalize_embeddings=True)
    q_emb = np.expand_dims(q_emb, axis=0).astype(np.float32)

    scores, indices = _INDEX.search(q_emb, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(_CHUNKS):
            continue
        chunk = _CHUNKS[idx]
        results.append({
            "text": chunk["text"],
            "url": chunk.get("url", ""),
            "title": chunk.get("title", ""),
            "score": float(score),
        })
    return results
