# Research job recovery — 2026-10-04

M4-T02a implements independent existing-job recovery. It does not close M4-T02's progressive admission/source review or M4's price/return/valuation acceptance. No dependency, SQL/archive revision, provider capability or permission boundary changed.

## Behavior

The authenticated no-store job-list endpoint selects at most 50 research summaries, active work first and then newest requests. It excludes document/term learning jobs, results, errors and events from the projection. Opening a listed job only reads its existing ID. Terminal results retain their original immutable evidence version; failed/cancelled/interrupted work is visibly stopped and requires an explicit new request. No credentials are stored in browser persistence.

The observer treats socket events as progress and reads authoritative state from the job endpoint. Socket/API failure falls back to polling without overlapping requests. Cleanup aborts the fetch and ignores late results. No recovery path submits research, changes provider/model settings or grants consent. Native bootstrap remains automatic; a developer browser reconnects with its temporary credential.

## Evidence

- Q passed **1,264 Python/32 frontend tests**, lint, generated contracts, documentation, static checks, TypeScript and production build. Final presentation/documentation follow-up is recorded at checkpoint below.
- Eighteen focused backend/storage/runtime scenarios passed. Four new backend cases cover active-first bounded projection, excluded raw/learning data, authentication/origin, interrupted startup, active rediscovery/cancellation and restore. Four new frontend cases cover socket loss/transient read failure without generation, nonoverlap/late cleanup, escaped metadata and recovery disclosures.
- Actual D passed private PostgreSQL initialization, lifecycle, transaction rollback/commit and restore/restart. Source/target/restarted job discovery preserved original requests and completed metadata, excluded learning jobs, and kept unfinished work interrupted. The original restored evidence/citation and attachment checks also passed; no provider was called.
- B used Chrome via Playwright CLI and the explicit `--recovery-demo` fixture because the in-app browser backend was unavailable. Started exactly two synthetic research jobs. First: reload/reconnect, rediscover and reopen its completed version. Second: reload/reconnect, reopen the same running job and cancel. Request logs showed two deliberate POST research calls total, GETs for recovery and one explicit POST cancel; no additional generation appeared. Reopened previous failed/interrupted jobs and their stopped-state disclosure. Keyboard focus/Enter reopened an older completed job and its original dated source drawer, distinct from the newer version.
- Normal and 640-pixel screenshots were inspected; the 640-pixel viewport and document width matched. Original publication/as-of gaps, retrieval date, permission/provenance and quotation remained visible. Console after reload: zero errors, one existing React DevTools shim warning. Ignored screenshots: `output/playwright/research-jobs-wide.png`, `research-jobs-640.png`, `recovered-original-source-640.png`.

## Repairs and limits

The first frontend run found a Windows module-name collision between `ResearchJobs.tsx` and `researchJobs.ts`; renamed the observer to `researchObservation.ts`, after which all frontend tests and TypeScript passed. The first dev-server command redundantly forwarded a host argument as a root path and returned HTTP failure; restarting with the existing `npm run dev` command fixed the test setup. One stale/mistyped element reference and one main-frame-only measurement were retried from current observed references; the scoped width check passed. These were visible failures, not skipped checks.

This is deterministic production-path recovery with a synthetic runtime. No live provider check or new installer/native acceptance is claimed; those interfaces and capabilities were unchanged. Browser/backend/Vite test processes were stopped after verification. Market data access/rights remain unresolved in the [separate investigation](2026-10-04-market-source-investigation.md).

## Checkpoint

Final F, all 32 frontend tests and production build passed after presentation/documentation edits. Full diff and generated contracts were reviewed; no credentials, raw provider diagnostics or unrelated files were staged. The test listeners stopped. M4-T02a is complete. Next independent work is M4-T02b progressive admission; optional source review and parent M4-T02/M4 acceptance remain incomplete.
