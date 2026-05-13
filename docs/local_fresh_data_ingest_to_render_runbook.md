# Local Fresh-Data Ingest-To-Render Runbook

Task: T-118, updated by T-119 through T-158 local API, manifest, durable-smoke, v0.6 handoff alignment, local MVP rehearsal, readiness thresholds, ingestion priority planning, AAPL-vs-VOO stock-vs-ETF localhost smoke coverage, stock-vs-ETF comparison readiness gating, local fresh-data MVP slice smoke coverage, optional slice browser/API localhost coverage, optional durable slice smoke coverage, lightweight local-slice manual-readiness gating, local slice comparison/export parity coverage, the lightweight live browser/API MVP slice smoke runner contract, lightweight API fallback diagnostics, the lightweight live durable MVP slice smoke runner contract, lightweight issuer-backed SPY/VTI/XLK enrichment, the optional Weekly News Focus live-source smoke, lightweight fresh-data comparison coverage for stock-vs-stock plus non-generated ETF pairs, the local deployment/environment smoke, the lightweight MVP readiness gate, and the Weekly News official document handoff proof

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
- local deployment/environment smoke through `local_deployment_env_smoke`, including placeholder env files, API-base/CORS wiring, Docker Compose config readiness when Docker is available, and no-secret boundaries.
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
- Weekly News Focus live-source smoke: when `LTT_WEEKLY_NEWS_LIVE_SOURCE_SMOKE_ENABLED=true` is set, runs the deterministic fixture-backed Weekly News Focus source smoke. It is skipped by default. If `LTT_WEEKLY_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED=true` is also set, it exercises the strict official document retrieval/parsing/snapshot path for `AAPL`, `VOO`, and `QQQ` with injected official-document fixtures, not CI network calls.
- live-AI review: delegates to the operator-only live-AI validation smoke and reports sanitized pass or blocker states.

Stop when any required deterministic check is `blocked`, or when an opted-in optional check is `blocked`. The rehearsal does not start production services, approve sources, promote manifests, write production storage, require live calls by default, or make fixture-sized/local-only data launch-approved.

## Local Deployment/Environment Smoke

Task: T-157.

Run the deployment/environment smoke before production hardening or first-deployment review:

```bash
TMPDIR=/tmp python3 scripts/run_local_deployment_env_smoke.py --json
```

The smoke uses schema `local-deployment-env-smoke-v1`. It is deterministic and CI-safe: default execution does not require live network, local services, a browser, durable repositories, a Docker daemon, deployment credentials, provider keys, LLM keys, or secrets. It reports `normal_ci_requires_live_calls=false`, `production_services_started=false`, `deployments_created=false`, `live_provider_calls_attempted=false`, `database_connections_opened=false`, `secret_values_reported=false`, `launch_or_public_deployment_approved=false`, and `production_ready=false`.

What it checks:

- placeholder env files `.env.example`, `apps/web/.env.example`, `deploy/env/api.example.env`, `deploy/env/web.example.env`, and `deploy/env/worker.example.env` exist, are non-empty, and expose env var names only.
- browser env surfaces contain only browser-safe names such as `NEXT_PUBLIC_API_BASE_URL`; server-only names such as `DATABASE_URL`, `OPENROUTER_API_KEY`, `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FINNHUB_API_KEY`, `TIINGO_API_KEY`, and `EODHD_API_KEY` stay out of browser env files.
- API and worker placeholders include safe readiness names for `PORT`, `CORS_ALLOWED_ORIGINS`, `DATABASE_URL` presence/redaction, `DATA_POLICY_MODE=lightweight`, `LIGHTWEIGHT_LIVE_FETCH_ENABLED` default-off behavior, `LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED`, `SEC_EDGAR_USER_AGENT` placeholder presence, `LLM_PROVIDER=mock`, `LLM_LIVE_GENERATION_ENABLED=false`, OpenRouter placeholders, Vercel `NEXT_PUBLIC_API_BASE_URL`, Cloud Run API env placeholders, and Cloud Run Job worker placeholders.
- `apps/web` remains the Vercel project root, root npm scripts delegate to `apps/web`, `apps/web/next.config.mjs` preserves the documented API-base or Next `/api/:path*` rewrite behavior, the API Dockerfile respects Cloud Run's `PORT` contract with a local fallback, the web Dockerfile builds the Next workspace, and `docker-compose.yml` remains local-only with API/web/worker/Postgres/Redis/MinIO scaffolding and mock LLM defaults.

Docker Compose validation is optional and safe. When Docker Compose is available, the smoke runs `docker compose config` without starting services, pulling images, creating volumes, or opening databases. When Docker is unavailable, it reports `docker_compose_config_status=skipped_unavailable` or another safe skipped reason and still allows deterministic CI to pass. To inspect the same validation manually, run:

```bash
docker compose config
```

Safe states:

