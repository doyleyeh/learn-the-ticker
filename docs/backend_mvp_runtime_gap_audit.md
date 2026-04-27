# MVP Fresh-Data Runtime Gap Audit

Task: 2026-04-27 control-doc refresh after updated PRD, technical design spec, proposal, and T-119 local API/CORS fixes.

Purpose: rebaseline the project after deterministic contract work through T-119. This audit separates what is already implemented from what still has to land before the MVP can locally ingest fresh official data, approve evidence, persist it, generate validated outputs, and render it through the frontend under local browser testing.

This is a planning artifact only. It does not enable live providers, change public route behavior, run production persistence, add broad source coverage, deploy services, or alter frontend workflows.

## Authority And Baseline

Safety and advice-boundary rules remain first. After that, the PRD is the product source of truth, the technical design spec is the engineering source of truth, then the proposal, SPEC, TASKS, and EVALS.

Frontend Design and Workflow v0.4 remains the planning baseline:

- home page single-asset stock or ETF search first
- comparison as a separate connected workflow
- glossary as contextual help inside reading flows
- mobile source, glossary, and chat surfaces as bottom sheets or full-screen panels where appropriate
- stock-vs-ETF comparison relationship badges and the single-company-vs-ETF-basket structure
- Weekly News Focus showing only the evidence-backed set, with AI Comprehensive Analysis suppressed when evidence is insufficient

The updated evidence baseline is:

- Top-500 stock support is runtime manifest-owned by `data/universes/us_common_stocks_top500.current.json`.
- Runtime coverage must never be resolved directly from a live ETF holdings file, provider holdings file, or provider ranking response.
- Top-500 refreshes produce reviewed candidate manifests, use official IWB holdings first, use official SPY/IVV/VOO holdings only as fallback inputs, validate against SEC and Nasdaq metadata, and require a diff report plus manual approval before promotion.
- Golden Asset Source Handoff is the approval layer between retrieval and evidence use. Fetching is not approval.

## Status Vocabulary

- `contract_complete`: deterministic contracts, validation, fixtures, or tests exist, but this label alone does not imply a fresh-data runtime path.
- `deterministic_complete`: a local deterministic path exists with mocks, fixtures, or in-memory repositories.
- `runtime_gap`: a functional fresh-data MVP is blocked until this area is wired or executed.
- `local_runtime_gap`: the repo has contracts, but a local ingest-to-persist-to-render run is not yet proven with fresh official data.
- `production_gap`: local behavior may exist, but production auth, deployment, scheduling, monitoring, or operations are not ready.
- `current`: the active promoted task or behavior to preserve.
- `backlog`: a narrow planned task area that follows the current task.
- `later`: explicitly deferred until local fresh-data behavior passes deterministic gates.

## Current Progress Snapshot

The project is well past planning-only:

