"""
Seed a few sample clinical SOP chunks into Qdrant for a working demo.

Embeds each chunk via the (mock or real) TEI service and upserts it into the
`clinical_sops` collection with the payload schema the backend reads. Run this
after qdrant_init.py once the stack is up.

    TEI_EMBEDDING_URL=http://localhost:8080 QDRANT_URL=http://localhost:6333 \
        python scripts/ingest_sample.py
"""
import os
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "clinical_sops")
TEI_EMBEDDING_URL = os.environ.get("TEI_EMBEDDING_URL", "http://localhost:8080")

SAMPLE_SOPS = [
    {
        "doc_id": "SOP-SEPSIS-2026",
        "title": "Emergency Department Sepsis Management",
        "department": "ER",
        "page_number": 3,
        "paragraph_text": (
            "Sepsis 1-Hour Bundle: upon recognition of sepsis or septic shock, "
            "measure lactate, obtain blood cultures before antibiotics, administer "
            "broad-spectrum antibiotics, begin 30 mL/kg crystalloid for hypotension "
            "or lactate >= 4 mmol/L, and apply vasopressors to maintain MAP >= 65 mmHg."
        ),
    },
    {
        "doc_id": "SOP-WARFARIN-2026",
        "title": "Anticoagulation Drug Interactions",
        "department": "Pharmacy",
        "page_number": 7,
        "paragraph_text": (
            "Concurrent use of NSAIDs such as ibuprofen with warfarin increases "
            "bleeding risk due to additive antiplatelet effects and gastric irritation. "
            "Prefer acetaminophen for analgesia in anticoagulated patients."
        ),
    },
]


def embed(text: str) -> list[float]:
    r = httpx.post(f"{TEI_EMBEDDING_URL}/embed", json={"inputs": [text]}, timeout=30.0)
    r.raise_for_status()
    return r.json()[0]


def main():
    client = QdrantClient(url=QDRANT_URL)
    points = []
    for i, sop in enumerate(SAMPLE_SOPS, start=1):
        vec = embed(sop["paragraph_text"])
        points.append(PointStruct(id=i, vector=vec, payload={**sop, "is_active": True}))
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"Ingested {len(points)} sample SOP chunks into '{QDRANT_COLLECTION}'.")


if __name__ == "__main__":
    main()
