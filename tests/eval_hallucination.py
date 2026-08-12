"""
Hallucination / grounding evaluation harness.

Framework for the PRD acceptance criterion "0% hallucination rate on a
standardized test suite of clinical queries". Runs a labeled set through the
real backend (in-process Qdrant hybrid + mock TEI/vLLM, no GPU) and scores:

  - GROUNDING: every [Doc: X, Page: Y] citation in an answer must reference a
    doc_id that exists in the knowledge base (no fabricated sources).
  - CORRECTNESS: in-topic queries must cite the expected doc_id.
  - REFUSAL: off-topic queries must return the "not found" fallback (no answer).

Exit code is non-zero if any check fails. With the deterministic mocks this
runs at 100%; point TEI/vLLM at the real BGE-M3 + Llama 3 for a meaningful
hallucination number over a larger suite.
"""
import asyncio
import os
import re
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

CORPUS = [
    {"doc_id": "SOP-SEPSIS-2026", "page_number": 3, "department": "ER",
     "paragraph_text": "Sepsis 1-Hour Bundle: measure lactate, obtain blood cultures, administer broad-spectrum antibiotics, give crystalloid, apply vasopressors to maintain MAP >= 65 mmHg."},
    {"doc_id": "SOP-WARFARIN-2026", "page_number": 7, "department": "Pharmacy",
     "paragraph_text": "Ibuprofen and other NSAIDs with warfarin increase bleeding risk; prefer acetaminophen in anticoagulated patients."},
    {"doc_id": "SOP-ANAPHYLAXIS-2026", "page_number": 2, "department": "ER",
     "paragraph_text": "Anaphylaxis: give intramuscular epinephrine 0.3-0.5 mg in the anterolateral thigh, repeat every 5-15 minutes, high-flow oxygen, IV access."},
]
KNOWN_IDS = {c["doc_id"] for c in CORPUS}

# (query, expected_doc_id or None for off-topic)
CASES = [
    ("what is the 1-hour sepsis bundle antibiotics and lactate", "SOP-SEPSIS-2026"),
    ("sepsis tx vasopressors MAP target", "SOP-SEPSIS-2026"),
    ("can ibuprofen be given with warfarin", "SOP-WARFARIN-2026"),
    ("nsaid anticoagulation bleeding risk acetaminophen", "SOP-WARFARIN-2026"),
    ("epinephrine dose for anaphylaxis intramuscular", "SOP-ANAPHYLAXIS-2026"),
    ("anaphylaxis first line management oxygen", "SOP-ANAPHYLAXIS-2026"),
    ("visitor parking hours and cafeteria menu", None),
    ("how do I reset my email password", None),
    ("what time does the gift shop close", None),
]

CITE_RE = re.compile(r"\[Doc:\s*([^,]+),\s*Page:\s*(\d+)\]")


async def run():
    qc = AsyncQdrantClient(location=":memory:")
    await qc.create_collection(
        "clinical_sops",
        vectors_config={"dense": models.VectorParams(size=1024, distance=models.Distance.COSINE)},
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )
    pts = []
    for i, c in enumerate(CORPUS, start=1):
        sp = sparse_encode(c["paragraph_text"])
        pts.append(models.PointStruct(id=i, vector={
            "dense": mock_tei.embed_text(c["paragraph_text"]),
            "sparse": models.SparseVector(indices=sp["indices"], values=sp["values"]),
        }, payload={**c, "is_active": True, **build_doc_meta(approval_status="approved")}))
    await qc.upsert("clinical_sops", points=pts)

    async with LifespanManager(main.app):
        main.qdrant_client = qc

        class E:
            def __init__(s, v): s._v = v
            def raise_for_status(s): pass
            def json(s): return [s._v]
        async def femb(path, json): return E(mock_tei.embed_text(json["inputs"][0]))
        main.embedding_client.post = femb

        async def fcreate(**kw):
            sysmsg = next(m["content"] for m in kw["messages"] if m["role"] == "system")
            ans = mock_vllm.build_answer(sysmsg, "")
            class D:
                def __init__(s, c): s.content = c
            class Ch:
                def __init__(s, c): s.choices = [type("x", (), {"delta": D(c)})]
            async def g():
                for w in ans.split(" "):
                    yield Ch(w + " ")
            return g()
        main.llm_client.chat.completions.create = fcreate

        tr = httpx.ASGITransport(app=main.app)
        passed = 0
        fabricated = 0
        async with httpx.AsyncClient(transport=tr, base_url="http://t") as client:
            for q, expected in CASES:
                r = await client.post("/api/v1/query", json={"query": q, "k_chunks": 5})
                text = r.text
                cites = CITE_RE.findall(text)
                cited_ids = {c[0].strip() for c in cites}
                # grounding: no fabricated doc ids
                fabricated_here = cited_ids - KNOWN_IDS
                if fabricated_here:
                    fabricated += 1

                if expected is None:
                    ok = ("No matching clinical guideline found" in text) and not cited_ids
                else:
                    ok = (expected in cited_ids) and not fabricated_here
                passed += int(ok)
                tag = "PASS" if ok else "FAIL"
                exp = expected or "REFUSE"
                print(f"[{tag}] expected={exp:<20} cited={sorted(cited_ids) or '-'}  q='{q[:42]}'")

        total = len(CASES)
        print(f"\nGrounding: {total - fabricated}/{total} answers with zero fabricated citations")
        print(f"Suite:     {passed}/{total} cases passed")
        hallucination_rate = fabricated / total * 100
        print(f"Fabricated-citation (hallucination) rate: {hallucination_rate:.1f}%")
        assert passed == total, f"{total - passed} case(s) failed"
        assert fabricated == 0, "fabricated citations detected"
        print("Eval passed.")

asyncio.run(run())
