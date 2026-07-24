# Document Ingestion (LlamaIndex)

Parses and chunks clinical source documents with **LlamaIndex**, then embeds
each chunk (dense via TEI/BGE-M3 + lexical sparse) and upserts into the Qdrant
`clinical_sops` hybrid collection the API reads.

```bash
pip install -r ingest/requirements.txt

# with the dev stack up (Qdrant on 6333, TEI on 8080):
QDRANT_URL=http://localhost:6333 \
TEI_EMBEDDING_URL=http://localhost:8080 \
python ingest/ingest_documents.py --input-dir sample_docs --department ER
```

Supports PDF, DOCX, TXT, and Markdown via LlamaIndex's `SimpleDirectoryReader`.
Chunking is controlled by `CHUNK_SIZE` (default 512) and `CHUNK_OVERLAP`
(default 64). Point IDs are deterministic, so re-ingesting a file updates its
chunks in place.
