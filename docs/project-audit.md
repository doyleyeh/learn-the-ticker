# Project audit — 2026-10-04

This is the one-time foundation audit, not the live backlog. Use [STATUS](../STATUS.md), [TASKS](../TASKS.md) and [PLAN](../PLAN.md) to continue.

## Current repository state

Baseline: clean codex/project-delivery-foundation at 2fd187f. Production is React/Vite/Tauri under apps/desktop and FastAPI under backend/app; generated contracts, SQLAlchemy/Alembic and private PostgreSQL are present. The full pre-change PowerShell gate passed 278 Python tests, static evaluations, seven frontend tests, type checking and Vite build. Rust tooling is absent. No live inference or installer is qualified.

Inspected tracked repository inventory, all 11 first-party Markdown documents including hidden review guidance, npm/Python/native manifests, environment example, Docker/Makefile/setup/packaging/check scripts, GitHub CI, production API/contracts/admission/orchestration/runtime/persistence/native structure, retained financial modules/components and unit/integration/desktop/evaluation suites. Ignored build/cache remnants are not authoritative source and are not deleted.

## Authoritative documents discovered

Before migration: PRD owned behavior, NEW_STRUCTURE accepted architecture, technical design mechanisms, IMPLEMENTATION backlog/results, TESTING commands, MIGRATION compatibility, PROPOSAL intent, README setup, AGENTS/CONTRIBUTING rules, hidden prompt manual review. New ownership is defined once in [AGENTS](../AGENTS.md).

## Duplicate and superseded documents

Archive PRD, PROPOSAL, NEW_STRUCTURE, IMPLEMENTATION and TESTING under docs/archive/2026-10-04. Their useful requirements/defaults/evidence survive in SPEC/DECISIONS/PLAN/TASKS/EVALS/STATUS or linked historical records. Old hosted/Top-500/agent-loop requirements are already superseded; do not recover them as active product requirements. Retained fixture algorithms/tests still protect behavior until migrated.

## Major contradictions resolved

- Old rules prohibited recreating SPEC/TASKS/EVALS. The explicit new request supersedes that document-organization decision, not the approved desktop product.
- Old AGENTS prohibited automatic agent-loop commits; the new delivery instruction authorizes reviewed local milestone commits. Push/PR/merge/publishing remain separate.
- A previous deletion ledger records removed historical/control documents. Preserve that dated statement; this migration intentionally introduces new canonical documents instead of rewriting the old ledger.
- Architecture requires progressive sections, three qualified providers, complete financial UI and installer. The current preview only publishes whole bundles, conservatively admits literal prose, disables Gemini, and has no native acceptance.
- Stored update/cache/start-at-login preferences are not operating features. Installed provider versions are not qualified capabilities. Original runtime checks can advertise generation/approvals too early; M1-T01 addresses this.
- The requested .codex skill path is an empty read-only ignored file. Preserve it locally before creating the skill directory and allowlist only that skill in Git.

## Implementation status and architectural gaps

Code and deterministic scenarios cover local authentication, immutable bundles, cache lookup, jobs/cancellation/recovery, source inspection, notes, reports/exports, conversations/bookmarks/expiry, term caching, and current-format backup/restore. PostgreSQL and synthetic-browser results from 2026-10-03 are historical, not newly rerun qualifications.

Open: independent identity and structured sources; numeric/date/unit validation and rights coverage; source-review queue; source-specific freshness and actual concurrent retrieval; incremental publication; imports; financial/chart/return parity; persisted comparisons and weekly/history reports; models/approvals/session qualification; Gemini/Claude onboarding; retention/deletion/scale; attachment/large archives; native failure cases; migration/update/rollback; reviewed runtimes/installer.

## Major testing gaps

No dedicated lint/format configuration, non-writing TS contract check, browser interaction harness, native CI or live-provider qualification. Current frontend tests largely use pure functions/server rendering; they do not establish full interactions. Normal CI never starts PostgreSQL. Static evaluations still cover retained legacy algorithms and must not be represented as current production coverage. SQLite does not qualify PostgreSQL migrations. Baseline timings are uncollected.

