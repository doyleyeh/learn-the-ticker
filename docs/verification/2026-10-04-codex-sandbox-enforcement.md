# Approved Windows sandbox setup and enforcement checks — 2026-10-04

Scope: M1-T05, native Windows, Codex 0.158.0-alpha.2.1. The user explicitly approved the prepared elevated sandbox setup. **Setup succeeded; complete isolation qualification did not.** M1 remains blocked and production generation remains disabled. This record follows [authenticated probe evidence](2026-10-04-authenticated-codex.md) without rewriting its historical results.

## Actual setup and preflight

`python -m scripts.setup_codex_sandbox --apply` ran once in a visible interactive PowerShell window, using the dedicated app profile and provider-managed elevated setup. It completed with exit code 0 at `2026-10-04T01:34:49.9381996Z`, including a fresh connection/config/readiness check. Subsequent inspection independently reported ready. No weaker-mode fallback, developer-profile auth copy, external sign-in or inference was requested.

`python -m scripts.qualify_codex --model gpt-6-astra` passed at `2026-10-04T01:35:23.139356+00:00`: exact version, dedicated subscription, selected model, included-usage permission, isolated thread and elevated readiness. The report retained generation_requested=false and live_qualified=false.

## Actual native enforcement

The new explicit `python -m scripts.verify_codex_sandbox` helper calls the installed runtime's standalone command endpoint under readOnly/networkAccess=false. This is a test-driver capability, never an added model tool. It uses PowerShell from Windows, synthetic temporary files, a disposable loopback TCP listener, command/request deadlines and bounded transport. It does not request model generation, retrieval, sign-in, OS setup or a permission grant; it stores no raw command output or account identifiers.

The first attempt at `01:36:30.066400Z` stopped before the control command because this pinned Windows endpoint rejects custom outputBytesCap. A diagnostic confirmed a sandbox-related invalid request. The pinned [command implementation](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/app-server/src/command_exec.rs) requires its default output cap. The helper was repaired to retain that default and its independent transport bound; deadlines and sandbox policy were unchanged.

The repaired attempt at `01:37:22.210042Z` passed command/read controls and both write denials, then failed network enforcement. A diagnostic repeat at `01:38:47.858003Z` confirmed:

| Check | Actual result |
| --- | --- |
| Sandboxed command and both synthetic canary reads | Passed |
| Write inside read-only workspace | UnauthorizedAccessException; canary unchanged |
| Write outside workspace | UnauthorizedAccessException; canary unchanged |
| Host connection to disposable listener | Passed control |
| Sandboxed connection to same loopback listener | **Connected; failed restriction** |
| Listener independently observed sandbox connection | Yes |

Read-only Windows inspection found Domain/Private/Public firewall profiles enabled and Codex offline inbound/outbound/loopback TCP/UDP block rules enabled. A separate bounded identity check compared the sandbox process account to the loopback rule's user filter in memory and reported a match. Identifiers were not retained. An existing Codex outbound allow rule was observed but was not altered; this alone does not establish the cause of the failure. The pinned [firewall provisioning code](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/windows-sandbox-rs/src/setup_provisioning/firewall.rs) contains loopback block rules; their existence is insufficient actual enforcement evidence.

Diagnosis: approved provisioning/readiness and read-only filesystem behavior work. Native loopback isolation is incompatible with the required network-disabled behavior on this installed runtime/host. The underlying Windows/provider mechanism has not been proven to be the root cause; do not claim a specific vendor bug or fix it by disabling firewall rules. No outbound public-network test was needed to establish this failed local restriction. No subscription-generation probes were run after setup.

## Deterministic verification and remaining work

Eight tests verify the harness's argument-vector encoding, unchanged readOnly/networkAccess=false policy, deadlines/default output cap, failed controls/write attempts, cleanup and the requirement that both the command and independent listener agree on network denial. A false denial marker cannot pass when a connection reached the listener. Tests use fake RPC/command execution and disposable local sockets, not a live provider.

Final `python -m scripts.verify milestone`: **465 Python tests**, seven frontend tests, static evaluations, Ruff/ESLint, contracts/docs/whitespace, TypeScript and Vite build passed. The existing Starlette/httpx warning remains. This gate validates the implementation; it cannot convert the failed installed-runtime check into a pass. Existing native packaging/full acceptance remains blocked by the previously recorded missing cargo prerequisite; no SQL, database/native lifecycle, frontend, contracts or dependencies changed here.

Next: review a supported runtime/Windows mechanism that actually enforces the required network boundary, or qualify a vendor/runtime fix. Preserve the failing probe and existing host firewall configuration. No third repair was attempted against the network failure: one repeat and a read-only identity/rule diagnosis established the current blocker. Account-side subscription usage confirmation and remaining live source/approval/failure acceptance are also incomplete. No production qualification-registry change, push, PR, merge or publication occurred. M2–M11 remain dependent on incomplete M1.
