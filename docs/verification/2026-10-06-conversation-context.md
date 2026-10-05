# Conversation page-version selection

Date: 2026-10-06 (Asia/Taipei). M5-T01b and final M5-T01 acceptance; M5 itself remains incomplete pending T02. Implements DEC-051 within P-014/P-023/P-024. No source-policy expansion, live request, dependency addition or public release.

## Behavior and review

New conversations retain the exact immutable page opened by the user, including older saved reports. Omitted creation fields capture the current page once. Refresh leaves existing selections unchanged. Explicit current-page selection or a resolved asset change appends a context boundary with the selected version. Original selections and responses stay accessible. Queuing snapshots the selection under the same conversation lock as updates; active answers reject scope/evidence changes, and completion checks the selection again.

The selected page is hydrated first within the existing five-version/400,000-character budget. It goes through the original-context identity, rights, source-alias and numerical-review path, retaining original dates and units. Earlier unverified prose is excluded, fresh retrieval is separate, and new quotations require independent source validation. The production-path tests check that the latest page's different facts never silently replace the selected page, including denied/unavailable source verification. Legacy conversations do not receive an invented original version; their cited answers remain reusable and users can select a page explicitly.

Additive optional fields on conversations, scope messages and research requests require no SQL/archive-format change. Archive checks reject missing/wrong-asset selected versions and preserve historical choices. Older binaries remain unqualified rollback targets. The updated test fixture now stores a real immutable bundle when selecting its second asset; no production validation was weakened to accommodate incomplete fixtures.

## Verification

| Check | Result |
| --- | --- |
| Targeted context/reuse/storage/backup | 56 passed; `.local/m5-context-targeted.log` |
| Q, including C/R, lint/docs/static/TypeScript/build | 1,859 Python and 87 frontend tests passed; `.local/m5-context-q.log` |
| D | Private service, PostgreSQL locks/transactions, atomic full restore and restart passed; `.local/m5-context-d.log` |
| Extended actual restore after adding pending-job context | Passed; `.local/m5-context-restore-final.log`. Original/newer selections and pending request survive; restored job is interrupted, current asset stays newer |
| B | Three workflows passed; `.local/m5-context-b.log`. Original-page creation after refresh, reload/provider/scope preservation, explicit new selection, next request's exact version, unchanged answer/report links, no external requests or page errors |
| Visual review | Inspected `conversation-original-context-narrow.png` and `conversation-selected-context-wide.png` under ignored `output/playwright/automated/research-conversation-scop-05c84-riginal-response-navigation`; readable normal/640-pixel layouts |
| Final F | Passed; `.local/m5-context-f-final.log` |

No gate failed in this checkpoint. Full-diff review covered contracts/generated output, application context, archive validation, scope locking, UI navigation, synthetic fixtures and documentation ownership. No raw provider data or credentials are added. Existing Starlette/httpx and test-runner color warnings remain non-failing.

## Remaining acceptance

M5-T01a's navigation/provider/refresh evidence plus this context acceptance complete M5-T01. M5-T02 still needs bilingual beginner/intermediate live learning/conversation and permitted-export qualification. No native binaries were rebuilt; existing packaged artifacts predate this context contract and the M5 UI. No Gemini/Claude, installer or public-release qualification is implied.
