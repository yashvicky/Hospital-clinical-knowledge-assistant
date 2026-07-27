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
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException, Header, Depends
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

qdrant_client: AsyncQdrantClient = None
embedding_client: httpx.AsyncClient = None
llm_client: AsyncOpenAI = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global qdrant_client, embedding_client, llm_client
    qdrant_client = AsyncQdrantClient(url=QDRANT_URL)
    embedding_client = httpx.AsyncClient(base_url=TEI_EMBEDDING_URL, timeout=60.0)
    llm_client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key=os.environ.get("VLLM_API_KEY", "not-needed"))
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
        hybrid = await qdrant_client.query_points(
            collection_name=QDRANT_COLLECTION,
            prefetch=[
                models.Prefetch(query=dense_vec, using="dense", limit=max(request.k_chunks, 10)),
                models.Prefetch(query=sparse_query, using="sparse", limit=max(request.k_chunks, 10)),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=request.k_chunks,
            with_payload=True,
        )
        hits = hybrid.points
        dense_only = await qdrant_client.query_points(
            collection_name=QDRANT_COLLECTION, query=dense_vec, using="dense", limit=1, with_payload=False,
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
    You are an expert clinical knowledge assistant. Answer the user's query using ONLY the verified excerpts provided in the <retrieved_documents> XML block.

    Strict Rules:
    1. If the context does not explicitly contain the answer, reply ONLY with: "Information not found in approved clinical guidelines."
    2. Do not use outside medical knowledge.
    3. You must include inline citations using the exact document id and page number provided in the XML, formatted as: [Doc: ID, Page: Y].

    {context_xml}
    """

    async def generate_llm_stream() -> AsyncGenerator[str, None]:
        try:
            stream = await llm_client.chat.completions.create(
                model=VLLM_MODEL_NAME, max_tokens=1024, temperature=0.0,
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


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


async def chunk_generator(text: str) -> AsyncGenerator[str, None]:
    yield text
