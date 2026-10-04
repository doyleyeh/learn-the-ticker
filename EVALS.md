# Verification contract

[EVALS](EVALS.md) owns commands and acceptance scenarios. [STATUS](STATUS.md) owns latest results; [PLAN](PLAN.md) selects required groups per milestone. Use the repository Python: .venv/Scripts/python.exe on Windows, .venv/bin/python on POSIX. Wrappers prefer those environments, then system Python; dependencies come from README setup. Commands below run from repository root.

## Verification tiers

| Group/tier | Exact command | What passing establishes |
| --- | --- | --- |
| F — fast | `python -m scripts.verify fast` | Ruff correctness lint, ESLint correctness lint, non-writing schema checks, local Markdown links/anchors, Git whitespace and TypeScript |
| Q — milestone | `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` or `bash scripts/run_quality_gate.sh` | Shared fast checks plus all Python tests, static evaluations, frontend tests and build (which includes type checking once) |
| C — contracts | `python -m scripts.contracts --check` and `node scripts/generate_types.mjs --check` | Tracked schema and types match generated output without rewriting files |
| R — security/evidence/runtime | `python -m pytest tests/desktop tests/unit -q` and `python evals/run_static_evals.py` | Existing deterministic admission, safety, protocol, export and secret-boundary scenarios; add missing feature cases with implementation |
| D — database | `python -m scripts.verify database` | Private service, PostgreSQL transaction/recovery and actual restore checks; requires PostgreSQL 17 binaries |
| N — packaged | `python -m scripts.verify packaged` | Builds PyInstaller sidecar and exercises packaged service; native Windows x64 and PostgreSQL required |
| N — native | `python -m scripts.verify native` | Tauri build; requires Rust/MSVC, reviewed PostgreSQL resources and built sidecar; does not prove tray/installer behavior |
| Full automated | `python -m scripts.verify full` | Q, D, packaged and native checks; fails with missing prerequisites, never silently skips them |
| B — browser | Synthetic preview procedure below | Inspect interactions/citations/layout and record results; automated browser interaction harness remains M4-T03 |
| L — live provider | Explicit scenarios under Required before public v1 | Live harness remains M1-T05/M8; protocol-only smoke is not inference qualification |
| W — clean machine | Windows acceptance matrix under Required before public v1 | M11 clean VM evidence; no existing automated clean-machine harness is claimed |

The skill's verify-fast, verify-milestone and verify-full wrappers exist in both .ps1 and .sh forms under .codex/skills/project-delivery/scripts. Windows uses PowerShell or Git Bash; POSIX uses Bash. They invoke the same dispatcher as CI and preserve failing exit codes. Database/packaged/native subsets are explicit additional lanes, never replacements for Q.

Underlying commands remain `python -m pytest tests -q`, `python evals/run_static_evals.py`, `npm test`, `npm run typecheck`, and `npm run build`. Python integration tests live under tests/integration and desktop behavior under tests/desktop. Focused edits may select affected paths/cases. Production code must gain behavioral scenarios; legacy static evaluations alone do not qualify migrated features.

Correctness lint commands are `python -m ruff check backend scripts tests evals` and `npm run lint`. Formatting validation is limited to `git diff --check` and `git diff --cached --check`; no broad formatter is configured or claimed. Set LTT_VERIFY_BASE to a known Git revision to additionally check committed changes against that base (CI sets it for PRs/pushes). Do not use autofix or generator mutation in checks.

To update contracts deliberately, run `python -m scripts.contracts` then `node scripts/generate_types.mjs` and commit both outputs. Documentation checks use `python -m scripts.check_docs`; manually verify that named commands exist and claims distinguish target/implemented/live/native states. The checker validates tracked and non-ignored new Markdown paths/headings without fetching external links.

## CI and full release gates

Normal CI runs Q on Windows and Ubuntu with no live providers, source retrieval, database service or Docker requirement. The manual full-evals workflow currently runs the D lane on windows-2025 using its installed PostgreSQL 17 binaries in separate disposable clusters. It does not start or modify the runner's system database. Runner availability is checked explicitly; [the official image inventory](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md) is an input to that prerequisite, not installer qualification. No automatic API-key Codex review is enabled.

