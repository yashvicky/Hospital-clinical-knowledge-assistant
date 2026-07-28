"""
One-shot bootstrap for local/dev runs: waits for Qdrant + the embedding
service, ensures the HYBRID collection exists, and seeds sample SOP chunks
(dense + sparse) so the API returns real answers immediately. Idempotent.

    python bootstrap.py
"""
import os
import time

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector

from qdrant_init import ensure_collection
from sparse import sparse_encode
from embedding import embed_sync

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "clinical_sops")
TEI_EMBEDDING_URL = os.environ.get("TEI_EMBEDDING_URL", "http://localhost:8080")

from seed_corpus import DOCUMENTS as SAMPLE_SOPS


def _wait(fn, what, tries=60, delay=2.0):
    last = None
    for _ in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(delay)
    raise RuntimeError(f"timed out waiting for {what}: {last}")


def main():
    qc = _wait(lambda: (QdrantClient(url=QDRANT_URL).get_collections(), QdrantClient(url=QDRANT_URL))[1], "Qdrant")
    ensure_collection(qc)

    with httpx.Client(base_url=TEI_EMBEDDING_URL, timeout=120.0) as hc:
        _wait(lambda: embed_sync(hc, ["healthcheck"]), "embedding service")
        points = []
        for i, sop in enumerate(SAMPLE_SOPS, start=1):
            vec = embed_sync(hc, [sop["paragraph_text"]])[0]
            sp = sparse_encode(sop["paragraph_text"])
            points.append(PointStruct(
                id=i,
                vector={"dense": vec, "sparse": SparseVector(indices=sp["indices"], values=sp["values"])},
                payload={**sop, "is_active": True},
            ))
        qc.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"Seeded {len(SAMPLE_SOPS)} sample SOP chunks (dense + sparse). Bootstrap complete.")


if __name__ == "__main__":
    main()
