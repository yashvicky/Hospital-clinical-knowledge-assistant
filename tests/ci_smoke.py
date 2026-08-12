"""
CI smoke test: boots the real backend (main.app) with an in-process Qdrant
(HYBRID: dense + sparse) and in-process mock TEI/vLLM (called directly, no
network). Seeds SOPs, then asserts:
  - a matching query returns a grounded, cited answer (hybrid retrieval)
  - an off-topic query hits the low-confidence fallback (LLM bypassed)

No GPU, no Docker, no network. Exits non-zero on failure.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mocks"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

os.environ.setdefault("VLLM_MODEL_NAME", "mock-llama-3")

import main  # noqa: E402
import mock_tei  # noqa: E402
import mock_vllm  # noqa: E402
from sparse import sparse_encode  # noqa: E402
from metadata import build_doc_meta  # noqa: E402
from qdrant_client import AsyncQdrantClient, models  # noqa: E402
import httpx  # noqa: E402
from asgi_lifespan import LifespanManager  # noqa: E402

SOPS = [
    {"doc_id": "SOP-SEPSIS-2026", "page_number": 3, "department": "ER",
     "paragraph_text": "Sepsis 1-Hour Bundle: measure lactate, obtain blood cultures, administer broad-spectrum antibiotics, give crystalloid, apply vasopressors to maintain MAP >= 65 mmHg."},
    {"doc_id": "SOP-WARFARIN-2026", "page_number": 7, "department": "Pharmacy",
     "paragraph_text": "Ibuprofen with warfarin increases bleeding risk; prefer acetaminophen in anticoagulated patients."},
]


async def main_test():
    qc = AsyncQdrantClient(location=":memory:")
    await qc.create_collection(
        "clinical_sops",
        vectors_config={"dense": models.VectorParams(size=1024, distance=models.Distance.COSINE)},
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )
    pts = []
    for i, s in enumerate(SOPS, start=1):
        sp = sparse_encode(s["paragraph_text"])
        pts.append(models.PointStruct(
            id=i,
            vector={"dense": mock_tei.embed_text(s["paragraph_text"]),
                    "sparse": models.SparseVector(indices=sp["indices"], values=sp["values"])},
            payload={**s, "is_active": True, **build_doc_meta(approval_status="approved")}))
    await qc.upsert("clinical_sops", points=pts)

    async with LifespanManager(main.app):
        main.qdrant_client = qc

        class E:
            def __init__(self, v): self._v = v
            def raise_for_status(self): pass
            def json(self): return [self._v]

        async def fake_embed(path, json):
            return E(mock_tei.embed_text(json["inputs"][0]))
        main.embedding_client.post = fake_embed

        async def fake_create(**kw):
            sysmsg = next(m["content"] for m in kw["messages"] if m["role"] == "system")
            answer = mock_vllm.build_answer(sysmsg, "")
            class D:
                def __init__(s, c): s.content = c
            class Ch:
                def __init__(s, c): s.choices = [type("x", (), {"delta": D(c)})]
            async def gen():
                for w in answer.split(" "):
                    yield Ch(w + " ")
            return gen()
        main.llm_client.chat.completions.create = fake_create

        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            r1 = await c.post("/api/v1/query", json={"query": "1-hour sepsis protocol antibiotics lactate", "k_chunks": 5})
            assert r1.status_code == 200, r1.status_code
            assert "SOP-SEPSIS-2026" in r1.text, r1.text
            print("PASS hybrid high-confidence cited:", r1.headers.get("X-Retrieval-Confidence"), "sim", r1.headers.get("X-Top-Similarity"))

            r2 = await c.post("/api/v1/query", json={"query": "ibuprofen warfarin bleeding acetaminophen", "k_chunks": 5})
            assert "SOP-WARFARIN-2026" in r2.text, r2.text
            print("PASS hybrid second topic:", r2.text[:70], "...")

            r3 = await c.post("/api/v1/query", json={"query": "parking cafeteria visitor hours", "k_chunks": 5})
            assert "No matching clinical guideline found" in r3.text, r3.text
            print("PASS fallback:", r3.text)

    print("CI smoke test passed.")

asyncio.run(main_test())