Full automated checks are necessary but insufficient for release. B/L/W, license/rights review, runtime isolation, signatures, migration/update/rollback interruption, and all SPEC workflows must also have dated passing evidence. Missing harnesses, toolchains, accounts or clean VM access keep the corresponding task/milestone incomplete. Extend the shared dispatcher/full-evals workflow only when real harnesses land, never with nonexistent placeholder commands.

Normal dependency installs may access package registries; product test data and outcomes remain deterministic. Package vulnerability checks are a separate changing supply-chain signal (`npm audit`), not live research. Dependency purpose/licenses/packaging are recorded in DECISIONS.

## Scenario coverage

Desktop scenarios use synthetic identities across stocks, ETFs, crypto, options, bonds and other assets. Verify ambiguity, source self-attestation rejection, wrong-asset claims, unsupported numeric claims, cache reuse, version preservation, cancellation, recovery without replay, local authentication, origin validation, credential filtering and hidden-reasoning exclusion. Frontend tests verify transport credentials and separation/escaping of unverified content. Extend scenarios rather than adding a production golden ticker list.

Keep existing citation, safety, source policy, glossary, weekly news and comparison regression checks while their algorithms migrate. Their fixture asset names do not define desktop coverage. Remove obsolete repository-layout assertions when replacing their actual behavior; retain safety tests.

## Local PostgreSQL check

Set `$env:LTT_PG_BIN = 'C:/Program Files/PostgreSQL/17/bin'` in PowerShell, then run `.venv/Scripts/python.exe scripts/smoke_local_service.py`. Use the actual binary directory on this machine; PostgreSQL 17 is the locally exercised major version. The script creates a new cluster under ignored `.local`, runs migrations and checks authenticated health, an empty library, idle Codex sign-in, term lookup and orderly shutdown. It does not touch an existing system service. Test database credentials are stored in the OS credential store; API credentials are generated in memory and sent over the parent pipe. Database smoke directories are disposable developer data, not library backups.

Run `.venv/Scripts/python.exe scripts/package_backend.py`, then the same smoke command with `--packaged` to exercise the generated Windows x64 executable. This is a sidecar test, not a Tauri/installer test. SQLite is a unit-test double only. PostgreSQL-specific migration, crash and concurrent-transaction behavior require separate PostgreSQL checks and future native CI coverage. A schema diff or successful `pg_restore --list` is not a restore test.

Run `.venv/Scripts/python.exe -m scripts.smoke_database` for actual PostgreSQL duplicate-library locking, failed-commit rollback, successful publication, recovery of a surviving private cluster and restart persistence. It creates a separate disposable library under `.local` and stops only that cluster. No live subscriptions are used. The ordinary unit suite also checks that a follow-up does not replace the asset overview and that conversation expiry preserves bookmarked conversations and saved evidence.

## Portable backup and restore

Run `.venv/Scripts/python.exe -m scripts.smoke_restore` to transfer a synthetic full library between two private PostgreSQL clusters. It verifies rollback after a failed write, saved-versus-current evidence versions, conversations/bookmarks, event sequence recovery, restart persistence, rejection of non-empty targets and interruption of restored pending runs. `tests/desktop/test_backup.py` also rejects malformed/truncated archives, unexpected files, changed checksums, unsupported versions, credential fields, duplicate records and missing references. No source archive is executed or extracted to arbitrary paths.

For the browser restore scenario, add `--restore-demo` to the preview command below. This writes `.local/restore-demo.lttbackup` from synthetic evidence and serves an empty in-memory test library. Restore it through Connections, inspect the library and validate a downloaded backup with `backend.app.backup.read_backup`. Use separate preview runs for restoration and term learning so initial state remains clear.

## Synthetic browser preview

In two repository-root terminals, run:

```powershell
.venv/Scripts/python.exe -m tests.desktop.preview_server --terms-demo --login-demo
```

```powershell
npm run dev
```

