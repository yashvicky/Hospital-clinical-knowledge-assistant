"""
Integration harness: serves the REAL backend (main.app) over real HTTP via
uvicorn, wired to the REAL mock TEI and mock vLLM services over real HTTP.

Qdrant runs in-process (qdrant-client local engine, same API surface) because
a standalone Qdrant server binary can't be downloaded in this sandbox. It is
seeded by embedding sample SOPs through the REAL mock TEI over HTTP, so the
retrieval scores are produced by the same embedding path the query uses.
"""
import os
from contextlib import asynccontextmanager

os.environ.setdefault("TEI_EMBEDDING_URL", "http://localhost:8080")
os.environ.setdefault("VLLM_BASE_URL", "http://localhost:8001/v1")
os.environ.setdefault("VLLM_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

import main

SAMPLE_SOPS = [
    {
        "doc_id": "SOP-SEPSIS-2026", "title": "ED Sepsis Management", "department": "ER",
        "page_number": 3,
        "paragraph_text": (
            "Sepsis 1-Hour Bundle: upon recognition of sepsis or septic shock, measure "
            "lactate, obtain blood cultures before antibiotics, administer broad-spectrum "
            "antibiotics, begin 30 mL/kg crystalloid for hypotension, and apply vasopressors "
            "to maintain MAP greater than or equal to 65 mmHg."
        ),
    },
    {
        "doc_id": "SOP-WARFARIN-2026", "title": "Anticoagulation Interactions", "department": "Pharmacy",
        "page_number": 7,
        "paragraph_text": (
            "Concurrent use of NSAIDs such as ibuprofen with warfarin increases bleeding risk. "
            "Prefer acetaminophen for analgesia in anticoagulated patients."
        ),
    },
]

_orig_lifespan = main.app.router.lifespan_context


@asynccontextmanager
async def seeded_lifespan(app):
    async with _orig_lifespan(app):
        local = AsyncQdrantClient(location=":memory:")
        await local.create_collection(
            collection_name=main.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
        async with httpx.AsyncClient(base_url=os.environ["TEI_EMBEDDING_URL"], timeout=30.0) as c:
            points = []
            for i, sop in enumerate(SAMPLE_SOPS, start=1):
                r = await c.post("/embed", json={"inputs": [sop["paragraph_text"]]})
                r.raise_for_status()
                vec = r.json()[0]
                points.append(PointStruct(id=i, vector=vec, payload={**sop, "is_active": True}))
            await local.upsert(collection_name=main.QDRANT_COLLECTION, points=points)
        # swap the real-server client for our seeded in-process one
        main.qdrant_client = local
        print("[harness] seeded in-process Qdrant with", len(SAMPLE_SOPS), "SOP chunks", flush=True)
        yield


main.app.router.lifespan_context = seeded_lifespan
app = main.app
