# TASKS.md

## Current task

### T-019: Add richer stock and ETF fixture data for MVP content sections

Goal:
Add richer deterministic local retrieval fixture evidence so the PRD asset overview sections introduced in T-018 can carry more source-backed stock and ETF content without live calls, frontend rendering changes, or schema changes.

Task scope:
This is a fixture, retrieval-contract, and deterministic overview-generation task. Expand the existing local retrieval fixtures for `AAPL`, `VOO`, and `QQQ` with source documents, source chunks, normalized facts, and explicit evidence gaps that better cover the MVP stock and ETF content sections. Update retrieval and overview generation only as needed to surface the new fixture-backed facts through the existing T-018 `sections` contract. Preserve all product guardrails: citations for important factual claims, section-level freshness or explicit unknown/stale/unavailable states, stable facts separated from recent developments, no live external calls, and educational framing instead of investment advice. Keep this narrow; do not implement frontend rendering, provider adapters, ingestion workers, caching, export, glossary, or new asset coverage.

Allowed files:

- data/retrieval_fixtures.json
- backend/retrieval.py
- backend/overview.py
- tests/unit/test_retrieval_fixtures.py
- tests/unit/test_overview_generation.py
- tests/unit/test_safety_guardrails.py
- tests/integration/test_backend_api.py
- evals/run_static_evals.py
- docs/agent-journal/

Do not change:

- backend/models.py
- app/
- components/
- lib/
- styles/
- backend/chat.py
- backend/comparison.py
- backend/citations.py
- backend/ingestion.py
- backend/search.py
- package files
- docs other than the agent journal
- provider adapter, ingestion worker, queue, cache, or export implementations
- frontend asset-page rendering
- generated chat or comparison behavior
- generated behavior for unsupported, unknown, ambiguous, or eligible-not-cached assets
- asset coverage beyond the existing `AAPL`, `VOO`, and `QQQ` fixture-backed generated overview assets

Acceptance criteria:

- Expand `data/retrieval_fixtures.json` for `AAPL` with same-asset source chunks and normalized facts that support richer stock PRD sections beyond primary business and top risks, including at least products/services detail, one source-backed strength or business-quality point, one financial-quality metric or trend item, and one valuation-context metric or explicit sourced valuation limitation.
- Expand `data/retrieval_fixtures.json` for both `VOO` and `QQQ` with same-asset source chunks and normalized facts that support richer ETF PRD sections beyond benchmark, expense ratio, holdings count, and top risks, including at least holdings/exposure detail, construction or methodology detail, and one cost/trading-context metric or explicit sourced trading-data limitation.
- Every new normalized fact references an existing or newly added source document and source chunk for the same asset; fixture validation rejects wrong-asset references, dangling source IDs, dangling chunk IDs, and duplicate IDs.
- New fixture source metadata includes source type, publisher, URL or local fixture URL, published/as-of date where applicable, retrieved timestamp, freshness state, and official-source status consistent with the existing fixture conventions.
- Existing overview sections consume the new fixture-backed facts where appropriate and reduce `unknown`, `unavailable`, `mixed`, `stale`, or `insufficient_evidence` states only when the new fixture evidence directly supports the section item or metric.
- Fields that still lack fixture evidence remain explicit gaps with no invented metrics, holdings, alternatives, source documents, or citations.
- Important factual claims introduced through the richer section content carry citation IDs and source document IDs that validate against the same asset knowledge pack.
- Recent-development fixture entries and overview sections remain separate from stable asset facts; do not turn recent-review fixture text into canonical business, holdings, valuation, or cost facts.
- Top risks still expose exactly three items first for each supported generated overview.
- Unsupported assets such as `BTC`, leveraged/inverse ETF examples, unknown tickers, ambiguous search results, and eligible-not-cached assets such as `SPY` and `MSFT` must not receive generated overview sections, generated factual claims, citations, source documents, generated routes, chat answers, or comparison output as part of this task.
- New fixture and overview copy remains educational and avoids buy/sell/hold, allocation, price-target, tax, brokerage, or personalized recommendation language.
- Backend API tests verify `/api/assets/{ticker}/overview` serializes the richer stock and ETF section content while preserving unsupported and unknown empty states.
- Static evals cover richer stock fixture coverage, richer ETF fixture coverage, same-asset citation binding for new section items and metrics, explicit residual evidence gaps, stable/recent separation, top-risk count, safety copy, and absence of live external calls.
- Normal CI remains deterministic and does not require provider credentials, market-data calls, news calls, LLM calls, Redis, PostgreSQL, queues, or network access.

