# Codex qualification harness and blocked preflight — 2026-10-04

Scope: implemented M1-T05 harness and included-usage guard. M1-T05 and M1 remain **BLOCKED**, not accepted. No live generation or sign-in was requested in this run.

## Implemented and verified

- A no-inference preflight checks exact version, isolated configuration, dedicated subscription authentication, catalog/model, included-usage permission and thread creation in sequence. It stops at the first unmet prerequisite.
- The explicit --live harness is ready for synthetic/public prompts, candidate source capture, a synthetic restriction canary, cancellation and explicit reconnect. It does not alter the production qualification registry; observations still require manual acceptance. These live paths have deterministic tests only, not a completed live run.
- Every Codex turn now requires ordinaryUsageAllowed=true from account/rateLimits/read. Missing/unknown/false stops even when credit balances or percentages look usable. No paid fallback or automatic retry.
- Interactive terminal sign-in reuses CodexLogin and the same native-app profile when Rust/native UI is unavailable. The helper refuses redirected input/output; durable tokens remain provider-managed in the OS credential store. Main developer profiles and their subdirectories are rejected. This helper has not yet been used for real authorization.
- `tests/desktop/test_codex_qualification.py`: 16 deterministic cases passed, covering explicit included usage, preflight auth/quota blocks with no turn/sign-in, exact version changes, output-bound cleanup, quota errors during restriction probes, protected developer profiles and redirected-code rejection.
- Final shared PowerShell milestone gate: **422 Python tests**, static evaluations, seven frontend tests, Ruff/ESLint, contract drift, links, whitespace, TypeScript and Vite build passed. Existing Starlette/httpx warning remains.

## Observed blockers

The explicit native Windows preflight at `2026-10-03T17:41:35.712718+00:00` (2026-10-04 in Asia/Taipei) reported:

```json
{
  "status": "blocked",
  "live_qualified": false,
  "generation_requested": false,
  "version": "0.158.0-alpha.2.1",
  "model": null,
  "blocker": "dedicated_subscription_sign_in"
}
```

The full dispatcher separately stopped with `BLOCKED: Missing cargo; follow README setup and EVALS prerequisites.` No native/installer/release checks were counted as passed. Prior actual database/restore and Windows source-process evidence remains in [runtime recovery](2026-10-04-runtime-recovery.md); browser evidence remains in its dated records.

## Next action

The user must complete dedicated sign-in via Connections or `.venv/Scripts/python.exe -m scripts.connect_codex` in an interactive terminal. This pause follows the user's explicit instruction to stop for sign-in, quota or charges. Then rerun preflight and the explicit live probes under [EVALS](../../EVALS.md#codex-subscription-qualification), resolve all unexercised acceptance scenarios and review billing/tool/source evidence before enabling any production capability. Do not proceed to M2–M11 past the incomplete M1 dependency. Native toolchain/resources and clean-machine release acceptance remain outstanding independently.
