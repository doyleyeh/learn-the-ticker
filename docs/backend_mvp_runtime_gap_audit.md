# Backend MVP Runtime Gap Audit

Task: T-100

Purpose: rebaseline the backend MVP runtime plan after the deterministic contract-scaffold work through T-099. This audit separates completed contracts from the fresh-data runtime path still needed to ingest official sources, persist knowledge packs, validate generated outputs, cache eligible artifacts, and render them through the frontend.

This is a planning artifact only. It does not wire live providers, change public route behavior, activate database or object-storage writes, enable generated-output cache writes, redesign frontend workflows, or expand deployment scope.

## Authority And Baseline

Safety and advice-boundary rules remain first. After that, the updated PRD is the product source of truth, the updated technical design spec is the engineering source of truth, then the proposal, SPEC, TASKS, and EVALS.

Frontend Design and Workflow v0.4 remains the planning baseline:

- home page single-asset stock or ETF search first
- comparison as a separate connected workflow
- glossary as contextual help inside reading flows
- mobile source, glossary, and chat surfaces as bottom sheets or full-screen panels where appropriate
- stock-vs-ETF comparison relationship badges and the single-company-vs-ETF-basket structure
- Weekly News Focus showing only the evidence-backed set, with AI Comprehensive Analysis suppressed when evidence is insufficient

## Status Vocabulary

- `contract_complete`: deterministic contracts, validation, fixtures, or tests exist, but this label alone does not imply a fresh-data runtime path.
- `runtime_gap`: a functional fresh-data MVP is blocked until this area is wired or executed.
- `current`: the active T-100 audit/tracker scope or the current deterministic behavior to preserve.
- `backlog`: a narrow planned task area that follows this audit.
- `later`: explicitly deferred until deterministic runtime parity exists.

## Runtime Gap Summary

The backend has broad deterministic contracts for search, overview/details, comparison, grounded chat, exports, source policy, persistence repositories, ingestion states, provider adapters, Weekly News Focus, generated-output cache metadata, trust metrics, and live-generation readiness.

The MVP is not yet fresh-data functional:

- public routes still default to fixtures where configured readers are absent
- ingestion jobs do not fetch real official sources
- persistence is not the normal read/write path
- provider adapters are fixture-backed
- generated-output cache writes are not activated for public output
- frontend asset/search pages still have local-fixture-first behavior for parts of the workflow

These are expected gaps, not defects to fix in T-100. The next tasks should close deterministic contract/runtime parity before live providers, paid providers, broad ingestion, or deployment hardening.

## Area Tracker

