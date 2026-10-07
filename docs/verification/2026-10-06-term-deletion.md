# Cached term and page-question deletion

Date: 2026-10-06 (Asia/Taipei). Scope: M9-T01f/P-022/P-025/P-043. M9 and public Windows v1 remain incomplete.

## Behavior

The saved interpretation in Understand this page now offers confirmation/cancel before deleting that term or question scope. Deletion removes the interpretation and its matching job/event history while preserving the original evidence, other modes/languages/reader levels/versions and curated definitions. Effects disclose that unreferenced pages can later be removed by cache cleanup. It works offline, is authenticated/idempotent and refuses active matching jobs.

Term deletion takes DEC-059's exclusive library gate before its record lock. Job matching uses the original canonical key in Python, including Unicode casefold, rather than SQL lowercasing. Malformed stored job/scope validation returns fixed errors without raw input. Deletion commits atomically. Frontend selected and hover caches clear together; a revision check rejects delayed hover responses after deletion. No dependency, SQL/archive revision, provider or source-permission change.

## Verification

- **38 targeted tests passed**, including six new term-deletion cases and all affected saved-item/term regressions. Covered both modes, other language/reader-level preservation, original bundles, authenticated offline/idempotent use, active refusal, `Revenue`/`REVENUE` and `Straße`/`STRASSE` job equivalence, late rollback, malformed-job diagnostic suppression and actual bounded archive round trips.
- **Actual PostgreSQL targeted deletion smoke passed**. Admission first can reuse the existing interpretation before deletion; deletion first removes the old result and permits a distinct subsequent explicit request against the still-existing original. Late failure restores interpretation/jobs/events. Deleted scopes stay absent and the other language/reader level remains exact after separate-cluster restore/restart. Earlier conversation/import deletion checks remain included.
- F passed during implementation and after the final documentation update. **Q passed: 2,073 Python/94 frontend**, lint, generated contracts, static evaluations, TypeScript/build. **Full D passed**, including earlier lifecycle/retention/rich restore, scale, all deletion races and protected cache checks. New scale output: `.local/library-scale-3c38025fce50/baseline.json`; original baselines remain unchanged.
- First B passed the eight existing workflows. The new workflow successfully deleted the interpretation and returned the curated fallback, but expected an uppercase `Revenue` heading; the actual curated glossary uses lowercase `revenue`. The test now matches that observed heading; production behavior was unchanged by this repair. **Final B: all nine workflows passed**, no retries (52.2 s), including keyboard confirmation/cancel, both deletion modes offline, cleared hover/selected interpretations, preserved reader-level scope/curated fallback, reload and original number without inference/external requests/page errors.
- Normal and 640-pixel confirmation screenshots were visually inspected: readable scope/effect text with wrapping and distinct Cancel/Delete controls. Ignored paths: `output/playwright/automated/research-offline-term-and--86328-ile-preserving-other-scopes/delete-term-wide.png` and `delete-question-narrow.png`.

React review covered distinct deletion keys, mutations only on confirmation, functional cache filtering by immutable interpretation ID, invalidation of pending hover revisions, clearing selected job state and retained curated definitions. Existing shared duplicate-submit/cancel/focus/error behavior is reused. Starlette/httpx and browser color-environment warnings remain.

Ignored logs: `.local/m9-term-deletion-targeted.log`, `m9-term-deletion-final-targeted.log`, `m9-term-deletion-f.log`, `m9-term-deletion-d-targeted.log`, `m9-term-deletion-d.log`, `m9-term-deletion-b.log` (fixture heading failure), `m9-term-deletion-b-repair.log`.

Fresh requirement review: explicit deletion now covers saved learning interpretations as well as the earlier artifact/document controls. Larger streamed archives and remaining native/live-provider/release gates still prevent M9/public-v1 completion. Existing archive/parser limits remain unchanged.
