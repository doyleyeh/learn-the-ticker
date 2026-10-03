# Owned runtime lifecycle and recovery — 2026-10-04

Scope: M1-T04 source-runtime lifecycle. Windows public v1, packaged-host behavior and live subscriptions remain unqualified.

Implemented suspended Windows launch with Job Object assignment before execution, kill-on-close descendant ownership, no breakaway, and bounded shutdown. Provider discovery, status/login and streams use the shared launcher. Current-turn interruption precedes cleanup; malformed/foreign turn events fail closed. Consumers close async generators on validation failures. Pending reviews withdraw on process death, cancellation or consent revocation. Explicit reconnect starts a fresh ephemeral operation; startup/state reads never replay interrupted jobs. No database schema or dependency change.

## Evidence

- `python -m pytest tests/desktop/test_owned_process.py tests/desktop/test_runtime_recovery.py -q`: 15 passed on native Windows, including real synthetic descendants, early launcher exit, a separate surviving child, assignment failure before execution, owner crash, foreign turns, bool-vs-int RPC IDs, pending review disconnect, consumer cancellation/oversize, current-turn interrupt and explicit reconnect without replay. Windows-specific cases ran; none were skipped locally.
- Focused existing runtime/policy/model/approval/term suites: 147 passed after lifecycle integration.
- Shared PowerShell milestone gate passed: 406 Python tests, static evaluations, seven frontend tests, correctness lint, generated-contract drift, document links, whitespace, TypeScript and Vite production build. Existing Starlette/httpx warning remains.
- Database lane with local PostgreSQL 17 passed private service initialization/shutdown, lock/transaction/recovery/restart checks and actual archive restore with rollback-on-failure. Separate disposable clusters only; model persistence and consent reset still passed.
- Explicit installed Codex protocol smoke passed after final transport changes: effective isolated configuration/features, account-read, thread-start, exact version and unauthenticated model status. No login, inherited authentication or inference.

## Limits

The Windows APIs are lifecycle ownership, not an inference security sandbox. App Server tool/sandbox and billing behavior still need M1-T05 live evidence. POSIX process groups support deterministic CI; Windows kill-on-owner-crash evidence does not claim equivalent non-Windows release behavior. Native Tauri/installer tests remain blocked by absent cargo and unfinished release resources. The owned-process tests run synthetic Python helpers only, without installed providers or external calls.
