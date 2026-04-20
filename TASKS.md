# TASKS.md

## Current task

### T-004: Add safety guardrail tests

Goal:
Add deterministic safety guardrail tests and eval coverage that detect buy/sell/hold recommendation leakage, personalized allocation advice, unsupported price targets, tax advice, brokerage/trading behavior, and certainty around future returns.

This is a safety-test task. It should strengthen classifiers, fixtures, evals, and tests for existing backend/frontend outputs, but it must not add live external market-data, SEC, issuer, news, brokerage, tax, or LLM calls.

Allowed files:

- TASKS.md
- Makefile
- backend/\*\*
- lib/\*\*
- app/\*\*
- components/\*\*
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
- production dependency files unless a dependency is clearly justified

Acceptance criteria:

- Safety eval cases include representative prompts for:
  - direct buy/sell/hold questions
  - personalized allocation or position sizing
  - unsupported price targets
  - tax advice
  - brokerage/trading execution
  - certainty around future returns
  - unsupported assets such as crypto, leveraged ETFs, and inverse ETFs
- A deterministic safety test or eval runner checks outputs, not only input fixture structure.
- Backend chat tests verify advice-like questions are redirected into educational framing and return no citations unless the answer is grounded in supported asset facts.
- Safety tests assert forbidden phrases do not appear in backend responses, frontend copy, fixture summaries, or comparison output.
- Safe educational prompts still produce educational responses rather than being over-blocked.
- Unsupported asset prompts are redirected into clear unsupported-scope language.
- Existing citation validation, backend route, frontend smoke, static eval, and quality gate behavior continue to pass.
- No endpoint, test, or CI command makes live external calls.
- If dependencies are added, document why they are needed and keep the dependency set minimal.
- The main quality gate passes.

Required commands:

- bash scripts/run_quality_gate.sh

Iteration budget:

- Max 3 Codex implementation loops before reporting blockers.

## Completed

### T-003: Add citation validation module

Goal:
Add a citation validation module that verifies generated or fixture-backed claims only cite source documents, chunks, or normalized facts that belong to the same asset or comparison pack and support the claim type.

Completed:

- Citation validation module exists in `backend/citations.py`.
- Validator accepts structured claims, citation IDs, source evidence, and asset or comparison-pack context.
- Validator rejects missing citations, nonexistent citations, wrong-asset citations, non-recent sources for recent claims, stale unlabeled sources, unsupported source types, and insufficient evidence.
- Citation eval cases are exercised by deterministic static evals and unit tests.
- Tests cover single-asset claims, comparison claims, recent-development claims, stale/unknown states, and wrong-asset citations.
- Existing backend, frontend, static eval, and quality gate behavior pass.

Completion commits:

- `98be660 agent(T-003): implement current task`
- `78a6508 fix: skip codex review without api key`
- `72535b7 Merge pull request #3 from doyleyeh/agent/T-003-20260420T054020Z`

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

### T-005: Add source-backed retrieval fixtures

Goal:
Create local fixture data and retrieval contracts for supported stocks and ETFs without live external calls in CI.

### T-006: Add asset overview generation pipeline

Goal:
Generate beginner asset overview responses from structured local facts, source metadata, and citation mappings.
