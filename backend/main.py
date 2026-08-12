"""
Hospital Clinical Knowledge Assistant — FastAPI Backend
BMAD Phase 4: Core Backend Implementation (Finalized Production Stack)

Self-hosted hybrid RAG pipeline:
  - PHI redaction + medical shorthand expansion on the incoming query
  - Query embedding: BGE-M3 (dense) via a self-hosted TEI container
  - Sparse encoding:  lexical BM25-style vector for exact keyword/dosage matches
  - Vector search:    Qdrant HYBRID (dense + sparse, Reciprocal Rank Fusion)
  - Generation:       Llama 3 via vLLM's OpenAI-compatible streaming API

Guardrails (from the PRD). The confidence gate uses the top DENSE cosine
similarity; hybrid RRF only decides chunk ordering:
  - dense cosine >= 0.82         -> Confidence: High
  - 0.65 <= dense cosine < 0.82  -> Confidence: Moderate
  - dense cosine < 0.65          -> bypass the LLM, return the fixed "not found"
"""

import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException, Header, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient, models

from sparse import sparse_encode
from embedding import embed_async
from phi import redact_phi
from normalize import expand_shorthand
from chunking import build_chunks
from metadata import build_doc_meta, now_ts

# ---------------------------------------------------------
# 1. Config & Global Clients
# ---------------------------------------------------------
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "clinical_sops")
TEI_EMBEDDING_URL = os.environ.get("TEI_EMBEDDING_URL", "http://localhost:8080")
VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL_NAME = os.environ.get("VLLM_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")

HIGH_CONF = float(os.environ.get("CONF_HIGH", "0.82"))
MIN_CONF = float(os.environ.get("CONF_MIN", "0.65"))

# Optional bearer-token auth. If API_KEY is unset (default), auth is disabled
# so the local dev stack works out of the box.
API_KEY = os.environ.get("API_KEY", "").strip()
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
_ID_NS = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")

qdrant_client: AsyncQdrantClient = None
embedding_client: httpx.AsyncClient = None
llm_client: AsyncOpenAI = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global qdrant_client, embedding_client, llm_client
    qdrant_client = AsyncQdrantClient(url=QDRANT_URL)
    embedding_client = httpx.AsyncClient(base_url=TEI_EMBEDDING_URL, timeout=60.0)
    llm_client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key=(os.environ.get("VLLM_API_KEY") or "not-needed"))
    yield
    await qdrant_client.close()
    await embedding_client.aclose()


app = FastAPI(
    title="Hospital Clinical Knowledge Assistant API",
    description="Self-hosted hybrid RAG (BGE-M3 + Qdrant + Llama 3) with PHI redaction",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Retrieval-Confidence", "X-Top-Similarity", "X-PHI-Redacted"],
)


async def require_api_key(authorization: Optional[str] = Header(default=None)):
    """No-op when API_KEY is unset; otherwise enforces `Authorization: Bearer <key>`."""
    if not API_KEY:
        return
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


# ---------------------------------------------------------
# 2. Models
# ---------------------------------------------------------
class ClinicalQueryRequest(BaseModel):
    query: str = Field(..., description="The medical query from the clinician")
    k_chunks: int = Field(5, description="Number of context chunks to retrieve")
    department: Optional[str] = Field(None, description="Restrict retrieval to a department")
    access_levels: Optional[list[str]] = Field(None, description="Allowed access levels for the requester")


def _retrieval_filter(department=None, access_levels=None):
    """Only retrieve approved, in-effect (non-expired), active documents;
    optionally scoped to a department and the requester's access levels."""
    must = [
        models.FieldCondition(key="is_active", match=models.MatchValue(value=True)),
        models.FieldCondition(key="approval_status", match=models.MatchValue(value="approved")),
        models.FieldCondition(key="expiry_ts", range=models.Range(gte=now_ts())),
    ]
    if department:
        must.append(models.FieldCondition(key="department", match=models.MatchValue(value=department)))
    if access_levels:
        must.append(models.FieldCondition(key="access_level", match=models.MatchAny(any=list(access_levels))))
    return models.Filter(must=must)


