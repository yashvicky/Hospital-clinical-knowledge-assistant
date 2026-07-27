# Testing Guide — CPU / Docker (no GPU required)

This runs the **entire pipeline in containers** using mock TEI + mock vLLM
services, so you can test the real backend, retrieval, guardrails, streaming,
and the UI on any laptop — no GPU, no Hugging Face downloads, no API keys.

> The mocks are deterministic: the embedding uses topic-anchored vectors and
> the "LLM" echoes the retrieved chunk with a citation. This exercises all the
> real plumbing (Qdrant search, confidence thresholds, XML prompting, SSE
> streaming, citation parsing). For real BGE-M3 + Llama 3, use
> `docker-compose.yml` on a GPU host instead.

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2) — `docker compose version`
- Node.js 18+ and npm (only needed for the frontend UI)

## 1. Start the backend stack

From the repo root:

```bash
docker compose -f docker-compose.dev.yml up --build
```

This starts five services:

| Service | Port | Role |
| --- | --- | --- |
| `qdrant` | 6333 | vector database |
| `mock-tei` | 8080 | embedding service (BGE-M3 stand-in) |
| `mock-vllm` | 8001 | generation service (Llama 3 stand-in) |
| `init` | — | one-shot: creates the collection + seeds 3 sample SOPs, then exits |
| `backend` | 8000 | the real FastAPI RAG API |
| `frontend` | 3000 | the Next.js clinical UI |

Wait until you see `clinical_init exited with code 0` and
`clinical_backend | ... Application startup complete.` The API is live on
`http://localhost:8000` and the **UI on http://localhost:3000**.

(Shortcut: `make up` runs the same command; `make down` tears it down.)

## 2. Test the API with curl

**High-confidence, cited answer:**

```bash
curl -N -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the 1-hour sepsis protocol including antibiotics and lactate?","k_chunks":5}'
```

Expected (streamed):

```
Based on the approved clinical guidelines: Sepsis 1-Hour Bundle: measure lactate, obtain blood cultures before antibiotics, ... [Doc: SOP-SEPSIS-2026, Page: 3]
```

**Other seeded topics** (also return grounded + cited answers):

```bash
curl -N -X POST http://localhost:8000/api/v1/query -H "Content-Type: application/json" \
  -d '{"query":"can ibuprofen be given with warfarin?","k_chunks":5}'

curl -N -X POST http://localhost:8000/api/v1/query -H "Content-Type: application/json" \
  -d '{"query":"epinephrine dose for anaphylaxis","k_chunks":5}'
```

**Guardrail — no matching source (bypasses the LLM):**

```bash
curl -N -X POST http://localhost:8000/api/v1/query -H "Content-Type: application/json" \
  -d '{"query":"visitor parking hours and cafeteria menu","k_chunks":5}'
# -> "No matching clinical guideline found. Highest similarity was only 0.xx."
```

Interactive API docs are at `http://localhost:8000/docs`.

## 3. Use the UI

The stack already serves the UI at **http://localhost:3000** (the `frontend`
container). Open it and:

1. Type **"What is the 1-hour sepsis protocol?"** and press *Ask Assistant*.
2. Watch the answer stream in on the left.
3. Click the blue **citation chip** (e.g. `SOP-SEPSIS-2026 (p. 3)`) — the right
   **Source Verification** panel activates with that document's ID and page.
4. Try an off-topic question to see the "no matching guideline" fallback.
5. Notice the **Confidence: High (…%)** badge next to *AI Assessment*.
6. Type a query with fake PHI (e.g. *"sepsis tx for patient John Doe MRN: 55231"*)
   and watch the amber **PHI redacted** notice appear — and the shorthand
   *"tx"* still resolves to the sepsis protocol.
7. After clicking a citation, the right panel shows the **exact source
   paragraph** with your query terms highlighted (via `GET /api/v1/source`).

## 4. Add your own SOPs (optional)

The seed data lives in `backend/bootstrap.py`. To add more without rebuilding,
run the host ingestion script against the running stack:

```bash
pip install -r backend/requirements.txt
QDRANT_URL=http://localhost:6333 TEI_EMBEDDING_URL=http://localhost:8080 \
  python scripts/ingest_sample.py
```

Edit `SAMPLE_SOPS` in that file to add your own `doc_id` / `page_number` /
`paragraph_text`. (Note: the mock embedder only "understands" the clinical
topics defined in `mocks/mock_tei.py`; real BGE-M3 handles arbitrary text.)

## 5. Teardown

```bash
docker compose -f docker-compose.dev.yml down -v      # -v also wipes Qdrant data
```

## Troubleshooting

- **Empty / fallback answers for seeded topics:** the `init` service may not
  have finished. Check `docker compose -f docker-compose.dev.yml logs init`;
  it retries for up to ~60s while Qdrant and TEI come up.
- **Frontend can't reach the API:** confirm `NEXT_PUBLIC_API_URL` in
  `frontend/.env.local` points at `http://localhost:8000/api/v1/query` and the
  backend container is healthy (`curl http://localhost:8000/docs`).
- **Port already in use:** stop whatever is on 8000/8080/8001/6333 or edit the
  port mappings in `docker-compose.dev.yml`.
