"""
Hospital Clinical Knowledge Assistant — FastAPI Backend
BMAD Phase 4: Core Backend Implementation (Finalized Production Stack)

Fully self-hosted RAG pipeline:
  - Query embedding: BGE-M3 (dense) via a self-hosted Hugging Face TEI container
  - Sparse encoding:  lexical BM25-style vector (backend/sparse.py) for exact
                      keyword / acronym / dosage matching
  - Vector search:    Qdrant HYBRID search — dense + sparse named vectors fused
                      with Reciprocal Rank Fusion (RRF)
  - Generation:       Llama 3 (8B/70B) via vLLM's OpenAI-compatible streaming API

Grounding guardrails (from the PRD's Constraints & Guardrails — business rules,
independent of the models). The confidence gate uses the top DENSE cosine
similarity (semantic relevance), while hybrid RRF decides chunk *ordering*:
  - dense cosine >= 0.82         -> Confidence: High
  - 0.65 <= dense cosine < 0.82  -> Confidence: Moderate
  - dense cosine < 0.65          -> bypass the LLM, return the fixed "not found"
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient, models

from sparse import sparse_encode

# ---------------------------------------------------------
# 1. App Lifespan & Global Clients
# ---------------------------------------------------------
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "clinical_sops")

TEI_EMBEDDING_URL = os.environ.get("TEI_EMBEDDING_URL", "http://localhost:8080")

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL_NAME = os.environ.get("VLLM_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")

# Confidence thresholds (top dense cosine similarity)
HIGH_CONF = float(os.environ.get("CONF_HIGH", "0.82"))
MIN_CONF = float(os.environ.get("CONF_MIN", "0.65"))

qdrant_client: AsyncQdrantClient = None
embedding_client: httpx.AsyncClient = None
llm_client: AsyncOpenAI = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global qdrant_client, embedding_client, llm_client
    qdrant_client = AsyncQdrantClient(url=QDRANT_URL)
    embedding_client = httpx.AsyncClient(base_url=TEI_EMBEDDING_URL, timeout=10.0)
    llm_client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key=os.environ.get("VLLM_API_KEY", "not-needed"))
    yield
    await qdrant_client.close()
    await embedding_client.aclose()


app = FastAPI(
    title="Hospital Clinical Knowledge Assistant API",
    description="Self-hosted hybrid RAG using BGE-M3 (TEI) + Qdrant + Llama 3 (vLLM)",
    lifespan=lifespan
)


# ---------------------------------------------------------
# 2. Pydantic Models
# ---------------------------------------------------------
class ClinicalQueryRequest(BaseModel):
    query: str = Field(..., description="The medical query from the clinician")
    k_chunks: int = Field(5, description="Number of context chunks to retrieve")


# ---------------------------------------------------------
# 3. Core RAG Endpoint
# ---------------------------------------------------------
@app.post("/api/v1/query")
async def clinical_query(request: ClinicalQueryRequest):
    """
    1. Embed query (dense via TEI/BGE-M3) + encode sparse (lexical)
    2. Hybrid vector search via Qdrant (dense + sparse, fused with RRF)
    3. Confidence gate on the top dense cosine similarity
    4. Stream a grounded, cited response via Llama 3 (vLLM)
    """

    # STEP 1: Dense embedding (TEI) + sparse lexical encoding
    try:
        embed_res = await embedding_client.post("/embed", json={"inputs": [request.query]})
        embed_res.raise_for_status()
        dense_vec = embed_res.json()[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failure: {str(e)}")

    sparse_vec = sparse_encode(request.query)
    sparse_query = models.SparseVector(indices=sparse_vec["indices"], values=sparse_vec["values"])

    # STEP 2: Hybrid search (dense + sparse, RRF fusion) for chunk ordering,
    # plus a dense-only top score for the confidence gate.
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
            collection_name=QDRANT_COLLECTION,
            query=dense_vec, using="dense", limit=1, with_payload=False,
        )
        top_similarity = dense_only.points[0].score if dense_only.points else 0.0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search failure: {str(e)}")

    # STEP 3: Confidence guardrails
    if not hits:
        return StreamingResponse(
            chunk_generator("Information not found in approved clinical guidelines."),
            media_type="text/event-stream"
        )

    if top_similarity < MIN_CONF:
        return StreamingResponse(
            chunk_generator(f"No matching clinical guideline found. Highest similarity was only {top_similarity:.2f}."),
            media_type="text/event-stream"
        )

    confidence = "High" if top_similarity >= HIGH_CONF else "Moderate"

    # STEP 4: Assemble XML context + grounded prompt
    context_xml = "<retrieved_documents>\n"
    for hit in hits:
        payload = hit.payload or {}
        doc_id = payload.get("doc_id", "UNKNOWN")
        page_number = payload.get("page_number", "?")
        chunk_text = payload.get("paragraph_text", "")
        context_xml += f'  <document id="{doc_id}" page="{page_number}">\n'
        context_xml += f'    {chunk_text}\n'
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
                model=VLLM_MODEL_NAME,
                max_tokens=1024,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.query},
                ],
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as e:
            yield f"\n[Generation Error: {str(e)}]"

    return StreamingResponse(
        generate_llm_stream(),
        media_type="text/event-stream",
        headers={"X-Retrieval-Confidence": confidence, "X-Top-Similarity": f"{top_similarity:.4f}"},
    )


async def chunk_generator(text: str) -> AsyncGenerator[str, None]:
    """Helper to stream static fallback text to the client."""
    yield text