M0 adds narrow lint, shared verification, documentation links, non-writing schema checks, and manual isolated PostgreSQL CI. M1–M11 add behavioral acceptance. Broad style formatting and optional paid semantic review stay out.

## Requirement traceability

Every P-series requirement is retained in [SPEC](../SPEC.md). Verification groups are defined in [EVALS](../EVALS.md).

| Requirements | Milestones | Evidence focus |
| --- | --- | --- |
| P-001, P-002 | M4, M5, all | Equal learning levels/languages, educational boundaries |
| P-010, P-011 | M2 | Identity, cache, structured-first gaps/freshness |
| P-012, P-013, P-014 | M2, M4, all | Rights, evidence layers, numeric alignment, citations |
| P-015 | M3 | Bounded untrusted imports and cached-only explanation |
| P-020, P-021 | M4 | Financial parity, progressive UI and missing states |
| P-022, P-023 | M1, M5, M8 | Terms, visible scope, persistent history/provider switches |
| P-024 | M4, M5, M7, M9 | Immutable saves, refresh, cited permitted exports |
| P-025 | M6 | Comparable metrics, gaps and offline restrictions |
| P-030 | M7 | Eastern weekly intervals, sparse context, historical independence |
| P-031 | M2, M4 | History, restatements, returns and aligned valuations |
| P-040 | M1, M8 | All three live subscription integrations |
| P-041 | M1, M3, M9 | Local authentication, isolation, secrets, bounded input |
| P-042 | M9, M10 | Tray/Quit, start-at-login, updates/rollback |
| P-043 | M3, M9, M10 | Retention/deletion, backups, compatibility, newer data |
| P-044 | M2, M9 | Retrieval/inference limits and measured scale |
| P-045 | M0, M11 | Setup, licenses, self-contained Windows acceptance |

| Previous item | New destination | Carried evidence/status |
| --- | --- | --- |
| D01 Contracts | M0, M1–M11 as contracts expand | Initial schema/types implemented; response coverage incomplete |
| D02 Shell | M4, M9, M11 | Browser shell partial; native unqualified |
| D03 Sidecar | M9, M11 | Auth/source/packaged smoke historical pass; clean-machine open |
| D04 PostgreSQL | M9, M10, M11 | Lifecycle partial; failure matrix/runtime packaging open |
| D05 Persistence | M9 | Atomic publication verified; scale/library operations open |
| D06 Admission | M2, M4 | Conservative prose only; numeric/rights/date/conflicts open |
| D07 Jobs | M1, M2, M4 | Durable synthetic recovery pass; process trees/approvals open |
| D08 Codex | M1 | Experimental; no live acceptance |
| D09 Research | M2 | Synthetic categories/cache pass; independent retrieval open |
| D10 Progressive UI | M4 | Progress and whole bundle only |
| D11 Structured sources | M2 | Pending |
| D12 Imports | M3 | Pending |
| D13 Financial UX | M4 | Retained UI; production parity incomplete |
| D14 Conversations/terms | M5, M8 | Synthetic/persistence slices pass; live parity open |
| D15 Comparison/offline | M6 | Cached pages/terms work; comparisons incomplete |
| D16 Weekly/history | M7 | Legacy regression only |
| D17 Providers | M8 | Gemini disabled, Claude experimental |
| D18 Library | M3, M9 | Current JSON backup verified; cache/deletion/attachments open |
| D19 Updates/rollback | M10 | Pending |
| D20 Installer | M11 | Pending |
| D21 Later platforms | Deferred | macOS, then WSL, then Linux after Windows |

## Recommended documentation structure

Seven root canonical documents; technical design and migration as subordinate mechanisms/compatibility references; one audit report; dated verification records; historical archive; repo-scoped delivery skill. README and CONTRIBUTING are entry points, not duplicate plans. No required public-v1 capability is removed by this reorganization.