Open `http://127.0.0.1:1420`, expand **Developer browser connection**, enter endpoint `http://127.0.0.1:18764` and the public test-only credential `synthetic-preview-credential-not-for-production`, then connect. This fixed credential belongs only to the synthetic test service, never a real library. Authentication is held in memory; reconnect after a browser reload. The preview uses disposable in-memory SQLite, synthetic evidence and fake runtime responses; it does not contact providers. Stop both terminals after testing.

Check source links, original dates/permissions, missing evidence, separate notes, saved versions, cancellation and navigation. Inspect the normal window and the 640-pixel minimum width for readability and overflow. The native tray, window close/Quit and provider browser handoff need separate desktop tests.

## Codex connection checks

Run `.venv/Scripts/python.exe -m scripts.smoke_codex_protocol` explicitly to check the installed App Server's initialization and account-read protocol. It creates an isolated temporary profile and requires it to have no inherited authentication. It does not request a device code, log in or generate content. It also checks exact-version reporting and confirms that the protocol-only unauthenticated connection advertises no generation, browsing or approvals. This check is separate from CI; exact tested versions are recorded in [IMPLEMENTATION.md](docs/archive/2026-10-04/IMPLEMENTATION.md#verification-record-2026-10-03), not a supported-version promise.

`tests/desktop/test_codex.py` covers early stream notifications, malformed/flooded/timed-out responses, subscription-only authentication, login success/cancel/expiry/failure, mismatched flow IDs, untrusted verification URLs, API authentication and credential exclusion. `preview_server --login-demo` uses a synthetic TEST-ONLY device code without launching a provider; use it for the browser start/cancel check. Never enter that synthetic code on the real provider website. Actual sign-in and live research remain separate acceptance checks.

`tests/desktop/test_codex_messages.py` verifies commentary/final separation, authoritative completion text, legacy null/omitted phases, bounded correlated message lifecycles, cancellation and no answer publication before successful turn completion. Research and cached-only term scenarios must still validate completed JSON and exclude raw commentary/diagnostics from events and persistence. Include replay, missing completion, conflicting/unknown phases, oversized discarded commentary, provider failure and prohibited tools after an answer. These deterministic cases are in Q/R; live qualification must separately observe phase handling with the selected model before capability promotion.

## Term learning checks

`tests/desktop/test_terms.py` exercises version/language/level cache identity, no-inference lookup, shared queue and cancellation, automatic refresh, unadmitted citation rejection, conservative copied-number/advice checks, atomic publication and strict archive references. The PostgreSQL restore smoke also preserves terms attached to older evidence versions and their completed jobs across restart. The installed Codex protocol smoke initializes with browsing disabled; it still makes no inference request.

Run `.venv/Scripts/python.exe -m tests.desktop.preview_server --terms-demo` with the frontend development server for a synthetic UI check. Open its synthetic asset, try a curated term offline, enable the fake connection, generate a term in English or Traditional Chinese, inspect its source, then disable cloud research and reuse the cached explanation. Select a short phrase in the evidence to expose its explanation action. Hover/focus must only look up cached definitions. Verify citation back navigation and the 640-pixel layout. This fake runtime proves UI/protocol behavior, not explanation quality or provider support.

## Required before public v1

Separately invoke live subscription checks for Codex, Gemini and Claude; record exact versions, plan authorization, model/capability availability, cancellation, quotas, reconnect, source capture and permission isolation. No keys, passwords, raw private documents or reasoning traces belong in test records. Never run live checks in normal CI.

Exercise imports, structured API fallback, conflicts/restatements, numeric units and return calculations, Chinese number/citation preservation, sparse weekly context, scope/provider changes, offline views and saved comparisons. Exercise source injection, redirects/private network retrieval, unauthorized WebSocket access and imported document limits.

Build and run the Windows package on a clean VM without Python, Node, PostgreSQL or development tooling. Verify provider prerequisite onboarding, duplicate launches, occupied ports, tray/quit, locked libraries, interrupted migrations/updates, backup restoration and preservation of newer research during rollback. Record updater signatures separately from OS code-signing status. Collect baseline performance; no numeric thresholds have been approved yet.

Current results and unverified boundaries are maintained in [STATUS.md](STATUS.md). Passing the ordinary gate never implies release readiness.

## Runtime capability checks

