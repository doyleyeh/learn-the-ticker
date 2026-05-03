# Local Fresh-Data Ingest-To-Render Runbook

Task: T-118, updated by T-119 through T-149 local API, manifest, durable-smoke, v0.6 handoff alignment, local MVP rehearsal, readiness thresholds, ingestion priority planning, AAPL-vs-VOO stock-vs-ETF localhost smoke coverage, stock-vs-ETF comparison readiness gating, local fresh-data MVP slice smoke coverage, optional slice browser/API localhost coverage, optional durable slice smoke coverage, lightweight local-slice manual-readiness gating, and local slice comparison/export parity coverage

This runbook describes the local golden-asset smoke path before production deployment work. Normal CI uses deterministic fixtures, mocked official-source acquisition, and in-memory repositories. It must not require real SEC, issuer, market-data, broad news, storage, database, Redis, RSS, or LLM calls.

Fetching alone is retrieval, not evidence approval. For strict/audit-quality evidence promotion, a retrieved source can support snapshots, normalized facts, citations, generated-output cache records, exports, or rendered UI only after Golden Asset Source Handoff approves source identity, source type, official-source status, storage rights, export rights, source-use policy, parser status, freshness/as-of metadata, and review status. For the personal lightweight MVP, `docs/LIGHTWEIGHT_DATA_POLICY.md` allows source-labeled official/provider-derived display before full handoff approval when raw payloads stay hidden, provenance and freshness are visible, and missing fields render as partial or unavailable.

ETF support note: T-120 implemented the split between supported ETF generated-output coverage and ETF/ETP recognition-only blocked states. ETF-500 is the v1 supported ETF target, while golden/pre-cache ETFs remain regression assets. Local smoke should verify supported ETF output comes from `data/universes/us_equity_etfs_supported.current.json` and recognition-only rows from `data/universes/us_etp_recognition.current.json` never unlock generated output.

## Local Modes

Use one of these local modes:

- `in_memory`: deterministic smoke mode. Uses injected in-memory ledgers and repositories. This is the CI-safe path.
- `local_durable`: optional operator-only local repository mode. Use placeholder-only local connection settings and never print credential values. This mode is for manual inspection only and is not required by CI.
- `operator_live_experiment`: optional local experiment mode. Keep it disabled by default. Lightweight fresh-data fetches may render source-labeled normalized facts for local review, while strict/audit-quality promotion still requires source handoff, citation, source-use, freshness, and safety validation. Do not commit fetched payloads, generated answers, logs, or diagnostics from this mode.

## One-Command MVP Rehearsal

Task: T-130.

Use the local rehearsal before production hardening work:

```bash
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
```

The default rehearsal is deterministic and fixture-backed. It checks:

- Golden Asset Source Handoff approval and blocked states before evidence use.
- governed golden API reads for overview, source drawer, exports, comparison, chat, Weekly News Focus, and AI Comprehensive Analysis threshold suppression.
- deterministic local fresh-data MVP slice smoke for `AAPL`, `MSFT`, `NVDA`, `VOO`, `SPY`, `VTI`, `QQQ`, and `XLK`, plus blocked examples `TQQQ`, `ARKK`, `BND`, and `GLD`.
- local slice comparison/export parity through `local_fresh_data_mvp_slice_comparison_export_parity`.
- unsupported, out-of-scope, pending-ingestion, and unknown asset blocking.
- launch-manifest review packets without promotion or launch approval.
- v0.4 frontend smoke markers for single-asset home search, separate comparison, contextual glossary, mobile source/glossary/chat surfaces, stock-vs-ETF relationship structure, citation/source export scope, and evidence-limited Weekly News Focus.
- a lightweight local MVP slice manual-readiness gate named `lightweight_local_mvp_slice_manual_readiness_gate`, separate from the broader `manual_fresh_data_readiness_gate`.

The JSON output reports each check as `pass`, `skipped`, or `blocked`. Optional checks are skipped unless their rehearsal flag is set:

```bash
LTT_REHEARSAL_BROWSER_SERVICES_ENABLED=true \
LTT_REHEARSAL_DURABLE_REPOSITORIES_ENABLED=true \
LTT_REHEARSAL_OFFICIAL_SOURCE_RETRIEVAL_ENABLED=true \
LTT_REHEARSAL_LIVE_AI_REVIEW_ENABLED=true \
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
```

Optional-mode meanings:

- browser services: checks already-running localhost web/API services and local CORS/proxy behavior.
- durable repositories: checks local durable repository prerequisites and reports sanitized blockers when the local DSN or private object namespace is missing or unsafe.
- official-source retrieval: when `LIGHTWEIGHT_LIVE_FETCH_ENABLED=true` is also set, runs the lightweight `AAPL` and `VOO` fresh-data smoke; otherwise it reports sanitized missing prerequisites. The required deterministic slice smoke covers the expanded local MVP ticker set without live calls. Neither path approves sources, promotes manifests, writes source snapshots, or exposes raw provider payloads.
- live-AI review: delegates to the operator-only live-AI validation smoke and reports sanitized pass or blocker states.

