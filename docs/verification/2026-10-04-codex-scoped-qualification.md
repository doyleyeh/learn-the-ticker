# Scoped Codex qualification — 2026-10-04

Scope: M1-T05f and final M1 acceptance on native Windows, Codex 0.158.0-alpha.2.1, selected gpt-6-astra. The [direct inventory checkpoint](2026-10-04-codex-wire-inventory.md) is commit 870fb3c; its evidence and earlier checkpoints retain their original dates/results.

## Production boundary

The reviewed registry can enable generation, hosted browsing, normalized streaming, cancellation and deny/cancel approvals only after native executable identity verification and provider-managed ChatGPT authentication. Version detection alone still returns protocol_only. A fresh unauthenticated profile has no enabled capabilities even when the runtime has live qualification. The status message names the measured Windows/model scope.

Before every production turn, the real RPC checks the exact selected model, catalog content/integrity, native executable SHA-256, typed provider capabilities and both browsing-mode policy fingerprints against reviewed constants. Only the temporary catalog path is normalized in policy hashing. Another OS, launcher shim, same-version replacement executable, model/catalog/capability change or tool-policy edit stops before turn/start without retry or fallback. Ordinary included usage, account identity, effective configuration/features, single-workspace read-only sandbox and readiness checks remain mandatory. No scope/policy is learned from an answer or stored user preference.

The existing explicit developer harness still supports prequalification probes; its new --production option uses the unmodified CodexRuntime, including both production qualification guards. It requires --live and retains fresh actual sandbox enforcement before turns. Neither mode modifies qualification records. Production code never imports the developer probe helpers.

## Deterministic and installed verification

- Thirty-six new scope cases cover native file content/OS/shim/missing-file differences, authentication/identity combinations, both policy modes, model/catalog/file/policy/capability drift, strict Boolean types and actual production guard ordering before turn/start. Drift cases close the owned RPC. Synthetic transports and files only; CI never invokes installed providers.
- Three added helper cases verify production class selection, rejection of --production without --live and explicit CLI routing.
- Q passed **755 Python tests**, **seven frontend tests**, static evaluations, Ruff/ESLint, contract/document/whitespace checks, TypeScript and build. Existing Starlette/httpx deprecation remains.
- Installed no-inference smoke passed both browsing modes, hostile-parent isolation, minimal elevated config, no inherited authentication and no enabled unauthenticated capabilities. Its first run reached a stale protocol_only assertion after all isolation checks passed. The assertion now checks the expected identity-dependent qualification independently of authentication, and strengthens the disabled-capabilities check to include streaming/cancellation. The repaired complete smoke passed without sign-in, OS setup or inference.
- No database schema, native process implementation, frontend component, dependency, license or installer resource changed. Required D/native owned-process and B evidence below remains applicable and retains its original dates.

## M1 acceptance review

| Acceptance | Evidence and boundary |
| --- | --- |
| Installed/authenticated/qualified are distinct | Exact-version negative tests; native identity gating; unauthenticated installed smoke; API/external-token rejection. Successful sign-in alone cannot enable an unmeasured installation. |
| Unsupported versions/tools fail closed | Q/R adversarial policy/catalog/event suites; direct complete empty cached and two-tool research serialization; final scope drift tests. Model statements are not used for certification. |
| Allowed capabilities have deterministic and live evidence | Separate actual subscription denial/cancel, hosted source support and cached preservation; direct inventory measured without account traffic; production-path recheck below. |
| Explicit model and included usage | Catalog/selection/rerouting suites, exact production model/catalog guards and ordinaryUsageAllowed=true immediately before live turns. Unknown/false usage stops deterministically; no deliberate quota exhaustion or paid fallback. User's prior included-usage confirmation remains in the [live acceptance record](2026-10-04-codex-live-acceptance.md). |
| Consent, cancellation, disconnect and reconnect | Real permission cancellation, actual consent revocation/disconnect in a disposable app-service library, explicit fresh reconnect and persistent provider-managed keyring authentication across process restarts. No replay on state reads; [restricted-catalog lifecycle evidence](2026-10-04-codex-restricted-catalog.md). |
| Approval/UI boundary | [Browser denial, keyboard cancellation, expiry and 640-pixel checks](2026-10-04-access-review.md), plus real subscription permission requests. Grants remain forbidden; no new frontend behavior. |
| Models/citations/readability UI | [Model-picker and source/date/rights/missing-state browser evidence](2026-10-04-model-selection.md). No UI component/layout changes in this checkpoint. |
| No credential/reasoning leakage | Filtered child environments, keyring-only auth, bounded/sanitized transport, admission buffering, report allowlists and negative tests. Inventory retains only names/hashes; production uses no diagnostic proxy. |
| Process/database recovery | [Actual Windows owned-descendant/owner-crash and D restore evidence](2026-10-04-runtime-recovery.md), repeated D/restore in the restricted-catalog checkpoint. No native ownership/database changes here. |
| Actual sandbox enforcement | Approved scoped WFP supplement and subsequent real file-write/IPv4/IPv6 TCP/UDP denials with reachable host controls; repeated before each explicit live qualification. Readiness alone is not the enforcement evidence. |

Packaged-host, reboot/BFE restart, installer/update/rollback and clean-machine acceptance remain M9–M11. Gemini/Claude qualification remains M8. M1 does not claim whole-product or public release completion.

## Final production-path outcome

The explicit `python -m scripts.qualify_codex_tools --live --production --model gpt-6-astra` run began at **2026-10-04T03:49:30.920085+00:00**, after Q. It repeated actual extended sandbox enforcement and finished all four turns with production_path=true and probes_finished_review_required. Both real permission reviews passed deny/cancel, one turn each, empty responses, no pending review and complete owned-process/catalog cleanup. Hosted search and the independent Investor.gov quotation check passed with document SHA-256 91823047edeec76d24579121f19c4c1c8b884ab23514c1554f14c3d87e4dcdd5. Cached output preserved 100/[fixture-1] with no search. The normal runtime's exact identity/model/catalog/policy/capability and included-usage guards ran; no probe qualification bypass was used. The helper retains live_qualified=false/nonzero review-required semantics because it cannot certify itself or edit the registry.

The M1 acceptance review above is complete: no required M1 failure remains. M1-T05/M1-T05f and M1 are DONE within the scoped developer-runtime boundary. The prior inventory blocker is resolved; no further user sign-in, administrator setup or policy approval was needed. F was repeated after the smoke assertion/documentation updates; Q's production code was unchanged. The next dependency-unblocked milestone is M2, beginning with independent identity/source-rights registration. No claim is made that initial provider-generated research already meets M2 admission requirements.
