# Deployment Guide

The app splits cleanly into two hosting targets (as the spec intends):

- **Frontend (Next.js UI)** → Vercel (free, CI/CD). UI only — never the models.
- **Backend + data + models** → your own infra: a cheap Linux CPU VPS for
  Qdrant + TEI + FastAPI, and a GPU host (or managed endpoint) for vLLM/Llama 3.

```
Vercel (UI)  --HTTPS-->  FastAPI (VPS :8000)  -->  Qdrant + TEI (VPS)
                                              -->  vLLM / Llama 3 (GPU host)
```

---

## 1. Frontend → Vercel

### Option A — Dashboard (simplest, no CI needed)

1. https://vercel.com/new → import `yashvicky/Hospital-clinical-knowledge-assistant`.
2. **Root Directory: `frontend`** (important — the repo is a monorepo).
3. Framework preset: **Next.js** (auto-detected).
4. Add an Environment Variable:
   `NEXT_PUBLIC_API_URL = https://<your-backend-host>/api/v1/query`
5. Deploy. Vercel auto-deploys on every push to `main`.

### Option B — GitHub Actions (included: `.github/workflows/deploy-frontend.yml`)

The workflow deploys on push to `main` (paths under `frontend/`). It stays a
no-op until you add three repo secrets. Create a Vercel token
(https://vercel.com/account/tokens), link the project once locally to get the
IDs, then set the secrets with `gh`:

```bash
# one-time: link the Vercel project to get org/project IDs
cd frontend
npx vercel link        # choose/create the project; sets .vercel/project.json
cat .vercel/project.json   # -> { "orgId": "...", "projectId": "..." }

# store secrets on the GitHub repo (uses your authed gh CLI)
gh secret set VERCEL_TOKEN      --body "<your-vercel-token>"
gh secret set VERCEL_ORG_ID     --body "<orgId>"
gh secret set VERCEL_PROJECT_ID --body "<projectId>"

# also set the API URL in Vercel project env (production)
npx vercel env add NEXT_PUBLIC_API_URL production
```

Trigger a deploy: push to `main`, or run it manually:

```bash
gh workflow run "Deploy Frontend (Vercel)"
gh run watch
```

---

## 2. Backend → self-hosted (Docker)

On your VPS (Qdrant + TEI + FastAPI) — and a GPU host for vLLM:

```bash
git clone https://github.com/yashvicky/Hospital-clinical-knowledge-assistant.git
cd Hospital-clinical-knowledge-assistant
cp backend/.env.example backend/.env      # fill in values (see below)
./scripts/deploy_backend.sh               # build + up + init Qdrant
```

`scripts/deploy_backend.sh` runs `docker compose -f docker-compose.yml up -d
--build` and initializes the Qdrant collection. The `vllm-generation` service
needs an NVIDIA GPU + the nvidia container runtime; if your GPU is a separate
box, run vLLM there and point `VLLM_BASE_URL` at it (drop the service from the
compose file on the CPU VPS).

Ingest your clinical documents once the stack is up:

```bash
pip install -r ingest/requirements.txt
python ingest/ingest_documents.py --input-dir /path/to/SOPs --department ER
```

### Backend `.env` essentials

| Variable | Set to |
| --- | --- |
| `QDRANT_URL` | `http://qdrant:6333` (in-compose) |
| `TEI_EMBEDDING_URL` | `http://tei-embedding-service:80` (in-compose) |
| `VLLM_BASE_URL` | your vLLM host, e.g. `http://gpu-host:8000/v1` |
| `VLLM_MODEL_NAME` | `meta-llama/Meta-Llama-3-8B-Instruct` |
| `API_KEY` | a strong secret → clients must send `Authorization: Bearer <key>` |
| `FRONTEND_ORIGIN` | your Vercel URL, e.g. `https://your-app.vercel.app` (CORS lock-down) |

> In production set both `API_KEY` **and** `FRONTEND_ORIGIN` so the API isn't
> open and CORS is restricted to your UI. Then add the same key to the Vercel
> project (e.g. as a header the UI sends) or terminate auth at your gateway.

---

## 3. Wiring the two together

1. Deploy the backend; note its public URL (put it behind HTTPS / a reverse proxy).
2. Set `NEXT_PUBLIC_API_URL=https://<backend>/api/v1/query` in Vercel.
3. Set `FRONTEND_ORIGIN=https://<your-app>.vercel.app` in the backend `.env`.
4. Redeploy both. Done.