Stop when any required deterministic check is `blocked`, or when an opted-in optional check is `blocked`. The rehearsal does not start production services, approve sources, promote manifests, write production storage, require live calls by default, or make fixture-sized/local-only data launch-approved.

## Lightweight Local MVP Slice Manual-Readiness Gate

Task: T-148.

`TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` returns `lightweight_local_mvp_slice_manual_readiness_gate` with schema `lightweight-local-mvp-slice-manual-readiness-gate-v1`. This is a slice-specific readiness signal for the local fresh-data MVP slice only. It can say `deterministic_local_slice_manual_review_ready` while the broader `manual_fresh_data_readiness_gate` still says `agent_work_remaining` for ETF-500, Top-500, source-pack, parser, handoff, freshness/as-of, checksum, production, deployment, live-provider, and live-AI blockers.

The slice gate has three decision states:

- `deterministic_local_slice_manual_review_ready`: the deterministic slice is ready for explicit operator manual browser/API review.
- `local_slice_agent_work_remaining`: deterministic slice behavior regressed and agent-loop work remains before manual review.
- `optional_local_check_blocked`: the deterministic slice is ready, but an explicitly opted-in optional local check is blocked by sanitized prerequisites or validation failures.

Default deterministic readiness means all of these are true:

- `local_fresh_data_mvp_slice_smoke` reports `pass`.
- `normal_ci_requires_live_calls=false`, `browser_startup_required=false`, and `local_services_required=false`.
- `raw_payload_exposed_count=0`, `secret_values_reported=false`, and `raw_payload_values_reported=false`.
- status counts are `pass=5`, `partial=3`, `blocked=4`, and `unavailable=0`.
- `AAPL`, `MSFT`, and `NVDA` pass as stock rows.
- `VOO` and `QQQ` pass as issuer-backed ETF rows.
- `SPY`, `VTI`, and `XLK` remain partial ETF rows with explicit issuer-evidence gaps.
- `TQQQ`, `ARKK`, `BND`, and `GLD` remain blocked and receive no source documents, citations, facts, provider fetches, generated pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, generated risk summaries, or generated-output cache writes.
- the existing `VOO`/`QQQ` ETF-vs-ETF and `AAPL`/`VOO` stock-vs-ETF smoke markers remain intact, including separate `/compare` workflow, `A vs B` redirect behavior, relationship badges, the `single-company-vs-ETF-basket` structure, export/chat proxy checks, and no `holding_verified` regression.

Skipped optional checks are reported explicitly as operator-only prerequisites; they are not hidden as pass. The optional operator-only local checks include browser/API services, local durable repositories, official-source retrieval, and live-AI review. When an optional flag is set and the check is blocked, the slice gate reports `optional_local_check_blocked` with env var names and safe diagnostics only, never credential values.

The slice gate is not launch readiness. It does not approve ETF-500, Top-500, production, deployment, source-pack, parser, Golden Asset Source Handoff, checksum, live-provider, or live-AI readiness. It does not approve sources, promote manifests, start services, write production storage, write generated-output cache entries, or unlock blocked products. Source-use policy still applies: fetching is retrieval, not evidence approval; source-labeled official/provider-derived display is allowed for the personal lightweight MVP only while raw payloads stay hidden, rights-safe output limits are preserved, provenance/freshness are visible, and missing evidence renders as `partial`, `unknown`, `stale`, `unavailable`, or `insufficient_evidence`.

## Local Slice Comparison And Export Parity

Task: T-149.

`TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` returns the required check `local_fresh_data_mvp_slice_comparison_export_parity` with schema `local-fresh-data-mvp-slice-comparison-export-parity-v1`. The check is deterministic and fixture-backed. It is a local fresh-data MVP slice parity signal only, not readiness versus broad launch readiness.

`TMPDIR=/tmp python3 scripts/run_local_fresh_data_slice_smoke.py --json` also exposes `comparison_export_parity_summary` with schema `local-fresh-data-mvp-slice-comparison-export-parity-inputs-v1` so the rehearsal can verify the same supported, partial, and blocked ticker contracts without live services.

Representative parity coverage:

- `VOO`/`QQQ` ETF-vs-ETF: comparison response is available, source-backed, same-comparison-pack citation bound, exportable as JSON and Markdown, includes the educational disclaimer, preserves source-use policy and source freshness metadata, and contains no advice output, hidden prompts, raw model reasoning, unrestricted provider payloads, raw source text, or secret-like values.
- `AAPL`/`VOO` stock-vs-ETF: comparison response is available with `stock-etf-relationship-v1`, `direct_holding`, relationship badges, the `single-company-vs-ETF-basket` structure, same-pack citations/source documents, comparison export parity, asset-chat compare redirect parity, and no `holding_verified` regression.
- `VOO`/`SPY`: missing local comparison pack involving the `SPY` partial ETF remains non-generated with `eligible_not_cached`, no beginner bottom line, no generated key differences, no citations, no source documents, and unavailable comparison export content.
- `VOO`/`TQQQ` and `AAPL`/`TQQQ`: blocked product comparison cases stay `unsupported`, non-generated, and export-empty.