Required commands:

- git status --short
- python3 -m pytest tests/unit/test_retrieval_fixtures.py tests/unit/test_overview_generation.py tests/unit/test_safety_guardrails.py tests/integration/test_backend_api.py -q
- python3 -m pytest tests -q
- python3 evals/run_static_evals.py
- bash scripts/run_quality_gate.sh

Iteration budget:
Max 2 attempts

## Completed

### T-018: Expand asset overview schema for PRD content sections

Goal:
Expand the backend asset overview response schema so supported stock and ETF pages can expose the PRD-required content sections with citations, freshness, and explicit unknown/stale/unavailable states before richer fixtures and frontend rendering are added.

Completed:

- Added overview section contract models in `backend/models.py`, including `EvidenceState`, `OverviewSectionType`, `OverviewMetric`, `OverviewSectionItem`, and `OverviewSection`.
- Extended `OverviewResponse` with a `sections` field while preserving the existing `beginner_summary`, `top_risks`, `recent_developments`, `suitability_summary`, `claims`, `citations`, and `source_documents` fields.
- Updated deterministic overview generation in `backend/overview.py` so fixture-backed stock overview responses expose `business_overview`, `products_services`, `strengths`, `financial_quality`, `valuation_context`, `top_risks`, `recent_developments`, and `educational_suitability` sections.
- Updated deterministic overview generation so fixture-backed ETF overview responses expose `fund_objective_role`, `holdings_exposure`, `construction_methodology`, `cost_trading_context`, `etf_specific_risks`, `similar_assets_alternatives`, `recent_developments`, and `educational_suitability` sections.
- Added section-level citation IDs, source document IDs, freshness state, evidence state, as-of dates, retrieved timestamps, limitations, items, and metrics where supported by the existing local retrieval packs.
- Represented missing fixture evidence as explicit `unknown`, `unavailable`, `stale`, `mixed`, `insufficient_evidence`, or `no_major_recent_development` states instead of inventing unsupported strengths, financial-quality metrics, valuation metrics, holdings details, trading metrics, alternatives, or recent events.
- Kept recent-development section data separate from stable asset basics, including source/as-of or retrieved-date context where the existing models provide it.
- Preserved exactly three top risks first for supported generated overviews.
- Kept unsupported and unknown assets such as `BTC` and `ZZZZ` blocked from generated PRD sections, generated factual claims, citations, source documents, and generated routes.
- Extended backend API tests so `/api/assets/VOO/overview` and `/api/assets/AAPL/overview` serialize the new section schema while unsupported and unknown overview responses keep empty `sections`.
- Extended overview unit tests and static evals for stock section presence, ETF section presence, same-asset citation/source binding for section items and metrics, explicit evidence-gap handling, stable/recent separation, top-risk count, safety copy, and absence of live external calls.
- Added `docs/agent-journal/20260422T050742Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-018 agent journal records that `git status --short`, focused backend/API/safety pytest, full pytest, static evals, and the full quality gate passed.
- T-018 agent journal records focused backend/API/safety pytest as 29 passed, the full pytest suite as 73 passed, static evals as passed, and the quality gate as passed including Python tests, static evals, frontend smoke checks, typecheck, production build, and backend checks.
- Remaining documented risk: the new overview sections are deterministic and fixture-backed only; they do not add richer source data, provider adapters, live ingestion, embeddings, LLM calls, or frontend rendering.
- Remaining documented risk: several PRD sections intentionally return `unknown`, `unavailable`, `stale`, `mixed`, or `insufficient_evidence` states because current local packs do not contain enough evidence for detailed strengths, financial quality, holdings exposure, trading metrics, or alternatives.
- Remaining documented risk: unsupported, unknown, and eligible-not-cached assets remain blocked from generated PRD sections, citations, source documents, chat answers, comparisons, and generated routes.

Completion commits:

- `a7564f4 feat(T-018): expand asset overview schema for PRD content sections`
- `d8c52a9 chore(T-018): merge expand asset overview schema for PRD content sections`

### T-017: Add on-demand ingestion job-state contract

Goal:
Define a deterministic backend/API contract for on-demand ingestion job states so eligible-but-not-cached assets from search can expose a future ingestion path without making live provider calls or generating unsupported pages.

Completed:

- Added typed ingestion job models in `backend/models.py`, including job type, job state, worker status, retryability, capabilities, error metadata, status URL, timestamps, generated route, and page/chat/comparison capability flags.
- Added deterministic fixture-backed ingestion service functions in `backend/ingestion.py` for requesting ingestion by ticker and reading job status by stable job ID.
- Wired `POST /api/admin/ingest/{ticker}` and `GET /api/jobs/{job_id}` in `backend/main.py`.
- Eligible-not-cached fixtures such as `SPY` and `MSFT` return deterministic on-demand job states with stable IDs such as `ingest-on-demand-spy` and `ingest-on-demand-msft`.
- Re-requesting an eligible-not-cached ticker is deterministic and does not depend on random IDs, wall-clock timing, live queues, provider credentials, market-data calls, news calls, or LLM calls.
- Cached supported fixtures such as `AAPL`, `VOO`, and `QQQ` return no-ingestion-needed behavior while preserving generated route and generated page/chat/comparison capability flags.
- Recognized unsupported assets such as `BTC`, `TQQQ`, and `SQQQ` return unsupported non-job states with no generated-page, chat, or comparison capabilities.
- Unknown tickers return unknown non-job states with no invented asset facts, job ID, citations, or generated route.
- Added fixture status coverage for pending, running, succeeded, refresh-needed, failed, and unavailable job states, including a deterministic failed job error code `fixture_ingestion_failed`.
- Extended search classification output so eligible-not-cached results expose `can_request_ingestion` and an ingestion request route, while cached, unsupported, ambiguous, and unknown states remain structurally blocked.
- Added focused unit and integration coverage in `tests/unit/test_ingestion_jobs.py`, `tests/unit/test_search_classification.py`, and `tests/integration/test_backend_api.py`.
- Added ingestion eval cases in `evals/ingestion_eval_cases.yaml` and extended `evals/run_static_evals.py` plus `evals/search_eval_cases.yaml` for ingestion request/status states, capability flags, deterministic reruns, and no live external calls.
- Added `docs/agent-journal/20260422T044335Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-017 agent journal records that `git status --short`, focused ingestion/search/API pytest, full pytest, `npm test`, static evals, and the full quality gate passed.
- Remaining documented risk: the ingestion contract is deterministic and fixture-backed only; it does not start real queues, fetch sources, parse documents, generate embeddings, call providers, or call LLMs.
- Remaining documented risk: eligible-not-cached assets such as `SPY` and `MSFT` expose request/status job states but still do not receive generated asset pages, chat answers, comparisons, citations, source documents, or new facts.
- Remaining documented risk: admin ingestion routes are unauthenticated in this local skeleton; the technical design still requires authentication and rate limiting before production use.

