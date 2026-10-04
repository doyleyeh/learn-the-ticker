# Codex pending approval ordering — 2026-10-04

Scope: M1-T05c, an independently actionable adapter repair discovered during M1 live qualification review. This checkpoint uses synthetic protocol events; no new inference, sign-in, administrator setup or OS policy mutation.

## Defect and repair

The [official approval sequence](https://learn.chatgpt.com/docs/app-server#approvals) emits item/started for a pending command/file action before requesting approval. The prior adapter rejected that declaration, making the existing deny/cancel review unreachable for a complete real sequence. Adding the pending and declined items to the authenticated API test reproduced the defect before implementation: `python -m pytest tests/desktop/test_approvals.py -k authenticated_app -q -x --tb=short` failed because no review appeared.

The adapter now tracks at most three unique pending command/file items, correlates each request to the same kind/ID and existing thread/turn, and requires denial followed by a matching declined completion. Output/exit status, output/terminal notifications, executed/failed completions, replay and unresolved work stop publication. Cancel/expiry/revocation retain interruption/cleanup. No raw proposed path/diff/command/output is exposed; only item IDs and bounded lifecycle state are retained in memory. Cached-only operations still reject these items outright. Permission requests keep their existing empty turn-scoped responses.

This implements existing DEC-012 denial behavior; [DEC-019](../../DECISIONS.md#dec-019-recognize-pending-access-declarations-without-permitting-execution) records the distinction between pending declaration and authorization. Launch configuration and OS enforcement are unchanged. Event validation cannot independently establish sandbox enforcement or the complete model-facing inventory.

## Validation

Initial focused approval/runtime/message/recovery suites passed 117 cases. Review then added explicit execution-output/terminal-notification rejection and five regressions before the full gate. `powershell -ExecutionPolicy Bypass -File .codex/skills/project-delivery/scripts/verify-milestone.ps1` passed **600 Python tests**, seven frontend tests, Ruff/ESLint, non-writing generated contracts, local documentation/whitespace checks, static evaluations, TypeScript and production build. The only test warning is the existing Starlette/httpx deprecation. No failed repair attempts followed the reproduced regression.

The authenticated API tests exercise denial, cancellation and consent revocation with full pending/request/declined ordering; separate adapter tests cover expiry and both command/file kinds. Negative cases require no candidate answer, sanitized errors, no grants and owned-turn interruption/closure. Normal tests never call providers. No new dependency, contract, SQL, UI or native process implementation was introduced, so this checkpoint requires R/C/Q; previous D/native/browser evidence retains its dates and does not become a new packaged acceptance claim.

Complete implementation/test/documentation changes were reviewed for widened permissions, raw provider/source data, credentials, generated artifacts, unrelated edits and weakened checks. Only synthetic path/output markers appear in tests. The qualification registry and selected model are unchanged. Documentation checks are repeated after recording these final results, followed by staged diff/whitespace review before the local commit.

## Remaining qualification

The [eight earlier live turns](2026-10-04-codex-live-acceptance.md) are unchanged evidence. They did not request actual access review; this repair does not retroactively make that check pass. M1-T05 remains blocked on real denied-access behavior and complete model-facing tool inventory under the selected gpt-6-astra and exact installed Codex version. Production capabilities remain disabled; later milestones remain dependent on M1. Do not repeat the same refusal prompt, enable tools to manufacture a denial, switch models or weaken requirements.