Asset export and source-list export parity:

- Renderable stock and issuer-backed ETF rows `AAPL`, `VOO`, and `QQQ` have asset export and source-list export parity for JSON and Markdown. Exports include the educational disclaimer, citation IDs, allowed source metadata, source-use policy, freshness/as-of metadata, uncertainty labels where present, and no buy/sell/hold, allocation, price-target, tax, brokerage, unrestricted provider payloads, hidden prompts, raw model reasoning, or secrets.
- `SPY` partial ETF export preserves explicit `partial` slice state and unavailable export state. provider fallback is not audit-quality evidence approval, and the parity check must not convert missing issuer evidence into generated export content.
- `TQQQ`, `ARKK`, `BND`, and `GLD` blocked export rows stay unsupported. blocked products receive no generated asset output, source documents, citations, facts, Weekly News Focus, AI Comprehensive Analysis, generated chat answers, or generated-output cache writes. `TQQQ`, `ARKK`, `BND`, and `GLD` blocked export coverage is representative regression coverage, not a broad complex-product approval path.

Optional operator-only local checks remain skipped by default. Browser/API parity can be reviewed only when `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1` and `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1` are set for already-running local services. Durable parity can be reviewed only when `LEARN_TICKER_LOCAL_DURABLE_SMOKE=1`, `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1`, `LOCAL_DURABLE_REPOSITORIES_ENABLED=true`, placeholder-only `DATABASE_URL`, and non-public `LOCAL_DURABLE_OBJECT_NAMESPACE` are set. Blocked optional diagnostics report env var names and safe reason codes only; they must not print env values, DSNs, credentials, temporary object links, raw provider payloads, raw source text, hidden prompts, raw model reasoning, transcripts, or secret-like tokens.

The parity check preserves v0.4 workflow markers: home remains `data-home-primary-workflow="single-supported-stock-or-etf-search"`, `data-search-comparison-route` keeps `A vs B` search routed to `/compare`, comparison remains a separate connected workflow, glossary remains contextual, source/glossary/chat mobile behavior stays bottom-sheet or full-screen oriented through `data-source-drawer-mobile-presentation="bottom-sheet"`, `data-glossary-mobile-presentation="bottom-sheet"`, and `data-asset-chat-mobile-presentation="bottom-sheet-or-full-screen"`, and stock-vs-ETF relationship badges stay present.

Weekly News Focus remains evidence-limited. "No major Weekly News Focus items found" is valid when evidence is thin, and AI Comprehensive Analysis remains suppressed unless at least two approved Weekly News Focus items exist. The parity check must not pad Weekly News Focus items or treat comparison/export parity as live-provider, live-AI, ETF-500, Top-500, source approval, manifest promotion, production, deployment, generated-output cache persistence, or public-launch readiness.

## Lightweight Fresh-Data Fetch Smoke

The personal-MVP fresh-data fetch path is explicit and opt-in. It prefers SEC official stock metadata and filings for stocks, uses local ETF manifest/scope signals for ETFs, and falls back to Yahoo Finance/yfinance-derived provider data for local-test fields when official issuer automation is incomplete. It returns normalized facts, source labels, freshness, and partial/unavailable gaps only; it does not return unrestricted raw payloads.

Task: T-144 / T-147.

The local fresh-data MVP slice smoke is deterministic and CI-safe. It uses injected fixtures, does not need secrets, live provider calls, browser startup, or local services, and reports `pass`, `partial`, `blocked`, and `unavailable` states with source labels/counts, citation/fact counts, freshness/as-of metadata, generated-output eligibility, and `raw_payload_exposed=false`. T-147 distinguishes issuer-backed ETF rows from still-partial ETF rows without broadening ETF-500, source approval, live issuer acquisition, or production deployment scope.

```bash
TMPDIR=/tmp python3 scripts/run_local_fresh_data_slice_smoke.py --json
```

Expected deterministic slice output:

- `AAPL`, `MSFT`, and `NVDA` report `pass` with SEC official source labels, provider-derived fallback labels, citations, freshness/as-of metadata, and available source drawer contracts.
- `VOO` and `QQQ` report `pass` as issuer-backed ETF rows when deterministic official issuer fixture evidence is present. They include official issuer sources, citations, normalized benchmark, expense-ratio, prospectus, holdings/exposure facts or explicit gaps, source-drawer-ready metadata, freshness/as-of metadata, and separately labeled provider-derived market/reference fallback when present.
- `SPY`, `VTI`, and `XLK` report `partial` with ETF manifest/scope evidence, provider-derived fallback labels, citations, freshness/as-of metadata, available source drawer contracts, and explicit partial/unavailable issuer-evidence gaps because no deterministic issuer fixture is registered for those rows.
- `TQQQ`, `ARKK`, `BND`, and `GLD` report `blocked`; they remain generated-output-ineligible and do not unlock generated pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, generated risk summaries, or generated-output cache entries.
- The smoke output must not contain provider secrets, raw payload values, raw source text, or unrestricted provider responses.