Run `python -m pytest tests/desktop/test_runtime_policy.py tests/desktop/test_codex.py tests/desktop/test_terms.py -q` for exact prerelease/build versions, bounded/sanitized discovery, qualified-capability/authentication separation, unsupported execution rejection and cached-only browsing denial. Synthetic qualification injection in tests is not a production supported-version declaration. Current code-owned qualification records contain no live-enabled runtime.

Add `tests/desktop/test_codex_policy.py` for pre-launch custom configuration rejection, credential preservation, effective config/feature drift, permission/workspace mismatches, startup cleanup and no-inference thread checks. The explicit `python -m scripts.smoke_codex_protocol` now tests a fresh profile beneath a synthetic hostile parent config, effective configuration/features and actual thread creation without login or inference. It requires no inherited account and keeps all generation capabilities disabled. This does not qualify sandbox/tool enforcement during inference; perform that separately in M1-T05. Current process policy deliberately rejects custom system/profile/workspace files rather than merging them.

`tests/desktop/test_codex_models.py` covers bounded catalog pagination, text/hidden filtering, duplicate/default ambiguity, authentication, server-side model substitution, selected-request snapshots and settings races. The installed no-inference smoke also requires an empty authentication_required catalog for a fresh profile. The D restore lane preserves an explicit synthetic model across backup, restoration and restart with cloud consent off. For a model-picker browser check, add `--models-demo` to the synthetic preview: refresh models, observe the removed saved-model warning, select the alternate with keyboard controls, verify provider switching clears selection, and inspect normal/640-pixel views. Do not use these synthetic model identifiers in a real connection.

Model tests also require every model/rerouted notification to stop the active run before publishing candidate text, including after a completed answer has been buffered. Foreign/malformed routing metadata must not bypass rejection or leak raw fields; interrupt/close the owned turn without retry or selection changes. Ordinary safety-buffering telemetry alone is not a model switch. A synthetic app-service test verifies the failed job, unchanged selected-model snapshot/settings and absence of newly persisted research.

`tests/desktop/test_approvals.py` covers authenticated active-job review, foreign/replayed/malformed requests, prohibition of grants, bounded waiting/counts, consent revocation, cancellation, sanitized events and ephemeral state. Add `--approvals-demo` to the synthetic preview for browser checks: submit a new query, deny access and confirm completion; repeat and cancel; let a review expire; inspect keyboard use and normal/640-pixel layouts. This fixture has no provider connection. No positive access grant is supported by the current research policy.

`python -m pytest tests/desktop/test_owned_process.py tests/desktop/test_runtime_recovery.py -q` starts only synthetic Python children. Windows tests verify descendants exit on cleanup and owner crash, unrelated processes survive, and failed assignment never runs the suspended child. Additional cases cover foreign/old turns, exact RPC response IDs, pending-review disconnects, consumer failure/cancellation, explicit fresh reconnect and interrupted-job state reads without replay. These are included in Q on Windows; Windows-only job/crash tests are skipped explicitly on Ubuntu. Repeat D for native process changes and run the separate no-inference installed Codex smoke. A source-process test is not native packaged-host acceptance.

## Codex subscription qualification

Run Q first. `python -m scripts.qualify_codex` checks the installed exact version, dedicated subscription account, bounded model catalog, included-usage permission and isolated thread creation without a turn or sign-in request. Its default Windows profile matches the native app under LOCALAPPDATA/org.learntheticker.desktop/connections/codex. An explicit `--profile` must be app-owned and separate from the developer profile; never copy credentials or use the main CODEX_HOME.

If sign-in is required, stop for the user to complete Connections sign-in or run `python -m scripts.connect_codex` in an interactive terminal. The helper uses the same provider-managed flow, exact-version check and keyring profile without inference. Device codes are ephemeral user-interface values; never redirect them to reports/logs. Test helpers never run this sign-in in CI.