# ---------------------------------------------------------
# 3. Core RAG Endpoint
# ---------------------------------------------------------
@app.post("/api/v1/query", dependencies=[Depends(require_api_key)])
async def clinical_query(request: ClinicalQueryRequest):
    # STEP 0: PHI redaction (before anything is embedded, sent, or logged) +
    # medical shorthand expansion (retrieval aid).
    scrubbed, phi_found = redact_phi(request.query)
    normalized = expand_shorthand(scrubbed)

    # STEP 1: dense embedding (TEI) + sparse lexical encoding of the normalized query
    try:
        dense_vec = (await embed_async(embedding_client, [normalized]))[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failure: {str(e)}")

    sp = sparse_encode(normalized)
    sparse_query = models.SparseVector(indices=sp["indices"], values=sp["values"])

    # STEP 2: hybrid search (RRF) for ordering + dense-only top score for the gate
    try:
        rf = _retrieval_filter(request.department, request.access_levels)
        hybrid = await qdrant_client.query_points(
            collection_name=QDRANT_COLLECTION,
            prefetch=[
                models.Prefetch(query=dense_vec, using="dense", limit=max(request.k_chunks, 10), filter=rf),
                models.Prefetch(query=sparse_query, using="sparse", limit=max(request.k_chunks, 10), filter=rf),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=request.k_chunks,
            with_payload=True,
        )
        hits = hybrid.points
        dense_only = await qdrant_client.query_points(
            collection_name=QDRANT_COLLECTION, query=dense_vec, using="dense", limit=1,
            query_filter=rf, with_payload=False,
        )
        top_similarity = dense_only.points[0].score if dense_only.points else 0.0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search failure: {str(e)}")

    resp_headers = {
        "X-PHI-Redacted": "true" if phi_found else "false",
        "X-Top-Similarity": f"{top_similarity:.4f}",
    }

    # STEP 3: confidence guardrails
    if not hits:
        return StreamingResponse(
            chunk_generator("Information not found in approved clinical guidelines."),
            media_type="text/event-stream", headers={**resp_headers, "X-Retrieval-Confidence": "None"},
        )
    if top_similarity < MIN_CONF:
        return StreamingResponse(
            chunk_generator(f"No matching clinical guideline found. Highest similarity was only {top_similarity:.2f}."),
            media_type="text/event-stream", headers={**resp_headers, "X-Retrieval-Confidence": "None"},
        )

    confidence = "High" if top_similarity >= HIGH_CONF else "Moderate"
    resp_headers["X-Retrieval-Confidence"] = confidence

    # STEP 4: XML context + grounded prompt
    context_xml = "<retrieved_documents>\n"
    for hit in hits:
        p = hit.payload or {}
        context_xml += f'  <document id="{p.get("doc_id","UNKNOWN")}" page="{p.get("page_number","?")}">\n'
        context_xml += f'    {p.get("paragraph_text","")}\n'
        context_xml += f'  </document>\n'
    context_xml += "</retrieved_documents>"

    system_prompt = f"""
You are an expert clinical knowledge assistant. Use the verified excerpts in the <retrieved_documents> block to answer the clinician's question directly and concisely.

Rules:
1. Base your answer ONLY on the provided excerpts. You MAY synthesize and paraphrase across excerpts to answer the question.
2. If the excerpts are relevant to the question, ANSWER it - do not refuse. Include any key cautions or contraindications the excerpts mention.
3. Only if NONE of the excerpts are relevant to the question, reply exactly: "Information not found in approved clinical guidelines."
4. Do not use outside medical knowledge beyond the excerpts.
5. Cite every claim inline using the exact document id and page from the XML, formatted as [Doc: ID, Page: Y].
6. Be concise - a few sentences suitable for rapid bedside use.

{context_xml}
"""

    async def generate_llm_stream() -> AsyncGenerator[str, None]:
        try:
            stream = await llm_client.chat.completions.create(
                model=VLLM_MODEL_NAME, max_tokens=int(os.environ.get("MAX_TOKENS", "400")), temperature=0.0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": scrubbed},
                ],
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as e:
            yield f"\n[Generation Error: {str(e)}]"

    return StreamingResponse(generate_llm_stream(), media_type="text/event-stream", headers=resp_headers)


# ---------------------------------------------------------
# 4. Source Verification Endpoint
# ---------------------------------------------------------
@app.get("/api/v1/source", dependencies=[Depends(require_api_key)])
async def get_source(doc_id: str, page: Optional[int] = None):
    """Return the exact stored source chunk for a citation (doc_id + optional page)."""
    must = [models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))]
    if page is not None:
        must.append(models.FieldCondition(key="page_number", match=models.MatchValue(value=page)))
    try:
        points, _ = await qdrant_client.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter=models.Filter(must=must),
            limit=1, with_payload=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Source lookup failure: {str(e)}")
    if not points:
        raise HTTPException(status_code=404, detail=f"No source found for doc_id={doc_id} page={page}")
    p = points[0].payload or {}
    return {
        "doc_id": p.get("doc_id"),
        "title": p.get("title", p.get("doc_id")),
        "department": p.get("department"),
        "page_number": p.get("page_number"),
        "paragraph_text": p.get("paragraph_text", ""),
    }