- `pass`: committed placeholder files and local scaffolding are present, browser/server env separation holds, default settings remain no-live/no-service/no-secret, and Docker Compose config passed or was safely skipped.
- `skipped`: only the Docker Compose config sub-check should be skipped when Docker or the caller's Docker config check is unavailable.
- `blocked`: a required placeholder env file is missing, a browser env file contains a server-only key, required local deployment scaffolding markers are missing, safe defaults regress, or Docker Compose config is available but invalid.

The diagnostics report env var names, configured/missing booleans, redacted-placeholder statuses, reason codes, and readiness states only. They must not include actual env values, DSNs, keys, tokens, service-account JSON, temporary credential-bearing links, raw provider payloads, raw source text, raw model output, raw model reasoning, hidden prompts, transcripts, or unrestricted excerpts.

This smoke is local deployment-scaffold readiness only. It is not source approval, Golden Asset Source Handoff approval, manifest promotion, generated-output cache promotion, ETF-500 completion, Top-500 completion, live-provider readiness, production deployment readiness, public-launch approval, or investment advice. It must not start Vercel deploys, Cloud Run deploys, Cloud Run Jobs, Cloud Scheduler, Docker services, database migrations, production object-storage writes, provider calls, news calls, market-data calls, or LLM calls.

`TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` includes this as the required deterministic check `local_deployment_env_smoke` and surfaces the same no-launch/no-production boundaries in prerequisite summaries.

## Lightweight MVP Readiness Gate

Task: T-158.

Use the lightweight MVP readiness gate to summarize whether the deterministic personal/local MVP slice is ready for explicit operator manual review:

```bash
TMPDIR=/tmp python3 scripts/run_lightweight_mvp_readiness_gate.py --json
```

The command emits schema `lightweight-mvp-readiness-gate-v1`. Default execution is deterministic and fixture-backed. It does not require live network, local services, a browser, durable repositories, a Docker daemon, deployment credentials, source/provider credentials, LLM credentials, or secrets. It reports `normal_ci_requires_live_calls=false`, `production_services_started=false`, `deployments_created=false`, `live_provider_calls_attempted=false`, `database_connections_opened=false`, `secret_values_reported=false`, `production_ready=false`, and `public_launch_ready=false`.

The gate consumes the existing `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` result, including the embedded `local_deployment_env_smoke` summary, instead of duplicating product checks. It returns `local_personal_mvp_ready_for_manual_review=true` only when deterministic local/manual-review prerequisites pass:

- `local_fresh_data_mvp_slice_smoke`
- `local_fresh_data_mvp_slice_comparison_export_parity`
- `stock_vs_etf_comparison_readiness`
- `local_deployment_env_smoke`
- `frontend_v04_smoke_markers`
- `source_handoff_approval_gate`
- `governed_golden_api_rendering`
- local threshold summaries for unsupported blocked tickers, source-use/export boundaries, no-live boundaries, and no-secret diagnostics

The output also includes status and reason-code summaries for launch-manifest review packets, stock SEC source-pack readiness, ETF issuer source-pack readiness, local ingestion priority planning, Weekly News Focus evidence-threshold behavior, live-AI optional readiness, unsupported blocked tickers `TQQQ`, `ARKK`, `BND`, and `GLD`, and the no-secret diagnostics surface.

`pass`, `blocked`, and `skipped` meanings:

- `pass`: deterministic local/manual-review checks pass, optional operator-only modes are skipped or pass, unsupported products remain blocked from generated output, and the local personal MVP can move to explicit operator manual browser/API review.
- `blocked`: a deterministic required check failed, an explicitly opted-in optional check blocked, unsupported or out-of-scope products unlocked generated output, no-live/no-secret boundaries regressed, source-use/export boundaries regressed, source-backed claims lost citations or uncertainty labels, or v0.4 frontend workflow markers are missing.
- `skipped`: an operator-only optional check was not enabled. Skipped optional checks are visible diagnostics, not hidden passes.

Strict/public-launch gates are intentionally represented as `audit_only` diagnostics in `strict_public_launch_audit_only_gates`. They do not block local personal-MVP manual review and they are not promoted or approved by this command. The audit-only list includes ETF-500 full supported-manifest validation, Top-500 current-manifest refresh approval, full Golden Asset Source Handoff approval, stock SEC source-pack approval, ETF issuer source-pack approval, launch-sized source artifacts, launch-manifest promotion, generated-output cache promotion, live-provider execution, live-AI review, production deployment, recurring jobs, and broad paid-provider/news integrations.

The readiness gate always keeps these launch/public flags false unless a future strict/public-launch task changes the contract: `strict_audit_ready=false`, `launch_or_public_deployment_approved=false`, `sources_approved_by_readiness_gate=false`, `manifests_promoted=false`, `generated_output_cache_promoted=false`, `production_ready=false`, and `public_launch_ready=false`.

Safe manual follow-up after a passing gate:

- Start local web/API services manually only when the operator intends to review the slice.
- Verify home single-asset search, clear `A vs B` routing to `/compare`, asset pages, citation chips, source drawer desktop/mobile behavior, contextual glossary desktop/mobile behavior, asset chat bottom-sheet or full-screen behavior, exports, and comparison flows.
- Verify stock-vs-ETF comparison still shows relationship badges and the `single-company-vs-ETF-basket` structure.
- Verify Weekly News Focus shows only the evidence-backed set, smaller or empty states remain valid, AI Comprehensive Analysis stays suppressed unless at least two approved Weekly News Focus items exist, and canonical facts remain separate from timely context.

This command is a local personal-MVP readiness summary only. It is not source approval, Golden Asset Source Handoff approval, manifest promotion, generated-output cache promotion, ETF-500 completion, Top-500 completion, live-provider readiness, live-AI readiness, production deployment readiness, public-launch approval, or investment advice. Its diagnostics report booleans, status counts, reason codes, safe markers, and readiness states only. They must not include actual env values, DSNs, keys, tokens, service-account JSON, signed credential-bearing links, raw provider payloads, raw source text, raw model output, raw model reasoning, hidden prompts, transcripts, full restricted article text, or unrestricted excerpts.

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
- status counts are `pass=8`, `partial=0`, `blocked=4`, and `unavailable=0`.
- `AAPL`, `MSFT`, and `NVDA` pass as stock rows.
- `VOO`, `QQQ`, `SPY`, `VTI`, and `XLK` pass as issuer-backed ETF rows.
- no ETF rows remain partial in the deterministic slice; unsupported fields such as current premium/discount or bid-ask spread remain explicit unavailable gaps.
- `TQQQ`, `ARKK`, `BND`, and `GLD` remain blocked and receive no source documents, citations, facts, provider fetches, generated pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, generated risk summaries, or generated-output cache writes.
- the existing `VOO`/`QQQ` ETF-vs-ETF and `AAPL`/`VOO` stock-vs-ETF smoke markers remain intact, and `AAPL`/`MSFT` stock-vs-stock coverage stays available with stock-appropriate dimensions and no ETF-only benchmark, expense-ratio, holdings-count, fund-construction, or ETF-role copy. These checks keep the separate `/compare` workflow, `A vs B` redirect behavior, relationship badges, the `single-company-vs-ETF-basket` structure, export/chat proxy checks, and no `holding_verified` regression.

Skipped optional checks are reported explicitly as operator-only prerequisites; they are not hidden as pass. The optional operator-only local checks include browser/API services, local durable repositories, official-source retrieval, and live-AI review. When an optional flag is set and the check is blocked, the slice gate reports `optional_local_check_blocked` with env var names and safe diagnostics only, never credential values.

The slice gate is not launch readiness. It does not approve ETF-500, Top-500, production, deployment, source-pack, parser, Golden Asset Source Handoff, checksum, live-provider, or live-AI readiness. It does not approve sources, promote manifests, start services, write production storage, write generated-output cache entries, or unlock blocked products. Source-use policy still applies: fetching is retrieval, not evidence approval; source-labeled official/provider-derived display is allowed for the personal lightweight MVP only while raw payloads stay hidden, rights-safe output limits are preserved, provenance/freshness are visible, and missing evidence renders as `partial`, `unknown`, `stale`, `unavailable`, or `insufficient_evidence`.

## Weekly News Focus Live-Source Smoke

Task: T-154.

The Weekly News Focus live-source smoke is an operator-only review contract for local MVP source acquisition behavior. It is deterministic and CI-safe by default, uses fixture-backed source candidates when opted in, and does not require live network calls, local services, durable repositories, browser startup, provider keys, news providers, market-data providers, or live LLMs.

Default command:

```bash
TMPDIR=/tmp python3 scripts/run_weekly_news_live_source_smoke.py --json
```

Default output uses schema `weekly-news-live-source-smoke-v1`, reports `status=skipped`, `normal_ci_requires_live_calls=false`, and names only the opt-in boundary `LTT_WEEKLY_NEWS_LIVE_SOURCE_SMOKE_ENABLED`. It never prints env values.

Deterministic opted-in command:

```bash
LTT_WEEKLY_NEWS_LIVE_SOURCE_SMOKE_ENABLED=true TMPDIR=/tmp python3 scripts/run_weekly_news_live_source_smoke.py --json
```

Expected deterministic cases:

