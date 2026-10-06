# Explicit saved-item deletion

Date: 2026-10-06 (Asia/Taipei). Scope: M9-T01c/P-043, with P-041 local transport protection. M9 and public Windows v1 remain incomplete.

## Result

Saved research now offers bookmark deletion; selected conversations, comparisons and historical reports offer their own deletion controls. Opening the disclosure does not mutate data. A separate confirmation names the item and explains that original evidence and independently saved items remain, including copies in prior exports/backups. Cancel restores keyboard focus. All four actions work offline.

The authenticated typed DELETE endpoint accepts only these four kinds and one bounded identifier. Missing items return an idempotent response. Assets, bundles, settings, credentials, retained imports and explanations cannot be deleted through this endpoint. Conversation deletion takes admission's row lock, refuses queued/running answers and deletes its transcript/jobs/events in one transaction. Original evidence is never cascaded away. The async API handler keeps this operation ordered with synchronous terminal publication on the service event loop. No SQL/archive revision, dependency, provider or source-policy change is involved; the response contract is generated from Pydantic.

## Verification and repairs

- **13 targeted backend tests passed**: authentication, offline use, each kind, idempotence, protected/unknown kinds, active refusal, late-failure rollback, unrelated-artifact preservation and archive round trips.
- Initial test fixtures passed dictionaries to a model-only comparison builder, then omitted the response's inherited `schema_version`. Both fixture expectations were corrected before targeted acceptance; production validation was not weakened.
- **Actual PostgreSQL deletion smoke passed**: queue-first admission blocks deletion; deletion-first rejects subsequent admission without an orphan job. A failure after event/job removal rolls everything back. A full backup restored into a separate private cluster retains every original evidence fingerprint and keeps all deleted artifacts absent after restart. Both clusters stop cleanly.
- **Full D passed**, including service lifecycle, retention races, rich financial/import/report restore and the 1,000-asset/24-attachment baseline. Its new scale output is `.local/library-scale-6ef951a84422/baseline.json`; original timing evidence remains unchanged.
- First B run found a real React regression: adjacent result views and new delete controls shared keys, causing duplicate conversation/comparison panels during navigation. Distinct delete-control keys fixed the cause; existing uniqueness assertions stayed unchanged. The new deletion test also captured its original page ID before navigation completed, selecting an empty comparison side. It now waits for observable routes/views and asserts the selection before submitting.
- **Final B: all six workflows passed**, no test retries. The new flow confirms/cancels using the keyboard, verifies exact selected DELETE requests, deletes all four kinds offline, reloads and reopens the original numerical evidence/source view without inference. Existing source-age, citation, missing-state, conversation, comparison and report checks also passed.
- Normal and 640-pixel confirmation screenshots were visually inspected: readable effects, wrapping without horizontal overflow and distinct Cancel/Delete controls. Screenshots: ignored `output/playwright/automated/research-explicit-offline--66ecb-e-and-requires-confirmation/delete-wide.png` and `delete-narrow.png`.
- **Final Q passed: 2,044 Python/94 frontend tests**, lint, generated contracts, static evaluations, TypeScript/build. F passed during implementation and after the final documentation update.

React review covered event-driven mutations, duplicate-submit prevention, distinct keys, generated types, accessible disclosures/status/error feedback, preserved source routes and refresh after deletion. No dependency or additional frontend storage was introduced.

Ignored logs: `.local/m9-deletion-targeted.log`, `.local/m9-deletion-d-targeted.log`, `.local/m9-deletion-d.log`, `.local/m9-deletion-b.log` (failed), `.local/m9-deletion-b-repair.log` (passed), `.local/m9-deletion-final-q.log`. Existing Starlette/httpx warning remains. B also logged a Windows Proactor connection-reset callback during reconnect coverage; all assertions passed and the owned preview listeners closed. This checkpoint does not claim to repair that diagnostic.

Fresh requirement review: this slice provides explicit deletion and preserves shared original evidence; it does not implement secure erasure, attachment/explanation deletion, automatic cache eviction, streamed archives or native installation. Those remaining M9 tasks and Gemini/Claude/clean-machine release gates prevent milestone/public-v1 completion.