When live lightweight mode is enabled, exact search and the existing asset-page contracts can use fresh renderable data:

- `/api/search?q=MSFT` can open a source-labeled local-MVP page even when the deterministic cached pack is absent.
- `/api/assets/{ticker}/overview` returns the existing overview contract with beginner summary, three risks, sections, citations, source documents, Weekly News Focus empty state, and AI Comprehensive Analysis suppression.
- `/api/assets/{ticker}/details` returns stock or ETF detail fields from the same source-labeled fetch.
- `/api/assets/{ticker}/sources` returns the source drawer contract with source groups, citation bindings, related claims, and section references.

```bash
DATA_POLICY_MODE=lightweight LIGHTWEIGHT_LIVE_FETCH_ENABLED=true LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true SEC_EDGAR_USER_AGENT="learn-the-ticker-local/0.1 contact@example.com" TMPDIR=/tmp python3 scripts/run_lightweight_data_fetch_smoke.py --live --ticker AAPL --ticker MSFT --ticker NVDA --ticker VOO --ticker SPY --ticker VTI --ticker QQQ --ticker XLK --json
```

The API equivalent is:

```bash
curl -s http://127.0.0.1:8000/api/assets/AAPL/fresh-data
curl -s http://127.0.0.1:8000/api/assets/VOO/fresh-data
curl -s http://127.0.0.1:8000/api/search?q=MSFT
curl -s http://127.0.0.1:8000/api/assets/MSFT/overview
curl -s http://127.0.0.1:8000/api/assets/SPY/details
curl -s http://127.0.0.1:8000/api/assets/SPY/sources
```

Expected local behavior:

- `AAPL`, `MSFT`, `NVDA`, and other SEC-resolved common stocks should include SEC official source labels and may include Yahoo-labeled provider fallback for market-reference fields.
- `VOO` and `QQQ` should use deterministic issuer-backed enrichment before final provider-fallback shaping and may render as `supported` when official issuer facts and citations are present.
- `SPY`, `VTI`, `XLK`, and other renderable in-scope ETFs without deterministic issuer fixtures should include local ETF manifest/scope metadata or heuristic scope context plus Yahoo-labeled provider fallback, and must preserve explicit issuer-evidence gaps.
- Renderable stock and ETF pages should have exactly three top risks, source/citation metadata, source drawer groups, and partial/unavailable states for missing issuer or provider fields.
- Unsupported or out-of-scope products such as `TQQQ`, `ARKK`, `BND`, `GLD`, leveraged, inverse, active, bond, commodity, crypto, ETN, single-stock, option-income, buffer, or multi-asset ETF-like products remain blocked.
- `raw_payload_exposed` must stay `false`; diagnostics must not include provider keys, full raw payloads, raw source text, or secret values.

## Current Local MVP Gap Track

The deterministic rehearsal can pass today, but that is not the same as a fully functional local fresh-data MVP. T-131 through T-144 added ETF eligible-universe review, stock and ETF source-pack readiness packets, local MVP thresholds, batchable ingestion priority planning, and a deterministic local fresh-data MVP slice smoke. The next agent-loop work should follow this order before the project can honestly become manual-test-only:

1. Finish T-136 ETF-500 candidate manifest review contracts while keeping golden/pre-cache ETFs as regression assets only.
2. Add T-137 ETF-500 issuer source-pack batch planning for required issuer pages, fact sheets, prospectus or summary prospectus documents, holdings, exposures, methodology/risk/shareholder sources, and sponsor announcements where relevant.
3. Add T-138 Top-500 SEC source-pack batch planning for submissions, latest 10-K, latest 10-Q where available, XBRL company facts, parser readiness, checksums, and Golden Asset Source Handoff actions.
4. Add T-139 local manual fresh-data readiness gate so the rehearsal can say `agent_work_remaining` while deterministic prerequisites are missing and `manual_test_ready` only when the next step is operator local testing.

All steps remain deterministic by default and must not approve sources, promote manifests, start production services, expose secrets, or make live provider/news/market-data/LLM calls in normal CI.

## Local Live-AI Validation Smoke

Task: T-127.

The local live-AI validation smoke is operator-only and disabled by default. It validates one supported golden grounded-chat case and one AI Comprehensive Analysis case where two approved Weekly News Focus items are available. Approved reputable third-party items may count only when source governance permits them and the item is labeled as third-party reporting. It does not approve sources, does not relax Golden Asset Source Handoff, does not write generated-output cache records, and does not print raw user text, prompts, source text, model reasoning, transcripts, generated live responses, or secret values.

Prerequisites:

- a server-side live provider key is already present in the operator shell
- local opt-in is intentional for this shell only
- live generation is explicitly enabled for this one command
- source evidence remains fixture-safe or already handoff-approved

Command:

```bash
LTT_LIVE_AI_SMOKE_ENABLED=true \
LLM_PROVIDER=<server-side-live-provider> \
LLM_LIVE_GENERATION_ENABLED=true \
TMPDIR=/tmp python3 scripts/run_live_ai_validation_smoke.py --json
```

Expected results:

- without `LTT_LIVE_AI_SMOKE_ENABLED=true`, both smoke cases report `skipped`
- without live-generation readiness or a server-side key, both smoke cases report `blocked`
- with readiness and valid output, cases report `pass`
- failed schema, citation, source-use, freshness, safety, evidence-threshold, or cache-eligibility checks report `blocked`

Stop conditions:

- any blocked validation result
- fewer than two approved Weekly News Focus items for the AI Comprehensive Analysis case
- any diagnostic or log path that would expose raw user text, prompts, source text, generated live responses, model reasoning, transcripts, unrestricted provider payloads, or secret values
- any attempt to treat local live-AI review as source approval or a Golden Asset Source Handoff override

Suggested placeholder-only environment for local frontend/API rendering:

```bash
export LTT_LOCAL_REPOSITORY_MODE=in_memory
export LTT_LOCAL_SOURCE_MODE=mocked_official_sources
export API_BASE_URL=http://127.0.0.1:8000
export NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
export CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

For optional T-122 local-durable smoke, run with the same API/base wiring and these prerequisite flags:

```bash
export DATABASE_URL=<local durable repository DSN, placeholder-only>
export LOCAL_DURABLE_REPOSITORIES_ENABLED=true
export LOCAL_DURABLE_OBJECT_NAMESPACE=ticker-smoke
export LEARN_TICKER_LOCAL_DURABLE_SMOKE=1
export LEARN_TICKER_LOCAL_BROWSER_SMOKE=1
export LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000
export LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000
```

Do not add provider credentials, production storage paths, signed links, public bucket links, raw provider payloads, raw source text, hidden prompts, raw model reasoning, raw user text, or transcript text to environment examples, fixtures, logs, diagnostics, or committed files.

## Deterministic Smoke Path

1. Start from a clean worktree and install the normal local dependencies.
2. Create a manual pre-cache job for a golden asset such as `VOO` through the backend route:

```bash
curl -s -X POST http://127.0.0.1:8000/api/admin/pre-cache/VOO
```

3. Execute the local worker in deterministic mode with mocked official-source acquisition. The smoke test uses:
   - mocked issuer acquisition for the golden asset
   - parser diagnostics marked `parsed`
   - Golden Asset Source Handoff marked `approved`
   - private source snapshot metadata only
   - normalized knowledge-pack records from deterministic fixtures
   - Weekly News Focus evidence records from deterministic official-source candidates
   - generated-output cache records that already passed citation, source-use, freshness, and safety validation

4. Verify the job status:

```bash
curl -s http://127.0.0.1:8000/api/admin/pre-cache/jobs/pre-cache-launch-voo
```

Expected result: `job_state` is `succeeded`, generated output is available only for supported cached golden assets, and diagnostics remain compact and sanitized.

5. Verify backend route reads:

```bash
curl -s http://127.0.0.1:8000/api/assets/VOO/overview
curl -s http://127.0.0.1:8000/api/assets/VOO/weekly-news
curl -s http://127.0.0.1:8000/api/assets/VOO/sources
curl -s http://127.0.0.1:8000/api/assets/VOO/glossary?term=expense%20ratio
curl -s http://127.0.0.1:8000/api/assets/VOO/export?export_format=json
```

Expected result:

- overview, sources, glossary, and exports use validated persisted records before fixture fallback where that surface supports persisted reads
- citation chips and source drawer metadata expose approved source metadata and allowed excerpts only
- Weekly News Focus shows the evidence-backed item count and may show fewer than the configured maximum
- AI Comprehensive Analysis is suppressed below two approved Weekly News Focus items and available only when the threshold is met
- unsupported, out-of-scope, pending-ingestion, partial, stale, unknown, unavailable, pending-review, rejected-source, parser-invalid, wrong-asset, hidden/internal, unclear-rights, and insufficient-evidence states stay blocked or labeled according to section behavior

6. Verify local frontend/API plumbing.

T-119 established two valid local strategies:

- browser helpers prefer `NEXT_PUBLIC_API_BASE_URL` and call FastAPI directly, with FastAPI CORS allowing the local web origins
- the Next app also rewrites `/api/:path*` to the configured FastAPI backend, so relative chat/export links do not hit missing Next API routes during local development

Start the API with the placeholder CORS origins:

```bash
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000 \
TMPDIR=/tmp python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Start the web app with both local API-base variables configured:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 \
API_BASE_URL=http://127.0.0.1:8000 \
npm --workspace apps/web run dev -- --hostname 127.0.0.1 --port 3000
```

Then verify the prior frontend 404 blockers:

```bash
curl -s -X POST http://127.0.0.1:3000/api/assets/VOO/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"What does this fund hold?"}'
curl -s http://127.0.0.1:3000/api/assets/VOO/export?export_format=markdown
curl -s -X POST http://127.0.0.1:3000/api/compare \
  -H 'Content-Type: application/json' \
  -d '{"left_ticker":"VOO","right_ticker":"QQQ"}'