- `source_backed_official_first`: `QQQ` candidates prove the U.S. Eastern market-week window, official-source priority, same-asset citation/source binding, source event dates, published dates, retrieved timestamps, period buckets, freshness labels, source rank tiers, source quality, official-vs-third-party labels, source-use policy, allowlist/review status, and citation IDs. Selected source rank tiers include `official_filing`, `etf_issuer_announcement`, and `allowlisted_news`; the allowlisted news item is labeled `third_party_reporting`.
- `limited_verified_set`: `AAPL` has one approved official item, so Weekly News Focus shows fewer than the configured maximum and AI Comprehensive Analysis remains suppressed.
- `empty_evidence`: `VOO` has no selected items and reports the clear empty state. "No major Weekly News Focus items found" remains valid when evidence is thin.
- `blocked_regression_tickers`: `TQQQ`, `ARKK`, `BND`, and `GLD` receive no Weekly News Focus, AI Comprehensive Analysis, citations, sources, facts, exports, generated pages, generated chat answers, generated comparisons, generated risk summaries, or generated-output cache writes.

Suppression diagnostics are compact reason-code counts only. The deterministic smoke covers duplicate, promotional, irrelevant, wrong-asset, outside-window, metadata-only, link-only, rejected, unrecognized, pending-review, parser-invalid, rights-disallowed, hidden/internal, stale-unlabeled, and license-disallowed candidates without printing raw article text, raw source text, unrestricted excerpts, provider payloads, signed links, hidden prompts, transcripts, model reasoning, generated live responses, or secret values.

AI threshold behavior is metadata-only in this smoke. `analysis_allowed=true` appears only when the selected approved item count is at least two. AI Comprehensive Analysis remains suppressed unless at least two approved Weekly News Focus items exist. The smoke must not call live LLMs or write generated-output cache records.

Strict official document retrieval proof:

```bash
LTT_WEEKLY_NEWS_LIVE_SOURCE_SMOKE_ENABLED=true LTT_WEEKLY_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED=true TMPDIR=/tmp python3 scripts/run_weekly_news_live_source_smoke.py --json
```

This reports `source_retrieval_mode=operator_real_source_document_acquisition` and uses injected official SEC/issuer HTML/JSON fixtures to exercise the real repository pipeline without CI network calls. The path discovers official requests for the golden scope, fetches document bytes through the SSRF/allowlist/content-type/size guarded fetcher, parses SEC JSON and issuer/IR HTML into same-asset `WeeklyNewsEventCandidateRow` records, derives evidence checksums from document bytes plus parsed event payloads, validates Golden Asset Source Handoff for `generated_claim_support`, writes private source snapshot metadata to an injected repository, and persists Weekly News evidence to an injected repository before selection can support Weekly News claims.

The strict proof is still local review only. It does not approve sources by itself, promote manifests, write production storage, create generated-output cache entries, broaden asset coverage beyond `AAPL`, `VOO`, and `QQQ`, or require/default to live external network calls.

`TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` includes `optional_weekly_news_live_source_smoke` as an optional operator-only check. It is skipped by default, appears in optional mode summaries and manual-readiness prerequisites, passes when explicitly opted into the deterministic fixture-backed smoke, and blocks rehearsal only when explicitly opted in and the smoke returns `blocked`.

This smoke is local source-acquisition review only: local smoke readiness is not source approval, Golden Asset Source Handoff approval, generated-output cache promotion, ETF-500 completion, Top-500 completion, live-AI readiness, deployment readiness, production readiness, investment suitability, or permission to store raw source text.

## Local Slice Comparison And Export Parity

Task: T-149.

`TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` returns the required check `local_fresh_data_mvp_slice_comparison_export_parity` with schema `local-fresh-data-mvp-slice-comparison-export-parity-v1`. The check is deterministic and fixture-backed. It is a local fresh-data MVP slice parity signal only, not readiness versus broad launch readiness.

`TMPDIR=/tmp python3 scripts/run_local_fresh_data_slice_smoke.py --json` also exposes `comparison_export_parity_summary` with schema `local-fresh-data-mvp-slice-comparison-export-parity-inputs-v1` so the rehearsal can verify the same supported, partial, and blocked ticker contracts without live services.

Representative parity coverage:

- `VOO`/`QQQ` ETF-vs-ETF: comparison response is available, source-backed, same-comparison-pack citation bound, exportable as JSON and Markdown, includes the educational disclaimer, preserves source-use policy and source freshness metadata, and contains no advice output, hidden prompts, raw model reasoning, unrestricted provider payloads, raw source text, or secret-like values.
- `AAPL`/`VOO` stock-vs-ETF: comparison response is available with `stock-etf-relationship-v1`, `direct_holding`, relationship badges, the `single-company-vs-ETF-basket` structure, same-pack citations/source documents, comparison export parity, asset-chat compare redirect parity, and no `holding_verified` regression.
- `AAPL`/`MSFT` stock-vs-stock: comparison response is available, source-backed, same-comparison-pack citation bound, exportable as JSON and Markdown, returns `comparison_type=stock_vs_stock`, includes a beginner bottom line, uses stock-appropriate dimensions (`Business model`, `Revenue trend`, `Business quality evidence`, `Risk context`, and `Valuation evidence availability`), labels the valuation evidence limit as partial/unavailable, and avoids ETF-only dimensions or copy such as benchmark, expense ratio, holdings count, fund construction, or ETF role.
- `VOO`/`SPY`: missing static comparison pack involving `SPY` remains non-generated with `eligible_not_cached`, no beginner bottom line, no generated key differences, no citations, no source documents, and unavailable comparison export content, even though the local fresh-data slice now has issuer-backed SPY evidence.
- `SPY`/`VTI` non-generated: an additional issuer-backed ETF pair without a static comparison pack remains `eligible_not_cached`, export-empty, and non-generated. Because there are no partial ETF rows in the current deterministic slice, the smoke reports `no_partial_etf_rows_in_current_slice` instead of inventing a partial ETF comparison row.
- `VOO`/`TQQQ` and `AAPL`/`TQQQ`: blocked product comparison cases stay `unsupported`, non-generated, and export-empty.

