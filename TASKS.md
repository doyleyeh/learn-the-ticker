## Current task

### T-146: Add optional durable repository smoke for the local fresh-data MVP slice

Goal:
Extend the operator-only local durable repository smoke so the T-144/T-145 fresh-data MVP slice can be checked through already-running Next/FastAPI services with local durable repository settings enabled, while keeping normal CI fixture-backed, deterministic, and free of localhost, live-provider, Docker, LLM, or durable-storage requirements.

Scope:
Build on the existing skip-by-default `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1`, `LEARN_TICKER_LOCAL_DURABLE_SMOKE=1`, and `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1` paths. Add durable-slice assertions and runbook guidance that verify the same local fresh-data slice remains API-backed when local durable repository configuration is present. This is a smoke/instructions/static-contract task only: it should probe already-running services and documented local durable settings, not add backend persistence behavior, migrations, repository implementations, manifest promotion, live AI generation, or deployment work. The smoke must keep the v0.4 frontend workflow markers visible: single-asset home search first, separate comparison workflow, contextual glossary, mobile source/glossary/chat surfaces, stock-vs-ETF relationship badges, and evidence-limited Weekly News Focus.

Allowed files:
- `tests/frontend/smoke.mjs`
- `tests/unit/test_repo_contract.py`
- `docs/local_fresh_data_ingest_to_render_runbook.md`
- `docs/agent-journal/<run-id>.md`

Do not change:
- Do not edit backend route behavior, repository implementations, database migrations, frontend product components, manifests, source allowlists, source-use policy, provider adapters, retrieval fixtures, cache behavior, generated-output logic, or package dependencies unless the user explicitly retasks the cycle.
- Do not make `npm test`, `npm run build`, repo-contract tests, the quality gate, `node tests/frontend/smoke.mjs`, or `scripts/run_local_fresh_data_rehearsal.py --json` require browser startup, localhost ports, local durable storage, live SEC/issuer/Yahoo/provider calls, Docker, or LLM calls.
- Do not print or document real `DATABASE_URL` values, provider keys, OpenRouter keys, signed URLs, object-store credentials, raw provider payloads, raw source text, raw model reasoning, or secret-like tokens.
- Do not promote Top-500 or ETF-500 manifests, approve new sources, bypass Golden Asset Source Handoff for strict/audit-quality evidence, write generated-output cache records as part of required CI, expose raw provider payloads, or unlock generated output for blocked products.

Acceptance criteria:
- Default `node tests/frontend/smoke.mjs`, `npm test`, `npm run build`, repo-contract tests, the local rehearsal command, and the quality gate remain deterministic and clearly skip all localhost, durable, and slice-durable checks unless explicit local-smoke env flags are set.
- The durable slice path runs only under the existing local browser smoke gate and local durable smoke gate, and it is tied to the fresh-data slice smoke gate. If prerequisites are missing, it reports sanitized blockers using env var names/status only.
- The optional command and runbook document all local operator prerequisites: already-running API and web services, `LEARN_TICKER_LOCAL_WEB_BASE`, `LEARN_TICKER_LOCAL_API_BASE`, `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1`, `LEARN_TICKER_LOCAL_DURABLE_SMOKE=1`, `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1`, `DATA_POLICY_MODE=lightweight`, `LIGHTWEIGHT_LIVE_FETCH_ENABLED=true`, `LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true`, placeholder `SEC_EDGAR_USER_AGENT`, `LOCAL_DURABLE_REPOSITORIES_ENABLED=true`, placeholder-only local `DATABASE_URL`, and non-public placeholder `LOCAL_DURABLE_OBJECT_NAMESPACE`.
- The durable prerequisite checks reject or block unsafe object namespaces that look public, signed, credential-bearing, or secret-bearing, and they never print actual DSN, namespace, key, token, signed URL, provider payload, raw source text, or secret values.
- With the durable prerequisites present, the optional smoke probes the T-144 supported slice `AAPL`, `MSFT`, `NVDA`, `VOO`, `SPY`, `VTI`, `QQQ`, and `XLK` through the Next `/api/:path*` proxy and direct FastAPI `/api/assets/{ticker}/fresh-data`, asserts JSON rather than Next HTML fallback, preserves CORS from the configured web origin, and rejects raw-payload or secret exposure.
- Supported stock probes still assert stock identity, renderable supported state, generated-output eligibility, official SEC/source label presence where the API exposes it, provider-derived fallback labeling where present, citations or explicit evidence states, freshness/as-of metadata, and source-drawer/source-count metadata.
- Supported ETF probes still assert ETF identity, renderable partial state, generated-output eligibility, manifest/scope or partial source labeling, provider-derived fallback labeling where present, citations or explicit partial/unavailable evidence states, freshness/as-of metadata, and visible partial/unavailable labels for missing issuer evidence.
- Representative durable stock and ETF rows, at minimum `AAPL` and `VOO`, are checked through running-service contracts for `/api/search`, `/api/assets/{ticker}/overview`, `/api/assets/{ticker}/details`, `/api/assets/{ticker}/sources`, asset JSON export, and source-list JSON export, proving overview, details, export, citation, freshness, and source-drawer surfaces remain API-backed under local durable configuration.
- The durable slice smoke uses repeated representative reads only for smoke-level consistency of stable fields such as ticker, asset type, fetch/render state, generated-output eligibility, source/citation presence, blocked state, and no raw/secret exposure. It must not require exact quote, timestamp, checksum, or payload equality that can vary across live local fetches.
- Blocked regression tickers `TQQQ`, `ARKK`, `BND`, and `GLD` remain generated-output-ineligible in durable optional probes and do not receive generated pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, generated risk summaries, source documents, citations, facts, provider fetches from blocked probes, or generated-output cache writes.
- Existing optional browser smoke for `VOO`/`QQQ` ETF-vs-ETF and `AAPL`/`VOO` stock-vs-ETF remains intact, including comparison-route redirects, stock-vs-ETF relationship badges, single-company-vs-ETF-basket structure, export/chat proxy checks, and no `holding_verified` regression.
- Static repo-contract coverage checks that the runbook contains the durable slice command, skip-by-default behavior, local durable env prerequisites, unsafe namespace/secret boundaries, supported and blocked ticker expectations, no-live-in-CI boundaries, no-secret/no-raw-payload boundaries, and cleanup warnings that local durable cleanup must not touch production databases, buckets, deployment resources, current manifests, candidate manifests, or diff reports.

Out of scope:
- Do not start local web/API services as part of required CI.
- Do not add backend durable repository behavior, migrations, new storage backends, live AI route generation, or Weekly News live acquisition.
- Do not add production dependencies, paid-provider integrations, deployment hardening, recurring jobs, account features, or broad launch-manifest promotion.
- Do not treat lightweight provider fallback as audit-quality source approval.

Required commands:
- `node tests/frontend/smoke.mjs`
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py -q`
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_lightweight_data_fetch.py tests/integration/test_backend_api.py tests/unit/test_search_classification.py tests/unit/test_repo_contract.py -q`
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_slice_smoke.py --json`
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json`
- `npm test`
- `npm run typecheck`
- `npm run build`
- `TMPDIR=/tmp python3 evals/run_static_evals.py`
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh`
- `git diff --check`

Optional operator command to document, not require in CI:
- `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1 LEARN_TICKER_LOCAL_DURABLE_SMOKE=1 LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1 LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000 LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000 DATA_POLICY_MODE=lightweight LIGHTWEIGHT_LIVE_FETCH_ENABLED=true LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true LOCAL_DURABLE_REPOSITORIES_ENABLED=true LOCAL_DURABLE_OBJECT_NAMESPACE=ticker-smoke DATABASE_URL="<local durable repository DSN, placeholder-only>" SEC_EDGAR_USER_AGENT="learn-the-ticker-local/0.1 contact@example.com" TMPDIR=/tmp npm run test:browser-smoke`

Iteration budget:
Max 2 attempts.

## Backlog

### T-147: Add issuer-backed ETF source enrichment for the local fresh-data MVP slice

### T-148: Add lightweight local manual-readiness gate for the MVP slice

### T-149: Add local fresh-data MVP slice comparison and export parity coverage

## Completed

### T-145: Add local fresh-data MVP browser/API smoke for the slice

Goal:
Add opt-in localhost browser/API smoke coverage for the T-144 local fresh-data MVP slice so an operator can verify the running Next/FastAPI path agrees with the deterministic slice contract for supported and blocked tickers without making browser services, live provider calls, or local ports required in normal CI.

Completion details:
- Implementation commit: `d6a451f feat(T-145): add local fresh-data MVP browser/API smoke for the slice`
- Local merge commit: `f25e875 chore(T-145): merge local fresh-data MVP browser/API smoke for the slice` from branch `agent/T-145-20260503T222700Z`
- Added `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE` as an opt-in slice gate under the existing `LEARN_TICKER_LOCAL_BROWSER_SMOKE` localhost browser/API path in `tests/frontend/smoke.mjs`.
- Added T-144 slice constants for supported stocks `AAPL`, `MSFT`, and `NVDA`, supported ETFs `VOO`, `SPY`, `VTI`, `QQQ`, and `XLK`, blocked regression tickers `TQQQ`, `ARKK`, `BND`, and `GLD`, and representative running-service contract rows for `AAPL` and `VOO`.
- Added prerequisite validation for already-running local web/API bases, `DATA_POLICY_MODE=lightweight`, `LIGHTWEIGHT_LIVE_FETCH_ENABLED=true`, `LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true`, and placeholder `SEC_EDGAR_USER_AGENT`, with sanitized blocker output using env var names only.
- Added fresh-data smoke assertions for common lightweight payload schema, stock renderability, ETF partial renderability, blocked generated-output ineligibility, search contracts, overview contracts, details contracts, source-drawer contracts, CORS from the configured local web origin, and JSON responses rather than Next HTML fallback.
- Added `assertNoRawPayloadOrSecretExposure` checks that reject `raw_payload_exposed=true` and secret-like or hidden-output markers including provider key names, bearer/private-key markers, hidden prompts, raw model reasoning, and unrestricted provider payload text.
- The optional slice smoke probes `/api/assets/{ticker}/fresh-data` through both the Next `/api/:path*` proxy and direct FastAPI paths for supported and blocked slice tickers, and checks representative `/api/search`, `/api/assets/{ticker}/overview`, `/api/assets/{ticker}/details`, and `/api/assets/{ticker}/sources` frontend-proxy paths for `AAPL` and `VOO`.
- The blocked ticker probes keep `TQQQ`, `ARKK`, `BND`, and `GLD` generated-output-ineligible with no source documents, citations, facts, generated pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, or generated risk summaries from the slice smoke.
- Existing optional browser smoke coverage for `VOO`/`QQQ` ETF-vs-ETF and `AAPL`/`VOO` stock-vs-ETF remains intact, including comparison-route redirects, stock-vs-ETF relationship badges, the `single-company-vs-ETF-basket` structure, export/chat proxy checks, and no `holding_verified` regression.
- `docs/local_fresh_data_ingest_to_render_runbook.md` documents the opt-in T-145 command, local service and lightweight fetch prerequisites, supported and blocked slice expectations, skip-by-default behavior, CORS/proxy coverage, and no-secret/no-raw-payload boundaries.
- `tests/unit/test_repo_contract.py` adds static coverage that the smoke and runbook contain the T-145 gate, local env prerequisites, supported/blocked ticker markers, fresh-data/search/overview/details/sources probes, v0.4 frontend workflow markers, and no-live-in-CI/no-secret/no-raw-payload boundaries.
- `docs/agent-journal/20260503T222700Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `node tests/frontend/smoke.mjs` - pass
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py -q` - pass (`23 passed`)
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_lightweight_data_fetch.py tests/integration/test_backend_api.py tests/unit/test_search_classification.py tests/unit/test_repo_contract.py -q` - pass (`86 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_slice_smoke.py --json` - pass
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `npm test` - pass
- `npm run typecheck` - pass on rerun after `npm run build` generated `.next/types`
- `npm run build` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`478 passed` in each Python phase plus frontend checks)
- `git diff --check` - pass

Remaining risks:
- The new slice browser/API path is operator-only and was not run against live localhost services in the CI-safe task attempt.
- Live lightweight provider behavior still depends on the operator's local SEC/Yahoo reachability and placeholder `SEC_EDGAR_USER_AGENT` configuration.
- ETF rows remain partial until issuer source-pack automation is completed in later tasks.

### T-144: Add local fresh-data MVP slice smoke contract

Goal:
Define and regression-cover the first local fresh-data MVP slice so the agent loop can move from golden `AAPL`/`VOO` proof toward a repeatable local test basket without changing strict manifest authority, requiring live calls in CI, exposing raw provider payloads, or weakening source/citation/safety boundaries.

Completion details:
- Implementation commit: `b7a3ef8 feat(T-144): add local fresh-data MVP slice smoke contract`
- Local merge commit: `b20446d chore(T-144): merge local fresh-data MVP slice smoke contract` from branch `agent/T-144-20260503T220727Z`
- Added `scripts/run_local_fresh_data_slice_smoke.py` with schema `local-fresh-data-mvp-slice-smoke-v1`, deterministic fake SEC/Yahoo fetcher inputs, and the local MVP slice tickers `AAPL`, `MSFT`, `NVDA`, `VOO`, `SPY`, `VTI`, `QQQ`, and `XLK`, plus blocked regression tickers `TQQQ`, `ARKK`, `BND`, and `GLD`.
- The slice smoke reports policy `lightweight_personal_mvp_only`, `normal_ci_requires_live_calls: false`, `browser_startup_required: false`, `local_services_required: false`, `secret_values_reported: false`, `raw_payload_values_reported: false`, and `raw_payload_exposed_count: 0`.
- The deterministic contract expects status counts of 3 `pass` stock rows, 5 `partial` ETF rows, 4 `blocked` rows, and 0 `unavailable` rows.
- Supported stock rows use official SEC-style fixture data plus provider-derived quote fallback and validate renderable overview/details/source-drawer surface contracts, citations, source counts, three top risks, freshness/as-of metadata, and no raw-payload exposure.
- Supported ETF rows use manifest/scope plus provider-derived fallback fixtures and validate partial renderable overview/details/source-drawer surface contracts, citations, source counts, freshness/as-of metadata, and explicit partial/unavailable issuer-evidence states.
- Blocked rows remain generated-output-ineligible, expose no sources, citations, or facts, use no provider fetch calls, and keep generated pages, generated chat answers, generated comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, generated risk summaries, and generated-output cache entries disabled.
- `scripts/run_local_fresh_data_rehearsal.py` now includes a required `local_fresh_data_mvp_slice_smoke` check, validates the slice status counts and ticker lists, rejects raw-payload/secret/live-call regressions, and surfaces the T-144 slice prerequisite in manual-readiness summaries.
- `docs/local_fresh_data_ingest_to_render_runbook.md` documents the deterministic slice command, expected output for supported and blocked tickers, the `/api/assets/{ticker}/fresh-data` API equivalent, and the optional live lightweight command using `DATA_POLICY_MODE=lightweight`, `LIGHTWEIGHT_LIVE_FETCH_ENABLED=true`, `LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true`, and a placeholder `SEC_EDGAR_USER_AGENT`.
- `tests/unit/test_lightweight_data_fetch.py` and `tests/unit/test_repo_contract.py` cover the deterministic slice contract, no-live/no-service/no-secret/no-raw-payload boundaries, source labels, status counts, rehearsal integration, and runbook markers.
- `docs/agent-journal/20260503T220727Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_slice_smoke.py --json` - pass
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_lightweight_data_fetch.py tests/unit/test_repo_contract.py -q` - pass (`30 passed`)
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_lightweight_data_fetch.py tests/integration/test_backend_api.py tests/unit/test_search_classification.py tests/unit/test_repo_contract.py -q` - pass (`85 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `npm test` - pass
- `npm run typecheck` - pass
- `npm run build` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`477` Python tests in quality-gate phases; static evals, frontend checks, and backend checks passed)
- `git diff --check` - pass

Remaining risks:
- The slice smoke uses deterministic injected fixtures and proves the local contract without live calls; optional live-provider behavior still depends on operator opt-in and provider availability.
- ETF issuer automation remains partial by design, so ETF rows intentionally render partial/unavailable issuer-evidence labels until later source-pack work closes that gap.
- Browser/API localhost proof for the full T-144 slice remains future work and is promoted as T-145.

### T-143: Add stock-vs-ETF comparison readiness gate

Goal:
Add a deterministic stock-vs-ETF comparison readiness signal to the local rehearsal/control-doc layer so the repo can report whether the `AAPL` vs `VOO` feature is locally functional or which exact blocker remains.

Completion details:
- Implementation commit: `4e5d41a feat(T-143): add stock-vs-ETF comparison readiness gate`
- Local merge commit: `7dfb3ad chore(T-143): merge stock-vs-ETF comparison readiness gate` from branch `agent/T-143-20260501T065703Z`
- `scripts/run_local_fresh_data_rehearsal.py` now adds a deterministic `stock_vs_etf_comparison_readiness` required check with schema `stock-vs-etf-comparison-readiness-v1` and review-only boundary `review_only_fixture_backed_no_services_no_live_calls_v1`.
- The readiness check validates the local `AAPL`/`VOO` backend comparison payload: `state.status = supported`, `comparison_type = stock_vs_etf`, `availability_state = available`, `stock-etf-relationship-v1`, `relationship_state = direct_holding`, relationship badges, `single-company-vs-etf-basket`, AAPL/VOO source-reference assets, same-comparison-pack citations/source documents, and absence of the old frontend-only `holding_verified` state.
- The check validates the `AAPL`/`VOO` comparison export as available, same-comparison-pack bound, citation/source backed, carrying `stock_etf_relationship_context`, preserving the educational disclaimer, and containing no forbidden advice phrases detected by `find_forbidden_output_phrases`.
- The check validates the asset-chat compare redirect for `POST /api/assets/VOO/chat` with `AAPL vs VOO`: `safety_classification = compare_route_redirect`, `comparison_availability_state = available`, route `/compare?left=AAPL&right=VOO`, no generated multi-asset factual chat answer, and zero factual citations/source documents in the redirect body.
- The check inspects existing frontend/runbook markers rather than starting localhost services: `A vs B` search remains a separate comparison workflow, the `AAPL`/`VOO` opt-in smoke markers are documented, the Next `/api/:path*` proxy is documented, and the required local API/web environment variables remain documented for operator runs.
- Existing `VOO` vs `QQQ` ETF-vs-ETF readiness remains available and independent of stock-vs-ETF markers.
- Unsupported or missing-pack comparison cases remain blocked in deterministic coverage for `VOO`/`BTC`, `VOO`/`GME`, `VOO`/`SPY`, `VOO`/`ZZZZ`, and `AAPL`/`QQQ`.
- The check publishes blocker reason-code catalog entries for `no_local_pack`, `missing_backend_relationship_schema`, `frontend_only_fallback`, `unavailable_export`, `chat_redirect_mismatch`, `missing_source_citation_metadata`, `missing_local_smoke_instructions`, `unsupported_state_regression`, and `live_call_requirement`.
- The readiness check is wired into required threshold checks and the manual-readiness prerequisite summaries, but a passing stock-vs-ETF readiness check does not make the repo manually ready by itself.
- `docs/local_fresh_data_ingest_to_render_runbook.md` documents stock-vs-ETF local functional readiness as narrow fixture-backed readiness for backend pack, API-aligned frontend markers, export/chat parity, optional localhost smoke instructions, and blocked unsupported/no-local-pack states. It explicitly does not prove broad stock-vs-ETF coverage, live-provider readiness, deployment readiness, production launch readiness, source approval, manifest promotion, generated-output cache writes, or unsupported generated-output unlocks.
- `tests/unit/test_repo_contract.py` now covers the readiness details, required threshold summary, manual-readiness prerequisite summary, blocker catalog, runbook markers, and review-only/no-live/no-service boundaries.
- `docs/agent-journal/20260501T065703Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py -q` - pass (`22 passed`)
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py tests/integration/test_backend_api.py -q` - pass (`60 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `npm test` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`468 passed` in Python phases; static evals, frontend smoke/typecheck/build, and backend checks passed)
- `git diff --check` - pass

Remaining risks:
- The readiness gate proves only deterministic local `AAPL`/`VOO` stock-vs-ETF and existing `VOO`/`QQQ` ETF-vs-ETF behavior; it does not prove broad comparison coverage.
- Optional localhost browser/API smoke remains operator-run and was not started by the deterministic rehearsal.
- Manual fresh-data readiness still reports `agent_work_remaining` because broader ETF-500 and Top-500 source-pack, parser, handoff, freshness/as-of, and checksum blockers remain.

### T-142: Add local AAPL-vs-VOO browser/API smoke coverage

Goal:
Add deterministic local smoke coverage for the fully wired `AAPL` vs `VOO` stock-vs-ETF comparison workflow so an operator can prove the browser, Next proxy, FastAPI CORS, compare page, compare API, export API, search redirect, and chat compare redirect all agree in a local run.

Completion details:
- Implementation commit: `594ccef feat(T-142): add local AAPL-vs-VOO browser/API smoke coverage`
- Local merge commit: `3aae2e9 chore(T-142): merge local AAPL-vs-VOO browser/API smoke coverage` from branch `agent/T-142-20260501T064007Z`
- `tests/frontend/smoke.mjs` now asserts `A vs B` search routing is defined before backend-preferred search resolution, emits comparison-route metadata, and keeps the home page as one primary single-asset search instead of a two-input comparison builder.
- The opt-in local browser smoke now covers `/compare?left=AAPL&right=VOO` markers for `stock_vs_etf`, `stock-etf-relationship-v1`, `direct_holding`, relationship badges, source/citation metadata, AAPL/VOO source references, and `single-company-vs-etf-basket`, while rejecting unsupported/no-local-pack rendering for that pair.
- The opt-in local browser smoke now calls `POST /api/compare` through the Next `/api/:path*` proxy and direct FastAPI path for `AAPL`/`VOO`, verifies JSON instead of Next HTML fallback, checks CORS preflight from the configured local web origin, and rejects the old frontend-only `holding_verified` state.
- The opt-in local browser smoke now calls `/api/compare/export` for `AAPL`/`VOO` and verifies available, source-backed, same-comparison-pack, citation-bearing export output with the educational disclaimer and no-advice framing.
- The opt-in local browser smoke now calls `POST /api/assets/VOO/chat` with `AAPL vs VOO` and verifies a compare-route redirect to `/compare?left=AAPL&right=VOO`, `comparison_availability_state = available`, no generated multi-asset factual answer, and no factual citations/source documents in the redirect body.
- The optional durable smoke path now receives the configured web/API bases, checks `AAPL`/`VOO` stock-vs-ETF page markers including `direct_holding`, and probes the `AAPL`/`VOO` comparison export path.
- `docs/local_fresh_data_ingest_to_render_runbook.md` now documents separate API and web startup commands with `CORS_ALLOWED_ORIGINS`, `NEXT_PUBLIC_API_BASE_URL`, and `API_BASE_URL`; curl probes for `AAPL`/`VOO` compare, export, chat redirect, and CORS preflight; and the operator-only `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1` command with `LEARN_TICKER_LOCAL_WEB_BASE` and `LEARN_TICKER_LOCAL_API_BASE`.
- Existing `VOO` vs `QQQ` ETF-vs-ETF behavior remains covered by the smoke and runbook.
- `docs/agent-journal/20260501T064007Z.md` records the files changed, tests/evals run, pass status, optional localhost blocker, and remaining risks.

Required commands executed in this task branch:
- `npm test` - pass
- `npm run typecheck` - pass
- `npm run build` - pass
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py tests/integration/test_backend_api.py -q` - pass (`60 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`468 passed` in Python phases; static evals, frontend smoke/typecheck/build, and backend checks passed)
- `git diff --check` - pass

Optional localhost smoke status:
- Attempted API/web dev-server startup was blocked in this sandbox: API bind failed on `127.0.0.1:8000`, and Next dev failed with `listen EPERM` on `127.0.0.1:3000`.
- The opt-in `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1 LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000 LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000 npm run test:browser-smoke` command was not run because localhost services could not be started in the sandbox.

Remaining risks:
- The new AAPL-vs-VOO smoke assertions are exercised by default only as static/default deterministic smoke markers; the full proxy/CORS/browser API path still requires an operator environment that can bind local API and web ports.
- Coverage remains limited to deterministic local `AAPL`/`VOO` stock-vs-ETF and existing `VOO`/`QQQ` ETF-vs-ETF packs; it does not imply broad comparison coverage.

### T-141: Align frontend comparison suggestions with API availability

Goal:
Remove frontend-only local-availability drift for comparison suggestions, fallback rendering, and stock-vs-ETF relationship display so the UI never advertises a source-backed pair that `POST /api/compare` cannot serve.

Completion details:
- Implementation commit: `11b7c2c feat(T-141): align frontend comparison suggestions with API availability`
- Local merge commit: `0a56f67 chore(T-141): merge align frontend comparison suggestions with API availability` from branch `agent/T-141-20260501T062508Z`
- `apps/web/lib/compare.ts` now validates the backend `stock_etf_relationship` model when present, including `schema_version = stock-etf-relationship-v1`, `comparison_type = stock_vs_etf`, badge/basket shape, and backend-supported relationship states `direct_holding`, `sector_or_theme`, `broad_market_context`, `weak_relationship`, and `unknown`.
- Removed the old frontend-only `holding_verified` relationship state from comparison rendering and translated the deterministic `AAPL`/`VOO` fallback relationship to `direct_holding` with `partial` basket evidence.
- `apps/web/app/compare/page.tsx` now passes the actual fetched comparison response into `getComparePageSuggestions`, so a successful unavailable or limited API response is rendered as unavailable/limited instead of being replaced by a richer local fixture for the requested pair.
- Compare-page unavailable rendering now carries availability-specific eyebrow, summary, detail, and freshness-state handling for states such as `partial`, `stale`, `unavailable`, and `insufficient_evidence`.
- `apps/web/lib/compareSuggestions.ts` and `apps/web/components/ComparisonSuggestions.tsx` now attach suggestion availability metadata, `backend_aligned_local_contract`, and `exampleOnly` flags; unavailable requested pairs show existing local fixture links only as examples, not facts about the requested pair.
- Local comparison suggestion pairs remain limited to the backend-aligned deterministic `VOO`/`QQQ` and `AAPL`/`VOO` packs.
- `tests/frontend/smoke.mjs` now checks stock-vs-ETF markers including `stock-etf-relationship-v1`, `direct_holding`, relationship badges, `single-company-vs-etf-basket`, same-pack AAPL/VOO citation markers, absence of `holding_verified`, and comparison-suggestion example-only metadata.
- Optional local browser and local durable smoke assertions were extended to distinguish ETF-vs-ETF `VOO`/`QQQ` pages from stock-vs-ETF `AAPL`/`VOO` pages, while remaining opt-in.
- `docs/agent-journal/20260501T062508Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `npm test` - pass
- `npm run typecheck` - pass
- `npm run build` - pass
- `TMPDIR=/tmp python3 -m pytest tests/integration/test_backend_api.py::test_compare_route_uses_fixture_pipeline_in_reverse_order_and_unavailable_states tests/integration/test_backend_api.py::test_chat_comparison_questions_redirect_to_compare_workflow_with_local_availability_states -q` - pass (`2 passed`)
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`468 passed` in Python phases; frontend smoke, typecheck, build, and backend checks passed)
- `git diff --check` - pass

Remaining risks:
- Frontend fallback comparison fixtures remain deterministic local examples; they prove only `VOO`/`QQQ` and `AAPL`/`VOO`, not broad comparison coverage.
- Optional localhost browser smoke remains opt-in and was not run in the T-141 attempt.

### T-140: Add backend AAPL-vs-VOO stock-vs-ETF comparison pack

Goal:
Add a governed backend/API-backed `AAPL` vs `VOO` stock-vs-ETF comparison pack so `POST /api/compare`, comparison export, and chat compare-route availability agree with the frontend stock-vs-ETF workflow while using deterministic local evidence only.

Completion details:
- Implementation commit: `21149ba feat(T-140): add backend AAPL-vs-VOO stock-vs-ETF comparison pack`
- Local merge commit: `65f07fd chore(T-140): merge backend AAPL-vs-VOO stock-vs-ETF comparison pack` from branch `agent/T-140-20260501T060807Z`
- Added stock-vs-ETF generation in `backend/comparison.py` for comparison packs containing one stock and one ETF, with required dimensions `Structure`, `Basket membership`, `Breadth`, `Cost model`, and `Educational role`.
- Added `StockEtfRelationshipBadge`, `StockEtfBasketStructure`, and `StockEtfRelationshipModel` to `backend/models.py`, and exposed `stock_etf_relationship` on `CompareResponse`.
- Added an `AAPL_vs_VOO` deterministic comparison fixture in `data/retrieval_fixtures.json` with computed differences tied to AAPL and VOO local facts/chunks.
- `generate_comparison("AAPL", "VOO")` and the reverse order now return `comparison_type = stock_vs_etf`, `state.status = supported`, `evidence_availability.availability_state = available`, citations, source documents, source references, and relationship badges.
- The relationship model labels Apple membership in VOO as `direct_holding` with `partial` evidence because the local VOO holdings fixture lists Apple among top holdings, while exact holding weight, top-10 concentration, sector exposure, and full overlap remain unavailable.
- Added same-comparison-pack citation/source binding coverage so AAPL evidence cites AAPL fixture sources and VOO evidence cites VOO fixture sources.
- Updated comparison export behavior in `backend/export.py` to include a `stock_etf_relationship_context` section with relationship badge items, citations, source metadata, freshness state, limitations, and the educational disclaimer.
- `/api/compare/export?left_ticker=AAPL&right_ticker=VOO` now returns an available source-backed stock-vs-ETF export; reverse-order export coverage is included in unit tests.
- Single-asset chat comparison redirects now report `AAPL vs VOO` availability as `available` while preserving compare-route workflow metadata instead of returning a multi-asset factual answer inside asset chat.
- Existing unavailable cases remain non-generated for unsupported, out-of-scope, eligible-not-cached, unknown, and missing-pack pairs; `AAPL` vs `QQQ` is the deterministic missing-pack stock-vs-ETF case.
- Existing `VOO` vs `QQQ` ETF-vs-ETF comparison behavior remains covered.
- Updated static evals and golden/export/comparison eval cases so `AAPL` vs `VOO` is available and validated, while unavailable pairs remain blocked.
- `docs/agent-journal/20260501T060807Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_retrieval_fixtures.py tests/unit/test_comparison_generation.py tests/unit/test_exports.py tests/unit/test_chat_generation.py tests/integration/test_backend_api.py -q` - pass (`94 passed`)
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`468 passed` in Python phases; static evals, frontend smoke/typecheck/build, and backend checks passed)
- `git diff --check` - pass

Remaining risks:
- The new stock-vs-ETF pack is deterministic and fixture-backed only; it does not prove broad stock-vs-ETF coverage.
- Exact VOO holding weight for Apple, top-10 concentration, sector exposure, and full holdings overlap remain unavailable by design and must stay labeled as limitations unless approved evidence is added later.
- Frontend API-alignment work remains in T-141 so the UI consumes the backend relationship schema and avoids frontend-only availability drift.

### T-139: Add local manual fresh-data readiness gate

Goal:
Add a deterministic local readiness gate that can tell the operator whether more agent-loop work remains before manual fresh-data testing, or whether the next step is manual local testing with explicit browser, durable repository, official-source retrieval, and live-AI opt-in checks.

Completion details:
- Implementation commit: `2df5b12 feat(T-139): add local manual fresh-data readiness gate`
- Local merge commit: `650b061 chore(T-139): merge local manual fresh-data readiness gate` from branch `agent/T-139-20260429T175733Z`
- Added `manual_fresh_data_readiness_gate` to `scripts/run_local_fresh_data_rehearsal.py --json` with schema `local-manual-fresh-data-readiness-gate-v1`.
- The gate reports a clear task-ready versus manual-test-ready decision through `decision`, `task_ready_vs_manual_test_ready_decision`, `task_ready_for_manual_testing`, `manual_test_ready`, `agent_work_remaining`, and `next_operator_action`.
- The gate aggregates prerequisite summaries for T-136 ETF-500 candidate review, T-137 ETF source-pack batch planning, T-138 Top-500 SEC source-pack batch planning, local MVP thresholds, local ingestion priority planning, governed golden rendering, and frontend v0.4 smoke markers.
- Current deterministic output reports `agent_work_remaining` because ETF-500 review remains fixture-only with category/source-pack gaps, ETF issuer source-pack batch planning still uses fixture fallback and incomplete source packs, Top-500 SEC planning still has insufficient-evidence, parser, handoff, freshness/as-of, and checksum blockers, and local ingestion planning still has blocked or not-ready assets.
- Added stop-condition reporting for required deterministic check failures, local-threshold blockers, ETF-500 fixture-only review, ETF-500 category gaps, ETF source-pack incompleteness, ETF handoff/rights/parser/checksum blockers, ETF source-pack batch fixture fallback, Top-500 SEC insufficient evidence, Top-500 handoff/parser/freshness/checksum blockers, ingestion-priority blocked assets, and explicitly enabled optional-mode blockers.
- Added sanitized no-secret diagnostics that report only opt-in environment variable names, not values, for browser services, durable repositories, official-source retrieval, live-AI review, local web base, and local API base.
- Added review-only boundary fields showing the gate does not start production services, fetch live sources, call live LLMs, approve sources, promote manifests, start ingestion, write generated-output cache entries, or unlock generated output for unsupported or incomplete assets.
- Added a manual-test checklist covering local web/API startup, API-base/proxy/CORS, home single-asset search, `A vs B` compare redirects, source drawer, citation chips, freshness labels, Markdown/JSON exports, comparison, stock-vs-ETF relationship badges, contextual glossary desktop/mobile behavior, asset chat mobile behavior, Weekly News Focus smaller/empty states, AI Comprehensive Analysis threshold behavior, unsupported/recognition-only blocking, optional durable repositories, optional official-source retrieval, and optional live-AI validation.
- Added unit coverage for the default `agent_work_remaining` path, optional-mode blocker behavior without secret leakage, and a synthetic all-clear `manual_test_ready` path.
- Updated `SPEC.md` to record the local manual fresh-data readiness gate as review-only, deterministic, and blocked from approving sources, promoting manifests, fetching live sources, exposing secrets, or unlocking generated output.
- `docs/agent-journal/20260429T175733Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py::test_local_fresh_data_rehearsal_default_is_deterministic_and_review_only tests/unit/test_repo_contract.py::test_local_fresh_data_rehearsal_optional_modes_report_blockers_without_secrets tests/unit/test_repo_contract.py::test_manual_fresh_data_readiness_gate_can_report_manual_test_ready_when_blockers_clear -q` - pass (`3 passed`)
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py tests/integration/test_backend_api.py -q` - pass (`60 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`465 passed` in Python phases; frontend and backend checks passed)
- `git diff --check` - pass

Remaining risks:
- The readiness gate is deterministic and review-only; it does not run browser automation, start services, fetch live official sources, call live AI, approve sources, promote manifests, write production storage, start ingestion, or unlock generated output.
- Current deterministic output still reports `agent_work_remaining`; real manual readiness depends on future reviewed source packs, parser readiness, Golden Asset Source Handoff approval, freshness/as-of metadata, and checksums.
- The `manual_test_ready` state is covered by a synthetic all-clear unit path only; it is not evidence that the current repository state is ready for manual fresh-data testing.

### T-138: Add Top-500 SEC source-pack batch planning contracts

Goal:
Add deterministic, review-only Top-500 stock SEC source-pack batch planning so current-manifest rows can be prioritized for SEC source review by rank, source component gaps, parser readiness, and local fresh-data coverage needs before any live retrieval, source approval, manifest promotion, or generated-output unlock happens.

Completion details:
- Implementation commit: `f36a190 feat(T-138): add Top-500 SEC source-pack batch planning contracts`
- Local merge commit: `8c4ed41 chore(T-138): merge Top-500 SEC source-pack batch planning contracts` from branch `agent/T-138-20260429T174655Z`
- Added `build_top500_sec_source_pack_batch_plan` in `backend/top500_candidate_manifest.py` with schema `top500-sec-source-pack-batch-plan-v1` and boundary `top500-sec-source-pack-batch-planning-review-only-v1`.
- The planner composes the T-132 stock SEC source-pack readiness packet and T-135 local ingestion priority planner while preserving `data/universes/us_common_stocks_top500.current.json` as the runtime stock authority.
- Planning explicitly reports `support_resolved_from_current_manifest_only: true`, `candidate_or_priority_data_resolves_runtime_support: false`, and `live_provider_or_exchange_data_resolves_runtime_support: false`.
- Candidate/current diagnostics are review-only: the current deterministic run found `data/universes/us_common_stocks_top500.candidate.2026-04.json`, 10 shared current/candidate tickers, 0 candidate-only tickers, 0 current-only tickers, and no candidate-driven generated-output unlock.
- Current deterministic planning reports 10 planned stock rows, 5 batch groups, 1 high-demand pre-cache row, 9 Top-500 review rows, 1 source-backed partial-ready row, 9 `insufficient_evidence` rows, and 9 blocked generated surfaces.
- Batch groups include `high-demand-pre-cache` with `AAPL`, `TOP500-50` with `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `BRK.B`, `JPM`, and `UNH`, plus empty `TOP500-150`, `TOP500-300`, and `TOP500-500` groups for later launch-sized review.
- Each planned row reports required SEC source components for SEC submissions, latest annual filing, latest quarterly filing when available, and XBRL company facts, including parser status, source snapshot/checksum requirements, freshness/as-of metadata, Golden Asset Source Handoff action, fallback state, and generated-output blocking.
- Readiness priority diagnostics currently report 1 `approved_partial_ready_needs_quarterly_or_full_review` row for `AAPL` and 9 `missing_required_sec_sources` rows for the remaining current-manifest fixture stocks.
- Source-handoff diagnostics currently report 3 approved components and 37 pending-review, unclear-rights, or wrong-asset/missing components; parser diagnostics report 3 parsed components and 37 `pending_review` components.
- Freshness/checksum diagnostics currently report 3 fresh components, 37 unavailable components, 3 checksum-required components, 0 checksum-present components, and no source snapshots written by the planner.
- Planned rows with incomplete, unapproved, parser-pending, unclear-rights, wrong-asset, unavailable, partial, or insufficient evidence remain blocked from generated pages, generated claims, chat, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, generated risk summaries, and generated-output cache entries.
- `scripts/run_local_fresh_data_rehearsal.py` now surfaces the Top-500 SEC source-pack batch planning summary under the stock SEC source-pack readiness check while preserving review-only deterministic behavior.
- Added unit/repo-contract coverage in `tests/unit/test_top500_candidate_manifest.py`, `tests/unit/test_ingestion_jobs.py`, and `tests/unit/test_repo_contract.py` for current-manifest authority, rank/batch ordering, candidate diagnostics, SEC component plans, source-handoff blockers, parser/freshness/checksum placeholders, generated-output blocking, rehearsal output, and repo-control doc markers.
- `docs/agent-journal/20260429T174655Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_top500_candidate_manifest.py tests/unit/test_ingestion_jobs.py tests/unit/test_repo_contract.py -q` - pass (`50 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`464 passed` in Python phases; frontend and backend checks passed)
- `git diff --check` - pass

Remaining risks:
- The Top-500 SEC source-pack batch planner is deterministic and review-only; it does not fetch SEC/provider data, approve sources, promote manifests, start ingestion, write generated-output cache entries, or unlock generated output.
- Current deterministic stock planning has only `AAPL` as source-backed partial-ready; the other current-manifest stock rows remain `insufficient_evidence` until SEC source packs, parser outputs, freshness/as-of metadata, checksums, and Golden Asset Source Handoff review are completed.
- Candidate-manifest relationship diagnostics are surfaced for review only and do not change runtime stock support authority from `data/universes/us_common_stocks_top500.current.json`.

### T-137: Add ETF-500 issuer source-pack batch planning contracts

Goal:
Add deterministic, review-only ETF-500 issuer source-pack batch planning so ETF-500 candidate rows can be grouped by batch, issuer, category, and missing official issuer evidence before any retrieval, source approval, manifest promotion, or generated-output unlock happens.

Completion details:
- Implementation commit: `29548ea feat(T-137): add ETF-500 issuer source-pack batch planning contracts`
- Local merge commit: `a300cc3 chore(T-137): merge ETF-500 issuer source-pack batch planning contracts` from branch `agent/T-137-20260429T173727Z`
- Added `build_etf500_issuer_source_pack_batch_plan` in `backend/etf_universe.py` with schema `etf500-issuer-source-pack-batch-plan-v1` and boundary `etf500-issuer-source-pack-batch-planning-review-only-v1`.
- The planner composes the T-136 ETF-500 launch review contract and T-133 issuer source-pack readiness packet without fetching issuer/provider data, approving sources, promoting manifests, starting ingestion, writing generated-output cache entries, or unlocking generated output.
- Candidate review metadata is consumed from the ETF-500 review contract, but no ETF-500 candidate artifacts are currently present; the planner falls back to current fixture-sized review metadata and explicitly marks the fallback as not launch coverage.
- Current deterministic planning reports 13 planned ETF rows, 4 batch groups, 5 issuers, 7 category buckets, 0 source-pack-ready rows, 2 source-backed partial-review rows, 11 missing-required-issuer-source rows, and 9 blocked generated surfaces.
- Batch groups include `ETF-50`, `ETF-150`, `ETF-300`, and `ETF-500`; the current fixture rows all land in `ETF-50`, with later launch-sized milestone groups empty until candidate artifacts exist.
- Category bucket diagnostics report 7 broad/core U.S. equity beta rows, 7 market-cap and size/style rows, 4 sector ETF rows, 2 industry/theme passive U.S. equity rows, and 0 rows for dividend/shareholder-yield, factor/smart-beta/equal-weight, and ESG/values-screened buckets.
- Issuer/source-pack priority diagnostics report Vanguard, iShares, State Street Global Advisors, Invesco, and VanEck grouping, with 2 `source_backed_partial_review` rows and 11 `missing_required_issuer_sources` rows.
- Each planned ETF row reports required issuer source components, including issuer page, fact sheet, prospectus or summary prospectus, holdings, exposures, methodology/shareholder/risk source, and sponsor announcements when relevant.
- Component planning diagnostics include same-fund checks, official-source identity, source-use policy needs, storage/export-rights needs, parser readiness, freshness/as-of/checksum placeholders, Golden Asset Source Handoff action, and blocked generated surfaces.
- Target context carries the ETF-500 practical supported-row range `475-525`, batch milestones, category target buckets, category gaps, current-fixture-not-launch status, source-pack readiness, parser/handoff readiness, checksum status, and no-padding stop conditions from T-136.
- `scripts/run_local_fresh_data_rehearsal.py` now surfaces the ETF-500 source-pack batch planning summary under the ETF issuer source-pack readiness check while preserving review-only, deterministic behavior.
- Added unit/repo-contract coverage in `tests/unit/test_search_classification.py` and `tests/unit/test_repo_contract.py` for planning boundaries, fallback-not-launch status, batch/category/issuer grouping, readiness priorities, component diagnostics, generated-output blocking, and rehearsal output.
- `docs/agent-journal/20260429T173727Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_repo_contract.py -q` - pass (`38 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`462 passed` in Python phases; frontend and backend checks passed)
- `git diff --check` - pass

Remaining risks:
- ETF-500 issuer source-pack batch planning is deterministic and review-only; it does not fetch issuer/provider data, approve sources, promote manifests, start ingestion, write generated-output cache entries, or unlock generated output.
- Current ETF planning falls back to fixture-sized current review metadata because no ETF-500 candidate artifacts are present, and it is explicitly marked as not launch coverage.
- Supported ETF source-pack readiness remains incomplete for all non-golden current rows until issuer source packs, parser outputs, freshness/as-of metadata, checksums, and Golden Asset Source Handoff review are completed.

### T-136: Add ETF-500 candidate manifest review contracts

Goal:
Add deterministic, review-only ETF-500 candidate manifest review contracts so supported ETF and ETF/ETP recognition candidate manifests can be inspected against the ETF-500 target range, category bucket targets, batch milestones, source-pack/parser gates, and generated-output blocking rules without promoting runtime manifests, broadening supported coverage, or making live calls.

Completion details:
- Implementation commit: `17f7808 feat(T-136): add ETF-500 candidate manifest review contracts`
- Local merge commit: `486cda8 chore(T-136): merge ETF-500 candidate manifest review contracts` from branch `agent/T-136-20260429T172950Z`
- Added ETF-500 review metadata in `backend/etf_universe.py` with contract version `etf500-candidate-manifest-review-contract-v1`.
- Added target metadata for practical supported-row range `475-525`, candidate artifact path conventions, batch milestones `ETF-50`, `ETF-150`, `ETF-300`, and `ETF-500`, and seven category target buckets sourced to `docs/ETF_MANIFEST_HANDOFF.md`.
- Extended `build_etf_launch_review_packet` to include `etf500_review_contract`, `etf500_target_metadata`, and `current_fixture_not_launch_coverage`.
- Current deterministic ETF diagnostics report 13 supported-manifest rows, 9 recognition rows, 7 category coverage gaps, 13 source-pack-incomplete rows, 0 source-pack-ready rows, 22 pending-review rows, 1 unavailable row, 0 parser-invalid rows, 22 handoff-not-ready rows, 22 unclear-rights rows, and matching supported/recognition checksums.
- Category diagnostics report current fixture counts of 7 broad/core U.S. equity beta rows, 7 market-cap and size/style rows, 4 sector ETF rows, 2 industry/theme rows, and 0 current rows for dividend/shareholder-yield, factor/smart-beta/equal-weight, and ESG/values-screened buckets.
- Disqualifier diagnostics report leveraged, inverse, active, fixed income, commodity, ETN, multi-asset, and unclear/pending-review products while preserving explicit no-padding stop conditions for leveraged, inverse, active, fixed income, commodity, crypto, single-stock, option-income/buffer, multi-asset, ETN, ETV, CEF, international equity, and unclear products.
- Generated-output blocking rules keep recognition-only rows, scope-gate failures, pending-review rows, unavailable rows, parser-invalid rows, unclear-rights rows, and source-pack-incomplete rows blocked from generated pages, generated claims, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, generated risk summaries, and generated-output cache entries.
- `scripts/run_local_fresh_data_rehearsal.py` now surfaces ETF-500 target metadata, category gaps, disqualifier counts, source-pack readiness, parser/handoff readiness, checksum status, no-padding stop conditions, current-fixture-not-launch status, and generated-output blocking rules in the launch-manifest review check.
- Added tests in `tests/unit/test_search_classification.py` and `tests/unit/test_repo_contract.py` for ETF-500 target metadata, category bucket targets, fixture-not-launch status, category/disqualifier diagnostics, source-pack/parser/handoff/checksum diagnostics, rehearsal output, and generated-output blocking.
- `docs/agent-journal/20260429T172950Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_repo_contract.py -q` - pass (`37 passed`)
- `TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect` - pass
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`461 passed` in Python test phases; frontend and backend checks passed)
- `git diff --check` - pass

Remaining risks:
- The ETF-500 contract is deterministic and review-only; it does not create candidate manifests, approve sources, promote manifests, start ingestion, write generated-output cache entries, or unlock generated output.
- Current supported ETF manifest remains fixture-sized, below the ETF-500 target range, and explicitly marked as not launch coverage.
- Source-pack readiness remains incomplete for all current supported ETF rows until issuer source packs and Golden Asset Source Handoff review are completed.

### T-135: Add batchable local ingestion priority planner

Goal:
Add a deterministic planner for local fresh-data ingestion order that prioritizes high-demand pre-cache assets first, then approved supported ETFs and Top-500 stocks by manifest/review priority, while preserving resumable pending/running/succeeded/failed states and review-only source approval.

Completion details:
- Implementation commit: `03cc7d6 feat(T-135): add batchable local ingestion priority planner`
- Local merge commit: `74c68c4 chore(T-135): merge batchable local ingestion priority planner` from branch `agent/T-135-20260429T015215Z`
- Added `build_local_ingestion_priority_plan` in `backend/ingestion.py` with schema `local-ingestion-priority-plan-v1` and boundary `local-ingestion-priority-planner-review-only-v1`.
- The planner is deterministic, batchable, resumable, review-only, and marked as making no live external calls in normal CI.
- Planner ordering starts with high-demand golden/pre-cache assets `AAPL`, `VOO`, and `QQQ`, then supported ETFs from `data/universes/us_equity_etfs_supported.current.json` by source-pack readiness and represented category coverage, then Top-500 stocks from `data/universes/us_common_stocks_top500.current.json` by current-manifest rank.
- The planner reports 23 planned assets in 6 batches: 3 high-demand pre-cache assets, 11 supported ETF-manifest assets, and 9 additional Top-500 stock-manifest assets, with 3 ready-to-inspect rows and 20 blocked-or-not-ready rows in the current deterministic fixtures.
- Planner diagnostics include `pending`, `running`, `succeeded`, `failed`, `unsupported`, `out_of_scope`, `unknown`, `unavailable`, `partial`, `stale`, and `insufficient_evidence` state keys.
- The planner keeps recognition-only ETF/ETP rows diagnostic only: `data/universes/us_etp_recognition.current.json` is not used for priority order and recognition rows do not unlock generated output.
- Planner safety boundaries explicitly report no ingestion start, no source approval, no manifest promotion, no generated-output cache writes, and no generated-output unlock for blocked assets.
- `scripts/run_local_fresh_data_rehearsal.py` now includes the local ingestion priority planner check and surfaces its summary, first-batch tickers, state diagnostics, runtime authorities, recognition-manifest boundaries, and blocked generated surfaces.
- Added unit/repo-contract coverage in `tests/unit/test_ingestion_jobs.py` and `tests/unit/test_repo_contract.py` for deterministic ordering, review-only boundaries, manifest authorities, blocked-state diagnostics, rehearsal integration, and generated-output blocking.
- `docs/agent-journal/20260429T015215Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_ingestion_jobs.py tests/unit/test_repo_contract.py -q` - pass (`38 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_ingestion_worker.py tests/unit/test_ingestion_jobs.py tests/unit/test_search_classification.py tests/unit/test_repo_contract.py -q` - pass (`80 passed`)
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`461 passed`)
- `git diff --check` - pass

Remaining risks:
- The planner is deterministic and review-only; it does not start ingestion, approve sources, promote manifests, write generated-output cache entries, or approve launch/public deployment.
- Planner ordering reflects the current local fixtures and manifest review metadata, including source-pack readiness gaps for non-golden ETFs and most Top-500 stocks.
- Recognition-only ETF/ETP rows remain diagnostic/blocking metadata only and do not unlock generated output.

### T-134: Add local fresh-data MVP readiness thresholds

Goal:
Extend the local rehearsal/status layer with explicit fully functional local-MVP thresholds for deterministic fresh-data testing, including allowed failed/unavailable asset counts, no generated claims for failed assets, optional-mode blockers, and deterministic source-backed partial fallback when live generation fails validation.

Completion details:
- Implementation commit: `acdefa8 feat(T-134): add local fresh-data MVP readiness thresholds`
- Local merge commit: `c8a678e chore(T-134): merge local fresh-data MVP readiness thresholds` from branch `agent/T-134-20260429T014416Z`
- Added `local_mvp_threshold_summary` to `scripts/run_local_fresh_data_rehearsal.py` with schema `local-fresh-data-mvp-threshold-summary-v1` and threshold contract `review_only_no_launch_approval_v1`.
- The threshold summary separates required checks, optional skipped modes, optional blockers, threshold blockers, failed/unavailable asset counts, partial/stale/unknown/insufficient-evidence counts, source-backed partial-ready counts, and `ready_for_local_operator_review` versus blocked local status.
- Required checks cover deterministic defaults, Golden Asset Source Handoff, governed golden API rendering, launch-manifest review packets, stock SEC source-pack readiness, ETF issuer source-pack readiness, and v0.4 frontend smoke markers.
- Optional browser, local durable repository, official-source retrieval, and live-AI review modes remain explicit opt-ins; missing opt-in prerequisites are reported as skipped or blocked without exposing secrets.
- Added deterministic local thresholds allowing one failed asset and one unavailable asset in current fixtures, while reporting reason codes such as `fixture_pre_cache_failed` and `unavailable`.
- Added review-only boundaries that keep the rehearsal from approving sources, promoting manifests, starting ingestion, writing generated-output cache entries, or approving launch/public deployment.
- Added live-generation validation failure fallback metadata showing generated claims, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, and generated-output cache entries are not allowed after failed validation; only labeled `partial`, `stale`, `unknown`, `unavailable`, or `insufficient_evidence` fallback states remain allowed.
- Added integration and repo-contract coverage in `tests/integration/test_backend_api.py` and `tests/unit/test_repo_contract.py` for the threshold summary, optional-mode blocker behavior, asset-state counts, review-only boundaries, and rehearsal output.
- `docs/agent-journal/20260429T014416Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py::test_local_fresh_data_rehearsal_default_is_deterministic_and_review_only tests/unit/test_repo_contract.py::test_local_fresh_data_rehearsal_optional_modes_report_blockers_without_secrets tests/integration/test_backend_api.py::test_t130_local_fresh_data_mvp_rehearsal_ties_governed_path_to_render_surfaces -q` - pass (`3 passed`)
- `TMPDIR=/tmp python3 -m pytest tests/integration/test_backend_api.py tests/unit/test_weekly_news.py tests/unit/test_llm_provider.py tests/unit/test_cache_contracts.py tests/unit/test_repo_contract.py -q` - pass (`138 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`460 passed`)
- `git diff --check` - pass

Remaining risks:
- The threshold summary is deterministic and review-only; it does not approve sources, promote manifests, start ingestion, write generated-output cache entries, or approve launch/public deployment.
- Allowed failed and unavailable counts reflect current local fixtures, not production readiness.
- Source-backed partial readiness remains limited to the existing deterministic stock and ETF readiness packets.

### T-133: Add ETF issuer source-pack readiness packet contracts

Goal:
Add deterministic ETF issuer source-pack readiness reporting for supported-manifest ETFs, covering issuer page, fact sheet, prospectus or summary prospectus, holdings, exposures, methodology/shareholder/risk sources, and sponsor announcements where relevant.

Completion details:
- Implementation commit: `58256c1 feat(T-133): add ETF issuer source-pack readiness packet contracts`
- Local merge commit: `2486398 chore(T-133): merge ETF issuer source-pack readiness packet contracts` from branch `agent/T-133-20260429T013254Z`
- Added deterministic, review-only ETF issuer source-pack readiness reporting in `backend/etf_universe.py` with schema `etf-issuer-source-pack-readiness-v1` and boundary `etf-issuer-source-pack-readiness-review-only-v1`.
- Readiness is keyed from `data/universes/us_equity_etfs_supported.current.json`; recognition-only rows from `data/universes/us_etp_recognition.current.json` are reported as blocked and non-authoritative for generated output.
- Supported ETF readiness rows now report issuer source components for issuer page, fact sheet, prospectus or summary prospectus, holdings, exposures, optional methodology/shareholder/risk sources, and sponsor announcements where relevant.
- Component metadata includes same-fund validation, official-source/source identity, source type, source-use policy, storage rights, export rights, parser status, freshness/as-of dates, citation readiness, Golden Asset Source Handoff action readiness, and review rationale where available.
- Added the ETF issuer readiness check to `scripts/run_local_fresh_data_rehearsal.py`, preserving review-only behavior with no manifest promotion, source approval, generated-output unlock, or live external calls.
- Added unit and repo-contract coverage in `tests/unit/test_search_classification.py` and `tests/unit/test_repo_contract.py` for supported-manifest authority, blocked recognition-only rows, partial golden ETF readiness, insufficient evidence for eligible-not-cached ETFs, stale holdings, parser-failed exposure, and wrong-fund issuer-source states.
- `docs/agent-journal/20260429T013254Z.md` records the files changed, tests/evals run, pass status, and remaining risks.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_search_classification.py tests/unit/test_source_policy.py tests/unit/test_repo_contract.py -q` - pass (`74 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`460 passed`)
- `git diff --check` - pass

Remaining risks:
- ETF issuer readiness remains deterministic and review-only; it does not approve sources, promote manifests, or unlock generated output.
- Current issuer fixtures provide source-backed partial readiness only for cached golden ETFs `VOO` and `QQQ`.
- Eligible-not-cached supported ETFs remain `insufficient_evidence` until issuer source packs are reviewed and added.

### T-132: Add stock SEC source-pack readiness packet contracts

Goal:
Add deterministic stock source-pack readiness reporting for the local fresh-data MVP so Top-500 stocks can prove whether SEC submissions, latest 10-K, latest 10-Q when available, and XBRL company facts are present, parser-valid, same-asset, approved for evidence use, and sufficient for source-backed partial rendering.

Completion details:
- Implementation commit: `476fdcd feat(T-132): add stock SEC source-pack readiness packet contracts`
- Local merge commit: `f800f7b chore(T-132): merge stock SEC source-pack readiness packet contracts` from branch `agent/T-132-20260429T012241Z`
- Added deterministic, review-only stock SEC source-pack readiness reporting in `backend/top500_candidate_manifest.py` for current Top-500 manifest rows and reviewed candidate rows.
- Readiness now reports SEC component status for submissions, annual filing, quarterly filing, and XBRL company facts with source-handoff, parser, freshness, rights, citation-readiness, and evidence-readiness metadata.
- Added the stock SEC readiness packet to `scripts/run_local_fresh_data_rehearsal.py` without promoting manifests, approving sources, starting live calls, or unlocking generated output.
- Added unit and repo-contract coverage in `tests/unit/test_top500_candidate_manifest.py` and `tests/unit/test_repo_contract.py` for deterministic readiness status, review-only behavior, and source-backed partial/failure states.
- Preserved Top-500 manifest promotion controls; the task did not replace `data/universes/us_common_stocks_top500.current.json`.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_top500_candidate_manifest.py tests/unit/test_overview_generation.py tests/unit/test_repo_contract.py -q` - pass (`50 passed`)
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`458 passed`)
- `git diff --check` - pass

Remaining risks:
- Current stock SEC readiness is fixture/local-only and is not launch approval.
- Only `AAPL` has deterministic SEC fixture coverage today; other Top-500 fixture rows report `insufficient_evidence`.
- `AAPL` is source-backed partial-ready, but the latest 10-Q component remains `partial` because no deterministic quarterly filing fixture is present.

### T-131: Add ETF eligible-universe review packet contracts

Goal:
Extend the current ETF launch-review packet from fixture-sized support counts into a deterministic eligible-universe review contract that reports category coverage, exclusions, source-pack readiness, pending-review rows, generated-output eligibility, and golden/pre-cache regression status without treating the golden ETF set as the coverage limit.

Completion details:
- Implementation commits:
  - `f49cca2 feat(T-131): align fresh-data MVP readiness contracts`
  - `9447b44 docs(T-131): align ETF proposal docs`
  - `b3d221d feat(T-131): add ETF eligible-universe review packet contracts`
- Local merge commit: `2e81a24 chore(T-131): merge ETF eligible-universe review packet contracts` from branch `agent/T-131-20260429T011520Z`
- Extended `backend/etf_universe.py` with deterministic ETF eligible-universe review reporting for scope categories, exclusions, support states, source-pack readiness, generated-output eligibility, and golden/pre-cache regression status.
- Added local rehearsal reporting for the new ETF readiness fields in `scripts/run_local_fresh_data_rehearsal.py` while keeping ETF manifests unpromoted and review-only.
- Added unit and repo-contract coverage in `tests/unit/test_search_classification.py` and `tests/unit/test_repo_contract.py` for category scope, readiness counts, golden/pre-cache distinction, and local rehearsal contract markers.
- Aligned ETF proposal and handoff documentation in the task branch so golden ETF tickers remain pre-cache/regression assets, not the full ETF coverage ceiling.
- Preserved the supported ETF manifest and ETF/ETP recognition manifest split; recognition-only, unsupported, pending-review, unavailable, and pending-ingestion products remain blocked from generated output.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_repo_contract.py -q` - pass
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass
- `git diff --check` - pass

Remaining risks:
- Current ETF manifests remain fixture/local-only review metadata and are not launch-approved.
- `source_pack_ready` is intentionally zero until reviewed issuer source packs and Golden Asset Source Handoff metadata are available.
- Generated-output eligibility remains limited to existing cached deterministic ETF fixtures and does not unlock recognition-only, unsupported, pending-review, unavailable, or pending-ingestion products.

### T-130: Add local fresh-data MVP rehearsal command

Goal:
Add an operator-facing local fresh-data MVP rehearsal command that verifies the golden path from governed source approval through API/frontend rendering without requiring production services.

Completion details:
- Implementation commit: `9eb09ef feat(T-130): add local fresh-data MVP rehearsal command`
- Local merge commit: `1c843e8 chore(T-130): merge local fresh-data MVP rehearsal command` from branch `agent/T-130-20260428T203343Z`
- Added `scripts/run_local_fresh_data_rehearsal.py`, a repo-native local rehearsal command with deterministic default behavior and sanitized JSON output.
- The rehearsal ties source-handoff gates, governed golden API reads, source drawer/export surfaces, comparison/chat paths, frontend smoke markers, launch-manifest review packets, and opt-in readiness checks into one local review command.
- Default execution is fixture-backed/mock-backed and makes no live external provider, news, market-data, browser-service, production database, production storage, or live LLM calls.
- Optional browser, durable repository, official-source retrieval, and live-AI modes are explicitly gated and report skipped or blocked states when prerequisites are missing.
- Rehearsal output distinguishes `pass`, `skipped`, and `blocked` checks and keeps source approval, manifest promotion, production service startup, launch approval, raw model reasoning, provider payloads, raw transcripts, and secrets out of the command.
- Added integration and contract coverage for the T-130 rehearsal path, including governed render-surface checks, review-only source approval status, deterministic default behavior, optional-mode blockers, and sanitized diagnostics.
- Updated `docs/local_fresh_data_ingest_to_render_runbook.md`, `docs/mvp_go_no_go_checklist.md`, `docs/mvp_functional_gap_review.md`, and `EVALS.md` with the rehearsal command, deterministic default, opt-in modes, skip/block meanings, and stop conditions.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/integration/test_backend_api.py tests/unit/test_repo_contract.py tests/unit/test_safety_guardrails.py -q` - pass (`73 passed`)
- `npm test` - pass
- `npm run typecheck` - pass
- `npm run build` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`456 passed`)
- `git diff --check` - pass

Remaining risks:
- The rehearsal is review-only and does not approve sources, promote manifests, start production services, or make fixture-sized/local-only data launch-approved.
- Optional modes were covered through default skip and missing-prerequisite blocker paths; no live browser service, durable database, official-source retrieval, or live-AI provider call was attempted.

### T-129: Add launch-manifest operator automation parity

Goal:
Add review-only operator automation parity for Top-500 stock and supported ETF launch-manifest packets without promoting runtime manifests automatically.

Completion details:
- Implementation commit: `622c914 feat(T-129): add launch-manifest operator automation parity`
- Local merge commit: `1b58178 chore(T-129): merge launch-manifest operator automation parity` from branch `agent/T-129-20260428T202241Z`
- Added `scripts/review_launch_manifests.py`, a repo-native review-only command with `top500 generate`, `top500 inspect`, and `etf inspect` modes.
- Extended `backend/top500_candidate_manifest.py` with Top-500 launch review summary generation/inspection, review summary output paths, checksum validation, manual-promotion requirements, launch-approval stop conditions, and blocked/review-needed/pass status reporting.
- Extended `backend/etf_universe.py` with ETF launch review packet generation for the supported ETF manifest and ETF/ETP recognition manifest, including support-state counts, checksum checks, generated-output eligibility, blocked-state reasons, wrapper/scope metadata, parser/handoff metadata where available, and stop conditions for fixture/local-only, unknown, unavailable, stale, partial, insufficient-evidence, source-quality, and checksum states.
- Added deterministic test coverage for Top-500 operator review summaries, checksum mismatch blocking, written review artifacts, ETF supported-vs-recognition review packets, blocked recognition-only products, and repo-contract markers for the new commands.
- Updated `docs/TOP500_MANIFEST_HANDOFF.md` and `docs/ETF_MANIFEST_HANDOFF.md` with repo-native review-only commands, manual-promotion requirements, no-live-call defaults, non-advice framing, and launch stop conditions.
- Updated `docs/mvp_functional_gap_review.md` and `docs/mvp_go_no_go_checklist.md` to record the T-129 launch-manifest automation parity status.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_top500_candidate_manifest.py tests/unit/test_search_classification.py tests/unit/test_provider_adapters.py tests/unit/test_repo_contract.py -q` - pass (`68 passed`)
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_safety_guardrails.py::test_mvp_functional_gap_review_copy_is_advice_safe_and_sanitized -q` - pass (`1 passed`)
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`453 passed`; static evals, frontend smoke, typecheck, build, and backend checks passed)
- `git diff --check` - pass

Remaining risks:
- The launch-manifest commands are deterministic review-only tooling. They do not approve launch-sized manifests, source packs, private mirrors, or production deployment.
- Current Top-500 and ETF manifests remain fixture-sized/local metadata and are explicitly reported as not launch-approved.
- ETF review output exposes parser and handoff metadata only where current manifest fields provide it; full issuer source-pack parser and Golden Asset Source Handoff approval remains future launch work.

### T-128: Prove governed golden evidence drives API and frontend rendering

Goal:
Prove that approved governed source evidence for the golden set can drive backend API responses and frontend rendering instead of relying only on fixture fallback.

Completion details:
- Implementation commit: `8d2baf4 feat(T-128): prove governed golden evidence drives API and frontend rendering`
- Local merge commit: `0649832 chore(T-128): merge prove governed golden evidence drives API and frontend rendering` from branch `agent/T-128-20260428T200718Z`
- Added source-snapshot validation to the persisted overview read path in `backend/overview.py`, so configured golden API reads can require same-asset private source snapshot artifacts alongside normalized knowledge-pack records and generated-output cache records.
- Routed `source_snapshot_repository` into the overview, source drawer, asset export, source-list export, recent, and Weekly News API paths in `backend/main.py`, with `backend/sources.py` and `backend/export.py` passing the reader through to governed overview generation.
- Added `read_source_snapshot_records(ticker)` support to both source snapshot repository implementations so route-level readers can filter governed snapshot records by asset.
- Extended deterministic integration coverage with `test_configured_governed_golden_records_drive_learning_surfaces_end_to_end`, covering configured repositories for `AAPL`, `VOO`, and `QQQ`; governed source groups; citation bindings; Weekly News limited/empty states; AI Comprehensive Analysis threshold suppression; glossary context; comparison; chat; and asset/source/comparison/chat exports.
- Added frontend smoke markers proving governed golden overview, source drawer, citation, freshness, and export rendering contracts are API-backed while preserving deterministic fixture fallback.
- Updated `docs/local_fresh_data_ingest_to_render_runbook.md`, `docs/mvp_functional_gap_review.md`, and `docs/mvp_go_no_go_checklist.md` to state that T-128 is deterministic golden-path proof only and does not approve new sources, launch-sized manifests, production storage, live providers, or broader generated-output coverage.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/integration/test_backend_api.py tests/unit/test_source_snapshot_repository.py tests/unit/test_knowledge_pack_repository.py tests/unit/test_cache_contracts.py tests/unit/test_exports.py tests/unit/test_source_drawer.py tests/unit/test_citation_validation.py tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` - pass (`150 passed`)
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_overview_generation.py tests/integration/test_backend_api.py -q` - pass (`56 passed`)
- `npm test` - pass
- `npm run typecheck` - pass
- `npm run build` - pass
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`450 passed`)
- `git diff --check` - pass

Remaining risks:
- The governed rendering proof is limited to deterministic golden assets and in-memory/local repository contracts.
- The task does not approve new sources, launch-sized manifests, production storage, live providers, or broader generated-output coverage.
- Comparison and chat continue to use their existing persisted cache and knowledge-pack proof paths; T-128 added source-snapshot gating to overview-derived asset, source drawer, recent/weekly, and export routes.

### T-127: Add opt-in local live-AI validation smoke

Goal:
Add an operator-only local live-AI validation smoke for grounded chat and AI Comprehensive Analysis while keeping deterministic mocks as the CI and ordinary local default.

Completion details:
- Implementation commit: `0b836a7 feat(T-127): add opt-in local live-AI validation smoke`
- Local merge commit: `c174d1c chore(T-127): merge opt-in local live-AI validation smoke` from branch `agent/T-127-20260428T195337Z`
- Added `scripts/run_live_ai_validation_smoke.py`, an operator-only local smoke command with sanitized JSON diagnostics for one supported golden grounded-chat case (`VOO`) and one AI Comprehensive Analysis threshold case (`QQQ`).
- The smoke is disabled by default through `LTT_LIVE_AI_SMOKE_ENABLED`, requires live-generation readiness and server-side key presence before attempting provider transport, and reports `skipped`, `blocked`, or `pass` states.
- The smoke validates schema, citation IDs, same-asset evidence, source-use policy, freshness state, safety classification, Weekly News Focus evidence threshold, and cache eligibility before live output is treated as usable.
- The implementation records sanitized diagnostics only: it does not store or print raw user text, prompts, source text, model reasoning, raw transcripts, generated live responses, or secret values.
- `tests/unit/test_llm_provider.py` now covers disabled-by-default behavior, missing readiness/key blocked states, deterministic mocked-transport pass paths for grounded chat and AI Comprehensive Analysis, validation failure blocking, cache-ineligible output blocking, and sanitized diagnostics.
- `docs/local_fresh_data_ingest_to_render_runbook.md` documents the opt-in command, prerequisites, expected skipped/blocked/pass results, and stop conditions.
- `docs/mvp_go_no_go_checklist.md` and `docs/mvp_functional_gap_review.md` now record T-127 as operator-smoke coverage only, not source approval or launch approval.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_llm_provider.py -q` - pass
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py -q` - pass
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_llm_provider.py tests/unit/test_chat_generation.py tests/unit/test_weekly_news.py tests/unit/test_safety_guardrails.py tests/unit/test_cache_contracts.py tests/unit/test_repo_contract.py -q` - pass (`131 passed`)
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`450 passed`, static evals passed, frontend smoke/typecheck/build passed, backend checks passed)
- `git diff --check` - pass

Remaining risks:
- The live-AI smoke was verified with deterministic mocked transport in tests; no real provider call was attempted in the CI-safe run.
- The smoke validates live output eligibility but intentionally does not approve sources, relax Golden Asset Source Handoff, or write generated-output cache records.

### T-126: Add repo-native source-handoff manifest smoke tooling

Goal:
Add repo-native source-handoff manifest inspection/finalization smoke tooling or accurately scoped equivalents so operators can validate reviewed governed-source packets without relying on commands from another repository layout.

Completion details:
- Implementation commit: `901fe9d feat(T-126): add repo-native source-handoff manifest smoke tooling`
- Local merge commit: `89c9e23 chore(T-126): merge repo-native source-handoff manifest smoke tooling` from branch `agent/T-126-20260428T194357Z`
- Added `scripts/inspect_source_handoff_manifest.py`, a repo-native JSON manifest tool for `source-handoff-manifest-v1` packets with `inspect` and `finalize` commands.
- The tool validates manifest shape, source counts, finalizable status, and source-level blockers across generated-claim support, generated-output cache eligibility, and Markdown/JSON section export actions.
- Finalization is limited to draft or already-finalized manifests, writes `manifest_status: finalized`, `finalized_at`, and an inspection summary, and refuses blocked packets with source-level reason codes.
- `tests/unit/test_source_policy.py` now covers approved/finalizable manifests plus pending-review, rejected, parser-invalid, missing-freshness, unclear-rights, hidden/internal, rejected-manifest, malformed-manifest, strict-inspect, and finalize behaviors.
- `tests/unit/test_repo_contract.py` was updated to require the new repo-native source-handoff tool and documented commands.
- `docs/SOURCE_HANDOFF.md` now documents the current enforcement status, manifest shape, `inspect`, `inspect --strict`, and `finalize` commands, safety boundaries, operator workflow, and stop conditions.

Required commands executed in this task branch:
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_source_policy.py tests/unit/test_ingestion_worker.py tests/unit/test_repo_contract.py -q` - pass (`55 passed`)
- `TMPDIR=/tmp python3 evals/run_static_evals.py` - pass
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh` - pass (`446 passed`, static evals passed, frontend smoke/typecheck/build passed, backend checks passed)
- `git diff --check` - pass

Remaining risks:
- The smoke tool validates reviewed JSON handoff packets and can finalize them locally, but the repo still does not include governed source artifacts for the full golden set.
- T-126 did not prove finalized governed evidence drives backend API or frontend rendering; that remains a follow-up backlog item.

### T-125: Align v0.6 handoff docs and MVP backlog

Goal:
Align the v0.6 proposal/PRD/TDS refresh with operational docs, handoff guides, repo-contract tests, and the next agent-loop backlog without changing public API routes or frontend behavior.

Completion details:
- Completed in commit `70d404e docs(T-125): align v0.6 handoff docs and MVP backlog`.
- The v0.6 source-document direction was preserved while operational docs were aligned to actual repo entrypoints.
- `docs/README.md` now indexes `SOURCE_HANDOFF.md`, `TOP500_MANIFEST_HANDOFF.md`, and `ETF_MANIFEST_HANDOFF.md`.
- T-119 through T-124 are recorded as completed deterministic/operator-scoped work across the MVP gap review, runbook, regression matrix, go/no-go checklist, and control docs.
- Findings 1-4 are documented as resolved by T-119, with API-base/proxy/CORS regression coverage preserved.
- T-126 was prepared for promotion, and T-127 through T-129 remain the next narrow agent-loop backlog.
- Windows `*:Zone.Identifier` sidecars are ignored and no tracked project docs use them as source material.

Required commands executed in this task branch:
- `git diff --check`
- `TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py tests/unit/test_safety_guardrails.py -q`
- `TMPDIR=/tmp python3 evals/run_static_evals.py`
- `npm test`
- `npm run typecheck`
- `npm run build`
- `TMPDIR=/tmp bash scripts/run_quality_gate.sh`
- `docker compose config` was blocked because Docker was unavailable in the WSL environment.

Remaining risks:
- T-125 was docs/control-doc alignment only; it intentionally did not add the repo-native handoff smoke tooling, live-AI validation smoke, governed golden evidence render proof, or launch-manifest operator automation parity.

### T-124: Prepare reviewed launch-universe expansion plan

Goal:
Prepare the next deterministic expansion cycle from current deterministic fixtures into a manually reviewed launch-universe plan without changing runtime support truth or the v0.4 single-asset-first frontend workflow.

Task-scope paragraph:
A narrow operator-facing manifest planning cycle updated the reviewed Top-500 candidate workflow inputs and output artifacts while preserving runtime support truth, explicit non-live execution in CI, and v0.4 workflow boundaries.

Allowed files:
- `backend/models.py`
- `backend/top500_candidate_manifest.py`
- `tests/unit/test_top500_candidate_manifest.py`
- `tests/unit/test_repo_contract.py`
- `data/universes/us_common_stocks_top500.candidate.2026-04.json`
- `data/universes/us_common_stocks_top500.diff.2026-04.json`
- `docs/agent-journal/20260428T015329Z.md`

Do not change
- home search as the primary home-page action and comparison as a separate connected workflow
- v0.4 contextual glossary behavior on desktop and mobile, source drawer behavior, and asset-chat surfaces
- source-use policy, Golden Asset Source Handoff semantics, citation strictness, and `stale`/`partial`/`unknown`/`unavailable` handling
- safety guardrails around advice boundaries
- deterministic CI defaults and runtime support truth

Acceptance criteria completed:
- Candidate and diff artifacts are generated under deterministic reviewed-manifest naming for 2026-04.
- Top-500 candidate and diff data are stored in repository-scoped artifacts and do not replace runtime support runtime manifest files without manual promotion.
- Tests validate candidate-generation, search-classification, and repository contract behavior.
- `TASKS.md` contract markers were updated to recognize the empty-backlog state after this completion.
- No production/live provider or live market-data calls were introduced.

Required commands executed in this task branch:
- `python3 -m pytest tests/unit/test_top500_candidate_manifest.py tests/unit/test_search_classification.py tests/unit/test_repo_contract.py -q`
- `python3 -m pytest tests -q`
- `python3 evals/run_static_evals.py`
- `bash scripts/run_quality_gate.sh`
- `git diff --check`

Iteration budget:
- One agent-loop cycle.

Completion evidence:
- Implementation commit: `59769c1 chore(T-124): prepare reviewed launch-universe expansion plan`
- Local merge commit: `2c1cedc chore(T-124): merge prepare reviewed launch-universe expansion plan` (from `agent/T-124-20260428T015329Z`)
- Files updated in the commit: `backend/models.py`, `backend/top500_candidate_manifest.py`, `tests/unit/test_top500_candidate_manifest.py`, `tests/unit/test_repo_contract.py`, `data/universes/us_common_stocks_top500.candidate.2026-04.json`, `data/universes/us_common_stocks_top500.diff.2026-04.json`
- `docs/agent-journal/20260428T015329Z.md` records: `python3 -m pytest tests/unit/test_top500_candidate_manifest.py tests/unit/test_search_classification.py tests/unit/test_repo_contract.py -q` passed; `python3 -m pytest tests -q` passed (`442 passed`); `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed
- Remaining risk recorded in the journal: the candidate-manifest fixture is contract-bound and should be regenerated if Top-500 manifest model fields or serialization changes.

### T-123: Promote real official-source fetchers behind handoff-gated local opt-in

Goal:
Promote local operator-only official-source execution for golden assets from retrieval-only readiness to handoff-gated execution while preserving deterministic defaults and strict source evidence gates.

Completion details:
- Implementation commit: `b7bce2b feat(T-123): promote real official-source fetchers behind handoff-gated local opt-in`
- Local merge commit: `6f7e7fc chore(T-123): merge promote real official-source fetchers behind handoff-gated local opt-in` from branch `agent/T-123-20260428T013508Z`
- Files changed in implementation:
  - `backend/provider_adapters/sec_stock.py`
  - `backend/provider_adapters/etf_issuer.py`
  - `backend/repositories/weekly_news.py`
  - `backend/weekly_news_repository.py`
  - `tests/unit/test_provider_adapters.py`
  - `tests/unit/test_weekly_news.py`
  - `tests/unit/test_repo_contract.py`
- Validation updates in this cycle also covered task-state contract assertions in `tests/unit/test_repo_contract.py`.
- `docs/agent-journal/20260428T013508Z.md` records:
  - `python3 -m pytest tests -q` — pass (`442` tests)
  - `python3 evals/run_static_evals.py` — pass
  - `bash scripts/run_quality_gate.sh` — pass
  - `git diff --check` — pass
- Remaining risk recorded in journal: live fetch execution remains explicit local operator opt-in; no automatic production/live execution was introduced.

### T-122: Prove local durable repository smoke with API proxy enabled

Goal:
Prove and document a local durable repository smoke path that validates API-backed browser surfaces through the `/api` proxy and deterministic APIs, while staying within the v0.4 frontend workflow.

Completion details:
- Local implementation branch commit: `00d4bfe feat(T-122): prove local durable repository smoke with API proxy enabled`
- Local merge commit: `e18b039 chore(T-122): merge prove local durable repository smoke with API proxy enabled` from `agent/T-122-20260428T012934Z`
- Files changed: `tests/frontend/smoke.mjs`, `tests/unit/test_repo_contract.py`, `docs/local_fresh_data_ingest_to_render_runbook.md`, `docs/agent-journal/20260428T012934Z.md`
- The updated smoke path now includes:
  - local durable smoke enablement and prerequisite checks (`LEARN_TICKER_LOCAL_DURABLE_SMOKE`, local web/API base wiring)
  - durable route assertions for VOO asset render, API chat, asset export, source export, source-list route, compare route, compare export, and `/api/search` CORS behavior
  - explicit blocker output when durable prerequisites are missing
  - preservation of deterministic, non-durable smoke behavior when local durable mode is not available
- `docs/local_fresh_data_ingest_to_render_runbook.md` now documents:
  - local-durable prerequisite env wiring (`DATABASE_URL`, durable repository mode flags, web/API base URLs)
  - optional local-durable browser smoke command with explicit flags
  - v0.4 workflow and marker expectations for smoke checkpoints
- Journal-recorded checks passed:
  - `python3 -m pytest tests -q` (`439` passed)
  - `npm test`
  - `npm run typecheck`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
  - `git diff --check`
- T-122 was marked pass in `docs/agent-journal/20260428T012934Z.md`.

Remaining risks:
- `tests/unit/test_repo_contract.py` still carries historical markers for pre-`T-122` behavior and is expected to be recycled as those legacy markers deprecate.

### T-121: Add browser E2E local smoke for API-backed MVP flows

Goal:
Validate API-backed MVP browser endpoints with a localhost-only smoke path while keeping the v0.4 single-asset search and separate comparison workflow baseline.

Completion details:
- Implementation commit `1f4b96a feat(T-121): add browser E2E local smoke for API-backed MVP flows`.
- Local merge commit `45202d9 chore(T-121): merge browser E2E local smoke for API-backed MVP flows` from branch `agent/T-121-20260428T012309Z`.
- `tests/frontend/smoke.mjs` now adds an opt-in browser smoke path gated by `LEARN_TICKER_LOCAL_BROWSER_SMOKE` that normalizes web/API base URLs from `LEARN_TICKER_LOCAL_WEB_BASE` / `LEARN_TICKER_LOCAL_API_BASE`, applies request timeouts and network-event logging, validates `POST /api/assets/VOO/chat`, `/api/assets/VOO/export`, `/api/assets/VOO/sources/export`, `/compare?left=VOO&right=QQQ`, compare-export API, and backend CORS, and asserts required home/search/asset/source/glossary/compare/source-list markers before failing with logged path/network diagnostics.
- `package.json` and `apps/web/package.json` gained `test:browser-smoke` scripts using `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1`.
- `tests/unit/test_repo_contract.py` updated to keep roadmap markers aligned with current-task preparation.
- `docs/agent-journal/20260428T012309Z.md` confirms the required checks passed for this task branch:
  - `npm test`
  - `npm run typecheck`
  - `npm run build`
  - `python3 -m pytest tests -q` (`439 passed`)
  - `bash scripts/run_quality_gate.sh`
  - `git diff --check`
- Result: all required commands passed; no commit to source-use policy, v0.5 split, or core safety model was introduced.

Remaining risks:
- Browser smoke remains optional and requires operator-started local web/API services; it does not auto-start services.

### T-120: Implement v0.5 ETF manifest split contracts

Goal:
Replace the legacy combined ETF universe contract with separate v0.5 manifests for supported ETF generated-output coverage and ETF/ETP recognition-only blocked search states.

Completed details:
- Implementation commit `ae6b8b9 feat(T-120): implement v0.5 ETF manifest split contracts`.
- Merge commit `fc3fc0d chore(T-120): merge v0.5 ETF manifest split contracts` from branch `agent/T-120-20260428T011703Z`.
- `backend/etf_universe.py` now resolves generated ETF support from `data/universes/us_equity_etfs_supported.current.json` and recognition rows from `data/universes/us_etp_recognition.current.json`.
- `data/universes/us_equity_etfs_supported.current.json` and `data/universes/us_etp_recognition.current.json` were updated for deterministic split-manifest runtime authority.
- `tests/unit/test_search_classification.py` and `tests/unit/test_provider_adapters.py` were updated to enforce support-state behavior from the split manifests.
- `docs/agent-journal/20260428T011703Z.md` captures checks and remaining risks.
- Required commands executed and passed:

```bash
python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_provider_adapters.py tests/unit/test_repo_contract.py -q
python3 -m pytest tests -q
npm test
npm run typecheck
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
git diff --check
```
- `docs/agent-journal/20260428T011703Z.md` records all required commands passing for this task branch.
- Remaining risks:
  - Legacy `data/universes/us_equity_etfs.current.json` remains for repo continuity while runtime now reads split manifests.
  - Documentation in `docs/mvp_functional_gap_review.md` still describes the split as pending and needs follow-up update.

Completion summary:
- Task moved to Completed with no production or live-provider changes.
- Coverage for v0.5 split enforcement is now backed by deterministic fixtures and repository contract tests.

### T-119: Wire local frontend API access and backend CORS

Goal:
Fix the local MVP blockers where chat, export, and comparison frontend paths could resolve to frontend 404s or masked fixture fallback even though the FastAPI routes work directly.

Completed details:

- Added `apps/web/lib/apiEndpoints.ts` so browser-facing chat, export, and comparison helpers prefer `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL`, use `http://127.0.0.1:8000` during local development, and keep relative `/api` fallback for deployments that proxy the backend.
- Added a Next.js rewrite in `apps/web/next.config.mjs` so local `/api/:path*` requests can proxy to the configured FastAPI backend when links or helpers stay relative.
- Updated `apps/web/lib/assetChat.ts`, `apps/web/lib/exportControls.ts`, and `apps/web/lib/compare.ts` so chat POSTs, export links/POSTs, and server-side comparison fetches no longer depend on a missing Next API route.
- Added `build_cors_settings` and CORS diagnostics in `backend/settings.py`, then installed `CORSMiddleware` in `backend/main.py` when FastAPI is available and origins are configured.
- Updated frontend smoke and persistence-settings tests for the API helper, rewrite, and CORS settings.
- Updated implementation docs, the runtime gap audit, SPEC, EVALS, and this task tracker so the next development cycle starts from the new local API/CORS baseline.
- `docs/agent-journal/20260427T203834Z.md` records focused checks, the full quality gate, local dev-server smoke results, and the Docker availability blocker.

Remaining risks:

- This task wires local browser/API plumbing and deterministic tests. It does not add production auth, rate limiting, production deployment, broad live provider execution, or a full reviewed 500-name launch manifest.
- Real official-source acquisition remains opt-in and golden-asset scoped until a future task promotes handoff-gated fetcher execution.
- Local browser E2E is still manual curl/dev-server smoke in this task; an automated localhost browser smoke remains T-121.
- The v0.5 ETF supported-manifest and recognition-manifest split remains T-120.

### T-118: Prove local fresh-data ingest-to-render smoke path

Goal:
Document and test the local MVP path for manually ingesting a golden asset into configured durable repositories or deterministic in-memory equivalents, reading it through backend APIs, and rendering it in the frontend before production deployment work.

Completed details:

- Implementation commit `1fe95ee feat(T-118): prove local fresh-data ingest-to-render smoke path` added `docs/local_fresh_data_ingest_to_render_runbook.md`, updated `tests/integration/test_backend_api.py`, `tests/frontend/smoke.mjs`, `tests/unit/test_repo_contract.py`, and wrote `docs/agent-journal/20260427T054921Z.md`.
- Merged branch `agent/T-118-20260427T054921Z` into `main` with local merge commit `e51dd9f chore(T-118): merge prove local fresh-data ingest-to-render smoke path`.
- Added a local fresh-data ingest-to-render runbook covering deterministic `in_memory` smoke mode, optional operator-only `local_durable` and `operator_live_experiment` modes, placeholder-only local environment examples, manual pre-cache trigger checks, backend route verification, frontend dev-server verification, cleanup, and troubleshooting.
- The runbook explicitly states that fetching alone is retrieval, not evidence approval, and keeps Golden Asset Source Handoff as the gate before source snapshots, normalized facts, citations, generated-output cache records, exports, or rendered UI can use retrieved sources.
- Added deterministic integration smoke coverage for the VOO golden path through a manual pre-cache job, mocked official-source acquisition, parser diagnostics, approved handoff metadata, source snapshot writes, acquisition-backed knowledge-pack writes, Weekly News evidence writes, generated-output cache availability, configured backend read dependencies, backend route reads, source drawer, knowledge pack, glossary, chat, comparison export, and asset export checks.
- Added frontend smoke markers proving API-backed asset-page rendering surfaces still expose overview, details, Weekly News, source drawer, and glossary rendering markers with deterministic local fallback behavior, plus contract validation markers for overview and source drawer adapters.
- Preserved the v0.4 frontend workflow: home remains single stock/ETF search first, comparison remains separate through `/compare`, glossary remains contextual, source/glossary/chat mobile behavior remains bottom-sheet or full-screen where appropriate, stock-vs-ETF comparison keeps relationship badges, and Weekly News Focus may render smaller evidence-backed sets.
- `docs/agent-journal/20260427T054921Z.md` records these checks: `python3 -m pytest tests/integration/test_backend_api.py::test_t118_local_fresh_data_ingest_to_render_smoke_path_is_deterministic -q` passed; `python3 -m pytest tests/unit/test_repo_contract.py::test_tasks_general_mvp_roadmap_marks_t118_current_with_empty_backlog_after_promotion tests/unit/test_repo_contract.py::test_t118_local_fresh_data_runbook_covers_deterministic_smoke_without_live_requirements -q` passed; `npm test` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 37 tests; `python3 -m pytest tests/unit/test_repo_contract.py -q` passed with 18 tests; `python3 -m pytest tests/unit/test_ingestion_worker.py -q` passed with 26 tests; `npm run typecheck` passed; `python3 -m pytest tests/unit/test_ingestion_worker.py tests/unit/test_source_policy.py tests/unit/test_exports.py tests/unit/test_repo_contract.py -q` passed with 59 tests; `npm run build` passed; `python3 -m pytest tests -q` passed with 437 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - The smoke path is deterministic and golden-asset scoped. It uses mocked official-source acquisition, in-memory repositories, and existing fixture-backed generated rendering; it does not add real provider, storage, database, Redis, RSS, or LLM execution.
  - Acquisition-backed normalized knowledge-pack records remain non-generated metadata records; frontend-rendered overview reuse still depends on validated generated-output cache records paired with render-compatible deterministic knowledge-pack records.
  - Production deployment, production durable storage, scheduled jobs, source allowlist expansion, admin auth/rate limiting, and broader live ingestion remain outside T-118.

Completion commits:

- `1fe95ee feat(T-118): prove local fresh-data ingest-to-render smoke path`
- `e51dd9f chore(T-118): merge prove local fresh-data ingest-to-render smoke path`

### T-117: Execute handoff-gated official-source acquisition for golden assets

Goal:
Turn the existing opt-in official-source readiness boundaries into a mocked-HTTP execution path for golden SEC stock, ETF issuer, and Weekly News acquisition that writes only handoff-approved records.

Completed details:

- Implementation commit `32f1abf feat(T-117): execute handoff-gated official-source acquisition for golden assets` updated `backend/provider_adapters/sec_stock.py`, `backend/provider_adapters/etf_issuer.py`, `backend/repositories/weekly_news.py`, `backend/weekly_news_repository.py`, `backend/ingestion_worker.py`, focused unit tests, roadmap contract tests, and `docs/agent-journal/20260427T053609Z.md`.
- Merged branch `agent/T-117-20260427T053609Z` into `main` with local merge commit `0c0cf0f chore(T-117): merge execute handoff-gated official-source acquisition for golden assets`.
- Added mocked HTTP/fetch and parser adapter boundaries for golden SEC stock and ETF issuer official-source acquisition.
- Added handoff-gated execution helpers that validate parser outcomes and Golden Asset Source Handoff before records can feed source snapshots, knowledge packs, or downstream cache metadata.
- Extended official Weekly News mocked acquisition with fetch/parser/handoff diagnostics and counts while preserving official-source filtering, dedupe, selected-item limits, and AI Comprehensive Analysis suppression below two selected items.
- Added ingestion worker fail-closed enforcement so live-attempted writer routing requires explicit official-source handoff approval metadata.
- `docs/agent-journal/20260427T053609Z.md` records these checks: `python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_ingestion_worker.py tests/unit/test_weekly_news.py tests/unit/test_source_policy.py -q` passed with 82 tests; `python3 -m pytest tests/unit/test_source_snapshot_repository.py tests/unit/test_knowledge_pack_repository.py tests/unit/test_cache_contracts.py tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 90 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 36 tests; `python3 -m pytest tests -q` passed with 435 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - T-117 remains mocked and golden-asset scoped. No real SEC, issuer, Weekly News, RSS, provider, storage, database, Redis, or LLM calls were added.
  - The new execution helpers prove ingest-to-persist writer routing, but they do not yet provide a local fresh-data ingest-to-render smoke path from persisted records through public routes.
  - Production source allowlist review, broad parser maintenance, scheduled jobs, and deployment wiring remain outside this task.

Completion commits:

- `32f1abf feat(T-117): execute handoff-gated official-source acquisition for golden assets`
- `0c0cf0f chore(T-117): merge execute handoff-gated official-source acquisition for golden assets`

### T-116: Add reviewed Top-500 candidate manifest workflow contracts

Goal:
Add a deterministic reviewed candidate-manifest workflow for monthly Top-500 stock universe refreshes without changing runtime coverage or overwriting the approved current manifest.

Completed details:

- Implementation commit `b7637e5 feat(T-116): add reviewed Top-500 candidate manifest workflow contracts` updated `backend/models.py`, added `backend/top500_candidate_manifest.py`, added `scripts/generate_top500_candidate_manifest.py`, created deterministic candidate and diff fixtures under `data/universes/`, added Top-500 refresh fixtures under `tests/fixtures/top500_refresh/`, and updated focused unit tests plus `docs/agent-journal/20260427T052312Z.md`.
- Merged branch `agent/T-116-20260427T052312Z` into `main` with local merge commit `4d2f2a7 chore(T-116): merge reviewed Top-500 candidate manifest workflow contracts`.
- `backend/models.py` added Top-500 candidate workflow contract models for official holdings inputs, validation status, review triggers, candidate rows, candidate manifests, and diff reports.
- `backend/top500_candidate_manifest.py` added deterministic candidate generation, mocked official IWB primary ranking, official SPY/IVV/VOO fallback handling, source handoff validation, common-stock filtering, class-share ticker normalization, SEC/Nasdaq validation, ranking/tie-break behavior, candidate checksum generation, diff-report shaping, and manual-promotion gate helpers.
- `scripts/generate_top500_candidate_manifest.py` added a deterministic local script entrypoint backed by fixtures and explicit candidate/diff output paths.
- `data/universes/us_common_stocks_top500.candidate.2026-04.json` and `data/universes/us_common_stocks_top500.diff.2026-04.json` were added as reviewed-output fixtures; `data/universes/us_common_stocks_top500.current.json` was not edited.
- `tests/fixtures/top500_refresh/` added mocked official IWB, SPY, IVV, and VOO holdings plus SEC `company_tickers_exchange.json`-style and Nasdaq symbol-directory validation fixtures.
- `tests/unit/test_top500_candidate_manifest.py` added coverage for primary IWB ranking, fallback source behavior, source handoff requirements, non-common-stock filtering, class-share normalization, SEC/Nasdaq validation warnings, deterministic checksums, diff-report content, and manual-review triggers.
- `tests/unit/test_search_classification.py` added coverage proving runtime search/support classification still reads only the approved current manifest and ignores candidate/diff artifacts for coverage truth.
- `tests/unit/test_source_policy.py` added coverage for official-source provenance handoff metadata used by the candidate workflow, and `tests/unit/test_repo_contract.py` was updated for the new roadmap/task contract markers.
- `docs/agent-journal/20260427T052312Z.md` records these checks: `python3 -m pytest tests/unit/test_top500_candidate_manifest.py tests/unit/test_search_classification.py tests/unit/test_source_policy.py tests/unit/test_repo_contract.py -q` passed with 43 tests; `python3 -m pytest tests -q` passed with 428 tests; `npm test` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - T-116 is deterministic contract and fixture work only. It does not fetch live IWB/SPY/IVV/VOO holdings, schedule refreshes, promote a candidate, or replace `data/universes/us_common_stocks_top500.current.json`.
  - The generated candidate fixture uses mocked official-source inputs and a small declared rank limit for regression coverage; a real monthly candidate still needs handoff-gated source acquisition and manual review before promotion.
  - Runtime search/support classification remains tied to the approved current manifest; candidate and diff files are not runtime coverage truth.

Completion commits:

- `b7637e5 feat(T-116): add reviewed Top-500 candidate manifest workflow contracts`
- `4d2f2a7 chore(T-116): merge reviewed Top-500 candidate manifest workflow contracts`

### T-115: Add Golden Asset Source Handoff contract enforcement

Goal:
Make Golden Asset Source Handoff a first-class deterministic contract across source policy, persisted evidence records, citations, generated-output cache records, source drawer responses, and exports.

Completed details:

- Implementation commit `ebb7dbd feat(T-115): add Golden Asset Source Handoff contract enforcement` updated `backend/models.py`, `backend/source_policy.py`, `backend/citations.py`, `backend/cache.py`, source snapshot, knowledge-pack, Weekly News, and generated-output repository validators, source drawer/export paths, focused unit tests, roadmap contract tests, and `docs/agent-journal/20260427T050512Z.md`.
- Merged branch `agent/T-115-20260427T050512Z` into `main` with local merge commit `ed821fe chore(T-115): merge Golden Asset Source Handoff contract enforcement`.
- `backend/models.py` added explicit source handoff metadata fields and enums for review status, parser status, storage rights, and export rights across source attribution, source checksums, knowledge-pack source metadata, source documents, source drawer groups, chat sources, and export source metadata.
- `backend/source_policy.py` added `SourceHandoffValidationResult`, `SourceHandoffContractError`, `source_handoff_fields_from_policy`, `validate_source_handoff`, and `require_source_handoff`, with fail-closed reason codes for missing identity/type/official status/rationale/freshness metadata, non-allowed allowlist or review states, rejected source policy, unknown or rejected rights, parser failures or pending review, weak source quality, and hidden/internal source identities.
- `backend/cache.py` now carries source identity, official-source status, freshness/as-of fields, source quality, storage rights, export rights, review status, approval rationale, parser status, and parser diagnostics into checksum records.
- Repository validation now applies Golden Asset Source Handoff to source snapshot artifacts, generated knowledge-pack evidence, source checksums backing generated outputs, selected Weekly News evidence, and generated-output cache source checksums.
- Citation, source drawer, and export paths now skip or flag sources that fail handoff validation, preserving same-asset/source-use gates and preventing unapproved evidence from supporting citation claims, source drawer excerpts, source-list exports, asset exports, comparison exports, or chat transcript exports.
- `tests/unit/test_source_policy.py` added direct coverage for required handoff metadata, missing metadata defaults, parser-failed blocking, pending-review blocking, hidden/internal blocking, and metadata-only generated-claim blocking.
- `tests/unit/test_cache_contracts.py` added generated-output cache coverage for parser-invalid and pending-review source checksum blocking, and `tests/unit/test_repo_contract.py` was updated for the new roadmap/source-handoff contract markers.
- `docs/agent-journal/20260427T050512Z.md` records these checks: `python3 -m pytest tests/unit/test_source_policy.py tests/unit/test_source_snapshot_repository.py tests/unit/test_knowledge_pack_repository.py tests/unit/test_weekly_news.py tests/unit/test_cache_contracts.py tests/unit/test_citation_validation.py tests/unit/test_source_drawer.py tests/unit/test_exports.py tests/unit/test_repo_contract.py -q` passed with 126 tests; `python3 -m pytest tests/unit/test_overview_generation.py tests/unit/test_comparison_generation.py tests/unit/test_chat_generation.py tests/unit/test_glossary_context.py tests/unit/test_safety_guardrails.py -q` passed with 77 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 36 tests; `python3 -m pytest tests -q` passed with 420 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - T-115 is contract-only enforcement. It does not add live fetching, source allowlist expansion, Top-500 candidate generation, production persistence execution, production deployment, prompt rewrites, or frontend redesign.
  - Existing deterministic fixtures still use compatibility defaults for approved parser/review/storage/export metadata where older response objects did not yet carry explicit values. Newly validated repository/cache/source paths now reject parser-failed, pending-review, rejected, hidden/internal, wrong-asset, and restricted evidence when those states are present.
  - Broader real-source acquisition still needs to populate the new handoff fields from actual parser and review outcomes before live retrieval can safely feed evidence paths.

Completion commits:

- `ebb7dbd feat(T-115): add Golden Asset Source Handoff contract enforcement`
- `ed821fe chore(T-115): merge Golden Asset Source Handoff contract enforcement`

### T-114: Expand launch pre-cache coverage and add MVP readiness regression matrix

Goal:
Expand deterministic launch pre-cache coverage beyond the smallest golden path and add an MVP readiness regression matrix plus go/no-go checklist before production deployment work, explicitly preserving the updated Top-500 manifest-owned coverage rule and Golden Asset Source Handoff gates.

Completed details:

- Implementation commit `5debd8e feat(T-114): expand launch pre-cache coverage and add MVP readiness regression matrix` updated `apps/web/lib/search.ts`, `tests/frontend/smoke.mjs`, `tests/unit/test_repo_contract.py`, `docs/mvp_launch_readiness_regression_matrix.md`, `docs/mvp_go_no_go_checklist.md`, and `docs/agent-journal/20260427T045509Z.md`.
- Merged branch `agent/T-114-20260427T045509Z` into `main` with local merge commit `73d0f08 chore(T-114): merge expand launch pre-cache coverage and add MVP readiness regression matrix`.
- `apps/web/lib/search.ts` expanded deterministic local search fallback blocked-state parity for recognized ETF-like categories: `ARKK` as an active ETF, `BND` as a fixed-income ETF, `GLD` as a commodity ETF, `AOR` as a multi-asset ETF, and `VXX` as an ETN-style out-of-scope product.
- The blocked search explanations now map those categories to explicit unsupported or out-of-scope reasons while preserving no-generated-output behavior for unsupported and out-of-scope assets.
- `docs/mvp_launch_readiness_regression_matrix.md` added the deterministic MVP launch readiness matrix covering backend route contracts, frontend workflow markers, launch pre-cache states, source-use and Golden Asset Source Handoff gates, Weekly News Focus evidence limits, AI Comprehensive Analysis thresholds, exports, glossary, chat, comparison, mobile behavior markers, Top-500 runtime-manifest support, and no-live-call defaults.
- `docs/mvp_go_no_go_checklist.md` recorded the production no-go decision and open production blockers for admin auth, rate limiting, deployment environment validation, private object storage, database migrations, Cloud Run API and Job settings, recurring jobs, source allowlist review, live-provider opt-in, monitoring, rollback, cost controls, launch support, and legal/compliance review.
- `tests/frontend/smoke.mjs` added static regression markers for the new local fallback blocked categories and blocked explanation categories.
- `tests/unit/test_repo_contract.py` added contract coverage for the readiness matrix, go/no-go checklist, required T-114 commands, v0.4 frontend workflow markers, source-use states, route surfaces, launch pre-cache coverage, production no-go risks, and secret/no-live-call exclusions.
- `docs/agent-journal/20260427T045509Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 36 tests; `python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_ingestion_jobs.py tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 59 tests; `python3 -m pytest tests -q` passed with 419 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed after the journal entry.
- Remaining risks from the journal:
  - T-114 remains deterministic regression coverage only. It does not enable production deployment, production persistence, live source/provider calls, recurring jobs, paid providers, broad news providers, source allowlist expansion, or live LLM generation.
  - At T-114 completion, Golden Asset Source Handoff had documented regression coverage and existing partial enforcement; T-115 has since completed the contract-enforcement task above.
  - Top-500 monthly candidate-manifest generation and reviewed promotion remain T-116 scope; the current runtime stock manifest was not edited.
  - Eligible-not-cached launch assets remain non-generated until validated source packs and handoff-gated persistence exist.

Completion commits:

- `5debd8e feat(T-114): expand launch pre-cache coverage and add MVP readiness regression matrix`
- `73d0f08 chore(T-114): merge expand launch pre-cache coverage and add MVP readiness regression matrix`

### T-113: Add official-source Weekly News live acquisition for golden assets

Goal:
Add explicit opt-in server-side live acquisition readiness for official-source Weekly News Focus evidence for golden assets, preserving source-use gates, dedupe, evidence-limited states, market-week windows, and AI Comprehensive Analysis thresholds.

Completed details:

- Implementation commit `0e33516 feat(T-113): add official-source Weekly News live acquisition for golden assets` updated `backend/settings.py`, `backend/repositories/weekly_news.py`, `backend/weekly_news_repository.py`, `backend/ingestion_worker.py`, focused unit tests, roadmap contract tests, and `docs/agent-journal/20260426T221149Z.md`.
- Merged branch `agent/T-113-20260426T221149Z` into `main` with local merge commit `90908ac chore(T-113): merge official-source Weekly News live acquisition for golden assets`.
- `backend/settings.py` extended the existing `live-acquisition-readiness-settings-v1` boundary with disabled-by-default Weekly News live acquisition readiness, including `LIVE_WEEKLY_NEWS_ACQUISITION_ENABLED`, `LIVE_WEEKLY_NEWS_OFFICIAL_SOURCE_CONFIGURED`, shared `LIVE_SOURCE_RATE_LIMIT_READY`, `LIVE_ACQUISITION_WEEKLY_NEWS_WRITER_READY`, `weekly_news_ready`, missing-reason diagnostics, and sanitized `safe_diagnostics`.
- `backend/repositories/weekly_news.py` added `WEEKLY_NEWS_LIVE_ACQUISITION_READINESS_BOUNDARY`, `WEEKLY_NEWS_OFFICIAL_SOURCE_MOCK_ACQUISITION_BOUNDARY`, `WeeklyNewsLiveAcquisitionReadiness`, `WeeklyNewsOfficialSourceAcquisitionResult`, `evaluate_weekly_news_live_acquisition_readiness`, and `acquire_weekly_news_event_evidence_from_official_sources`.
- Weekly News readiness now requires explicit opt-in, official-source configuration, source rate-limit readiness, Weekly News evidence writer readiness, same-asset support-state validation, golden-asset scope for AAPL/VOO/QQQ, source-use validation, and U.S. Eastern market-week window validation before mocked official-source acquisition can proceed.
- Mocked official-source acquisition filters to official filing, investor-relations release, ETF issuer announcement, prospectus update, and fact-sheet change source tiers, then routes through the existing fixture acquisition and Weekly News evidence repository validation path.
- Weekly News evidence validation now requires `sha256:` title checksums when present and `sha256:` evidence checksums, preserving compact metadata and rejecting malformed evidence before persistence.
- `backend/ingestion_worker.py` now fails closed when a ready live Weekly News acquisition outcome requires repository writers but no Weekly News repository writer is configured, while still routing ready mocked records through the existing injected writer boundary when configured.
- Tests added or updated coverage for blocked default Weekly News readiness, missing official-source/rate-limit/writer readiness, ready weekly settings, ready official-source AAPL/VOO/QQQ acquisition paths, unsupported and wrong-asset candidates, non-official, promotional, rejected, stale-without-label, and outside-window candidates, evidence checksum validation, sanitized diagnostics, worker fail-closed behavior, and worker persistence through the mocked Weekly News writer.
- `docs/agent-journal/20260426T221149Z.md` records these checks: `python3 -m pytest tests/unit/test_weekly_news.py tests/unit/test_overview_generation.py tests/unit/test_source_policy.py -q` passed with 47 tests; `python3 -m pytest tests/unit/test_ingestion_worker.py tests/unit/test_ingestion_jobs.py -q` passed with 40 tests; `python3 -m pytest tests/unit/test_persistence_settings.py -q` passed with 18 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 36 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 30 tests; `python3 -m pytest tests -q` passed with 418 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - Weekly News live acquisition remains readiness-only and mocked. No real HTTP transport, broad news provider, paid news API, scheduler, production database/object-storage execution, or deployment wiring was added.
  - Golden coverage is limited to AAPL, VOO, and QQQ official-source candidate paths that route through existing Weekly News evidence selection and repository validation.
  - The path persists evidence metadata only; it does not create live generated Weekly News prose, AI Comprehensive Analysis content, public route schema changes, frontend changes, or generated-output cache content changes.

Completion commits:

- `0e33516 feat(T-113): add official-source Weekly News live acquisition for golden assets`
- `90908ac chore(T-113): merge official-source Weekly News live acquisition for golden assets`

### T-112: Add explicit opt-in live SEC and ETF issuer golden acquisition

Goal:
Add explicit server-side opt-in live acquisition readiness for the golden SEC EDGAR stock and ETF issuer paths, writing through configured repositories, while keeping normal CI fully mocked and deterministic.

Completed details:

- Implementation commit `d73e371 feat(T-112): add explicit opt-in live SEC and ETF issuer golden acquisition` updated `backend/settings.py`, `backend/provider_adapters/sec_stock.py`, `backend/provider_adapters/etf_issuer.py`, `backend/provider_adapters/__init__.py`, `backend/ingestion_worker.py`, focused unit tests, roadmap contract tests, and `docs/agent-journal/20260426T215921Z.md`.
- Merged branch `agent/T-112-20260426T215921Z` into `main` with local merge commit `eae0cd1 chore(T-112): merge explicit opt-in live SEC and ETF issuer golden acquisition`.
- `backend/settings.py` added the `live-acquisition-readiness-settings-v1` settings boundary with disabled-by-default live SEC stock and ETF issuer acquisition flags, source configuration readiness flags, shared rate-limit readiness, repository writer readiness flags, missing-reason diagnostics, and sanitized `safe_diagnostics` that avoid secret, database URL, storage URL, and key exposure.
- `backend/provider_adapters/sec_stock.py` added `SEC_STOCK_LIVE_ACQUISITION_READINESS_BOUNDARY`, `SecStockLiveAcquisitionReadiness`, and `evaluate_sec_stock_live_acquisition_readiness` for the AAPL SEC golden path. Readiness requires explicit opt-in, SEC source configuration, rate-limit readiness, repository writer readiness, supported common-stock identity, Top-500 manifest/CIK validation, source-use validation, same-asset/source binding, `sha256:` checksums, and non-rejected source policy metadata.
- `backend/provider_adapters/etf_issuer.py` added `ETF_ISSUER_LIVE_ACQUISITION_READINESS_BOUNDARY`, `EtfIssuerLiveAcquisitionReadiness`, and `evaluate_etf_issuer_live_acquisition_readiness` for VOO and QQQ issuer golden paths. Readiness requires explicit opt-in, issuer source configuration, rate-limit readiness, repository writer readiness, supported non-leveraged U.S. equity ETF identity, ETF universe generation eligibility, issuer/source binding, same-asset citations, `sha256:` checksums, and non-rejected source policy metadata.
- `backend/ingestion_worker.py` added live acquisition metadata fields to deterministic fixture outcomes, records live readiness metadata on the ledger, fails closed before source writes when live readiness fails, and routes readiness-passed mocked acquisition records only through existing source snapshot and knowledge-pack writer boundaries.
- Tests added coverage for blocked default readiness, ready AAPL/VOO paths, wrong CIK, wrong issuer, wrong source binding, unsupported/out-of-scope inputs, invalid checksum/source-use validation, sanitized diagnostics, worker fail-closed behavior, and worker routing through existing mocked writer boundaries.
- `docs/agent-journal/20260426T215921Z.md` records these checks: `python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_ingestion_worker.py tests/unit/test_ingestion_jobs.py tests/unit/test_source_policy.py -q` passed with 64 tests; `python3 -m pytest tests/unit/test_persistence_settings.py -q` passed with 18 tests; `python3 -m pytest tests/unit/test_source_snapshot_repository.py tests/unit/test_knowledge_pack_repository.py tests/unit/test_cache_contracts.py -q` passed with 59 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 36 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 30 tests; `python3 -m pytest tests -q` passed with 412 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed, including Python tests, static evals, frontend smoke, typecheck, build, and backend checks; `git diff --check` passed.
- Remaining risks from the journal:
  - Live SEC and ETF issuer acquisition remains readiness-only. No real HTTP transport, production credentials, production database/object-storage execution, Cloud Run Job wiring, recurring jobs, or source-provider calls were added.
  - Readiness is exercised through deterministic AAPL, VOO, and QQQ mocked acquisition paths and existing repository validation boundaries.
  - Generated-output cache metadata remains governed by existing validation paths; T-112 does not create live generated prose, Weekly News acquisition, or public route behavior changes.

Completion commits:

- `d73e371 feat(T-112): add explicit opt-in live SEC and ETF issuer golden acquisition`
- `eae0cd1 chore(T-112): merge explicit opt-in live SEC and ETF issuer golden acquisition`

### T-111: Wire local durable repository execution with in-memory fallback

Goal:
Add local durable Postgres/object-storage-style repository execution for ingestion ledger, source snapshots, knowledge packs, Weekly News evidence, and generated-output cache records while preserving in-memory fallback and deterministic CI.

Completed details:

- Implementation commit `9579789 feat(T-111): wire local durable repository execution with in-memory fallback` updated `backend/settings.py`, `backend/db.py`, `backend/persistence.py`, `backend/main.py`, durable-capable repository modules for ingestion jobs, source snapshots, knowledge packs, Weekly News evidence, and generated-output cache records, focused unit tests, roadmap contract tests, and `docs/agent-journal/20260426T214414Z.md`.
- Merged branch `agent/T-111-20260426T214414Z` into `main` with local merge commit `5086635 chore(T-111): merge wire local durable repository execution with in-memory fallback`.
- `backend/settings.py` added explicit local durable repository settings and sanitized diagnostics for `LOCAL_DURABLE_REPOSITORIES_ENABLED`, `LOCAL_DURABLE_OBJECT_NAMESPACE`, and `LOCAL_DURABLE_REPOSITORY_COMMIT_ON_WRITE`, with disabled-by-default fallback and validation that rejects public, signed, secret-like, or frontend-readable object namespaces.
- `backend/persistence.py` added `LocalDurableRepositoryFactories`, lazy durable session wrapping, factory methods for ingestion job ledger, source snapshot, knowledge-pack, Weekly News, and generated-output cache repositories, and `build_backend_read_dependencies_from_local_durable_config` with fail-safe fallback to default in-memory behavior when configuration is absent, disabled, invalid, or cannot be constructed.
- `backend/main.py` now configures backend read dependencies from the local durable configuration while preserving fixture/in-memory fallback and avoiding public route shape changes.
- Durable-capable repository modules now support validated `save_repository_record`/`save`/`add_all` write boundaries, optional `commit_on_write`, and read helpers keyed by ticker, job ID, artifact category, or comparison identity as appropriate.
- Ingestion job durable execution preserves validated ledger records and states through save/read tests without import-time database or provider calls.
- Source snapshot durable execution preserves metadata-only private artifact records and continues to reject wrong-asset/source bindings, invalid checksums, public or signed storage references, raw provider payload flags, raw source text flags, and unsanitized diagnostics.
- Knowledge-pack durable execution preserves validated acquisition-backed records by ticker, including same-asset facts, source documents, allowed excerpts/chunks, evidence gaps, source checksums, and non-generated blocked states.
- Weekly News durable execution preserves validated event evidence by ticker, including market-week windows, selected-event counts, limited or empty evidence states, source-use gates, and AI Comprehensive Analysis suppression metadata.
- Generated-output cache durable execution preserves validated cache metadata and read helpers by asset artifact category or comparison identity without storing raw model reasoning, hidden prompts, raw user text, transcripts, unrestricted source text, or provider payloads.
- `docs/agent-journal/20260426T214414Z.md` records these checks: `python3 -m pytest tests/unit/test_persistence_settings.py tests/unit/test_ingestion_job_repository.py tests/unit/test_source_snapshot_repository.py tests/unit/test_knowledge_pack_repository.py tests/unit/test_weekly_news.py tests/unit/test_cache_contracts.py -q` passed with 107 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 36 tests; `python3 -m pytest tests/unit/test_ingestion_worker.py -q` passed with 20 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 30 tests after a focused stale-roadmap assertion update; `python3 -m pytest tests -q` passed with 406 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - Durable execution is still exercised through mocked/local session boundaries only; no live Postgres, object storage, source acquisition, provider calls, or production deployment wiring was added.
  - SQLAlchemy-backed execution remains factory-gated and lazy, with fallback to default in-memory behavior when config is disabled, invalid, missing, or cannot be safely constructed.
  - Durable repositories store validated metadata records only and do not store raw source text, raw provider payloads, hidden prompts, raw model reasoning, raw user text, transcripts, secrets, signed URLs, or public storage URLs.

Completion commits:

- `9579789 feat(T-111): wire local durable repository execution with in-memory fallback`
- `5086635 chore(T-111): merge wire local durable repository execution with in-memory fallback`

### T-110: Verify persisted golden-path comparison, chat, sources, glossary, and exports end to end

Goal:
Prove the MVP learning surfaces can render and export persisted golden-path evidence and generated-output cache records end to end after T-109 made frontend search and asset pages API-backed.

Completed details:

- Implementation commit `032ca82 feat(T-110): verify persisted golden-path comparison, chat, sources, glossary, and exports end to end` updated `backend/glossary.py`, `backend/main.py`, `backend/overview.py`, `tests/integration/test_backend_api.py`, `tests/unit/test_repo_contract.py`, and `docs/agent-journal/20260426T212915Z.md`.
- Merged branch `agent/T-110-20260426T212915Z` into `main` with local merge commit `e3fdee4 chore(T-110): merge verify persisted golden-path comparison, chat, sources, glossary, and exports end to end`.
- `backend/glossary.py` added a configured persisted knowledge-pack reader path for glossary responses, using `read_persisted_knowledge_pack_response` and repository-record conversion when validated persisted records are available, with deterministic fixture fallback when records are missing, unavailable, non-generated, or invalid.
- `backend/main.py` now passes the configured `knowledge_pack_reader` into `/api/assets/{ticker}/glossary`, aligning glossary with the configured backend read dependency pattern already used by overview, sources, comparison, chat, Weekly News, and exports.
- `backend/overview.py` received a narrow compatibility update needed by persisted golden-path route verification.
- `tests/integration/test_backend_api.py` added configured golden repository coverage proving persisted AAPL, VOO, and QQQ records can drive overview, Weekly News, source drawer, glossary, VOO-vs-QQQ comparison, grounded chat, asset export, source-list export, comparison export, and chat transcript export through existing backend route dependencies.
- The persisted route coverage verifies evidence-limited Weekly News behavior: QQQ returns one selected item against a configured maximum of eight with `limited_verified_set`, AI Comprehensive Analysis remains suppressed below the two-item threshold, and AAPL returns an empty Weekly News state with analysis suppressed.
- The route coverage verifies source drawer metadata, allowed source-use policies, allowed excerpts, same-asset glossary bindings for AAPL revenue context, same-comparison-pack comparison citations for VOO-vs-QQQ, educational grounded chat citations for VOO, JSON export validation metadata, educational disclaimers, licensing notes, and omission of raw model reasoning/OpenRouter markers.
- `tests/unit/test_repo_contract.py` was updated to mark T-110 as the current roadmap task during that branch and keep T-111 through T-114 in the prepared backlog.
- `docs/agent-journal/20260426T212915Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 36 tests; `python3 -m pytest tests/unit/test_comparison_generation.py tests/unit/test_chat_generation.py tests/unit/test_exports.py tests/unit/test_source_drawer.py tests/unit/test_glossary_context.py -q` passed with 56 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 30 tests; `python3 -m pytest tests -q` passed with 396 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - Verification remains deterministic and in-memory/mocked only; no durable local database/object-storage execution, live official-source acquisition, live provider calls, or production deployment wiring was added.
  - Backend persisted verification covers the existing supported VOO-vs-QQQ comparison path; the frontend-only AAPL-vs-VOO stock-vs-ETF relationship view remains covered by existing frontend smoke/static markers and is not converted into a new backend comparison route.
  - A persisted details-route edge case with complex normalized fact values was observed during focused testing but left out of scope for T-110 because the task targets comparison, chat, sources, glossary, Weekly News, and exports.

Completion commits:

- `032ca82 feat(T-110): verify persisted golden-path comparison, chat, sources, glossary, and exports end to end`
- `e3fdee4 chore(T-110): merge verify persisted golden-path comparison, chat, sources, glossary, and exports end to end`

### T-109: Wire frontend search and dynamic asset pages to backend APIs

Goal:
Move frontend search, pending-ingestion states, and dynamic asset pages from local-fixture-first behavior to backend API-backed behavior while preserving deterministic fixture fallback during transition.

Completed details:

- Implementation commit `3b35858 feat(T-109): wire frontend search and dynamic asset pages to backend APIs` updated `apps/web/lib/search.ts`, `apps/web/components/SearchBox.tsx`, `apps/web/lib/assetOverview.ts`, `apps/web/app/assets/[ticker]/page.tsx`, `apps/web/app/assets/[ticker]/sources/page.tsx`, `tests/frontend/smoke.mjs`, and `docs/agent-journal/20260426T211844Z.md`.
- Roadmap-contract commit `f932b20 chore(T-109): update roadmap contract for promoted task` updated `TASKS.md` and `tests/unit/test_repo_contract.py`.
- Merged branch `agent/T-109-20260426T211844Z` into `main` with local merge commit `2ff9750 chore(T-109): merge wire frontend search and dynamic asset pages to backend APIs`.
- `apps/web/lib/search.ts` added `resolveSearchResponse`, `fetchBackendSearchResponse`, `/api/search` endpoint construction from `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL`, backend response-shape validation, and fixture fallback through `resolveLocalSearchResponse` for unavailable API configuration, failed requests, and invalid payloads.
- Search comparison-query handling remains local-first so clear `A vs B` searches still route to `/compare?left=...&right=...` instead of becoming a two-input home workflow.
- `apps/web/components/SearchBox.tsx` now keeps immediate deterministic local search state while asynchronously resolving the configured backend search contract, with loading copy that explicitly preserves fixture fallback.
- `apps/web/lib/assetOverview.ts` now allows backend overview mapping without an existing local fixture, merges backend citations/source documents with fallback data when present, and derives facts and citation contexts from backend overview sections for dynamic supported pages.
- `apps/web/app/assets/[ticker]/page.tsx` now attempts backend overview loading for fixture and non-fixture tickers, renders `LimitedAssetStatePage` for blocked, unknown, unsupported, out-of-scope, or pending-ingestion states, and builds empty Weekly News Focus plus suppressed AI Comprehensive Analysis fallbacks when backend-only dynamic pages lack local timely-context fixtures.
- `apps/web/app/assets/[ticker]/sources/page.tsx` now resolves source-list support state through `resolveSearchResponse`, preserving blocked source-list behavior for unsupported, out-of-scope, unknown, unavailable, and eligible-not-cached states.
- `tests/frontend/smoke.mjs` was updated to assert backend search preference before fixture fallback, dynamic asset limited-state markers, pending-ingestion/no-generated-output markers, source-list search resolution, and continued no-inline-fetch/no-live-external-call frontend boundaries.
- `docs/agent-journal/20260426T211844Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 35 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 30 tests; `python3 -m pytest tests -q` passed with 395 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - Frontend search now prefers `/api/search` only when a configured API base is available; local/offline behavior still depends on deterministic fixture fallback.
  - Dynamic backend-only asset pages can render from the overview contract and show blocked or pending states, but persisted comparison/chat/export end-to-end verification remains T-110 scope.
  - No live providers, production persistence, deployment wiring, or broad pre-cache expansion were added.

Completion commits:

- `f932b20 chore(T-109): update roadmap contract for promoted task`
- `3b35858 feat(T-109): wire frontend search and dynamic asset pages to backend APIs`
- `2ff9750 chore(T-109): merge wire frontend search and dynamic asset pages to backend APIs`

### T-108: Activate generated-output cache writes and freshness invalidation for validated outputs

Goal:
Activate deterministic generated-output cache writes for validated, citation-bound, source-policy-allowed golden-path outputs and preserve freshness-hash invalidation.

Completed details:

- Implementation commit `18af86e feat(T-108): activate generated-output cache writes and freshness invalidation for validated outputs` updated `backend/repositories/generated_outputs.py`, `backend/generated_output_cache_repository.py`, `backend/repositories/__init__.py`, `backend/overview.py`, `backend/comparison.py`, `backend/chat.py`, `backend/export.py`, `backend/ingestion_worker.py`, `tests/unit/test_cache_contracts.py`, `tests/unit/test_overview_generation.py`, `tests/unit/test_comparison_generation.py`, `tests/unit/test_chat_generation.py`, `tests/unit/test_exports.py`, `tests/unit/test_ingestion_worker.py`, `tests/unit/test_repo_contract.py`, and `docs/agent-journal/20260426T061322Z.md`.
- Merged branch `agent/T-108-20260426T061322Z` into `main` with local merge commit `e2fb8a5 chore(T-108): merge activate generated-output cache writes and freshness invalidation for validated outputs`.
- `backend/repositories/generated_outputs.py` added `InMemoryGeneratedOutputCacheRepository` plus `persist_generated_output_cache_records`, allowing configured mocked writers to validate and persist generated-output cache records through `persist`, `write_generated_output_cache_records`, or `save` writer boundaries.
- The in-memory repository indexes validated records by cache entry ID, asset/artifact category, and comparison/artifact category, and exposes deterministic read helpers for asset overview, grounded chat answers, exports, source-list metadata, and comparison output records.
- `backend/generated_output_cache_repository.py` added `build_deterministic_generated_output_cache_records`, which builds cache keys, knowledge-pack freshness hashes, generated-output freshness hashes, schema/prompt metadata, deterministic model metadata, citation IDs, TTL metadata, and validation-ready generated-output cache records from existing deterministic knowledge inputs.
- Freshness validation was tightened so unknown or unavailable source freshness can be cacheable only when explicit section or evidence labels carry the corresponding `unknown` or `unavailable` state.
- `backend/overview.py`, `backend/comparison.py`, and `backend/chat.py` added optional generated-output cache writer hooks that write only after existing deterministic output validation passes, citations bind to the same asset or comparison pack, forbidden advice phrases are absent, and required citations/source checksums are present.
- `backend/export.py` added optional cache writer hooks for asset-page export metadata, asset source-list metadata, comparison export metadata, and educational chat export metadata while preserving export validation and source-use behavior.
- `backend/ingestion_worker.py` added a `GeneratedOutputCacheWriterBoundary`, fixture outcome support for generated-output cache records, worker metadata for generated-output cache persistence, and fail-closed behavior when a configured mocked writer rejects persistence.
- Tests were added or updated for generated-output cache writer activation, deterministic cache record construction, freshness-label invalidation, overview/comparison/chat/export cache writes, worker persistence metadata, writer rejection fail-closed behavior, and roadmap contract alignment.
- `docs/agent-journal/20260426T061322Z.md` records these checks: `python3 -m pytest tests/unit/test_cache_contracts.py tests/unit/test_overview_generation.py tests/unit/test_comparison_generation.py tests/unit/test_chat_generation.py tests/unit/test_exports.py tests/unit/test_source_policy.py -q` passed with 95 tests; `python3 -m pytest tests/unit/test_ingestion_worker.py -q` passed with 20 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 30 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 35 tests; `python3 -m pytest tests -q` passed with 395 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed, including Python tests, static evals, frontend smoke, typecheck, build, and backend checks; `git diff --check` passed.
- Remaining risks from the journal:
  - Generated-output cache persistence remains deterministic and in-memory/mocked only; no production database, object storage, live provider, live LLM, scheduler, or frontend API migration path was activated.
  - Cache records store metadata only and do not store generated prose, raw source text, raw provider payloads, raw user text, prompts, transcripts, or secrets.
  - Golden-path write coverage is limited to existing deterministic AAPL, VOO, QQQ, VOO-vs-QQQ, grounded educational chat, export metadata, source-list metadata, and worker metadata paths.

Completion commits:

- `18af86e feat(T-108): activate generated-output cache writes and freshness invalidation for validated outputs`
- `e2fb8a5 chore(T-108): merge activate generated-output cache writes and freshness invalidation for validated outputs`

### T-107: Persist official-source Weekly News Focus event evidence for golden assets

Goal:
Persist official-source Weekly News Focus event evidence for the golden stock and ETF path while preserving evidence-limited selection, dedupe, source-use gates, and AI Comprehensive Analysis thresholds.

Completed details:

- Implementation commit `e3e1bb2 feat(T-107): persist official-source Weekly News Focus event evidence for golden assets` updated `backend/repositories/weekly_news.py`, `backend/weekly_news_repository.py`, `backend/repositories/__init__.py`, `backend/ingestion_worker.py`, `tests/unit/test_weekly_news.py`, `tests/unit/test_ingestion_worker.py`, `tests/unit/test_repo_contract.py`, and `docs/agent-journal/20260426T060412Z.md`.
- Merged branch `agent/T-107-20260426T060412Z` into `main` with local merge commit `4ad51db chore(T-107): merge persist official-source Weekly News Focus event evidence for golden assets`.
- `backend/repositories/weekly_news.py` added an in-memory Weekly News event evidence repository that validates persisted market-week windows, candidate rows, source-rank inputs, dedupe rows, selected events, evidence states, AI threshold metadata, validation rows, and sanitized diagnostics before records are read or written.
- The repository path preserves evidence-limited Weekly News behavior for fixture-backed golden assets: official-source evidence can be persisted while invalid, wrong-asset, wrong-window, source-policy-blocked, stale-without-label, unavailable, unknown, or otherwise unsafe records are rejected or fall back safely.
- The persisted evidence metadata preserves source-use gates, same-asset citation/source bindings, selected-event counts, suppressed-candidate diagnostics, and AI Comprehensive Analysis threshold metadata without generating or rewriting AI Comprehensive Analysis content.
- `backend/ingestion_worker.py` added an injected mocked Weekly News evidence writer path so the deterministic worker can persist Weekly News evidence metadata through the existing server-side worker/ledger boundary, and fail closed when the configured writer rejects records.
- The implementation preserved fixture fallback, no-live-call defaults, public route schemas, generated-output cache inactivity, and existing AI Comprehensive Analysis content behavior.
- Tests were added for in-memory Weekly News evidence persistence, worker writer integration, writer rejection fail-closed behavior, roadmap contract updates, and no public behavior drift.
- `docs/agent-journal/20260426T060412Z.md` records these checks: `python3 -m pytest tests/unit/test_weekly_news.py tests/unit/test_ingestion_worker.py tests/unit/test_repo_contract.py -q` passed with 52 tests; `python3 -m pytest tests/unit/test_weekly_news.py tests/unit/test_overview_generation.py tests/unit/test_source_policy.py -q` passed with 41 tests; `python3 -m pytest tests/unit/test_ingestion_worker.py -q` passed with 18 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 30 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 35 tests; `python3 -m pytest tests -q` passed with 388 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed, including Python tests, static evals, frontend smoke, typecheck, build, and backend checks; `git diff --check` passed.
- Remaining risks from the journal:
  - Persistence remains deterministic and in-memory/mocked only; no production database, object storage, live source acquisition, scheduler, or provider path was activated.
  - Golden-path coverage remains limited to fixture-backed records exercised by tests.
  - Generated-output cache writes, generated analysis activation from fresh persisted data, frontend API migration, recurring acquisition, and production hardening remain follow-up tasks.

Completion commits:

- `e3e1bb2 feat(T-107): persist official-source Weekly News Focus event evidence for golden assets`
- `4ad51db chore(T-107): merge persist official-source Weekly News Focus event evidence for golden assets`

### T-106: Write normalized knowledge packs from acquisition outputs

Goal:
Write normalized, source-backed knowledge packs from the persisted golden-path acquisition artifacts, then route existing configured readers through those packs with fixture fallback.

Completed details:

- Implementation commit `1cf6dde feat(T-106): write normalized knowledge packs from acquisition outputs` updated `backend/repositories/knowledge_packs.py`, `backend/knowledge_pack_repository.py`, `backend/repositories/__init__.py`, `backend/ingestion_worker.py`, `tests/unit/test_knowledge_pack_repository.py`, `tests/unit/test_retrieval_repository.py`, `tests/unit/test_ingestion_worker.py`, `tests/unit/test_repo_contract.py`, and `docs/agent-journal/20260426T055026Z.md`.
- Merged branch `agent/T-106-20260426T055026Z` into `main` with local merge commit `b6f09d9 chore(T-106): merge write normalized knowledge packs from acquisition outputs`.
- `backend/repositories/knowledge_packs.py` added `InMemoryAssetKnowledgePackRepository` and `knowledge_pack_records_from_acquisition_result` for deterministic acquisition-backed knowledge-pack records.
- The builder converts mocked AAPL SEC and VOO/QQQ ETF issuer acquisition outputs plus T-105 source snapshot records into normalized non-generated pack metadata: source documents, source chunks or allowed excerpts, normalized facts, recent-development rows, evidence gaps, section freshness inputs, source checksums, citation IDs, pack freshness hash metadata, support/build state, and generated-output unavailable/cache-miss flags.
- The implementation validates same-ticker, same provider response asset, same source-document set, same checksum, source-use policy, same-asset facts, citation IDs, source checksums, no-live-call metadata, and sanitized diagnostics before records can be persisted.
- Rights-tier behavior is enforced before chunk/excerpt creation: full-text-allowed and summary-allowed sources can contribute policy-permitted chunks or allowed excerpts, while rejected or source-policy-blocked sources are rejected and cannot create usable knowledge-pack evidence.
- Non-generated acquisition states such as unsupported, out-of-scope, unknown, unavailable, and eligible-not-cached are represented as non-generated knowledge-pack records with explicit unavailable/cache-miss flags rather than generated pages, chat answers, comparisons, risk summaries, or generated-output cache writes.
- `backend/ingestion_worker.py` added an injected mocked `KnowledgePackWriterBoundary`, worker fixture support for `knowledge_pack_records`, ledger metadata for configured knowledge-pack persistence, and fail-closed behavior when a configured mocked writer rejects records.
- Persisted-read coverage proves acquisition-backed records can be read by the existing knowledge-pack reader path while preserving `generated_output_available=False`, `generated_route=None`, and fixture fallback behavior for public routes until generated-output cache activation is handled later.
- Tests were added for AAPL/VOO/QQQ acquisition-backed record creation, in-memory repository persistence/read aliases, summary-allowed excerpt storage, rejected/wrong-checksum blocking, retrieval reader behavior for non-generated acquisition records, worker persistence through an injected writer, writer failure fail-closed behavior, and roadmap contract alignment.
- `docs/agent-journal/20260426T055026Z.md` records these checks: `python3 -m pytest tests/unit/test_knowledge_pack_repository.py tests/unit/test_retrieval_repository.py tests/unit/test_ingestion_worker.py -q` passed with 38 tests; `python3 -m pytest tests/unit/test_knowledge_pack_repository.py tests/unit/test_retrieval_repository.py tests/unit/test_overview_generation.py tests/unit/test_source_policy.py -q` passed with 45 tests; `python3 -m pytest tests/unit/test_ingestion_worker.py -q` passed with 16 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` failed once on a stale T-105 roadmap assertion, then passed after the focused test update with 30 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 35 tests; `python3 -m pytest tests -q` passed with 385 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed, including Python tests, static evals, frontend smoke, typecheck, build, and backend checks; `git diff --check` passed.
- Remaining risks from the journal:
  - Knowledge-pack persistence remains deterministic and in-memory/mocked only; no production database, object storage, live provider, or generated-output cache write path was activated.
  - Acquisition-backed records are normalized evidence metadata with generated-output availability disabled, so overview/details still require generated-output cache activation in a later task before public generated pages can use them.
  - Golden coverage remains limited to AAPL, VOO, and QQQ acquisition outputs.

Completion commits:

- `1cf6dde feat(T-106): write normalized knowledge packs from acquisition outputs`
- `b6f09d9 chore(T-106): merge write normalized knowledge packs from acquisition outputs`

### T-105: Persist source snapshots and parsed acquisition artifacts for the golden path

Goal:
Persist validated source snapshot metadata and parsed acquisition artifacts from the mocked SEC stock and ETF issuer golden paths into the configured private storage/repository boundary, preserving rights-tier source-use rules and fixture fallback.

Completed details:

- Implementation commit `cde7692 feat(T-105): persist source snapshots and parsed acquisition artifacts for the golden path` updated `backend/repositories/source_snapshots.py`, `backend/source_snapshot_repository.py`, `backend/repositories/__init__.py`, `backend/ingestion_worker.py`, `tests/unit/test_source_snapshot_repository.py`, `tests/unit/test_ingestion_worker.py`, `tests/unit/test_repo_contract.py`, and `docs/agent-journal/20260426T053753Z.md`.
- Merged branch `agent/T-105-20260426T053753Z` into `main` with local merge commit `2b42762 chore(T-105): merge persist source snapshots and parsed acquisition artifacts for the golden path`.
- `backend/repositories/source_snapshots.py` added `InMemorySourceSnapshotArtifactRepository` and `source_snapshot_records_from_acquisition_result` for deterministic private source snapshot metadata built from acquisition results.
- The snapshot builder creates artifact metadata for supported AAPL, VOO, and QQQ acquisition outputs with same-asset, same-source-document, deterministic checksum, source-use policy, allowlist, source quality, freshness, permitted operation, evidence-gap, retrieval/as-of, private storage-key, and sanitized diagnostic metadata.
- Rights-tier behavior is enforced before artifact creation: full-text-allowed sources can create raw-source and parsed-text artifact metadata, summary-allowed sources can create summary artifact metadata, metadata-only/link-only sources can create checksum metadata, and rejected sources do not create snapshot artifacts.
- The source snapshot validation now rejects missing source bindings, source-reference mismatches, non-`sha256:` checksums, wrong asset/source bindings, wrong issuer/source metadata, public/signed/frontend-readable storage references, raw provider payload flags, raw source text flags, and secret flags.
- `backend/ingestion_worker.py` added an injected mocked `SourceSnapshotWriterBoundary`, worker fixture support for `source_snapshot_records`, ledger metadata for configured snapshot persistence, and fail-closed behavior when a configured mocked writer rejects records.
- The deterministic worker can persist golden acquisition snapshot records through an in-memory mocked writer without activating generated pages, generated chat answers, comparisons, risk summaries, normalized knowledge-pack writes, generated-output cache writes, live calls, or database/object-storage execution.
- Tests were added for AAPL/VOO/QQQ artifact creation, rights-tier enforcement, rejected/wrong-source/wrong-asset/invalid-checksum blocking, sanitized diagnostics, no public or signed storage references, in-memory repository persistence, worker persistence through an injected writer, and writer failure fail-closed behavior.
- `docs/agent-journal/20260426T053753Z.md` records these checks: `python3 -m pytest tests/unit/test_source_snapshot_repository.py tests/unit/test_provider_adapters.py tests/unit/test_ingestion_worker.py tests/unit/test_source_policy.py -q` passed with 55 tests; `python3 -m pytest tests/unit/test_ingestion_jobs.py -q` passed with 16 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 30 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 35 tests; `python3 -m pytest tests -q` passed with 378 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed, including Python tests, static evals, frontend smoke, typecheck, build, and backend checks; `git diff --check` passed.
- Remaining risks from the journal:
  - Persistence remains deterministic and in-memory/mocked only; no production object storage, database session, live SEC/issuer fetching, or signed/public storage URL path was added.
  - Snapshot records reference raw and parsed artifact metadata only; no raw source text, provider payloads, normalized knowledge-pack rows, generated-output cache records, generated pages, generated chat answers, comparisons, or risk summaries are written.
  - Golden coverage is limited to AAPL, VOO, and QQQ acquisition outputs. Eligible-but-not-golden, unsupported, unknown, wrong-source, wrong-asset, invalid-checksum, rejected-source, and writer-failure paths are blocked or diagnosed without generated output.

Completion commits:

- `cde7692 feat(T-105): persist source snapshots and parsed acquisition artifacts for the golden path`
- `2b42762 chore(T-105): merge persist source snapshots and parsed acquisition artifacts for the golden path`

### T-104: Implement official ETF issuer acquisition for the ETF golden path

Goal:
Implement the first server-side official ETF issuer acquisition path for golden ETFs such as VOO and QQQ, using mocked issuer fixtures in tests and preserving source-use restrictions.

Completed details:

- Implementation commit `209c558 feat(T-104): implement official ETF issuer acquisition for the ETF golden path` updated `backend/provider_adapters/etf_issuer.py`, `tests/unit/test_provider_adapters.py`, `tests/unit/test_ingestion_worker.py`, `tests/unit/test_repo_contract.py`, and `docs/agent-journal/20260426T052954Z.md`.
- Merged branch `agent/T-104-20260426T052954Z` into `main` with local merge commit `55190bd chore(T-104): merge official ETF issuer acquisition for the ETF golden path`.
- `backend/provider_adapters/etf_issuer.py` added backend-only `etf-issuer-acquisition-boundary-v1` metadata for mocked official ETF issuer acquisition.
- The acquisition result normalizes VOO and QQQ issuer fixture evidence with issuer readiness, source-use policy metadata, deterministic checksums, freshness/as-of metadata, evidence-gap diagnostics, and no generated-output activation.
- The implementation added blocked or labeled acquisition states for wrong asset type, eligible-but-not-golden ETF inputs, unsupported ETF classes, out-of-scope assets, unknown assets, fixture validation failures, and source-policy-blocked sources.
- The deterministic ingestion worker fixture outcome now exercises ETF acquisition checksum/source-policy metadata without enabling source snapshot writes, knowledge-pack writes, generated-output cache writes, generated pages, generated chat answers, generated comparisons, or generated risk summaries.
- Tests were added in `tests/unit/test_provider_adapters.py` and `tests/unit/test_ingestion_worker.py`; `tests/unit/test_repo_contract.py` was updated during the branch to reflect the roadmap task state at that point.
- `docs/agent-journal/20260426T052954Z.md` records these checks: `python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_source_policy.py tests/unit/test_ingestion_worker.py tests/unit/test_ingestion_jobs.py -q` passed with 52 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 30 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 35 tests; `python3 -m pytest tests -q` passed with 371 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed, including Python tests, static evals, frontend smoke, typecheck, build, and backend checks; `git diff --check` passed.
- Remaining risks from the journal:
  - ETF issuer acquisition remains fixture-backed for VOO and QQQ only; SPY is labeled eligible-but-not-golden because no deterministic acquisition fixture was added.
  - No live issuer fetching, source snapshot persistence, normalized knowledge-pack persistence, generated-output cache writes, public route behavior changes, frontend rendering changes, scheduling, rate limiting, paid provider integration, or deployment wiring was added.
  - Future source persistence and live readiness work must preserve same-ticker, same-issuer, same-source-document binding, source-use gates, sanitized diagnostics, no-live-call defaults, and no generated-output activation until later validation gates are implemented.

Completion commits:

- `209c558 feat(T-104): implement official ETF issuer acquisition for the ETF golden path`
- `55190bd chore(T-104): merge official ETF issuer acquisition for the ETF golden path`

### T-103: Implement server-side SEC EDGAR acquisition for the stock golden path

Goal:
Implement the first server-side SEC EDGAR stock acquisition path for a small golden stock set, using mocked HTTP fixtures in tests and preserving no live external calls in normal CI.

Completed details:

- Implementation commit `feb69c6 feat(T-103): implement server-side SEC EDGAR acquisition for the stock golden path` updated `backend/provider_adapters/sec_stock.py`, `tests/unit/test_provider_adapters.py`, `tests/unit/test_ingestion_worker.py`, `tests/unit/test_repo_contract.py`, and `docs/agent-journal/20260426T045949Z.md`.
- Merged branch `agent/T-103-20260426T045949Z` into `main` with local merge commit `347a7c7 chore(T-103): merge server-side SEC EDGAR acquisition for the stock golden path`.
- `backend/provider_adapters/sec_stock.py` added a backend-only `sec-stock-acquisition-boundary-v1` result for the SEC stock golden path.
- The acquisition result normalizes the existing AAPL SEC fixture provider response with explicit configuration-readiness metadata, deterministic source checksums, source-use policy metadata, freshness/as-of metadata, evidence-gap states, and sanitized diagnostics.
- Unsupported, wrong-asset-type, out-of-scope, eligible-but-not-golden, unknown, source-policy-blocked, wrong-CIK, and wrong-source-binding cases are blocked without generated outputs.
- The existing deterministic worker outcome path now exercises SEC acquisition checksum/source-policy metadata without enabling generated pages, chat answers, comparisons, risk summaries, source snapshot writes, knowledge-pack writes, generated-output cache writes, live calls, or database connections.
- `tests/unit/test_provider_adapters.py` and `tests/unit/test_ingestion_worker.py` added coverage for the mocked SEC acquisition path and worker exercise behavior. `tests/unit/test_repo_contract.py` was updated during the branch to reflect T-103 as the current roadmap task after T-102 completion.
- `docs/agent-journal/20260426T045949Z.md` records these checks: `python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_source_policy.py tests/unit/test_ingestion_worker.py tests/unit/test_ingestion_jobs.py -q` passed with 48 tests; `python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_source_policy.py tests/unit/test_ingestion_worker.py tests/unit/test_ingestion_jobs.py tests/unit/test_repo_contract.py -q` passed with 63 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 29 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 35 tests; `python3 -m pytest tests -q` passed with 366 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed, including Python tests, static evals, frontend smoke, typecheck, build, and backend checks; `git diff --check` passed.
- Remaining risks from the journal:
  - This is still fixture-backed and limited to the AAPL SEC golden path; it does not perform live SEC fetching.
  - No source snapshots, normalized knowledge-pack persistence, generated-output cache writes, public route wiring, frontend rendering, production scheduling, rate limiting, or deployment wiring were added.
  - Future live SEC readiness work must preserve the explicit no-live-call default, sanitized diagnostics, same-ticker/same-CIK binding, source-use gates, and no generated-output activation until persistence and validation gates are added.

Completion commits:

- `feb69c6 feat(T-103): implement server-side SEC EDGAR acquisition for the stock golden path`
- `347a7c7 chore(T-103): merge server-side SEC EDGAR acquisition for the stock golden path`

### T-102: Make ingestion jobs executable through the local ledger

Goal:
Make manual pre-cache and on-demand ingestion jobs executable through the existing ingestion job ledger and worker boundary using mocked acquisition outcomes, so local runtime job state transitions can be exercised without live provider calls.

Completed details:

- Implementation commit `e3652a0 feat(T-102): make ingestion jobs executable through the local ledger` updated `backend/ingestion.py`, `backend/main.py`, `backend/persistence.py`, `tests/unit/test_ingestion_jobs.py`, `tests/unit/test_ingestion_worker.py`, `tests/unit/test_repo_contract.py`, `tests/integration/test_backend_api.py`, and `docs/agent-journal/20260426T044844Z.md`.
- Merged branch `agent/T-102-20260426T044844Z` into `main` with local merge commit `3fa8d40 chore(T-102): merge make ingestion jobs executable through the local ledger`.
- `backend/persistence.py` added `ingestion_job_ledger` to the app-level `BackendReadDependencies` boundary, active-reader calculation, and safe diagnostics without opening a database connection at import time.
- `backend/main.py` now passes the configured ingestion job ledger, when explicitly enabled, into admin ingestion creation, ingestion job status lookup, launch-universe pre-cache creation/status, individual pre-cache job status, and individual pre-cache creation routes.
- `backend/ingestion.py` now lets eligible on-demand and pre-cache job creation/status read and save configured ledger records, with fixture fallback when the configured ledger is absent, fails, misses, returns invalid records, or returns records for the wrong ticker/job.
- `backend/ingestion.py` added `execute_ingestion_job_through_ledger`, which runs the deterministic worker against a configured ledger when provided and falls back to serialized fixture records otherwise.
- Ledger-backed response shaping maps ledger records back into existing public ingestion/pre-cache response models, including sanitized diagnostics, generated-output capability flags, status URLs, timestamps, and terminal state handling. Stale ledger terminal states remain internal and surface through the existing public `refresh_needed` enum to avoid a public schema change.
- Successful mocked execution remains non-generative for newly executable jobs: it does not create generated pages, generated chat answers, generated comparisons, generated risk summaries, source snapshots, normalized knowledge packs, source chunks, or generated-output cache writes.
- Tests added coverage for ledger-backed on-demand creation/status/execution, ledger-backed pre-cache creation/status/execution, configured-ledger failure fallback, invalid or wrong-ticker ledger fallback, server-side execution helper configured/fallback behavior, and route-level ledger wiring with fixture fallback.
- `docs/agent-journal/20260426T044844Z.md` records these checks: `python3 -m pytest tests/unit/test_ingestion_job_repository.py tests/unit/test_ingestion_worker.py tests/unit/test_ingestion_jobs.py -q` passed with 38 tests; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 28 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 35 tests; `python3 -m pytest tests -q` passed with 362 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `docker compose config` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - This only wires the configured in-memory/mocked ingestion ledger path; it does not add live source acquisition, source snapshots, normalized knowledge-pack writes, generated-output cache writes, production scheduling, admin auth, rate limiting, or deployment hardening.
  - Stale ledger terminal states are preserved internally by the worker; existing public ingestion response enums still surface them through the existing `refresh_needed` state to avoid a public schema change.
  - Future T-103/T-104 acquisition work must preserve the same fixture fallback, sanitized diagnostics, no-live-call defaults, terminal-state idempotency, and no generated-output activation until validated source persistence and generation gates are added.

Completion commits:

- `e3652a0 feat(T-102): make ingestion jobs executable through the local ledger`
- `3fa8d40 chore(T-102): merge make ingestion jobs executable through the local ledger`

### T-101: Wire backend routes to configured persistence readers with fixture fallback

Goal:
Wire public backend read paths to configured persistent repository readers and existing injected boundaries when persistence is explicitly configured, while preserving deterministic fixture fallback and current route schemas when it is not.

Completed details:

- Implementation commit `1d9d664 feat(T-101): wire backend routes to configured persistence readers with fixture fallback` updated `backend/persistence.py`, `backend/main.py`, `backend/export.py`, `backend/chat_sessions.py`, `backend/sources.py`, `backend/compat.py`, `tests/integration/test_backend_api.py`, `tests/unit/test_repo_contract.py`, and `docs/agent-journal/20260426T043838Z.md`.
- Merged branch `agent/T-101-20260426T043838Z` into `main` with local merge commit `11b9785 chore(T-101): merge wire backend routes to configured persistence readers with fixture fallback`.
- `backend/persistence.py` added the `BackendReadDependencies` app-state boundary, default disabled dependencies, safe diagnostics, and helpers to configure or read app-level dependencies without opening a database connection at import time.
- `backend/main.py` now passes configured readers into overview, recent context, Weekly News Focus, comparison, knowledge-pack, source drawer, asset export, comparison export, grounded chat, chat-session status/delete/export, and chat export routes when persisted reads are explicitly enabled.
- `backend/main.py` added a configured-reader details path that builds a `DetailsResponse` from validated persisted knowledge-pack records when available, otherwise preserving deterministic fixture fallback.
- `backend/export.py`, `backend/chat_sessions.py`, and `backend/sources.py` now accept configured persisted pack/cache, Weekly News, and chat-session reader/writer dependencies while preserving existing fallback behavior and source-use/export validation.
- `backend/compat.py` was adjusted for compatibility support needed by the route wiring tests.
- `tests/integration/test_backend_api.py` added a `RouteReaderSpy` integration test proving configured route wiring for overview, Weekly News Focus, details, sources, knowledge pack, comparison, asset export, comparison export, chat, chat-session status, and chat export while preserving fixture fallback responses.
- `tests/unit/test_repo_contract.py` was updated so the runtime roadmap recognized T-101 as current after T-100 completion during that task branch.
- The implementation did not add live database sessions, source acquisition, source snapshot writes, normalized knowledge-pack writes, generated-output cache writes, frontend migration, live provider calls, or deployment hardening.
- `docs/agent-journal/20260426T043838Z.md` records these checks: `python3 -m pytest tests/unit/test_overview_generation.py tests/unit/test_weekly_news.py tests/unit/test_comparison_generation.py tests/unit/test_chat_generation.py tests/unit/test_chat_sessions.py tests/unit/test_exports.py -q` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - This wires configured reader boundaries only; it does not add live database sessions, source acquisition, generated-output cache writes, source snapshot writes, frontend migration, or deployment hardening.
  - Source drawer and export paths still preserve deterministic fixture fallback when configured persisted readers miss, fail, or are absent.
  - Future production reader wiring must preserve the same no-import-time-connection behavior, same-asset/comparison-pack citation binding, source-use gates, chat transcript metadata-only behavior, and no-live-call defaults.

Completion commits:

- `1d9d664 feat(T-101): wire backend routes to configured persistence readers with fixture fallback`
- `11b9785 chore(T-101): merge wire backend routes to configured persistence readers with fixture fallback`

### T-100: Rebaseline backend MVP runtime gap audit and roadmap tracker

Goal:
Add a deterministic backend MVP runtime gap audit and roadmap tracker that separates completed deterministic contracts from the remaining fresh-data runtime path needed to ingest official sources, persist knowledge packs, generate/cache validated outputs, and render them through the frontend.

Completed details:

- Implementation commit `8b341fd feat(T-100): rebaseline backend MVP runtime gap audit and roadmap tracker` added `docs/backend_mvp_runtime_gap_audit.md` and `docs/agent-journal/20260426T042922Z.md`, updated `TASKS.md`, and expanded `tests/unit/test_repo_contract.py` and `tests/unit/test_safety_guardrails.py`.
- Merged branch `agent/T-100-20260426T042922Z` into `main` with local merge commit `8f6bca5 chore(T-100): merge rebaseline backend MVP runtime gap audit and roadmap tracker`.
- `docs/backend_mvp_runtime_gap_audit.md` added the T-100 audit artifact with PRD/TDS authority after safety rules, Frontend Design and Workflow v0.4 baseline markers, status vocabulary for `contract_complete`, `runtime_gap`, `current`, `backlog`, and `later`, a runtime gap summary, an area tracker, fresh-data MVP blockers, non-goals, and guardrails to preserve.
- The audit covers source acquisition, provider adapters, source snapshot storage, normalized knowledge-pack persistence, configured route read-path wiring, generated-output cache writes, Weekly News Focus acquisition, ingestion job execution, frontend API rendering, launch-universe pre-cache, exports/source-use enforcement, live-generation readiness, trust metrics, and production hardening.
- The audit explicitly records that public routes still default to fixtures where configured readers are absent, ingestion jobs do not fetch real official sources, persistence is not the normal read/write path, provider adapters are fixture-backed, generated-output cache writes are not activated for public output, and frontend asset/search pages still have local-fixture-first behavior for parts of the workflow.
- The audit maps the next narrow runtime tasks to T-101 route read-path wiring, T-102 executable ingestion jobs, T-103 SEC golden-path acquisition, and T-104 ETF issuer golden-path acquisition, while keeping live providers, paid providers, broad ingestion, and deployment hardening later.
- `TASKS.md` was corrected in the T-100 branch to mark T-099 complete, mark T-100 current at that time, and align the backend roadmap tracker with the fresh-data MVP runtime gap sequence.
- `tests/unit/test_repo_contract.py` added coverage for audit shape, required status vocabulary, required gap coverage, v0.4 workflow markers, next-task mapping, and absence of live-network, secret, signed/public storage URL, or import-time environment markers in the audit.
- `tests/unit/test_safety_guardrails.py` added coverage that the audit copy remains advice-safe and sanitized.
- `docs/agent-journal/20260426T042922Z.md` records these checks: `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed after one focused wording fix; `npm test` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `docker compose config` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - This is a planning and validation artifact only; no runtime fresh-data path was wired.
  - Public routes still default to fixtures where configured readers are absent.
  - Ingestion jobs still do not fetch official sources or persist normalized knowledge packs.
  - Generated-output cache writes remain inactive for public output.
  - Frontend search and asset pages still have local-fixture-first behavior for parts of the workflow.

Completion commits:

- `8b341fd feat(T-100): rebaseline backend MVP runtime gap audit and roadmap tracker`
- `8f6bca5 chore(T-100): merge rebaseline backend MVP runtime gap audit and roadmap tracker`

### T-099: Add provider content export-rights hardening contract

Goal:
Add deterministic provider-content export-rights hardening so exports, caches, generated-output eligibility, and diagnostics consistently enforce `metadata_only`, `link_only`, `summary_allowed`, `full_text_allowed`, and `rejected` tiers for provider and source-derived content.

Completed details:

- Implementation commit `bba6f8b feat(T-099): add provider content export-rights hardening contract` updated `backend/source_policy.py`, `backend/export.py`, `backend/cache.py`, `tests/unit/test_source_policy.py`, `tests/unit/test_exports.py`, `tests/unit/test_cache_contracts.py`, and `docs/agent-journal/20260426T041918Z.md`.
- Merged branch `agent/T-099-20260426T041918Z` into `main` with local merge commit `6c61062 chore(T-099): merge provider content export-rights hardening contract`.
- `backend/source_policy.py` added deterministic source-use action classification for generated-claim support, cache input/checksum use, generated-output cache eligibility, source-list metadata export, allowed excerpt export, Markdown/JSON section export, and sanitized diagnostics.
- `backend/cache.py` tightened generated-output cache metadata so restricted `metadata_only`, `link_only`, rejected, or not-allowed source checksum inputs cannot make generated outputs cacheable.
- `backend/export.py` hardened export source shaping so rejected and not-allowlisted sources are suppressed, metadata-only and link-only sources export metadata-limited entries without passages, and export validation records restricted-content messages.
- Existing persisted chat-session metadata-only export behavior was preserved while restricted passages remain omitted.
- Tests in `tests/unit/test_source_policy.py`, `tests/unit/test_exports.py`, and `tests/unit/test_cache_contracts.py` cover the action-level rights checks, restricted-source cache eligibility blocking, source-list export suppression, metadata-only/link-only omission behavior, and restricted-content validation messages.
- The implementation did not add live provider calls, legal/licensing review, source acquisition, persistence writes, frontend workflow changes, public route behavior changes, or deployment work.
- `docs/agent-journal/20260426T041918Z.md` records these checks: `python3 -m pytest tests/unit/test_source_policy.py tests/unit/test_exports.py tests/unit/test_cache_contracts.py tests/unit/test_provider_adapters.py -q` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - This is deterministic contract hardening only; no live provider, legal/licensing review, source acquisition, persistence writes, or frontend workflow changes were added.
  - Future provider or source-ingestion wiring must preserve these action-level rights checks before allowing restricted source material into generated claims, cacheable outputs, exports, or diagnostics.

Completion commits:

- `bba6f8b feat(T-099): add provider content export-rights hardening contract`
- `6c61062 chore(T-099): merge provider content export-rights hardening contract`

### T-098: Add live-generation validation and fallback orchestration contract

Goal:
Add a deterministic live-generation orchestration contract that can validate mocked provider outputs through schema, citation, source-policy, freshness, and safety gates, perform one repair retry, and represent paid fallback metadata without routing public outputs through live generation.

Completed details:

- Implementation commit `4d9b517 feat(T-098): add live-generation validation and fallback orchestration contract` updated `backend/llm.py`, `backend/models.py`, `tests/unit/test_llm_provider.py`, and `docs/agent-journal/20260426T034633Z.md`.
- Merged branch `agent/T-098-20260426T034633Z` into `main` with local merge commit `3abb3d6 chore(T-098): merge live-generation validation and fallback orchestration contract`.
- `backend/llm.py` extended `validate_llm_generated_output` to validate freshness-label state, unsupported-claim codes, and Weekly News Focus analysis evidence rules in addition to schema, citation/source-policy, safety, hidden-prompt, raw-reasoning, and unrestricted-source-text gates.
- `backend/llm.py` added `run_mocked_live_generation_orchestration`, a dormant backend-only `llm-live-orchestration-contract-v1` boundary that calls the T-097 injected OpenRouter transport only when runtime readiness is explicit, the caller opts in, and a mocked transport is supplied.
- The orchestration contract records sanitized attempt metadata, validates mocked transport content, models one repair retry, preserves paid DeepSeek fallback metadata when validation still fails after repair, and returns generated-content usability, public metadata, cache eligibility, and compact rejection diagnostics without exposing raw generated text.
- Cache eligibility now remains conservative for invalid, suppressed, missing-input-hash, non-success, and repair-attempt outputs; the journal notes that repair success is usable in contract metadata but is not cache-eligible.
- Weekly News Focus analysis artifacts are validated against the two-selected-item threshold and canonical-fact citation availability before being marked usable.
- `backend/models.py` added blocked/not-validated/freshness/unsupported-claim/Weekly-News validation statuses and added `generated_content_usable` plus sanitized diagnostics to `LlmOrchestrationResult`.
- Tests in `tests/unit/test_llm_provider.py` cover active mocked orchestration, inactive states without readiness/opt-in/transport, one repair retry success, validation failure after repair with paid fallback metadata, wrong-asset and rejected-source citations, stale-without-label, freshness failure, unsupported claims, safety failure, hidden prompt, raw reasoning, unrestricted source text, Weekly News Focus threshold enforcement, cache eligibility blocking, and sanitized diagnostics that exclude raw mocked output.
- The implementation did not add public route integration, live provider execution, frontend exposure, generated-output cache writes, prompt rewrites, production secret setup, or public generated-output behavior changes.
- `docs/agent-journal/20260426T034633Z.md` records these checks: `python3 -m pytest tests/unit/test_llm_provider.py -q` passed; `python3 -m pytest tests/unit/test_llm_provider.py tests/unit/test_overview_generation.py tests/unit/test_comparison_generation.py tests/unit/test_chat_generation.py tests/unit/test_safety_guardrails.py -q` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - The orchestration path is dormant and backend-only; no public route integration, live provider execution, frontend exposure, or generated-output cache write was added.
  - Repair success is validated and usable in contract metadata, but cache eligibility remains conservative for repair-attempt output.
  - Future live wiring must preserve explicit readiness and caller opt-in gates, sanitized diagnostics, citation/source-use/freshness/safety validation, Weekly News Focus analysis thresholds, and fallback-as-metadata behavior before any public output can consume it.

Completion commits:

- `4d9b517 feat(T-098): add live-generation validation and fallback orchestration contract`
- `3abb3d6 chore(T-098): merge live-generation validation and fallback orchestration contract`

### T-097: Add gated OpenRouter transport adapter with mocked tests

Goal:
Add an OpenRouter-compatible live-provider transport adapter behind explicit server-side feature flags and injectable mocked transports, preserving deterministic mock behavior and making no live calls in normal CI.

Completed details:

- Implementation commit `57c4b6e test(T-097): add gated OpenRouter transport adapter with mocked tests` added `backend/llm_transport.py` and `docs/agent-journal/20260426T033549Z.md`, and updated `backend/models.py`, `tests/unit/test_llm_provider.py`, and `tests/unit/test_repo_contract.py`.
- Merged branch `agent/T-097-20260426T033549Z` into `main` with local merge commit `f634a14 chore(T-097): merge gated OpenRouter transport adapter with mocked tests`.
- `backend/llm_transport.py` added the dormant `llm-transport-contract-v1` OpenRouter transport boundary with `call_openrouter_transport`, `build_openrouter_transport_request`, `TransportCallable`, `OPENROUTER_CHAT_COMPLETIONS_PATH`, and a default 30-second timeout metadata value.
- The transport boundary never imports a network client, never reads process configuration, and can execute only through an explicitly injected callable, keeping normal local and CI behavior deterministic.
- Transport gating blocks non-OpenRouter providers, disabled live generation, missing server-side key state, missing OpenRouter base URL, missing model chain, incomplete endpoint configuration, validation-not-ready state, readiness states other than `ready_for_explicit_live_call`, missing caller opt-in, and missing injected transport.
- Request metadata preserves schema-mode or JSON-mode intent, configured free-model chain metadata from T-096, paid fallback metadata, base URL/model-chain/endpoint configured booleans, validation retry count, reasoning-summary-only state, timeout/retryability metadata, and sanitized diagnostics.
- Response handling maps mocked provider success into compact metadata with model name, model tier, provider status, finish reason, token usage, cost, latency, request mode, and sanitized diagnostics while returning content only as the direct transport result.
- Mocked failures are classified as timeout, retryable provider error, nonretryable provider error, invalid response shape, missing content, or blocked, with compact diagnostic codes and without surfacing raw exception text.
- `backend/models.py` added `LlmTransportMode`, `LlmTransportStatus`, `LlmTransportRetryability`, `LlmTransportRequestMetadata`, `LlmTransportResponseMetadata`, and `LlmTransportResult`.
- Tests cover disabled/missing-key/missing-endpoint/missing-model-chain/validation-not-ready/no-opt-in/missing-injected-transport blocking, mocked schema-mode success, mocked JSON-mode and paid-model metadata, retryable/nonretryable provider failures, invalid shape, missing content, timeout handling, diagnostic redaction, no raw reasoning exposure, no live network client import, no browser env exposure, and deterministic mock defaults.
- The implementation did not add live OpenRouter calls, route-level live-generation integration, generated-output cache writes, frontend exposure, production secret wiring, prompt rewrites, provider licensing changes, or public generated-output behavior changes.
- `docs/agent-journal/20260426T033549Z.md` records these checks: `python3 -m pytest tests/unit/test_llm_provider.py tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - The OpenRouter transport is a backend-only dormant contract with injected mocked transports only; no live network client, public route integration, generated-output cache write, frontend exposure, or production secret wiring was added.
  - Future live-generation orchestration must preserve the same readiness gates, explicit opt-in requirement, sanitized diagnostics, no raw reasoning exposure, citation/source-use validation, freshness/uncertainty labels, and safety checks before any generated output is used or cached.

Completion commits:

- `57c4b6e test(T-097): add gated OpenRouter transport adapter with mocked tests`
- `f634a14 chore(T-097): merge gated OpenRouter transport adapter with mocked tests`

### T-096: Add live LLM runtime readiness diagnostics contract

Goal:
Add a server-side live LLM runtime readiness diagnostics contract for the OpenRouter-first deployment model chain, feature flags, sanitized configuration state, validation requirements, and disabled-by-default behavior without making live model calls or exposing secrets.

Completed details:

- Implementation commit `0f41586 feat(T-096): add live LLM runtime readiness diagnostics contract` updated `backend/llm.py`, `backend/models.py`, `tests/unit/test_llm_provider.py`, `tests/integration/test_backend_api.py`, and `docs/agent-journal/20260426T032750Z.md`.
- Merged branch `agent/T-096-20260426T032750Z` into `main` with local merge commit `aaaf430 chore(T-096): merge live LLM runtime readiness diagnostics contract`.
- `backend/models.py` added `LlmReadinessStatus` with `disabled_by_default`, `unavailable`, `validation_not_ready`, and `ready_for_explicit_live_call`, and expanded `LlmRuntimeConfig` with readiness status, base URL configured state, model-chain configured state, validation readiness, validation gates, and `no_live_call_status`.
- `backend/llm.py` added `LLM_VALIDATION_GATE_CODES`, readiness-status calculation, base URL/model-chain/paid-fallback configuration booleans, validation readiness checks, and compact unavailable reason codes for missing base URL, missing free model order, missing paid fallback model, validation retry count below minimum, and disabled reasoning-summary-only behavior.
- The default mock runtime remains disabled by default with deterministic mock provider metadata, `live_network_calls_allowed=False`, `no_live_call_status="no_live_calls_attempted"`, validation retry count `1`, reasoning-summary-only enabled, and validation gate metadata present.
- The OpenRouter readiness path now distinguishes disabled-by-default, missing-key or missing-endpoint unavailable states, validation-not-ready states, and ready-for-explicit-live-call states while preserving the configured free-model chain and paid fallback metadata.
- Integration diagnostics coverage was tightened so the LLM runtime diagnostics response exposes sanitized readiness fields without exposing credentials, private prompt fields, model reasoning payloads, or live-call behavior.
- Tests were expanded for deterministic mock defaults, OpenRouter flag/key/endpoint gating, model-chain order and tier metadata, paid fallback order metadata, missing base URL, missing free model order, missing paid fallback model, validation-not-ready handling, validation gate codes, no-live-call status, and sanitized runtime diagnostics.
- The implementation did not add live OpenRouter transport, model invocation, route-level live generation, prompt rewrites, generated-output cache writes, provider secret wiring, frontend exposure, external provider calls, or generated-output behavior changes.
- `docs/agent-journal/20260426T032750Z.md` records these checks: `python3 -m pytest tests/unit/test_llm_provider.py -q` passed; `python3 -m pytest tests/unit/test_llm_provider.py tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - This is a readiness and diagnostics contract only; no live OpenRouter transport, model invocation, route-level live generation, prompt rewrite, cache write, provider secret wiring, or frontend exposure was added.
  - Future live-generation work must preserve the same readiness status codes, validation gates, no-live-call defaults, secret redaction, citation/source binding, source-use, freshness/uncertainty, and safety requirements before any generated output can be cacheable.

Completion commits:

- `0f41586 feat(T-096): add live LLM runtime readiness diagnostics contract`
- `aaaf430 chore(T-096): merge live LLM runtime readiness diagnostics contract`

### T-095: Route Weekly News Focus through persisted event evidence fallback

Goal:
Route Weekly News Focus and AI Comprehensive Analysis threshold reads through injected persisted recent-event evidence boundaries first, while preserving deterministic fixture fallback, stable/timely context separation, source-use policy, empty/limited states, and current API/frontend behavior.

Completed details:

- Implementation commit `ac16b34 feat(T-095): route Weekly News Focus through persisted event evidence fallback` updated `backend/weekly_news.py`, `backend/overview.py`, `tests/unit/test_weekly_news.py`, `tests/unit/test_overview_generation.py`, and `docs/agent-journal/20260426T031547Z.md`.
- Merged branch `agent/T-095-20260426T031547Z` into `main` with local merge commit `6db2302 chore(T-095): merge route Weekly News Focus through persisted event evidence fallback`.
- `backend/weekly_news.py` added `WEEKLY_NEWS_PERSISTED_READ_BOUNDARY`, `WeeklyNewsEventEvidenceRecordReader`, `PersistedWeeklyNewsReadResult`, and `read_persisted_weekly_news_focus` to validate injected persisted Weekly News Focus event evidence records before using them.
- Valid same-asset persisted records are mapped into the existing `WeeklyNewsFocusResponse` schema with event type, period bucket, citation/source references, event or published dates where available, retrieved timestamp, source quality, source-use tier, freshness state, selected-vs-configured counts, suppressed candidate counts, and empty/limited state metadata.
- The read path preserves deterministic fixture fallback when no reader is injected, a reader misses, a reader fails, records fail validation, no matching same-asset window exists, or AI threshold metadata is disconnected from selected events.
- Persisted event display text is metadata-derived because the repository contract intentionally avoids raw article text and unrestricted source passages.
- `backend/overview.py` routes overview generation through the injected Weekly News reader only when explicitly supplied and reads validated AI threshold metadata so persisted selected items with fewer than two approved Weekly News Focus events suppress AI Comprehensive Analysis instead of inventing analysis.
- Tests were expanded for persisted-first Weekly News reads, fallback on miss/failure/invalid/wrong-asset records, empty and limited states without padding, disconnected threshold rejection, sanitized diagnostics, source-use tiers, overview integration with injected Weekly News records, and AI Comprehensive Analysis threshold availability/suppression.
- The implementation did not add live database execution, provider calls, cache writes, acquisition worker scheduling, source allowlist changes, frontend changes, generated-output cache integration, or public route behavior changes.
- `docs/agent-journal/20260426T031547Z.md` records these checks: `python3 -m pytest tests/unit/test_weekly_news.py -q` passed; `python3 -m pytest tests/unit/test_overview_generation.py -q` passed; `python3 -m pytest tests/unit/test_weekly_news.py tests/unit/test_overview_generation.py tests/unit/test_source_policy.py -q` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - The persisted Weekly News reader is injectable and dormant only; no live database, provider, cache write, acquisition worker, scheduler, source allowlist change, frontend change, or generated-output cache integration was added.
  - Future production reader wiring must preserve the same same-asset, source-use, freshness, dedupe, empty/limited-state, AI-threshold, and sanitized-diagnostic fallback gates.

Completion commits:

- `ac16b34 feat(T-095): route Weekly News Focus through persisted event evidence fallback`
- `6db2302 chore(T-095): merge route Weekly News Focus through persisted event evidence fallback`

### T-094: Add deterministic Weekly News Focus acquisition worker contract

Goal:
Add a deterministic fixture-backed Weekly News Focus acquisition worker contract that can consume persisted recent-event evidence boundaries, apply windowing, dedupe, source ranking, and empty/limited-state selection without live news/provider calls or generated analysis changes.

Completed details:

- Implementation commit `bb2686a feat(T-094): add deterministic Weekly News Focus acquisition worker contract` updated `backend/repositories/weekly_news.py`, `backend/weekly_news_repository.py`, `tests/unit/test_weekly_news.py`, and `docs/agent-journal/20260426T030431Z.md`.
- Merged branch `agent/T-094-20260426T030431Z` into `main` with local merge commit `d748752 chore(T-094): merge deterministic Weekly News Focus acquisition worker contract`.
- `backend/repositories/weekly_news.py` added `WEEKLY_NEWS_FIXTURE_ACQUISITION_BOUNDARY`, `WeeklyNewsFixtureAcquisitionBoundary`, and `acquire_weekly_news_event_evidence_from_fixtures` to transform local `WeeklyNewsEventCandidateRow` records into validated `WeeklyNewsEventEvidenceRepositoryRecords`.
- The fixture acquisition path builds deterministic U.S. Eastern market-week windows, prepares candidate rows, computes source rank inputs, applies source-use policy gates, groups dedupe metadata, selects ranked events up to the configured maximum, records selected-vs-configured and suppressed candidate counts, and emits evidence-state, AI threshold, validation, and sanitized diagnostic rows.
- The selection logic skips wrong-asset candidates, suppresses blocked, stale/unavailable-without-label, non-allowlisted, policy-disallowed, promotional, irrelevant, duplicate, out-of-window, and below-score candidates, and preserves compact suppression metadata without raw article bodies or unrestricted source text.
- AI Comprehensive Analysis threshold metadata remains metadata-only and enforces the two high-signal selected-item rule without changing generated AI analysis output.
- `backend/weekly_news_repository.py` re-exports the new acquisition boundary and helper alongside the T-093 repository row models and validators.
- Tests were expanded for ranked and deduped fixture acquisition, wrong-asset skipping, selected-vs-configured counts, suppressed candidate counts, empty and limited states, AI threshold availability/suppression metadata, source-use blocking, freshness/uncertainty labels, sanitized diagnostics, no advice language, no secret exposure, and no live network/provider/database/LLM imports.
- The implementation did not change public routes, generated Weekly News Focus output, generated AI Comprehensive Analysis output, frontend behavior, live provider wiring, source allowlists, route-level persisted-read fallback, generated-output caches, database execution, worker scheduling, or deployment wiring.
- `docs/agent-journal/20260426T030431Z.md` records these checks: `python3 -m pytest tests/unit/test_weekly_news.py -q` passed; `python3 -m pytest tests/unit/test_weekly_news.py tests/unit/test_overview_generation.py tests/unit/test_source_policy.py -q` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - The acquisition boundary is still dormant and fixture-only; no live worker, database execution, route-level persisted-read fallback, provider fetch, cache write, or scheduler wiring was added.
  - Future route integration must preserve same-asset citation/source binding, source-use policy gates, freshness/uncertainty labels, dedupe suppression metadata, empty/limited states, and AI analysis threshold suppression before generated output consumes persisted events.

Completion commits:

- `bb2686a feat(T-094): add deterministic Weekly News Focus acquisition worker contract`
- `d748752 chore(T-094): merge deterministic Weekly News Focus acquisition worker contract`

### T-093: Add persisted Weekly News Focus event evidence contracts

Goal:
Add dormant persisted recent-event evidence contracts for Weekly News Focus items, candidate scoring diagnostics, source ranking, dedupe metadata, market-week windows, empty/limited states, and AI Comprehensive Analysis threshold inputs without live news/provider acquisition or generated analysis changes.

Completed details:

- Implementation commit `67a948e feat(T-093): add persisted Weekly News Focus event evidence contracts` added `backend/repositories/weekly_news.py`, `backend/weekly_news_repository.py`, `alembic/versions/20260425_0008_weekly_news_event_evidence_contracts.py`, and `docs/agent-journal/20260425T203725Z.md`, and updated `backend/repositories/__init__.py`, `tests/unit/test_weekly_news.py`, `tests/unit/test_source_policy.py`, `tests/unit/test_repo_contract.py`, and `tests/unit/test_safety_guardrails.py`.
- Merged branch `agent/T-093-20260425T203725Z` into `main` with local merge commit `446619f chore(T-093): merge persisted Weekly News Focus event evidence contracts`.
- `backend/repositories/weekly_news.py` added a dormant pure-Python Weekly News Focus event evidence repository contract with inspectable table metadata, row models, and validation helpers for candidate events, selected event items, market-week windows, source ranking inputs, dedupe groups, evidence-limited states, AI Comprehensive Analysis threshold metadata, source/citation references, source-use policy, freshness labels, validation status, and sanitized diagnostics.
- `backend/weekly_news_repository.py` added a re-export shim for the repository contract.
- The Alembic-style revision `20260425_0008_weekly_news_event_evidence_contracts.py` is importable and inspectable without Alembic or a live database connection; the journal records that it was not run against a database.
- Tests were expanded for repository metadata shape, serialization/validation helpers, deterministic U.S. Eastern market-week window calculations, ranking policy metadata, dedupe metadata, source-use gating, selected-vs-configured counts, evidence-limited and empty states, AI analysis threshold suppression/availability metadata, same-asset source/citation binding, sanitized diagnostics, no advice language, no secret exposure, and no live network/provider/database/LLM imports.
- The implementation did not add a persisted Weekly News Focus reader, acquisition worker, route fallback, live database execution, provider fetch, cache write, frontend change, generated Weekly News Focus output change, or generated AI Comprehensive Analysis change.
- `docs/agent-journal/20260425T203725Z.md` records these checks: `python3 -m pytest tests/unit/test_weekly_news.py tests/unit/test_source_policy.py tests/unit/test_repo_contract.py tests/unit/test_safety_guardrails.py -q` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - The contract is metadata-only and dormant; no persisted Weekly News Focus reader, acquisition worker, route fallback, live database execution, provider fetch, cache write, frontend change, or generated AI Comprehensive Analysis change was added.
  - Future T-094/T-095 work must preserve the same source-use, same-asset citation, freshness/uncertainty, empty/limited state, AI-threshold, and sanitized diagnostics gates when wiring acquisition or persisted-read fallback.

Completion commits:

- `67a948e feat(T-093): add persisted Weekly News Focus event evidence contracts`
- `446619f chore(T-093): merge persisted Weekly News Focus event evidence contracts`

### T-092: Broaden search support classification through manifests

Goal:
Route backend search/support classification through the Top-500 stock manifest and eligible ETF metadata contracts while preserving current cached asset behavior, blocked generated-output states, deterministic fixtures, frontend fallback behavior, and no-live-provider defaults.

Completed details:

- Implementation commit `0356606 feat(T-092): broaden search support classification through manifests` updated `backend/data.py`, `backend/search.py`, `backend/ingestion.py`, `backend/providers.py`, `tests/unit/test_search_classification.py`, `tests/unit/test_ingestion_jobs.py`, `tests/unit/test_provider_adapters.py`, and `tests/integration/test_backend_api.py`, and added `docs/agent-journal/20260425T202552Z.md`.
- Merged branch `agent/T-092-20260425T202552Z` into `main` with local merge commit `d09b1b1 chore(T-092): merge broaden search support classification through manifests`.
- Backend search now routes stock eligible-not-cached candidates through the Top-500 manifest helper instead of relying on duplicated launch-universe classification inputs.
- Backend search now routes eligible, blocked, out-of-scope, unknown, and unavailable ETF search candidates through the ETF universe metadata contract.
- Cached generated behavior for `AAPL`, `VOO`, and `QQQ` was preserved.
- Eligible-not-cached and unsupported/out-of-scope assets remain blocked from generated output, including manifest-backed ETF examples.
- The existing public unsupported search asset type for recognized unsupported assets was preserved while sourcing ETF classification from the manifest.
- `backend/ingestion.py` and `backend/providers.py` were adjusted so related ingestion/provider classification paths preserve fixture-only, no-live-call behavior while consuming manifest-backed support metadata where applicable.
- Tests were expanded for manifest-backed stock and ETF classification, ingestion job behavior, provider adapter behavior, and API schema stability.
- `docs/agent-journal/20260425T202552Z.md` records these checks: `python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_ingestion_jobs.py tests/unit/test_provider_adapters.py -q` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed; `python3 -m pytest tests -q` passed; `npm test` passed; `python3 evals/run_static_evals.py` passed after a revision restored the existing public `asset_type: unsupported` schema for recognized unsupported assets; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - Search classification consumes the current deterministic manifests, but broader ETF-like products beyond manifest entries remain future metadata additions.
  - Out-of-scope ETF-like products are covered through the existing out-of-scope compatibility map name, which still references common stocks for historical callers.
  - No live provider lookup, ingestion execution, generated output, frontend search rendering, or source allowlist expansion was added.

Completion commits:

- `0356606 feat(T-092): broaden search support classification through manifests`
- `d09b1b1 chore(T-092): merge broaden search support classification through manifests`

### T-091: Add eligible ETF universe metadata contracts

Goal:
Add deterministic eligible ETF universe metadata contracts so search and support classification can later broaden beyond the cached launch fixtures while preserving generated-output blocking for eligible-not-cached, unsupported, out-of-scope, unknown, unavailable, leveraged, inverse, ETN, fixed-income, commodity, active, and multi-asset ETF states.

Completed details:

- Implementation commit `6ab7c4c feat(T-091): add eligible ETF universe metadata contracts` added `backend/etf_universe.py`, `data/universes/us_equity_etfs.current.json`, and `docs/agent-journal/20260425T201409Z.md`, and updated `backend/data.py`, `backend/models.py`, `tests/unit/test_search_classification.py`, `tests/unit/test_provider_adapters.py`, `tests/unit/test_repo_contract.py`, and `tests/unit/test_safety_guardrails.py`.
- Merged branch `agent/T-091-20260425T201409Z` into `main` with local merge commit `6cf68aa chore(T-091): merge eligible ETF universe metadata contracts`.
- `data/universes/us_equity_etfs.current.json` added a deterministic ETF universe manifest for supported-scope non-leveraged U.S.-listed equity index, sector, and thematic ETF candidates, with manifest metadata, provenance, checksum fields, support state, launch/cache state, evidence/freshness or unavailable metadata, exclusion flags, and non-advice framing.
- `backend/etf_universe.py` added pure loader, validation, checksum, no-advice-language, lookup, cached-supported, eligible-not-cached, blocked-entry, and generated-output-eligibility helpers for the ETF universe metadata contract.
- `backend/models.py` added ETF universe manifest and entry models covering ETF category, support state, launch cache state, exclusion flags, evidence metadata, and manifest metadata.
- `backend/data.py` now derives legacy eligible-not-cached ETF metadata from the ETF universe contract while preserving existing deterministic search behavior until the T-092 route-level classification task.
- The contract preserves cached generated coverage for `VOO` and `QQQ`, keeps eligible-not-cached ETFs such as `SPY`, `VTI`, `IVV`, `IWM`, `DIA`, `VGT`, `XLK`, `SOXX`, `SMH`, `XLF`, and `XLV` blocked from generated output, and explicitly blocks unsupported ETF classes including leveraged, inverse, ETN, fixed-income, commodity, active, multi-asset, unknown, and unavailable states.
- Tests cover manifest shape, checksum/provenance fields, supported-scope ETF eligibility, cached-supported versus eligible-not-cached states, unsupported ETF blocking, unknown/unavailable states, advice-language rejection, no-live-call/no-secret behavior, and preservation of current search/provider behavior.
- The implementation did not change public search routes, generated-output behavior, provider behavior, frontend behavior, live provider wiring, source allowlists, GCS/provider/ingestion/cache/deployment wiring, or default fixture-generated output.
- `docs/agent-journal/20260425T201409Z.md` records these checks: `python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_provider_adapters.py tests/unit/test_repo_contract.py tests/unit/test_safety_guardrails.py -q` passed with 47 tests; `python3 -m pytest tests -q` passed with 318 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - The ETF universe contract is metadata-only. Public route-level search/support classification still consumes the existing deterministic search fixtures until T-092.
  - Unsupported and out-of-scope ETF-like products beyond the narrow fixture examples remain future metadata additions.
  - The production mirror env var is declared as contract metadata only; no GCS, provider, ingestion, cache, or deployment wiring was added.

Completion commits:

- `6ab7c4c feat(T-091): add eligible ETF universe metadata contracts`
- `6cf68aa chore(T-091): merge eligible ETF universe metadata contracts`

### T-090: Add trust-metric event sink persistence contracts

Goal:
Add dormant trust-metric event sink persistence contracts for compact metadata events covering citation coverage, unsupported claims, freshness accuracy, glossary use, comparison use, source drawer use, safety redirects, export use, and latency without enabling real analytics emission, frontend instrumentation, external analytics vendors, live database execution, or raw user text storage.

Completed details:

- Implementation commit `5d69d7c feat(T-090): add trust-metric event sink persistence contracts` added `backend/repositories/trust_metrics.py`, `backend/trust_metric_repository.py`, `alembic/versions/20260425_0007_trust_metric_event_contracts.py`, and `docs/agent-journal/20260425T200127Z.md`, and updated `backend/repositories/__init__.py` and `tests/unit/test_trust_metrics.py`.
- Merged branch `agent/T-090-20260425T200127Z` into `main` with local merge commit `a3bbbeb chore(T-090): merge trust-metric event sink persistence contracts`.
- `backend/repositories/trust_metrics.py` added a dormant pure-Python trust-metric event repository contract with table metadata and row models for accepted event metadata, validation status, aggregate counters, latency summaries, freshness states, safety statuses, generated-output state consistency, and sanitized diagnostics.
- `backend/trust_metric_repository.py` added a re-export boundary so future tasks can import the trust-metric repository contract without reaching into `backend/repositories` internals.
- The Alembic-style revision `20260425_0007_trust_metric_event_contracts.py` is importable and inspectable without Alembic or a live database connection; the journal records that it was not run against a database.
- Repository rows are derived from validated compact events and preserve the existing validation-only trust-metrics behavior, including `validation_only=True`, `persistence_enabled=False`, `external_analytics_enabled=False`, and no-live-call semantics.
- Validation and tests reject or suppress raw query text, questions, answers, source passages, source URLs, personal identifiers, cookies, portfolio/allocation details, external analytics IDs, hidden prompts, raw model reasoning, unrestricted provider payloads, real secrets, public storage URLs, and signed URLs.
- The contract preserves support-state, generated-output, citation/source-use, freshness/uncertainty, safety, and v0.4 workflow boundaries while keeping diagnostics compact and sanitized.
- The implementation did not add frontend files, public API route changes, analytics emission, external analytics vendors, production database writers, cache writes, provider calls, LLM calls, generated-output changes, source allowlist changes, user identity, cookies, browser storage, or production observability wiring.
- `docs/agent-journal/20260425T200127Z.md` records these checks: `python3 -m pytest tests/unit/test_trust_metrics.py tests/unit/test_repo_contract.py tests/unit/test_safety_guardrails.py -q` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed.
- Remaining risks from the journal:
  - The trust-metric repository is a dormant pure-Python contract only; no production database writer, analytics sink, route wiring, or migration execution was added.
  - The Alembic-style revision is importable and inspectable but was not run against a database.
  - Future integration must preserve the same compact metadata, no raw user text, no source URL, citation/source-use, freshness, support-state, and safety gates when an injected persisted sink is introduced.

Completion commits:

- `5d69d7c feat(T-090): add trust-metric event sink persistence contracts`
- `a3bbbeb chore(T-090): merge trust-metric event sink persistence contracts`

### T-089: Route chat session lifecycle and exports through persisted session boundaries

Goal:
Route accountless chat session lifecycle and transcript export lookup through injected persisted session boundaries first, while preserving existing deterministic in-memory or fixture fallback, deletion behavior, seven-day TTL semantics, safety redirects, comparison redirects, selected-asset grounding, and export licensing rules.

Completed details:

- Implementation commit `5282cfc feat(T-089): route chat session lifecycle and exports through persisted session boundaries` updated `backend/chat_sessions.py`, `backend/export.py`, `tests/unit/test_chat_sessions.py`, and `docs/agent-journal/20260425T194835Z.md`.
- Merged branch `agent/T-089-20260425T194835Z` into `main` with local merge commit `dbfc7cf chore(T-089): merge route chat session lifecycle and exports through persisted session boundaries`.
- `backend/chat_sessions.py` added the dormant `CHAT_SESSION_PERSISTED_BOUNDARY`, `PersistedChatSessionReader`, and `PersistedChatSessionWriter` boundaries for accountless chat session records.
- `answer_chat_with_session`, `get_chat_session_status`, `delete_chat_session`, and `chat_session_export_payload` now accept optional persisted reader/writer boundaries while preserving the default deterministic in-memory `ChatSessionStore` path.
- Persisted records are read through `ChatSessionRepositoryRecords.model_validate` and `validate_chat_session_records` before use, with reader failures, missing records, invalid records, validation failures, and unsupported shapes falling back to the existing store behavior.
- Persisted status and export lookup reconstruct public session metadata, safe turn summaries, citations, source metadata, comparison redirect metadata, advice redirect metadata, freshness labels, uncertainty labels, and unavailable/expired/deleted states from validated T-088 rows.
- Persisted lifecycle handling preserves selected-asset binding and returns ticker-mismatch semantics without converting wrong-asset persisted records into factual answers.
- Persisted deletion handling creates validated deleted records with `user_deleted` state, clears turn summaries, disables export availability, removes citation/source references from deleted records, and calls the injected writer when available.
- Persisted active-session continuation may append a new deterministic chat response to a validated persisted record and pass validated metadata-only records to the injected writer; no live database, ORM, cache, object storage, provider, or LLM path was added.
- Persisted transcript exports reconstruct metadata-only safe text and preserve Markdown/JSON export behavior, educational disclaimer metadata, citation/source/freshness/uncertainty labels, comparison route suggestions, advice redirect framing, and source-use restrictions.
- `backend/export.py` routes `export_chat_transcript`, `export_chat_session_transcript`, and the existing-session chat export helper through an optional `persisted_session_reader` before fixture question export behavior.
- `tests/unit/test_chat_sessions.py` added in-memory persisted reader/writer fixtures and coverage for persisted-first status/export/delete lookup, fallback for reader failures/missing/invalid records, TTL expiry, ticker mismatch, safe writes, advice redirect export metadata, comparison redirect export metadata, `metadata_only` source-use export behavior, and ensuring raw questions are not exported from persisted sessions.
- The implementation did not add frontend storage, cookies, user accounts, route schema changes, live database/cache/provider/LLM execution, analytics emission, production persistence wiring, export format changes, or public API behavior changes.
- `docs/agent-journal/20260425T194835Z.md` records these checks: `python3 -m pytest tests/unit/test_chat_sessions.py -q` passed with 23 tests; `python3 -m pytest tests/unit/test_chat_sessions.py tests/unit/test_exports.py tests/unit/test_safety_guardrails.py -q` passed with 40 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 33 tests; `python3 -m pytest tests -q` passed with 308 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed.
- Remaining risks from the journal:
  - Persisted chat session boundaries are injectable and dormant only; no live database, ORM, cache, provider, LLM, frontend storage, route schema, cookie, analytics, or production persistence wiring was added.
  - Persisted transcript exports reconstruct safe metadata-only turn text from validated T-088 rows; raw user questions and raw answer transcripts remain unavailable by design.
  - Future production readers/writers still need separate wiring with the same selected-asset, TTL, deletion, source-use, citation, freshness, and no-raw-transcript gates.

Completion commits:

- `5282cfc feat(T-089): route chat session lifecycle and exports through persisted session boundaries`
- `dbfc7cf chore(T-089): merge route chat session lifecycle and exports through persisted session boundaries`

### T-088: Add accountless chat session persistence contracts

Goal:
Add dormant accountless chat session persistence contracts for anonymous conversation IDs, seven-day TTL metadata, deletion state, safe turn summaries, comparison redirects, and transcript export metadata without routing current chat behavior through a live database.

Completed details:

- Implementation commit `1a02e01 feat(T-088): add accountless chat session persistence contracts` added `backend/repositories/chat_sessions.py`, `backend/chat_session_repository.py`, `alembic/versions/20260425_0006_chat_session_repository_contracts.py`, and `docs/agent-journal/20260425T185521Z.md`, and updated `backend/repositories/__init__.py` and `tests/unit/test_chat_sessions.py`.
- Merged branch `agent/T-088-20260425T185521Z` into `main` with local merge commit `8747e0a chore(T-088): merge accountless chat session persistence contracts`.
- `backend/repositories/chat_sessions.py` added a dormant pure-Python accountless chat session repository contract with table metadata and row models for session envelopes, selected-asset scope, seven-day TTL timestamps, lifecycle state, deletion state, safe turn summaries, comparison redirect metadata, transcript export metadata, source/citation references, and compact diagnostics.
- `backend/chat_session_repository.py` re-exports the accountless chat session repository boundary, row models, validation helpers, serialization helpers, metadata helper, turn-kind and diagnostic enums, and contract error for future lifecycle/export integration.
- The Alembic-style revision `20260425_0006_chat_session_repository_contracts.py` is importable and inspectable without Alembic or a live database connection; the journal records that it was not executed against a database.
- Repository validation enforces anonymous opaque conversation IDs, selected-asset binding, seven-day TTL metadata, active/expired/deleted/ticker-mismatch/unavailable lifecycle states, idempotent user-deleted state, export availability rules, source/citation binding, source-use rights, freshness and uncertainty labels, and compact sanitized diagnostics.
- Safe turn summaries are metadata-only and may represent factual answers, advice redirects, and comparison redirects without storing raw user text, raw answer text for analytics/training/evaluation, hidden prompts, raw model reasoning, secrets, unrestricted source text, unrestricted provider payloads, public URLs, or signed URLs.
- The contract preserves advice redirect semantics by allowing advice-like turns only as safe metadata without factual citation/source reuse or buy/sell/hold, allocation, price-target, tax, brokerage/trading, or personalized recommendation output.
- The contract preserves comparison redirect semantics by requiring second-ticker comparison questions to remain safe route metadata rather than single-asset factual answers or persisted generated answer artifacts.
- The implementation did not add live database execution, route wiring, browser storage, analytics emission, persisted transcript lookup, provider calls, LLM calls, frontend changes, production repository execution, or public API schema changes.
- `tests/unit/test_chat_sessions.py` added coverage for repository metadata/table shape, migration importability, TTL/deletion metadata, safe turn summary serialization, comparison redirect metadata, advice redirect metadata, source/citation binding, selected-asset enforcement, export metadata, blocked generated-output states, source-use gating, citation/freshness/uncertainty gating, sanitized diagnostics, no raw prompt/reasoning/user-text/transcript/secret exposure, no live database/cache/provider/LLM imports, and preservation of existing chat session behavior.
- `docs/agent-journal/20260425T185521Z.md` records these checks: `python3 -m pytest tests/unit/test_chat_sessions.py tests/unit/test_exports.py tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 43 tests; `python3 -m pytest tests -q` passed with 302 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - The accountless chat session repository is intentionally dormant and metadata-only; no live database execution, route wiring, browser storage, analytics emission, or persisted transcript lookup was added.
  - The Alembic-style revision is importable and inspectable, but it was not executed against a database.
  - The follow-up T-089 wiring later preserved the same selected-asset, TTL, deletion, source-use, citation, freshness, export, and no-raw-transcript gates through injected dormant boundaries.

Completion commits:

- `1a02e01 feat(T-088): add accountless chat session persistence contracts`
- `8747e0a chore(T-088): merge accountless chat session persistence contracts`

### T-087: Route grounded chat answer artifacts through persisted pack and cache boundaries

Goal:
Route grounded single-asset chat answer generation through injected persisted knowledge-pack and chat-safe generated-output cache read boundaries first, while preserving selected-asset grounding, advice redirects, comparison redirects, accountless session semantics, deterministic fixture fallback, citation/source-use/freshness gates, and current public chat/export behavior.

Completed details:

- Implementation commit `dd86f8c feat(T-087): route grounded chat answer artifacts through persisted pack and cache boundaries` updated `backend/chat.py`, `tests/unit/test_chat_generation.py`, and `docs/agent-journal/20260425T184456Z.md`.
- Merged branch `agent/T-087-20260425T184456Z` into `main` with local merge commit `9dd0518 chore(T-087): merge route grounded chat answer artifacts through persisted pack and cache boundaries`.
- `backend/chat.py` added an injected, read-only persisted chat answer artifact boundary for supported single-asset factual chat answers.
- The default `generate_asset_chat(ticker, question)` path remains deterministic and fixture-backed when no persisted readers are supplied.
- Advice-like prompts and second-ticker comparison questions keep redirect precedence before persisted reader or cache lookup.
- Persisted chat reuse validates same-asset knowledge-pack records, chat-safe generated-output cache metadata, cache freshness hashes, source and citation bindings, source-use rights, freshness labels, raw transcript blocks, citation validation, and safety output before returning a response.
- Invalid or blocked persisted reads fall back to existing deterministic chat behavior.
- The implementation did not add live database or cache readers, cache writers, invalidation workers, route wiring, frontend changes, provider calls, LLM calls, or public API schema changes.
- `tests/unit/test_chat_generation.py` added coverage for persisted-first grounded chat answer reads, default fixture fallback, invalid cache records, wrong-pack source/citation rejection, wrong-asset identity rejection, advice redirect precedence, comparison redirect preservation, source-use gating, freshness blocking, unsupported/out-of-scope/eligible-not-cached/unknown/unavailable blocking, safety blocking, sanitized diagnostics, raw transcript blocking, and unchanged deterministic output.
- `docs/agent-journal/20260425T184456Z.md` records these checks: `python3 -m pytest tests/unit/test_chat_generation.py -q` passed with 18 tests; `python3 -m pytest tests/unit/test_chat_generation.py tests/unit/test_cache_contracts.py tests/unit/test_safety_guardrails.py -q` passed with 54 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 33 tests; `python3 -m pytest tests -q` passed with 294 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed.
- Remaining risks from the journal:
  - The persisted chat path is injectable only; no live database/cache reader, cache writer, invalidation worker, route wiring, frontend change, provider call, or LLM call was added.
  - Generated-output cache records remain metadata-only, so this slice validates cache eligibility and freshness boundaries while regenerating the chat response from persisted knowledge-pack evidence plus the existing deterministic chat planner.
  - Future production integration still needs separate live persistence readers and route-level wiring with the same fallback, citation, source-use, freshness, safety, and accountless session gates.

Completion commits:

- `dd86f8c feat(T-087): route grounded chat answer artifacts through persisted pack and cache boundaries`
- `9dd0518 chore(T-087): merge route grounded chat answer artifacts through persisted pack and cache boundaries`

### T-086: Route comparison generation through persisted pack and cache boundaries

Goal:
Route supported comparison generation through injected persisted knowledge-pack and generated-output cache read boundaries first, while preserving deterministic local comparison fallback, same-comparison-pack citation boundaries, blocked states, export behavior, and stock-vs-ETF relationship behavior.

Completed details:

- Implementation commit `63522b8 feat(T-086): route comparison generation through persisted pack and cache boundaries` updated `backend/comparison.py`, `tests/unit/test_comparison_generation.py`, and `docs/agent-journal/20260425T183344Z.md`.
- Merged branch `agent/T-086-20260425T183344Z` into `main` with local merge commit `73968e9 chore(T-086): merge route comparison generation through persisted pack and cache boundaries`.
- `backend/comparison.py` added the injected `COMPARISON_PERSISTED_READ_BOUNDARY`, `GeneratedOutputComparisonCacheRecordReader`, `PersistedComparisonReadResult`, and `read_persisted_comparison_response` boundary for supported comparison generation.
- The default `generate_comparison(left_ticker, right_ticker)` path remains deterministic and fixture-backed unless persisted knowledge-pack and generated-output comparison cache readers are explicitly supplied.
- Persisted comparison reuse validates requested left/right identity, same comparison pack, comparison cache scope, output identity, source/citation bindings, freshness hashes, generated-output hash, source-use permissions, blocked states, citation validation, and safety output before returning a persisted comparison result.
- Invalid or blocked persisted inputs fall back to existing deterministic comparison behavior, including missing readers, reader failures, cache misses, invalid cache metadata, wrong identity, wrong citation or source bindings, no-local-pack states, unsupported states, source-use blocks, stale-without-label states, and unsafe persisted content.
- Generated-output cache records remain metadata-only in this slice; the persisted path validates cache eligibility and freshness boundaries while regenerating comparison output from persisted knowledge-pack evidence plus the existing deterministic comparison fixture.
- The implementation did not add live database or cache readers, cache writers, invalidation workers, route wiring, frontend changes, provider calls, LLM calls, export rewrites, or public API schema changes.
- `tests/unit/test_comparison_generation.py` added coverage for valid persisted reads, default fallback, invalid cache fallback, wrong identity/citation rejection, reverse-order preservation, no-local-pack and unsupported blocking, source-use blocking, stale-without-label blocking, safety blocking, sanitized diagnostics, and unchanged deterministic output.
- `docs/agent-journal/20260425T183344Z.md` records these checks: `python3 -m pytest tests/unit/test_comparison_generation.py -q` passed with 16 tests; `python3 -m pytest tests/unit/test_comparison_generation.py tests/unit/test_cache_contracts.py tests/unit/test_retrieval_repository.py -q` passed with 50 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 33 tests; `python3 -m pytest tests -q` passed with 287 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed.
- Remaining risks from the journal:
  - The persisted comparison path is injectable only; no live database/cache reader, cache writer, invalidation worker, route wiring, frontend change, provider call, or LLM call was added.
  - Generated-output cache records remain metadata-only, so this slice validates cache eligibility and freshness boundaries while regenerating the comparison from persisted knowledge-pack evidence plus the existing deterministic comparison fixture.
  - Future production integration still needs separate live persistence readers and route-level wiring with the same fallback, citation, source-use, freshness, and safety gates.

Completion commits:

- `63522b8 feat(T-086): route comparison generation through persisted pack and cache boundaries`
- `73968e9 chore(T-086): merge route comparison generation through persisted pack and cache boundaries`

### T-085: Route asset overview through persisted pack and cache boundaries

Goal:
Route the supported asset overview generation path through injected persisted knowledge-pack and generated-output cache read boundaries first, while preserving deterministic fixture fallback, current API response shape, current frontend behavior, and current safety/citation/source-use behavior.

Completed details:

- Implementation commit `d5061e7 feat(T-085): route asset overview through persisted pack and cache boundaries` updated `backend/overview.py`, `tests/unit/test_overview_generation.py`, and `docs/agent-journal/20260425T182004Z.md`.
- Merged branch `agent/T-085-20260425T182004Z` into `main` with local merge commit `889b0f1 chore(T-085): merge route asset overview through persisted pack and cache boundaries`.
- `backend/overview.py` added the injected `OVERVIEW_PERSISTED_READ_BOUNDARY`, `GeneratedOutputCacheRecordReader`, `PersistedOverviewReadResult`, and `read_persisted_overview_response` boundary for supported asset overview generation.
- The default `generate_asset_overview(ticker)` path remains deterministic and fixture-backed unless both a persisted knowledge-pack reader and generated-output cache reader are explicitly supplied.
- Persisted overview reuse validates same-asset knowledge-pack records, generated-output cache metadata, source and citation bindings, source-use policy, freshness hashes, safety output, and section freshness before returning a persisted-read result.
- Invalid or blocked persisted inputs fall back to the existing fixture path, including missing readers, reader failures, cache misses, invalid cache metadata, freshness mismatch, wrong-asset source/citation bindings, source-policy blocks, unsupported, eligible-not-cached, unknown, unavailable, and advice-like persisted content.
- Generated-output cache records remain metadata-only in this slice; the persisted path validates cache eligibility and freshness boundaries, then regenerates the overview from persisted knowledge-pack evidence.
- The implementation did not add live database or cache readers, cache writers, invalidation workers, route wiring, frontend changes, provider calls, LLM calls, or public API schema changes.
- `tests/unit/test_overview_generation.py` added coverage for persisted-first overview reads, default fixture fallback, invalid cache records, freshness mismatch, wrong-asset source/citation rejection, source-use gating, blocked states, safety blocking, sanitized diagnostics, and no raw prompt/reasoning/user-text/secret exposure.
- `docs/agent-journal/20260425T182004Z.md` records these checks: `python3 -m pytest tests/unit/test_overview_generation.py tests/unit/test_cache_contracts.py tests/unit/test_retrieval_repository.py -q` passed; `python3 -m pytest tests/integration/test_backend_api.py -q` passed; `python3 -m pytest tests -q` passed; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed.
- Remaining risks from the journal:
  - The persisted overview path is injectable only; no live database/cache reader, cache writer, invalidation worker, route wiring, frontend change, provider call, or LLM call was added.
  - Generated-output cache records remain metadata-only, so this slice validates cache eligibility and freshness boundaries while regenerating the overview from persisted knowledge-pack evidence.
  - Future production integration still needs separate live persistence readers and route-level wiring with the same fallback, citation, source-use, freshness, and safety gates.

Completion commits:

- `d5061e7 feat(T-085): route asset overview through persisted pack and cache boundaries`
- `889b0f1 chore(T-085): merge route asset overview through persisted pack and cache boundaries`

### T-084: Add persisted generated-output cache and freshness-hash contracts

Goal:
Add dormant persisted generated-output cache and freshness-hash repository contracts for overview, comparison, chat-safe answer artifacts, exports, source checksums, knowledge-pack hashes, generated-output freshness hashes, validation status, and invalidation diagnostics without routing current responses through the cache.

Completed details:

- Implementation commit `6201ddb feat(T-084): add persisted generated-output cache and freshness-hash contracts` added `alembic/versions/20260425_0005_generated_output_cache_contracts.py`, `backend/generated_output_cache_repository.py`, `backend/repositories/generated_outputs.py`, and `docs/agent-journal/20260425T180425Z.md`, and updated `backend/repositories/__init__.py` and `tests/unit/test_cache_contracts.py`.
- Merged branch `agent/T-084-20260425T180425Z` into `main` with local merge commit `cbb4ee3 chore(T-084): merge persisted generated-output cache and freshness-hash contracts`.
- `backend/repositories/generated_outputs.py` added a dormant pure-Python generated-output cache repository contract for cache envelopes, artifact records, source checksum inputs, knowledge-pack hash inputs, generated-output freshness hash inputs, validation statuses, citation/source binding metadata, safety/source-use/freshness statuses, and compact invalidation diagnostics.
- `backend/generated_output_cache_repository.py` re-exports the generated-output cache repository boundary, row models, categories, validation helpers, serialization helpers, metadata helper, and contract error for future route-level cache integration.
- The generated-output cache contract covers asset overview section artifacts, comparison outputs, grounded chat-safe answer artifacts, Markdown/JSON export payload metadata, source-list export metadata, source checksum records, knowledge-pack hash inputs, generated-output hash inputs, validation status records, and diagnostics.
- Cache validation preserves same-asset and same-comparison-pack boundaries, left/right comparison identity, citation/source binding, supported-asset requirements, safety gating, source-use gating, allowed freshness labels, and generated-output blocking for unsupported, out-of-scope, eligible-not-cached, unknown, unavailable, partial-without-label, stale-without-label, insufficient-evidence-without-label, validation-failed, advice-like, wrong-asset, wrong-pack, source-policy-blocked, and rejected-source states.
- The contract keeps chat cache records to answer-artifact metadata and blocks raw user transcript text for analytics, training, or evaluation.
- Source-use policy continues to win over recency or cache scoring: `metadata_only` and `link_only` records cannot persist raw chunk text, `summary_allowed` records are limited to allowed summaries or excerpts, and `rejected` or source-policy-blocked sources cannot feed cacheable generated output.
- Diagnostics are limited to compact sanitized metadata such as validation codes, invalidation reasons, source IDs, checksums, timestamps, and freshness states, without unrestricted raw source text, raw provider payloads, hidden prompts, raw model reasoning, raw user text, credentials, or secrets.
- The Alembic revision `20260425_0005_generated_output_cache_contracts.py` is importable and inspectable, limited to generated-output cache contract tables, and was not executed against a database in this task.
- The journal records that no API route, retrieval, generation, chat, comparison, export, glossary, provider, frontend, live database, live cache, Redis, object storage, or LLM behavior was changed.
- `docs/agent-journal/20260425T180425Z.md` records these checks: `python3 -m pytest tests/unit/test_cache_contracts.py tests/unit/test_source_policy.py tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q` passed with 48 tests; `python3 -m pytest tests -q` passed with 274 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `git diff --check` passed.
- Remaining risks from the journal:
  - The contract is metadata-only and intentionally dormant; no production database reader/writer, cache integration, invalidation worker, route wiring, or executed migration was added.
  - The Alembic revision is importable and inspectable, but it was not executed against a database in this task.
  - Future route-level cache integration still needs separate surface-specific tasks for overview, comparison, chat-safe answer artifacts, and exports so fixture fallback and safety/citation/source-use gates remain intact.

Completion commits:

- `6201ddb feat(T-084): add persisted generated-output cache and freshness-hash contracts`
- `cbb4ee3 chore(T-084): merge persisted generated-output cache and freshness-hash contracts`

### T-083: Add ETF issuer and holdings source adapter fixture contracts

Goal:
Add fixture-backed ETF issuer, fact-sheet, holdings, prospectus, and exposure-file adapter contracts for supported non-leveraged U.S.-listed equity ETFs without live issuer/provider calls, generated-output changes, or unsupported ETF expansion.

Completed details:

- Implementation commit `d1ab858 feat(T-083): add ETF issuer and holdings source adapter fixture contracts` added `backend/provider_adapters/etf_issuer.py` and `docs/agent-journal/20260425T060213Z.md`, and updated `backend/providers.py` and `tests/unit/test_provider_adapters.py`.
- Merged branch `agent/T-083-20260425T060213Z` into `main` with local merge commit `8f5b6c8 chore(T-083): merge ETF issuer and holdings source adapter fixture contracts`.
- `backend/provider_adapters/etf_issuer.py` added a dormant fixture-backed ETF issuer adapter contract for existing deterministic `VOO` and `QQQ` coverage.
- The ETF fixture contract normalizes ETF identity, issuer/fact-sheet metadata, benchmark, expense ratio, holdings count, prospectus references, holdings rows, exposure rows, official issuer source attribution, freshness metadata, and explicit unavailable evidence gaps.
- `backend/providers.py` routes the existing mock ETF issuer provider through the new fixture contract while preserving eligible-not-cached, unsupported, out-of-scope, unknown, and no-generated-output behavior.
- The fixture contract validates same-ticker, same-issuer, same-source, source-use policy, official issuer quality, blocked ETF class indicators, and official ETF source ranking ahead of structured reference and recent-context sources.
- Provider responses keep generated-output flags false and remain fixture-only/import-safe with no frontend behavior, public API route behavior, live issuer/provider calls, credential paths, source allowlist changes, ETF universe expansion, generated pages, chat answers, comparisons, risk summaries, exports, or cacheable generated output.
- `tests/unit/test_provider_adapters.py` covers ETF issuer/fact-sheet/prospectus/holdings/exposure normalization, official source attribution, freshness and unavailable evidence-gap states, same-ETF ticker/issuer/source binding, blocked ETF class handling, source-policy enforcement, generated-output blocking, and no-live-call/no-secret import behavior.
- `docs/agent-journal/20260425T060213Z.md` records these checks: `python3 -m pytest tests/unit/test_provider_adapters.py -q` passed with 14 tests; `python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_retrieval_fixtures.py tests/unit/test_source_policy.py tests/unit/test_repo_contract.py -q` passed with 35 tests; `python3 -m pytest tests -q` passed with 264 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed, including Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - The ETF issuer adapter contract is intentionally fixture-only and dormant; it does not fetch live issuer pages, fact sheets, prospectuses, holdings files, exposure files, or provider data.
  - Only existing deterministic cached ETF coverage (`VOO` and `QQQ`) is represented; this does not broaden supported ETF coverage or generate output for eligible-not-cached ETFs such as `SPY`.
  - Future live ETF ingestion still needs separate source snapshot, parser, storage, source-use, licensing, persistence, route/admin, and generated-output validation work before production execution is enabled.

Completion commits:

- `d1ab858 feat(T-083): add ETF issuer and holdings source adapter fixture contracts`
- `8f5b6c8 chore(T-083): merge ETF issuer and holdings source adapter fixture contracts`

### T-082: Add SEC stock source adapter fixture contract

Goal:
Add a fixture-backed SEC stock source adapter and parser contract for identity, submissions, selected filing metadata, XBRL company facts, source attribution, freshness, and evidence gaps without live SEC calls, generated-output changes, or broader stock coverage.

Completed details:

- Implementation commit `6ccf295 feat(T-082): add SEC stock source adapter fixture contract` added `backend/provider_adapters/__init__.py`, `backend/provider_adapters/sec_stock.py`, and `docs/agent-journal/20260425T054900Z.md`, and updated `backend/providers.py` and `tests/unit/test_provider_adapters.py`.
- Merged branch `agent/T-082-20260425T054900Z` into `main` with local merge commit `b4538c2 chore(T-082): merge SEC stock source adapter fixture contract`.
- `backend/provider_adapters/sec_stock.py` added a dormant fixture-backed SEC stock adapter contract for `AAPL` with normalized SEC submissions metadata, selected Form 10-K filing metadata, XBRL company-fact metadata, official SEC source attribution, freshness metadata, and an explicit unavailable evidence gap for current valuation metrics.
- `backend/providers.py` routes the existing mock SEC provider through the new fixture contract when a registered SEC stock fixture exists, while preserving existing supported, eligible-not-cached, unsupported, out-of-scope, unknown, and unavailable provider states.
- The fixture contract validates Top-500 manifest CIK/ticker identity binding, same-asset source and fact binding, official SEC source policy, permitted source-use operations, wrong-CIK rejection, wrong-source rejection, and generated-output blocking.
- Provider responses keep generated-output flags false and remain fixture-only/import-safe with no live SEC calls, credentials, route wiring, frontend changes, generated pages, chat answers, comparisons, risk summaries, exports, cache writes, source allowlist changes, or broader stock coverage.
- `tests/unit/test_provider_adapters.py` covers SEC fixture parsing, submissions/filing/XBRL normalization, official attribution, freshness and unavailable evidence-gap states, same-asset binding, wrong-ticker/wrong-CIK/wrong-source rejection, source-policy blocking, generated-output blocking, and no-live-call/no-secret import behavior.
- `docs/agent-journal/20260425T054900Z.md` records these checks: `python3 -m pytest tests/unit/test_provider_adapters.py -q` passed with 10 tests; `python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_retrieval_fixtures.py tests/unit/test_source_policy.py tests/unit/test_repo_contract.py -q` passed with 32 tests; `python3 -m pytest tests -q` passed with 261 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed.
- Remaining risks from the journal:
  - The SEC stock adapter contract is intentionally dormant and fixture-only; it does not fetch live SEC data, persist source snapshots, execute ingestion jobs, or route public APIs through a live provider.
  - Only the existing deterministic cached stock fixture coverage is represented; this does not broaden stock support or add generated output for eligible-not-cached stocks.
  - Future live SEC ingestion work still needs separate source snapshot, storage, rate-limit, user-agent, persistence, source-policy, and route/admin contracts before production execution is enabled.

Completion commits:

- `6ccf295 feat(T-082): add SEC stock source adapter fixture contract`
- `b4538c2 chore(T-082): merge SEC stock source adapter fixture contract`

### T-081: Add source snapshot artifact metadata contracts

Goal:
Add dormant source snapshot artifact metadata contracts for raw, parsed, generated, and diagnostics artifacts so future ingestion can reference private object storage safely while preserving rights-tiered source-use policy and no-public-snapshot behavior.

Completed details:

- Implementation commit `355863b feat(T-081): add source snapshot artifact metadata contracts` updated `backend/repositories/source_snapshots.py`, `backend/source_snapshot_repository.py`, `backend/repositories/__init__.py`, `alembic/versions/20260425_0004_source_snapshot_artifact_contracts.py`, `tests/unit/test_source_snapshot_repository.py`, and `docs/agent-journal/20260425T053555Z.md`.
- Merged branch `agent/T-081-20260425T053555Z` into `main` with local merge commit `611d957 chore(T-081): merge source snapshot artifact metadata contracts`.
- `backend/repositories/source_snapshots.py` added a dormant pure-Python source snapshot artifact repository contract with explicit metadata rows for `source_snapshot_artifacts` and `source_snapshot_diagnostics`.
- The contract defines artifact categories including `raw_source`, `parsed_text`, `normalized_facts_input`, `generated_artifact_reference`, `diagnostics_metadata`, metadata, checksum metadata, allowed-excerpt, and summary records.
- Source snapshot artifacts record private object URI or storage key metadata, checksum, byte size, content type, retrieved and created timestamps, source-use policy, allowlist status, source quality, permitted operations, freshness/evidence state, generated-output eligibility flags, and compact diagnostics without storing unrestricted raw text in the contract.
- Validation enforces private-by-construction storage references by rejecting public URLs, signed URLs, frontend-readable storage paths, and external fetch URLs as storage locations.
- Validation enforces rights-tier behavior for `full_text_allowed`, `summary_allowed`, `metadata_only`, `link_only`, and `rejected` sources before raw, parsed, metadata, summary, allowed-excerpt, checksum, diagnostics, or generated-artifact-reference records can be represented.
- Validation rejects wrong-asset and wrong-comparison-pack bindings, blocks rejected sources, blocks generated-output availability for unsupported or policy-blocked states, and keeps diagnostics limited to compact sanitized metadata.
- `backend/source_snapshot_repository.py` re-exports the source snapshot repository boundary, row models, categories, validation helpers, serialization helpers, metadata helper, and contract error for future ingestion integration.
- `backend/repositories/__init__.py` exposes the source snapshot artifact repository contract alongside the existing dormant repository contracts.
- The Alembic revision `20260425_0004_source_snapshot_artifact_contracts.py` is importable and limited to source snapshot artifact and diagnostic contract tables; the journal records that it was not executed against a database.
- `tests/unit/test_source_snapshot_repository.py` covers metadata/table shape, required artifact categories, migration importability, rights-tier storage rules, private reference validation, wrong-asset and wrong-pack rejection, sanitized diagnostics, generated-output blocking, repository validation/persistence behavior, serialization, and import-time no-live-storage/no-network/no-database behavior.
- The journal records that the task did not add a live object-storage client, signed URL generation, provider fetch, migration execution, route wiring, retrieval wiring, generated-output cache write, or export behavior.
- `docs/agent-journal/20260425T053555Z.md` records these checks: `python3 -m pytest tests/unit/test_source_snapshot_repository.py tests/unit/test_source_policy.py tests/unit/test_knowledge_pack_repository.py tests/unit/test_repo_contract.py -q` passed with 32 tests; `python3 -m pytest tests -q` passed with 258 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `docker compose config` passed.
- Remaining risks from the journal:
  - The source snapshot contract is intentionally dormant and metadata-only; no live object-storage client, signed URL generation, provider fetch, migration execution, route wiring, retrieval wiring, generated-output cache write, or export behavior was added.
  - The Alembic revision is importable and inspectable, but it was not executed against a database.
  - Future live ingestion work still needs separate object-storage, authorization, source-policy, persistence execution, and route/admin contracts before any production snapshot path is enabled.

Completion commits:

- `355863b feat(T-081): add source snapshot artifact metadata contracts`
- `611d957 chore(T-081): merge source snapshot artifact metadata contracts`

### T-080: Add deterministic ingestion worker execution contract

Goal:
Add a deterministic ingestion worker execution contract that consumes T-079 ingestion job ledger records through injected in-memory boundaries, runs fixture-only job transitions, and preserves existing API, retrieval, generation, chat, comparison, export, glossary, frontend, provider, and fixture behavior without live providers, live database execution, schedulers, or production worker wiring.

Completed details:

- Implementation commit `d047924 feat(T-080): add deterministic ingestion worker execution contract` updated `backend/ingestion_worker.py`, `backend/repositories/ingestion_jobs.py`, `tests/unit/test_ingestion_worker.py`, and `docs/agent-journal/20260425T052201Z.md`.
- Merged branch `agent/T-080-20260425T052201Z` into `main` with local merge commit `a278a7d chore(T-080): merge deterministic ingestion worker execution contract`.
- `backend/ingestion_worker.py` added a dormant pure-Python deterministic ingestion worker boundary with an injected in-memory ledger adapter, fixture-only terminal outcomes, compact execution summaries, and no database, provider, scheduler, object-storage, route, frontend, or production worker wiring.
- The worker transitions pending and running ledger records into deterministic terminal states including `succeeded`, `failed`, `unsupported`, `out_of_scope`, `unknown`, `unavailable`, and `stale` using fixture-only inputs.
- Unsupported, out-of-scope, unknown, unavailable, approved pending-ingestion, validation-failed, and source-policy-blocked jobs preserve generated-output blocking for pages, chat answers, comparisons, risk summaries, and cacheability.
- The worker preserves idempotent terminal execution and retry-safe deterministic failures while storing only sanitized diagnostics.
- `backend/repositories/ingestion_jobs.py` tightened ledger validation so failed ledger rows cannot expose generated output.
- `tests/unit/test_ingestion_worker.py` covers the worker execution contract, fixture-only state transitions, terminal idempotency, retryable failure behavior, blocked generated-output states, sanitized diagnostics, and no-live-call/no-database import behavior.
- The journal records that the task did not add production database readers/writers, source snapshot persistence, provider adapter execution, scheduler behavior, Cloud Run Job wiring, admin route wiring, generated-output cache writes, generated pages, generated chat answers, comparisons, risk summaries, citations, source documents, or cacheable generated output.
- `docs/agent-journal/20260425T052201Z.md` records these checks: `python3 -m pytest tests/unit/test_ingestion_worker.py tests/unit/test_ingestion_job_repository.py tests/unit/test_ingestion_jobs.py -q` passed with 33 tests; `python3 -m pytest tests -q` passed with 246 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `docker compose config` passed.
- Remaining risks from the journal:
  - The worker contract is intentionally dormant and in-memory/unit-tested only; no production database reader/writer, source snapshot persistence, provider adapter execution, scheduler, Cloud Run Job wiring, admin route wiring, or generated-output cache write path exists yet.
  - Fixture-success for approved pending-ingestion records only records deterministic worker completion and still does not create generated pages, chat answers, comparisons, risk summaries, citations, source documents, or cacheable generated output.
  - Future live ingestion work still needs separate source snapshot, source-use, provider licensing, persistence, and route/admin authorization contracts before any production execution path is enabled.

Completion commits:

- `d047924 feat(T-080): add deterministic ingestion worker execution contract`
- `a278a7d chore(T-080): merge deterministic ingestion worker execution contract`

### T-079: Add persisted ingestion job ledger contracts

Goal:
Add the first persisted ingestion job ledger contract on top of the dormant persistence boundary so future manual pre-cache and on-demand ingestion work can track deterministic job states without routing current API, retrieval, generation, chat, comparison, export, or frontend behavior through a live database.

Completed details:

- Implementation commit `b3881fa feat(T-079): add persisted ingestion job ledger contracts` updated `backend/repositories/ingestion_jobs.py`, `backend/ingestion_job_repository.py`, `backend/repositories/__init__.py`, `alembic/versions/20260425_0003_ingestion_job_ledger_contracts.py`, `tests/unit/test_ingestion_job_repository.py`, and `docs/agent-journal/20260425T050556Z.md`.
- Merged branch `agent/T-079-20260425T050556Z` into `main` with local merge commit `398aee5 chore(T-079): merge persisted ingestion job ledger contracts`.
- `backend/repositories/ingestion_jobs.py` added a dormant pure-Python ingestion job ledger repository contract with explicit table metadata, row models, deterministic job categories, required ledger states, MVP scope classification, compact sanitized diagnostics, source-policy references, checksum references, and generated-output blocking for unsupported, out-of-scope, unknown, unavailable, and unapproved pending-ingestion jobs.
- `backend/ingestion_job_repository.py` re-exports the ingestion job ledger boundary, tables, category/state models, record models, contract error, repository, metadata helper, scope classifier, serializer, and validator for future ingestion worker integration.
- `backend/repositories/__init__.py` exposes the ingestion job ledger repository contract alongside existing dormant repository contracts.
- The Alembic revision `20260425_0003_ingestion_job_ledger_contracts.py` is import-only and limited to ingestion ledger contract tables; the journal records that it was not executed against a database.
- `tests/unit/test_ingestion_job_repository.py` covers metadata, supported categories and states, migration importability, MVP scope classification, approved pending-ingestion serialization, manual pre-cache blocked assets, unsupported/out-of-scope/unknown/unavailable generated-output blocking, sanitized diagnostics, source-reference storage boundaries, validation errors, repository import behavior, and fixture preservation.
- The journal records that the task did not add live database connections, production database readers/writers, executed migrations, worker loops, schedulers, provider calls, route wiring, frontend behavior, generated-output cache persistence, source snapshot persistence, chat persistence, or export behavior.
- `docs/agent-journal/20260425T050556Z.md` records these checks: `python3 -m pytest tests/unit/test_ingestion_job_repository.py tests/unit/test_ingestion_jobs.py -q` passed with 24 tests; `python3 -m pytest tests/unit/test_ingestion_job_repository.py -q` passed with 12 tests; `python3 -m pytest tests/unit/test_repo_contract.py tests/unit/test_persistence_settings.py -q` passed with 20 tests; `python3 -m pytest tests/unit/test_ingestion_jobs.py -q` passed with 12 tests; `python3 -m pytest tests -q` passed with 237 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `docker compose config` passed.
- Remaining risks from the journal:
  - The ledger contract is intentionally dormant and in-memory/unit-tested only; no production database reader/writer, executed migration, worker execution path, scheduler, admin auth, or route integration exists yet.
  - Scope validation uses the current deterministic fixture and Top-500 manifest boundary; future live ingestion adapters still need their own source snapshot, policy, and worker execution contracts.
  - The migration is importable and inspectable, but it was not executed against a database in this task.

Completion commits:

- `b3881fa feat(T-079): add persisted ingestion job ledger contracts`
- `398aee5 chore(T-079): merge persisted ingestion job ledger contracts`

### T-078: Route retrieval through persisted packs with fixture fallback

Goal:
Route the asset knowledge-pack build-result retrieval path through an injectable persisted-pack read boundary first, with deterministic fixture fallback preserved as the default behavior and no live database dependency in normal local or CI runs.

Completed details:

- Implementation commit `6cfd5da feat(T-078): route retrieval through persisted packs with fixture fallback` updated `backend/retrieval_repository.py`, `backend/retrieval.py`, `backend/repositories/knowledge_packs.py`, `backend/repositories/__init__.py`, `tests/unit/test_retrieval_repository.py`, and `docs/agent-journal/20260425T042223Z.md`.
- Merged branch `agent/T-078-20260425T042223Z` into `main` with local merge commit `19f5169 chore(T-078): merge route retrieval through persisted packs with fixture fallback`.
- `backend/retrieval_repository.py` added a pure-Python retrieval read boundary for injected persisted `KnowledgePackRepositoryRecords`, including `KnowledgePackRecordReader`, `RetrievalRepositoryReadResult`, `RETRIEVAL_REPOSITORY_BOUNDARY`, and `read_persisted_knowledge_pack_response`.
- `build_asset_knowledge_pack_result(ticker)` remains backward compatible and fixture-backed by default; callers may opt into the persisted-first path with an injected `persisted_reader`.
- Persisted records are deserialized through the T-077 `AssetKnowledgePackRepository` contract before use, and repository misses, unconfigured readers, reader failures, invalid reader shapes, wrong-ticker records, wrong-asset source bindings, and source-use contract violations do not replace deterministic fixture output.
- `backend/repositories/knowledge_packs.py` now preserves repository row order during deserialization and restores persisted `permitted_operations` into `SourceKnowledgePackMetadata` so persisted metadata reconstructs the fixture-backed response shape more closely.
- `backend/repositories/__init__.py` re-exports the retrieval repository boundary and read helper.
- `tests/unit/test_retrieval_repository.py` covers persisted-first retrieval for `VOO`, fixture fallback for missing/empty/failing readers, non-generated metadata-only states for `SPY`, `TQQQ`, and `ZZZZ`, rejected source-use and wrong-asset persisted records, reader ticker mismatch, lazy no-database/no-live-provider imports, invalid reader shapes, and visible deserialization contract errors.
- The journal records that the task did not add FastAPI route wiring, a live database connection, migrations, frontend behavior, generated content, source-use policy changes, provider calls, or secret-handling changes.
- `docs/agent-journal/20260425T042223Z.md` records these checks: `python3 -m pytest tests/unit/test_retrieval_repository.py tests/unit/test_knowledge_pack_repository.py tests/unit/test_retrieval_fixtures.py tests/integration/test_backend_api.py -q` passed with 59 tests; `python3 -m pytest tests -q` passed with 225 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `docker compose config` passed.
- Remaining risks from the journal:
  - The persisted read path is intentionally injectable only; no production database reader, route wiring, or live persistence execution path was added.
  - Persisted responses reconstruct metadata-only `KnowledgePackBuildResponse` records; `cache_revalidation` is still not stored by the T-077 repository contract.

Completion commits:

- `6cfd5da feat(T-078): route retrieval through persisted packs with fixture fallback`
- `19f5169 chore(T-078): merge route retrieval through persisted packs with fixture fallback`

### T-077: Add persisted knowledge-pack repository contracts

Goal:
Add the first persisted asset knowledge-pack repository contract on top of the dormant persistence boundary, without routing any current API, retrieval, generation, chat, comparison, export, or fixture behavior through a live database.

Completed details:

- Implementation commit `141b3c4 feat(T-077): add persisted knowledge-pack repository contracts` updated `backend/repositories/knowledge_packs.py`, `backend/knowledge_pack_repository.py`, `backend/repositories/__init__.py`, `alembic/versions/20260425_0002_knowledge_pack_repository_contracts.py`, `tests/unit/test_knowledge_pack_repository.py`, and `docs/agent-journal/20260425T040950Z.md`.
- Merged branch `agent/T-077-20260425T040950Z` into `main` with local merge commit `80a318b chore(T-077): merge persisted knowledge-pack repository contracts`.
- `backend/repositories/knowledge_packs.py` added a dormant pure-Python asset knowledge-pack repository contract with explicit table definitions and row models for pack envelopes, source documents, source chunks or excerpts, normalized facts, recent developments, evidence gaps, section freshness inputs, and source checksum metadata.
- Serialization/deserialization helpers preserve supported fixture-backed `KnowledgePackBuildResponse` metadata and optional retrieval fixture details without routing runtime API, retrieval, generation, chat, comparison, export, glossary, Weekly News Focus, AI Comprehensive Analysis, or frontend behavior through a live database.
- The repository contract validates source-use and same-asset boundaries: rejected or generated-output-disallowed sources are blocked, `metadata_only` and `link_only` sources do not persist raw chunk text, and facts, recent developments, and gaps must bind to same-pack sources and chunks.
- `backend/knowledge_pack_repository.py` re-exports the repository boundary, table names, record model, contract error, and metadata helpers for future retrieval integration.
- The Alembic revision is inspectable and limited to knowledge-pack repository contract tables. The journal records that it imports without Alembic or a database connection, while running it still requires Alembic/SQLAlchemy.
- The journal records that the task did not add live database connections, ORM session execution, route wiring, ingestion persistence, generated-output cache persistence, production repository execution, or changes to current API/retrieval/generation/chat/comparison/export/glossary/frontend behavior.
- `docs/agent-journal/20260425T040950Z.md` records these checks: `python3 -m pytest tests/unit/test_knowledge_pack_repository.py tests/unit/test_repo_contract.py -q` passed with 17 tests; `python3 -m pytest tests -q` passed with 216 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `docker compose config` passed.
- Remaining risks from the journal:
  - The repository contract is intentionally dormant and in-memory/unit-tested only; no live database connection, ORM session, route wiring, ingestion persistence, generated-output cache persistence, or production repository execution path was added.
  - The migration is deterministic and inspectable, but it was not executed against a database in this task.
  - Deserialization reconstructs the knowledge-pack contract metadata; cache revalidation runtime objects remain outside the persisted contract for now.

Completion commits:

- `141b3c4 feat(T-077): add persisted knowledge-pack repository contracts`
- `80a318b chore(T-077): merge persisted knowledge-pack repository contracts`

### T-076: Add backend persistence settings and migration scaffold

Goal:
Add the backend persistence configuration and migration scaffold needed for later persisted knowledge-pack work, without routing any current API, retrieval, generation, chat, comparison, or export behavior through a live database.

Completed details:

- Implementation commit `351895f chore(T-076): add backend persistence settings and migration scaffold` updated `requirements.txt`, `.env.example`, backend API/worker env examples, backend persistence settings modules, Alembic scaffold files, `tests/unit/test_persistence_settings.py`, and `docs/agent-journal/20260425T035646Z.md`.
- Merged branch `agent/T-076-20260425T035646Z` into `main` with local merge commit `d26cc62 chore(T-076): merge backend persistence settings and migration scaffold`.
- `backend/settings.py` added `PersistenceSettings` helpers that read server-side database configuration, expose sanitized diagnostics, redact credentials and sensitive query values, and use deterministic missing-config defaults for local tests.
- `backend/db.py` added a lazy `DatabaseEngineFactory` boundary so importing the module does not import SQLAlchemy or open a database connection; engine and session creation are explicit and fail fast when `DATABASE_URL` is missing.
- `backend/persistence.py` added dormant persistence metadata with zero tables and diagnostics for the metadata boundary.
- `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, and `alembic/versions/20260425_0001_persistence_baseline.py` added an Alembic-style migration scaffold with a no-op baseline revision that can be imported without Alembic or a database connection.
- `.env.example`, `deploy/env/api.example.env`, and `deploy/env/worker.example.env` added placeholder-only database tuning variables; no frontend `NEXT_PUBLIC_*` database variables were added.
- `requirements.txt` added bounded production dependencies for SQLAlchemy, Alembic, and psycopg. The journal records the rationale: standard future engine/session abstraction, deterministic migration tooling, and PostgreSQL driver readiness once the dormant boundary is activated; alternatives considered were a custom migration runner or driver-only connection code.
- The journal records that the task did not add repository read/write behavior, migration-generated tables, ingestion persistence, cache persistence, chat persistence, route wiring, live provider calls, or a real database connection in CI.
- `docs/agent-journal/20260425T035646Z.md` records these checks: `python3 -m pytest tests/unit/test_persistence_settings.py tests/unit/test_repo_contract.py -q` passed with 20 tests; `python3 -m pytest tests -q` passed with 208 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed, including 208 tests in both Python phases plus static evals, frontend smoke, typecheck, build, and backend checks; `docker compose config` passed.
- Remaining risks from the journal:
  - The scaffold is intentionally dormant: no repository read/write layer, migration-generated tables, ingestion persistence, cache persistence, chat persistence, or route wiring was added.
  - SQLAlchemy, Alembic, and psycopg are declared as production dependencies, but this task does not install or exercise a real database connection in CI.
  - The baseline migration is a no-op; future persistence work must add real tables and repository contracts in separate, narrowly scoped tasks.

Completion commits:

- `351895f chore(T-076): add backend persistence settings and migration scaffold`
- `d26cc62 chore(T-076): merge backend persistence settings and migration scaffold`

### T-075: Re-audit home page and navigation against frontend workflow docs

Goal:
Re-audit and tighten the home page plus global navigation against the PRD/TDS Frontend Design and Workflow v0.4 baseline so the first user path remains single-stock-or-ETF search, while comparison stays separate but connected and glossary remains contextual inside reading flows.

Completed details:

- Implementation commit `09791f6 docs(T-075): re-audit home page and navigation against frontend workflow docs` updated `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, `tests/frontend/smoke.mjs`, and added `docs/agent-journal/20260425T034732Z.md`.
- Merged branch `agent/T-075-20260425T034732Z` into `main` with local merge commit `fcde6ec chore(T-075): merge re-audit home page and navigation against frontend workflow docs`.
- `apps/web/app/layout.tsx` changed the global Compare navigation entry from the default `VOO`/`QQQ` pair to the neutral `/compare` builder and added deterministic markers for the single-search/separate-compare navigation workflow.
- `apps/web/app/page.tsx` added deterministic markers for the single-asset-search-first home baseline and clarified that glossary help is contextual inside the learning flow.
- `tests/frontend/smoke.mjs` added checks for the search-first home workflow, neutral separate comparison navigation, absence of default-pair top-level navigation, and absence of a top-level glossary workflow.
- The journal records that the task did not change search resolution behavior, comparison route behavior, glossary popover behavior, backend contracts, source-use policy, deterministic fixtures, generated content, or live-provider behavior.
- `docs/agent-journal/20260425T034732Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Coverage is deterministic static smoke coverage and build/type checks; it does not include browser screenshot or interaction testing.
  - The home and navigation audit did not change search resolution behavior, comparison route behavior, glossary popover behavior, or backend contracts.

Completion commits:

- `09791f6 docs(T-075): re-audit home page and navigation against frontend workflow docs`
- `fcde6ec chore(T-075): merge re-audit home page and navigation against frontend workflow docs`

### T-074: Add route-level frontend docs-alignment smoke coverage

Goal:
Add deterministic route-level smoke coverage that checks the existing frontend routes still expose the documented Frontend Design and Workflow v0.4 structure, without changing route behavior, React component logic, backend contracts, source-backed content, or generated copy.

Completed details:

- Implementation commit `8b9e58f docs(T-074): add route-level frontend docs-alignment smoke coverage` updated `tests/frontend/smoke.mjs` and added `docs/agent-journal/20260425T033755Z.md`.
- Merged branch `agent/T-074-20260425T033755Z` into `main` with local merge commit `299d608 chore(T-074): merge route-level frontend docs-alignment smoke coverage`.
- `tests/frontend/smoke.mjs` added grouped deterministic helpers for static marker and ordering assertions.
- Smoke coverage now checks route-level v0.4 workflow markers across home/search, supported asset pages, Weekly News Focus, AI Comprehensive Analysis, source-list/source drawer, contextual glossary, asset chat, comparison, and export controls.
- The journal records that the change stayed test-only: no application routes, React components, backend contracts, deterministic fixtures, generated content, source-use policy, dependencies, or behavior were changed.
- `docs/agent-journal/20260425T033755Z.md` records these checks: `npm test` passed after one focused assertion revision; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Coverage is deterministic static smoke coverage only; it does not replace browser screenshot, viewport, or interaction testing for hover, tap, focus, drawers, bottom sheets, chat, or export controls.
  - The smoke checks depend on existing route/component markers staying meaningful and aligned with actual rendered behavior.

Completion commits:

- `8b9e58f docs(T-074): add route-level frontend docs-alignment smoke coverage`
- `299d608 chore(T-074): merge route-level frontend docs-alignment smoke coverage`

### T-073: Align global responsive spacing and no-overlap frontend layout

Goal:
Tighten shared responsive spacing and no-overlap layout rules across the existing frontend learning surfaces so the v0.4 home, asset, comparison, source drawer, glossary, chat, and export workflows remain usable on small and desktop viewports without changing routes, backend contracts, generated content, or source-backed evidence.

Completed details:

- Implementation commit `339095f feat(T-073): align global responsive spacing and no-overlap frontend layout` updated `apps/web/styles/globals.css`, `tests/frontend/smoke.mjs`, and `docs/agent-journal/20260424T221303Z.md`.
- `apps/web/styles/globals.css` tightened shared responsive rules for text wrapping, min-width containment, and max-width constraints across buttons, chips, source metadata, glossary controls, export controls, helper rails, source drawers, and comparison surfaces.
- The CSS added desktop helper-rail viewport-height containment with internal scrolling, while restoring normal in-flow behavior below the tablet breakpoint.
- The CSS added mobile scroll margins for asset regions, chat, export, source drawer, and glossary surfaces so sticky actions are less likely to obscure anchored content.
- `tests/frontend/smoke.mjs` expanded deterministic frontend smoke coverage for responsive/no-overlap CSS selectors and preservation of v0.4 surface markers.
- `docs/agent-journal/20260424T221303Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Responsive/no-overlap behavior is covered by deterministic CSS selectors, smoke checks, typecheck, and build rather than browser screenshots or device interaction testing.
  - The changes are CSS-only and do not add JavaScript-managed modal coordination between simultaneously open mobile source, glossary, chat, and export surfaces.

Completion commits:

- `339095f feat(T-073): align global responsive spacing and no-overlap frontend layout`
- `ab9bfb3 chore(T-073): merge align global responsive spacing and no-overlap frontend layout`

### T-072: Align mobile chat and export surfaces with documented helper behavior

Goal:
Align asset chat and export controls with Frontend Design and Workflow v0.4 so chat remains a helper surface in the asset learning flow and mobile users get bottom-sheet or full-screen-style behavior for chat/export interactions without changing backend contracts or generated content.

Completed details:

- Implementation commit `ac52af7 feat(T-072): align mobile chat and export surfaces with documented helper behavior` updated `apps/web/components/AssetChatPanel.tsx`, `apps/web/components/ExportControls.tsx`, `apps/web/styles/globals.css`, `tests/frontend/smoke.mjs`, and `docs/agent-journal/20260424T220036Z.md`.
- `AssetChatPanel` now exposes deterministic markers for a bounded asset-specific helper, selected-asset knowledge-pack scope, no general finance chatbot behavior, mobile bottom-sheet or full-screen-style presentation, internal scrolling, sticky asset-context helper affordance, no raw transcript analytics, advice redirects before answer content, `/compare` redirects for comparison questions, no live external calls, and in-flow no-overlap behavior.
- The chat panel wraps prompts, the form, request states, answers, citations, source metadata, session markers, and chat transcript export controls in an `asset-chat-scroll-region`; helper copy states that answers come from the selected asset knowledge pack and that transcript text is not used for product analytics.
- Chat answers now include deterministic markers for redirect-label-before-answer ordering, single-asset-only answer scope, and `/compare` routing when a comparison redirect is returned, while preserving existing advice redirects, unsupported/insufficient-evidence states, citations, source drawers, session metadata, and transcript export behavior.
- `ExportControls` now exposes deterministic markers for Markdown/JSON citation/source/freshness/disclaimer scope, compact stacked mobile behavior, in-flow no-overlap behavior, no unrestricted raw text, no restricted provider payload export, no hidden prompts, no raw model reasoning, and no secret exposure.
- Link and chat transcript export controls now expose compact full-width mobile markers and scope markers; chat transcript exports also mark no raw transcript analytics, no hidden prompts, no raw model reasoning, and internally scrollable mobile results.
- `apps/web/styles/globals.css` added shared chat/export layout rules, mobile chat bottom-sheet-style constraints with `max-height: min(82vh, 720px)`, sticky chat helper header behavior, internal chat scrolling, compact export spacing, `max-height: min(58vh, 520px)` for export results, textarea height constraints, and overflow wrapping for export buttons.
- `tests/frontend/smoke.mjs` added checks for the new chat/export helper-role markers, mobile presentation markers, no-overlap/no-live/no-raw-transcript markers, export scope and restriction markers, chat export safety markers, and responsive CSS selectors.
- `docs/agent-journal/20260424T220036Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Mobile chat and export behavior is covered by deterministic markers, responsive CSS checks, typecheck, and build rather than browser screenshot or interaction testing.
  - The chat surface remains an in-flow bottom-sheet-style panel on mobile; it does not add a JavaScript modal, route-level full-screen view, or gesture-based close behavior.

Completion commits:

- `ac52af7 feat(T-072): align mobile chat and export surfaces with documented helper behavior`
- `dbd2d29 chore(T-072): merge align mobile chat and export surfaces with documented helper behavior`

### T-071: Align comparison builder and result layouts with PRD workflow

Goal:
Align `/compare` with the PRD/TDS comparison workflow so it behaves as a separate but connected comparison surface: an empty builder when no assets are selected, a one-side-selected builder when only one asset is present, and a scan-friendly result layout when a source-backed deterministic comparison pack is available.

Completed details:

- Implementation commit `78446ea feat(T-071): align comparison builder and result layouts with PRD workflow` updated `apps/web/app/compare/page.tsx`, `apps/web/styles/globals.css`, `tests/frontend/smoke.mjs`, and `docs/agent-journal/20260424T214336Z.md`.
- `/compare` no longer silently defaults an empty request to `VOO` vs `QQQ`; query params are normalized, empty requests render an empty builder, and one-sided requests render a selected-asset builder without fetching or generating a two-asset comparison.
- The builder state includes GET form controls, selected-asset cards, deterministic example/suggestion links, freshness labels for non-generated builder output, and explicit no-generated-output/no-live-call markers.
- Available comparison results now expose deterministic PRD markers and section-order markers for header, selected assets, beginner bottom line, stock-vs-ETF relationship context when applicable, key differences, export controls, suggested comparisons, and source metadata.
- The result layout keeps stock-vs-ETF relationship context separate from generic key differences, moves the beginner bottom line before the relationship/key-difference sections, keeps export controls after key differences, and keeps suggested comparisons before source metadata.
- `apps/web/styles/globals.css` added responsive compare-builder form and selected-card styling, including mobile collapse through the existing small-screen grid rules.
- `tests/frontend/smoke.mjs` added checks that empty and one-sided builders branch before `fetchComparisonResponse`, that `VOO`/`QQQ` are no longer defaulted for empty params, that PRD section markers exist in order, and that compare-builder CSS markers are present.
- `docs/agent-journal/20260424T214336Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Responsive behavior is covered by deterministic markers, CSS checks, typecheck, and build rather than browser screenshot or interaction testing.
  - The builder inputs are simple GET form controls and rely on the existing deterministic comparison route/fallback behavior after two tickers are submitted.

Completion commits:

- `78446ea feat(T-071): align comparison builder and result layouts with PRD workflow`
- `c3deebd chore(T-071): merge align comparison builder and result layouts with PRD workflow`

### T-070: Align source-list page with PRD source inspection flow

Goal:
Align the dedicated supported asset source-list page with the PRD/TDS source inspection flow so `/assets/[ticker]/sources` is a clear, citation-first source review surface that complements the asset page without changing backend contracts, source-use policy, or generated content behavior.

Completed details:

- Implementation commit `6314b79 feat(T-070): align source-list page with PRD source inspection flow` updated `apps/web/app/assets/[ticker]/sources/page.tsx`, `apps/web/styles/globals.css`, and `tests/frontend/smoke.mjs` to align supported `/assets/[ticker]/sources` pages with the PRD source inspection flow.
- Supported source-list pages now include deterministic source-list markers, documented section order, backend-contract versus local-fixture fallback labels, source count, official/structured source count, freshness/source-use/allowlist overview, full-text export permission count, source drawer entry markers, back navigation, blocked-state copy, and an educational source-use note.
- The implementation preserved the existing source drawer adapter, same-asset source boundaries, local no-API-base fallback, citation/claim context, allowed excerpt handling, and mobile bottom-sheet source drawer behavior.
- `tests/frontend/smoke.mjs` added coverage for the supported source-list inspection flow marker, blocked or limited source-list marker, section-order marker, rendering/fallback labels, summary counts, source-use/freshness overview markers, back navigation, blocked-state copy, and CSS source-list summary rules.
- `docs/agent-journal/20260424T213305Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Responsive source-list behavior is covered by deterministic markers and CSS checks, not browser screenshot or interaction testing.
  - The full-text export summary depends on the existing source drawer contract or fixture fields; local fixtures without explicit permission fields report zero permitted full-text exports.

Completion commits:

- `6314b79 feat(T-070): align source-list page with PRD source inspection flow`
- `5e6f797 chore(T-070): merge align source-list page with PRD source inspection flow`

### T-069: Align supported asset-page layout with PRD learning flow

Goal:
Align the supported stock and ETF asset-page layout with the PRD/proposal learning-page flow so the page order, desktop helper rail, and mobile action surfaces match the documented user experience without changing backend contracts or source-backed content behavior.

Completed details:

- Implementation commit `0ace5fd feat(T-069): align supported asset-page layout with PRD learning flow` updated `apps/web/app/assets/[ticker]/page.tsx`, `apps/web/components/AssetHeader.tsx`, `apps/web/components/AssetModeLayout.tsx`, and `apps/web/styles/globals.css` to add deterministic PRD layout markers and make the supported asset-page learning flow explicit.
- Supported asset pages now render the documented sequence for Beginner Summary, Top 3 Risks, Key Facts, What It Does/What It Holds, Weekly News Focus, AI Comprehensive Analysis, Deep Dive, Ask, Sources, and the educational framing section.
- Source drawers were moved into a Sources section after chat; the page now includes a desktop helper rail for ask/compare/freshness/source access and mobile in-flow sticky actions for Ask, Compare, and Sources.
- Existing backend adapters, deterministic fixtures, citations, source drawers, glossary context, export controls, Weekly News Focus evidence-limited states, AI Comprehensive Analysis suppression, comparison suggestions, and chat behavior were kept intact.
- `tests/frontend/smoke.mjs` added coverage for the PRD layout marker, section-order marker, section-specific markers, helper rail source access, beginner stable/recent separation, and mobile action/layout markers.
- `docs/agent-journal/20260424T211700Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Responsive behavior is covered by deterministic markers and CSS smoke checks, not browser screenshot or interaction testing.
  - The helper rail uses anchor links and source titles for access context; it does not duplicate full source drawer content outside the Sources section.

Completion commits:

- `0ace5fd feat(T-069): align supported asset-page layout with PRD learning flow`
- `380ef31 chore(T-069): merge align supported asset-page layout with PRD learning flow`

### T-068: Tighten Weekly News Focus evidence-limited states

Goal:
Make Weekly News Focus contract and UI behavior explicit when the selected evidence set is smaller than the configured maximum or empty, so the product never pads timely context with weak items and AI Comprehensive Analysis stays suppressed unless enough approved evidence exists.

Completed details:

- Implementation commit `6a37299 feat(T-068): tighten Weekly News Focus evidence-limited states` added deterministic Weekly News Focus metadata for configured maximum item count, selected item count, suppressed candidate count, evidence state, and evidence-limited state across `backend/models.py`, `backend/weekly_news.py`, and `backend/overview.py`.
- `apps/web/lib/assetWeeklyNews.ts`, `apps/web/lib/fixtures.ts`, `apps/web/components/WeeklyNewsPanel.tsx`, and `apps/web/components/AIComprehensiveAnalysisPanel.tsx` now carry/render frontend markers for limited verified sets, empty `no_high_signal` states, selected-vs-configured counts, suppressed candidate counts, and AI Comprehensive Analysis threshold availability or suppression.
- The backend and frontend changes preserve the evidence-limited Weekly News Focus rule: show fewer items when only a smaller verified set passes selection, show explicit empty states when no high-signal evidence exists, and keep AI Comprehensive Analysis suppressed unless at least two approved Weekly News Focus items exist.
- `tests/unit/test_weekly_news.py`, `tests/unit/test_overview_generation.py`, `tests/integration/test_backend_api.py`, `tests/frontend/smoke.mjs`, `evals/weekly_news_eval_cases.yaml`, and `evals/run_static_evals.py` added coverage for configured-vs-selected counts, limited/empty states, AI analysis threshold metadata, and deterministic UI/eval markers.
- `docs/agent-journal/20260424T200434Z.md` records these checks: `git status --short` passed; `python3 -m pytest tests/unit/test_weekly_news.py tests/unit/test_overview_generation.py tests/unit/test_safety_guardrails.py -q` passed with 27 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 33 tests; `python3 evals/run_static_evals.py` passed; `npm test` passed; `npm run typecheck` initially failed because `.next/types` had not been generated while `npm run build` was running in parallel, then passed after build completed; `npm run build` passed; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Frontend coverage remains deterministic marker/smoke based; no browser screenshot or interaction run was added.
  - Local frontend fixtures still provide a QQQ available-but-limited example, while backend deterministic pack fixtures currently evaluate QQQ as no-high-signal.
  - Suppressed candidate count is aggregate metadata and does not expose per-candidate rejection details in the public response.

Completion commits:

- `6a37299 feat(T-068): tighten Weekly News Focus evidence-limited states`
- `3b73c80 chore(T-068): merge tighten Weekly News Focus evidence-limited states`

### T-067: Add stock-vs-ETF comparison relationship badges

Goal:
Align the comparison page with Frontend Design and Workflow v0.4 for stock-vs-ETF pairs by adding deterministic relationship badges and a special single-company-vs-ETF-basket comparison structure.

Completed details:

- Implementation commit `230400b feat(T-067): add stock-vs-ETF comparison relationship badges` updated `apps/web/lib/compare.ts` with deterministic stock-vs-ETF comparison data for the local `AAPL` vs `VOO` pack, including the `stock-etf-relationship-v1` model, stock ticker, ETF ticker, relationship state, evidence state, badge data, basket-structure data, same-pack citations, and source documents.
- `apps/web/app/compare/page.tsx` now renders a stock-vs-ETF relationship section for `comparison_type === "stock_vs_etf"`, including relationship badges, single-company and ETF-basket panels, verified holding membership copy, partial-overlap/unavailable detail, citation chips, and deterministic `data-*` markers.
- `apps/web/lib/compareSuggestions.ts` now includes `AAPL`/`VOO` as a local comparison pair only when the deterministic source-backed pack is available, with stock-vs-ETF-specific suggestion copy.
- `apps/web/styles/globals.css` added relationship-badge and single-company-vs-ETF-basket styling, and `tests/frontend/smoke.mjs` added marker coverage for stock-vs-ETF schema, ticker markers, relationship/evidence states, same-pack AAPL/VOO citations, unavailable overlap detail, and the allowed local suggestion pairs.
- `docs/agent-journal/20260424T195049Z.md` records these checks: `git status --short` passed; `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Stock-vs-ETF coverage is intentionally limited to the deterministic `AAPL` vs `VOO` local comparison pack.
  - Relationship badge smoke coverage checks deterministic markers and source boundaries, not browser-rendered screenshots.
  - Exact holding weight, top-10 concentration, sector exposure, and full overlap remain unavailable and are labeled as partial evidence.

Completion commits:

- `230400b feat(T-067): add stock-vs-ETF comparison relationship badges`
- `1b9aa8c chore(T-067): merge stock-vs-ETF comparison relationship badges`

### T-066: Align contextual glossary popovers and mobile sheets with v0.4

Goal:
Align contextual glossary help with Frontend Design and Workflow v0.4 so glossary terms remain inline reading aids on desktop and open as mobile bottom-sheet-style cards where appropriate.

Completed details:

- Implementation commit `ce91962 feat(T-066): align contextual glossary popovers and mobile sheets with v0.4` updated `apps/web/components/GlossaryPopover.tsx` with shared interaction behavior for hover preview, click-to-pin/toggle, keyboard focus, Escape close, and an explicit close control.
- The same component update added deterministic `data-*` markers for desktop interaction mode, mobile bottom-sheet presentation, close control, visible term context, and internal scroll readiness.
- `apps/web/styles/globals.css` added responsive mobile glossary rules so glossary cards render as fixed bottom-sheet-style panels with constrained height, sticky term/close header, and internal scrolling.
- Existing curated generic definitions, backend asset-context overlays, citation/source metadata, evidence/freshness states, generic-only fallback labels, and trust-metric readiness markers were preserved.
- `tests/frontend/smoke.mjs` added smoke coverage for glossary desktop behavior markers and mobile bottom-sheet CSS markers.
- `docs/agent-journal/20260424T193948Z.md` records these checks: `git status --short` passed; `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - The mobile glossary sheet is CSS/state based and does not add drag gestures or a backdrop.
  - Smoke coverage verifies deterministic markers and CSS rules; it does not browser-test hover, focus, tap, and Escape interaction sequences.

Completion commits:

- `ce91962 feat(T-066): align contextual glossary popovers and mobile sheets with v0.4`
- `05d4090 chore(T-066): merge align contextual glossary popovers and mobile sheets with v0.4`

### T-065: Add mobile source drawer bottom-sheet behavior

Goal:
Align source inspection with Frontend Design and Workflow v0.4 so source drawers remain usable on desktop and open as mobile bottom-sheet-style panels for citation/source access.

Completed details:

- Implementation commit `b2be252 feat(T-065): add mobile source drawer bottom-sheet behavior` updated `apps/web/components/SourceDrawer.tsx` with deterministic `data-source-drawer-mobile-presentation="bottom-sheet"`, `data-source-drawer-close-control="native-details-summary"`, and `data-source-title` markers while leaving citation chip anchors unchanged.
- The same component update changed the native `<summary>` label from a generic source-drawer label to a two-line summary with `source-summary-kicker` and `source-summary-title`, so the source title remains visible when users collapse or reopen the drawer.
- `apps/web/styles/globals.css` added mobile-only source drawer rules under `@media (max-width: 620px)`, including `max-height: min(76vh, 640px)`, rounded top corners, upward sheet-style shadow, sticky summary context, internal source-body scrolling, and `overscroll-behavior: contain`.
- `tests/frontend/smoke.mjs` added smoke coverage for the bottom-sheet marker, native details-summary close marker, source title summary class, mobile media query, constrained height, internal scroll behavior, and source-title styling.
- `docs/agent-journal/20260424T193152Z.md` records these checks: `git status --short` passed with a clean initial worktree and only intended task files changed; `npm test` passed; `npm run typecheck` failed once because `.next/types` were not present while build was running, then passed after `npm run build`; `npm run build` passed; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - The mobile source drawer uses responsive CSS and native `<details>` behavior rather than a JavaScript-managed modal sheet; this preserves keyboard behavior and same-page citation anchors but does not add gesture-based drag controls.
  - The drawer remains rendered in page flow on mobile to avoid overlapping page content; it is bottom-sheet-style through constrained height, rounded top corners, shadow, sticky summary context, and internal scrolling.

Completion commits:

- `b2be252 feat(T-065): add mobile source drawer bottom-sheet behavior`
- `74f80a8 chore(T-065): merge mobile source drawer bottom-sheet behavior`

### T-064: Align home search with frontend workflow v0.4

Goal:
Align the home page and search/autocomplete experience with Frontend Design and Workflow v0.4 so the first screen has one primary action: search for a single supported stock or ETF.

Completed details:

- Implementation commit `5e5464a feat(T-064): align home search with frontend workflow v0.4` updated `apps/web/app/page.tsx` with the v0.4 headline `Understand a stock or ETF in plain English`, the required supporting copy, and secondary workflow cards that keep single-asset search primary while linking comparison separately.
- `apps/web/components/SearchBox.tsx` now uses the required placeholder `Search a ticker or name, like VOO, QQQ, or Apple`, labels example chips `VOO`, `QQQ`, `AAPL`, `NVDA`, and `SOXX` as examples only and not recommendations, shows v0.4 support-state chips, and keeps supported results routed to `/assets/[ticker]`.
- `apps/web/lib/search.ts` added deterministic clear `A vs B` / `A versus B` ticker-pattern detection that returns a `comparison_route` search result for `/compare?left=...&right=...` without turning the home page into a comparison builder.
- Recognized unsupported copy now uses `We found this ticker, but it is not supported in v1.`, the supported-scope reminder names U.S.-listed common stocks and non-leveraged U.S.-listed equity ETFs, and unknown/no-match searches show `No supported stock or ETF found for "{query}".` plus a no-invented-facts note.
- `apps/web/styles/globals.css` added styling for the updated home workflow cards, support-state legend, and example chip row; `tests/frontend/smoke.mjs` added smoke coverage for the v0.4 home copy, primary-action marker, separate comparison markers, comparison-route search result, support-state labels, unsupported copy, and no-result copy.
- `docs/agent-journal/20260424T191708Z.md` records these checks: `npm test` failed once on a smoke regex for the literal `/compare?left=` route marker, then passed; `npm run typecheck` failed once because a temporary `comparison` search asset type widened the compare contract type, then passed after keeping comparison as a search state/route only; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - The comparison-query detector is intentionally simple and deterministic; it handles clear ticker-style `A vs B` and `A versus B` patterns, while broader natural-language comparison phrasing remains out of scope for this task.
  - Search remains fixture-backed and local; partial, stale, and unavailable states are exposed as labels, but this task did not add new data fixtures for those states.

Completion commits:

- `5e5464a feat(T-064): align home search with frontend workflow v0.4`
- `40fc840 chore(T-064): merge align home search with frontend workflow v0.4`

### T-063: Surface backend trust-metric validation readiness in frontend control surfaces

Goal:
Expose deterministic frontend markers and lightweight adapter validation for the existing backend trust-metric catalog/validation contracts so citation, source drawer, glossary, comparison, export, and safety redirect surfaces remain ready for aggregate metrics without logging raw chat transcript content, adding real analytics, or weakening citation, source-use, freshness, uncertainty, and advice-boundary rules.

Completed details:

- Implementation commit `49e7caa feat(T-063): surface backend trust-metric validation readiness in frontend control surfaces` added `apps/web/lib/trustMetrics.ts` with `trust-metrics-event-v1`, validation-only mode, deterministic timestamp default `1970-01-01T00:00:00Z`, no persistence, no external analytics, no live external calls, required product events, required trust events, compact surface descriptor construction, and lightweight catalog-response validation.
- `apps/web/components/SourceDrawer.tsx`, `apps/web/components/GlossaryPopover.tsx`, `apps/web/components/ComparisonSuggestions.tsx`, `apps/web/app/compare/page.tsx`, `apps/web/components/ExportControls.tsx`, and `apps/web/components/AssetChatPanel.tsx` now expose deterministic `data-*` trust-metric readiness markers for source drawer usage, glossary usage, comparison usage, export usage, chat answer outcomes, chat safety redirects, citation coverage, freshness accuracy, and safety redirect rate.
- The frontend markers use compact metadata such as workflow area, selected section, asset ticker/support state, comparison tickers/state, export content type/format, citation count, source document count, freshness state, evidence state, safety classification, and chat outcome; they do not add analytics emission, backend persistence, browser storage, cookies, live provider calls, or raw transcript/content fields.
- Chat and safety redirect surfaces now label trust-metric readiness for `chat_answer_outcome`, `chat_safety_redirect`, and `safety_redirect_rate` while preserving advice redirects, comparison redirects, unsupported/insufficient-evidence behavior, accountless session handling, and no raw question/answer analytics.
- `tests/frontend/smoke.mjs` now checks the trust-metrics helper constants/catalog validation shape and the frontend marker coverage for source drawer, glossary, comparison, export, citation/freshness, chat answer, and safety redirect surfaces.
- `docs/agent-journal/20260424T173249Z.md` records these checks: `npm test` pass; `npm run typecheck` pass; `npm run build` pass; `python3 -m pytest tests/unit/test_trust_metrics.py tests/integration/test_backend_api.py tests/unit/test_safety_guardrails.py -q` pass with 52 tests; `python3 evals/run_static_evals.py` pass; `bash scripts/run_quality_gate.sh` pass, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Frontend trust-metric readiness remains marker-only and pure-helper validation only; it does not fetch the backend catalog or emit validation events.
  - The helper validates the required T-032 catalog shape at a lightweight frontend level, so future backend catalog expansion may need a matching descriptor update.
  - Markers intentionally expose only compact counts and state labels; they are not a substitute for backend trust-metric validation or storage if real analytics are added later.

Completion commits:

- `49e7caa feat(T-063): surface backend trust-metric validation readiness in frontend control surfaces`
- `5467c4a chore(T-063): merge surface backend trust-metric validation readiness in frontend control surfaces`

### T-062: Align accountless chat export controls with session export contracts

Goal:
Improve the chat export path so supported accountless chat exports can use the existing session export contract when a conversation ID exists, while preserving the current single-turn transcript export fallback, advice redirects, compare redirects, 7-day TTL/deleted-session states, source-use rights, and no raw transcript analytics assumptions.

Completed details:

- Implementation commit `1cb064d feat(T-062): align accountless chat export controls with session export contracts` extended `apps/web/lib/assetChat.ts` with `ChatSessionMetadata`, the `chat-session-contract-v1` session shape, broader support-state typing, `compare_route_redirect` classification, and optional `conversation_id` submission through the existing relative `/api/assets/{ticker}/chat` helper.
- `apps/web/lib/exportControls.ts` now attempts a session-backed `POST /api/assets/{ticker}/chat/export` request when an active conversation ID exists, validates available Markdown `chat_transcript` exports against same-asset or no-factual-evidence bindings, `export-validation-v1`, `export_licensing_scope`, `local_accountless_chat_session`, safe session turn records, `used_existing_chat_contract`, no-new-facts, and no-live-call diagnostics, then falls back to the existing single-turn transcript export path when the session contract is unavailable or invalid.
- `apps/web/components/AssetChatPanel.tsx` now keeps active accountless session metadata in component state for the current interaction, reuses the active conversation ID on follow-up chat calls, renders deterministic chat-session contract markers, passes exportable session metadata to `ExportControls`, and labels comparison workflow redirects separately from advice redirects.
- `apps/web/components/ExportControls.tsx` now renders deterministic chat export markers for `session_contract` versus `single_turn_fallback`, conversation ID presence, lifecycle state, export availability, expiration, validation schema, binding scope, citation/source counts, safe session records, existing chat contract use, and no-live-call diagnostics.
- `tests/frontend/smoke.mjs` now checks chat session markers, session export markers, conversation ID handling, `chat_transcript`, `session_contract`, `single_turn_fallback`, `local_accountless_chat_session`, `used_existing_chat_contract`, `no_factual_evidence`, and safe session turn record markers.
- `docs/agent-journal/20260424T171652Z.md` records these checks: `npm test` failed once on an outdated smoke marker and then passed after a focused marker update; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests -q` passed with 197 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed.
- Remaining risks from the journal:
  - Chat session continuity is held only in component state for the current interaction; no browser persistence was added.
  - Session-backed export validation is frontend-side contract validation over the existing backend response, so backend chat export schema expansion may require a matching frontend adapter update.
  - When a session export is unavailable or invalid, the control intentionally falls back to the existing single-turn transcript export path and labels it as `single_turn_fallback`.

Completion commits:

- `1cb064d feat(T-062): align accountless chat export controls with session export contracts`
- `c67e379 chore(T-062): merge align accountless chat export controls with session export contracts`

### T-061: Align comparison export controls with backend comparison export contracts

Goal:
Reduce comparison-page export drift by making comparison export controls prefer the existing backend comparison export contract when available, while preserving deterministic `VOO` vs `QQQ` fixture fallback, same-comparison-pack citation boundaries, blocked-state behavior, and no-live-call guardrails.

Completed details:

- Implementation commit `83e30db feat(T-061): align comparison export controls with backend comparison export contracts` extended `apps/web/lib/exportControls.ts` with `fetchSupportedComparisonExportContract`, a shared API-base export endpoint helper, same-comparison-pack Markdown export validation for `/api/compare/export?left_ticker={LEFT}&right_ticker={RIGHT}&export_format=markdown`, and comparison freshness/as-of extraction from export validation sections or source metadata.
- The adapter accepts comparison export payloads only when they are available Markdown comparison exports for the requested left/right supported tickers with educational disclaimer text, `export_licensing_scope`, rendered Markdown, `export-validation-v1`, `same_comparison_pack` binding scope, citation/source/section validation metadata, `same_comparison_pack_*` diagnostics, `used_existing_comparison_contract`, no-live-call diagnostics, no-new-facts diagnostics, allowed exportable source-use policy, and allowed source metadata.
- `apps/web/app/compare/page.tsx` now attempts backend comparison export validation only for already available source-backed local comparison packs, passes the validated contract into `ExportControls`, and preserves the existing relative Markdown export link and local fallback helper copy when validation is unavailable or invalid.
- `apps/web/components/ExportControls.tsx` now exposes comparison contract markers for link exports, including backend/local rendering, validation schema, binding scope, export state, freshness/as-of values, citation/source counts, left/right ticker, and comparison ID while keeping relative Markdown links as the baseline.
- `tests/frontend/smoke.mjs` now checks comparison export adapter markers, same-comparison-pack diagnostics, comparison export route usage, and UI contract markers.
- `docs/agent-journal/20260424T170401Z.md` records these checks: `npm test` pass; `npm run typecheck` failed once on nullable backend comparison export fields, then passed after explicit narrowing; `npm run build` pass; `python3 -m pytest tests -q` pass with 197 tests; `python3 evals/run_static_evals.py` pass; `bash scripts/run_quality_gate.sh` pass.
- Remaining risks from the journal:
  - Comparison export contract validation only runs when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise comparison export controls intentionally show `local_fallback` while preserving the relative Markdown export link.
  - The comparison page only attempts backend export validation for already available local comparison packs, so unavailable, unsupported, out-of-scope, eligible-not-cached, no-local-pack, unknown, and blocked states continue to hide export controls.

Completion commits:

- `83e30db feat(T-061): align comparison export controls with backend comparison export contracts`
- `6a5b96c chore(T-061): merge align comparison export controls with backend comparison export contracts`

### T-060: Align asset-page export controls with backend export contracts

Goal:
Reduce remaining asset-page export drift by validating backend asset-page and source-list export payload availability from existing deterministic export routes while preserving safe Markdown-only links, licensing notes, citation/freshness metadata expectations, and fallback behavior when no API base URL is configured.

Completed details:

- Implementation commit `c677892 feat(T-060): align asset-page export controls with backend export contracts` extended `apps/web/lib/exportControls.ts` with `fetchSupportedAssetExportContract`, `AssetExportContractValidation`, and same-asset Markdown export validation for `/api/assets/{ticker}/export?export_format=markdown` and `/api/assets/{ticker}/sources/export?export_format=markdown`.
- The adapter accepts only supported available Markdown exports with same-asset identity, educational disclaimer text, `export_licensing_scope`, citation/source metadata, freshness or as-of metadata, `export-validation-v1`, `same_asset` binding scope, allowed exportable source-use policy, no-live-call diagnostics, and existing-overview/no-new-facts diagnostics.
- `apps/web/app/assets/[ticker]/page.tsx` now fetches the asset-page and source-list export contracts independently for supported asset pages, records `data-asset-page-export-contract` and `data-asset-source-list-export-contract`, and preserves local fallback rendering when a backend response is unavailable, invalid, blocked, unsupported, non-Markdown, or no API base URL is configured.
- `apps/web/components/ExportControls.tsx` now renders export contract markers for link controls, including `backend_contract` or `local_fallback`, schema, binding scope, export state, freshness, as-of date, citation count, and source count, while keeping relative Markdown links as the baseline.
- `tests/frontend/smoke.mjs` now checks the asset export adapter routes, contract markers, validation diagnostics, licensing/disclaimer context, and no new live external URL usage.
- `docs/agent-journal/20260424T165234Z.md` records these checks: `npm test` pass; `npm run typecheck` pass after a focused type-narrowing fix; `npm run build` pass; `python3 -m pytest tests -q` pass with 197 tests; `python3 evals/run_static_evals.py` pass; `bash scripts/run_quality_gate.sh` pass.
- Remaining risks from the journal:
  - Backend export contract validation only runs when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise asset-page controls intentionally show `local_fallback` while keeping the relative Markdown links.
  - Asset-page and source-list export validations fall back independently if either backend response is unavailable, blocked, unsupported, non-Markdown, or contract-invalid.

Completion commits:

- `c677892 feat(T-060): align asset-page export controls with backend export contracts`
- `2bfe273 chore(T-060): merge align asset-page export controls with backend export contracts`

### T-059: Fetch supported glossary context from backend glossary contracts

Goal:
Reduce remaining supported asset-page glossary drift by consuming the existing backend glossary asset-context contract when it is available, while preserving curated generic glossary definitions, deterministic fallback rendering, same-asset citation boundaries, and current blocked/no-live-call guardrails.

Completed details:

- Implementation commit `e2a5aa7 feat(T-059): fetch supported glossary context from backend glossary contracts` added `apps/web/lib/assetGlossary.ts`, a deterministic frontend adapter for `/api/assets/{ticker}/glossary` that validates the `glossary-asset-context-v1` schema, supported same-asset identity, no-live-call diagnostics, generic-definitions-not-evidence diagnostics, same-asset evidence boundaries, and restricted-text suppression before returning usable glossary context.
- The adapter filters backend glossary terms to terms already rendered in the asset-page glossary groups, skips generic-only entries, requires same-asset allowed citation bindings for cited context, maps allowed `summary_allowed` or `full_text_allowed` source references, and keeps explicit uncertainty labels or suppression reasons when citations are absent.
- `apps/web/app/assets/[ticker]/page.tsx` now fetches backend glossary context independently after the existing overview/details/weekly-news/source-drawer fetches, passes available term context into `GlossaryPopover`, records `data-asset-glossary-rendering`, and preserves deterministic static glossary fallback when the backend response is unavailable, invalid, filtered to no usable rendered terms, or no API base URL is configured.
- `apps/web/components/GlossaryPopover.tsx` keeps curated generic definitions visible while adding optional asset-context state, evidence state, freshness state, citation IDs, uncertainty labels, source-reference metadata, suppression reasons, and generic-only labels inside glossary cards.
- `tests/frontend/smoke.mjs` now checks glossary backend-context markers, asset citation/source/uncertainty markers, the injectable asset-glossary fetch helper, and no new live external URL usage.
- `docs/agent-journal/20260424T164150Z.md` records these passing checks: `npm test`; `npm run typecheck`; `npm run build`; `python3 -m pytest tests/integration/test_backend_api.py -q`; `python3 evals/run_static_evals.py`; `bash scripts/run_quality_gate.sh`.
- Remaining risks from the journal:
  - Supported asset pages only use backend glossary context when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise they intentionally keep the deterministic static glossary path.
  - The frontend adapter overlays backend context only for terms already rendered in the asset-page glossary groups, with generic-only and unusable backend records falling back to curated definitions.

Completion commits:

- `e2a5aa7 feat(T-059): fetch supported glossary context from backend glossary contracts`
- `0a3a782 chore(T-059): merge fetch supported glossary context from backend glossary contracts`

### T-058: Align asset-page source drawer contexts with backend source metadata contracts

Goal:
Reduce remaining supported asset-page source drawer drift by preferring the existing backend source-drawer contract for related claim context, section references, and allowed excerpts when it is available, while preserving deterministic fallback rendering, same-asset citation boundaries, and current blocked/no-live-call guardrails.

Completed details:

- Implementation commit `be3527b feat(T-058): align asset-page source drawer contexts with backend source metadata contracts` updated the supported asset page to overlay backend `/api/assets/{ticker}/sources` entries onto already-rendered source drawers by `source_document_id` when the response matches the existing deterministic `asset-source-drawer-v1` contract.
- `apps/web/lib/sourceDrawer.ts` now exposes a small source-record mapping helper that lets the asset page reuse backend related claims, section references, and allowed excerpts without changing backend routes or source-use policy.
- `apps/web/app/assets/[ticker]/page.tsx` preserves independent deterministic fallback rendering when the backend source-drawer response is unavailable, invalid, missing a rendered source document ID, or no API base URL is configured.
- `tests/frontend/smoke.mjs` now checks the supported asset-page source-drawer backend overlay markers.
- `docs/agent-journal/20260424T025701Z.md` records these passing checks: `npm test`; `npm run typecheck`; `npm run build`; `python3 evals/run_static_evals.py`; `python3 -m pytest tests/integration/test_backend_api.py -q`; `bash scripts/run_quality_gate.sh`.
- Remaining risks from the journal:
  - Supported asset pages still intentionally stay on deterministic local fixture drawer rendering when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is not configured.
  - The asset page now overlays backend source-drawer entries per rendered `source_document_id`, but any supported page source not present in the backend `/sources` response still falls back to the existing local claim-context path for this cycle.

Completion commits:

- `6d29283 chore(T-058): prepare align asset-page source drawer contexts with backend source metadata contracts task`
- `be3527b feat(T-058): align asset-page source drawer contexts with backend source metadata contracts`
- `1f978dc chore(T-058): merge align asset-page source drawer contexts with backend source metadata contracts`

### T-057: Fetch supported asset detail and recent-context sections from backend contracts

Goal:
Reduce remaining frontend fixture drift on supported asset pages by consuming the existing backend detail and weekly-news contracts for Deep-Dive sections and timely-context rendering when they are available, while preserving deterministic fallback rendering, stable-vs-timely separation, and current blocked/no-live-call guardrails.

Completed details:

- Implementation commit `66adeec feat(T-057): fetch supported asset detail and recent-context sections from backend contracts` added `apps/web/lib/assetDetails.ts` to validate supported `/api/assets/{ticker}/details` payloads and merge backend stock `business_model` and `diversification_context` plus ETF `role`, `holdings`, and `cost_context` fields, refreshed citations, and updated freshness dates into the existing deterministic asset fixture shape.
- The same commit added `apps/web/lib/assetWeeklyNews.ts` to validate `weekly-news-focus-v1` and `ai-comprehensive-analysis-v1` responses from `/api/assets/{ticker}/weekly-news`, then map backend weekly-news windows, items, citations, source documents, analysis sections, suppression state, and source-document bindings into the existing Weekly News Focus and AI Comprehensive Analysis fixture shape while preserving no-live-call and stable-facts-separate behavior.
- `apps/web/app/assets/[ticker]/page.tsx` now prefers backend overview, details, and weekly-news fetches independently for supported assets, records `data-asset-overview-rendering`, `data-asset-details-rendering`, and `data-asset-weekly-news-rendering`, and preserves deterministic local fallback whenever any response is unavailable or invalid.
- `tests/frontend/smoke.mjs` now checks the asset detail and weekly-news adapter markers, including required `/details` and `/weekly-news` route strings and the page-level rendering markers.
- `docs/agent-journal/20260424T022200Z.md` records these checks: `npm test` pass; `npm run typecheck` fail on first run, then pass after one focused type fix; `npm run build` pass; `python3 evals/run_static_evals.py` pass; `python3 -m pytest tests/integration/test_backend_api.py -q` pass; `bash scripts/run_quality_gate.sh` pass.
- Remaining risks from the journal:
  - Supported asset pages only attempt backend detail and weekly-news fetches when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise they intentionally stay on the deterministic local fixture path.
  - The `/api/assets/{ticker}/details` contract is narrower than the existing deep-dive fixture sections, so this cycle overlays backend-backed stock and ETF detail fields onto the current section structure instead of replacing every section with a fully backend-native shape.
  - Weekly News Focus and AI Comprehensive Analysis now prefer the backend wrapper contract, but the deep-dive `recent_developments` fixture section remains unchanged in this cycle.

Completion commits:

- `ceb9c3a chore(T-057): prepare fetch supported asset detail and recent-context sections from backend contracts task`
- `66adeec feat(T-057): fetch supported asset detail and recent-context sections from backend contracts`
- `3ba8925 chore(T-057): merge fetch supported asset detail and recent-context sections from backend contracts`

### T-056: Fetch supported asset overview pages from backend overview contracts

Goal:
Reduce frontend fixture drift on supported asset pages by consuming the existing backend overview contract for stable beginner-overview content when it is available, while preserving deterministic fallback rendering and current blocked/no-live-call guardrails.

Completed details:

- Implementation commit `c5fab18 feat(T-056): fetch supported asset overview pages from backend overview contracts` added `apps/web/lib/assetOverview.ts` as a deterministic frontend adapter for `/api/assets/{ticker}/overview`, validating supported stock and ETF overview payloads and merging backend asset identity, freshness, beginner summary, top risks, suitability summary, claims, citations, and source documents into the existing asset fixture shape.
- `apps/web/app/assets/[ticker]/page.tsx` now attempts the backend overview fetch for supported assets, records whether overview rendering came from `backend_contract` or `local_fixture`, and preserves the existing local deterministic fallback when the response is unavailable, invalid, or the API base URL is not configured.
- `tests/frontend/smoke.mjs` now checks the overview adapter markers, including the overview fetch helper, backend-rendering marker, and required overview route strings.
- `docs/agent-journal/20260424T015016Z.md` records these passing checks: `npm test`, `npm run typecheck`, `npm run build`, `python3 -m pytest tests/integration/test_backend_api.py -q`, and `bash scripts/run_quality_gate.sh`.
- Remaining risks from the journal:
  - Supported asset pages only attempt the backend overview fetch when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise they intentionally fall back to the deterministic local fixture path.
  - This cycle only backend-aligns stable overview identity, freshness, beginner summary, top risks, suitability, citations, and source metadata; the stable fact list, citation contexts, and deep-dive sections remain on the deterministic local adapter path until later tasks expand the contract usage.

Completion commits:

- `cf9d665 chore(T-056): prepare fetch supported asset overview pages from backend overview contracts task`
- `c5fab18 feat(T-056): fetch supported asset overview pages from backend overview contracts`
- `bca802b chore(T-056): merge fetch supported asset overview pages from backend overview contracts`

### T-055: Fetch supported source-list pages from backend source-drawer contracts

Goal:
Reduce frontend fixture drift on supported source-list pages by consuming the existing backend source-drawer contract when it is available, while preserving deterministic blocked-state behavior and safe fallback rendering.

Completed details:

- Implementation commit `4faa192 feat(T-055): fetch supported source-list pages from backend source-drawer contracts` added `apps/web/lib/sourceDrawer.ts` as a deterministic frontend adapter for `/api/assets/{ticker}/sources`, validating the backend `asset-source-drawer-v1` payload and mapping `source_groups`, `citation_bindings`, `related_claims`, `section_references`, and `allowed_excerpts` into the existing `SourceDrawer` render shape.
- `apps/web/app/assets/[ticker]/sources/page.tsx` now attempts the backend source-drawer fetch for supported assets, records whether rendering came from `backend_contract` or `local_fixture`, and preserves the existing local deterministic fallback when the response is unavailable, invalid, or the API base URL is not configured.
- `apps/web/components/SourceDrawer.tsx` was updated to accept backend-mapped excerpt notes and to render a safe empty-excerpt message when supporting passages are unavailable for the current drawer state.
- `tests/frontend/smoke.mjs` now checks the new source-list rendering markers and confirms the source-drawer adapter route and contract markers are present.
- `docs/agent-journal/20260424T012006Z.md` records these passing checks: `npm test`, `npm run typecheck`, `npm run build`, `python3 -m pytest tests/integration/test_backend_api.py -q`, and `bash scripts/run_quality_gate.sh`.
- Remaining risks from the journal:
  - Supported source-list pages only attempt the backend source-drawer fetch when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise they intentionally fall back to the deterministic local fixture path.
  - The frontend maps backend `related_claims` plus `allowed_excerpts` into the existing `SourceDrawer` context shape, so future backend contract expansion beyond the validated fields will need a matching adapter update.

Completion commits:

- `ab9f117 chore(T-055): prepare fetch supported source-list pages from backend source-drawer contracts task`
- `4faa192 feat(T-055): fetch supported source-list pages from backend source-drawer contracts`
- `c833638 chore(T-055): merge fetch supported source-list pages from backend source-drawer contracts`

### T-054: Align unsupported and unavailable source-list empty states with backend support-state contracts

Goal:
Align unsupported and unavailable source-list rendering and empty states with backend support-state contracts so blocked and non-blocked source routes behave deterministically and safely.

Task-scope paragraph:
Updated the source-list route and shared source-list helpers to map backend-aligned support-state classes onto source-list and source-empty UI behavior for unsupported, out-of-scope, unknown, unavailable, stale, partial, eligible-not-cached, and insufficient-evidence cases while preserving existing supported-asset metadata behavior and non-advice educational framing.

Completed details:

- Branch commit `6436893 feat(T-054): align unsupported and unavailable source-list empty states with backend support-state contracts` added/updated:
  - `apps/web/app/assets/[ticker]/sources/page.tsx` with deterministic support-state handling for source-list and source-empty behavior.
  - `apps/web/components/SourceDrawer.tsx` to export a shared support-state mapping helper.
  - `tests/frontend/smoke.mjs` with source-list presence and state-marker coverage.
- Local commit/merge evidence `18a8dc1 chore(T-054): merge align unsupported and unavailable source-list empty states with backend support-state contracts` includes the completed branch merge and a quality-gate pass note.
- `docs/agent-journal/20260423T224910Z.md` records:
  - `npm test` pass
  - `npm run typecheck` pass
  - `npm run build` pass
  - `python3 evals/run_static_evals.py` pass
  - `bash scripts/run_quality_gate.sh` pass
- Remaining risks:
  - Source-list supported-state rendering remains fixture-only.
  - Support-state derivation uses local search contracts and must be updated when those contracts change.

Completion commits:

- `6436893 feat(T-054): align unsupported and unavailable source-list empty states with backend support-state contracts`
- `18a8dc1 chore(T-054): merge align unsupported and unavailable source-list empty states with backend support-state contracts`

### T-053: Replace compare-page fixture-only routing with backend-aligned deterministic comparison adapters

Goal:
Align the compare route to backend comparison-contract inputs while preserving existing deterministic behavior and blocked-state safety.

Completed details:

- `apps/web/lib/compare.ts` and `apps/web/app/compare/page.tsx` use backend-aligned comparison contract inputs when available and keep deterministic fixture fallback behavior.
- `fetchComparisonResponse` and response shape validation were already in use in the compare flow, with fallback to local comparison fixtures when backend responses are unavailable or invalid.
- Contract-aware smoke assertions in `tests/frontend/smoke.mjs` cover compare-route behavior.
- Journal evidence at `docs/agent-journal/20260423T223353Z.md` confirms `npm test`, `npm run typecheck`, `npm run build`, and `bash scripts/run_quality_gate.sh` passed.
- Journal evidence at `docs/agent-journal/20260423T221625Z.md` confirms the same command set and documents remaining risks around backend contract fallback.
- This task was completed through branch `agent/T-053-20260423T223353Z` and merged with commit `ea385d4`.

Completion commits:

- `ea385d4` (local merge commit on branch `agent/T-053-20260423T223353Z`)


### T-052: Align home search UI with backend support-classification and blocked-state contracts

Goal:
Align the home search UX with existing backend support-classification contract states so supported, ambiguous, eligible-not-cached, recognized-unsupported, out-of-scope, and unknown search outcomes render deterministically and clearly, while preserving blocked-copy messaging, no-generated-page behavior, and educational framing.

Completed details:

- Implementation branch commit `97a3a99 feat(T-052): align home search UI with backend support-classification and blocked-state contracts` changed comparison data flow to prefer backend `/api/compare` results with deterministic fallback through local fixtures, and added runtime comparison payload validation in `apps/web/lib/compare.ts`.
- `apps/web/app/compare/page.tsx` now calls an async comparison fetch path with fallback to `getComparePageFixture` when backend fetch or payload validation fails.
- `apps/web/lib/compare.ts` now includes `fetchComparisonResponse`, `CompareRequest`, and a runtime payload guard that checks for expected backend comparison fields before rendering.
- `tests/frontend/smoke.mjs` assertions now verify that compare fixtures and routing flow are contract-aware instead of fixture-only, including `/api/compare` usage.
- Completion evidence includes a local merge commit `24cbd87 chore(T-052): merge align home search UI with backend support-classification and blocked-state contracts`.
- Journal evidence at `docs/agent-journal/20260423T221625Z.md` reports `npm test`, `npm run typecheck`, `npm run build`, and `bash scripts/run_quality_gate.sh` as passing for the branch.
- There is no separate `T-052`-specific journal content in this workspace; the existing timestamped journal file is present but labeled as `Task T-053`.

Completion commits:

- `97a3a99 feat(T-052): align home search UI with backend support-classification and blocked-state contracts`
- `dc501e3 chore(T-052): prepare align home search UI with backend support-classification and blocked-state contracts`
- `24cbd87 chore(T-052): merge align home search UI with backend support-classification and blocked-state contracts`

### T-051: Render Weekly News Focus and AI Comprehensive Analysis on supported asset pages

Goal:
Render Weekly News Focus and AI Comprehensive Analysis for supported assets using the existing deterministic contract shape on asset pages, while keeping both modules visually and semantically separate from stable canonical facts and preserving unknown/stale/partial evidence handling.

Completed:

- Updated `apps/web/app/assets/[ticker]/page.tsx`, `apps/web/components/WeeklyNewsPanel.tsx`, and `apps/web/components/AIComprehensiveAnalysisPanel.tsx` to render deterministic timely-context contract fields for supported assets only.
- Kept timely context separation from stable facts in the page flow and preserved no-advice educational framing and uncertainty labels in fallback states.
- Left backend contracts, provider wiring, and live data paths unchanged; implementation remained deterministic and fixture-backed.
- Task completed after one focused iteration following an initial typecheck pass.

Verification:

- `npm test` — pass
- `npm run typecheck` — fail then pass after focused typefix
- `npm run build` — pass
- `python3 evals/run_static_evals.py` — pass
- `bash scripts/run_quality_gate.sh` — pass

Remaining risks:

- `SourceDrawer` state mapping still treats unrecognized freshness states as `unknown`.
- AI Comprehensive Analysis renders only when `analysisAvailable` and section data exist; suppressed/empty states are textual by design.

Completion commits:

- `07f3729` chore(T-051): prepare render Weekly News Focus and AI Comprehensive Analysis on supported asset pages
- `328d08c` feat(T-051): render Weekly News Focus and AI Comprehensive Analysis on supported asset pages
- `81993ca` chore(T-051): merge render Weekly News Focus and AI Comprehensive Analysis on supported asset pages

### T-050: Align asset-page source drawer and freshness labels with backend contracts

Goal:
Align all asset-page source-drawer and freshness-label rendering with existing backend contract shapes so source metadata, freshness states, and uncertainty labels remain consistent across supported, blocked, and unavailable asset flows, while staying deterministic and education-first.

Completed:

- Updated `apps/web/app/assets/[ticker]/page.tsx`, `apps/web/components/FreshnessLabel.tsx`, and `apps/web/components/SourceDrawer.tsx` to consume deterministic contract-shaped fields for source metadata and freshness rendering.
- Fixed an initial typecheck issue by switching `SourceDrawer` to normalized contract fields (`supportingPassage`, `isOfficial`) instead of non-existent snake_case aliases.
- Kept existing blocked/unsupported/unknown/unavailable support-state behavior intact while preserving citation and uncertainty boundaries.
- No backend or live-provider changes were introduced in this frontend-contract alignment task.

Acceptance criteria:

- `SourceDrawer` and freshness chips render backend-contracted state labels (`fresh`, `stale`, `unknown`, `unavailable`, `partial`, `insufficient_evidence`) consistently for available/blocked/unavailable rows.
- `SourceDrawer` uses normalized contract fields for source metadata and freshness, preserving existing blocked-state semantics and citation access behavior.
- The updated asset-page path contains deterministic, contract-backed source/freshness behavior with no additional scope changes.
- Required checks passed, and the task was marked as pass after one revision (initial typecheck failure was corrected and re-ran).

Verification:

- `npm test`
- `npm run typecheck`
- `npm run build`
- `python3 -m pytest tests -q`
- `python3 evals/run_static_evals.py`
- `bash scripts/run_quality_gate.sh`

Remaining risks:

- `SourceDrawer` currently supports blocked-state rendering via `drawerState`, but the local fixture route continues to pass `available` for rendered source rows.
- Freshness label copy is tested through smoke-path checks without dedicated unit assertions for exact copy variants.

Completion commits:

- `8b81fae924b105182e0c515fa6f425d460eae8ea` feat(T-050): align asset-page source drawer and freshness labels with backend contracts
- `1fb6af6b8f25784f174f452c5242436d53acf8f0` chore(T-050): merge align asset-page source drawer and freshness labels with backend contracts

### T-049: Reduce frontend fixture drift by introducing shared deterministic view adapters


### T-049: Reduce frontend fixture drift by introducing shared deterministic view adapters

Goal:
Reduce frontend fixture drift by using one shared deterministic adapter path for local search, comparison, and source/freshness rendering, replacing duplicated fixture-only derivation in page components.

Completed:

- Added a shared frontend adapter module and rewired the local search/compare path to consume adapter-shaped outputs for support-state, source metadata, and freshness labels.
- Updated `apps/web/components/SearchBox.tsx`, `apps/web/components/ComparisonSourceDetails.tsx`, `apps/web/components/SourceDrawer.tsx`, and `apps/web/components/FreshnessLabel.tsx` rendering to use adapter-shaped labels/metadata instead of local ad hoc derivation.
- Updated `tests/frontend/smoke.mjs` to assert shared-adapter marker behavior and deterministic render paths.
- Added `apps/web/lib/viewAdapters.ts` as the adapter entrypoint used by `apps/web/lib/search.ts` and `apps/web/lib/compare.ts`.
- No unsupported or advisory-style outputs were added; blocked/unsupported/unknown states preserve existing deterministic guardrails.
- Remaining documented risk: compare-page availability copy in `app/compare/page.tsx` remains page-local, while support-state and source-metadata shaping is now centralized.
- A required journal entry was referenced as [docs/agent-journal/20260423T201841Z.md], but that file is not present in this workspace.

Verification:

- `python3 -m pytest tests -q`
- `npm test`
- `npm run typecheck`
- `npm run build`
- `python3 evals/run_static_evals.py`
- `bash scripts/run_quality_gate.sh`

Completion commits:

- `4a1091360017e16a421fa71f7a5e6affb88dcd16 feat(T-049): reduce frontend fixture drift by introducing shared deterministic view adapters`
- `9c602cc4fae2f4e1bf759e0cd95dea021e726d51 chore(T-049): merge reduce frontend fixture drift by introducing shared deterministic view adapters task`

### T-048: Replace compare-page fixture logic with backend-aligned deterministic comparison contracts

Goal:
Align the deterministic compare page with the existing backend comparison contract so supported and unavailable comparison states render from backend-aligned response shapes instead of compare-page-only fixture logic, without introducing live calls, new comparison packs, or advice-like copy.

Completed:

- Refactored the compare-page data path around backend-aligned deterministic comparison shaping in `apps/web/lib/compare.ts`, then updated `apps/web/app/compare/page.tsx` and `apps/web/components/ComparisonSourceDetails.tsx` to consume that local contract instead of compare-page-only fixture fields.
- Updated compare UI gating so unsupported or unavailable comparison states do not imply supported generated output, while `apps/web/components/ComparisonSuggestions.tsx` and `apps/web/lib/compareSuggestions.ts` stay aligned with the current deterministic comparison availability flow.
- Extended `tests/frontend/smoke.mjs` for compare-route rendering markers and state gating, and recorded the run in `docs/agent-journal/20260423T194410Z.md`.
- The T-048 agent journal records that these commands passed:
  - `python3 -m pytest tests/unit/test_comparison_generation.py tests/integration/test_backend_api.py -q`
  - `npm test`
  - `npm run typecheck`
  - `npm run build`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
- Merged local branch: `agent/T-048-20260423T194410Z`.
- Remaining documented risk: the compare page now mirrors the backend comparison contract shape and availability taxonomy locally, but it is still deterministic fixture-backed only and does not fetch `/api/compare`.
- Remaining documented risk: available comparison evidence details remain implemented only for the current local `VOO`/`QQQ` pack and its reverse order; future local packs will need matching contract data to preserve parity.

Completion commits:

- `402fddd feat(T-048): replace compare-page fixture logic with backend-aligned deterministic comparison contracts`
- `c6e5740 chore(T-048): merge replace compare-page fixture logic with backend-aligned deterministic comparison contracts`

### T-047: Align home search UI with backend support-classification states

Goal:
Align the deterministic home search UI with the existing backend search support-classification contract so beginners see clear, state-correct results for supported, ambiguous, eligible-not-cached, recognized-unsupported, out-of-scope, and unknown searches without introducing live calls, new asset coverage, or advice-like copy.

Completed:

- Added `apps/web/lib/search.ts` as a compare-independent local search contract module with backend-aligned support-classification types, blocked-explanation metadata, deterministic candidate sets, and resolution helpers for `cached_supported`, `eligible_not_cached`, `recognized_unsupported`, `out_of_scope`, and `unknown` search states.
- Updated `apps/web/components/SearchBox.tsx` to render state-specific result panels for supported, ambiguous, ingestion-needed, unsupported, out-of-scope, and unknown searches, including generated-page gating via `can_open_generated_page`, disambiguation requirements for multi-result searches, and explicit no-invented-facts handling for unknown queries.
- Updated `apps/web/app/page.tsx` home-page copy and example cards so the visible search examples match the backend-aligned state taxonomy, including ambiguous, ingestion-needed, unsupported, out-of-scope, and unknown examples.
- Extended `tests/frontend/smoke.mjs` to assert the new home-search state markers, result gating markers, blocked-state messaging, ingestion-needed messaging, and unknown-search no-invented-facts copy.
- Added `docs/agent-journal/20260423T191509Z.md` documenting the changed files, commands run, pass/fail status, and remaining risks.
- The agent journal records that these commands passed:
  - `npm run typecheck`
  - `npm test`
  - `npm run build`
  - `python3 -m pytest tests -q`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
- Merged local branch: `agent/T-047-20260423T191509Z`.
- Remaining documented risk: the home search contract is still duplicated in frontend-local deterministic fixtures, so future backend search-candidate or copy changes will need a matching frontend update to keep parity.
- Remaining documented risk: search disambiguation now reflects backend support states and routing gates, but it remains fixture-backed only and does not add live API fetching or broader entity-resolution coverage beyond the local contract examples.

Completion commits:

- `0b2a651 feat(T-047): align home search UI with backend support-classification states`
- `de95739 chore(T-047): merge align home search UI with backend support-classification states`

### T-046: Render Weekly News Focus and AI analysis on asset pages

Goal:
Render the existing deterministic Weekly News Focus and AI Comprehensive Analysis contract on supported frontend asset pages so the UI matches the PRD/TDS separation between stable facts and timely context without introducing live calls, new assets, or advice-like copy.

Completed:

- Added dedicated frontend timely-context components in `apps/web/components/WeeklyNewsPanel.tsx` and `apps/web/components/AIComprehensiveAnalysisPanel.tsx`, with explicit Weekly News Focus state markers, source quality and source-use metadata, and AI Comprehensive Analysis section ordering for `What Changed This Week`, `Market Context`, `Business/Fund Context`, and `Risk Context`.
- Updated `apps/web/app/assets/[ticker]/page.tsx` to render those modules separately from stable facts and to wire the deterministic timely-context fixture helpers already referenced by the asset-page scaffold.
- Expanded `apps/web/lib/fixtures.ts` with deterministic Weekly News Focus and AI Comprehensive Analysis fixture data and state handling used by supported asset pages, while keeping the implementation fixture-backed and local only.
- Extended `tests/frontend/smoke.mjs` to assert the new timely-context rendering markers, including Weekly News Focus visibility, AI analysis state handling, and the required separation from stable facts.
- Added `docs/agent-journal/20260423T183709Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- The agent journal records that these commands passed:
  - `npm test`
  - `npm run typecheck`
  - `npm run build`
  - `python3 -m pytest tests/unit/test_repo_contract.py -q`
  - `bash scripts/run_quality_gate.sh`
- Remaining documented risk: Weekly News Focus and AI Comprehensive Analysis remain deterministic fixture-backed frontend rendering only; no live provider or backend-fetch integration was added.
- Remaining documented risk: the available-analysis path is exercised by local `QQQ` fixture context, while `VOO` and `AAPL` intentionally remain in empty or suppressed analysis states.
- Remaining documented risk: weekly-context source drawers reuse asset citation contexts when available and otherwise fall back to timely-context claim labels instead of richer per-citation weekly context records.

Completion commits:

- `d42cc82 feat(T-046): render Weekly News Focus and AI analysis on asset pages`
- `4dd683c chore(T-046): merge render Weekly News Focus and AI analysis on asset pages`

### T-045: Add grounded chat comparison-redirect contract

Goal:
Add a deterministic grounded chat comparison-redirect contract so single-asset chat can detect second-ticker comparison questions and return a compare-workflow suggestion backed by existing local comparison availability states instead of generating a multi-asset answer inside the single-asset endpoint, without adding frontend UI, live calls, new facts, new comparison pairs, or weakening citation, source-use, freshness, unknown/stale/unavailable/partial, and safety rules.

Completed:

- Added additive grounded-chat redirect models in `backend/models.py`, including `ChatCompareRouteDiagnostics` and `ChatCompareRouteSuggestion`, plus `compare_route_suggestion` support on `ChatResponse`, `ChatTurnRecord`, and `ChatSessionTurnSummary`.
- Updated `backend/chat.py` so second-ticker questions in single-asset chat detect the ordered comparison pair from the submitted question, call the existing deterministic comparison pipeline, reuse `comparison.evidence_availability.availability_state`, and return `compare_route_redirect` workflow guidance with ordered `/compare?left=...&right=...` metadata instead of a multi-asset factual answer.
- Preserved grounding and safety boundaries by returning empty chat citations and source documents for redirect-only turns, keeping advice redirects higher priority than comparison convenience, and reusing existing local availability states for `available`, `no_local_pack`, `eligible_not_cached`, `unsupported`, `out_of_scope`, and `unknown` comparison cases covered by local fixtures.
- Updated `backend/chat_sessions.py` and `backend/export.py` so compare redirects persist through session turn records, session status, and transcript export, including `comparison_redirect` and `comparison_redirects` export sections plus `no_factual_evidence` validation without fabricated comparison evidence.
- Extended `evals/run_static_evals.py`, `tests/unit/test_chat_generation.py`, `tests/unit/test_chat_sessions.py`, `tests/unit/test_exports.py`, `tests/unit/test_safety_guardrails.py`, and `tests/integration/test_backend_api.py` for redirect schema coverage, second-ticker detection, ordered route metadata, supported and unavailable comparison states, advice-precedence behavior, session/export propagation, and no mixed-asset citation or source-document leakage.
- Added `docs/agent-journal/20260423T163224Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- The agent journal records that these commands passed:
  - `python3 -m pytest tests/unit/test_chat_generation.py tests/unit/test_chat_sessions.py tests/unit/test_exports.py tests/unit/test_safety_guardrails.py -q`
  - `python3 -m pytest tests/integration/test_backend_api.py -q`
  - `python3 -m pytest tests -q`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
- Merged local branch: `agent/T-045-20260423T163224Z`.
- Remaining documented risk: second-ticker detection is intentionally narrow and ticker-token-based; it handles the deterministic comparison question patterns covered by local fixtures without expanding into broader name/entity resolution.
- Remaining documented risk: comparison redirects reuse current local comparison availability only and do not expose comparison facts, so future fixture changes need to preserve the same availability-state meanings and route-order expectations.

Completion commits:

- `09b0c7d feat(T-045): add grounded chat comparison-redirect contract`
- `5551f0e chore(T-045): merge grounded chat comparison-redirect contract`

### T-044: Add export source-use and freshness validation contract

Goal:
Add a deterministic export source-use and freshness validation contract so backend and UI clients can tell whether each available export payload's freshness labels, as-of dates, allowed excerpts, and source-use permissions are supported by the existing same-asset or same-comparison-pack evidence already present in the export, without adding frontend UI, live calls, new facts, new assets, or weakening citation, source-use, unknown/stale/unavailable/partial, and safety rules.

Completed:

- Added export validation contract models in `backend/models.py`, including `ExportValidationOutcome`, `ExportValidationBindingScope`, `ExportValidationCitationBinding`, `ExportValidationSourceBinding`, `ExportValidationDiagnostics`, `ExportValidation`, and additive `export_validation` support on `ExportResponse`.
- Extended `backend/export.py` so asset-page, source-list, comparison, and chat transcript exports serialize deterministic `export-validation-v1` metadata with section validations, same-asset and same-comparison-pack binding checks, no-factual-evidence handling for advice redirects, limitation messaging, and diagnostics derived from existing overview/comparison/chat contracts only.
- Preserved existing export payload behavior while validating current evidence boundaries, including the stale-with-limitations `VOO` `cost_trading_context` export path instead of promoting it to a cleaner freshness state.
- Added `evals/export_eval_cases.yaml` and extended `evals/run_static_evals.py` for supported `AAPL`, `VOO`, and `QQQ` export cases, `VOO` freshness-limitation preservation, comparison-pack-only bindings for `VOO`/`QQQ` in both directions, advice-redirect chat exports with `no_factual_evidence`, blocked-state handling, and no live-call or secret-exposure regressions.
- Extended `tests/unit/test_exports.py` and `tests/integration/test_backend_api.py` for asset-page, source-list, comparison, grounded-chat, advice-redirect chat, and blocked export serialization, binding-scope coverage, and deterministic diagnostics.
- Added `docs/agent-journal/20260423T155943Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- The agent journal records that these commands passed:
  - `python3 -m pytest tests/unit/test_exports.py tests/unit/test_safety_guardrails.py -q`
  - `python3 -m pytest tests/integration/test_backend_api.py -q`
  - `python3 -m pytest tests -q`
  - `npm test`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
- Merged local branch: `agent/T-044-20260423T155943Z`.
- Remaining documented risk: the export validation contract is deterministic and fixture-backed only; it validates existing export citations, freshness labels, source-use rights, and blocked states without adding live evidence, new facts, or new export routes.
- Remaining documented risk: asset-page freshness preservation relies on the current overview freshness-validation contract for matched overview sections and export-local metadata for export-only sections, so future fixture changes need to preserve the same same-asset binding assumptions.
- Remaining documented risk: comparison export validation stays limited to the current local comparison packs and prevents non-pack bindings by diagnostics and tests; future comparison fixtures will need to preserve the same comparison-pack-only guarantees.

Completion commits:

- `4866c0a feat(T-044): add export source-use and freshness validation contract`
- `ec7f295 chore(T-044): merge export source-use and freshness validation contract`

### T-043: Add section-level freshness validation contract

Goal:
Add a deterministic section-level freshness validation contract so backend and UI clients can tell whether each generated overview section's displayed freshness label is supported by the selected asset's existing same-asset evidence, dates, and knowledge-pack freshness inputs, without adding frontend UI, live calls, new facts, new assets, or weakening citation, source-use, unknown/stale/unavailable/partial, and safety rules.

Completed:

- Added additive overview freshness-validation models in `backend/models.py`, including `OverviewSectionFreshnessValidationOutcome`, `OverviewSectionFreshnessCitationBinding`, `OverviewSectionFreshnessSourceBinding`, `OverviewSectionFreshnessDiagnostics`, and `OverviewSectionFreshnessValidation`, plus `section_freshness_validation` on `OverviewResponse`.
- Extended `backend/overview.py` so generated supported overviews now build deterministic section freshness validation records for overview sections, `weekly_news_focus`, and `ai_comprehensive_analysis` by reusing existing same-asset citations, source documents, and knowledge-pack section freshness inputs.
- Kept validation evidence-bound by recording displayed vs validated freshness/as-of metadata, same-asset citation/source bindings, matched knowledge-pack section IDs, missing-binding diagnostics, and mismatch reasons when a displayed label is not supported by the existing local evidence.
- Preserved non-generated routing by returning no section freshness validation records for unsupported or unknown assets, and preserved existing stale/limited states such as `VOO` `cost_trading_context` instead of promoting them to `fresh`.
- Extended `evals/run_static_evals.py` for required freshness-validation models/helpers, route behavior, same-asset binding, stale/unknown/unavailable handling, no live-call imports, and advice-boundary checks.
- Extended `tests/unit/test_overview_generation.py` and `tests/integration/test_backend_api.py` for supported stock and ETF serialization, same-asset binding coverage, recent-context separation, stale `VOO` cost/trading validation, mismatch detection, and blocked-state behavior.
- Added `docs/agent-journal/20260423T152949Z.md` documenting the changed files, commands run, pass/fail status, and remaining risks.
- The agent journal records that these commands passed:
  - `python3 -m pytest tests/unit/test_cache_contracts.py tests/unit/test_overview_generation.py tests/unit/test_safety_guardrails.py -q`
  - `python3 -m pytest tests/integration/test_backend_api.py -q`
  - `python3 -m pytest tests -q`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
- Merged local branch: `agent/T-043-20260423T152949Z`.
- Remaining documented risk: the section freshness validation contract is deterministic and fixture-backed only; it validates existing overview freshness labels and bindings but does not add live freshness sources, new facts, or new assets.
- Remaining documented risk: Weekly News Focus and AI Comprehensive Analysis validation currently reflects the existing local no-high-signal and insufficient-evidence fixture states; future timely-context fixtures must preserve the same same-asset binding and mismatch checks.

Completion commits:

- `a55fe1f feat(T-043): add section-level freshness validation contract`
- `bdcc9c8 chore(T-043): merge section-level freshness validation contract`

### T-042: Add unsupported asset search explanation contract

Goal:
Add a deterministic unsupported-asset search explanation contract so search clients can show a clear structured explanation for recognized unsupported and out-of-scope search matches, including why the asset is blocked, which capabilities stay disabled, and what the supported MVP scope is, without adding frontend UI, live calls, new asset coverage, or weakening classification, citation, source-use, freshness, unknown/unavailable/partial, and safety rules.

Completed:

- Added additive blocked-search explanation contract models in `backend/models.py`, including `SearchBlockedCapabilityFlags`, `SearchBlockedExplanationDiagnostics`, and `SearchBlockedExplanation`, plus `blocked_explanation` fields on `SearchResult` and `SearchState`.
- Updated `backend/search.py` so single-result recognized unsupported and out-of-scope matches attach deterministic `search-blocked-explanation-v1` metadata with explanation category, scope rationale, supported-v1 scope reminder, blocked capability flags, and no-ingestion diagnostics while preserving existing supported, ambiguous, eligible-not-cached, and unknown behavior.
- Kept blocked explanations scope-bound and non-analytical by deriving them from existing deterministic unsupported-category metadata and Top-500 manifest-backed out-of-scope stock handling rather than adding citations, source text, freshness claims, or new asset facts.
- Added `evals/search_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required models/helpers, blocked explanation coverage for unsupported and out-of-scope results, preservation of unknown and eligible-not-cached behavior, no live-call imports, and no forbidden advice language.
- Extended `tests/unit/test_search_classification.py`, `tests/unit/test_safety_guardrails.py`, and `tests/integration/test_backend_api.py` for blocked explanation serialization, API coverage, supported/ambiguous/eligible-not-cached preservation, and safety checks.
- Added `docs/agent-journal/20260423T150352Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-042 agent journal records that focused search/safety pytest passed with 19 tests, backend API pytest passed with 30 tests, full Python pytest passed with 190 tests, `npm test` passed with frontend smoke checks, static evals passed, and the full quality gate passed.
- Merged local branch: `agent/T-042-20260423T150352Z`.
- Remaining documented risk: the blocked search explanation is deterministic product-state metadata only; it does not add citations, freshness, source text, live calls, or any new asset coverage.
- Remaining documented risk: the contract currently covers recognized unsupported assets and manifest-backed out-of-scope stocks in local fixtures; future broader search datasets will need to preserve the same blocked-capability and no-advice guarantees.

Completion commits:

- `bcef2b4 feat(T-042): add unsupported asset search explanation contract`
- `bc75dce chore(T-042): merge unsupported asset search explanation contract`

### T-041: Add glossary asset-context evidence contract

Goal:
Add a deterministic backend glossary asset-context evidence contract so UI clients can request beginner glossary terms for a selected asset and see which optional asset-specific glossary context is source-backed, generic-only, unavailable, stale, partial, or suppressed without adding frontend UI, live calls, new facts, generated unsupported content, or weakening citation, source-use, freshness, unknown/unavailable/partial, and safety rules.

Completed:

- Added `backend/glossary.py` with a deterministic `glossary-asset-context-v1` response builder, a backend-owned curated term catalog, and asset-aware term coverage for stock terms such as `market cap`, `revenue`, `operating margin`, `EPS`, `free cash flow`, `debt`, `P/E ratio`, and `forward P/E`, plus ETF terms such as `expense ratio`, `AUM`, `benchmark`, `holdings`, `tracking error`, and `tracking difference`.
- Added glossary response and asset-context contract models in `backend/models.py` so term identity, generic definition fields, asset-context availability state, evidence metadata, and diagnostics serialize through a stable backend schema.
- Wired `GET /api/assets/{ticker}/glossary` in `backend/main.py` with optional `term` filtering.
- Implemented deterministic generic-only and source-backed glossary behavior in `backend/glossary.py`, including same-asset citation/source binding, preserved unavailable or insufficient-evidence states, and non-generated states for `eligible_not_cached`, `unsupported`, `out_of_scope`, and `unknown` assets.
- Added `evals/glossary_context_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required glossary models/helpers, curated term coverage, same-asset citation/source binding, generic-only behavior, non-generated blocked states, no restricted text exposure, no live-call imports, and no forbidden advice language.
- Added `tests/unit/test_glossary_context.py` and updated retrieval, citation, safety, and backend API coverage in `tests/unit/test_retrieval_fixtures.py`, `tests/unit/test_citation_validation.py`, `tests/unit/test_safety_guardrails.py`, and `tests/integration/test_backend_api.py` for supported `AAPL`, `VOO`, and `QQQ` glossary serialization, optional term filtering, generic-only terms, and blocked states for `SPY`, `TQQQ`, `GME`, and `ZZZZ`.
- Added `docs/agent-journal/20260423T143641Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-041 agent journal records that focused glossary/retrieval/citation/safety pytest passed with 36 tests, backend API pytest passed with 30 tests, full Python pytest passed with 189 tests, static evals passed, `npm test` and `npm run typecheck` passed, and the full quality gate passed.
- Merged local branch: `agent/T-041-20260423T143641Z`.
- Remaining documented risk: glossary asset-context is deterministic and fixture-backed only; it does not add live ingestion, scraping, persistence, frontend rendering, or new asset facts.
- Remaining documented risk: asset-specific glossary context exposes evidence metadata and bindings, not new explanatory prose or raw source passages.
- Remaining documented risk: future persisted glossary context will need to preserve the same same-asset citation/source binding and source-use policy checks.

Completion commits:

- `b61747e feat(T-041): add glossary asset-context evidence contract`
- `046b05f chore(T-041): merge glossary asset-context evidence contract`

### T-040: Add comparison evidence availability contract

Goal:
Add a deterministic backend comparison evidence availability contract so comparison UI clients can tell which comparison dimensions are source-backed, partial, stale, unavailable, or suppressed for each side of a comparison without adding frontend UI, making live calls, generating unsupported comparisons, or weakening citation, source-use, freshness, unknown/unavailable/partial, and safety rules.

Completed:

- Added comparison evidence availability contract models in `backend/models.py`, including availability states, side roles, diagnostics, source references, evidence items, dimensions, citation bindings, claim bindings, and the top-level `ComparisonEvidenceAvailability`.
- Extended `CompareResponse` with additive `evidence_availability` metadata while preserving the existing `left_asset`, `right_asset`, `state`, `comparison_type`, `key_differences`, `bottom_line_for_beginners`, `citations`, and `source_documents` response shape.
- Added deterministic availability helpers in `backend/comparison.py`, including required comparison dimensions for `Benchmark`, `Expense ratio`, `Holdings count`, `Breadth`, and `Educational role`.
- Supported existing local `VOO` vs `QQQ` and `QQQ` vs `VOO` comparison packs with `available` metadata, per-side evidence roles, dimension-to-citation/source mappings, claim bindings, source references, freshness/source-use metadata, and no-live-call/no-new-generated-output diagnostics.
- Added explicit non-generated evidence availability states for unsupported, out-of-scope, unknown, eligible-not-cached, no-local-pack, unavailable-style comparisons, with no generated key differences, beginner bottom line, citations, source documents, claim support, or live calls.
- Preserved same-comparison-pack citation/source binding by requiring availability citation bindings to reference citations and source documents already present in the selected `CompareResponse`.
- Preserved source-use policy by resolving source permissions and only marking allowed, citation-supporting, generated-output-supporting sources as supporting generated comparison claims; restricted text is not newly exposed.
- Added `evals/comparison_evidence_eval_cases.yaml` and extended `evals/run_static_evals.py` for required models/helpers, supported and non-generated states, required dimensions, citation/source binding, source-use/freshness handling, no restricted markers, no live-call imports, and no forbidden advice language.
- Extended `tests/unit/test_comparison_generation.py` and `tests/integration/test_backend_api.py` for supported availability serialization, reverse ticker order, per-side roles, dimension and claim bindings, non-generated states for `BTC`, `TQQQ`, `GME`, `SPY`, `ZZZZ`, and `AAPL`/`VOO`, and API serialization.
- Added `docs/agent-journal/20260423T140420Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-040 agent journal records that focused comparison/citation/safety pytest passed with 26 tests, backend API pytest passed with 29 tests, full Python pytest passed with 178 tests, static evals passed, and the full quality gate passed.
- Merged local branch: `agent/T-040-20260423T140420Z`.
- Remaining documented risk: the comparison evidence availability contract is deterministic and fixture-backed only; it does not add live ingestion, scraping, provider calls, persistence, frontend rendering, or new comparison pairs.
- Remaining documented risk: stale, partial, unavailable, and insufficient-evidence states are modeled in the contract for deterministic response shaping, but current local comparison fixtures only exercise available and non-generated unavailable-style routes.
- Remaining documented risk: future persisted comparison packs will need to preserve the same same-pack citation/source binding rules and source-use policy fields.

Completion commits:

- `7b305ea feat(T-040): add comparison evidence availability contract`
- `58c5f63 chore(T-040): merge comparison evidence availability contract`

### T-039: Add asset source drawer response contract

Goal:
Add a deterministic backend asset source drawer response contract so UI clients can open a source drawer for an asset or citation and receive source metadata, related claim context, freshness, source-use rights, and allowed excerpts without exposing restricted raw text, adding frontend UI, making live calls, or weakening citation, source-use, freshness, unknown/unavailable/partial, and safety rules.

Completed:

- Added source drawer contract models in `backend/models.py`, including `SourceDrawerState`, `SourceDrawerExcerpt`, `SourceDrawerRelatedClaim`, `SourceDrawerSectionReference`, `SourceDrawerCitationBinding`, `SourceDrawerSourceGroup`, and `SourceDrawerDiagnostics`.
- Extended `SourcesResponse` with additive source drawer fields while preserving the legacy `asset`, `state`, and `sources` response shape.
- Added `backend/sources.py` with `build_asset_source_drawer_response`, deterministic `asset-source-drawer-v1` shaping, and explicit non-generated responses for unavailable asset states.
- Built source drawer related-claim and section-reference context from existing overview claims, snapshot metrics, top risks, PRD overview sections, Weekly News Focus items, and AI Comprehensive Analysis sections when present.
- Built citation bindings from existing overview citations and asset knowledge-pack facts, chunks, and recent-development evidence, with same-asset source document checks and evidence-layer labels for canonical facts, source chunks, and timely context.
- Built source groups from existing overview and knowledge-pack source documents with source type, title, publisher, URL, published/as-of/retrieved dates, freshness, official-source flag, source quality, allowlist status, source-use policy, permitted operations, citation IDs, related claim IDs, section IDs, allowed excerpts, and excerpt-suppression reasons.
- Added deterministic filtering for `citation_id` and `source_document_id`, including diagnostics for applied filters and omitted citation/source IDs.
- Gated source drawer excerpts through the existing source-use policy resolver so `full_text_allowed` and `summary_allowed` sources can expose short allowed fixture passages while restricted policies suppress source text with explicit suppression reasons.
- Wired `GET /api/assets/{ticker}/sources` in `backend/main.py` to return the new source drawer contract and accept optional `citation_id` and `source_document_id` query filters.
- Added `evals/source_drawer_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required models/helpers/routes, supported cached assets, non-generated cases, same-asset source/citation binding, source-use/freshness handling, no restricted markers, no live-call imports, and no forbidden advice language.
- Added `tests/unit/test_source_drawer.py` plus API coverage in `tests/integration/test_backend_api.py` for supported `AAPL`, `VOO`, and `QQQ` source drawer serialization, citation/source filtering, related-claim mapping, source-use excerpt behavior, and non-generated `SPY`, `TQQQ`, `GME`, and `ZZZZ` states.
- Added `docs/agent-journal/20260423T133237Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-039 agent journal records that focused source-drawer pytest passed with 4 tests, focused source-drawer/citation/safety pytest passed with 21 tests, backend API pytest passed with 29 tests, full Python pytest passed with 178 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-039-20260423T133237Z`.
- Remaining documented risk: the source drawer contract is deterministic and fixture-backed only; it does not add live ingestion, persistence, scraping, source allowlist changes, or frontend rendering.
- Remaining documented risk: the contract groups and filters source drawer metadata from existing asset overviews and knowledge packs only, so future persisted claim/source tables may need an adapter to preserve the same response shape.
- Remaining documented risk: non-generated states return explicit empty drawer payloads, but richer deleted/stale/partial production states will still depend on future storage and ingestion lifecycle work.

Completion commits:

- `f84ddcc feat(T-039): add asset source drawer response contract`
- `94943ba chore(T-039): merge asset source drawer response contract`

### T-038: Add accountless chat session lifecycle contract

Goal:
Add a deterministic accountless chat session lifecycle contract so grounded chat can issue anonymous conversation IDs, record safe turn metadata, expose TTL/delete/session status, and support transcript export without adding user accounts, persistent storage, raw transcript analytics, live LLM/provider calls, or weakening citation, source-use, freshness, unknown/unavailable/partial, and safety rules.

Completed:

- Added `backend/chat_sessions.py` with a deterministic in-memory `ChatSessionStore`, injectable clock and ID generator, `CHAT_SESSION_TTL_DAYS = 7`, `CHAT_SESSION_TTL_SECONDS = 604800`, opaque deterministic UUID-style conversation IDs, active/expired/deleted/ticker-mismatch/unavailable lifecycle handling, idempotent deletion, and safe export payload helpers.
- Added chat session lifecycle models in `backend/models.py`, including `ChatSessionLifecycleState`, `ChatSessionDeletionStatus`, `ChatTurnRecord`, `ChatSessionTurnSummary`, `ChatSessionPublicMetadata`, `ChatSessionStatusResponse`, and `ChatSessionDeleteResponse`.
- Extended chat request/response contracts so `ChatRequest` accepts optional `conversation_id` and `ChatResponse` can return additive safe session metadata without changing the existing deterministic grounded chat answer fields.
- Wired `POST /api/assets/{ticker}/chat` through `answer_chat_with_session` so supported cached assets can create sessions when `conversation_id` is omitted, append turns for active same-ticker sessions, and return no generated chat answer for expired, deleted, unavailable, or ticker-mismatched sessions.
- Added deterministic chat session routes in `backend/main.py`: `GET /api/chat-sessions/{conversation_id}`, `POST /api/chat-sessions/{conversation_id}/delete`, and `GET /api/chat-sessions/{conversation_id}/export`.
- Extended chat transcript export in `backend/export.py` so stored session transcript exports include safe session metadata, display-ready turn answers, citations, source metadata, freshness/source-use information, uncertainty labels, and the educational disclaimer while deleted or unavailable sessions return minimal unavailable export states.
- Preserved the existing single-turn chat export path, including the documented fallback where client-submitted question export can still work when no stored session is found.
- Added `evals/chat_session_eval_cases.yaml` and extended `evals/run_static_evals.py` for TTL constants, lifecycle states, required models/helpers/routes, no account/auth/cookie/analytics/live-call imports, no restricted storage markers, source-use/freshness metadata, and advice-boundary safety.
- Added `tests/unit/test_chat_sessions.py` plus focused updates to chat generation, safety guardrail, and backend API tests for session creation, continuation, expiry, deletion, ticker mismatch, unsupported-session blocking, advice redirects, source-policy preservation, transcript export, and API serialization.
- Added `docs/agent-journal/20260423T130125Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-038 agent journal records that focused chat-session/chat-generation/safety pytest passed with 26 tests, backend API pytest passed with 29 tests, full Python pytest passed with 174 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-038-20260423T130125Z`.
- Remaining documented risk: session storage is an in-memory deterministic contract only; it does not add database persistence, distributed cleanup, cross-process sharing, or production rate limiting.
- Remaining documented risk: accountless conversation IDs and timestamps are deterministic for local contract behavior; production entropy and real clock wiring can be swapped through the existing injection points.
- Remaining documented risk: stored session transcript export intentionally omits submitted question text from stored session turns; the existing single-turn export shape still supports client-submitted question export when no stored session is found.

Completion commits:

- `5395cb8 feat(T-038): add accountless chat session lifecycle contract`
- `79ef9ea chore(T-038): merge accountless chat session lifecycle contract`

### T-037: Add LLM provider orchestration and live-generation gating contract

Goal:
Add a deterministic LLM provider orchestration and live-generation gating contract so generated-output attempts, validation, model fallback metadata, cache eligibility, and public reasoning summaries are modeled without making live LLM calls, exposing secrets, changing generated asset/chat/comparison output, or weakening citation, source-use, freshness, and safety rules.

Completed:

- Added `backend/llm.py` with pure deterministic orchestration helpers for mock default behavior, sanitized OpenRouter gate metadata, generation-attempt metadata, validation-before-cache decisions, fallback decisions, and runtime diagnostics without live provider calls.
- Added LLM runtime, provider, model-chain, live-gate, generation request/attempt, validation, fallback, public metadata, and cache-eligibility contract models in `backend/models.py`.
- Extended `backend/cache.py` with cache eligibility metadata for validated generated-output contracts.
- Added a diagnostics-only `GET /api/llm/runtime` route in `backend/main.py` that exposes sanitized runtime metadata only.
- Added `evals/llm_provider_eval_cases.yaml` and extended `evals/provider_eval_cases.yaml` and `evals/run_static_evals.py` for model-chain order, live-gate behavior, sanitized public metadata, no secret exposure, no live-call imports, validation-before-cache behavior, no raw prompt/reasoning/source-text exposure, and no advice-like generated language.
- Added `tests/unit/test_llm_provider.py` for mock default behavior, OpenRouter disabled/enabled gate metadata from sanitized config, fallback decision metadata, validation rejection cases, cache eligibility, no secret/raw prompt/raw reasoning/source-text exposure, and no live-call imports.
- Extended safety and backend API tests for provider diagnostics serialization and safety guardrails.
- Added `docs/agent-journal/20260423T123524Z.md` documenting changed files, commands run, pass/fail status, an initial focused-test failure, final passing results, and remaining risks.
- T-037 agent journal records that the first focused pytest run failed with two test-scan issues around the literal OpenRouter model name and a validator marker phrase; the focused checks/marker were revised without changing runtime behavior.
- T-037 agent journal records that focused LLM/cache/citation/safety pytest passed with 40 tests, backend API pytest passed with 28 tests, full Python pytest passed with 163 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-037-20260423T123524Z`.
- Remaining documented risk: this is a deterministic contract and metadata layer only; it does not implement live OpenRouter calls or replace existing generated asset, chat, comparison, export, Weekly News Focus, or AI Comprehensive Analysis output.
- Remaining documented risk: live-provider enablement still requires separate server-side configuration wiring, provider-call implementation, licensing/cost review, and validation around any future network path.
- Remaining documented risk: cache eligibility is modeled and test-covered, but no persistent cache store or generated-summary persistence was added in this task.

Completion commits:

- `d9c6fd9 feat(T-037): add LLM provider orchestration and live-generation gating contract`
- `2f63449 chore(T-037): merge LLM provider orchestration and live-generation gating contract`

### T-036: Add Weekly News Focus and AI Comprehensive Analysis contracts

Goal:
Add deterministic Weekly News Focus and AI Comprehensive Analysis contracts so timely context is modeled, validated, cited, and kept separate from stable canonical facts, without adding live news/provider/market/LLM calls, new generated asset pages, or prediction/recommendation language.

Completed:

- Added `backend/weekly_news.py` with deterministic Weekly News Focus window calculation, candidate selection, source-priority scoring, exclusion rationale, deduplication metadata, empty/no-high-signal states, and AI Comprehensive Analysis construction/validation.
- Added Weekly News Focus and AI Comprehensive Analysis contract models in `backend/models.py`, including market-week periods, event types, contract states, source metadata, selected items, selection rationale, empty states, analysis sections, and the combined weekly-news response.
- Wired deterministic Weekly News Focus and AI Comprehensive Analysis into overview generation and the asset knowledge-pack section metadata while preserving stable canonical facts as separate overview sections.
- Added `GET /api/assets/{ticker}/weekly-news` in `backend/main.py` to return the selected asset's Weekly News Focus and AI Comprehensive Analysis contract data from the existing deterministic overview path.
- Updated exports so asset-page exports include separate Weekly News Focus and AI Comprehensive Analysis sections with citation IDs, source document IDs, freshness/as-of metadata, suppression messaging, and no hidden prompts or restricted raw text.
- Added `evals/weekly_news_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify market-week window logic, contract models, fixture empty states, AI analysis suppression, stable/recent separation, no live-call imports, and no advice-like analysis language.
- Added `tests/unit/test_weekly_news.py` for explicit Eastern as-of window behavior, fixture empty states without padding, official-source priority, disallowed/duplicate/promotional/irrelevant/wrong-asset exclusion, AI analysis threshold, required section order, and no live network imports.
- Extended retrieval, overview, export, and backend API tests for weekly-news section metadata, overview serialization, export serialization, and API response coverage.
- Added `docs/agent-journal/20260423T120556Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-036 agent journal records that focused weekly-news pytest passed with 5 tests, focused retrieval/overview/export/API pytest passed with 52 tests, the required focused task pytest passed with 53 tests, backend API pytest passed with 27 tests, full Python pytest passed with 152 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-036-20260423T120556Z`.
- Remaining documented risk: this is a deterministic contract and fixture-selection layer only; it does not add live news, SEC, issuer-site, market-data, or LLM calls.
- Remaining documented risk: existing cached local packs still produce empty/no-high-signal Weekly News Focus states, so the available AI Comprehensive Analysis path is covered by contract tests with deterministic candidates rather than by a persisted asset fixture.
- Remaining documented risk: Weekly News Focus candidate examples remain local and synthetic; future live or scraped sources still require allowlist, source-use, licensing, caching, and export review before use.

Completion commits:

- `9be562d feat(T-036): add Weekly News Focus and AI Comprehensive Analysis contracts`
- `dbf9865 chore(T-036): merge Weekly News Focus and AI Comprehensive Analysis contracts`

### T-035: Add source allowlist and rights-tiered raw text policy contract

Goal:
Add a deterministic source allowlist and rights-tiered raw text policy contract so source ingestion, retrieval metadata, citation resolution, exports, provider fixtures, and future Weekly News Focus work can validate source-use rights before storage, summarization, rendering, caching, or export, without adding live provider/news/market/LLM calls or changing generated learning output.

Completed:

- Added `config/source_allowlist.yaml` with a versioned local source-use policy registry for fixture and mock-provider sources, including required policy tiers, source type, source quality, allowlist status, operation permissions, allowed excerpt behavior, rationale, and review metadata.
- Added `backend/source_policy.py` with deterministic allowlist loading, validation, fixture/domain resolution, and explicit allowed/rejected/pending-review/not-allowlisted decisions without network calls.
- Added source-policy and allowlist models in `backend/models.py`, including `SourceUsePolicy`, `SourceAllowlistStatus`, `SourceQuality`, `SourceOperationPermissions`, `SourceAllowedExcerptBehavior`, allowlist record/config models, and source-policy decision models.
- Threaded source-use policy and allowlist status through deterministic retrieval, provider, citation, overview, comparison, chat, export, and cache metadata surfaces where source metadata is exposed.
- Updated `data/retrieval_fixtures.json` so existing SEC, ETF issuer, local fixture, provider, and recent-context sources carry explicit policy metadata while preserving current generated learning output.
- Updated citation validation so disallowed source-policy states cannot support generated claims.
- Updated export behavior so source-list and generated-output exports respect metadata, excerpt, and full-text operation permissions and do not expose restricted raw payloads.
- Added `evals/source_policy_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify allowlist path/schema, required tiers, official and fixture records, rejected/unrecognized source blocking, rights-tier operation flags, provider licensing consistency, no live-call imports, and no advice-like policy language.
- Extended provider eval cases for source-use and licensing consistency.
- Added `tests/unit/test_source_policy.py` for policy loading, validation, resolution, operation permissions, rejected/unrecognized sources, and no-network behavior.
- Extended retrieval, citation, export, provider, and backend API tests for source-policy metadata, disallowed evidence rejection, allowed-excerpt behavior, provider fixture policy consistency, and API serialization.
- Added `docs/agent-journal/20260423T064752Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-035 agent journal records that the first focused test run failed because PyYAML parsed unquoted allowlist dates into date/datetime values while the Pydantic contract expected strings; a focused `backend/models.py` revision normalized those YAML scalar types before validation.
- T-035 agent journal records that focused source-policy/retrieval/citation/export/provider pytest passed with 34 tests, backend API pytest passed with 27 tests, full Python pytest passed with 147 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-035-20260423T064752Z`.
- Remaining documented risk: this is a deterministic policy contract and fixture metadata layer only; it does not implement live ingestion, Weekly News Focus fetching, or provider licensing review.
- Remaining documented risk: restricted provider and recent-context handling are validated against local fixtures and mocks only.
- Remaining documented risk: future allowlist updates still need coordinated config, validation tests, and development-log rationale to preserve source-use governance.

Completion commits:

- `d73b51a feat(T-035): add source allowlist and rights-tiered raw text policy contract`
- `a65feae chore(T-035): merge source allowlist and rights-tiered raw text policy contract`

### T-034: Add Top-500 stock universe manifest contract

Goal:
Add a deterministic Top-500 U.S.-listed common stock universe manifest contract so stock support scope is driven by a versioned local manifest instead of live provider queries, without adding live market/reference calls, changing generated asset pages, or treating the manifest as an endorsement, recommendation, portfolio, or ranking surface.

Completed:

- Added `data/universes/us_common_stocks_top500.current.json` with schema version `top500-us-common-stock-universe-v1`, runtime path metadata, production mirror env-var metadata, monthly refresh cadence, snapshot/provenance/checksum fields, non-advice policy language, and deterministic launch stock entries for `AAPL`, `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `BRK.B`, `JPM`, and `UNH`.
- Added Top-500 manifest models in `backend/models.py`, including entry and manifest fields for ticker, name, stock/security type, CIK, exchange, rank, rank basis, source provenance, snapshot date, checksum input/checksum, approval timestamp, launch group, and aliases.
- Added deterministic manifest loading and validation helpers in `backend/data.py`, including runtime path validation, `TOP500_UNIVERSE_MANIFEST_URI` metadata validation, stock-only/security-type checks, rank and ticker uniqueness checks, checksum-field checks, snapshot-date consistency, no-advice-language checks, and lookup helpers.
- Rebuilt eligible-not-cached stock metadata from the manifest so cached `AAPL` remains generated from its local pack while `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `BRK.B`, `JPM`, and `UNH` become manifest-backed eligible-not-cached stocks.
- Added `OUT_OF_SCOPE_COMMON_STOCKS` handling for a recognized common stock outside the manifest, including `GME`, so search, ingestion, pre-cache, and provider fixtures return out-of-scope non-generated states rather than treating it as eligible-not-cached.
- Updated `backend/search.py`, `backend/ingestion.py`, and `backend/providers.py` so manifest-backed eligible-not-cached stocks expose ingestion/pre-cache/provider fixture states without generated pages, chat answers, comparisons, citations, source documents, or risk summaries.
- Extended `evals/search_eval_cases.yaml`, `evals/ingestion_eval_cases.yaml`, `evals/provider_eval_cases.yaml`, and `evals/run_static_evals.py` to verify the manifest path/schema/fields, required stock membership, cached versus eligible-not-cached boundaries, out-of-scope stock behavior, no generated output for non-cached stocks, no live provider imports, and no advice-like manifest language.
- Extended `tests/unit/test_search_classification.py`, `tests/unit/test_ingestion_jobs.py`, `tests/unit/test_provider_adapters.py`, and `tests/integration/test_backend_api.py` for manifest-backed classification, ingestion/pre-cache routing, provider mock states, API serialization, and out-of-scope common-stock behavior.
- Added `docs/agent-journal/20260423T061610Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-034 agent journal records that focused search/ingestion/provider pytest passed with 28 tests, backend API pytest passed with 27 tests, full Python pytest passed with 143 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-034-20260423T061610Z`.
- Remaining documented risk: the manifest is a deterministic contract fixture for the current launch stock set, not a live refreshed 500-entry universe.
- Remaining documented risk: manifest rank is operational coverage metadata only; future refreshes must preserve the non-advice framing and checksum/provenance fields.
- Remaining documented risk: no generated pages, source evidence, citations, chat answers, comparisons, or risk summaries were added for manifest-backed eligible-not-cached stocks.

Completion commits:

- `cb1bda5 feat(T-034): add Top-500 stock universe manifest contract`
- `73c0153 chore(T-034): merge Top-500 stock universe manifest contract`

### T-033: Rebase agent instructions and local environment to updated PRD/TDS

Goal:
Rebaseline the project control plane, local agent-loop environment, and frontend workspace layout around the updated proposal, PRD, and technical design spec without rolling back the user's documentation changes, changing product behavior, adding live provider calls, or exposing secrets.

Completed:

- Updated `AGENTS.md`, `SPEC.md`, `EVALS.md`, `TASKS.md`, and `.github/codex/prompts/review.md` around the updated PRD/TDS/proposal authority order, Top-500-first MVP scope, Weekly News Focus and AI Comprehensive Analysis separation, source-use rights, OpenRouter/live-provider gating, secret handling, and `apps/web` frontend root.
- Moved the Next.js frontend into `apps/web` with 100% file renames for the `app`, `components`, `lib`, styles, Next config, and TypeScript config files.
- Added root npm workspace delegation so `npm run dev`, `npm run build`, `npm run start`, and `npm run typecheck` delegate to `apps/web`, while `npm test` continues to run frontend smoke checks from the repo root.
- Added `apps/web/package.json` with local Next.js dev/build/start/typecheck scripts and updated `package-lock.json` for the workspace layout.
- Updated frontend smoke and safety tests so path-sensitive checks read frontend files from `apps/web`.
- Updated Bash and PowerShell agent-loop and quality-gate scripts so prompts read the proposal, PRD, TDS, SPEC, TASKS, and EVALS with PRD/TDS-first authority after safety.
- Added placeholder-only local environment examples in `.env.example`, `apps/web/.env.example`, and `deploy/env/*.example.env` without real secret values or browser-exposed provider keys.
- Added local-only Docker Compose scaffolding for web, API, ingestion-worker placeholder, Postgres/pgvector, Redis, and MinIO-compatible object storage, plus web/API Dockerfiles.
- Normalized the updated PRD, technical design spec, and proposal docs to LF line endings so `git diff --check` passes.
- Verified the staged diff detected frontend moves as `R100` renames and found no P0/P1 review blockers before commit.
- Ran `python3 -m pytest tests/unit/test_repo_contract.py -q`: 9 tests passed.
- Ran `npm test`: frontend smoke checks passed.
- Ran `python3 -m pytest tests -q`: 140 tests passed.
- Ran `python3 evals/run_static_evals.py`: passed.
- Ran `npm run typecheck`: passed.
- Ran `npm run build`: passed.
- Ran `bash scripts/run_quality_gate.sh`: passed, including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Ran `docker compose config`: passed.
- Pushed `main` to `origin/main` with commit `2a3175f`.
- Remaining documented risk: Docker Compose was syntax-validated only; it was not used to build images or run the local stack end to end.
- Remaining documented risk: the workspace move did not add new frontend behavior; future UI tasks still need browser/mobile verification when they change rendered flows.
- Remaining documented risk: placeholder provider environment variables remain configuration readiness only; live provider behavior still requires separate licensing, caching, display, export, and validation work.

Completion commits:

- `2a3175f chore(T-033): rebase control plane for updated PRD/TDS`

### T-032: Add trust metrics event contract for MVP workflows

Goal:
Add a deterministic backend trust-metrics event contract so MVP workflows can validate and inspect privacy-preserving product/trust event payloads without adding real analytics, persistence, user tracking, live calls, or changes to generated learning output.

Completed:

- Added trust-metrics contract models in `backend/models.py`, including workflow areas, event types, metric kind, validation status, asset support states, output kinds, safety status, generated-output metadata, event, validated event, catalog, validation request/response, and summary response models.
- Added `backend/trust_metrics.py` with schema version `trust-metrics-event-v1`, deterministic default timestamp `1970-01-01T00:00:00Z`, a validation-only product/trust event catalog, and pure helpers for event validation, batch validation, and in-memory summarization.
- Product event catalog coverage includes search success, unsupported asset outcomes, asset-page views, comparison usage, source drawer usage, glossary usage, export usage, chat follow-up, chat answer outcomes, chat safety redirects, and latency-to-first-meaningful-result metadata.
- Trust event catalog coverage includes citation coverage, unsupported-claim drops, weak citation counts, generated-output validation failures, safety redirect rate, freshness accuracy, source retrieval failure, hallucination/unsupported-fact incidents, and stale data incidents.
- Validation normalizes asset tickers and infers support states for cached supported assets, eligible-not-cached assets, recognized unsupported assets, and unknown assets without implying generated output exists for non-generated states.
- Validation rejects privacy-sensitive or licensing-sensitive field names such as `raw_query`, `question`, `answer`, `source_passage`, `source_url`, `email`, `ip_address`, `user_agent`, `account_id`, `portfolio`, `allocation`, cookies, and external analytics identifiers.
- Validation rejects inconsistent metric payloads including generated-output availability for eligible-not-cached, unsupported, unknown, or unavailable assets; citation coverage outside `0..1`; negative counts or latency; source/citation IDs when no generated output exists; and freshness/retrieval/stale-data metrics without explicit freshness state.
- Generated-output metadata can carry compact validation metadata such as output kind, prompt version, model name, schema-valid flag, citation coverage rate, citation IDs, source document IDs, freshness hash/state, safety status, unsupported-claim count, weak-citation count, stale-source count, and latency, while raw generated text, retrieved text, source passages, URLs, prompts, and personal identifiers remain forbidden.
- Deterministic summarization aggregates accepted events only into event-type counts, workflow-area counts, product/trust metric counts, rates, and latency min/max/average without persistence, clock dependence, analytics services, or network calls.
- Added validation-only API routes in `backend/main.py`: `GET /api/trust-metrics/catalog` and `POST /api/trust-metrics/validate`; responses explicitly report validation-only behavior and do not store, forward, or enrich events from live services.
- Added `evals/trust_metrics_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required models, helpers, product/trust event coverage, forbidden fields, required routes, deterministic validation/summarization, and absence of persistence, analytics SDK, credential, environment, and live-network imports.
- Added `tests/unit/test_trust_metrics.py` for catalog coverage, anonymous metadata normalization, eligible-not-cached/unsupported/unknown state distinction, generated-output metadata acceptance, privacy/state rejection cases, and deterministic summarization.
- Extended `tests/integration/test_backend_api.py` for catalog/validation API serialization, accepted and rejected payloads, no-storage response flags, invalid generated-output states, and no mutation of existing overview/chat/comparison/export responses.
- Extended `tests/unit/test_safety_guardrails.py` so trust-metrics contract and API copy are scanned for forbidden advice-like language.
- Added `docs/agent-journal/20260422T203211Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-032 agent journal records that `git status --short`, focused trust metrics/API/safety pytest, full pytest, safety guardrail pytest, static evals, and the full quality gate passed.
- T-032 agent journal records focused trust metrics/API/safety pytest as 42 tests passed, full Python pytest as 136 tests passed, safety guardrail pytest as 7 tests passed, static evals as passed, and the full quality gate as passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-032-20260422T203211Z`.
- Remaining documented risk: this is a deterministic validation and summarization contract only; it does not emit analytics from frontend components, persist events, forward payloads, add an analytics SDK, or create a real metrics store.
- Remaining documented risk: accepted event payloads intentionally carry compact anonymous metadata only; future instrumentation must continue to reject raw questions, generated answers, source passages, source URLs, personal identifiers, cookies, portfolio/allocation details, and external analytics IDs.
- Remaining documented risk: aggregation is in-memory and count/rate based for contract validation; production observability would need separate privacy and licensing review before any storage or vendor integration is added.

Completion commits:

- `4e84de1 feat(T-032): add trust metrics event contract for MVP workflows`
- `3138655 chore(T-032): merge trust metrics event contract for MVP workflows`

### T-031: Add common comparison suggestions for supported assets

Goal:
Add deterministic common comparison suggestions for fixture-backed supported assets so beginners can discover available local comparisons and understand when comparison evidence is unavailable, without generating unsupported comparisons, adding new asset facts, or making live calls.

Completed:

- Added `lib/compareSuggestions.ts` with a deterministic comparison-suggestion model, `local_comparison_available`, `no_local_comparison_pack`, and `unavailable_with_fixture_examples` states, relative `/compare?left={left}&right={right}` URL construction, and local availability checks against the existing compare-page fixture.
- Kept the only actionable local comparison pair as `VOO`/`QQQ`: `VOO` suggests `QQQ`, `QQQ` suggests `VOO`, and `AAPL` receives an explicit no-local-comparison-pack state with no generated peer list or factual differences.
- Added `components/ComparisonSuggestions.tsx` with stable markers for suggestion scope, selected ticker, state, requested comparison tickers, target ticker, left/right tickers, compare URL, and no-local-pack state, plus accessible link labels that preserve educational non-advice framing.
- Wired comparison suggestions into `app/assets/[ticker]/page.tsx` for fixture-backed asset pages and into `app/compare/page.tsx` for supported and unavailable comparison states without changing the generated comparison output.
- Added responsive comparison-suggestion styling in `styles/globals.css`.
- Extended `tests/frontend/smoke.mjs` for the new comparison-suggestion component/helper markers, `VOO`/`QQQ` fixture pair coverage, unavailable-state copy, no-local-pack copy, and absence of live external comparison behavior from the suggestion UI.
- Extended `tests/unit/test_safety_guardrails.py` so comparison suggestion copy is scanned for forbidden advice-like language.
- Added `docs/agent-journal/20260422T200644Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-031 agent journal records that the initial `npm test` failed because a new smoke-test regex marker did not escape literal parentheses, then passed after one focused smoke-test assertion revision.
- T-031 agent journal records that `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, static evals, and the full quality gate passed.
- T-031 agent journal records safety guardrail pytest as 6 tests passed and the full quality gate as passed including 123 Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-031-20260422T200644Z`.
- Remaining documented risk: comparison suggestions remain deterministic frontend discovery only; no new comparison evidence, backend contract, retrieval pack, source fixture, generated output, export behavior, analytics, or live-call path was added.
- Remaining documented risk: `AAPL` and unavailable requested comparison states intentionally show no-local-pack or fixture-example messaging rather than generated peer lists or factual differences.
- Remaining documented risk: the only actionable local comparison suggestion remains the existing `VOO`/`QQQ` fixture-backed pair in either direction.

Completion commits:

- `5f7d041 feat(T-031): add common comparison suggestions for supported assets`
- `a2cb228 chore(T-031): merge common comparison suggestions for supported assets`

### T-030: Add frontend export controls for saved learning outputs

Goal:
Add deterministic frontend export controls so users can save fixture-backed asset-page output, asset source lists, comparison output, and chat transcripts through the existing export API contracts, while preserving citations, freshness labels, source metadata, educational disclaimers, licensing scope, unsupported/unavailable states, and no-live-call behavior.

Completed:

- Added reusable frontend export URL/request helpers in `lib/exportControls.ts` for asset-page, asset source-list, comparison, and chat transcript exports using relative local API paths.
- Added `components/ExportControls.tsx` with accessible link controls for GET exports and a deterministic POST/copy flow for chat transcript Markdown exports.
- Wired fixture-backed asset pages in `app/assets/[ticker]/page.tsx` so `AAPL`, `VOO`, and `QQQ` show asset-page and source-list export controls with citation, freshness, disclaimer, and licensing context.
- Wired supported `VOO`/`QQQ` and `QQQ`/`VOO` comparison pages in `app/compare/page.tsx` to show comparison export controls, while unavailable comparison states keep export controls hidden and preserve non-generated guardrail copy.
- Added chat transcript export controls in `components/AssetChatPanel.tsx` after a deterministic chat answer is returned, preserving educational redirect, unsupported/unknown, and insufficient-evidence states through the backend export contract.
- Added responsive export-control styling in `styles/globals.css`.
- Extended `tests/frontend/smoke.mjs` for export markers, relative API paths, no live external URLs, unavailable export states, package dependency shape, and backend export-route presence.
- Extended `tests/unit/test_safety_guardrails.py` for advice-safe export helper and component copy.
- Added `docs/agent-journal/20260422T193929Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-030 agent journal records that `git status --short`, `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, focused export/API pytest, static evals, and the full quality gate passed.
- T-030 agent journal records safety guardrail pytest as 5 tests passed, focused export/API pytest as 29 tests passed, static evals as passed, and the full quality gate as passed including 122 Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-030-20260422T193929Z`.
- Remaining documented risk: export controls open or prepare existing JSON/Markdown-style backend export payloads; this task does not add PDF generation, file storage, browser file naming, authentication, analytics, or persistence.
- Remaining documented risk: chat transcript export still depends on the local backend route being available at runtime; normal CI remains deterministic and uses no provider credentials or live external calls.
- Remaining documented risk: licensing copy is frontend trust-context UI only; final provider-specific redistribution rules still need review before paid or restricted provider content is exposed.

Completion commits:

- `982b1a2 feat(T-030): add frontend export controls for saved learning outputs`
- `fbc5484 chore(T-030): merge frontend export controls for saved learning outputs`

### T-029: Add deterministic asset knowledge-pack builder

Goal:
Add a deterministic asset knowledge-pack builder contract that makes the bounded evidence set for each local cached asset inspectable, freshness-hashable, and explicitly unavailable for eligible-not-cached, unsupported, and unknown assets without adding new source facts, generated output, live calls, or frontend UI.

Completed:

- Added knowledge-pack build contract models in `backend/models.py`: `KnowledgePackBuildState`, `KnowledgePackCounts`, `KnowledgePackSourceMetadata`, `KnowledgePackFactMetadata`, `KnowledgePackChunkMetadata`, `KnowledgePackRecentDevelopmentMetadata`, `KnowledgePackEvidenceGapMetadata`, and `KnowledgePackBuildResponse`.
- Added `build_asset_knowledge_pack_result` in `backend/retrieval.py` with schema version `asset-knowledge-pack-build-v1` and stable pack IDs such as `asset-knowledge-pack-aapl-local-fixture-v1`, `asset-knowledge-pack-voo-local-fixture-v1`, and `asset-knowledge-pack-qqq-local-fixture-v1`.
- Supported cached local assets `AAPL`, `VOO`, and `QQQ` now return available knowledge-pack metadata from existing local retrieval fixtures, including generated routes, generated-output availability, page/chat/comparison capability flags, page and section freshness labels, source-document IDs, derived citation IDs, counts, source checksums, cache keys, cache revalidation state, and deterministic knowledge-pack freshness hashes.
- Supported cached responses expose same-asset source, fact, chunk, recent-development, and evidence-gap metadata while intentionally omitting raw chunk text, supporting passages, and full source-document exports.
- Eligible-not-cached assets such as `SPY` return explicit non-generated `eligible_not_cached` knowledge-pack states with no sources, citations, normalized facts, chunks, recent developments, source checksums, freshness hash, generated route, page/chat/comparison capability, or reusable generated-output cache hit; only the ingestion-request capability is true for eligible-not-cached states.
- Unsupported assets such as `TQQQ` and unknown assets such as `ZZZZ` return explicit non-generated `unsupported` or `unknown` knowledge-pack states with no generated output, no source evidence, no citations, no freshness hash, and non-reusable cache revalidation results.
- Added the read-only API route `GET /api/assets/{ticker}/knowledge-pack` in `backend/main.py`, serializing the same deterministic response for supported cached, eligible-not-cached, unsupported, and unknown tickers.
- Preserved existing generated overview, chat, and comparison behavior by keeping existing `build_asset_knowledge_pack` and `build_comparison_knowledge_pack` callers compatible.
- Added `evals/knowledge_pack_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required models/helpers, stable pack IDs, supported cached coverage, eligible-not-cached and unsupported/unknown non-generation, source/citation absence for nonexistent packs, same-asset binding, freshness-hash determinism, no raw full-document export, API serialization, and forbidden live-call or credential imports scoped to retrieval.
- Added focused coverage in `tests/unit/test_retrieval_fixtures.py`, `tests/unit/test_cache_contracts.py`, `tests/unit/test_overview_generation.py`, `tests/unit/test_chat_generation.py`, `tests/unit/test_comparison_generation.py`, and `tests/integration/test_backend_api.py` for deterministic repeated builds, metadata-only supported responses, no generated output for non-cached states, freshness-hash integration, route serialization, and preservation of generated overview/chat/comparison outputs.
- Added `docs/agent-journal/20260422T191056Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-029 agent journal records that `git status --short`, focused retrieval/cache pytest, focused overview/chat/comparison pytest, backend API pytest, full pytest, static evals, and the full quality gate passed.
- T-029 agent journal records focused retrieval/cache pytest as 24 tests passed, focused overview/chat/comparison pytest as 27 tests passed, backend API integration pytest as 23 tests passed, full Python pytest as 121 tests passed, static evals as passed after one eval-only revision, and the full quality gate as passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-029-20260422T191056Z`.
- Remaining documented risk: the knowledge-pack builder is a deterministic read-only contract over existing local fixtures; it does not add ingestion workers, persistence, provider calls, source facts, LLM calls, frontend UI, or generated output for non-cached assets.
- Remaining documented risk: eligible-not-cached assets remain explicit non-generated states with no source evidence, citations, facts, chunks, recent developments, freshness hash, generated route, or reusable generated-output cache hit.
- Remaining documented risk: supported cached assets expose metadata and freshness hashes for existing `AAPL`, `VOO`, and `QQQ` fixture packs, but intentionally omit raw chunk text and full source-document passages.

Completion commits:

- `bfeba12 feat(T-029): add deterministic asset knowledge-pack builder`
- `5ac1597 chore(T-029): merge deterministic asset knowledge-pack builder`

### T-028: Add pre-cache launch-universe job contracts

Goal:
Add deterministic pre-cache launch-universe job contracts so the MVP operational pre-cache set can be requested and inspected as fixture-backed job state without starting real workers, making provider calls, generating new asset output, or changing search/support classification.

Completed:

- Added pre-cache response models in `backend/models.py`: `PreCacheJobResponse`, `PreCacheBatchSummary`, and `PreCacheBatchResponse`, using existing ingestion job types, job states, worker states, capabilities, retryability, generated-output flags, citation/source ID lists, and status URLs.
- Added deterministic pre-cache contract helpers in `backend/ingestion.py`, including stable launch batch ID `pre-cache-launch-universe-v1`, stable launch status URL `/api/admin/pre-cache/launch-universe`, stable per-asset job IDs such as `pre-cache-launch-voo`, and fixture-backed request/status helpers for launch-universe assets.
- The launch-universe pre-cache contract covers cached local generated assets `AAPL`, `VOO`, and `QQQ` plus the eligible-not-cached launch assets from `ELIGIBLE_NOT_CACHED_ASSETS`.
- Cached local assets are marked succeeded/already available with existing generated routes and page/chat/comparison capability flags preserved.
- Eligible-not-cached assets remain non-generated: the contract gives pending/queued states for most launch assets, a deterministic running fixture for `MSFT`, and a deterministic failed retryable fixture for `AMZN`, with no generated route, citations, source documents, generated page, chat answer, comparison, or reusable generated-output cache hit.
- Unsupported and unknown pre-cache requests return explicit unsupported or unknown non-generated states, and missing pre-cache job IDs return an unavailable non-generated state.
- Added API routes in `backend/main.py` for `POST /api/admin/pre-cache/launch-universe`, `GET /api/admin/pre-cache/launch-universe`, `GET /api/admin/pre-cache/jobs/{job_id}`, and `POST /api/admin/pre-cache/{ticker}` while preserving existing `/api/admin/ingest/{ticker}` and `/api/jobs/{job_id}` behavior.
- Added `evals/pre_cache_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required models, status states, launch-universe coverage, stable IDs, capability flags, no generated output for non-cached states, absence of citations/source documents from nonexistent packs, and forbidden live-call or credential imports.
- Added focused coverage in `tests/unit/test_ingestion_jobs.py`, `tests/unit/test_cache_contracts.py`, and `tests/integration/test_backend_api.py` for deterministic batch/status responses, cached versus eligible-not-cached capabilities, running/failed/unsupported/unknown/unavailable states, cache non-reuse for non-generated states, and API serialization.
- Added `docs/agent-journal/20260422T184635Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-028 agent journal records that `git status --short`, focused ingestion/cache pytest, backend API pytest, full pytest, static evals, and the full quality gate passed.
- T-028 agent journal records focused ingestion/cache pytest as 24 tests passed, backend API integration pytest as 22 tests passed, full Python pytest as 113 tests passed, static evals as passed, and the full quality gate as passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-028-20260422T184635Z`.
- Remaining documented risk: the pre-cache work is contract-only; it does not add real workers, queues, Redis/PostgreSQL persistence, provider calls, source facts, retrieval packs, generated pages, generated chat answers, generated comparisons, frontend UI, analytics, auth, or deployment config.
- Remaining documented risk: eligible-not-cached launch assets remain non-generated even though their pre-cache jobs expose deterministic pending/running/failed states and status URLs.
- Remaining documented risk: cached local assets `AAPL`, `VOO`, and `QQQ` are marked pre-cache succeeded only because existing fixture-backed generated routes and capabilities already exist.

Completion commits:

- `a61de16 feat(T-028): add pre-cache launch-universe job contracts`
- `f23e33f chore(T-028): merge pre-cache launch-universe job contracts`

### T-027: Expand golden asset eval coverage for MVP launch universe

Goal:
Expand deterministic golden eval coverage so the MVP launch-universe control set catches regressions in search/support classification, on-demand ingestion eligibility, provider mock states, unavailable comparisons, citations/freshness expectations, and advice-boundary safety without making live external calls or generating unsupported asset content.

Completed:

- Expanded `evals/golden_assets.yaml` to schema `golden-assets-v2` with technical-design golden assets, cached supported assets, eligible-not-cached launch assets, unsupported samples, unknown samples, common comparison pairs, local generated comparison pairs, and expected capability flags.
- Preserved `AAPL`, `VOO`, and `QQQ` as the only cached supported local generated fixtures with generated routes, page/chat/comparison capabilities, citations, source documents, freshness expectations, stable/recent separation, and exactly three top risks.
- Added deterministic eligible-not-cached launch-universe metadata in `backend/data.py` for non-cached launch assets including broad ETFs, sector/theme ETFs, and large stocks such as `SPY`, `VTI`, `IVV`, `IWM`, `DIA`, `VGT`, `XLK`, `SOXX`, `SMH`, `XLF`, `XLV`, `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `BRK.B`, `JPM`, and `UNH`.
- Extended deterministic ingestion behavior in `backend/ingestion.py` so eligible-not-cached launch assets return stable on-demand job IDs and status URLs with no generated route, page capability, chat capability, comparison capability, citations, or invented facts.
- Extended mocked provider behavior in `backend/providers.py` so market/reference asset-resolution responses cover eligible-not-cached launch assets with same-asset identity and generated-output flags still false.
- Extended search, ingestion, provider, backend API, and static eval coverage through `tests/unit/test_search_classification.py`, `tests/unit/test_ingestion_jobs.py`, `tests/unit/test_provider_adapters.py`, `tests/integration/test_backend_api.py`, `evals/search_eval_cases.yaml`, `evals/ingestion_eval_cases.yaml`, `evals/provider_eval_cases.yaml`, and `evals/run_static_evals.py`.
- Golden comparison coverage now preserves the existing generated local `VOO`/`QQQ` comparison where a local pack exists and verifies common pairs involving eligible-not-cached or missing packs stay unavailable without generated factual differences, beginner bottom lines, citations, source documents, or invented facts.
- Static evals verify launch-universe membership, cached-supported versus eligible-not-cached capability boundaries, citation/source/freshness expectations for cached fixtures, unavailable states for missing comparison packs, advice-boundary safety, and no live-call or credential imports.
- Added `docs/agent-journal/20260422T181551Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-027 agent journal records that `git status --short`, focused search/ingestion/provider pytest, backend API pytest, full pytest, static evals, and the full quality gate passed.
- T-027 agent journal records focused search/ingestion/provider pytest as 20 tests passed, backend API pytest as 20 tests passed, full pytest as 105 tests passed, static evals as passed, and the quality gate as passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-027-20260422T181551Z`.
- Remaining documented risk: launch-universe additions are deterministic resolution and eval metadata only; they do not add real source facts, retrieval knowledge packs, generated pages, chat answers, comparison packs, exports, provider network calls, or ingestion workers.
- Remaining documented risk: eligible-not-cached generated API paths remain blocked by the existing local fixture behavior, but forced overview/chat calls still surface unavailable or unsupported-redirect style responses because no retrieval packs exist yet.
- Remaining documented risk: provider responses for newly added launch assets are mocked asset-resolution contracts only; future real provider ingestion must preserve same-asset binding, licensing constraints, freshness metadata, and no-live-call CI behavior.

Completion commits:

- `c803eee test(T-027): expand golden asset eval coverage for MVP launch universe`
- `d6be27a chore(T-027): merge expand golden asset eval coverage for MVP launch universe`

### T-026: Add caching and freshness-hash contracts

Goal:
Add deterministic backend cache-key, source-checksum, and freshness-hash contracts so future cached asset pages, comparisons, chat answers, exports, pre-cache jobs, and refresh jobs can decide whether cached outputs are reusable without making live external calls or weakening citation, freshness, licensing, or safety guarantees.

Completed:

- Added cache contract enums and models in `backend/models.py`, including `CacheEntryKind`, `CacheScope`, `CacheEntryState`, `CacheInvalidationReason`, `CacheKeyMetadata`, `SourceChecksumInput`, `SourceChecksumRecord`, `FreshnessFactInput`, `FreshnessRecentEventInput`, `FreshnessEvidenceGapInput`, `SectionFreshnessInput`, `KnowledgePackFreshnessInput`, `GeneratedOutputFreshnessInput`, `CacheEntryMetadata`, and `CacheRevalidationResult`.
- Added `backend/cache.py` with pure deterministic helpers for cache-key construction, source-document checksum computation, knowledge-pack freshness hashes, generated-output freshness hashes, cache revalidation decisions, local text fingerprinting, retrieval/provider source checksum adapters, knowledge/comparison pack freshness inputs, generated-output freshness inputs, and generated-output cache metadata.
- Cache keys include schema version, cache scope, entry kind, asset or comparison identity, mode/output type, source freshness state, prompt version, model name, and input freshness hash where provided.
- Comparison cache keys preserve left/right direction with identities such as `comparison-voo-to-qqq` and `comparison-qqq-to-voo`.
- Source checksums normalize unordered fact bindings, recent-event bindings, citation IDs, and local chunk text fingerprints so equivalent reordering does not change checksums.
- Source checksum records preserve source document ID, asset ticker, checksum, freshness state, cache permission, source type/rank, citation IDs, fact bindings, and recent-event bindings without storing raw local chunk text.
- Knowledge-pack and generated-output freshness hashes sort source checksum, fact, recent-event, evidence-gap, and section-freshness inputs so unordered equivalent inputs hash consistently.
- Generated-output freshness hashes change when prompt version, model name, schema version, source freshness state, source checksum, canonical fact input, or recent-development input changes.
- Cache revalidation can return `hit`, `miss`, `stale`, `hash_mismatch`, `expired`, `permission_limited`, `unsupported`, `unknown`, `unavailable`, and `eligible_not_cached` states without inventing facts.
- Unsupported, unknown, eligible-not-cached, unavailable, stale, and permission-limited inputs are explicitly blocked from reusable generated-output cache hits.
- Provider/source licensing metadata is respected at the contract level: `cache_allowed=False` produces a permission-limited non-reusable cache decision.
- Cache entry metadata preserves source document IDs, citation IDs, source freshness states, section freshness labels, unknown/stale/unavailable evidence-gap states, prompt/model metadata, cache permission, and export permission.
- Added focused cache contract tests in `tests/unit/test_cache_contracts.py` covering deterministic cache keys, direction-preserving comparison keys, source checksum determinism, raw text exclusion, provider cache permissions, order-insensitive knowledge hashes, generated-output hash invalidation, revalidation states, no-live-call/no-store imports, and preserved metadata.
- Added `evals/cache_eval_cases.yaml` and extended `evals/run_static_evals.py` for required cache models, required helpers, revalidation states, invalidation reasons, checksum inputs, freshness-hash inputs, cache-key cases, permission-limited blocking, unsupported blocking, hash-mismatch blocking, and forbidden imports.
- Added `docs/agent-journal/20260422T174755Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-026 agent journal records that `git status --short`, cache contract pytest, backend API pytest, full pytest, static evals, and the full quality gate passed.
- T-026 agent journal records cache contract pytest as 12 passed, backend API pytest as 20 passed, full pytest as 103 passed, static evals as passed, and the quality gate as passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Remaining documented risk: the cache work is contract-only; no Redis, PostgreSQL, persistence layer, queue, provider fetch path, LLM path, API route, frontend UI, or generated-output behavior was wired to these helpers.
- Remaining documented risk: freshness hashes are deterministic over local fixture/provider-contract inputs, but future ingestion/provider implementations must map real source metadata, normalized facts, recent events, evidence gaps, and licensing permissions into these models consistently.
- Remaining documented risk: provider licensing is enforced only at the cache-contract decision level; real paid or restricted provider terms still need review before storing, exporting, or redistributing any provider content.

Completion commits:

- `a44dada feat(T-026): add caching and freshness-hash contracts`
- `9b1896a chore(T-026): merge caching and freshness-hash contracts`

### T-025: Add provider adapter interfaces with mocked tests

Goal:
Add typed provider adapter interfaces and deterministic mocked adapter responses for the future SEC, ETF issuer, market/reference, and recent-development provider layer so ingestion work has explicit contracts for source-backed data, attribution, freshness, licensing, and failure states without making live external calls.

Completed:

- Added provider contract enums and models in `backend/models.py`, including `ProviderKind`, `ProviderDataCategory`, `ProviderResponseState`, `ProviderSourceUsage`, `ProviderRequestMetadata`, `ProviderCapability`, `ProviderLicensing`, `ProviderSourceAttribution`, `ProviderFact`, `ProviderRecentDevelopmentCandidate`, `ProviderResponseFreshness`, `ProviderError`, `ProviderGeneratedOutputFlags`, and `ProviderResponse`.
- Added `backend/providers.py` with a `ProviderAdapter` protocol, deterministic `MockProviderAdapter`, `NO_LIVE_EXTERNAL_CALLS`, `DEFAULT_PROVIDER_RETRIEVED_AT`, factory functions for SEC-like, ETF issuer, market/reference, and recent-development mock adapters, plus `get_mock_provider_adapters` and `fetch_mock_provider_response`.
- Added a deterministic SEC-like stock provider response for `AAPL` with official SEC source attribution, source rank `1`, canonical usage, `primary_business`, and `net_sales_trend_available` facts.
- Added deterministic ETF issuer provider responses for `VOO` and `QQQ` with official issuer fact-sheet and holdings-file attribution, source rank `1`, benchmark, expense-ratio, and holdings-count facts.
- Added deterministic structured market/reference responses for `AAPL`, `VOO`, and `QQQ` as supported local assets, and `SPY` and `MSFT` as eligible-not-cached assets.
- Market/reference responses use structured-reference source usage, source rank `4`, non-official attribution, and restricted licensing metadata with export and redistribution disallowed for restricted provider payloads.
- Added deterministic recent-development responses where `AAPL` has a high-signal recent-context filing-review candidate, while `VOO` and `QQQ` return an explicit `no_high_signal` state.
- Recent-development source attribution and candidates are marked as recent context only and cannot overwrite canonical facts.
- Added explicit provider failure states for recognized unsupported assets such as `BTC`, `TQQQ`, and `SQQQ`, unknown assets such as `ZZZZ`, and unavailable recent-development fixtures without invented facts.
- Provider responses include source document IDs, source types, publishers, URLs where available, published/as-of dates, retrieved timestamps, freshness states, official-source flags, provider names/kinds, data categories, source usage/rank, licensing metadata, provider errors, and generated-output flags.
- Generated-output flags remain false for asset pages, chat answers, comparisons, overview sections, export payloads, and frontend routes.
- Provider facts and recent-development candidates bind to the requested asset only, bind citations to source document IDs where applicable, and do not use glossary entries as support for asset-specific claims.
- Added focused provider adapter tests in `tests/unit/test_provider_adapters.py` covering adapter capabilities, supported responses, eligible-not-cached states, unsupported/unknown/unavailable states, same-asset binding, source hierarchy, freshness fields, licensing constraints, recent-context separation, no-high-signal recent-development handling, generated-output flags, and absence of live-call or credential imports.
- Added provider static eval cases in `evals/provider_eval_cases.yaml` and extended `evals/run_static_evals.py` for required provider kinds, supported stock/ETF/market/recent cases, eligible-not-cached cases, failure states, no-high-signal recent-development cases, licensing constraints, source hierarchy, generated-output flags, and forbidden live-call imports.
- Added `docs/agent-journal/20260422T172010Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-025 agent journal records that `git status --short`, provider adapter pytest, backend API pytest, full pytest, static evals, and the full quality gate passed.
- T-025 agent journal records provider adapter pytest as 8 passed, backend API pytest as 20 passed, full pytest as 91 passed, static evals as passed, and the quality gate as passed including provider contract tests, static evals, full Python suite, frontend smoke/type/build checks, and backend checks.
- Remaining documented risk: provider adapters are deterministic mock contracts only; they do not fetch SEC, ETF issuer, market/reference, or news data.
- Remaining documented risk: provider contracts are intentionally not wired into search, ingestion jobs, overview generation, comparison, chat, export, persistence, caching, queues, or frontend UI.
- Remaining documented risk: licensing metadata documents export/display constraints at the contract level, but real provider terms still require review before paid or restricted data is exposed, cached, or exported.

Completion commits:

- `e14a798 test(T-025): add provider adapter interfaces with mocked tests`
- `0d0cbb6 chore(T-025): merge provider adapter interfaces with mocked tests`

### T-024: Add export/download contracts for pages, comparisons, sources, and chat

Goal:
Add deterministic accountless export/download API contracts for fixture-backed asset pages, comparison output, source lists, and chat transcripts so users can save learning outputs with citations, source metadata, freshness context, and the educational disclaimer, without adding live calls or unsupported asset facts.

Completed:

- Added typed export contract models in `backend/models.py`, including `ExportFormat`, `ExportContentType`, `ExportState`, `ExportExcerpt`, `ExportSourceMetadata`, `ExportCitation`, `ExportedItem`, `ExportedSection`, `ExportNote`, `ComparisonExportRequest`, `ChatTranscriptExportRequest`, `ExportResponse`, and the reusable `EDUCATIONAL_DISCLAIMER`.
- Added `backend/export.py` with deterministic `export_asset_page`, `export_asset_source_list`, `export_comparison`, and `export_chat_transcript` functions that shape existing local overview, source, comparison, and chat outputs into JSON/Markdown-style export payloads.
- Added the export licensing note `export_licensing_scope`, including citation IDs, source attribution, freshness metadata, short allowed fixture passages, and an explicit restriction against exporting full paid-news articles, full filings, full issuer documents, or restricted provider payloads unless rights are confirmed.
- Wired export API routes in `backend/main.py`: `GET /api/assets/{ticker}/export`, `GET /api/assets/{ticker}/sources/export`, `POST /api/compare/export`, `GET /api/compare/export`, and `POST /api/assets/{ticker}/chat/export`.
- Asset-page exports preserve asset identity, page freshness, beginner summary, exactly three top risks first, recent developments separated from stable facts, educational suitability, PRD sections, citation IDs, source metadata, rendered Markdown, disclaimer, and licensing note for supported local assets.
- Source-list exports preserve source document ID, title, source type, publisher, URL, published/as-of date, retrieved timestamp, freshness state, official-source flag, metadata, and short allowed excerpt notes without exporting full source documents.
- Comparison exports preserve left/right asset identity, key differences, beginner bottom line, comparison type metadata, citation IDs, comparison source metadata, rendered Markdown, disclaimer, and licensing note for `VOO` vs `QQQ` in both directions.
- Chat transcript exports preserve ticker, question, direct answer, why-it-matters text, uncertainty notes, safety classification, citations, source metadata, disclaimer, and licensing note.
- Advice-like chat transcript exports preserve the educational redirect and avoid generated factual citations or source documents for the redirected answer.
- Unsupported, unknown, unavailable-comparison, unsupported-comparison, and eligible-not-cached export requests return `unsupported` or `unavailable` states with no generated factual sections, citations, source documents, pages, chat answers, comparisons, or invented facts.
- Added focused export tests in `tests/unit/test_exports.py`, API route coverage in `tests/integration/test_backend_api.py`, and export static eval coverage in `evals/export_eval_cases.yaml` plus `evals/run_static_evals.py`.
- Extended safety guardrail coverage so `backend/export.py` is scanned for forbidden advice-like output.
- Added `docs/agent-journal/20260422T081035Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-024 agent journal records that `git status --short`, focused export/API pytest, safety guardrail pytest, full pytest, frontend smoke via `npm test`, static evals, and the full quality gate passed.
- T-024 agent journal records focused export/API pytest as 26 passed, safety guardrail pytest as 4 passed, full pytest as 83 passed, frontend smoke as passed, static evals as passed, and the quality gate as passed including Python tests, static evals, frontend smoke, TypeScript typecheck, production build, and backend checks.
- Remaining documented risk: exports are JSON/Markdown-style contract payloads only; no PDF rendering, file storage, browser download controls, clipboard behavior, persistence, analytics, caching, provider adapters, or live ingestion were added.
- Remaining documented risk: exported content is limited to existing deterministic local overview, comparison, source, and chat outputs; it does not add new evidence or fill existing unknown, stale, unavailable, mixed, or insufficient-evidence gaps.
- Remaining documented risk: source excerpts are short local fixture supporting passages with licensing notes; final provider-specific redistribution rules still need legal/licensing review before using paid or restricted provider content.

Completion commits:

- `2e6ccf7 feat(T-024): add export/download contracts for pages, comparisons, sources, and chat`
- `df9a0f9 chore(T-024): merge export/download contracts for pages, comparisons, sources, and chat`

### T-023: Add hybrid glossary baseline terms and UI hooks

Goal:
Add a broader curated glossary baseline and deterministic frontend hooks so Beginner Mode can expose beginner-friendly finance terms for local fixture-backed stock and ETF pages without adding unsupported asset-specific claims or live calls.

Completed:

- Expanded `lib/glossary.ts` into a curated static glossary baseline covering the required PRD core terms, including ETF cost/size/structure/exposure/tracking/pricing/trading terms, stock company-size/fundamental/profitability/cash-generation/balance-sheet/valuation terms, and risk terms.
- Added `category` metadata to glossary entries and preserved short beginner-readable definitions, why-it-matters text, and common beginner mistakes for each curated term.
- Added stock and ETF glossary term groups in `lib/glossary.ts`, including `stock-business-metrics`, `stock-valuation-risk`, `etf-fund-basics`, `etf-exposure-risk`, and `etf-trading-tracking`.
- Added `getGlossaryTerm` lookup behavior so `GlossaryPopover` can accept a string term and handle unavailable terms without inventing definitions.
- Updated `components/GlossaryPopover.tsx` with stable glossary markers for term, category, definition, why-it-matters, beginner-mistake, and availability state.
- Preserved keyboard and screen-reader behavior in `GlossaryPopover` with `aria-expanded`, `aria-controls`, dialog labeling, and Escape handling for the open popover.
- Updated `app/assets/[ticker]/page.tsx` so fixture-backed Beginner Mode pages render a deterministic `Glossary for this page` learning area with stock/ETF term groups, asset ticker/type markers, and a no-generated-context marker.
- Kept inline glossary access near the beginner overview and made ETF pages show `expense ratio` and `index tracking`, while stock pages show `market risk` and `P/E ratio`.
- Added glossary learning-area CSS in `styles/globals.css`.
- Extended `tests/frontend/smoke.mjs` to require glossary catalog coverage, glossary UI markers, glossary term groups, generic-education/no-generated-context markers, no asset-specific glossary claims in `lib/glossary.ts`, preservation of fixture-backed citations/freshness/source checks, and absence of live external glossary calls.
- T-023 agent journal records that `git status --short`, `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, static evals, and the full quality gate passed.
- T-023 agent journal records the full quality gate as passed with Python tests 73 passed, frontend smoke checks passed, production build passed and prerendered `/assets/VOO`, `/assets/QQQ`, and `/assets/AAPL`, and backend checks 73 passed.
- Remaining documented risk: glossary content is static frontend data only; it does not add backend glossary APIs, generated asset-specific glossary context, glossary detail pages, exports, analytics, or persistence.
- Remaining documented risk: AAPL, VOO, and QQQ glossary hooks are grouped by asset type and local page vocabulary, but they do not fill existing explicit evidence gaps such as unavailable ETF exposure/trading metrics or stock valuation metrics.
- Remaining documented risk: glossary entries are generic educational explanations and are intentionally not citation sources for asset-specific claims.

Completion commits:

- `c22f022 feat(T-023): add hybrid glossary baseline terms and UI hooks`
- `3e53e25 chore(T-023): merge hybrid glossary baseline terms and UI hooks`

### T-022: Add Beginner Mode and Deep-Dive Mode page structure

Goal:
Add a clear Beginner Mode first and Deep-Dive Mode baseline structure to the fixture-backed asset pages so beginners can start with the plain-English learning view and still reach the richer cited PRD sections without live calls.

Completed:

- Added `components/AssetModeLayout.tsx` with accessible Beginner Mode and Deep-Dive Mode regions, stable frontend markers, and a sidebar area for source and learning tools.
- Updated `app/assets/[ticker]/page.tsx` so `AAPL`, `VOO`, and `QQQ` render Beginner Mode first and Deep-Dive Mode second through the new layout component.
- Built the Beginner Mode flow from existing local fixture data: plain-English beginner overview, primary citation chip, page and section freshness labels, glossary access, exactly three top risks first, stable fact details, visually separate recent developments, educational suitability copy, and the existing asset chat panel.
- Preserved educational framing in Beginner Mode without adding buy/sell/hold, allocation, tax, brokerage, or price-target language.
- Preserved Deep-Dive Mode rendering by routing `AAPL` through `AssetStockSections` and `VOO`/`QQQ` through `AssetEtfSections`.
- Preserved the existing stock PRD section IDs for `AAPL`: `business_overview`, `products_services`, `strengths`, `financial_quality`, `valuation_context`, `top_risks`, `recent_developments`, and `educational_suitability`.
- Preserved the existing ETF PRD section IDs for `VOO` and `QQQ`: `fund_objective_role`, `holdings_exposure`, `construction_methodology`, `cost_trading_context`, `etf_specific_risks`, `similar_assets_alternatives`, `recent_developments`, and `educational_suitability`.
- Updated source-tool rendering on the asset page so pages with PRD sections render `SourceDrawer` entries for section source documents with related claim contexts; the primary-source fallback remains for pages without PRD sections.
- Added CSS for the two-mode layout, mode stack, mode regions, and mode headings in `styles/globals.css`.
- Extended frontend smoke checks to require mode layout markers, Beginner Mode ordering, top-risk ordering, stable/recent separation, chat placement, PRD section preservation, source/citation/freshness availability, risk count preservation, and no live external calls from the mode layout.
- Extended safety guardrail coverage so `components/AssetModeLayout.tsx` is scanned for forbidden advice-like frontend copy.
- Added `docs/agent-journal/20260422T070202Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-022 agent journal records that `git status --short`, `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, static evals, and the full quality gate passed.
- T-022 agent journal records the full quality gate as passed with Python tests 73 passed, frontend smoke checks passed, production build passed and prerendered `/assets/VOO`, `/assets/QQQ`, and `/assets/AAPL`, and backend checks 73 passed.
- Remaining documented risk: the mode structure is frontend-only and fixture-backed; it does not add backend overview calls, ingestion, providers, caching, export, glossary expansion, comparison changes, or chat behavior changes.
- Remaining documented risk: Beginner Mode reuses existing local fixture fields and citations; it does not add new evidence or fill existing unknown, stale, unavailable, insufficient-evidence, or no-high-signal gaps.
- Remaining documented risk: Deep-Dive Mode preserves the existing stock and ETF PRD section components, so source drawer links still use the existing source-document drawer anchor pattern rather than per-citation deep links.

Completion commits:

- `fd7d0f5 feat(T-022): add Beginner Mode and Deep-Dive Mode page structure`
- `65c538f chore(T-022): merge Beginner Mode and Deep-Dive Mode page structure`

### T-021: Render ETF PRD sections on asset pages

Goal:
Render the richer ETF PRD overview sections for the local `VOO` and `QQQ` asset pages so beginners can inspect fund objective/role, holdings/exposure, construction/methodology, cost/trading limitations, ETF-specific risks, similar-assets gaps, recent developments, educational suitability, citations, and freshness states in the frontend without live calls.

Completed:

- Added `components/AssetEtfSections.tsx` to render ETF-only PRD sections from deterministic local fixtures with section, item, metric, evidence-state, freshness-state, stable/recent-separation, and top-risk-count markers.
- Updated `app/assets/[ticker]/page.tsx` so `VOO` and `QQQ` use the ETF PRD section path while `AAPL` continues to use the stock PRD section path.
- Updated the asset-page sidebar source handling so PRD-section pages render source drawers for the section source documents instead of a single primary-source fallback.
- Extended `lib/fixtures.ts` with ETF section fixture data for `VOO` and `QQQ`, including ETF section items, metrics, citation IDs, source-document bindings, citation contexts, and explicit evidence-gap states.
- Rendered the VOO and QQQ ETF PRD sections for `fund_objective_role`, `holdings_exposure`, `construction_methodology`, `cost_trading_context`, `etf_specific_risks`, `similar_assets_alternatives`, `recent_developments`, and `educational_suitability`.
- Rendered VOO source-backed S&P 500 benchmark and broad U.S. large-company ETF role details from the local fixture.
- Rendered QQQ source-backed Nasdaq-100 benchmark and narrower growth-oriented ETF role details from the local fixture.
- Preserved ETF holdings, methodology, trading-data, similar-assets, and recent-development evidence gaps instead of inventing unsupported facts.
- Preserved exactly three ETF-specific risk items first, with citation chips and no extra risk claims inserted ahead of them.
- Added CSS for ETF PRD section spacing, ETF section item cards, compact evidence-state pills, evidence-gap notes, and ETF item headings.
- Extended frontend smoke checks to require ETF PRD component markers, VOO and QQQ ETF section IDs, ETF citation/source markers, explicit gap markers, source drawer metadata hooks, freshness and stable/recent markers, exactly three ETF top risks, AAPL stock-section preservation, no cross-asset source binding, no asset-page backend overview calls, and no live external calls.
- Extended safety guardrail coverage so `components/AssetEtfSections.tsx` is scanned for forbidden advice-like frontend copy.
- Added `docs/agent-journal/20260422T063309Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-021 agent journal records that `git status --short`, `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, static evals, and the full quality gate passed.
- T-021 agent journal records the final quality gate as passed with Python tests 73 passed, static evals passed, frontend smoke passed, typecheck passed, production build passed, and backend checks 73 passed.
- Remaining documented risk: ETF PRD sections are deterministic local frontend fixtures only; no backend overview calls, provider adapters, ingestion, caching, chat, comparison, glossary, or export behavior were added.
- Remaining documented risk: VOO and QQQ still show explicit evidence gaps for top-10 weights, top-10 concentration, sector exposure, country exposure, largest-position data, full methodology details, bid-ask spread, average volume, premium/discount, holdings overlap, similar ETFs, simpler alternatives, and diversification-addition claims.
- Remaining documented risk: source drawers expose local fixture source metadata and related claim context, but citation links still target the existing source-document drawer anchors rather than deep-linking to an individual citation row.

Completion commits:

- `5adaf8d feat(T-021): render ETF PRD sections on asset pages`
- `bf3aea9 chore(T-021): merge render ETF PRD sections on asset pages`

### T-020: Render stock PRD sections on asset pages

Goal:
Render the richer stock PRD overview sections for the local `AAPL` asset page so beginners can inspect stock business, products/services, strengths, financial quality, valuation-context limitations, top risks, recent developments, educational suitability, citations, and freshness states in the frontend without live calls.

Completed:

- Added `components/AssetStockSections.tsx` to render stock-only PRD sections from deterministic local fixtures with section, item, metric, evidence-state, freshness-state, stable/recent-separation, and top-risk-count markers.
- Updated `app/assets/[ticker]/page.tsx` so `AAPL` uses the stock PRD section path while `VOO` and `QQQ` intentionally stay on the existing ETF rendering path until T-021.
- Updated the asset-page sidebar so stock PRD pages render source drawers for the stock section source documents instead of a single primary-source fallback.
- Extended `components/SourceDrawer.tsx` to accept citation contexts, render related claim context lists, and deduplicate supporting passages while preserving title, source type, publisher, URL, published/as-of date, retrieved timestamp, freshness state, and official-source metadata.
- Extended `lib/fixtures.ts` with stock-section fixture types, AAPL `stockSections`, `citationContexts`, additional AAPL source-document bindings, and citation IDs for primary business, products/services detail, business-quality strength, SEC XBRL net sales trend, valuation-data limitation, risk context, and no-high-signal recent-development review.
- Rendered the AAPL stock PRD sections for `business_overview`, `products_services`, `strengths`, `financial_quality`, `valuation_context`, `top_risks`, `recent_developments`, and `educational_suitability`.
- Preserved explicit evidence gaps in the AAPL UI for business segments, revenue drivers, geographic exposure, competitor detail, earnings, margins, cash flow, debt, cash, ROE, ROIC, valuation metrics, and no high-signal recent developments instead of inventing unsupported facts.
- Preserved exactly three AAPL top risks first, with citation chips and no extra risk claims inserted ahead of them.
- Added CSS for stock PRD section spacing, stock section item cards, compact evidence-state pills, evidence-gap notes, and source context lists.
- Extended frontend smoke checks to require the new stock PRD component, AAPL section IDs, AAPL section citation/source markers, explicit gap markers, source drawer metadata hooks, stable/recent markers, exactly three top risks, no `stockSections` on `VOO` or `QQQ`, no asset-page backend overview calls, and no live external calls.
- Extended safety guardrail coverage so `components/AssetStockSections.tsx` is scanned for forbidden advice-like frontend copy.
- Added `docs/agent-journal/20260422T060036Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-020 agent journal records that `git status --short`, `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, static evals, and the full quality gate passed.
- T-020 agent journal records the final quality gate as passed with Python tests 73 passed, static evals passed, frontend smoke passed, typecheck passed, production build passed, and backend checks 73 passed.
- Remaining documented risk: AAPL stock PRD sections are deterministic local frontend fixtures only; no backend overview API calls, provider adapters, ingestion, caching, export, chat, comparison, glossary, or ETF-section behavior were added.
- Remaining documented risk: VOO and QQQ intentionally remain on the existing ETF page rendering path; ETF PRD section rendering is left for T-021.
- Remaining documented risk: AAPL still shows explicit evidence gaps for business segments, revenue drivers, geographic exposure, competitor detail, earnings, margins, cash flow, debt, cash, ROE, ROIC, and valuation metrics.
- Remaining documented risk: source drawers expose local fixture source metadata and claim context, but do not deep-link per citation beyond the existing source-document drawer anchor pattern.

Completion commits:

- `56e1a07 feat(T-020): render stock PRD sections on asset pages`
- `48d9db2 chore(T-020): merge render stock PRD sections on asset pages`

### T-019: Add richer stock and ETF fixture data for MVP content sections

Goal:
Add richer deterministic local retrieval fixture evidence so the PRD asset overview sections introduced in T-018 can carry more source-backed stock and ETF content without live calls, frontend rendering changes, or schema changes.

Completed:

- Expanded `data/retrieval_fixtures.json` for `AAPL` with additional same-asset source documents, chunks, and normalized facts for products/services detail, a business-quality strength, an FY2023-FY2024 net sales trend, and a cited valuation-data limitation.
- Added an `AAPL` SEC XBRL fixture source and a local valuation-data limitation source with source type, publisher, URL, published/as-of date, retrieved timestamp, freshness state, and official-source metadata.
- Expanded `data/retrieval_fixtures.json` for `VOO` and `QQQ` with holdings-file sources, holdings/exposure detail chunks, construction/methodology chunks, and local trading-data limitation sources.
- Added normalized ETF facts for holdings exposure detail, construction methodology, and trading-data limitations for both `VOO` and `QQQ`, with same-asset source document and chunk bindings.
- Updated `backend/overview.py` so AAPL stock sections consume the richer fixture facts: products/services uses supported product and services detail, strengths becomes supported when the business-quality point exists, financial quality becomes mixed with a net sales trend and residual metric gaps, and valuation context becomes mixed with a cited valuation limitation plus remaining valuation metric gaps.
- Updated `backend/overview.py` so VOO and QQQ ETF sections consume richer fixture facts for holdings exposure detail, construction methodology, and cited trading-data limitations while preserving residual gaps for full holdings weights, concentration, sector/country exposure, trading metrics, overlap, and alternatives.
- Preserved stable/recent separation, exactly three top risks first, educational framing, and blocking for unsupported, unknown, ambiguous, and eligible-not-cached assets.
- Extended `tests/unit/test_retrieval_fixtures.py` to require the richer stock and ETF fact fields for `AAPL`, `VOO`, and `QQQ`.
- Extended `tests/unit/test_overview_generation.py` and `tests/integration/test_backend_api.py` to verify richer stock and ETF section item IDs, citation/source presence, and updated evidence states.
- Extended `evals/run_static_evals.py` to cover richer fixture field coverage and richer generated overview section expectations.
- Added `docs/agent-journal/20260422T053337Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-019 agent journal records an initial focused test failure from an outdated T-018 assertion expecting AAPL strengths to remain unknown, followed by a focused revision and passing reruns.
- T-019 agent journal records focused retrieval/overview/safety/API pytest as 36 passed, full pytest as 73 passed, static evals as passed, and the quality gate as passed including Python tests, static evals, frontend smoke checks, typecheck, production build, and backend checks.
- Remaining documented risk: richer content remains deterministic local fixture evidence only; no provider adapters, live ingestion, embeddings, LLM calls, cache refresh, export behavior, or frontend rendering were added.
- Remaining documented risk: AAPL still has explicit gaps for segment, revenue-driver, geographic, competitor, margin, cash-flow, debt, cash, ROE/ROIC, and valuation metrics.
- Remaining documented risk: VOO and QQQ still have explicit gaps for full top-10 weights, concentration, sector/country exposure, largest position, full methodology details, bid-ask spread, average volume, premium/discount, overlap, and alternatives.
- Remaining documented risk: unsupported, unknown, ambiguous, and eligible-not-cached assets remain blocked from generated overview content, citations, source documents, chat answers, and comparison output.

Completion commits:

- `ef06a5e feat(T-019): add richer stock and ETF fixture data for MVP content sections`
- `693350f chore(T-019): merge richer stock and ETF fixture data for MVP content sections`

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

## Historical Backlog Note

This older scaffold note is retained only for history. Active runnable local fresh-data MVP tasks are prepared at the top of this file after the 2026-04-28 implementation-doc rebaseline.

## General MVP Roadmap

This section is intentionally non-operational for the agent loop. Keep runnable repeat-mode tasks above this roadmap as third-level task headings, and keep this longer MVP roadmap as bullets until each item is promoted into a narrow task contract. This roadmap now covers the full functional MVP path: deterministic launch readiness, Golden Asset Source Handoff, reviewed Top-500 candidate refreshes, server-side/admin ingestion, source snapshot storage, normalized knowledge-pack persistence, generated-output cache writes, Weekly News Focus execution, backend route reads, frontend API rendering, comparison/chat/export rendering, local fresh-data verification, and production readiness.

Current runtime snapshot:

- Backend contracts, configured reader boundaries, ingestion ledger execution, source-use/export gates, Weekly News contracts, generated-output cache contracts, and live-generation readiness diagnostics are broad and stable.
- The current runtime has deterministic local fresh-data ingest-to-render smoke coverage for a golden asset. Official-source acquisition remains mocked/golden-path, source snapshots, normalized knowledge packs, Weekly News evidence, and generated-output cache records can be routed through deterministic in-memory/mocked boundaries or explicitly configured local durable repository factories, and production persistence/storage is not the normal path.
- The frontend renders the main learning surfaces with deterministic fixtures and selected backend adapters; T-109 added API-backed home search and dynamic asset-page rendering with deterministic fixture fallback, and T-119 wired local chat, export, and comparison API access through configured backend URLs plus a Next `/api` rewrite fallback.
- The updated PRD/TDS/proposal make Golden Asset Source Handoff a blocker before retrieved sources can become evidence for storage, generation, citation, cache, source drawer, or export behavior.
- The updated Top-500 workflow keeps runtime stock support tied to the approved current manifest; T-116/T-124 added deterministic IWB/SPY/IVV/VOO candidate generation, SEC/Nasdaq validation, diff reporting, and manual-promotion gates, but no launch-sized candidate has been approved or promoted to the current manifest.
- T-119 closed the local frontend/API plumbing blockers found during manual smoke testing: chat POSTs, export URLs, comparison fetches, and browser direct backend calls now have a documented API-base/proxy/CORS strategy.
- T-120 through T-124 are completed: ETF manifest split contracts, localhost browser E2E smoke, optional local durable smoke, handoff-gated official-source fetcher boundaries, and reviewed launch-universe expansion planning.
- T-125 completed the v0.6 handoff-doc and MVP-backlog alignment pass.
- T-126 completed repo-native source-handoff manifest inspection/finalization smoke tooling for reviewed governed-source packets.
- T-127 completed the opt-in local live-AI validation smoke for grounded chat and AI Comprehensive Analysis.
- T-128 completed deterministic governed golden API/frontend rendering proof for the golden set.
- T-129 completed launch-manifest operator automation parity for Top-500 stock and supported ETF launch-manifest packets.
- T-130 completed the deterministic local fresh-data MVP rehearsal command.
- T-131 through T-135 completed the ETF eligible-universe, stock SEC source-pack readiness, ETF issuer source-pack readiness, local MVP readiness-threshold packets, and batchable local ingestion priority planner.
- The ETF-500 scope update is documented across the product and handoff docs; T-136 completed deterministic ETF-500 candidate manifest review contracts, and T-137 completed ETF-500 issuer source-pack batch planning contracts.
- T-138 completed deterministic Top-500 SEC source-pack batch planning contracts, T-139 completed the local manual fresh-data readiness gate, T-140 completed the backend/API-backed `AAPL` vs `VOO` stock-vs-ETF comparison pack, T-141 aligned frontend/API comparison availability, T-142 completed local browser/API smoke coverage, T-143 completed the deterministic stock-vs-ETF readiness-reporting gate, T-144 completed the first local fresh-data MVP slice smoke contract, and T-145 completed the local slice browser/API smoke task. T-146 is now the current optional durable repository smoke task for the local slice, with T-147 through T-149 staged as follow-on local slice backlog before production hardening.
- T-118 documented and regression-covered the deterministic local fresh-data ingest-to-render smoke path before production hardening. Production deployment, production durable storage, scheduled jobs, full governed source artifacts, admin auth/rate limiting, broader live ingestion, and launch-sized reviewed manifests remain unpromoted.

Operational defaults for general MVP roadmap tasks:

- T-076 established the persistence boundary and migration tooling before provider or worker work starts. It is completed and must not be reintroduced as runnable backlog.
- T-077 established persisted knowledge-pack repository contracts. It is completed and must not be reintroduced as runnable backlog.
- T-078 routed retrieval through persisted packs with deterministic fixture fallback. It is completed and must not be reintroduced as runnable backlog.
- T-079 established the dormant persisted ingestion job ledger contract. It is completed and must not be reintroduced as runnable backlog.
- T-080 established the deterministic ingestion worker execution contract on top of injected ledger records. It is completed and must not be reintroduced as runnable backlog.
- T-081 established dormant source snapshot artifact metadata contracts. It is completed and must not be reintroduced as runnable backlog.
- T-082 established fixture-backed SEC stock source adapter/parser contracts without live SEC calls, route wiring, generated-output changes, or broader stock coverage. It is completed and must not be reintroduced as runnable backlog.
- T-083 established fixture-backed ETF issuer/holdings source adapter contracts without live issuer/provider calls, route wiring, generated-output changes, or unsupported ETF expansion. It is completed and must not be reintroduced as runnable backlog.
- T-084 established dormant persisted generated-output cache and freshness-hash contracts. It is completed and must not be reintroduced as runnable backlog.
- T-085 established injected persisted-read routing for asset overview generation with fixture fallback. It is completed and must not be reintroduced as runnable backlog.
- T-086 established injected persisted-read routing for comparison generation with fixture fallback. It is completed and must not be reintroduced as runnable backlog.
- T-087 established injected persisted-read routing for grounded chat answer artifacts with fixture fallback. It is completed and must not be reintroduced as runnable backlog.
- T-088 established dormant accountless chat session persistence contracts without route wiring, frontend changes, live database/cache execution, provider/LLM calls, analytics emission, or export rewrites. It is completed and must not be reintroduced as runnable backlog.
- T-089 established injected persisted chat session lifecycle and transcript export boundaries after T-088 contracts. It is completed and must not be reintroduced as runnable backlog.
- T-090 established dormant trust-metric event sink persistence contracts without real analytics emission, frontend instrumentation, route wiring, live database execution, or external analytics vendors. It is completed and must not be reintroduced as runnable backlog.
- T-091 established eligible ETF universe metadata contracts. It is completed and must not be reintroduced as runnable backlog.
- T-092 established route-level manifest-backed search support classification. It is completed and must not be reintroduced as runnable backlog.
- T-093 established dormant Weekly News Focus event evidence contracts. It is completed and must not be reintroduced as runnable backlog.
- T-094 established deterministic Weekly News Focus acquisition/selection. It is completed and must not be reintroduced as runnable backlog.
- T-095 established route-level persisted-read fallback for Weekly News Focus. It is completed and must not be reintroduced as runnable backlog.
- T-096 established live LLM runtime readiness diagnostics. It is completed and must not be reintroduced as runnable backlog.
- T-097 established the gated OpenRouter transport adapter with mocked tests. It is completed and must not be reintroduced as runnable backlog.
- T-098 established live-generation validation and fallback orchestration after the mocked transport boundary. It is completed and must not be reintroduced as runnable backlog.
- T-099 established deterministic provider content export-rights hardening. It is a prerequisite rights gate, not the runtime fresh-data completion point.
- T-100 established the backend MVP runtime gap audit and roadmap tracker. It is completed and must not be reintroduced as runnable backlog.
- T-101 established configured persisted-reader route wiring with fixture fallback. It is completed and must not be reintroduced as runnable backlog.
- T-102 established executable local ingestion ledger and mocked worker transitions. It is completed and must not be reintroduced as runnable backlog.
- T-103 established mocked SEC EDGAR stock golden-path acquisition. It is completed and must not be reintroduced as runnable backlog.
- T-104 established mocked official ETF issuer golden-path acquisition. It is completed and must not be reintroduced as runnable backlog.
- T-105 established deterministic source snapshot and parsed acquisition artifact persistence. It is completed and must not be reintroduced as runnable backlog.
- T-106 established deterministic normalized knowledge-pack writes from acquisition outputs. It is completed and must not be reintroduced as runnable backlog.
- T-107 established deterministic persisted Weekly News Focus event evidence for golden assets. It is completed and must not be reintroduced as runnable backlog.
- T-108 established deterministic generated-output cache writes and freshness invalidation for validated golden-path outputs. It is completed and must not be reintroduced as runnable backlog.
- T-109 established frontend API-backed search, pending states, and dynamic asset-page rendering. It is completed and must not be reintroduced as runnable backlog.
- T-110 established persisted end-to-end comparison, chat, source, glossary, Weekly News, and export verification. It is completed and must not be reintroduced as runnable backlog.
- T-111 established local durable repository execution with in-memory fallback. It is completed and must not be reintroduced as runnable backlog.
- T-112 established opt-in live SEC and ETF issuer golden acquisition readiness. It is completed and must not be reintroduced as runnable backlog.
- T-113 established opt-in official-source Weekly News live acquisition readiness for golden assets. It is completed and must not be reintroduced as runnable backlog.
- T-114 established deterministic launch pre-cache expansion and the MVP readiness regression matrix. It is completed and must not be reintroduced as runnable backlog.
- T-115 established Golden Asset Source Handoff contract enforcement. It is completed and must not be reintroduced as runnable backlog.
- T-116 established reviewed Top-500 candidate manifest workflow contracts. It is completed and must not be reintroduced as runnable backlog.
- T-117 established handoff-gated mocked official-source acquisition execution for golden assets. It is completed and must not be reintroduced as runnable backlog.
- T-118 established the local fresh-data ingest-to-render runbook and deterministic smoke coverage. It is completed and must not be reintroduced as runnable backlog.
- T-119 established local frontend API access and backend CORS for chat, exports, comparison, and direct browser API calls. It is completed and must not be reintroduced as runnable backlog.
- T-120 established the v0.5 split between supported ETF generated-output coverage and ETF/ETP recognition-only blocked states. It is completed and must not be reintroduced as runnable backlog.
- T-121 established optional localhost browser/API E2E smoke. It is completed and must not be reintroduced as runnable backlog.
- T-122 established optional local durable repository smoke with API proxy/CORS enabled. It is completed and must not be reintroduced as runnable backlog.
- T-123 established handoff-gated official-source fetcher boundaries behind local opt-in. It is completed and must not be reintroduced as runnable backlog.
- T-124 established reviewed launch-universe expansion planning. It is completed and must not be reintroduced as runnable backlog.
- T-125 established v0.6 docs, handoff docs, and backlog alignment. It is completed and must not be reintroduced as runnable backlog.
- T-126 established repo-native source-handoff manifest smoke tooling. It is completed and must not be reintroduced as runnable backlog.
- T-127 established opt-in local live-AI validation smoke. It is completed and must not be reintroduced as runnable backlog.
- T-128 established deterministic governed golden evidence API/frontend rendering proof. It is completed and must not be reintroduced as runnable backlog.
- T-129 established launch-manifest operator automation parity. It is completed and must not be reintroduced as runnable backlog.
- T-130 established the local fresh-data MVP rehearsal command. It is completed and must not be reintroduced as runnable backlog.
- T-134 through T-145 are completed. T-146 is the current optional durable repository smoke task for the local fresh-data MVP slice, and T-147 through T-149 are prepared backlog headings for the remaining local slice path.
- Production hardening remains unpromoted until a new narrow launch-readiness task is explicitly prepared.
- Full production deployment, recurring production jobs, broad paid-provider integrations, and post-MVP features move later until explicit launch readiness work is promoted into a narrow task and passes deterministic CI coverage.
- Later promoted tasks must keep live providers, secrets, deployment credentials, broad pre-cache refreshes, and recurring jobs out of normal CI until the explicit production-hardening stage.
- Each promoted task should run the relevant EVALS.md checks, `python3 -m pytest tests -q`, `python3 evals/run_static_evals.py`, `bash scripts/run_quality_gate.sh`, and `git diff --check`.

Roadmap integration tracker:

| Roadmap area | Status | Task mapping |
| --- | --- | --- |
| Persistence settings and migration scaffold | Completed | T-076 |
| Persisted knowledge-pack repository contracts | Completed | T-077 |
| Persisted-pack-first retrieval with fixture fallback | Completed | T-078 |
| Ingestion job ledger | Completed | T-079 |
| Deterministic ingestion worker execution path | Completed | T-080 |
| Source snapshot storage metadata | Completed | T-081 |
| SEC stock source adapter/parser | Completed | T-082 |
| ETF issuer, holdings, prospectus, and exposure adapters | Completed | T-083 |
| Generated-output cache and freshness hashes | Completed | T-084 |
| Route overview generation through persisted packs/cache | Completed | T-085 |
| Route comparison generation through persisted packs/cache | Completed | T-086 |
| Route grounded chat answer artifacts through persisted packs/cache | Completed | T-087 |
| Accountless chat session persistence contracts | Completed | T-088 |
| Persisted chat session lifecycle and exports | Completed | T-089 |
| Trust-metric event sink | Completed | T-090 |
| Eligible ETF universe metadata contracts | Completed | T-091 |
| Manifest-backed search support classification | Completed | T-092 |
| Weekly News Focus persisted event evidence contracts | Completed | T-093 |
| Weekly News Focus deterministic acquisition/selection | Completed | T-094 |
| Weekly News Focus persisted-read fallback | Completed | T-095 |
| Live LLM runtime readiness diagnostics | Completed | T-096 |
| Gated OpenRouter mocked transport adapter | Completed | T-097 |
| Live-generation validation and fallback orchestration | Completed | T-098 |
| Provider source-use/export enforcement hardening | Completed | T-099 |
| Backend fresh-data MVP runtime gap tracker | Completed | T-100 |
| Configured persisted-reader route wiring | Completed | T-101 |
| Executable local ingestion ledger and mocked worker path | Completed | T-102 |
| SEC EDGAR stock golden-path acquisition | Completed | T-103 |
| Official ETF issuer golden-path acquisition | Completed | T-104 |
| Source snapshot and parsed acquisition artifact persistence | Completed | T-105 |
| Normalized knowledge-pack writes from ingestion | Completed | T-106 |
| Weekly News Focus official-source event evidence persistence | Completed | T-107 |
| Generated-output cache writes and invalidation | Completed | T-108 |
| Frontend API-backed search, pending states, and asset rendering | Completed | T-109 |
| Persisted comparison/chat/source/glossary/export end-to-end verification | Completed | T-110 |
| Local durable repository execution with in-memory fallback | Completed | T-111 |
| Opt-in live SEC and ETF issuer golden acquisition | Completed | T-112 |
| Official-source Weekly News live acquisition for golden assets | Completed | T-113 |
| Launch pre-cache expansion and MVP readiness regression matrix | Completed | T-114 |
| Golden Asset Source Handoff contract enforcement | Completed | T-115 |
| Reviewed Top-500 candidate manifest workflow contracts | Completed | T-116 |
| Handoff-gated official-source acquisition execution for golden assets | Completed | T-117 |
| Local fresh-data ingest-to-render runbook and smoke coverage | Completed | T-118 |
| Local frontend API access and backend CORS | Completed | T-119 |
| Split supported ETF and recognition manifests | Completed | T-120 |
| Optional localhost browser/API smoke | Completed | T-121 |
| Optional local durable API proxy smoke | Completed | T-122 |
| Handoff-gated official-source fetcher boundaries | Completed | T-123 |
| Reviewed launch-universe expansion planning | Completed | T-124 |
| v0.6 docs, handoff docs, and backlog alignment | Completed | T-125 |
| Repo-native source-handoff manifest smoke tooling | Completed | T-126 |
| Opt-in local live-AI validation smoke | Completed | T-127 |
| Governed golden evidence API/frontend rendering proof | Completed | T-128 |
| Launch-manifest operator automation parity | Completed | T-129 |
| Local fresh-data MVP rehearsal command | Completed | T-130 |
| ETF eligible-universe review packet contracts | Completed | T-131 |
| Stock SEC source-pack readiness packets | Completed | T-132 |
| ETF issuer source-pack readiness packets | Completed | T-133 |
| Local fresh-data MVP readiness thresholds | Completed | T-134 |
| Batchable local ingestion priority planner | Completed | T-135 |
| ETF-500 candidate manifest review contracts | Completed | T-136 |
| ETF-500 issuer source-pack batch planning | Completed | T-137 |
| Top-500 SEC source-pack batch planning | Completed | T-138 |
| Local manual fresh-data readiness gate | Completed | T-139 |
| Backend AAPL-vs-VOO stock-vs-ETF comparison pack | Completed | T-140 |
| Frontend comparison suggestions API-availability alignment | Completed | T-141 |
| Local AAPL-vs-VOO browser/API smoke coverage | Completed | T-142 |
| Stock-vs-ETF comparison readiness gate | Completed | T-143 |
| Local fresh-data MVP slice smoke contract | Completed | T-144 |
| Local fresh-data MVP browser/API smoke for the slice | Completed | T-145 |
| Optional durable repository smoke for the local fresh-data MVP slice | Current | T-146 |
| Issuer-backed ETF source enrichment for the local fresh-data MVP slice | Prepared | T-147 |
| Lightweight local manual-readiness gate for the MVP slice | Prepared | T-148 |
| Local fresh-data MVP slice comparison and export parity coverage | Prepared | T-149 |
| Full production deployment, recurring jobs, and broad paid-provider integrations | Later | Unpromoted |

Remaining unpromoted general MVP sequence:

- T-139 produced a deterministic readiness gate that says whether more agent-loop work remains or whether manual local fresh-data testing is the next step.
- The stock-vs-ETF comparison feature-completion sequence is complete through the final prepared step: T-141 aligned frontend suggestions/fallback with API availability, T-142 added optional localhost browser/API smoke coverage, and T-143 added the deterministic readiness signal. The promoted local fresh-data MVP slice sequence has completed T-145 and continues with T-146.
- Full production deployment remains unpromoted until a narrow launch-readiness task is added: admin auth enforcement, rate limiting, deployment env validation, private object storage, database migration execution, Cloud Run/Job settings, monitoring, and rollback/go-no-go procedures.
- Recurring production jobs only after manual official-source acquisition, Top-500 candidate refresh review, and local fresh-data behavior are stable.
- Broad paid-provider or news-provider integrations only after provider licensing/source-use review, no-secret-exposure tests, mocked CI fixtures, source-rights validation, and export/display constraints are documented.
- Post-MVP features such as accounts, saved assets, watchlists, PDF exports, localization, richer analytics dashboards, and broad provider enrichment remain out of the fully functional MVP stage.
