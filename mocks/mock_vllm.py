"""
Mock vLLM server (OpenAI-compatible) — Llama 3 stand-in.

Drop-in stand-in for a real vLLM GPU server, for CPU-only / offline
development. It implements just enough of the OpenAI Chat Completions
streaming API for the backend's AsyncOpenAI client to work.

It reads the retrieved-context XML the backend places in the system prompt,
extracts the top <document id=... page=...>, and streams back a short grounded
answer that includes a citation in the exact [Doc: ID, Page: Y] format the
frontend parser expects. If no context is present it streams the standard
"not found" fallback.

Run:  uvicorn mock_vllm:app --host 0.0.0.0 --port 8001
"""
import json
import re
import time

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="Mock vLLM (Llama 3 stand-in)")

_doc_re = re.compile(r'<document id="([^"]+)" page="([^"]+)">\s*(.*?)\s*</document>', re.DOTALL)


def build_answer(system_prompt: str, user_query: str) -> str:
    docs = _doc_re.findall(system_prompt or "")
    if not docs:
        return "Information not found in approved clinical guidelines."
    doc_id, page, text = docs[0]
    snippet = " ".join(text.split())
    if len(snippet) > 220:
        snippet = snippet[:220].rsplit(" ", 1)[0] + "..."
    return f"Based on the approved clinical guidelines: {snippet} [Doc: {doc_id}, Page: {page}]"


@app.get("/v1/models")
def models():
    return {
        "object": "list",
        "data": [{"id": "meta-llama/Meta-Llama-3-8B-Instruct", "object": "model", "owned_by": "mock"}],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "meta-llama/Meta-Llama-3-8B-Instruct")
    messages = body.get("messages", [])
    system_prompt = next((m["content"] for m in messages if m.get("role") == "system"), "")
    user_query = next((m["content"] for m in messages if m.get("role") == "user"), "")
    answer = build_answer(system_prompt, user_query)

    created = int(time.time())

    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    async def stream():
        # Stream token-by-token (word chunks) like a real model would.
        for i, word in enumerate(answer.split(" ")):
            chunk = {
                "id": "chatcmpl-mock",
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {"index": 0, "delta": {"content": (" " if i > 0 else "") + word}, "finish_reason": None}
                ],
            }
            yield sse(chunk)
        done = {
            "id": "chatcmpl-mock",
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield sse(done)
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok", "model": "mock-llama-3"}