Asset export and source-list export parity:

- Renderable stock and issuer-backed ETF rows `AAPL`, `VOO`, and `QQQ` have asset export and source-list export parity for JSON and Markdown. Exports include the educational disclaimer, citation IDs, allowed source metadata, source-use policy, freshness/as-of metadata, uncertainty labels where present, and no buy/sell/hold, allocation, price-target, tax, brokerage, unrestricted provider payloads, hidden prompts, raw model reasoning, or secrets.
- `SPY` asset export remains unavailable in the static export parity path because no cached generated-output pack exists; local deterministic issuer enrichment is not audit-quality ETF-500 source-pack approval, provider fallback is not audit-quality evidence approval, and neither must be treated as generated-output cache promotion.
- `TQQQ`, `ARKK`, `BND`, and `GLD` blocked export rows stay unsupported. blocked products receive no generated asset output, source documents, citations, facts, Weekly News Focus, AI Comprehensive Analysis, generated chat answers, or generated-output cache writes. `TQQQ`, `ARKK`, `BND`, and `GLD` blocked export coverage is representative regression coverage, not a broad complex-product approval path.

Optional operator-only local checks remain skipped by default. Browser/API parity can be reviewed only when `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1` and `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1` are set for already-running local services. Durable parity can be reviewed only when `LEARN_TICKER_LOCAL_DURABLE_SMOKE=1`, `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1`, `LOCAL_DURABLE_REPOSITORIES_ENABLED=true`, placeholder-only `DATABASE_URL`, and non-public `LOCAL_DURABLE_OBJECT_NAMESPACE` are set. Blocked optional diagnostics report env var names and safe reason codes only; they must not print env values, DSNs, credentials, temporary object links, raw provider payloads, raw source text, hidden prompts, raw model reasoning, transcripts, or secret-like tokens.

The parity check preserves v0.4 workflow markers: home remains `data-home-primary-workflow="single-supported-stock-or-etf-search"`, `data-search-comparison-route` keeps `A vs B` search routed to `/compare`, comparison remains a separate connected workflow, glossary remains contextual, source/glossary/chat mobile behavior stays bottom-sheet or full-screen oriented through `data-source-drawer-mobile-presentation="bottom-sheet"`, `data-glossary-mobile-presentation="bottom-sheet"`, and `data-asset-chat-mobile-presentation="bottom-sheet-or-full-screen"`, and stock-vs-ETF relationship badges stay present.

Weekly News Focus remains evidence-limited. "No major Weekly News Focus items found" is valid when evidence is thin, and AI Comprehensive Analysis remains suppressed unless at least two approved Weekly News Focus items exist. The parity check must not pad Weekly News Focus items or treat comparison/export parity as live-provider, live-AI, ETF-500, Top-500, source approval, manifest promotion, production, deployment, generated-output cache persistence, or public-launch readiness.

## Lightweight Fresh-Data Fetch Smoke

The personal-MVP fresh-data fetch path is explicit and opt-in. It prefers SEC official stock metadata and filings for stocks, uses local ETF manifest/scope signals for ETFs, and falls back to Yahoo Finance/yfinance-derived provider data for local-test fields when official issuer automation is incomplete. It returns normalized facts, source labels, freshness, and partial/unavailable gaps only; it does not return unrestricted raw payloads.

Task: T-144 / T-147 / T-153.

The local fresh-data MVP slice smoke is deterministic and CI-safe. It uses injected fixtures, does not need secrets, live provider calls, browser startup, or local services, and reports `pass`, `partial`, `blocked`, and `unavailable` states with source labels/counts, citation/fact counts, freshness/as-of metadata, generated-output eligibility, and `raw_payload_exposed=false`. T-153 extends the issuer-backed ETF rows to `SPY`, `VTI`, and `XLK` without broadening ETF-500, source approval, live issuer acquisition, generated-output cache promotion, or production deployment scope. T-151 adds a compact `fallback_diagnostics` object with schema `lightweight-api-fallback-diagnostics-v1`; it contains reason codes, source path, fetch state, page render state, generated-output eligibility, source label counts, official/provider/gap counts, issuer-evidence state, freshness/as-of summary, and `raw_payload_exposed=false`.

