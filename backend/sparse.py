"""
Lexical sparse encoder for hybrid retrieval.

The dense vector (semantic meaning) comes from the embedding model (BGE-M3 via
TEI). This module produces the complementary *sparse* vector — a hashed,
BM25-style bag-of-words — that captures exact keyword / acronym / drug-dosage
matches the dense model can smear over. Qdrant fuses the two with Reciprocal
Rank Fusion.

Deterministic and dependency-free, so ingestion and query time stay aligned.
(To use BGE-M3's *learned* sparse output instead, point `sparse_encode` at a
TEI sparse-embeddings endpoint — the Qdrant plumbing is identical.)
"""
import math
import re
from collections import Counter

_token_re = re.compile(r"[a-z0-9]+")
SPARSE_DIM = 1 << 20  # 1,048,576 hashed term buckets


def sparse_encode(text: str) -> dict:
    """Return a Qdrant-style sparse vector: {'indices': [...], 'values': [...]}."""
    counts: Counter = Counter()
    for tok in _token_re.findall(text.lower()):
        h = 0
        for ch in tok:
            h = (h * 131 + ord(ch)) & 0xFFFFFFFF
        counts[h % SPARSE_DIM] += 1
    indices = list(counts.keys())
    values = [1.0 + math.log(counts[i]) for i in indices]  # sublinear tf
    return {"indices": indices, "values": values}