Completion commits:

- `188ce86 feat(T-017): add on-demand ingestion job-state contract`
- `226744d chore(T-017): merge on-demand ingestion job-state contract`

### T-016: Define search support-classification contract

Goal:
Define a deterministic search support-classification contract that lets backend clients distinguish cached supported assets, recognized-but-unsupported assets, unknown assets, ambiguous matches, and eligible assets that would require on-demand ingestion later.

Completed:

- Added structured search support-classification models in `backend/models.py`, including response/result status enums, support classifications, disambiguation and ingestion flags, generated routes, and generated page/chat/comparison capability flags.
- Added deterministic fixture-backed search logic in `backend/search.py` and wired `/api/search` in `backend/main.py` to use it.
- Search now ranks cached supported local assets from `ASSETS`, recognized unsupported assets from `UNSUPPORTED_ASSETS` plus search metadata, and eligible-not-cached assets from `ELIGIBLE_NOT_CACHED_ASSETS`.
- Cached supported fixtures such as `AAPL`, `VOO`, and `QQQ` resolve by ticker or name and are marked safe to open only when a local generated asset page is available.
- Ambiguous searches such as `S&P 500 ETF` return multiple candidates and require disambiguation instead of silently choosing a ticker.
- Recognized unsupported examples such as crypto, leveraged ETFs, and inverse ETFs are blocked from generated pages, generated chat, and generated comparisons.
- Unknown searches return an unknown state without invented facts, citations, or generated routes.
- Eligible-but-not-cached examples such as `SPY` and `MSFT` expose the future ingestion-needed contract while remaining blocked from generated page, chat, and comparison output.
- Added focused unit and integration coverage in `tests/unit/test_search_classification.py` and `tests/integration/test_backend_api.py`.
- Added search eval cases in `evals/search_eval_cases.yaml` and static eval checks in `evals/run_static_evals.py` for supported, ambiguous, unsupported, unknown, ingestion-needed, capability flags, and no live external calls.
- Added `docs/agent-journal/20260422T041752Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-016 agent journal records that `git status --short`, focused search/API pytest, full pytest, `npm test`, static evals, and the full quality gate passed.
- Remaining documented risk: search classification is deterministic and fixture-backed only; it does not perform live provider lookup or start ingestion jobs.
- Remaining documented risk: eligible-but-not-cached examples expose the future ingestion-needed contract but intentionally do not generate pages, chat, or comparisons in this task.
- Remaining documented risk: the frontend still uses its existing local search path; this task only defined and tested the backend `/api/search` contract.

Completion commits:

- `b2c71d9 feat(T-016): define search support-classification contract`
- `d49a938 chore(T-016): merge define search support-classification contract`

### T-015: Align MVP control docs with PRD v0.2

Goal:
Update SPEC.md, EVALS.md, TASKS.md, and the technical design spec where needed so the agent loop follows the updated PRD v0.2 MVP direction.

Completed:

- Updated `SPEC.md` so MVP direction covers all eligible U.S.-listed common stocks and plain-vanilla ETFs, recognized-but-unsupported blocking, Massive / ETF Global provider planning, provider licensing review, glossary support, export/download metadata, freshness hashes, and expanded trust metrics.
- Expanded `EVALS.md` with task-specific guidance for search/support classification, glossary/beginner education, export/download, and broader no-live-provider-call expectations across task categories.
- Updated `TASKS.md` backlog from T-016 through T-027 to align with PRD v0.2 MVP sequencing, including search classification, on-demand ingestion job states, PRD asset sections, glossary, export, provider adapters, caching/freshness hashes, and golden asset coverage.
- Updated `docs/learn_the_ticker_technical_design_spec.md` for durable v0.2 architecture details: accountless export behavior, Phase 4 MVP reliability/accountless learning features, caching and freshness-hash work, glossary support, export acceptance, trust metrics, and unsupported asset exclusions.
- Added `docs/agent-journal/20260422T035714Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-015 agent journal records that `git status --short` and `bash scripts/run_quality_gate.sh` passed on attempt 1.
- Remaining documented risk: this was a documentation/control-plane task only; no product behavior was implemented.
- Remaining documented risk: future provider, export, and on-demand ingestion tasks still need mocked tests and licensing review before exposing restricted data or live external calls.