@app.get("/api/v1/sources", dependencies=[Depends(require_api_key)])
async def list_sources():
    """List the documents currently in the knowledge base (what the assistant can answer about)."""
    docs = {}
    offset = None
    try:
        while True:
            points, offset = await qdrant_client.scroll(
                collection_name=QDRANT_COLLECTION, limit=256, offset=offset,
                with_payload=True, with_vectors=False,
            )
            for pt in points:
                pl = pt.payload or {}
                did = pl.get("doc_id", "UNKNOWN")
                d = docs.setdefault(did, {"doc_id": did, "title": pl.get("title", did),
                                          "department": pl.get("department"), "chunks": 0, "pages": set(),
                                          "version": pl.get("version"), "approval_status": pl.get("approval_status", "approved"),
                                          "access_level": pl.get("access_level", "general"),
                                          "effective_date": pl.get("effective_date"), "expiry_date": pl.get("expiry_date"),
                                          "review_date": pl.get("review_date")})
                d["chunks"] += 1
                if pl.get("page_number") is not None:
                    d["pages"].add(pl["page_number"])
            if offset is None:
                break
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sources listing failure: {str(e)}")
    documents = [{"doc_id": d["doc_id"], "title": d["title"], "department": d["department"],
                  "chunks": d["chunks"], "pages": sorted(d["pages"]), "version": d["version"],
                  "approval_status": d["approval_status"], "access_level": d["access_level"],
                  "effective_date": d["effective_date"], "expiry_date": d["expiry_date"],
                  "review_date": d["review_date"]} for d in docs.values()]
    return {"count": len(documents), "documents": documents}


@app.post("/api/v1/ingest", dependencies=[Depends(require_api_key)])
async def ingest_document(
    file: UploadFile = File(default=None),
    text: str = Form(default=None),
    doc_id: str = Form(default=None),
    title: str = Form(default=None),
    department: str = Form(default="General"),
    version: str = Form(default="1"),
    effective_date: str = Form(default=None),
    expiry_date: str = Form(default=None),
    review_date: str = Form(default=None),
    approval_status: str = Form(default="approved"),
    access_level: str = Form(default="general"),
):
    """Add a document to the knowledge base from an uploaded file (PDF/TXT/MD)
    or pasted text. Chunks, embeds (dense + sparse), and upserts into Qdrant."""
    has_text = bool(text and text.strip())
    if file is None and not has_text:
        raise HTTPException(status_code=400, detail="Provide a file or text.")

    filename = file.filename if file is not None else (doc_id or "pasted-document")
    data = await file.read() if file is not None else b""
    try:
        chunks = build_chunks(filename, data, text_override=text if has_text else None)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse document: {str(e)}")
    if not chunks:
        raise HTTPException(status_code=400, detail="No extractable text found in the document.")

    did = doc_id or (os.path.splitext(filename)[0] if file is not None else "PASTED-DOC")
    ttl = title or did
    doc_meta = build_doc_meta(version, effective_date, expiry_date, review_date, approval_status, access_level)

    texts = [c[1] for c in chunks]
    try:
        vecs = await embed_async(embedding_client, texts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failure: {str(e)}")

    # replace any existing chunks for this doc_id, then upsert fresh ones
    try:
        await qdrant_client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=models.FilterSelector(filter=models.Filter(
                must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=did))])),
        )
        points = []
        for idx, ((page_no, chunk), vec) in enumerate(zip(chunks, vecs)):
            sp = sparse_encode(chunk)
            points.append(models.PointStruct(
                id=str(uuid.uuid5(_ID_NS, f"{did}:{idx}")),
                vector={"dense": vec, "sparse": models.SparseVector(indices=sp["indices"], values=sp["values"])},
                payload={"doc_id": did, "title": ttl, "department": department,
                         "page_number": page_no, "paragraph_text": chunk, "is_active": True,
                         **doc_meta},
            ))
        await qdrant_client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failure: {str(e)}")

    return {"doc_id": did, "title": ttl, "department": department, "chunks_added": len(points),
            "approval_status": doc_meta["approval_status"], "access_level": doc_meta["access_level"],
            "effective_date": doc_meta["effective_date"], "expiry_date": doc_meta["expiry_date"]}


@app.delete("/api/v1/source", dependencies=[Depends(require_api_key)])
async def delete_source(doc_id: str):
    """Remove a document (all its chunks) from the knowledge base."""
    try:
        await qdrant_client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=models.FilterSelector(filter=models.Filter(
                must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))])),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failure: {str(e)}")
    return {"deleted": doc_id}


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


async def chunk_generator(text: str) -> AsyncGenerator[str, None]:
    yield text
