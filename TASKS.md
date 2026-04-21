# TASKS.md

## Current task

### T-008: Add grounded asset chat pipeline

Goal:
Generate asset-specific chat responses from selected asset knowledge packs, citation mappings, and safety classification.

This is a deterministic backend chat-pipeline task. It should replace the remaining stub chat response path with a source-backed local generation path that answers bounded beginner questions from `AssetKnowledgePack` data for fixture-backed supported assets. It must keep advice-like questions on the existing educational redirect path, keep unsupported assets on the unsupported redirect path, and must not add live external market-data, SEC, issuer, news, brokerage, tax, or LLM calls.

Allowed files:

- TASKS.md
- backend/\*\*
- data/\*\*
- tests/\*\*
- evals/\*\*
- scripts/\*\*
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
- frontend UI or visual design
- comparison generation behavior except where shared citation or safety helpers must stay compatible
- overview generation behavior except where shared citation or safety helpers must stay compatible
- production dependency files unless a dependency is clearly justified
- endpoint response schemas unless the existing `ChatResponse` contract cannot satisfy citation validation, in which case keep the change minimal and test compatibility

Acceptance criteria:

- A deterministic chat generation module or service builds `ChatResponse`-compatible payloads from `AssetKnowledgePack` data.
- Backend `/api/assets/{ticker}/chat` uses the chat generation pipeline for fixture-backed supported assets instead of the previous generic stub summary path.
- Supported educational chat works for `AAPL`, `VOO`, and `QQQ`.
- Generated supported chat answers include:
  - the canonical asset identity
  - a direct answer
  - a beginner-friendly `why_it_matters`
  - at least one citation for factual claims when evidence exists
  - an uncertainty or limits note that names missing, partial, stale, unavailable, or fixture-bounded evidence when relevant
  - `educational` safety classification for safe educational questions
- The deterministic question handling covers a narrow but useful set of beginner intents:
  - asset identity or "what is this?"
  - stock business basics for supported stocks when local evidence exists
  - ETF holdings, benchmark, breadth, or cost basics for supported ETFs when local evidence exists
  - top-risk or "biggest risk" questions from source-backed risk evidence
  - recent-development questions from the recent-development layer
  - educational suitability or "why do beginners consider it?" questions without giving personal advice
- When the selected asset knowledge pack does not contain enough evidence for a supported educational question, the response says insufficient evidence or unknown, does not invent facts, and does not attach unsupported citations.
- Chat citations bind only to source documents and chunks from the selected asset knowledge pack.
- Chat citation validation rejects or surfaces missing citations, wrong-asset citations, stale-unlabeled citations, unsupported source types, and insufficient evidence.
- Advice-like questions continue to redirect into educational framing with no citations and no factual claims beyond the redirect.
- Unsupported or unknown assets continue to return clear unsupported-scope or unknown states with no generated factual claims or citations.
- Generated chat copy avoids buy/sell/hold recommendations, personalized allocation advice, unsupported price targets, tax advice, brokerage/trading behavior, and certainty around future returns.
- Static evals or focused tests check schema validity, citation coverage, same-asset source binding, supported educational chat intents, advice redirects, unsupported states, stale/unknown/insufficient evidence handling, and no live external calls.
- Existing overview generation tests, comparison generation tests, retrieval fixture tests, citation validation, safety evals, backend route tests, frontend smoke checks, static evals, and quality gate behavior continue to pass.
- No endpoint, test, or CI command makes live external calls.
- If dependencies are added, document why they are needed and keep the dependency set minimal.
- The main quality gate passes.

Required commands:

- python3 -m pytest tests/unit/test_safety_guardrails.py tests/integration/test_backend_api.py -q
- python3 evals/run_static_evals.py
- bash scripts/run_quality_gate.sh

Iteration budget:

- Max 3 Codex implementation loops before reporting blockers.

## Completed

### T-007: Add comparison generation pipeline

Goal:
Generate beginner comparison responses from structured local facts, comparison knowledge packs, source metadata, and citation mappings.

Completed:

- Added deterministic comparison generation in `backend/comparison.py`.
- Backend `/api/compare` now uses `generate_comparison` for fixture-backed comparison responses.
- Supported `VOO` vs `QQQ` comparison generation works in either ticker order.
- Generated ETF comparison responses include canonical left/right assets, supported state, `etf_vs_etf` type, key differences for benchmark, expense ratio, holdings count, breadth, educational role, a beginner bottom line, and citations.
- Comparison citation binding maps generated citation IDs to same-pack source documents, normalized facts, and source chunks from the local comparison knowledge pack.
- Comparison validation covers generated responses and planned claims, including missing citations, wrong-asset citations, stale sources, unsupported source types, and insufficient evidence.
- Unsupported, unknown, or unavailable comparison requests return `unavailable` comparison state without key differences, bottom-line content, or citations.
- Static evals now include the generated comparison contract, reverse ticker order, unavailable states, same-pack citation binding, safety phrase checks, and no network-client imports.
- Focused unit and integration tests were added for comparison generation and `/api/compare`.
- T-007 agent journal records that focused comparison/API tests, static evals, backend compile check, and the main quality gate passed.
- Remaining documented risk: comparison generation is deterministic and fixture-backed for `VOO` vs `QQQ` only; other supported ticker pairs intentionally return an unavailable comparison state until a local comparison pack exists.
- Remaining documented risk: `CompareResponse` exposes citation metadata but not full comparison source documents, so source drawer-style rendering would need a later schema/UI extension if required.

Completion commits:

- `46b05f2 feat(T-007): add comparison generation pipeline`
- `285948d chore(T-007): merge comparison generation pipeline`

### T-006: Add asset overview generation pipeline

Goal:
Generate beginner asset overview responses from structured local facts, source metadata, and citation mappings.

Completed:

- Deterministic overview generation exists in `backend/overview.py`.
- Supported overview generation works for fixture-backed `AAPL`, `VOO`, and `QQQ`.
- Generated overviews include canonical identity, state, freshness metadata, snapshot fields, beginner summary, exactly three top risks, separated recent developments, suitability summary, claims, citations, and source documents.
- Citation IDs generated for claims, summary facts, risks, and recent developments resolve to same-asset sources.
- Unsupported and unknown assets return explicit states without generated factual claims, invented summaries, or citations.
- Backend asset overview, source, and recent routes use generated overview output for fixture-backed assets.
- Tests and static evals cover schema validity, citation coverage, top-risk count, freshness fields, stable/recent separation, unsupported states, safety language, and no live external calls.
- Existing retrieval fixture tests, citation validation, safety evals, backend route tests, frontend smoke checks, static evals, and quality gate behavior pass.

Completion commits:

- `0f4fd70 feat(T-006): add asset overview generation pipeline`
- `910761c Merge pull request #6 from doyleyeh/agent/T-006-20260420T214313Z`

### T-005: Add source-backed retrieval fixtures

Goal:
Create local fixture data and retrieval contracts for supported stocks and ETFs without live external calls in CI.

Completed:

- Local retrieval fixture data exists in `data/retrieval_fixtures.json` for `AAPL`, `VOO`, and `QQQ`.
- Retrieval models and services exist in `backend/retrieval.py`.
- Asset knowledge packs include canonical identity, source document metadata, stable chunk IDs, normalized facts, freshness fields, recent-development layer data, and explicit evidence gaps.
- Single-asset retrieval is filtered to the requested asset and does not return wrong-asset evidence.
- Comparison retrieval builds a bounded `VOO` vs `QQQ` comparison pack.
- Tests and static evals check fixture shape, source linkage, asset filtering, freshness metadata, explicit evidence states, and no network-client imports.
- Existing citation validation, safety evals, backend route tests, frontend smoke checks, static evals, and quality gate behavior pass.

Completion commits:

- `ef731a3 agent(T-005): implement current task`
- `92c54c9 Merge pull request #5 from doyleyeh/agent/T-005-20260420T205818Z`

### T-004: Add safety guardrail tests

Goal:
Add deterministic safety guardrail tests and eval coverage that detect buy/sell/hold recommendation leakage, personalized allocation advice, unsupported price targets, tax advice, brokerage/trading behavior, and certainty around future returns.

Completed:

- Safety eval cases cover direct buy/sell/hold questions, allocation or position sizing, unsupported price targets, tax advice, brokerage/trading execution, future-return certainty, unsupported assets, and safe educational prompts.
- Static safety evals check backend chat outputs and forbidden output phrases, not only fixture structure.
- Backend chat tests verify advice-like questions redirect into educational framing and return no citations unless grounded in supported asset facts.
- Safety tests assert forbidden phrases do not appear in backend responses, frontend copy, fixture summaries, or comparison output.
- Safe educational prompts continue to produce grounded educational responses.
- Unsupported asset prompts redirect into clear unsupported-scope language.
- Existing citation validation, backend route, frontend smoke, static eval, and quality gate behavior pass.

Completion commits:

- `3be6ff1 agent(T-004): implement current task`
- `08f68d0 Merge pull request #4 from doyleyeh/agent/T-004-20260420T182024Z`

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