Completion commits:

- `1828e06 docs(T-015): align MVP control docs with PRD v0.2`
- `7231055 chore(T-015): merge align MVP control docs with PRD v0.2`

### T-014: Add beginner chat starter prompts

Goal:
Make the asset-page grounded chat easier for beginners to start by showing asset-aware starter prompts that cover identity, holdings or business model, risks, recent developments, and advice-boundary education.

Completed:

- Updated `components/AssetChatPanel.tsx` with typed deterministic starter prompt intents for identity, stock business model, ETF holdings/exposure, top risk, recent developments, and advice-boundary education.
- Added asset-aware prompt selection so the local stock fixture `AAPL` receives business-model language, while ETF fixtures such as `VOO` and `QQQ` receive holdings and fund-exposure language.
- Preserved the existing local chat submission flow: clicking a starter prompt submits that exact question through the current `postAssetChat` path and leaves loading, error, answer, citation, source metadata, educational redirect, unsupported, and insufficient-evidence rendering in place.
- Added stable frontend markers for smoke checks with `data-chat-starter-group="beginner-prompts"` and per-intent `data-chat-starter-intent` values.
- Added responsive starter prompt styling in `styles/globals.css` so longer beginner questions wrap cleanly and become full-width on narrow viewports.
- Extended frontend smoke checks for starter prompt markers, stock-specific prompt text, ETF-specific prompt text, advice-boundary prompt text, and no live external chat calls.
- Extended safety guardrail tests with explicit forbidden advice-like examples and starter-prompt copy checks.
- T-014 agent journal records that `npm test`, `npm run typecheck`, `npm run build`, `python3 -m pytest tests/unit/test_safety_guardrails.py -q`, `python3 evals/run_static_evals.py`, and `bash scripts/run_quality_gate.sh` passed.
- Remaining documented risk: starter prompts remain deterministic and fixture-aware for the current local supported assets `AAPL`, `VOO`, and `QQQ`.
- Remaining documented risk: frontend coverage is static smoke coverage plus typecheck/build; it does not browser-click every starter prompt.

