"""
Hospital Clinical Knowledge Assistant — FastAPI Backend
BMAD Phase 4: Core Backend Implementation (Finalized Production Stack)

Fully self-hosted RAG pipeline:
  - Query embedding: BGE-M3 served via a self-hosted Hugging Face
    Text Embeddings Inference (TEI) container
  - Vector search:   Qdrant (cosine distance)
  - Generation:      Llama 3 (8B/70B) served via vLLM's OpenAI-compatible
                      streaming API — no external LLM API dependency

Grounding guardrails (carried over unchanged from the PRD's Constraints &
Guardrails section — these are business requirements, independent of which
vector DB or LLM serves them):
  - similarity >= 0.82           -> Confidence: High
  - 0.65 <= similarity < 0.82    -> Confidence: Moderate
  - similarity < 0.65            -> bypass the LLM entirely, return the
                                     fixed "not found" message
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient

# ---------------------------------------------------------
# 1. App Lifespan & Global Clients
# ---------------------------------------------------------
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "clinical_sops")

# Self-hosted Text Embeddings Inference (TEI) service running BGE-M3.
# No external API key required -- embeddings never leave the hospital network.
TEI_EMBEDDING_URL = os.environ.get("TEI_EMBEDDING_URL", "http://localhost:8080")

# Self-hosted vLLM server exposing an OpenAI-compatible API for Llama 3.
VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL_NAME = os.environ.get("VLLM_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")

qdrant_client: AsyncQdrantClient = None
embedding_client: httpx.AsyncClient = None
llm_client: AsyncOpenAI = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global qdrant_client, embedding_client, llm_client
    qdrant_client = AsyncQdrantClient(url=QDRANT_URL)
    embedding_client = httpx.AsyncClient(base_url=TEI_EMBEDDING_URL, timeout=10.0)
    # vLLM's OpenAI-compatible server doesn't require a real key
    llm_client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key=os.environ.get("VLLM_API_KEY", "not-needed"))
    yield
    await qdrant_client.close()
    await embedding_client.aclose()


app = FastAPI(
    title="Hospital Clinical Knowledge Assistant API",
    description="Self-hosted RAG using BGE-M3 (TEI) + Qdrant + Llama 3 (vLLM)",
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
    Executes the clinical RAG pipeline:
    1. Embed query with the self-hosted TEI service (BGE-M3)
    2. Vector search via Qdrant
    3. Filter by similarity threshold
    4. Stream response via Llama 3 (vLLM)
    """

    # STEP 1: Embed the user query using the self-hosted embedding model
    try:
        embed_res = await embedding_client.post(
            "/embed",
            json={"inputs": [request.query]}
        )
        embed_res.raise_for_status()
        query_vector = embed_res.json()[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failure: {str(e)}")

    # STEP 2: Vector Search via Qdrant
    # Collection is configured with Distance.COSINE, so `.score` on each hit
    # is already a cosine similarity in [0, 1] (no manual 1 - distance math).
    try:
        result = await qdrant_client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=query_vector,
            limit=request.k_chunks,
            with_payload=True,
        )
        hits = result.points
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vector search failure: {str(e)}")

    # STEP 3: Apply Confidence Thresholds (Guardrails)
    if not hits:
        return StreamingResponse(
            chunk_generator("Information not found in approved clinical guidelines."),
            media_type="text/event-stream"
        )

    top_similarity = hits[0].score

    # Hard cutoff if the highest match is below 0.65
    if top_similarity < 0.65:
        return StreamingResponse(
            chunk_generator(f"No matching clinical guideline found. Highest similarity was only {top_similarity:.2f}."),
            media_type="text/event-stream"
        )

    # STEP 4: Assemble Context & XML Prompts
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

    # STEP 5: Stream Llama 3 Response via vLLM's OpenAI-compatible API
    async def generate_llm_stream() -> AsyncGenerator[str, None]:
        try:
            stream = await llm_client.chat.completions.create(
                model=VLLM_MODEL_NAME,
                max_tokens=1024,
                temperature=0.0,  # deterministic, grounded clinical answers
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

    return StreamingResponse(generate_llm_stream(), media_type="text/event-stream")


async def chunk_generator(text: str) -> AsyncGenerator[str, None]:
    """Helper to stream static fallback text to the client."""
    yield text
