"""
Mock Text Embeddings Inference (TEI) service.

Drop-in stand-in for the real Hugging Face TEI container running BGE-M3, for
CPU-only / offline development where you cannot download the real model. It
exposes the same POST /embed contract the backend calls and returns
deterministic 1024-dim vectors.

Design: a "topic-anchored" embedding. Each known clinical topic has a fixed
random unit anchor vector; a text's embedding is the (normalized) sum of the
anchors for topics it mentions, plus a small lexical hashing component. This
makes same-topic query/document pairs land close together (high cosine), while
unrelated text stays far apart — enough to exercise the retrieval +
confidence-threshold logic realistically without a GPU or the real weights.

NOTE: this is a stand-in for offline/CPU demos only, not a semantic model.

Run:  uvicorn mock_tei:app --host 0.0.0.0 --port 8080
"""
import math
import random
import re

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock TEI (BGE-M3 stand-in)")

DIM = 1024
_token_re = re.compile(r"[a-z0-9]+")

# Clinical topic anchors: topic -> keyword triggers. Each anchor is a fixed,
# deterministic unit vector so results are reproducible across restarts.
TOPIC_KEYWORDS = {
    "sepsis": {"sepsis", "septic", "lactate", "bundle", "antibiotics", "vasopressors", "crystalloid", "map", "cultures"},
    "anticoagulation": {"warfarin", "ibuprofen", "nsaid", "nsaids", "anticoagulant", "anticoagulated", "bleeding", "acetaminophen"},
    "airway": {"airway", "intubation", "intubate", "ventilation", "oxygen", "rsi"},
    "cardiac": {"stemi", "troponin", "chest", "aspirin", "mi", "myocardial", "ischemia"},
    "anaphylaxis": {"anaphylaxis", "epinephrine", "allergic", "allergy", "intramuscular", "adrenaline"},
    "stroke": {"stroke", "ischemic", "alteplase", "tpa", "fibrinolytic", "thrombolytic", "fast", "hemorrhage", "neurological", "ct"},
    "stemi": {"stemi", "nitroglycerin", "nitro", "aspirin", "balloon", "cath", "coronary", "ecg", "myocardial", "chest"},
}


def _anchor(topic: str) -> list[float]:
    rng = random.Random(f"anchor::{topic}")
    v = [rng.gauss(0, 1) for _ in range(DIM)]
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


ANCHORS = {t: _anchor(t) for t in TOPIC_KEYWORDS}


def _normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v))
    return v if n == 0.0 else [x / n for x in v]


def embed_text(text: str) -> list[float]:
    tokens = _token_re.findall(text.lower())
    tokset = set(tokens)
    vec = [0.0] * DIM

    # Topic-anchor component (dominant): strengthens same-topic similarity.
    for topic, kws in TOPIC_KEYWORDS.items():
        overlap = len(tokset & kws)
        if overlap:
            anchor = ANCHORS[topic]
            weight = 1.0 + 0.15 * overlap
            for i in range(DIM):
                vec[i] += weight * anchor[i]

    # Small lexical component: separates texts within the same topic a little.
    for tok in tokens:
        h = 0
        for ch in tok:
            h = (h * 131 + ord(ch)) & 0xFFFFFFFF
        vec[h % DIM] += 0.08

    return _normalize(vec)


class EmbedRequest(BaseModel):
    inputs: list[str] | str


@app.post("/embed")
def embed(req: EmbedRequest):
    texts = [req.inputs] if isinstance(req.inputs, str) else req.inputs
    return [embed_text(t) for t in texts]


@app.get("/health")
def health():
    return {"status": "ok", "model": "mock-bge-m3", "dim": DIM}
