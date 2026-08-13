# Hospital Clinical Knowledge Assistant

[![CI](https://github.com/yashvicky/Hospital-clinical-knowledge-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/yashvicky/Hospital-clinical-knowledge-assistant/actions/workflows/ci.yml)

A HIPAA-oriented, fully self-hosted **Retrieval-Augmented Generation (RAG)** platform that lets clinicians query internal SOPs, WHO/CDC guidelines, and drug manuals in natural language and get **grounded, citation-backed answers** — with a hard rule never to answer without a matching source.

> Retrieval and generation are kept strictly separate so the system stays sub-3-second, cost-efficient, and keeps clinical documents inside the hospital network. No third-party embedding or LLM API is required.

## ▶️ Try it in one command (no keys, no accounts)

Fully self-contained — Qdrant + **Qwen2.5** (LLM) + **BGE-M3** (embeddings) run
locally in Docker via Ollama. You need only Docker:

```bash
docker compose -f docker-compose.demo.yml up      # then open http://localhost:3000
```

First run downloads the open-weight models (~5 GB) and seeds sample protocols.
Snappier on a small machine: `LLM_MODEL=qwen2.5:3b docker compose -f docker-compose.demo.yml up`.
Full demo + video walkthrough: **[docs/DEMO.md](docs/DEMO.md)**.

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
| Vector database | **Qdrant** — hybrid search (dense cosine + sparse lexical, RRF fusion) |
| Generative LLM | **Llama 3** (8B/70B) served by **vLLM** (OpenAI-compatible API) |
| Orchestration | **FastAPI** (query API) + **LlamaIndex** (document ingestion/chunking) |
| Frontend | **Next.js 15** (App Router) + **Tailwind CSS** + **shadcn/ui** |
| Packaging | Docker & Docker Compose |

See [`docs/hospital-rag-blueprint.md`](docs/hospital-rag-blueprint.md) for the full BMAD PRD, System Architecture Document, and the decision history (including the earlier Claude+Voyage+pgvector and the finalized Qdrant+vLLM stacks).

## Repository layout

```
backend/           FastAPI service (main.py), hybrid search, PHI redaction,
                   shorthand expansion, Qdrant bootstrap, Dockerfile
frontend/          Next.js + shadcn/ui clinical dashboard
ingest/            LlamaIndex document ingestion pipeline (PDF/DOCX/TXT -> Qdrant)
mocks/             CPU-only stand-ins for TEI + vLLM (no GPU / no model download)
scripts/           ingest_sample.py, run_local_dev.sh
tests/             serve_integration.py, ci_smoke.py, eval_hallucination.py
sample_docs/       example clinical document(s) for the ingestion pipeline
docs/              hospital-rag-blueprint.md (BMAD PRD + SAD), TESTING.md
.github/workflows/ CI (backend smoke test + frontend build)
docker-compose.yml         Production stack (real TEI + vLLM, needs a GPU host)
docker-compose.dev.yml     CPU/offline override (mock TEI + vLLM)
```

## Quick start

### Run it for $0 (real models, no GPU rental)

Want real answers without paying for a GPU? Run the LLM locally with Ollama (or
a free Groq key) — the backend is OpenAI-compatible, so it's just env values:
```bash
ollama pull bge-m3 && ollama pull llama3.2
docker compose -f docker-compose.free.yml up --build   # -> http://localhost:3000
```
Full guide: **[docs/FREE_LOCAL.md](docs/FREE_LOCAL.md)**.

### Option A — CPU / offline (mock ML services, no GPU)

Runs the **real** backend + **real** Qdrant with lightweight mock TEI/vLLM so you can exercise the full pipeline on any laptop. The stack is self-seeding — an `init` service creates the collection and loads sample SOPs automatically.

```bash
docker compose -f docker-compose.dev.yml up --build   # or: make up
```

This brings up **everything** — Qdrant, mock TEI/vLLM, the FastAPI backend
(auto-seeded), and the Next.js UI. Open **http://localhost:3000** to test, or
hit the API on `http://localhost:8000`.

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
| `API_KEY` | If set, requires `Authorization: Bearer <key>` (default: open) |
| `FRONTEND_ORIGIN` | CORS origin for the UI (default `*`) |

`.env` files are git-ignored — never commit real credentials.

## Retrieval

Search is **hybrid**: a dense semantic vector (BGE-M3 via TEI) and a sparse
lexical vector (`backend/sparse.py`, BM25-style — catches exact acronyms and
drug dosages) are fused in Qdrant with Reciprocal Rank Fusion. The
confidence-threshold gate runs on the top *dense cosine* similarity so the
guardrail semantics are unchanged.

## Ingesting your own documents

```bash
pip install -r ingest/requirements.txt
QDRANT_URL=http://localhost:6333 TEI_EMBEDDING_URL=http://localhost:8080 \
  python ingest/ingest_documents.py --input-dir sample_docs --department ER
```

LlamaIndex parses and chunks PDF/DOCX/TXT/MD (see [`ingest/README.md`](ingest/README.md)).

## Continuous integration

`.github/workflows/ci.yml` runs on every push/PR: a backend smoke test
(`tests/ci_smoke.py` — in-process Qdrant hybrid search + guardrails, no GPU),
a grounding/hallucination eval (`tests/eval_hallucination.py`), and a full
frontend production build.

## Deployment

See **[docs/DEPLOY.md](docs/DEPLOY.md)** — Vercel for the UI (dashboard or the included `deploy-frontend.yml` workflow) and Docker on your VPS/GPU host for the backend.

## Testing

`tests/serve_integration.py` boots the real backend against an in-process Qdrant seeded through the real TEI service, wired to the mock TEI + vLLM over HTTP, and verifies both the high-confidence cited path and the low-similarity fallback.

## Clinical safety & UX features

- **PHI redaction** (`backend/phi.py`): incoming queries are scrubbed for
  obvious identifiers (SSN, MRN, phone, email, dates, patient names) *before*
  they are embedded, sent to the LLM, or logged. The UI shows a notice when a
  redaction occurs (`X-PHI-Redacted` header).
- **Medical shorthand expansion** (`backend/normalize.py`): terse queries like
  "sepsis tx" or "MI dx" are expanded to improve retrieval.
- **Confidence badge**: the UI shows `Confidence: High (96%)` / `Moderate`
  derived from the top dense cosine similarity (`X-Retrieval-Confidence`).
- **In-app document manager**: a "Manage Documents" panel in the UI to upload PDFs/TXT/MD or paste text, list the knowledge base, and delete documents (backed by `POST /api/v1/ingest`, `GET /api/v1/sources`, `DELETE /api/v1/source`).
- **Source verification**: clicking a citation calls `GET /api/v1/source` and
  renders the *exact* stored source paragraph with matched query terms
  highlighted.
- **Optional API-key auth**: set `API_KEY` to require
  `Authorization: Bearer <key>` on the API (disabled by default for local dev).

## Security & compliance notes

- No PHI is ingested or logged; conversation state is ephemeral (browser session only).
- Embeddings and generation run inside the hospital network — no external embedding/LLM API dependency.
- Every answer is grounded in retrieved source chunks with page-level citations for clinician verification.

> This is a reference implementation / scaffold. A production clinical deployment requires formal validation, a signed BAA for any hosted component, security review, and clinical sign-off.


## Production document management

- **Governance metadata** on every document: `version`, `effective_date`,
  `expiry_date`, `review_date`, `approval_status` (approved/draft/retired), and
  `access_level`. Set them in the Manage Documents panel or the ingest CLI.
- **Freshness + approval filtering:** only `approved`, non-expired documents are
  ever used to answer — expired or draft content is automatically excluded, so
  the assistant never cites a retired protocol.
- **Department & access scoping:** `POST /api/v1/query` accepts `department` and
  `access_levels` to restrict retrieval per unit/role.
- **Batch folder ingestion:** `python ingest/ingest_documents.py --input-dir <dir>
  --department ER --approval-status approved --effective-date 2026-01-01 --expiry-date 2027-01-01`
  ingests an entire folder of PDFs/DOCX/TXT with LlamaIndex parsing.
- **Public guidelines fetcher:** `python ingest/fetch_public_guidelines.py`
  downloads openly-licensed source PDFs (WHO/CDC/StatPearls) into a folder for
  review before ingestion (see the script header for licensing).
