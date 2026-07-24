"""
One-shot bootstrap for local/dev runs: waits for Qdrant + the embedding
service, ensures the HYBRID collection exists, and seeds sample SOP chunks
(dense + sparse vectors) so the API returns real answers immediately.
Idempotent and safe to re-run.

    python bootstrap.py
"""
import os
import time

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector

from qdrant_init import ensure_collection
from sparse import sparse_encode

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "clinical_sops")
TEI_EMBEDDING_URL = os.environ.get("TEI_EMBEDDING_URL", "http://localhost:8080")

SAMPLE_SOPS = [
    {
        "doc_id": "SOP-SEPSIS-2026", "title": "Emergency Department Sepsis Management",
        "department": "ER", "page_number": 3,
        "paragraph_text": (
            "Sepsis 1-Hour Bundle: upon recognition of sepsis or septic shock, measure "
            "lactate, obtain blood cultures before antibiotics, administer broad-spectrum "
            "antibiotics, begin 30 mL/kg crystalloid for hypotension or lactate >= 4 mmol/L, "
            "and apply vasopressors to maintain MAP >= 65 mmHg."
        ),
    },
    {
        "doc_id": "SOP-WARFARIN-2026", "title": "Anticoagulation Drug Interactions",
        "department": "Pharmacy", "page_number": 7,
        "paragraph_text": (
            "Concurrent use of NSAIDs such as ibuprofen with warfarin increases bleeding risk "
            "due to additive antiplatelet effects and gastric irritation. Prefer acetaminophen "
            "for analgesia in anticoagulated patients."
        ),
    },
    {
        "doc_id": "SOP-ANAPHYLAXIS-2026", "title": "Anaphylaxis First-Line Management",
        "department": "ER", "page_number": 2,
        "paragraph_text": (
            "Anaphylaxis: administer intramuscular epinephrine 0.3-0.5 mg (1:1000) into the "
            "anterolateral thigh immediately, repeat every 5-15 minutes as needed, position the "
            "patient supine, give high-flow oxygen, and establish IV access for fluids."
        ),
    },
]


def _wait(fn, what, tries=40, delay=1.5):
    last = None
    for _ in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(delay)
    raise RuntimeError(f"timed out waiting for {what}: {last}")


def embed(client: httpx.Client, text: str) -> list[float]:
    r = client.post(f"{TEI_EMBEDDING_URL}/embed", json={"inputs": [text]}, timeout=30.0)
    r.raise_for_status()
    return r.json()[0]


def main():
    qc = _wait(lambda: (QdrantClient(url=QDRANT_URL).get_collections(), QdrantClient(url=QDRANT_URL))[1], "Qdrant")
    ensure_collection(qc)

    with httpx.Client() as hc:
        _wait(lambda: embed(hc, "healthcheck"), "embedding service")
        points = []
        for i, sop in enumerate(SAMPLE_SOPS, start=1):
            sp = sparse_encode(sop["paragraph_text"])
            points.append(PointStruct(
                id=i,
                vector={
                    "dense": embed(hc, sop["paragraph_text"]),
                    "sparse": SparseVector(indices=sp["indices"], values=sp["values"]),
                },
                payload={**sop, "is_active": True},
            ))
        qc.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"Seeded {len(SAMPLE_SOPS)} sample SOP chunks (dense + sparse). Bootstrap complete.")


if __name__ == "__main__":
    main()
