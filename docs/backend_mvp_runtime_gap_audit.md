# MVP Fresh-Data Runtime Gap Audit

Task: 2026-04-27 control-doc refresh after updated PRD, technical design spec, and proposal.

Purpose: rebaseline the project after the deterministic contract work through T-113 and the updated Top-500 manifest workflow plus Golden Asset Source Handoff policy. This audit separates what is already implemented from what still has to land before the MVP can locally ingest fresh official data, approve evidence, persist it, generate validated outputs, and render it through the frontend.

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
- T-101 through T-113 established configured persisted readers, executable ledger and worker boundaries, mocked SEC and ETF issuer acquisition, source snapshot records, normalized knowledge-pack writes, Weekly News event evidence records, generated-output cache writes, API-backed frontend rendering, end-to-end persisted verification, local durable repository execution with in-memory fallback, and opt-in live acquisition readiness for SEC, issuer, and Weekly News golden paths.

The MVP is still not locally fresh-data functional end to end:

- official-source acquisition readiness is mocked and golden-asset scoped
- real allowlisted fetchers and parsers are not the normal local path
- Golden Asset Source Handoff is partially represented through source-use policy and allowlist status, but the updated approval fields are not yet enforced across every persistence, citation, generation, cache, source drawer, and export boundary
- the Top-500 monthly candidate-manifest workflow does not yet exist
- a newly fetched official source cannot yet be run through a documented local ingest-to-persist-to-render workflow and verified in the frontend
- production deployment, admin protections, rate limiting, recurring jobs, monitoring, rollback, and cost controls remain later work

## Area Tracker

| Area | Status | Current deterministic state | Functional MVP blocker | Next task area |
| --- | --- | --- | --- | --- |
| Route contracts and fixture fallback | `deterministic_complete` | Public schemas and fixture fallback are broad and stable. | Fresh persisted data still needs a proven local run. | Preserve in T-114 and later local fresh-data verification. |
| Configured persisted readers | `deterministic_complete` | App-level dependencies can prefer configured knowledge-pack, cache, Weekly News, ledger, and source repositories with fallback. | Local configuration and migration execution need fresh-data verification. | T-118 local fresh-data runbook and smoke. |
| Ingestion ledger and worker | `deterministic_complete` | Manual ingestion and pre-cache job states can execute through mocked outcomes and in-memory or local durable boundaries. | Real official fetch and parser outcomes are not yet the normal path. | T-117 official-source acquisition execution. |
| Source snapshot storage | `contract_complete` | Rights-aware source snapshot records and private artifact metadata exist. | Fresh retrieved sources need Golden Asset Source Handoff before snapshot writes. | T-115 then T-117. |
| Normalized knowledge-pack persistence | `deterministic_complete` | Knowledge-pack repository contracts and writes from deterministic acquisition outputs exist. | Real parser outputs need to populate normalized facts and evidence gaps. | T-117. |
| Generated-output cache writes | `deterministic_complete` | Cache writes and freshness invalidation exist for validated deterministic outputs. | Fresh-source inputs need handoff metadata and validation before cache writes. | T-115 then T-118. |
| Weekly News Focus evidence | `deterministic_complete` | Official-source event evidence records, selection, windows, and persisted reads exist for golden paths. | Real official event fetchers are readiness-only and mocked. | T-117. |
| Golden Asset Source Handoff | `runtime_gap` | Source allowlist and source-use gates exist. | Updated PRD requires approval status, official-source status, storage rights, export rights, parser status, freshness/as-of metadata, rationale, and review status across evidence boundaries. | T-115. |
| Top-500 current manifest | `contract_complete` | Runtime support classification reads the approved current manifest. | Current file is a small fixture manifest, not the reviewed top-500 candidate output. | T-116. |
| Top-500 candidate refresh | `runtime_gap` | Policy is documented in PRD/TDS/proposal. | No IWB primary workflow, fallback workflow, SEC/Nasdaq validation, diff report, or reviewable PR workflow exists. | T-116. |
| Frontend API rendering | `deterministic_complete` | Search and dynamic asset pages call backend APIs with deterministic fallback and MVP workflow markers. | A fresh persisted asset needs a local browser/dev-server verification path. | T-118. |
| Launch pre-cache readiness | `current` | T-114 is promoted for deterministic launch pre-cache expansion and MVP readiness regression coverage. | It does not make fresh acquisition or production deployment complete. | T-114. |
| Production hardening | `production_gap` | Free-tier target architecture is documented. | Admin auth, rate limiting, migration execution, private storage, Cloud Run settings, recurring jobs, monitoring, rollback, and budget checks are not done. | Later after T-118. |

## Fresh-Data MVP Blockers

The local functional MVP still needs these gaps closed, in order:

1. Finish T-114 so launch-readiness regression coverage and go/no-go documentation lock down existing behavior before broader runtime changes.
2. Add Golden Asset Source Handoff as a first-class contract across source records, repository rows, source snapshots, normalized knowledge packs, citations, generated-output cache records, source drawer output, and exports.
3. Add the reviewed Top-500 candidate-manifest workflow so the app can move from a 10-entry fixture manifest toward a real top-500 launch manifest without making live runtime coverage decisions.
4. Add official-source acquisition execution for golden assets through mocked HTTP tests and explicit local opt-in, including parser diagnostics and handoff-gated persistence.
5. Prove a local fresh-data run from manual ingestion through persisted data, generated-output cache validation, backend routes, frontend rendering, and export/source drawer behavior.
6. Only after local fresh-data behavior is reliable, add production hardening for admin routes, rate limiting, deployment env validation, private storage, database migrations, Cloud Run service/job settings, recurring job decisions, monitoring, rollback, and cost controls.

## Refined Agent Track

Current promoted task:

- T-114: deterministic launch pre-cache expansion and MVP readiness regression matrix. This should preserve v0.4 frontend behavior, source/freshness states, Weekly News evidence limits, AI Comprehensive Analysis thresholds, safety gates, and no-live-call defaults.

Next runnable backlog after T-114:

- T-115: add Golden Asset Source Handoff contract fields and fail-closed validation across source policy, source snapshots, knowledge packs, citations, generated-output cache, source drawer, and exports.
- T-116: add Top-500 candidate-manifest generation and validation contracts using official IWB primary input, official SPY/IVV/VOO fallback inputs, SEC/Nasdaq validation, checksums, warnings, and diff-report output.
- T-117: add handoff-gated official-source acquisition execution for golden SEC stock, ETF issuer, and Weekly News paths with injected mocked HTTP tests and explicit local opt-in.
- T-118: add local fresh-data ingest-to-render runbook and smoke coverage that verifies a manually ingested golden asset can render through backend APIs, frontend pages, source drawer, exports, Weekly News, and generated-output cache without weakening deterministic CI.

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
