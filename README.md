# Hospital Clinical Knowledge Assistant

A HIPAA-oriented, fully self-hosted **Retrieval-Augmented Generation (RAG)** platform that lets clinicians query internal SOPs, WHO/CDC guidelines, and drug manuals in natural language and get **grounded, citation-backed answers** — with a hard rule never to answer without a matching source.

> Retrieval and generation are kept strictly separate so the system stays sub-3-second, cost-efficient, and keeps clinical documents inside the hospital network. No third-party embedding or LLM API is required.

## Architecture

```
        Next.js + shadcn/ui (clinical workstation UI, split-pane verify view)
                                   │  POST /api/v1/query  (streamed)
                                   ▼
                        FastAPI backend (async orchestration)
                 │                     │                        │
     1. embed query          2. vector search          3. stream generation
                 ▼                     ▼                        ▼
      TEI  (BGE-M3, Docker)   Qdrant (cosine, HNSW)   vLLM (Llama 3, OpenAI API)
```

**Grounding guardrails (business rules, independent of the models):**

| Top cosine similarity | Behavior |
| --- | --- |
| `>= 0.82` | High confidence — answer with inline `[Doc: ID, Page: N]` citations |
| `0.65 – 0.82` | Moderate confidence — answer with citations |
| `< 0.65` | **Bypass the LLM entirely** and return `"No matching clinical guideline found."` |

If retrieval returns nothing, the API returns `"Information not found in approved clinical guidelines."` The system prompt further forbids the LLM from using outside knowledge.

## Tech stack

| Layer | Choice |
| --- | --- |
| Embedding model | `BGE-M3` (BAAI) via Hugging Face **TEI**, 1024-dim |
| Vector database | **Qdrant** (cosine distance) |
| Generative LLM | **Llama 3** (8B/70B) served by **vLLM** (OpenAI-compatible API) |
| Orchestration | **FastAPI** + LlamaIndex |
| Frontend | **Next.js 15** (App Router) + **Tailwind CSS** + **shadcn/ui** |
| Packaging | Docker & Docker Compose |

See [`docs/hospital-rag-blueprint.md`](docs/hospital-rag-blueprint.md) for the full BMAD PRD, System Architecture Document, and the decision history (including the earlier Claude+Voyage+pgvector and the finalized Qdrant+vLLM stacks).

## Repository layout

```
backend/           FastAPI service (main.py), Qdrant bootstrap, Dockerfile
frontend/          Next.js + shadcn/ui clinical dashboard
mocks/             CPU-only stand-ins for TEI + vLLM (no GPU / no model download)
scripts/           ingest_sample.py, run_local_dev.sh
tests/             serve_integration.py (real-HTTP integration harness)
docs/              hospital-rag-blueprint.md (BMAD PRD + SAD)
docker-compose.yml         Production stack (real TEI + vLLM, needs a GPU host)
docker-compose.dev.yml     CPU/offline override (mock TEI + vLLM)
```

## Quick start

### Option A — CPU / offline (mock ML services, no GPU)

Runs the **real** backend + **real** Qdrant with lightweight mock TEI/vLLM so you can exercise the full pipeline on any laptop. The stack is self-seeding — an `init` service creates the collection and loads sample SOPs automatically.

```bash
docker compose -f docker-compose.dev.yml up --build
```

See **[docs/TESTING.md](docs/TESTING.md)** for a full walkthrough (curl examples, expected output, and the UI test).

Or without Docker at all:

```bash
./scripts/run_local_dev.sh      # needs python3 + a Qdrant (Docker or `qdrant` binary)
```

Then query it:

```bash
curl -N -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the 1-hour sepsis protocol?","k_chunks":5}'
```

### Option B — Production (real BGE-M3 + Llama 3)

Requires an NVIDIA GPU host with the nvidia container runtime (for vLLM) and outbound access to Hugging Face for first-boot model downloads.

```bash
docker compose up -d
docker compose exec backend python qdrant_init.py
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local     # point NEXT_PUBLIC_API_URL at the backend
npm install
npm run dev                          # http://localhost:3000
```

## Configuration

Copy `backend/.env.example` to `backend/.env` and adjust:

| Variable | Purpose |
| --- | --- |
| `QDRANT_URL` | Qdrant endpoint (default `http://localhost:6333`) |
| `QDRANT_COLLECTION` | Collection name (`clinical_sops`) |
| `TEI_EMBEDDING_URL` | TEI embedding service base URL |
| `VLLM_BASE_URL` | vLLM OpenAI-compatible base URL |
| `VLLM_MODEL_NAME` | Served model id |
| `EMBEDDING_DIM` | Vector dimension for `qdrant_init.py` (1024) |

`.env` files are git-ignored — never commit real credentials.

## Testing

`tests/serve_integration.py` boots the real backend against an in-process Qdrant seeded through the real TEI service, wired to the mock TEI + vLLM over HTTP, and verifies both the high-confidence cited path and the low-similarity fallback.

## Security & compliance notes

- No PHI is ingested or logged; conversation state is ephemeral (browser session only).
- Embeddings and generation run inside the hospital network — no external embedding/LLM API dependency.
- Every answer is grounded in retrieved source chunks with page-level citations for clinician verification.

> This is a reference implementation / scaffold. A production clinical deployment requires formal validation, a signed BAA for any hosted component, security review, and clinical sign-off.
