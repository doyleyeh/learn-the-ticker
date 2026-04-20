# TASKS.md

## Current task

### T-003: Add citation validation module

Goal:
Add a citation validation module that verifies generated or fixture-backed claims only cite source documents, chunks, or normalized facts that belong to the same asset or comparison pack and support the claim type.

This is a validation-contract task. It should add deterministic local validation logic, schemas, fixtures, and tests. It must not add live external market-data, SEC, issuer, news, or LLM calls yet.

Allowed files:

- TASKS.md
- Makefile
- requirements.txt
- requirements-dev.txt
- backend/\*\*
- lib/\*\*
- tests/\*\*
- evals/\*\*
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
- frontend visual design except where tests need deterministic citation fixture exports

Acceptance criteria:

- A citation validation module exists in the backend or shared project code.
- The validator accepts structured claims, citation IDs, source documents, and asset or comparison-pack context.
- The validator rejects:
  - missing citations for important factual claims
  - citations that do not exist
  - citations from the wrong asset
  - recent-development claims that cite non-recent sources
  - stale sources unless the claim or result labels them stale
  - citations whose supporting source type does not support the claim type
- The validator returns explicit statuses such as valid, missing citation, wrong asset, stale source, unsupported source, or insufficient evidence.
- Supported asset fixtures and comparison fixtures can be checked without live external calls.
- Citation eval cases in `evals/citation_eval_cases.yaml` are exercised by tests or a deterministic eval runner.
- Tests cover single-asset claims, comparison claims, recent-development claims, stale/unknown states, and wrong-asset citations.
- Existing backend, frontend smoke, static eval, and quality gate behavior continue to pass.
- No endpoint, test, or CI command makes live external calls.
- If dependencies are added, document why they are needed and keep the dependency set minimal.
- The main quality gate passes.

Required commands:

- bash scripts/run_quality_gate.sh

Iteration budget:

- Max 3 Codex implementation loops before reporting blockers.

## Completed

### T-002: Create frontend Next.js skeleton

Goal:
Create the initial frontend structure for search, asset pages, comparison, citation chips, source drawer, freshness labels, stale/unknown states, and glossary popovers.

Completed:

- Next.js frontend app exists at the repo root using TypeScript.
- Routes exist for `/`, `/assets/[ticker]`, and `/compare`.
- Home page provides a ticker search workflow with supported, unsupported, unknown, and example states.
- Asset page renders deterministic fixture-backed stable facts, recent developments, exactly three top risks, citation chips, freshness labels, source drawer, glossary popovers, and stale/unknown treatment.
- Compare page renders a deterministic `VOO` vs `QQQ` comparison.
- Frontend copy stays educational and avoids buy/sell/hold, allocation, price target, tax, and brokerage behavior.
- Frontend smoke checks and Next build run in the quality gate.
- `package-lock.json` is committed so CI can run `npm ci`.
- Normal tests and CI make no live external calls.

Completion commits:

- `1164a3d agent(T-002): implement current task`
- `098f7ac fix: make frontend checks reproducible`
- `ec66cb2 Merge T-002 frontend skeleton`

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

### T-004: Add safety guardrail tests

Goal:
Detect buy/sell language, personalized allocation advice, unsupported price targets, and certainty around future returns.

### T-005: Add source-backed retrieval fixtures

Goal:
Create local fixture data and retrieval contracts for supported stocks and ETFs without live external calls in CI.

### T-006: Add asset overview generation pipeline

Goal:
Generate beginner asset overview responses from structured local facts, source metadata, and citation mappings.
