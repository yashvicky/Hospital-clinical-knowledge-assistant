# Hospital Clinical Knowledge Assistant — dev shortcuts
DEV := docker compose -f docker-compose.dev.yml

.PHONY: up down logs test eval frontend-build help

help:
	@echo 'make up     - build + start the full local stack (Qdrant, mock TEI/vLLM, backend, UI)'
	@echo 'make down   - stop everything and wipe Qdrant data'
	@echo 'make logs   - follow logs'
	@echo 'make test   - backend smoke test (in-process, no Docker)'
	@echo 'make eval   - grounding / hallucination eval'

up:
	$(DEV) up --build

down:
	$(DEV) down -v

logs:
	$(DEV) logs -f

test:
	python tests/ci_smoke.py

eval:
	python tests/eval_hallucination.py

frontend-build:
	cd frontend && npm ci && npm run build

