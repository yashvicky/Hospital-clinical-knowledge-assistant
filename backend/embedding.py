"""
Pluggable embedding backend (select with EMBED_BACKEND):

  - "tei" (default): Hugging Face Text Embeddings Inference.
        POST {base}/embed  {"inputs": [...]}  ->  [[...], ...]
        Used by the mock dev stack and the real TEI production stack.

  - "openai": any OpenAI-compatible embeddings endpoint, incl. **Ollama**.
        POST {base}/v1/embeddings  {"model": M, "input": "<text>"}
        ->  {"data": [{"embedding": [...]}]}
        Lets the $0 local stack use Ollama (e.g. `bge-m3`) for embeddings, so
        no TEI container / Hugging Face download is needed.
"""
import os

EMBED_BACKEND = os.environ.get("EMBED_BACKEND", "tei").lower()
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")


async def embed_async(client, texts):
    if EMBED_BACKEND == "openai":
        out = []
        for t in texts:
            r = await client.post("/v1/embeddings", json={"model": EMBED_MODEL, "input": t})
            r.raise_for_status()
            out.append(r.json()["data"][0]["embedding"])
        return out
    r = await client.post("/embed", json={"inputs": texts})
    r.raise_for_status()
    return r.json()


def embed_sync(client, texts):
    if EMBED_BACKEND == "openai":
        out = []
        for t in texts:
            r = client.post("/v1/embeddings", json={"model": EMBED_MODEL, "input": t})
            r.raise_for_status()
            out.append(r.json()["data"][0]["embedding"])
        return out
    r = client.post("/embed", json={"inputs": texts})
    r.raise_for_status()
    return r.json()