- Backend route contracts exist for search, asset overview/details, knowledge packs, source drawer, Weekly News Focus, AI Comprehensive Analysis, comparison, grounded chat, glossary, exports, ingestion states, pre-cache states, trust metrics, and runtime diagnostics.
- Frontend surfaces exist for home search, dynamic asset pages, comparison, source metadata, freshness labels, contextual glossary, chat, and exports, with deterministic fallback.
- Deterministic tests and evals cover search/support classification, citations, source policy, safety, Weekly News Focus, cache/freshness hashes, exports, glossary, comparison, chat, provider adapters, ingestion jobs, repository contracts, and frontend smoke markers.
- The Top-500 manifest contract is implemented, but the checked-in current manifest is a 10-entry fixture manifest for `AAPL`, `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `BRK.B`, `JPM`, and `UNH`, not a full reviewed 500-name launch manifest.
- ETF manifest metadata exists for supported, eligible-not-cached, unsupported, and out-of-scope ETF states. Local generated ETF pages are still limited to the fixture-backed cached path.
- T-101 through T-119 established configured persisted readers, executable ledger and worker boundaries, mocked SEC and ETF issuer acquisition, source snapshot records, normalized knowledge-pack writes, Weekly News event evidence records, generated-output cache writes, API-backed frontend rendering, end-to-end persisted verification, local durable repository execution with in-memory fallback, opt-in live acquisition readiness for SEC/issuer/Weekly News golden paths, Golden Asset Source Handoff enforcement, reviewed Top-500 candidate workflow contracts, local fresh-data ingest-to-render runbook coverage, and local browser API/CORS plumbing for chat, exports, and comparison.

The MVP is closer, but still not fully locally fresh-data functional end to end:

- official-source acquisition readiness is mocked and golden-asset scoped
- real allowlisted fetchers and parsers are not the normal local path
- the local fresh-data smoke path is deterministic and in-memory/mocked by default, not a proven local durable Postgres/object-storage run
- local browser verification is still manual curl/dev-server smoke, not an automated localhost browser E2E check
- a newly fetched real official source cannot yet be run through handoff-gated local fetcher execution as the normal path
- the checked-in current Top-500 manifest remains a small fixture manifest; candidate workflow contracts exist, but no real reviewed 500-name manifest has been promoted
- production deployment, admin protections, rate limiting, recurring jobs, monitoring, rollback, and cost controls remain later work

## Area Tracker

| Area | Status | Current deterministic state | Functional MVP blocker | Next task area |
| --- | --- | --- | --- | --- |
| Route contracts and fixture fallback | `deterministic_complete` | Public schemas and fixture fallback are broad and stable. | Fresh real-source persisted data still needs a proven local durable/browser run. | Preserve in T-120 and T-121. |
| Configured persisted readers | `deterministic_complete` | App-level dependencies can prefer configured knowledge-pack, cache, Weekly News, ledger, and source repositories with fallback. | Optional local durable smoke still needs proof outside in-memory/mocked CI. | T-120. |
| Ingestion ledger and worker | `deterministic_complete` | Manual ingestion and pre-cache job states can execute through mocked outcomes and in-memory or local durable boundaries. | Real official fetch and parser outcomes are not yet the normal path. | T-122. |
| Source snapshot storage | `deterministic_complete` | Rights-aware source snapshot records and private artifact metadata exist behind handoff gates. | Real retrieved source snapshots still need operator-only fetcher execution and parser diagnostics. | T-122. |
| Normalized knowledge-pack persistence | `deterministic_complete` | Knowledge-pack repository contracts and writes from deterministic acquisition outputs exist. | Real parser outputs need to populate normalized facts and evidence gaps under handoff approval. | T-122. |
| Generated-output cache writes | `deterministic_complete` | Cache writes and freshness invalidation exist for validated deterministic outputs. | Fresh-source inputs need real handoff-gated fetch/parser execution before cache writes. | T-122. |
| Weekly News Focus evidence | `deterministic_complete` | Official-source event evidence records, selection, windows, and persisted reads exist for golden paths. | Real official event fetchers are readiness-only and mocked. | T-122. |
| Golden Asset Source Handoff | `deterministic_complete` | Approval metadata and fail-closed validation are enforced across source policy, snapshots, knowledge packs, citations, cache, source drawer, and exports. | Real fetchers must populate the same fields before evidence use. | Preserve in T-122 and later. |
| Top-500 current manifest | `contract_complete` | Runtime support classification reads the approved current manifest. | Current file is a small fixture manifest, not a reviewed top-500 launch manifest. | T-123. |
| Top-500 candidate refresh | `deterministic_complete` | IWB primary, SPY/IVV/VOO fallback, SEC/Nasdaq validation, checksums, warnings, diff report, and manual-promotion gates exist as deterministic contracts. | A real reviewed candidate has not been generated, reviewed, or promoted. | T-123. |
| Frontend API rendering | `deterministic_complete` | Search, asset pages, chat, export links, and comparison helpers can target the backend via API base or local Next rewrite, with deterministic fallback where appropriate. | Automated localhost browser E2E is still missing. | T-121. |
| FastAPI CORS | `deterministic_complete` | `CORS_ALLOWED_ORIGINS` is parsed into FastAPI CORS middleware when available. | Production origin review remains deployment-hardening work. | Preserve in deployment tasks. |
| Launch pre-cache readiness | `deterministic_complete` | Deterministic launch pre-cache expansion and MVP readiness regression coverage exist. | It does not make real broad acquisition or production deployment complete. | Preserve. |
| Production hardening | `production_gap` | Free-tier target architecture is documented. | Admin auth, rate limiting, migration execution, private storage, Cloud Run settings, recurring jobs, monitoring, rollback, and budget checks are not done. | Later after T-120 through T-123. |

## Fresh-Data MVP Blockers

The local functional MVP still needs these gaps closed, in order:

1. Prove optional local durable repository execution through the T-118/T-119 route and browser surfaces when Docker/Postgres/object-storage substitutes are available.
2. Add automated localhost browser E2E smoke for the local web/API pairing so chat, exports, comparison, source drawer, glossary, and CORS regressions are caught before production work.
3. Promote real official-source fetcher execution for golden assets behind explicit local opt-in and Golden Asset Source Handoff approval, while keeping CI mocked.
4. Prepare reviewed launch-universe expansion from candidate contracts toward a real top-500 stock manifest and ETF launch pack without changing runtime support truth until review.
5. Only after local fresh-data behavior is reliable, add production hardening for admin routes, rate limiting, deployment env validation, private storage, database migrations, Cloud Run service/job settings, recurring job decisions, monitoring, rollback, and cost controls.

## Refined Agent Track

Current promoted task:

- T-119 is complete: local frontend API access and FastAPI CORS are wired for chat, exports, comparison, and direct browser API calls.

Next runnable backlog after T-119:

- T-120: prove optional local durable repository smoke with API proxy/CORS enabled.
- T-121: add automated localhost browser E2E smoke for API-backed MVP flows.
- T-122: promote real official-source fetchers behind handoff-gated local opt-in for golden assets.
- T-123: prepare reviewed launch-universe expansion planning without unreviewed manifest promotion.

Later, unpromoted work:

- production admin auth and rate limiting
- production database migration execution and private object-storage setup
- Cloud Run service and Cloud Run Job deployment settings
- recurring manifest and ingestion job decisions
- monitoring, rollback, cost controls, and launch support procedures
- broad paid-provider or news-provider integrations after licensing/source-use review
- post-MVP accounts, saved assets, watchlists, PDF exports, localization, richer analytics dashboards, and broader provider enrichment

## Non-Goals For This Audit

This audit must not add or enable:

- live external calls in CI
- production database sessions or object-storage writes
- generated-output changes
- public route behavior changes
- frontend workflow redesign
- source allowlist expansion
- broad paid-provider integration
- deployment credentials or recurring production jobs
- raw restricted source text, unrestricted provider payloads, raw user text, hidden prompts, raw model reasoning, credentials, temporary storage access links, or frontend-readable storage paths

## Guardrails To Preserve

- Stable canonical facts stay separate from Weekly News Focus and AI Comprehensive Analysis.
- Important factual claims require citations or explicit uncertainty labels.
- Weekly News Focus stays evidence-limited and must not be padded.
- Unsupported and out-of-scope assets remain blocked from generated pages, generated chat answers, generated comparisons, and generated risk summaries.
- Source-use policy and Golden Asset Source Handoff win over scoring, convenience, and provider availability.
- Top-500 runtime coverage remains manifest-owned.
- Normal CI remains deterministic and does not require live provider, market-data, news, storage, database, or LLM calls.
- Educational framing remains mandatory; the product must not provide personalized investment instructions, allocation instructions, tax guidance, brokerage/trading behavior, or unsupported price-target claims.
