# Codex live acceptance continuation — 2026-10-04

Scope: M1-T05 on native Windows, exact Codex 0.158.0-alpha.2.1 and selected gpt-6-astra. On 2026-10-04 the user answered yes to confirmation that prior live checks used included subscription usage only, without paid credits or extra charges, and requested continuation. This records the user's confirmation, not an independent billing audit. Earlier evidence retains its original dates/results.

## Resumed checks

The unchanged application code at 853a2a0 had passed Q (546 Python/seven frontend, lint/contracts/docs/static/TypeScript/build). Dedicated no-inference preflight passed at 02:32:31 UTC. The explicit standard live harness began at 02:32:45 UTC and finished with probes_finished_review_required:

- Extended actual file-write and IPv4/IPv6 TCP/UDP restrictions passed before any inference. No administrator setup or filter mutation was requested.
- Cached output preserved synthetic 100 and [fixture-1], without tool activity.
- Hosted search emitted webSearch and returned a valid official Investor.gov candidate URL.
- Restriction canary stayed unchanged. Commentary and final_answer phases were observed and normalized successfully. No prohibited tool attempt/approval denial occurred; restricted_probe_stopped_by_adapter=false remains an unexercised check, not a pass.
- Current-turn interruption was acknowledged, owned provider process closed, and explicit fresh reconnect returned its marker.
- Every turn required fresh ordinaryUsageAllowed=true and the selected-model thread check. No automatic retry, model switch or API fallback was enabled. No provider error was reported.

## Additional acceptance helper

scripts/qualify_codex_acceptance.py adds three explicit guarded turns for independent source-quote retrieval, consent revocation via the authenticated app API, and disconnect of only the probe's owned provider process. Its disposable in-memory SQLite library cannot qualify PostgreSQL/native persistence. It retains only normalized statuses/booleans and a source document fingerprint, with no raw source/provider text or credentials. No dependency or production contract/policy change. All output still requires manual acceptance review; qualification records are never changed by the helper.

Focused tests initially passed 51 cases across the existing qualification and new acceptance suites. Review added whitespace-only quote rejection before the full gate. The shared PowerShell milestone wrapper then passed **569 Python tests**, seven frontend tests, Ruff/ESLint, generated contracts, documentation/whitespace checks, static evaluations, TypeScript and production build. The existing Starlette/httpx deprecation remains.

The additional explicit live run began at **02:38:34 UTC**, after that Q pass, and finished with probes_finished_review_required. All three turns used the unchanged exact runtime/model and the same included-usage/authentication/policy guards. Extended actual sandbox enforcement passed again before inference.

| Scenario | Actual observation |
| --- | --- |
| Independent source capture | webSearch observed; allowlisted HTTPS URL validated; a 20–200 character quotation matched independently downloaded visible text after whitespace/case normalization. Document SHA-256: 91823047edeec76d24579121f19c4c1c8b884ab23514c1554f14c3d87e4dcdd5. No quote/body/URL was retained in the report. |
| Message phases | The source turn contained commentary and final_answer; final JSON parsed successfully without progress-text contamination. |
| Consent revocation | Authenticated API disabled cloud consent; active job became cancelled; current-turn interruption acknowledged; owned process closed. |
| Provider disconnect | Only the probe's owned provider process was closed; the active job became failed and no research was published. |
| Persistence/replay boundary | Both lifecycle cases retained selected-model settings, had no pending access requests/raw message events/new asset or bundle, and made exactly one turn despite repeated job reads. |

Lifecycle checks used production service/API logic with a disposable in-memory SQLite library and real provider processes, not a packaged window or the user's PostgreSQL library. Earlier D/native evidence is neither replaced nor redated. This checkpoint changed only developer verification helpers/tests/docs; no production runtime, SQL, UI, tool permission or qualification registry changed. The complete diff was reviewed for secrets, raw provider/source output and unrelated files before a local commit.

## Remaining acceptance

Production capabilities remain disabled and M1-T05 is BLOCKED on **real denied-access behavior and a complete model-facing tool inventory**. The standard live restriction prompt refused the write without a file/command attempt or access request, so user denial/cancellation of a real pending review was not exercised. Synthetic review tests and actual standalone sandbox write/network denials do not substitute for that missing observation. Thread-start reported the requested model and the adapter rejects rerouting; no claim is made about unreported upstream identity.

Pinned source review shows tool construction can depend on model metadata, and ToolPolicy's allowed_tools ceiling is supplied internally through ExtensionDataInit rather than exposed in the reviewed App Server request schema. Disabled feature flags and the direct web namespace override therefore cannot alone certify the complete model-facing inventory. The existing adapter still rejects prohibited activity and grants no expanded permissions. Next action: identify a supported way to inspect that inventory and exercise a real denial under the unchanged selected model and restrictions. Do not repeat the identical refusal prompt, broaden tools to manufacture a pass, or promote the registry from completed positive probes. A needed runtime/model/security change requires explicit review/authorization under the existing decisions.

The user's prior usage confirmation is no longer a blocker. The new eight bounded turns checked ordinaryUsageAllowed=true; this is recorded permission, not an independent account invoice audit. No API fallback, overage enablement or administrator prompt occurred. Source capture is not independent asset identity or full M2 source/rights admission. Reboot/packaged/clean-machine acceptance and all three subscription providers remain required at their owning milestones; M2–M11 remain dependent on incomplete M1.

Follow-up review identified an actionable adapter ordering defect: the [official approval sequence](https://learn.chatgpt.com/docs/app-server#approvals) declares pending command/file work before its access request, but the current adapter stops at that declaration. The next independent M1 repair must recognize only bounded pending declarations, preserve deny/cancel-only replies and reject any executed or unreviewed completion. No permission configuration change is needed or authorized by this finding. This remains a separate implementation checkpoint; the live checks above did not exercise that sequence.