After authentication, `python -m scripts.qualify_codex --live [--model MODEL_ID]` explicitly runs bounded synthetic/public probes: preserved numbers/citation with browsing off, hosted search plus an official candidate URL, an unchanged synthetic canary outside the workspace, current-turn cancellation and a fresh explicit reconnect. It checks ordinaryUsageAllowed immediately before every turn, stops for unknown/exhausted included usage or errors, and uses no API/paid-credit fallback or permission grants. Reports include only fixed statuses/stages/failure categories, allowlisted item types/message phases/provider-error categories, normalized version/model, booleans and timestamps; no generated text, account identifiers, device codes or credentials. Unknown diagnostic values become fixed generic categories rather than exposing vendor content. Quota failures must stop even during a restriction probe. Normal CI tests only deterministic harness behavior in tests/desktop/test_codex_qualification.py.

Native Windows now also requires the explicitly selected elevated sandbox to report ready before preflight succeeds or a turn begins. `python -m scripts.setup_codex_sandbox` inspects this prerequisite without setup/inference. Its `--apply` option is a separate interactive administrator-approved action: provider-managed sandbox accounts, filesystem permissions and firewall changes; no project write roots, login, inference or weaker fallback. Never run --apply in CI. The provider-persisted config exception permits only the exact elevated mode in the dedicated profile; test extra settings, foreign layers, malformed/oversized config, non-ready states, setup failure/timeout and reconnect. The no-inference protocol smoke checks both browsing modes and this minimal config. Setup/readiness is not evidence of actual tool or sandbox enforcement.

After approved setup, run `python -m scripts.verify_codex_sandbox` explicitly on Windows to exercise the installed runtime's standalone command sandbox without a model turn. It first proves command execution and reads of synthetic control files, then requires actual UnauthorizedAccessException on inside/outside file writes with unchanged canaries. A disposable loopback listener must be reachable from the test host but unreachable from the sandbox; both the command marker and observed connection count must agree. Commands have deadlines and retain the provider's default output cap (the pinned Windows endpoint rejects custom caps); raw output/identifiers stay out of the report. This helper never enables model command tools, provisions the OS, signs in, or qualifies capabilities. Deterministic tests in tests/desktop/test_codex_sandbox_enforcement.py use a fake RPC/command executor and local disposable sockets only. An installed-runtime failure blocks L and must not be excused by a ready flag or unchanged canary from a model refusal.

For the native loopback repair, `python -m scripts.verify_codex_sandbox --extended` additionally requires IPv6 TCP and IPv4/IPv6 UDP denials, with a reachable ordinary-user control and no observed sandbox traffic for each listener. Missing IPv6 or a failed control is a blocker, never a skip/pass. UDP requires a bounded echo response; Windows IPv6 host controls use a complete four-part socket address. The explicit live harness repeats this extended enforcement check before requesting any turn, so a stale passing report cannot authorize a new live probe.

`python -m scripts.repair_codex_sandbox` reads the supplemental WFP objects from an elevated terminal. Explicit elevated interactive `--apply` / `--remove` install/remove only its validated objects in a transaction; default invocation never changes policy. Test missing/partial/foreign objects, idempotence, rollback on errors/readback failure, priority normalization, changed account/loopback/action scope and noninteractive denial in tests/desktop/test_codex_windows_filter.py. These deterministic tests use synthetic stores and never mutate Windows policy. Separate administrator-approved installed acceptance must cover installation, fresh-process readback, repeated application, removal, repeated removal and reinstallation, followed by actual normal-user enforcement probes. Record BFE's assigned priority without user SIDs or raw native/provider diagnostics. Reboot/BFE restart, policy drift recovery and packaged/clean-machine lifecycle remain native release checks. Preserve the original failure evidence and record the supplement's shared-offline-account scope; never disable global firewall policy or rewrite provider-owned rules to make a test pass.

Preflight success exits 0. Blockers or finished probes needing manual review exit 2. Review results before any qualification-registry change: a candidate URL is not admitted evidence, a refused canary prompt is not proof that a tool attempted/was sandboxed, and included-usage permission does not alone qualify subscription accounting. Confirm actual account usage, model identity, keyring persistence/reconnect, source capture, attempted scope restrictions and approval/cancellation behavior separately; record unknown or unexercised scenarios as blockers. No credentials, raw provider transcript or paid overage belongs in evidence. A live-compatible version cannot be enabled merely because this script finished.