```bash
TMPDIR=/tmp python3 scripts/run_local_fresh_data_slice_smoke.py --json
```

Expected deterministic slice output:

- `AAPL`, `MSFT`, and `NVDA` report `pass` with SEC official source labels, provider-derived fallback labels, citations, freshness/as-of metadata, and available source drawer contracts.
- `VOO`, `QQQ`, `SPY`, `VTI`, and `XLK` report `pass` as issuer-backed ETF rows when deterministic official issuer fixture evidence is present. They include official issuer sources, citations, normalized benchmark, expense-ratio, prospectus, holdings/exposure facts or explicit unavailable gaps, source-drawer-ready metadata, freshness/as-of metadata, and separately labeled provider-derived market/reference fallback when present.
- `TQQQ`, `ARKK`, `BND`, and `GLD` report `blocked`; they remain generated-output-ineligible and do not unlock generated pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, generated risk summaries, or generated-output cache entries.
- The smoke output must not contain provider secrets, raw payload values, raw source text, or unrestricted provider responses.

Fallback diagnostic paths to expect:

- Stocks such as `AAPL`, `MSFT`, and `NVDA`: `fallback_diagnostics.source_path=sec_official_provider_fallback`.
- `VOO`, `QQQ`, `SPY`, `VTI`, and `XLK`: `fallback_diagnostics.source_path=issuer_backed_etf_provider_fallback` and `issuer_evidence_state=supported`.
- Other eligible ETFs without deterministic issuer fixtures: `fallback_diagnostics.source_path=etf_manifest_scope_provider_fallback` when they are locally renderable, partial, and provider-backed.
- Partial ETFs: none in the deterministic slice after T-153; T-156 reports `no_partial_etf_rows_in_current_slice` and uses the non-generated `SPY`/`VTI` pair as representative ETF-pair coverage without a source-backed comparison pack.
- Blocked tickers `TQQQ`, `ARKK`, `BND`, and `GLD`: `fallback_diagnostics.source_path=blocked_scope_screen`, `generated_output_eligible=false`, source/citation/fact counts of zero, and no generated surfaces unlocked.

When live lightweight mode is enabled, exact search and the existing asset-page contracts can use fresh renderable data:

- `/api/search?q=MSFT` can open a source-labeled local-MVP page even when the deterministic cached pack is absent.
- `/api/assets/{ticker}/overview` returns the existing overview contract with beginner summary, three risks, sections, citations, source documents, Weekly News Focus empty state, and AI Comprehensive Analysis suppression.
- `/api/assets/{ticker}/details` returns stock or ETF detail fields from the same source-labeled fetch.
- `/api/assets/{ticker}/sources` returns the source drawer contract with source groups, citation bindings, related claims, and section references.

Operators can inspect T-151 diagnostics in these API fields:

- Search: `GET /api/search?q=MSFT` or another live-fallback-resolved eligible/partial ticker returns `results[].fallback_diagnostics`. Cached deterministic fixture rows such as cached `VOO` may keep this field `null` unless the existing lightweight search fallback path is actually used.
- Overview: `GET /api/assets/{ticker}/overview` returns `fallback_diagnostics` when the lightweight page path renders.
- Details: `GET /api/assets/{ticker}/details` returns the same `fallback_diagnostics` when the lightweight page path renders.
- Sources/source drawer: `GET /api/assets/{ticker}/sources` returns the same `fallback_diagnostics` next to the source drawer diagnostics.
- Fresh-data and T-150 local live smoke summary: `GET /api/assets/{ticker}/fresh-data` returns `fallback_diagnostics`, and the optional `local-live-browser-api-mvp-slice-smoke-v1` summary includes it under `fresh_data_diagnostics[].fallback_diagnostics`.

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
- `VOO`, `QQQ`, `SPY`, `VTI`, and `XLK` should use deterministic issuer-backed enrichment before final provider-fallback shaping and may render as `supported` when official issuer facts and citations are present.
- Other renderable in-scope ETFs without deterministic issuer fixtures should include local ETF manifest/scope metadata or heuristic scope context plus Yahoo-labeled provider fallback, and must preserve explicit issuer-evidence gaps.
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

Task: T-127 baseline, updated by T-155.

The local live-AI validation smoke is operator-only and disabled by default. T-155 extends it from the original T-127 two-case smoke into a lightweight MVP-slice contract for:

- grounded chat for one supported stock (`AAPL`) and one supported ETF (`VOO`)
- AI Comprehensive Analysis for `QQQ` only when the T-154 Weekly News Focus threshold has at least two selected approved items
- zero-item and one-item Weekly News Focus cases that suppress AI output as empty or insufficient evidence
- blocked-product regression coverage for `TQQQ`, `ARKK`, `BND`, and `GLD`
- sanitized readiness and validation diagnostics only