curl -s -X POST http://127.0.0.1:3000/api/compare \
  -H 'Content-Type: application/json' \
  -d '{"left_ticker":"AAPL","right_ticker":"VOO"}'
curl -s 'http://127.0.0.1:3000/api/compare/export?left_ticker=AAPL&right_ticker=VOO&export_format=json'
curl -s -X POST http://127.0.0.1:3000/api/assets/VOO/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"AAPL vs VOO"}'
curl -s -D - -o /dev/null http://127.0.0.1:8000/api/search?q=VOO \
  -H 'Origin: http://127.0.0.1:3000'
curl -s -X OPTIONS http://127.0.0.1:8000/api/compare \
  -H 'Origin: http://127.0.0.1:3000' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type' \
  -D - -o /dev/null
```

Expected result: chat, export, and compare return backend payloads instead of Next 404s. `AAPL` vs `VOO` returns `comparison_type = stock_vs_etf`, `stock_etf_relationship.schema_version = stock-etf-relationship-v1`, `relationship_state = direct_holding`, `evidence_availability.availability_state = available`, citations, source documents, source-reference metadata, relationship badges, and the `single-company-vs-etf-basket` structure. The `AAPL vs VOO` chat request returns `safety_classification = compare_route_redirect`, `comparison_availability_state = available`, no factual citations, and no multi-asset factual answer in the chat body. Origin and preflight requests include an `Access-Control-Allow-Origin` header for the configured local origin.

7. Optional local browser/API smoke (T-142): run the stock-vs-ETF localhost smoke with the same web/API bases.

```bash
LEARN_TICKER_LOCAL_BROWSER_SMOKE=1 \
LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000 \
LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000 \
npm run test:browser-smoke
```

This opt-in smoke checks:

- `/compare?left=AAPL&right=VOO` renders `stock_vs_etf`, `stock-etf-relationship-v1`, `direct_holding`, relationship badges, source/citation metadata, and `single-company-vs-etf-basket`.
- `POST /api/compare` through the Next `/api/:path*` proxy returns backend JSON for `AAPL` and `VOO`, not a Next 404, HTML fallback, or frontend-only fixture response.
- direct FastAPI CORS/preflight behavior allows the local web origin configured by `LEARN_TICKER_LOCAL_WEB_BASE`.
- `/api/compare/export` for `AAPL` and `VOO` is available, source-backed, citation-bearing, and preserves the educational disclaimer and no-advice framing.
- `POST /api/assets/VOO/chat` with `AAPL vs VOO` redirects to `/compare?left=AAPL&right=VOO` with `comparison_availability_state = available`, no factual citations, and no multi-asset factual answer in chat.
- the home page remains single-asset search first, while `A vs B` search handling remains a separate comparison-route workflow.
- existing `VOO` vs `QQQ` ETF-vs-ETF comparison behavior remains available and does not render stock-vs-ETF basket markers.

Stock-vs-ETF local functional readiness (T-143): the deterministic rehearsal command reports `stock_vs_etf_comparison_readiness` for the local `AAPL` vs `VOO` pack. Passing this check means the backend comparison pack, API-aligned frontend markers, comparison export, asset-chat compare redirect, optional localhost smoke instructions, and blocked unsupported/no-local-pack comparison states all agree for the fixture-backed `AAPL`/`VOO` path. It does not mean broad stock-vs-ETF coverage, live-provider readiness, deployment readiness, production launch readiness, source approval, manifest promotion, generated-output cache writes, or any generated-output unlock for unsupported, out-of-scope, eligible-not-cached, unknown, or missing-pack pairs.

8. Optional local fresh-data MVP slice browser/API smoke (T-145): run this only when already-running API and web services are started with the lightweight local MVP settings. This smoke is skip-by-default and must not start browser services, local ports, live provider calls, Docker, or LLM calls in normal CI. It checks the Next `/api/:path*` proxy, direct FastAPI JSON responses, and CORS from the configured web origin for the T-144 slice.

```bash
LEARN_TICKER_LOCAL_BROWSER_SMOKE=1 LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1 LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000 LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000 DATA_POLICY_MODE=lightweight LIGHTWEIGHT_LIVE_FETCH_ENABLED=true LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true SEC_EDGAR_USER_AGENT="learn-the-ticker-local/0.1 contact@example.com" TMPDIR=/tmp npm run test:browser-smoke
```

Required local prerequisites:

- `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1`
- `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1`
- `LEARN_TICKER_LOCAL_WEB_BASE` pointing to the already-running Next service
- `LEARN_TICKER_LOCAL_API_BASE` pointing to the already-running FastAPI service
- `DATA_POLICY_MODE=lightweight`
- `LIGHTWEIGHT_LIVE_FETCH_ENABLED=true`
- `LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true`
- placeholder `SEC_EDGAR_USER_AGENT`

When one of these prerequisites is missing, the smoke reports sanitized blockers using env var names only. It must not print secret values, unrestricted provider payloads, raw source text, or raw payload values.

Slice expectations:

- `AAPL`, `MSFT`, and `NVDA` are probed through `/api/assets/{ticker}/fresh-data` via both the frontend proxy and direct FastAPI. They should return JSON rather than a Next HTML fallback, stock identity, renderable supported state, generated-output eligibility, official SEC/source labeling where exposed, provider-derived fallback labeling where present, citations or explicit evidence states, freshness/as-of metadata, and source-drawer/source-count metadata.
- `VOO` and `QQQ` are probed through `/api/assets/{ticker}/fresh-data` via both the frontend proxy and direct FastAPI. They should return JSON rather than a Next HTML fallback, ETF identity, renderable supported state when official issuer fixture evidence is present, generated-output eligibility, official issuer source labels, issuer-backed normalized facts, provider-derived fallback labeling where present, citations, freshness/as-of metadata, and source-drawer/source-count metadata.
- `SPY`, `VTI`, and `XLK` are probed through `/api/assets/{ticker}/fresh-data` via both the frontend proxy and direct FastAPI. They should return JSON rather than a Next HTML fallback, ETF identity, renderable partial state, generated-output eligibility, manifest/scope or partial source labels, provider-derived fallback labeling where present, citations or explicit partial/unavailable evidence states, freshness/as-of metadata, and visible partial/unavailable labels for missing issuer evidence.
- Representative stock and ETF rows also check `/api/search`, `/api/assets/{ticker}/overview`, `/api/assets/{ticker}/details`, and `/api/assets/{ticker}/sources` through the running-service contract so overview, details, citation, freshness, and source-drawer surfaces remain API-backed.
- The blocked regression tickers `TQQQ`, `ARKK`, `BND`, and `GLD` remain generated-output-ineligible. They must not receive generated pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, generated risk summaries, source documents, citations, facts, provider fetches from the slice smoke, or generated-output cache writes.
- The existing optional browser smoke remains intact for `VOO`/`QQQ` ETF-vs-ETF and `AAPL`/`VOO` stock-vs-ETF, including comparison-route redirects, relationship badges, the `single-company-vs-ETF-basket` structure, export/chat proxy checks, and no `holding_verified` regression.

9. Optional durable local fresh-data MVP slice browser/API smoke (T-146): run this only when the already-running API and web services use lightweight local MVP settings plus local durable repository settings. This is skip-by-default and gated by all three local smoke flags: `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1`, `LEARN_TICKER_LOCAL_DURABLE_SMOKE=1`, and `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1`.

```bash
LEARN_TICKER_LOCAL_BROWSER_SMOKE=1 LEARN_TICKER_LOCAL_DURABLE_SMOKE=1 LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1 LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000 LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000 DATA_POLICY_MODE=lightweight LIGHTWEIGHT_LIVE_FETCH_ENABLED=true LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true LOCAL_DURABLE_REPOSITORIES_ENABLED=true LOCAL_DURABLE_OBJECT_NAMESPACE=ticker-smoke DATABASE_URL="<local durable repository DSN, placeholder-only>" SEC_EDGAR_USER_AGENT="learn-the-ticker-local/0.1 contact@example.com" TMPDIR=/tmp npm run test:browser-smoke
```

Required durable slice prerequisites:

- already-running FastAPI and Next services
- `LEARN_TICKER_LOCAL_WEB_BASE`
- `LEARN_TICKER_LOCAL_API_BASE`
- `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1`
- `LEARN_TICKER_LOCAL_DURABLE_SMOKE=1`
- `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1`
- `DATA_POLICY_MODE=lightweight`
- `LIGHTWEIGHT_LIVE_FETCH_ENABLED=true`
- `LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true`
- placeholder `SEC_EDGAR_USER_AGENT`
- `LOCAL_DURABLE_REPOSITORIES_ENABLED=true`
- placeholder-only local `DATABASE_URL`
- non-public placeholder `LOCAL_DURABLE_OBJECT_NAMESPACE`

The durable slice smoke reports missing prerequisites with env var names/status only. It rejects object namespaces that look public, URL-like, signed-link-like, credential-bearing, token-bearing, password-bearing, or secret-bearing. It must not print actual DSNs, object namespaces, provider credentials, unrestricted provider payloads, raw source text, raw payload values, generated live responses, or hidden diagnostics.

Durable slice expectations:

- `AAPL`, `MSFT`, and `NVDA` still return stock identity, supported render state, generated-output eligibility, official SEC/source labels where exposed, provider-derived fallback labels where present, citations or explicit evidence states, freshness/as-of metadata, and source-drawer/source-count metadata through both the Next `/api/:path*` proxy and direct FastAPI `/api/assets/{ticker}/fresh-data`.
- `VOO` and `QQQ` still return ETF identity, supported render state when official issuer fixture evidence is present, generated-output eligibility, official issuer labels, issuer-backed normalized facts, provider-derived fallback labels where present, citations, freshness/as-of metadata, and source-drawer/source-count metadata through both paths.
- `SPY`, `VTI`, and `XLK` still return ETF identity, partial render state, generated-output eligibility, manifest/scope or partial source labels, provider-derived fallback labels where present, citations or explicit partial/unavailable evidence states, freshness/as-of metadata, and visible partial/unavailable labels for missing issuer evidence through both paths.
- Representative durable rows `AAPL` and `VOO` check `/api/search`, `/api/assets/{ticker}/overview`, `/api/assets/{ticker}/details`, `/api/assets/{ticker}/sources`, `/api/assets/{ticker}/export?export_format=json`, and `/api/assets/{ticker}/sources/export?export_format=json` so overview, details, export, citation, freshness, and source-drawer surfaces remain API-backed under local durable configuration.
- Repeated representative reads compare only smoke-level stable fields: ticker, asset type, fetch/render state, generated-output eligibility, source/citation presence, blocked state, and no raw/secret exposure. They do not require exact quote, timestamp, checksum, freshness timestamp, or payload equality.
- Blocked regression tickers `TQQQ`, `ARKK`, `BND`, and `GLD` remain generated-output-ineligible and receive no generated pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, available exports, generated risk summaries, source documents, citations, facts, provider fetches from blocked probes, or generated-output cache writes.
- Default `node tests/frontend/smoke.mjs`, `npm test`, `npm run build`, repo-contract tests, local rehearsal, and the quality gate remain deterministic and skip localhost, durable, and durable-slice checks unless the local-smoke flags above are set.

10. Optional local-durable smoke (T-122): run the browser smoke with durable prereqs set.

```bash
LEARN_TICKER_LOCAL_BROWSER_SMOKE=1 \
LEARN_TICKER_LOCAL_DURABLE_SMOKE=1 \
LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000 \
LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000 \
npm run test:browser-smoke
```

When durable prereqs are present, this optional run validates:

- VOO asset render through API-backed pages
- `/api/assets/VOO/chat`
- `/api/assets/VOO/export`
- `/api/assets/VOO/sources/export`
- `/assets/VOO/sources`
- `/compare?left=VOO&right=QQQ`
- `/compare?left=AAPL&right=VOO`
- `/api/compare/export`
- CORS behavior from `/api/search?q=VOO` using the local web origin
- out-of-scope/unknown search blocking behavior under API proxy

If any durable prerequisites are missing, the smoke should print blockers and report that durable smoke is skipped.

11. Verify frontend rendering with the API base configured:

```bash
npm run dev
```

Open `http://127.0.0.1:3000/assets/VOO`. The page should preserve Frontend Design and Workflow v0.4:

- home remains single stock/ETF search first
- comparison remains a separate connected `/compare` workflow
- glossary appears as contextual help
- source drawer, glossary, and chat remain mobile bottom-sheet or full-screen surfaces where appropriate
- stock-vs-ETF comparison keeps relationship badges and the single-company-vs-ETF-basket structure
- Weekly News Focus renders only the evidence-backed set

## Cleanup

For `in_memory`, stop the API and frontend processes. Records disappear with the process.

For optional `local_durable`, remove only local throwaway data created for the smoke run. Do not touch production databases, buckets, deployment resources, current Top-500 manifests, candidate manifests, or diff reports.

## Troubleshooting

- If an overview falls back to fixtures, check that persisted knowledge-pack, generated-output cache, and source snapshot readers are configured for the governed path.
- If generated-output cache reuse is rejected, check freshness hashes, same-asset citation bindings, source-use policy, parser status, private source snapshot artifacts, and handoff metadata.
- If Weekly News Focus has fewer items than expected, treat that as valid when evidence is thin. Do not pad the section.
- If source drawer or export output is empty, verify that sources are allowlisted, parser-valid, same-asset, and excerpt-allowed.
- If frontend rendering uses local fallback, confirm `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` points to the local backend.
- If chat or export links return frontend 404s, confirm the web dev server was started after setting `NEXT_PUBLIC_API_BASE_URL` or that the Next `/api/:path*` rewrite can reach the local FastAPI backend.
- If browser direct API calls fail, confirm `CORS_ALLOWED_ORIGINS` includes the exact local web origin, including hostname and port.

The deterministic regression for this runbook is `test_t118_local_fresh_data_ingest_to_render_smoke_path_is_deterministic` in `tests/integration/test_backend_api.py`. T-119 added static coverage for the frontend API helper, Next rewrite, and CORS settings. T-121/T-122 added optional localhost browser and durable smoke paths. T-125 keeps this runbook aligned with the v0.6 handoff docs. T-127 covers operator-only live-AI validation smoke, T-128 proves deterministic governed golden source snapshots, knowledge-pack records, and generated-output cache records can drive API and frontend-rendering markers without approving new sources or adding live calls, T-144 adds the deterministic local fresh-data MVP slice smoke, and T-145 adds the opt-in local fresh-data MVP slice browser/API smoke under the existing localhost browser smoke gate.
