# Delivery plan

[ SPEC.md](SPEC.md) defines the finished product. This plan owns milestone scope and acceptance; [TASKS](TASKS.md) owns actionable states and [STATUS](STATUS.md) current progress. The original D01–D21 mapping is in [the audit](docs/project-audit.md). Windows public v1 is the delivery finish line; later platforms remain deferred.

**A milestone cannot be marked complete while any required validation for that milestone is failing.**

All milestones preserve existing useful behavior and safety/source boundaries. Required missing checks are incomplete, not passed. Do not begin application implementation until M0 is verified and committed. A blocked dependency prevents dependent milestones; independent tasks within the current milestone may continue.

## Validation groups

Commands and prerequisites live in [EVALS](EVALS.md#verification-tiers). Q is the shared milestone gate; F fast checks; C contract checks; R security/evidence/provider scenarios; D actual isolated PostgreSQL lifecycle/restore; B browser UI acceptance; N native/packaged acceptance; L explicit live-provider qualification; W clean-machine Windows release acceptance. Focused commands below use repository Python (virtual environment preferred); tests/desktop gains new scenarios as their features land, without pretending unimplemented harnesses already exist.

## M0 — Delivery foundation

- Objective: Document ownership/traceability, non-writing schema checks, linting, wrapper failure behavior and CI.
- Dependencies: None.
- Components: Governance documents, archives, verification scripts, delivery skill and CI.
- Acceptance: Every P requirement and D01–D21 item mapped; historical dates preserved; skill discoverable/tracked; all local links resolve; existing scenarios preserved; foundation quality gate passes and reviewed local commit exists.
- Validation: Q, F; wrapper/validator tests; skill validator; Windows and Bash wrapper checks; CI definition inspection. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all foundation acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Later live/native acceptance remains required by its owning milestones.

## M1 — Codex runtime qualification

- Objective: Supported versions, capability truth, isolated tools/configuration, models, approvals, sessions and cancellation.
- Dependencies: M0.
- Components: Runtime contracts, runtime_base, codex_rpc/runtime/login, API and Connections.
- Acceptance: Installed/authenticated/qualified are distinguished; unsupported versions/tools fail closed; allowed capabilities have deterministic and explicit live evidence; consent/quota/reconnect/approval/cancellation work without credential leakage or inference replay.
- Validation: Q, C, R, B, L; tests/desktop/test_codex.py and test_terms.py. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## M2 — Verified research pipeline

- Objective: Independent identity; structured-first retrieval and cache freshness; numeric/date/unit/conflict/restatement admission; bounded gap investigation.
- Dependencies: M1.
- Components: Evidence/identity/source services, rights registry, contracts, research scheduling and persistence.
- Acceptance: Previously uncached categories resolve/disambiguate; wrong-asset/fabricated/unauthorized values fail admission; permitted history is normalized with missing data explicit; structured financial/news retrieval and autonomous live search/source-page reading work together; latest-information requests check source dates and refresh stale evidence; two retrieval jobs and one inference enforced; all numeric outputs trace to admitted evidence. Browsing observation and independent fact admission use separate gates (DEC-028); reused conversation evidence retains original version-scoped citations.
- Validation: Q, C, R, D; tests/desktop plus retained source/citation/ingestion tests; explicit live retrieval qualification outside CI. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## M3 — Imports

- Objective: Untrusted URL/PDF/CSV/XLSX imports with bounded parsing, provenance, rights and attachment portability.
- Dependencies: M2.
- Components: Import parsers, native selection, evidence service/UI and backup format.
- Acceptance: Malformed/oversized/injected documents fail safely; no filesystem traversal/private network retrieval; no-browsing providers use admitted imports only; retained attachments survive real restore before shipping.
- Validation: Q, C, R, D, B; extend tests/desktop import/archive scenarios. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## M4 — Progressive financial UI

- Objective: Financial section parity, independently admitted progressive sections, chart/return alignment, source review and recovery.
- Dependencies: M2.
- Components: Desktop App, retained financial components/lib, source review, evidence events and calculations.
- Acceptance: All useful financial sections adapted with citations/date/unit/rights; charts and returns use aligned admitted numeric evidence; missing/stale/partial/not-applicable states honest; normal and 640-pixel layouts and keyboard interactions pass.
- Validation: Q, C, R, D, B; frontend interaction scenarios plus calculations tests. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## M5 — Conversations and learning

- Objective: Scope/provider transitions, refresh, immutable reports, bilingual interpretations and cache behavior.
- Dependencies: M4.
- Components: Conversation/term services, routes, provider/model controls, saved versions and exports.
- Acceptance: Visible scope changes, history preservation and saved versions pass; language/level parity preserves original numbers/units/citations; hover performs no inference; notes/interpretations never become factual inputs; retention/bookmarks remain correct.
- Validation: Q, C, R, D, B, L; tests/desktop/test_storage.py and test_terms.py plus frontend. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## M6 — Comparisons and offline

- Objective: Migrate aligned mixed-type comparisons and persist previously generated results.
- Dependencies: M4.
- Components: Comparison service/contracts, saved results and comparison UI.
- Acceptance: Incompatible metrics/gaps explicit; no investment winner; online generation grounded in admitted evidence; offline cached pages/terms/previous comparisons work without new calculations or inference.
- Validation: Q, C, R, D, B; retained comparison regressions and desktop scenarios. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## M7 — Weekly and historical reports

- Objective: Migrate useful weekly algorithms and independent historical reports.
- Dependencies: M2, M4.
- Components: Weekly selector/date extraction, reports, source presentation and exports.
- Acceptance: Eastern dates/DST, deduplication, fewer-than-three Earlier context, two-item weekly minimum pass; older context never becomes weekly/canonical evidence; historical reports do not require recent news.
- Validation: Q, C, R, D, B; retained weekly tests plus production report integration. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## M8 — Gemini and Claude parity

- Objective: Qualify each provider separately using supported subscription mechanisms.
- Dependencies: M1, M5.
- Components: Provider-specific adapters/onboarding, shared AIRuntime contract and Connections.
- Acceptance: Gemini and Claude each pass isolated tools/auth/models/quotas/session/reconnect/cancellation/evidence checks live; cached-only limits visible; no API billing or silent provider fallback; unsupported integrations remain blockers rather than workarounds.
- Validation: Q, C, R, B, L separately for Gemini and Claude. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## M9 — Library and native lifecycle

- Objective: Protect saved evidence, enforce library operations and complete native failure handling.
- Dependencies: M3, M5, M6, M7.
- Components: Database/indexes, cache/retention/deletion, archives, Tauri supervisor and private PostgreSQL.
- Acceptance: 10-GB disposable cache honors protected permitted evidence; saved deletion/retention work; attachment/large-library restore and 1,000-asset baseline pass; occupied ports/duplicate locks/crashes/tray/Quit stop only owned processes.
- Validation: Q, C, R, D, B, N; measured scale and actual multi-cluster restore. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## M10 — Updates and rollback

- Objective: Verified artifacts, notify/approve/manual/auto updates, rollback and opt-in start-at-login.
- Dependencies: M9.
- Components: Update service, native startup, migration coordination and compatible library switching.
- Acceptance: Interrupted update/migration recovers; app/schema switch is coordinated; pre-upgrade restore validated separately; newer research preserved before rollback; future schema rejected; login-start setting actually works.
- Validation: Q, C, R, D, N; interruption and old/new app/schema matrix. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## M11 — Windows release acceptance

- Objective: Self-contained Windows x64 installer and full requirement review.
- Dependencies: M1–M10.
- Components: Packaging resources, installer/release workflow, notices and provider prerequisites.
- Acceptance: Clean VM has no Python/Node/PostgreSQL/developer tools; core app and all three connections qualify; install/update/rollback/backup/tray/Quit pass; dependencies/rights/notices and signatures reviewed; no required check missing; specification review finds no unresolved requirement.
- Validation: Q, C, R, D, B, N, L, W; full automated gate plus clean-machine and live evidence. Run Q with `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh`. Focused production scenarios use `python -m pytest tests/desktop -q`; foundation scenarios use `python -m pytest tests/unit/test_verification.py tests/unit/test_repo_contract.py -q`. Group-specific executable commands and manual scenarios are in EVALS.
- Exit: all acceptance checks above pass with dated evidence, tasks updated, reviewed checkpoint committed. Any missing live/native evidence keeps this milestone open.

## Compatibility and cleanup

Expand the existing Pydantic -> JSON Schema -> TypeScript pipeline for provider models/approvals, normalized values, imports/review, comparisons/reports and maintenance. Vendor events stop at AIRuntime. Changes to persisted records/archives require compatible versioned migration and actual restore evidence. Saved versions remain immutable.

Reuse financial UI/algorithms and migrate their regression checks before removing fixture-only dependencies. Do not reintroduce Top-500 coverage gating, hosted routes, mock production providers or duplicate legacy trees. [MIGRATION](docs/MIGRATION.md) owns compatibility details.

## Final specification review

M11-T02 independently inspects every SPEC requirement against implementation, tests and dated evidence. Identify forgotten, partial, untested, divergent or regressed behavior; repair and repeat affected/full checks. Numerical performance thresholds remain unapproved; collect baselines. No local release commit authorizes publishing, pushing, opening a PR or merging.
