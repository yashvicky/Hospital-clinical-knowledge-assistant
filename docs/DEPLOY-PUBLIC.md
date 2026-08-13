# Put it online so anyone can open it on any device (free)

Goal: a public link (e.g. `your-app.vercel.app`) that anyone opens on a phone or
laptop — no install, no Docker. Three free pieces, all using Chinese open-weight
models (Qwen2.5 + BGE-M3):

```
  Vercel (the UI / public link)  --HTTPS-->  Backend on a free host
                                             ├─ Qdrant runs IN-PROCESS (no DB account)
                                             └─ SiliconFlow: Qwen2.5 (LLM) + BGE-M3 (embeddings)
```

Accounts you'll create (all free, no card): **SiliconFlow**, a **backend host**
(Render / Koyeb / Hugging Face Spaces), and **Vercel**. No database account —
the backend seeds an in-process Qdrant at startup.

---

## 1. SiliconFlow API key (models)

Sign up at **https://siliconflow.cn** (or siliconflow.com) → create an API key.
Their free tier is OpenAI-compatible, no card, and includes Qwen2.5-7B (free)
and BGE-M3 embeddings. One key covers both the LLM and embeddings.

## 2. Deploy the backend (free container host)

Deploy the **`backend/`** folder as a Docker service on any free host (Render,
Koyeb, Hugging Face Spaces, Zeabur…). The image reads `$PORT` automatically.

Set these environment variables (this is the whole config — in-process Qdrant,
SiliconFlow for both models):

```
QDRANT_MODE=embedded
EMBED_BACKEND=openai
EMBED_MODEL=BAAI/bge-m3
TEI_EMBEDDING_URL=https://api.siliconflow.cn
EMBED_API_KEY=<your SiliconFlow key>
VLLM_BASE_URL=https://api.siliconflow.cn/v1
VLLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
VLLM_API_KEY=<your SiliconFlow key>
CONF_MIN=0.45
CONF_HIGH=0.6
MAX_TOKENS=400
FRONTEND_ORIGIN=*            # tighten to your Vercel URL in step 4
```

Notes per host:
- **Render / Koyeb:** New Web Service → connect this GitHub repo → Root Directory
  `backend` → Docker → add the env vars above. They inject `$PORT` automatically.
- **Hugging Face Spaces (Docker):** create a Docker Space, add the backend files,
  set `app_port: 8000` in the Space README metadata and `PORT=8000` in secrets,
  plus the env vars above.

After it deploys you'll get a public backend URL like
`https://your-backend.onrender.com`. Test it:
`https://your-backend.onrender.com/api/v1/health` → `{"status":"ok"}`.

## 3. Deploy the UI to Vercel

1. https://vercel.com/new → import this repo.
2. **Root Directory: `frontend`**. Framework: Next.js (auto).
3. Environment variable:
   `NEXT_PUBLIC_API_URL = https://your-backend.onrender.com/api/v1/query`
4. Deploy → you get a public URL like `https://your-app.vercel.app`.

## 4. Lock CORS (recommended)

Set `FRONTEND_ORIGIN=https://your-app.vercel.app` on the backend and redeploy so
only your UI can call the API.

---

**Share the Vercel link — anyone can open it on any device.** ✅

### Honest caveats
- **In-process Qdrant is ephemeral:** on a backend restart it re-seeds the sample
  corpus, and any documents added through the UI reset. That's usually *good* for
  a public demo (random visitors can't permanently change it). For persistence,
  use **Qdrant Cloud** (free 1 GB): set `QDRANT_MODE=server`,
  `QDRANT_URL=<cluster url>`, `QDRANT_API_KEY=<key>` and seed once with
  `bootstrap.py`.
- **Free backend hosts sleep** when idle — the first request after a nap is slow.
- **SiliconFlow free tier** has rate limits (fine for a demo).
- Cloud APIs = **not for real PHI** without a BAA (see docs/DEPLOY.md). This public
  demo uses the sample corpus, not patient data.
