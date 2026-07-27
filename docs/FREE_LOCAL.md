# Running for $0 (no GPU rental, no paid services)

The only part that needed a paid GPU was the LLM. Because the backend talks to
an **OpenAI-compatible** endpoint, you can point it at a free local or free
cloud model with **zero code changes** — just env values. Everything else
(Qdrant, BGE-M3 embeddings on CPU, FastAPI, the UI) runs free on your machine.

There are two free routes. Pick one.

---

## Option 1 — Fully local & private (recommended)  ·  Ollama

Nothing leaves your computer, so it's HIPAA-appropriate and truly free.

**Prereqs:** Docker Desktop + [Ollama](https://ollama.com) (macOS/Windows/Linux).

```bash
# 1. Pull BOTH models (Ollama serves embeddings AND generation — no TEI/HF needed)
ollama pull bge-m3            # embeddings, 1024-dim (~1.2 GB)
ollama pull llama3.2         # generation (~2 GB). Tiny machine? use llama3.2:1b
#    (Ollama serves an OpenAI-compatible API on http://localhost:11434)

# 2. Start the stack (just Qdrant + backend + UI; models run in Ollama on the host)
docker compose -f docker-compose.free.yml up --build

# 3. Open the UI
#    http://localhost:3000
```

Both embeddings and the LLM run in your local Ollama, so there is **no Hugging
Face download inside Docker** (this avoids the TEI "could not download model
artifacts" error). To use different models, change `EMBED_MODEL` /
`VLLM_MODEL_NAME` in `docker-compose.free.yml` to whatever you pulled.

Notes:
- On **Apple Silicon**, run Ollama natively (not in Docker) so it uses the GPU
  via Metal — the compose file already reaches it at `host.docker.internal`.
- CPU generation is slower than a datacenter GPU, but fine for testing. Smaller
  models (`llama3.2:1b`, `llama3.2:3b`, `phi3`) are much faster.

---

## Option 2 — Zero local compute for the LLM  ·  Groq free tier

If your laptop is too small to run a model, use **Groq's free API** (very fast,
free tier, OpenAI-compatible). Embeddings still run locally via TEI (free).

> ⚠️ Queries leave your machine and go to Groq. Fine for a demo; **not** for
> real patient data / production PHI. For that, use Option 1.

```bash
# 1. Get a free key at https://console.groq.com/keys
# 2. Start Qdrant + TEI + backend + UI, pointing the LLM at Groq:
VLLM_BASE_URL=https://api.groq.com/openai/v1 \
VLLM_MODEL_NAME=llama-3.1-8b-instant \
VLLM_API_KEY=gsk_your_free_groq_key \
docker compose -f docker-compose.free.yml up --build
```

(These env vars override the Ollama defaults in the compose file; you don't need
Ollama installed for this path.)

---

## Option 3 — Just the app flow, instantly  ·  mock stack

Already set up, needs nothing but Docker — deterministic mock embedder + LLM,
for testing the UI/pipeline (not real answers):

```bash
docker compose -f docker-compose.dev.yml up --build      # or: make up
```

---

## Free hosting (optional, if you want it online)

- **Frontend:** Vercel Hobby tier is free — import the repo, Root Directory
  `frontend` (see `docs/DEPLOY.md`).
- **Vector DB:** Qdrant Cloud has a free 1 GB cluster.
- **Backend + models:** hardest to host free 24/7. Cheapest realistic path is
  your own machine (Option 1) exposed via a free tunnel (e.g. `cloudflared`
  quick tunnel) when you want to show it to someone — no server bill.

**Bottom line:** for testing and even day-to-day private use, Option 1 costs
nothing and runs the real models on hardware you already own.

### Tuning retrieval confidence

BGE-M3 cosine similarities run lower than the blueprint's original 0.65/0.82
cutoffs, so the free stack sets `CONF_MIN=0.45` and `CONF_HIGH=0.6` in
`docker-compose.free.yml`. Lower `CONF_MIN` if relevant answers are being
refused; raise it if irrelevant chunks slip through. Terse one-word queries
score low either way — ask a fuller question for best results.
