# Native Codex loopback repair — 2026-10-04

Scope: repair the reproduced M1-T05 native Windows loopback failure at the user's request. The prior administrator-approved provider setup remains in place. Codex is still protocol-only; no live generation, new sign-in, billing, model substitution or production capability promotion occurred during this repair.

## Diagnosis and repair

The [original failure](2026-10-04-codex-sandbox-enforcement.md) remains historical evidence. Matching enabled Windows firewall rules and a ready sandbox did not prevent a real connection to a disposable localhost listener. Pinned provider source uses a shared local offline account; its ordinary loopback firewall rules differ from its WFP supplements for selected protocols/ports. A dynamic, automatically expiring WFP diagnostic added only offline-account loopback blocks. The unchanged original probe passed at 01:58:22 UTC; the dynamic session subsequently closed and removed its own objects.

The durable helper in scripts/repair_codex_sandbox.py uses the documented Windows filtering APIs through stdlib ctypes. It adds two persistent application-owned filters at IPv4/IPv6 ALE_AUTH_CONNECT and one dedicated sublayer. The conditions require the exact local CodexSandboxOffline descriptor AND IS_LOOPBACK, with BLOCK action. No credentials, user identifiers, provider binaries, SDK sources or raw diagnostics enter Git. No new dependency/driver. [DEC-017](../../DECISIONS.md#dec-017-supplement-native-offline-sandbox-loopback-restrictions) records scope and alternatives.

Install/remove require explicit elevated interactive commands; inspection is read-only and may also require elevation because Windows protects these policy objects. Ownership, metadata, persistence, account descriptor, conditions, action and priority range are checked within one transaction. Partial/conflicting objects are not replaced. The CLI cannot select arbitrary accounts, addresses or rules. Codex's offline account is shared across native profiles, including other profiles' local-binding exceptions; ordinary-user traffic, the online sandbox account and WSL are outside this rule scope.

## Repair checks and intermediate findings

- The first native ABI precheck caught an incorrect asserted pointer offset before any WFP operation; corrected to the Windows x64 SDK layout (200-byte filter; conditions pointer at offset 120). Local account resolution now uses the OS-reported computer name explicitly; the `.` shorthand was not accepted by LookupAccountNameW here.
- The first elevated apply could not discover Codex because the ordinary/elevated terminal PATH lacks the desktop runtime. It installed nothing. The next command supplied only the known runtime directory to that terminal's PATH; no persistent PATH/profile change.
- First persistent installation was atomically aborted on readback: BFE assigned sublayer priority 65532 instead of the requested 65535. A separate aborted diagnostic transaction verified that both filter definitions matched exactly. Microsoft's [installation guidance](https://learn.microsoft.com/en-us/windows/win32/fwp/installing-a-provider) documents nearest-available sublayer weights. The corrected validator requires the top 256 priority values; actual enforcement remains mandatory. No partial objects remained after either aborted transaction.
- At 02:07:30 UTC, elevated lifecycle checks passed install, idempotent install, remove, idempotent remove and reinstall, each checked through a new WFP connection. The final state retains the two persistent filters and dedicated sublayer. No provider-owned rule was removed or changed. Normal-user inspection correctly encountered Windows access denial; the CLI explains elevation instead of exposing raw diagnostics.
- First extended run passed file writes, IPv4/IPv6 TCP and IPv4 UDP, then exposed a test-host IPv6 UDP address-shape error before sandbox execution. Corrected the Windows proactor host control to send a four-part IPv6 socket address; a deterministic Windows regression test exercises that host socket path without a provider.

## Actual enforcement

`python -m scripts.verify_codex_sandbox --extended`, run as the ordinary user against Codex 0.158.0-alpha.2.1 at 02:09:27 UTC, exited 0:

| Check | Observation |
| --- | --- |
| Sandboxed command and synthetic file reads | Passed |
| Inside/outside workspace writes | Actual access denials; both canaries unchanged |
| IPv4 TCP | Host control reachable; sandbox reported blocked; listener observed no connection |
| IPv6 TCP | Host control reachable; sandbox reported blocked; listener observed no connection |
| IPv4 UDP | Host echo reachable; sandbox reported blocked; listener observed no datagram |
| IPv6 UDP | Host echo reachable; sandbox reported blocked; listener observed no datagram |

The original IPv4 TCP probe is preserved. The extended checks are additional requirements, and live qualification now repeats all of them before requesting inference. Result remains enforcement_probes_passed_review_required with generation_requested=false and live_qualified=false.

## Deterministic and database verification

Initial Q passed 487 Python tests. Final shared PowerShell milestone wrapper passed **495 Python tests**, seven frontend tests, static evaluations, lint, generated contracts, Markdown links, whitespace, TypeScript and production build. The existing Starlette/httpx deprecation warning remains. New tests never provision Windows or request provider inference.

The D lane passed isolated PostgreSQL service initialization/authentication/shutdown, lock/atomic publication/rollback/recovery/restart and actual full-library backup restoration into a separate private cluster. Nonempty restore rejection, saved versions, event recovery and consent reset passed. No system database or application library was modified, and no provider inference ran.

After final Q, the installed no-inference protocol smoke passed fresh unauthenticated profiles, both browsing configurations, strict minimal elevated settings and isolated thread creation. Dedicated authenticated preflight passed for the unchanged gpt-6-astra selection at 02:11:41 UTC, still generation_requested=false/live_qualified=false. A separate elevated inspection process at 02:11:54 UTC reported installed after all installer/diagnostic processes had exited; all three policy objects matched. No reboot or BFE restart was performed.

## Remaining boundaries

This resolves the observed developer-machine localhost enforcement failure. It does not qualify all model tools, source admission, subscription accounting, all three providers, arbitrary firewall configurations, reboot/BFE restart or installer/update/uninstall/rollback behavior. Persistent is the documented WFP object lifetime, not a claim that this machine was reboot-tested. Production generation remains disabled and M1-T05 stays incomplete pending account-side included-usage confirmation and remaining live/manual acceptance. Native packaging still lacks cargo/resources/clean-machine qualification. No remote Git action is authorized or performed.