| Area | Status | Current deterministic state | Functional fresh-data blocker | Next task area |
| --- | --- | --- | --- | --- |
| T-100 audit artifact | `current` | This document records the runtime gap and next-step tracker. | None inside T-100; implementation changes are intentionally out of scope. | Keep as control evidence for T-101 through T-104. |
| Public route fixture baseline | `current` | Public API schemas and deterministic fixture outputs are stable. | Routes are not globally configured to prefer persisted readers at runtime. | T-101 route read-path wiring. |
| Source acquisition | `runtime_gap` | SEC and ETF issuer/provider adapter contracts are fixture-backed. | Jobs do not acquire fresh official SEC filings, issuer pages, fact sheets, prospectuses, holdings, or exposure files. | T-103 SEC golden-path acquisition; T-104 ETF issuer golden-path acquisition. |
| Provider adapters | `contract_complete` | Mocked provider and official-source adapter contracts normalize fixture metadata and gaps. | They are not a live acquisition path and do not make public output fresh-data functional. | Feed T-103 and T-104 mocked acquisition boundaries first. |
| Source snapshot storage | `runtime_gap` | Source snapshot artifact metadata contracts exist with private-storage and source-use constraints. | Runtime jobs do not write validated snapshots or parsed artifacts to configured private storage. | Unpromoted source snapshot execution task after T-103/T-104 acquisition records exist. |
| Normalized knowledge-pack persistence | `runtime_gap` | Repository contracts and persisted-pack readers exist. | Ingestion does not write normalized facts, evidence gaps, source checksums, and section freshness into configured persistence as the normal path. | Unpromoted knowledge-pack write task after T-102/T-104. |
| Configured route read-path wiring | `runtime_gap` | Overview, comparison, chat, and Weekly News Focus have injected persisted-read boundaries with fallback. | App-level route dependencies do not yet supply configured readers across public read paths. | T-101 route read-path wiring. |
| Generated-output cache writes | `runtime_gap` | Cache metadata, freshness hashes, rights checks, and validation contracts exist. | Public output does not activate writes for validated generated sections, comparisons, chat answers, or analysis. | Unpromoted cache-write activation after route reads and persisted packs are stable. |
| Weekly News Focus acquisition | `runtime_gap` | Event evidence contracts and deterministic selection/windowing exist. | Jobs do not acquire official filings, investor-relations releases, issuer announcements, prospectus updates, fact-sheet changes, or allowlisted compatible items into persisted event evidence. | After T-102, add official-source Weekly News acquisition execution. |
| Ingestion job execution | `runtime_gap` | Ledger and worker contracts exist with deterministic states. | Manual jobs are not executable through a configured local ledger with mocked acquisition outcomes. | T-102 executable ingestion jobs. |
| Frontend API rendering | `runtime_gap` | Frontend renders MVP surfaces from deterministic fixtures and selected backend adapters. | Search and asset pages remain local-fixture-first for parts of the workflow and do not yet render newly persisted dynamic assets end to end. | Unpromoted frontend API-backed search/rendering task after backend route wiring. |
| Launch-universe pre-cache | `backlog` | Top-500 and ETF manifests define operational coverage, and fixture assets cover the golden path. | The launch universe is not pre-cached through an ingest-to-persist-to-render runtime path. | Expand only after T-101 through T-104 and persisted writes are complete. |
| Exports and source-use enforcement | `contract_complete` | Rights-tier checks cover generated-claim support, cache eligibility, source-list export, allowed excerpts, and diagnostics. | Runtime exports still depend on available persisted/source metadata; enforcement itself is not the blocker. | Preserve in T-101 through cache-write tasks. |
| Live-generation readiness | `contract_complete` | Runtime diagnostics, mocked transport, validation, repair, and fallback orchestration contracts exist and are disabled by default. | Live generation is deliberately not part of the deterministic fresh-data parity milestone. | Keep later until persisted evidence, cache writes, and validation gates are stable. |
| Trust metrics | `contract_complete` | Metadata-only trust-metric catalog, validation, and sink contracts exist without external analytics. | Production analytics emission is not needed for the first fresh-data runtime path. | Later instrumentation after route/runtime parity. |
| Production hardening | `later` | Deployment target and no-live-call defaults are documented. | Route regression matrix, go/no-go checklist, credentials, recurring jobs, and deployment hardening wait until ingest-to-persist-to-render works locally. | Later production-hardening task. |

## Fresh-Data MVP Blockers

The functional fresh-data MVP remains blocked until these narrow runtime areas land:

1. T-101 wires public backend routes to configured persisted readers with fixture fallback.
2. T-102 makes ingestion jobs executable through the local ledger with mocked acquisition outcomes.
3. T-103 adds server-side SEC EDGAR acquisition for the stock golden path using mocked HTTP fixtures in tests.
4. T-104 adds official ETF issuer acquisition for the ETF golden path using mocked HTTP fixtures in tests.
5. Follow-up tasks persist source snapshots and normalized knowledge packs from acquisition outputs.
6. Follow-up tasks activate generated-output cache writes only for validated, citation-bound, source-policy-allowed output.
7. Follow-up tasks move frontend search and asset rendering from local-fixture-first behavior to backend API-backed dynamic data once the backend can ingest, persist, read, and validate it.

## Non-Goals For This Audit

T-100 must not add or enable:

- live external provider calls
- production database sessions or object-storage writes
- generated-output cache writes
- public route behavior changes
- frontend workflow rewrites
- source allowlist expansion
- paid-provider integration
- deployment credentials or recurring production jobs
- raw source text, unrestricted provider payloads, raw user text, hidden prompts, raw model reasoning, credentials, temporary storage access links, or frontend-readable storage paths

## Guardrails To Preserve

- Stable canonical facts stay separate from Weekly News Focus and AI Comprehensive Analysis.
- Important factual claims require citations or explicit uncertainty labels.
- Weekly News Focus stays evidence-limited and must not be padded.
- Unsupported and out-of-scope assets remain blocked from generated pages, generated chat answers, generated comparisons, and generated risk summaries.
- Source-use policy wins over scoring for display, generated-output support, caching, diagnostics, and exports.
- Normal CI remains deterministic and does not require live provider, market-data, news, storage, database, or LLM calls.
- Educational framing remains mandatory; the product must not provide personalized investment instructions, allocation instructions, tax guidance, brokerage/trading behavior, or unsupported price-target claims.
