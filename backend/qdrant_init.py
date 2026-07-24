"""
Qdrant collection bootstrap for the Hospital Clinical Knowledge Assistant.

Creates the `clinical_sops` collection with a HYBRID vector configuration:
  - "dense"  : 1024-dim cosine (BGE-M3 semantic embedding)
  - "sparse" : lexical BM25-style vector (exact keyword / acronym / dosage)

Run once against a fresh Qdrant instance before ingesting SOPs:

    python qdrant_init.py
"""
import os

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams, PayloadSchemaType,
)

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "clinical_sops")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "1024"))


def ensure_collection(client: QdrantClient) -> None:
    if client.collection_exists(QDRANT_COLLECTION):
        print(f"Collection '{QDRANT_COLLECTION}' already exists — skipping creation.")
        return
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config={"dense": VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)},
        sparse_vectors_config={"sparse": SparseVectorParams()},
    )
    for field_name, schema_type in [
        ("doc_id", PayloadSchemaType.KEYWORD),
        ("department", PayloadSchemaType.KEYWORD),
        ("is_active", PayloadSchemaType.BOOL),
    ]:
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION, field_name=field_name, field_schema=schema_type,
        )
    print(f"Created hybrid collection '{QDRANT_COLLECTION}' (dense={EMBEDDING_DIM} cosine + sparse).")


def main():
    ensure_collection(QdrantClient(url=QDRANT_URL))


if __name__ == "__main__":
    main()