The smoke does not approve sources, does not relax Golden Asset Source Handoff, does not promote ETF-500 or Top-500 coverage, does not mark deployment readiness, does not provide investment advice, does not write generated-output cache records, and does not print raw user text, prompts, source text, model reasoning, transcripts, generated live responses, raw provider payloads, or secret values.

Prerequisites:

- `LTT_LIVE_AI_SMOKE_ENABLED=true` for this shell only
- `LLM_PROVIDER=openrouter`
- `LLM_LIVE_GENERATION_ENABLED=true`
- server-side `OPENROUTER_API_KEY` presence in the operator shell, without echoing or pasting the value into logs
- OpenRouter base URL, free model chain, paid fallback model metadata, validation retry count, and `LLM_REASONING_SUMMARY_ONLY=true` remain configured server-side
- source evidence remains fixture-safe or already source-governed; this command is validation, not source approval

Command:

```bash
LTT_LIVE_AI_SMOKE_ENABLED=true \
LLM_PROVIDER=openrouter \
LLM_LIVE_GENERATION_ENABLED=true \
TMPDIR=/tmp python3 scripts/run_live_ai_validation_smoke.py --json
```

Deterministic mocked test path:

```bash
TMPDIR=/tmp python3 -m pytest tests/unit/test_llm_provider.py -q
TMPDIR=/tmp python3 evals/run_static_evals.py
```

Expected results:

- without `LTT_LIVE_AI_SMOKE_ENABLED=true`, all six smoke cases report `skipped`
- without live-generation readiness or server-side key presence, the stock chat, ETF chat, and two-item analysis cases report `blocked` with env var names and safe reason codes only
- with readiness and valid output, the stock chat, ETF chat, two-item analysis, zero-item suppression, one-item suppression, and blocked-regression cases report `pass`
- zero selected Weekly News Focus items remain an empty state, one selected item remains insufficient evidence, and neither case treats live or mocked AI output as usable
- `normal_ci_requires_live_calls=false`, `live_network_calls_attempted=false` for mocked tests, and `generated_output_cache_entries_written=false`
- failed schema, citation, source-use, freshness, safety, evidence-threshold, or cache-eligibility checks report `blocked`

Stop conditions:

- any blocked validation result
- fewer than two approved Weekly News Focus items for the AI Comprehensive Analysis case
- any generated single-asset chat answer that includes a second ticker instead of staying grounded to the selected asset
- any generated AI Comprehensive Analysis section order other than What Changed This Week, Market Context, Business/Fund Context, and Risk Context
- any generated claim that lacks same-asset or same-pack citation binding, source-use eligibility, freshness or uncertainty labels, and educational framing
- any generated output for `TQQQ`, `ARKK`, `BND`, or `GLD`
- any diagnostic or log path that would expose raw user text, prompts, source text, generated live responses, model reasoning, transcripts, unrestricted provider payloads, or secret values
- any attempt to treat local live-AI review as source approval, Golden Asset Source Handoff approval, generated-output cache promotion, ETF-500 or Top-500 completion, production readiness, or investment advice

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

T-150 adds the named lightweight live browser/API MVP slice smoke runner command for the same already-running local services:

```bash
LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000 LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000 DATA_POLICY_MODE=lightweight LIGHTWEIGHT_LIVE_FETCH_ENABLED=true LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true SEC_EDGAR_USER_AGENT="learn-the-ticker-local/0.1 contact@example.com" TMPDIR=/tmp npm run test:local-live-slice-smoke
```

The T-150 runner is still operator-only and skipped by deterministic CI. It sets `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1` and `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1` for the smoke process, then validates the existing running-service contract without starting Next, FastAPI, Docker, live AI, or any provider process.

The smoke summary uses schema `local-live-browser-api-mvp-slice-smoke-v1` and prints sanitized metadata only:

- API/proxy bases: normalized `next_api_proxy_base` and `direct_fastapi_base`.
- Per-ticker source labels, source/citation/fact/gap counts, freshness/as-of metadata, fetch state, page render state, generated-output eligibility, and partial/unavailable states.
- Blocked export diagnostics for `TQQQ`, `ARKK`, `BND`, and `GLD` across asset-page and source-list JSON exports through both the Next proxy and direct FastAPI base.
- No-raw-payload/no-secret diagnostics showing raw payload values and secret values were not reported.

Old strict source-pack/readiness stop conditions are audit diagnostics for this local lightweight path, not failure conditions for lightweight live browser/API smoke when the fresh-data response is renderable, source-labeled, and raw payloads remain hidden. This includes strict Golden Asset Source Handoff, ETF-500 source-pack, Top-500 source-pack, parser, checksum, manifest-promotion, and broad readiness gates. Those strict gates still matter for audit-quality promotion and public-launch hardening; they do not block this local personal-MVP smoke contract.

