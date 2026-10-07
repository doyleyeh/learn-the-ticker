# Dedicated sign-in and partial live Codex checks — 2026-10-04

Scope: M1-T05 on native Windows, Codex 0.158.0-alpha.2.1 and explicitly selected gpt-6-astra. Dedicated ChatGPT sign-in succeeded. M1 and production capabilities remain unqualified. Prior [preflight](2026-10-04-live-preflight.md) and [resume](2026-10-04-delivery-resume.md) records retain their original results.

## Sign-in and actual observations

The ordinary Windows PATH had no Codex runtime; this agent's PATH supplied the reviewed bundled runtime. The helper previously described both missing runtime and unsupported version as the same error. It now distinguishes missing/unstartable, unverifiable and unreviewed versions. Sign-in ran in an interactive PowerShell window; the user enabled device authorization and completed the restarted flow. No device code, credential or auth file was captured/copied into project evidence.

The authenticated no-inference preflight at `2026-10-04T00:31:40.970333+00:00` passed subscription-account, model-catalog, included-usage and isolated-thread checks. This was before the newly added native sandbox readiness gate; it does not certify sandbox enforcement.

| Live run start (UTC) | Result | Interpretation |
| --- | --- | --- |
| 00:32:13.089030 | Blocked after cached-number/citation check | Original report lacked a specific failure stage; no retry inside the harness |
| 00:36:04.486010 | Cached check passed; source check failed | Bounded observations showed no webSearch event, completed turns and no provider-error category |
| 00:42:52.910587 | Probes finished; manual review required | After direct-web configuration repair, search, cancellation and reconnect observations passed; restriction enforcement remained unexercised |

All live turns checked ordinaryUsageAllowed=true. No API billing, paid-credit fallback, permission grant, automatic retry or model/provider switch was enabled. Actual account-side usage confirmation remains pending; the Boolean permission is not a complete billing audit.

Final live observations:

- Cached output preserved the synthetic 100 and [fixture-1], with no tool progress.
- Source output provided a parseable HTTPS www.investor.gov candidate URL, without credentials/query, and a webSearch event. No content was admitted to the library; candidate discovery is not claim-support/rights verification.
- The synthetic outside-workspace canary remained unchanged. No command/file tool or approval request was observed, so the adapter did not exercise a denial and this is **not** sandbox acceptance.
- Current-turn interrupt was acknowledged and the owned process reference was closed; fresh explicit reconnect returned its expected marker. This supplements, not replaces, earlier Windows process-tree evidence.
- Recorded metadata consisted only of allowlisted event/phase/error categories and booleans. No hidden reasoning text, message text, account IDs, device codes, raw errors or tool arguments were retained in the report.

## Diagnosis and repair

The pinned model metadata selected code_mode_only. The pinned runtime prioritizes that over the disabled code-mode feature flags and hides web tools inside code mode. DEC-015 exposes the existing permitted web namespace directly while keeping the code-mode execution service disabled. In this version disable_in_process_fallback=true would select a process-owned host, so the app explicitly requires false. Deterministic adversarial policy tests and installed no-inference checks passed before the third live run; that run observed working search. Repair history: one diagnostic refinement, then one configuration repair; no repeated live failure remained at that source stage.

A separate no-inference readiness check then returned notConfigured with no explicit Windows mode. Selecting elevated mode only for inspection returned updateRequired. The thread's readOnly response therefore was insufficient native enforcement evidence. DEC-016 adds an elevated-mode/readiness gate before further inference, including script-only probes. No more live calls were made after this finding.

The new setup helper defaults to inspection. Its real inspection confirmed setup is required without changing the OS. Explicit --apply is prepared for a user-approved interactive provider setup. It requests no project write roots, sign-in or generation, and refuses weaker fallback. Pinned source shows setup persists its elevated-mode config; only that exact minimal profile setting and matching user layer are now accepted. Extra configuration stays blocked and is preserved.

## Verification

- Focused policy, qualification and setup tests: 92 passed before the final shared gate.
- `python -m scripts.smoke_codex_protocol`: passed against the installed exact version with browsing disabled and enabled, hostile parent config, no inherited account, and the minimal provider-persisted elevated config. No OS setup/inference was requested.
- `python -m scripts.setup_codex_sandbox`: correctly stopped at missing dedicated elevated setup; no --apply run occurred.
- Final no-inference preflight at `2026-10-04T00:50:31.375759+00:00` retained the authenticated version/model and correctly stopped with windows_sandbox_setup_required, generation_requested=false and live_qualified=false.
- Final `python -m scripts.verify milestone`: **457 Python tests**, seven frontend tests, static evaluations, Ruff/ESLint, contracts, local docs/whitespace, TypeScript and Vite build passed. The existing Starlette/httpx deprecation warning remains. Earlier Q gates in this session passed with 429 then 433 Python tests before subsequent safeguards were added.
- Database/native process implementation, frontend behavior, SQL/contracts and dependencies were not changed; their prior dated evidence remains separate. Native/full acceptance still has the previously recorded missing-cargo blocker.

## Remaining acceptance and next action

M1-T05 is BLOCKED on administrator-approved dedicated Windows sandbox provisioning and account-side usage confirmation. The prepared command is `.venv/Scripts/python.exe -m scripts.setup_codex_sandbox --apply`, run interactively only after approval of its local accounts/filesystem/firewall changes. This is a system security change under AGENTS; the helper does not run it implicitly during sign-in, inspection or tests.

After setup: require fresh readiness/config checks, exercise actual synthetic filesystem/network restriction attempts and denied access, review source capture/model/subscription accounting, and repeat required live failure/cancellation/reconnect acceptance. A readiness flag, unchanged canary without a tool attempt, or successful helper is never sufficient to update the qualification registry. M2–M11 remain dependent on incomplete M1. No provider secrets/config logs, new packages or public/remote Git actions belong to this checkpoint.
