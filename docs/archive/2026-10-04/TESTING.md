> Historical snapshot archived 2026-10-04. This document is no longer authoritative. See [the current source of truth](../../../EVALS.md) and [document ownership](../../../AGENTS.md). Original verification dates and claims below are preserved.

# Testing and release evidence

Run `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` on native Windows, or `bash scripts/run_quality_gate.sh` elsewhere. The gate runs Python scenarios, retained financial static evaluations, frontend tests, type checking and the Vite production build. It does not make live provider calls.

Install dependencies with the [README setup steps](../../../README.md#development-on-windows) first. The PowerShell gate prefers `.venv/Scripts/python.exe`; Bash uses `.venv/bin/python` when present, otherwise `PYTHON` or `python3`. These interpreter paths differ by platform. Hosted CI runs the gate on Windows and Ubuntu and separately regenerates/checks JSON Schema and TypeScript. It does not build Tauri, start PostgreSQL or qualify desktop platform support. The old automatic API-key PR-review workflow is removed; use [manual review guidance](../../../.github/codex/prompts/review.md) only when requested.

For contract changes run `.venv/Scripts/python.exe -m scripts.contracts` and `node scripts/generate_types.mjs`; commit both generated outputs with the model changes. The schema unit test checks against Pydantic and CI detects generated-file drift. For documentation changes check local links, named scripts/paths, target-versus-implemented claims and the quality gate. No new runtime dependency or mirrored-content test is needed for prose edits.

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

Run `.venv/Scripts/python.exe -m scripts.smoke_codex_protocol` explicitly to check the installed App Server's initialization and account-read protocol. It creates an isolated temporary profile and requires it to have no inherited authentication. It does not request a device code, log in or generate content. This check is separate from CI; exact tested versions are recorded in [IMPLEMENTATION.md](IMPLEMENTATION.md#verification-record-2026-10-03), not a supported-version promise.

`tests/desktop/test_codex.py` covers early stream notifications, malformed/flooded/timed-out responses, subscription-only authentication, login success/cancel/expiry/failure, mismatched flow IDs, untrusted verification URLs, API authentication and credential exclusion. `preview_server --login-demo` uses a synthetic TEST-ONLY device code without launching a provider; use it for the browser start/cancel check. Never enter that synthetic code on the real provider website. Actual sign-in and live research remain separate acceptance checks.

## Term learning checks

`tests/desktop/test_terms.py` exercises version/language/level cache identity, no-inference lookup, shared queue and cancellation, automatic refresh, unadmitted citation rejection, conservative copied-number/advice checks, atomic publication and strict archive references. The PostgreSQL restore smoke also preserves terms attached to older evidence versions and their completed jobs across restart. The installed Codex protocol smoke initializes with browsing disabled; it still makes no inference request.

Run `.venv/Scripts/python.exe -m tests.desktop.preview_server --terms-demo` with the frontend development server for a synthetic UI check. Open its synthetic asset, try a curated term offline, enable the fake connection, generate a term in English or Traditional Chinese, inspect its source, then disable cloud research and reuse the cached explanation. Select a short phrase in the evidence to expose its explanation action. Hover/focus must only look up cached definitions. Verify citation back navigation and the 640-pixel layout. This fake runtime proves UI/protocol behavior, not explanation quality or provider support.

## Required before public v1

Separately invoke live subscription checks for Codex, Gemini and Claude; record exact versions, plan authorization, model/capability availability, cancellation, quotas, reconnect, source capture and permission isolation. No keys, passwords, raw private documents or reasoning traces belong in test records. Never run live checks in normal CI.

Exercise imports, structured API fallback, conflicts/restatements, numeric units and return calculations, Chinese number/citation preservation, sparse weekly context, scope/provider changes, offline views and saved comparisons. Exercise source injection, redirects/private network retrieval, unauthorized WebSocket access and imported document limits.

Build and run the Windows package on a clean VM without Python, Node, PostgreSQL or development tooling. Verify provider prerequisite onboarding, duplicate launches, occupied ports, tray/quit, locked libraries, interrupted migrations/updates, backup restoration and preservation of newer research during rollback. Record updater signatures separately from OS code-signing status. Collect baseline performance; no numeric thresholds have been approved yet.

Current results and unverified boundaries are maintained in [IMPLEMENTATION.md](IMPLEMENTATION.md). Passing the ordinary gate never implies release readiness.
