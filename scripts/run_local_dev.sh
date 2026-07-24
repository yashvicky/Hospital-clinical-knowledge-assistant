#!/usr/bin/env bash
#
# Run the full stack locally on a CPU box WITHOUT Docker, using the mock
# TEI/vLLM services. Requires: python3, and either Docker (for Qdrant) or a
# `qdrant` binary on PATH. Starts everything, seeds sample data, and leaves
# the backend running on http://localhost:8000.
#
#   ./scripts/run_local_dev.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
export QDRANT_COLLECTION="${QDRANT_COLLECTION:-clinical_sops}"
export TEI_EMBEDDING_URL="${TEI_EMBEDDING_URL:-http://localhost:8080}"
export VLLM_BASE_URL="${VLLM_BASE_URL:-http://localhost:8001/v1}"
export VLLM_MODEL_NAME="${VLLM_MODEL_NAME:-meta-llama/Meta-Llama-3-8B-Instruct}"

pids=()
cleanup() { echo "Shutting down..."; for p in "${pids[@]:-}"; do kill "$p" 2>/dev/null || true; done; docker rm -f clinical_qdrant_dev 2>/dev/null || true; }
trap cleanup EXIT

echo "==> Installing python deps"
pip install -q -r backend/requirements.txt -r mocks/requirements.txt

echo "==> Starting Qdrant"
if command -v docker >/dev/null 2>&1; then
  docker rm -f clinical_qdrant_dev 2>/dev/null || true
  docker run -d --name clinical_qdrant_dev -p 6333:6333 qdrant/qdrant:latest >/dev/null
elif command -v qdrant >/dev/null 2>&1; then
  qdrant & pids+=($!)
else
  echo "ERROR: need Docker or a 'qdrant' binary on PATH to run Qdrant." >&2
  exit 1
fi

echo "==> Starting mock TEI (:8080) and mock vLLM (:8001)"
( cd mocks && uvicorn mock_tei:app --host 0.0.0.0 --port 8080 ) & pids+=($!)
( cd mocks && uvicorn mock_vllm:app --host 0.0.0.0 --port 8001 ) & pids+=($!)

echo "==> Waiting for services..."
sleep 6

echo "==> Initializing Qdrant collection + seeding sample SOPs"
python backend/qdrant_init.py
python scripts/ingest_sample.py

echo "==> Starting backend on http://localhost:8000"
( cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 ) & pids+=($!)

echo ""
echo "Stack is up. Try:"
echo '  curl -N -X POST http://localhost:8000/api/v1/query -H "Content-Type: application/json" -d '"'"'{"query":"What is the 1-hour sepsis protocol?","k_chunks":5}'"'"''
echo ""
echo "Press Ctrl+C to stop."
wait
