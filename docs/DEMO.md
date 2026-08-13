# Try it in one command (no keys, no accounts)

A fully self-contained demo: Qdrant + **Qwen2.5** (LLM) + **BGE-M3** (embeddings)
all run locally inside Docker via Ollama. You need **only Docker Desktop** —
no API keys, no sign-ups, no separate installs.

```bash
git clone https://github.com/yashvicky/Hospital-clinical-knowledge-assistant.git
cd Hospital-clinical-knowledge-assistant
docker compose -f docker-compose.demo.yml up
```

First run downloads the models (~5 GB) into a cached volume, then seeds the
sample knowledge base. When you see `clinical_backend | Application startup
complete`, open **http://localhost:3000**.

- Everything is **Chinese open-weight**: Qwen2.5 (Alibaba, Apache-2.0) + BGE-M3 (BAAI).
- Nothing leaves your machine — fully local and private.
- Stop with `Ctrl+C`; wipe everything with `docker compose -f docker-compose.demo.yml down -v`.

### Make it faster / lighter
- Low-RAM laptop or you want snappier answers on CPU:
  `LLM_MODEL=qwen2.5:3b docker compose -f docker-compose.demo.yml up`
- NVIDIA GPU: uncomment the `deploy:` block under the `ollama` service in
  `docker-compose.demo.yml` — generation becomes near-instant.

---

# Recording a demo video — suggested flow

The sample knowledge base ships with 5 protocols (sepsis, warfarin interactions,
anaphylaxis, code stroke, code STEMI), so these all work out of the box.

**Before you hit record:** run `docker compose -f docker-compose.demo.yml up`
once and ask one question, so the models are already downloaded and warm — you
don't want a 5 GB download or a cold-start pause on camera. If you're on a CPU-
only laptop, use `qwen2.5:3b` (or a GPU) so responses are quick on video.

A tight ~2–3 minute story that shows the real value:

1. **Grounded answer + citation.** Ask *"What is the 1-hour sepsis protocol?"*
   → watch it stream, show the **High confidence** badge, then **click the
   citation chip** → the right panel shows the exact source paragraph with your
   terms highlighted. (This is the trust story: every claim traces to a source.)

2. **Real clinical nuance.** Ask *"Can I give Nitroglycerin to a STEMI patient?"*
   → it answers *yes, with the caution* (avoid if RV infarction / recent PDE
   inhibitors), citing the exact page. Shows genuine synthesis, not lookup.

3. **The anti-hallucination guardrail (the money shot).** Ask something it has
   no source for, e.g. *"What is the visitor parking policy?"* → it replies
   *"Information not found in approved clinical guidelines."* instead of making
   something up. This is what makes it safe.

4. **PHI protection.** Ask *"sepsis tx for patient John Doe, MRN 12345"* → the
   **PHI redacted** notice appears; identifiers are scrubbed before anything is
   processed, and the shorthand "tx" still resolves.

5. **Live extensibility + governance.** Open **Manage Documents** → paste a new
   short protocol, set it **approved**, ingest it → ask about it → it answers
   immediately with a citation. Then flip a document to **draft** (or set a past
   **expiry**) → ask again → it's excluded. Shows production-grade freshness &
   approval control, not just a static demo.

### Talking points to say out loud
- "Retrieval-augmented — answers come only from approved documents, with page-level citations."
- "Hybrid search: semantic embeddings plus exact keyword matching, so acronyms and drug doses aren't missed."
- "It refuses when it has no source — zero fabricated citations on our eval set."
- "Runs fully local on open-weight Chinese models — Qwen2.5 and BGE-M3 — no data leaves the machine."
- "Documents carry approval status and expiry dates, so retired protocols are never cited."
