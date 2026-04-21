# TASKS.md

## Current task

### T-013: Add fixture-backed asset name search states

Goal:
Let the home-page search workflow resolve supported fixture-backed assets by ticker or asset name, while preserving clear unsupported, unknown, and multi-match states without live calls or invented facts.

This is a narrow frontend/search-state task. The backend `/api/search` already supports deterministic fixture-backed ticker and name matching, but the home-page `SearchBox` currently resolves only exact ticker keys from local fixtures. Update the fixture-backed frontend search workflow so beginner users can type supported asset names such as Apple, Apple Inc., Vanguard S&P 500 ETF, or Invesco QQQ Trust and see deterministic local results. Keep the workflow local and fixture-backed for this task. Do not add live external market-data, SEC, issuer, news, brokerage, tax, or LLM calls. Do not turn search into advice, ranking, recommendations, portfolio guidance, or market commentary.

Allowed files:

- TASKS.md
- app/page.tsx
- components/SearchBox.tsx
- lib/fixtures.ts
- styles/globals.css
- tests/frontend/smoke.mjs
- tests/integration/test_backend_api.py
- tests/unit/test_safety_guardrails.py
- docs/agent-journal/\*\*

Do not change:

- AGENTS.md
- SPEC.md
- EVALS.md
- docs/learn_the_ticker_PRD.md
- docs/learn_the_ticker_technical_design_spec.md
- backend models, routes, search behavior, comparison generation, chat generation, overview generation, citation validation, or retrieval logic
- retrieval fixture content in `data/`
- asset page rendering
- asset page chat panel behavior
- comparison page rendering
- comparison fixture coverage beyond the existing local `VOO` vs `QQQ` comparison pack
- financial safety rules
- advice-boundary rules
- production dependency files

Acceptance criteria:

- The home-page search accepts supported tickers and supported asset-name queries using local fixture data only, case-insensitively and with leading or trailing whitespace ignored.
- Supported name queries resolve deterministic local matches for at least `Apple`, `Apple Inc.`, `Vanguard S&P 500 ETF`, `S&P 500`, `Invesco QQQ Trust`, and `Nasdaq-100` where the match is supported by existing fixture names, summaries, or source-backed identity fields.
- A single supported match shows a supported state with the canonical ticker, asset name, asset type, exchange, and issuer when available, and the Open action links to `/assets/{ticker}` for that canonical ticker.
- A query that matches more than one supported local fixture, such as a broad ETF name fragment, is not silently guessed. It shows a multi-match or disambiguation state with each matching ticker/name as an asset-page link.
- Unsupported ticker queries such as `BTC`, `ETH`, `TQQQ`, and `SQQQ` still show the existing unsupported-scope message, do not link to an asset page, and do not show factual citation chips or source drawers.
- Unknown ticker or name queries such as `ZZZZ` or a non-fixture company still show an unknown local-fixture state, explicitly say no facts are invented, do not link to an asset page, and do not imply stale or unsupported evidence as a fact.
- Existing quick links for supported examples and `VOO vs QQQ` remain visible.
- Search result copy stays educational and does not include buy/sell/hold recommendations, personalized allocation advice, unsupported price targets, tax advice, brokerage/trading behavior, or certainty around future returns.
- Frontend smoke checks cover ticker search markers, supported asset-name search markers, single-match state, multi-match/disambiguation state, unsupported state, unknown state, and absence of live external search calls.
- If backend search tests are touched, they only assert the existing deterministic local `/api/search` fixture behavior and do not require backend implementation changes or live external calls.
- Existing citation chips, source drawer behavior, freshness labels, stale/unknown labels, comparison source metadata rendering, and asset chat UI behavior remain unchanged.
- No endpoint, frontend helper, test, or CI command makes live external calls.
- No new production dependency is added.
- The main quality gate passes.

Required commands:

- npm test
- npm run typecheck
- npm run build
- python3 -m pytest tests/integration/test_backend_api.py -q
- python3 -m pytest tests/unit/test_safety_guardrails.py -q
- python3 evals/run_static_evals.py
- bash scripts/run_quality_gate.sh

Iteration budget:

- Max 3 Codex implementation loops before reporting blockers.

## Completed

### T-012: Render comparison source metadata on compare page

Goal:
Render comparison source-document metadata on the compare page so beginners can inspect the sources, freshness, and supporting passages behind generated comparison citations.

Completed:

- Reworked `app/compare/page.tsx` to use a comparison-specific fixture shape from `lib/compare.ts` instead of the older `compareFixture` and left-asset primary-source fallback.
- Added `lib/compare.ts` with deterministic `VOO` vs `QQQ` and `QQQ` vs `VOO` compare-page fixtures, comparison citation IDs for benchmark, expense ratio, holdings count, and educational role, same-pack comparison source documents, and unsupported/unknown unavailable states with no citations or source documents.
- Added `getComparisonCitationMetadata` so compare-page citation chips resolve to the matching comparison source document and related claim context.
- Added `components/ComparisonSourceDetails.tsx` to render comparison source document ID, title, source type, publisher, URL, published or as-of date, retrieved timestamp, freshness state, official-source badge, related comparison claims, and supporting passage.
- Updated `CitationChip` to expose `data-source-document-id` and `data-freshness-state` markers used by comparison source metadata smoke checks.
- Updated compare-page unavailable states so unsupported, unknown, or unavailable comparison pairs show an unavailable comparison source-pack label and explicitly avoid factual citation chips or source drawers.
- Added source-context list styling in `styles/globals.css`.
- Extended frontend smoke checks to cover comparison source metadata markers, chip-to-source linkage markers, official-source display, freshness display, supporting passages, absence of live compare calls, absence of `/api/compare` calls from the fixture-backed compare page, and absence of `AAPL` sources in comparison metadata.
- Extended safety guardrail frontend-copy coverage to include `components/ComparisonSourceDetails.tsx` and `lib/compare.ts`.
- T-012 agent journal records that `npm test`, `npm run typecheck`, `npm run build`, focused comparison/API pytest, safety pytest, static evals, and the main quality gate passed. The initial `npm test` and `npm run typecheck` required one focused revision to make smoke citation markers literal and narrow the comparison bottom-line value.
- Remaining documented risk: comparison source rendering remains deterministic and fixture-backed for the existing local `VOO` vs `QQQ` / `QQQ` vs `VOO` comparison pack only.
- Remaining documented risk: frontend coverage is static smoke coverage plus build/typecheck; it does not browser-click citation chips to verify scrolling or focus behavior.

Completion commits:

- `b5f1d1d feat(T-012): render comparison source metadata on compare page`
- `ecacb1b chore(T-012): merge render comparison source metadata on compare page`

### T-011: Add comparison source metadata contract

Goal:
Expose source-document metadata for comparison citations so UI clients can render source drawer details for generated comparison answers without making unsupported assumptions from citation IDs alone.

Completed:

- Added `source_documents` to `CompareResponse`.
- Updated deterministic comparison generation so citation bindings carry both citation metadata and full `SourceDocument` metadata built from same-pack comparison source fixtures.
- Supported `VOO` vs `QQQ` comparison responses now include deduplicated source-document metadata for cited comparison facts and supporting chunks.
- Reverse-order `QQQ` vs `VOO` comparison responses include source-document metadata bound to the reversed local comparison pack and selected assets.
- Unavailable, unsupported, and unknown comparison responses return empty key differences, no beginner bottom line, no factual citations, and no source documents.
- Comparison validation now checks source metadata after citation validation and rejects missing citation metadata, wrong-asset source documents, stale sources, unsupported source types, and empty supporting passages.
- Backend route tests cover serialized `/api/compare` source metadata, including source document ID, title, publisher, source type, URL, published or as-of date, retrieved timestamp, freshness state, official-source flag, and supporting passage.
- Unit tests cover schema-valid source-backed comparison metadata, reverse-order metadata, unavailable responses with no metadata, and validation failures for missing, wrong-asset, stale, unsupported, and insufficient source metadata.
- Static evals cover comparison source metadata same-pack binding, reverse-order source binding, required source metadata fields, unavailable responses with no source metadata, and no live external calls.
- T-011 agent journal records that focused comparison/API tests, static evals, backend compile check, and the main quality gate passed.
- Remaining documented risk: comparison source metadata is deterministic and fixture-backed for the existing local `VOO` vs `QQQ` comparison pack only.
- Remaining documented risk: UI rendering of comparison `source_documents` was intentionally not included in this backend/API contract task.

Completion commits:

- `f9313b1 feat(T-011): add comparison source metadata contract`
- `e9b9c7f chore(T-011): merge comparison source metadata contract`

### T-010: Add asset page chat panel for fixture-backed assets

Goal:
Add a beginner-facing asset page chat panel that calls the grounded chat API for fixture-backed supported assets and renders citations, source metadata, advice redirects, unsupported states, and insufficient-evidence states.

Completed:

- Added `AssetChatPanel` to asset pages for fixture-backed assets and wired `app/assets/[ticker]/page.tsx` to render it.
- Added a client-side chat workflow with starter prompts, text input, submit control, empty state, loading state, error state, answer state, and explicit advice redirect, unsupported or unknown, and insufficient-evidence labels.
- Added `lib/assetChat.ts` with typed chat response shapes and an injectable `postAssetChat` helper that calls the local relative `/api/assets/{ticker}/chat` endpoint.
- Rendered supported chat answers with direct answer, `why_it_matters`, uncertainty notes, citation chips, and chat source metadata details including title, source type, publisher, published or as-of date, retrieved timestamp, freshness state, official-source badge, source URL, chunk/source IDs, and supporting passage.
- Rendered no-citation copy for educational redirects, unsupported states, and insufficient-evidence states without inventing factual claims.
- Frontend smoke checks now cover the chat panel, local endpoint helper, chat state markers, source metadata hooks, educational redirect copy, unsupported or unknown copy, insufficient-evidence copy, and no live external chat URLs.
- Safety guardrail tests include the new asset chat panel in frontend copy checks.
- T-010 agent journal records that `npm test`, `npm run typecheck`, `npm run build`, static evals, and the main quality gate passed. The initial `npm test` failed because the new smoke check rejected existing fixture source URLs; the check was narrowed to the new chat helper/component and passed on rerun.
- Remaining documented risk: the frontend chat helper uses the local relative `/api/assets/{ticker}/chat` path, so deployment still needs the frontend and backend served or proxied so that path resolves at runtime.
- Remaining documented risk: frontend coverage is static smoke coverage, not browser automation of typed questions and rendered network responses.

Completion commits:

- `6f51ae2 feat(T-010): add asset page chat panel for fixture-backed assets`
- `167f1b9 chore(T-010): merge asset page chat panel for fixture-backed assets`

### T-009: Add chat source metadata contract

Goal:
Expose source-document metadata for grounded chat citations so UI clients can render source drawer details for chat answers without making unsupported assumptions from citation IDs alone.

Completed:

- Added chat source metadata fields to the backend response models.
- Grounded chat responses now include source-document metadata derived from the selected asset knowledge pack.
- Chat source metadata includes citation ID, source document ID, title, source type, URL, as-of date, retrieved timestamp, freshness state, stale flag, and supporting passage where available.
- Supported grounded chat responses for `AAPL`, `VOO`, and `QQQ` include source metadata for grounded citations.
- Advice-like redirects, unsupported assets, unknown assets, and insufficient-evidence responses continue to return no generated factual citations or source metadata.
- Chat validation now checks response source metadata against selected-pack citation evidence.
- Backend route tests cover the serialized `source_documents` shape.
- Static evals cover chat source metadata same-asset binding and no live external calls.
- T-009 agent journal records that the focused pytest slice, static evals, and main quality gate passed.
- Remaining documented risk: chat source metadata remains deterministic and fixture-backed for the current supported assets.
- Remaining documented risk: UI rendering for the new chat `source_documents` field was not changed in this backend-only task.

Completion commits:

- `8306738 feat(T-009): add chat source metadata contract`

### T-008: Add grounded asset chat pipeline

Goal:
Generate asset-specific chat responses from selected asset knowledge packs, citation mappings, and safety classification.

Completed:

- Added deterministic grounded chat generation in `backend/chat.py`.
- Backend `/api/assets/{ticker}/chat` now uses the grounded chat pipeline for fixture-backed supported assets.
- Supported educational chat works for `AAPL`, `VOO`, and `QQQ`.
- Chat intent handling covers asset identity, stock business basics, ETF holdings or benchmark basics, ETF cost or breadth questions, top risks, recent developments, and beginner educational suitability framing.
- Generated supported chat responses include canonical asset identity, a direct answer, `why_it_matters`, citations when evidence exists, source-backed uncertainty or limits notes, and an educational safety classification.
- Chat citation binding is restricted to source documents and chunks from the selected asset knowledge pack.
- Advice-like questions continue to redirect into educational framing without generated factual claims or citations.
- Unsupported and unknown assets continue to return clear unsupported-scope or unknown states without generated factual claims.
- Static evals and tests cover schema validity, supported chat intents, same-asset citation binding, advice redirects, unsupported states, insufficient-evidence behavior, safety phrasing, and no live external calls.
- T-008 agent journal records that focused chat tests, the required safety/API test slice, static evals, and the main quality gate passed.
- Remaining documented risk: chat generation is deterministic and fixture-backed for `AAPL`, `VOO`, and `QQQ`; unsupported, unknown, or non-fixture-backed assets intentionally return redirect or insufficient-evidence states.
- Remaining documented risk: intent handling is narrow by design and covers only the beginner intents required for this task.
- Remaining documented risk: `ChatResponse` still exposes chat citations as source document and chunk IDs rather than full source-document metadata; richer source drawer behavior would need a later schema/UI extension.

Completion commits:

- `37e6f59 feat(T-008): add grounded asset chat pipeline`
- `dbbab3c chore(T-008): merge grounded asset chat pipeline`

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

### T-014: Add beginner chat starter prompts