T-152 adds a named lightweight live durable MVP slice smoke runner for the same already-running local services plus local durable repository settings:

```bash
LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000 LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000 DATA_POLICY_MODE=lightweight LIGHTWEIGHT_LIVE_FETCH_ENABLED=true LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true LEARN_TICKER_LOCAL_DURABLE_SMOKE=1 LOCAL_DURABLE_REPOSITORIES_ENABLED=true LOCAL_DURABLE_OBJECT_NAMESPACE=ticker-smoke DATABASE_URL="<local durable repository DSN, placeholder-only>" SEC_EDGAR_USER_AGENT="learn-the-ticker-local/0.1 contact@example.com" TMPDIR=/tmp npm run test:local-live-durable-slice-smoke
```

The T-152 runner is still operator-only and skipped by deterministic CI. The npm command sets `LEARN_TICKER_LOCAL_BROWSER_SMOKE=1`, `LEARN_TICKER_LOCAL_FRESH_DATA_SLICE_SMOKE=1`, and `LEARN_TICKER_LOCAL_DURABLE_SMOKE=1` for the smoke process, then validates the live lightweight slice through the Next proxy and direct FastAPI paths without starting services, Docker, live AI, or production storage.

The durable-live contract summary uses schema `local-live-durable-mvp-slice-smoke-v1` and adds `durable_repository_diagnostics` with sanitized metadata only:

- prerequisite status reports env var names, set/missing booleans, placeholder-local database status, non-public object-namespace status, and safe reason codes.
- repository mode reports `local_durable`, whether local durable repositories are enabled, and confirms production database and production storage are not used.
- persistence availability reports whether throwaway durable writes or direct repository-read proof are available. When the current browser/API path cannot prove a real durable write/read, it reports blocked optional reason codes such as `throwaway_durable_write_api_not_exercised_by_browser_smoke` and `repository_read_proof_not_exposed_by_lightweight_fresh_data_api` instead of pretending persistence passed.
- stable repeated reads for representative renderable rows are checked across fresh-data, overview, details, sources, asset JSON export, and source-list JSON export surfaces. Repeated reads compare only smoke-level stable fields.
- safe record metadata includes counts plus hashed record keys and checksums only; it does not print raw keys, DSNs, namespace values, raw provider payloads, raw source text, hidden prompts, model reasoning, or credential-like values.
- fallback diagnostic summaries include `lightweight-api-fallback-diagnostics-v1` source paths and reason codes, while freshness/as-of summaries and generated-output eligibility remain compact.
- no-raw/no-secret flags confirm raw payload values, secret values, database DSN values, object namespace values, hidden prompts, and model reasoning were not reported.

Expected durable-live states:

- `pass`: local services are reachable, all live lightweight slice probes pass, representative repeated-read checks pass, and durable diagnostics are sanitized.
- `blocked`: required local-service, lightweight live, durable, placeholder-local database, non-public namespace, or placeholder SEC user-agent prerequisites are missing or unsafe, or a slice/blocking/export regression is detected.

This smoke is local durability validation only. It does not approve Golden Asset Source Handoff, promote manifests, create production cache fixtures, broaden support classification, convert `SPY` issuer gaps into issuer evidence, or unlock generated output for `TQQQ`, `ARKK`, `BND`, `GLD`, unknown tickers, or any clearly unsupported product.

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
- `SPY`, `VTI`, and `XLK` are probed through `/api/assets/{ticker}/fresh-data` via both the frontend proxy and direct FastAPI. They should return JSON rather than a Next HTML fallback, ETF identity, supported issuer-backed render state, generated-output eligibility, official issuer/source labels, provider-derived fallback labeling where present, citations, freshness/as-of metadata, and explicit partial/unavailable labels only for remaining unsupported fields such as current premium/discount or bid-ask spread.
- Representative stock and ETF rows also check `/api/search`, `/api/assets/{ticker}/overview`, `/api/assets/{ticker}/details`, and `/api/assets/{ticker}/sources` through both the Next proxy and direct FastAPI running-service contract so overview, details, citation, freshness, and source-drawer surfaces remain API-backed.
- The blocked regression tickers `TQQQ`, `ARKK`, `BND`, and `GLD` remain generated-output-ineligible. They must not receive generated pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, available exports, generated risk summaries, source documents, citations, facts, provider fetches from the slice smoke, or generated-output cache writes. Their asset-page and source-list JSON exports return unsupported or unavailable export-safe blocked states with empty factual evidence.
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
- `SPY`, `VTI`, and `XLK` still return ETF identity, supported issuer-backed render state, generated-output eligibility, official issuer/source labels, provider-derived fallback labels where present, citations, freshness/as-of metadata, and explicit partial/unavailable labels only for remaining unsupported fields such as current premium/discount or bid-ask spread through both paths.
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
