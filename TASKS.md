# TASKS.md

## Current task

### T-002: Create frontend Next.js skeleton

Goal:
Create the initial frontend structure for search, asset pages, comparison, citation chips, source drawer, freshness labels, stale/unknown states, and glossary popovers.

This is a skeleton task. It should define stable routes, UI structure, component contracts, and tests, but it must not add live external market-data, SEC, issuer, news, or LLM calls yet. Use deterministic local fixtures or API stubs only.

Allowed files:

- TASKS.md
- Makefile
- package.json
- package-lock.json
- next.config.\*
- tsconfig.json
- postcss.config.\*
- tailwind.config.\*
- app/\*\*
- components/\*\*
- lib/\*\*
- public/\*\*
- styles/\*\*
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
- backend API behavior except test fixtures or integration shims needed by frontend tests
- product requirements
- financial safety rules
- advice-boundary rules

Acceptance criteria:

- A Next.js frontend app exists at the repo root using TypeScript.
- The first screen is the usable product experience: search and beginner asset learning entry point, not a marketing landing page.
- Routes exist for:
  - `/`
  - `/assets/[ticker]`
  - `/compare`
- The home page provides a ticker search workflow with beginner-readable empty, loading, unsupported, and example states.
- The asset page renders a deterministic fixture-backed asset overview with:
  - stable facts separated from recent developments
  - exactly three top risks shown first
  - visible citation chips near important claims
  - freshness or as-of labels
  - unknown/stale state treatment
  - source drawer UI
  - glossary popovers or inline glossary affordances for beginner terms
- The compare page renders a deterministic fixture-backed comparison for at least `VOO` vs `QQQ`.
- UI copy stays educational and does not include buy/sell/hold recommendations, personalized allocation advice, price targets, tax advice, or brokerage/trading behavior.
- Frontend tests or smoke checks verify route rendering, citation chips, source drawer, freshness labels, stale/unknown states, and beginner readability markers.
- No frontend test or normal CI command makes live external calls.
- If production dependencies are added, document why they are needed in the relevant dependency file comments or task journal, and keep the dependency set minimal.
- The main quality gate passes.

Required commands:

- bash scripts/run_quality_gate.sh

Iteration budget:

- Max 3 Codex implementation loops before reporting blockers.

## Completed

### T-001: Create backend FastAPI skeleton

Goal:
Create the initial backend service structure for search, asset overview, sources, recent developments, compare, and asset-grounded chat endpoints.

Completed:

- Backend FastAPI app exists under `backend/`.
- Health, search, asset overview, details, sources, recent, compare, and chat endpoints exist.
- Endpoint responses use explicit typed models.
- Stub responses are deterministic and educational.
- Unsupported and unknown asset states are covered.
- Advice-like chat inputs are redirected into educational framing.
- Normal tests and CI make no live external calls.
- Backend route, schema, unsupported-state, and advice-boundary tests pass.

Completion commits:

- `61b2bd0 chore: fix codex exec approval flag`
- `7bfe0f6 agent(T-001): implement current task`
- `a27ea80 Merge pull request #2 from doyleyeh/agent/T-001-20260420T024831Z`

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
