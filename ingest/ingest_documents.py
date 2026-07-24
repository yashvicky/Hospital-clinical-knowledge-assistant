"""
Document-first ingestion pipeline (LlamaIndex).

Uses LlamaIndex to parse and chunk clinical source documents (PDF, DOCX, TXT,
MD — including tables/structure in dense guideline PDFs), then embeds each
chunk with the self-hosted TEI service (dense / BGE-M3) plus a lexical sparse
vector, and upserts into the same Qdrant HYBRID `clinical_sops` collection the
API reads.

Usage:
    pip install -r ingest/requirements.txt
    QDRANT_URL=http://localhost:6333 TEI_EMBEDDING_URL=http://localhost:8080 \
        python ingest/ingest_documents.py --input-dir sample_docs --department ER

Each output point matches the backend payload schema:
    doc_id, title, department, page_number, paragraph_text, is_active
`doc_id` defaults to the file stem; `page_number` comes from the parser's page
metadata. Point IDs are deterministic (uuid5 of doc_id + chunk index), so
re-running updates chunks in place instead of duplicating them.
"""
import argparse
import os
import sys
import uuid

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter

# reuse the backend's sparse encoder + collection bootstrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from sparse import sparse_encode          # noqa: E402
from qdrant_init import ensure_collection  # noqa: E402

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "clinical_sops")
TEI_EMBEDDING_URL = os.environ.get("TEI_EMBEDDING_URL", "http://localhost:8080")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "64"))

_NS = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")  # fixed namespace for stable IDs


def embed(hc: httpx.Client, text: str) -> list[float]:
    r = hc.post(f"{TEI_EMBEDDING_URL}/embed", json={"inputs": [text]}, timeout=60.0)
    r.raise_for_status()
    return r.json()[0]


def build_points(nodes, department: str):
    points = []
    with httpx.Client() as hc:
        for idx, node in enumerate(nodes):
            text = node.get_content()
            if not text.strip():
                continue
            meta = node.metadata or {}
            doc_id = os.path.splitext(meta.get("file_name", "DOC"))[0]
            page_number = int(meta.get("page_label", meta.get("page_number", 1)) or 1)
            sp = sparse_encode(text)
            pid = str(uuid.uuid5(_NS, f"{doc_id}:{idx}"))
            points.append(PointStruct(
                id=pid,
                vector={
                    "dense": embed(hc, text),
                    "sparse": SparseVector(indices=sp["indices"], values=sp["values"]),
                },
                payload={
                    "doc_id": doc_id,
                    "title": meta.get("file_name", doc_id),
                    "department": department,
                    "page_number": page_number,
                    "paragraph_text": text,
                    "is_active": True,
                },
            ))
    return points


def main():
    ap = argparse.ArgumentParser(description="Ingest clinical documents into Qdrant (hybrid).")
    ap.add_argument("--input-dir", required=True, help="Directory of PDF/DOCX/TXT/MD files")
    ap.add_argument("--department", default="General", help="Department tag for these docs")
    args = ap.parse_args()

    print(f"Reading documents from {args.input_dir} ...")
    documents = SimpleDirectoryReader(args.input_dir).load_data()
    print(f"Loaded {len(documents)} document page(s). Chunking (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}) ...")

    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"Produced {len(nodes)} chunks. Embedding + upserting ...")

    client = QdrantClient(url=QDRANT_URL)
    ensure_collection(client)
    points = build_points(nodes, args.department)
    if not points:
        print("No non-empty chunks found; nothing to ingest.")
        return
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"Ingested {len(points)} chunks into '{QDRANT_COLLECTION}'.")


if __name__ == "__main__":
    main()