Completion commits:

- `99adaf3 feat(T-014): add beginner chat starter prompts`
- `e12735a chore(T-014): merge beginner chat starter prompts`

### T-013: Add fixture-backed asset name search states

Goal:
Let the home-page search workflow resolve supported fixture-backed assets by ticker or asset name, while preserving clear unsupported, unknown, and multi-match states without live calls or invented facts.

Completed:

- Updated `components/SearchBox.tsx` with deterministic local fixture search resolution over supported asset tickers, names, asset type, exchange, issuer, beginner summaries, claims, facts, and source-document fields.
- Added case-insensitive, trimmed query handling with scoring so exact ticker and name matches rank ahead of broader text matches.
- Added a multi-match state that lists each matching local fixture as an asset-page link instead of silently choosing one.
- Added supported-result rendering with canonical ticker, asset name, asset type, exchange, and issuer when available, and kept the Open action pointed at `/assets/{ticker}` only for a single supported result.
- Preserved unsupported and unknown states with no asset-page link, including explicit no-invented-facts copy for unknown ticker or name searches.
- Updated search helper text and placeholders to include supported name-search examples such as Apple, Vanguard S&P 500 ETF, Invesco QQQ Trust, and Nasdaq-100.
- Added search result panel styling in `styles/globals.css`.
- Extended frontend smoke checks with markers for local search resolution, supported result, multi-match result, unsupported result, unknown result, result links, supported fixture name examples, and no live external search calls or `/api/search` call from the fixture-backed home search.
- T-013 agent journal records that `npm test`, `npm run typecheck`, `npm run build`, backend API pytest, safety pytest, static evals, and the main quality gate passed.
- Remaining documented risk: home search remains deterministic and fixture-backed for the current local `AAPL`, `VOO`, and `QQQ` fixtures only.
- Remaining documented risk: frontend coverage is static smoke coverage plus typecheck/build; it does not browser-type every search query.

Completion commits:

- `8e963c8 feat(T-013): add fixture-backed asset name search states`
- `e1b59db chore(T-013): merge fixture-backed asset name search states`

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

### T-020: Render stock PRD sections on asset pages
### T-021: Render ETF PRD sections on asset pages
### T-022: Add Beginner Mode and Deep-Dive Mode page structure
### T-023: Add hybrid glossary baseline terms and UI hooks
### T-024: Add export/download contracts for pages, comparisons, sources, and chat
### T-025: Add provider adapter interfaces with mocked tests
### T-026: Add caching and freshness-hash contracts
### T-027: Expand golden asset eval coverage for MVP launch universe
