from __future__ import annotations

import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def cosine_similarity_matrix(query: list[float], matrix: list[list[float]]) -> list[float]:
    """Vectorized cosine similarity of one query against many vectors —
    used by the numpy vector index backend for the POC (see
    app/retrieval/vector_index.py)."""
    if not matrix:
        return []
    q = np.asarray(query, dtype=np.float32)
    m = np.asarray(matrix, dtype=np.float32)
    q_norm = np.linalg.norm(q)
    m_norms = np.linalg.norm(m, axis=1)
    denom = q_norm * m_norms
    denom[denom == 0] = 1e-9
    sims = (m @ q) / denom
    return sims.tolist()
