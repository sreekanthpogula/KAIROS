# ECIP Build Checklist

All phases complete. Verified end-to-end: backend (100/100 tests passing),
frontend (visually verified via headless-browser screenshots across every
screen, both themes, zero console errors), docs (11 files), Docker/Makefile
scaffolding.

## Phase 1 — Repo, Backend, Frontend, DB, Docker skeleton [DONE]
## Phase 2 — Ontology, Synthetic Data, File Detection, Extractors [DONE]
## Phase 3 — Classification, Ontology Mapping, Enrichment [DONE]
## Phase 4 — Segmentation & Type-aware Chunking [DONE]
## Phase 5 — Embeddings, Indexing, Hybrid Retrieval [DONE]
## Phase 6 — RAG, Citations, Lineage [DONE]
## Phase 7 — FastAPI wiring, Review workflow, Frontend (all 10 screens) [DONE]
- [x] Dashboard, Documents, Document Detail, Ingestion, Classification,
      Ontology, Search, RAG, Review Queue, Scale Simulator, System Health
- [x] Found + fixed during visual verification: badge/pill backgrounds
      invisible (invalid `var(--x)1a` alpha-suffix CSS — fixed via
      color-mix()); Scale Simulator routing percentages summed to 128%
      instead of 100% (SECONDARY_VALIDATION double-counted — fixed to
      mutually-exclusive bands)

## Phase 8 — Docker/Makefile/scripts [DONE]
- [x] docker-compose.yml (postgres w/ pgvector image, backend, frontend, pgadmin)
- [x] backend/Dockerfile, frontend/Dockerfile
- [x] Makefile + scripts/demo.ps1 (Windows equivalent)
- [x] scripts/run_demo_ingestion.py, scripts/evaluate.py
- [x] Production readiness scorecard page (frontend)

## Phase 9 — Testing & Documentation [DONE — delegated to background agents, verified]
- [x] 100 unit/integration tests, 0 failures, 0 source bugs found
- [x] README.md + 10 docs/*.md files + 7 ADRs

## Final acceptance criteria (spec section 68) — verified live via API + browser
- [x] Upload PDF -> detect -> extract -> classify -> ontology-map -> confidence -> entities/topics -> chunk -> embed -> index -> search -> RAG -> citations -> lineage
- [x] Review Queue shows low-confidence docs; correction workflow tested end-to-end with full audit trail
- [x] Dashboard, Ontology Explorer, Scale Simulator all functional with real data
