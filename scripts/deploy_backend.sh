#!/usr/bin/env bash
#
# Deploy/refresh the backend stack on a self-hosted host (Linux VPS for
# Qdrant + TEI + FastAPI; a GPU host for vLLM). Pulls latest code and brings
# the production compose stack up. Run from the repo root on the server.
#
#   ./scripts/deploy_backend.sh
#
# Prereqs: git, docker + docker compose v2, and (for the real vLLM service) an
# NVIDIA GPU with the nvidia container runtime. Copy backend/.env.example to
# backend/.env and fill it in first.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> Pulling latest main"
git pull --ff-only origin main

echo "==> Building + starting production stack (docker-compose.yml)"
docker compose -f docker-compose.yml up -d --build

echo "==> Initializing Qdrant collection (idempotent)"
docker compose -f docker-compose.yml exec -T backend python qdrant_init.py

echo "==> Done. API should be reachable on port 8000."
echo "    Health: curl -s http://localhost:8000/api/v1/health"
