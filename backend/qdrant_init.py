"""
Qdrant collection bootstrap for the Hospital Clinical Knowledge Assistant.

Replaces the earlier PostgreSQL + pgvector schema.sql now that the finalized
tech stack uses Qdrant as the vector store. Run this once against a fresh
Qdrant instance (or whenever the collection needs to be recreated) before
ingesting any SOPs.

    python qdrant_init.py

Payload schema per point (matches the System Architecture Document's
"Vector Payload Data Schema" section):
    {
        "doc_id": "SOP-ER-2026-004",
        "title": "Emergency Department Sepsis Management",
        "category": "Hospital SOP",
        "version": "3.1",
        "section_title": "1-Hour Bundle Protocol",
        "page_number": 4,
        "paragraph_text": "...",
        "access_level": "clinical_staff",
        "department": "ER",
        "is_active": true
    }
"""
import os

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "clinical_sops")

# BGE-M3 dense output is 1024-dimensional (matches bge-large-en-v1.5).
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "1024"))


def main():
    client = QdrantClient(url=QDRANT_URL)

    if client.collection_exists(QDRANT_COLLECTION):
        print(f"Collection '{QDRANT_COLLECTION}' already exists — skipping creation.")
    else:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"Created collection '{QDRANT_COLLECTION}' (dim={EMBEDDING_DIM}, cosine distance).")

    # Payload indexes for hybrid filtering (e.g., filtering out outdated SOPs
    # or scoping to a department), mirroring the metadata columns from the
    # earlier pgvector schema.
    for field_name, schema_type in [
        ("doc_id", PayloadSchemaType.KEYWORD),
        ("department", PayloadSchemaType.KEYWORD),
        ("is_active", PayloadSchemaType.BOOL),
    ]:
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION,
            field_name=field_name,
            field_schema=schema_type,
        )
    print("Payload indexes created on: doc_id, department, is_active.")


if __name__ == "__main__":
    main()
