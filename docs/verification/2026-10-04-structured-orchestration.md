# Structured-first orchestration checkpoint — 2026-10-04

M2-T03a follows typed numeric admission at `718142b`. M2-T03/M2 remain incomplete pending structured event/news dates, source freshness and actual live search/read/follow-up acceptance. No new live qualification is claimed in this checkpoint.

## Behavior

After independent instrument resolution, ResearchService retrieves applicable SEC financial observations before inference. The independently resolved instrument is passed to the financial adapter without a duplicate instrument lookup; issuer resolution remains separate. Current unconflicted observations, original dates/units, issuer scope and explicit gaps become context. The result includes the validated financial document and application-owned citations, published atomically with the job/current snapshot. Refresh preserves previous immutable versions. Model numeric claims remain unverified notes without numeric values and cannot overwrite adapter citations.

Retrieval now runs outside the inference semaphore. Two worker-owned retrieval slots and one shared research/term inference slot enforce the configured concurrency. A cancelled caller signals its worker but cannot prematurely release the occupied slot; shutdown awaits owned workers. Consent is checked before/after retrieval, before inference and before publication. Manual review skips automatic financial retrieval and strips automatic admission if enabled during inference. Source failures report fixed availability notes without leaking errors or using model values as fallback. Offline cache behavior remains unchanged; online numeric reuse remains disabled pending proper refresh policy.

## Verification

- Existing application/identity/recovery/approval/admission/adapter suites: **160 passed**.
- New orchestration suite: **six passed**. It covers ordered context/publication, refresh preservation, portable restore, manual review before/during inference, source failure, two simultaneous retrievals, one inference, cancellation retaining its slot, and consent revocation before inference/publication.
- Q: **1,005 Python/seven frontend tests passed**, plus Ruff/ESLint, generated schema/type consistency, docs/whitespace, static evals, TypeScript and Vite build. Existing Starlette/httpx deprecation remains.
- D: private PostgreSQL startup/authentication, lock/recovery, atomic rollback/commit and actual full-library restore/restart passed. The new fixture runs the production ResearchService with explicit synthetic source/runtime adapters against the real database, then verifies its exact persisted job/snapshot after restore and restart alongside legacy evidence. Failure rollback and refusal to overwrite a non-empty destination remain passing. No provider/network fixture calls occurred.
- Review inspected scheduling ownership, cancellation, phase consent, manual-review transitions, source-ID handling and immutable atomic publication. No required check was weakened and no failed repair cycle occurred.

No new SQL/schema/archive format, dependency, source permission, provider qualification, native permission or UI component. No account/sign-in/billing changes, public exposure or remote Git actions. Earlier real SEC/FIGI checks and Codex runtime qualification retain their original dated scopes; they do not substitute for the pending complete live research check.
