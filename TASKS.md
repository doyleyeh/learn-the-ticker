# TASKS.md

## Current task

### T-001: Create backend FastAPI skeleton

Goal:
Create the initial backend service structure for search, asset overview, sources, recent developments, compare, and asset-grounded chat endpoints.

This is a skeleton task. It should define stable routes, response shapes, validation, and tests, but it must not add live market-data, SEC, issuer, news, or LLM calls yet.

Allowed files:

- TASKS.md
- Makefile
- requirements.txt
- requirements-dev.txt
- backend/\*\*
- tests/\*\*
- scripts/\*\*
- .github/\*\*
- docs/agent-journal/\*\*

Do not change:

- AGENTS.md
- SPEC.md
- EVALS.md
- docs/learn_the_ticker_PRD.md
- docs/learn_the_ticker_technical_design_spec.md
- product requirements
- financial safety rules
- advice-boundary rules

Acceptance criteria:

- A backend FastAPI app exists under `backend/`.
- The app exposes a health endpoint.
- The app exposes the initial API surface from the technical design:
  - `GET /api/search?q=VOO`
  - `GET /api/assets/{ticker}/overview`
  - `GET /api/assets/{ticker}/details`
  - `GET /api/assets/{ticker}/sources`
  - `GET /api/assets/{ticker}/recent`
  - `POST /api/compare`
  - `POST /api/assets/{ticker}/chat`
- Endpoint responses use explicit schemas or typed models.
- Stub responses are deterministic and educational.
- Unsupported or unknown assets return a clear unsupported or unknown state.
- Chat/advice-like inputs are redirected into educational framing and do not include buy/sell/hold recommendations, allocation advice, price targets, tax advice, or brokerage/trading behavior.
- No endpoint makes live external calls in normal tests or CI.
- Backend tests cover route availability, schema shape, unsupported states, and the advice-boundary redirect.
- If production dependencies are added, document why they are needed in the relevant dependency file comments or task journal, and keep the dependency set minimal.
- The main quality gate passes.

Required commands:

- bash scripts/run_quality_gate.sh

Iteration budget:

- Max 3 Codex implementation loops before reporting blockers.

## Completed

### T-000: Create agentic development scaffold

Goal:
Set up the files, tests, eval folders, scripts, and CI workflow needed for Codex-assisted development.

Completed:

- Core agent instruction files exist.
- Quality gate script exists.
- Agent loop script exists.
- Basic repo contract tests pass.
- Basic static evals pass.
- CI workflow runs the quality gate.
- Git commits are created by the harness, not directly by Codex.

Completion commits:

- `4be1fa3 chore: add agentic development scaffold`
- `c7e2004 chore: add agent loop retries`

## Backlog

### T-002: Create frontend Next.js skeleton

Goal:
Create the initial frontend structure for search, asset page, citation chips, source drawer, and glossary popovers.

### T-003: Add citation validation module

Goal:
Validate that generated claims map to valid source documents, chunks, or facts.

### T-004: Add safety guardrail tests

Goal:
Detect buy/sell language, personalized allocation advice, unsupported price targets, and certainty around future returns.

### T-005: Add source-backed retrieval fixtures

Goal:
Create local fixture data and retrieval contracts for supported stocks and ETFs without live external calls in CI.

### T-006: Add asset overview generation pipeline

Goal:
Generate beginner asset overview responses from structured local facts, source metadata, and citation mappings.
