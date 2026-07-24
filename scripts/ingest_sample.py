"""
Seed a few sample clinical SOP chunks into Qdrant for a working demo (hybrid:
dense + sparse). Embeds via the (mock or real) TEI service and upserts with the
payload schema the backend reads. Run after qdrant_init.py once the stack is up.

    TEI_EMBEDDING_URL=http://localhost:8080 QDRANT_URL=http://localhost:6333 \
        python scripts/ingest_sample.py
"""
import os
import sys

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector

# reuse the backend's sparse encoder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from sparse import sparse_encode  # noqa: E402

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "clinical_sops")
TEI_EMBEDDING_URL = os.environ.get("TEI_EMBEDDING_URL", "http://localhost:8080")

SAMPLE_SOPS = [
    {"doc_id": "SOP-SEPSIS-2026", "title": "Emergency Department Sepsis Management",
     "department": "ER", "page_number": 3,
     "paragraph_text": "Sepsis 1-Hour Bundle: measure lactate, obtain blood cultures before antibiotics, administer broad-spectrum antibiotics, begin 30 mL/kg crystalloid for hypotension, and apply vasopressors to maintain MAP >= 65 mmHg."},
    {"doc_id": "SOP-WARFARIN-2026", "title": "Anticoagulation Drug Interactions",
     "department": "Pharmacy", "page_number": 7,
     "paragraph_text": "Concurrent use of NSAIDs such as ibuprofen with warfarin increases bleeding risk. Prefer acetaminophen for analgesia in anticoagulated patients."},
]


def embed(client: httpx.Client, text: str) -> list[float]:
    r = client.post(f"{TEI_EMBEDDING_URL}/embed", json={"inputs": [text]}, timeout=30.0)
    r.raise_for_status()
    return r.json()[0]


def main():
    client = QdrantClient(url=QDRANT_URL)
    points = []
    with httpx.Client() as hc:
        for i, sop in enumerate(SAMPLE_SOPS, start=1):
            sp = sparse_encode(sop["paragraph_text"])
            points.append(PointStruct(
                id=i,
                vector={"dense": embed(hc, sop["paragraph_text"]),
                        "sparse": SparseVector(indices=sp["indices"], values=sp["values"])},
                payload={**sop, "is_active": True},
            ))
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"Ingested {len(points)} sample SOP chunks (dense + sparse) into '{QDRANT_COLLECTION}'.")


if __name__ == "__main__":
    main()
