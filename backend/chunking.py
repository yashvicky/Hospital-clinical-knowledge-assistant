"""
Lightweight document extraction + chunking for the in-app ingestion endpoint.

Supports PDF (per-page), and plain text / Markdown. Chunks are packed from
paragraph boundaries up to a max character budget so citations stay meaningful.
(For large-scale ingestion with richer parsing, use the LlamaIndex pipeline in
ingest/.)
"""
import io
import re

MAX_CHARS = 800


def extract_pages(filename: str, data: bytes) -> list[tuple[int, str]]:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return [(i + 1, (page.extract_text() or "")) for i, page in enumerate(reader.pages)]
    # txt / md / anything else: decode as text (page 1)
    return [(1, data.decode("utf-8", errors="ignore"))]


def _split_paragraph(p: str) -> list[str]:
    if len(p) <= MAX_CHARS:
        return [p]
    # hard-split overly long paragraphs on sentence boundaries where possible
    out, cur = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", p):
        if len(cur) + len(sent) + 1 <= MAX_CHARS:
            cur = (cur + " " + sent).strip()
        else:
            if cur:
                out.append(cur)
            cur = sent if len(sent) <= MAX_CHARS else ""
            if not cur:
                for i in range(0, len(sent), MAX_CHARS):
                    out.append(sent[i:i + MAX_CHARS])
    if cur:
        out.append(cur)
    return out


def chunk_text(text: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 1 <= MAX_CHARS:
            cur = (cur + "\n" + p).strip()
        else:
            if cur:
                chunks.append(cur)
                cur = ""
            for piece in _split_paragraph(p):
                if len(cur) + len(piece) + 1 <= MAX_CHARS:
                    cur = (cur + "\n" + piece).strip()
                else:
                    if cur:
                        chunks.append(cur)
                    cur = piece
    if cur:
        chunks.append(cur)
    return chunks


def build_chunks(filename: str, data: bytes, text_override: str | None = None) -> list[tuple[int, str]]:
    """Return list of (page_number, chunk_text)."""
    pages = [(1, text_override)] if text_override else extract_pages(filename, data)
    out = []
    for page_no, ptext in pages:
        for ch in chunk_text(ptext or ""):
            if ch.strip():
                out.append((page_no, ch))
    return out
