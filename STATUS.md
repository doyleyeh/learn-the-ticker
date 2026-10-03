# Delivery status

Updated: 2026-10-04. Public Windows v1 is **not ready**.

- Current milestone: M0 — verified foundation checkpoint; next is M1.
- Current task: M0-T04 — checkpoint records the reviewed foundation; next task M1-T01.
- Completed milestones: M0 (this foundation checkpoint). Prior application slices remain partial against M1–M11.
- Latest verification: [foundation evidence](docs/verification/2026-10-04-foundation.md): 285 Python tests, static evaluations, seven frontend tests, correctness lint, non-writing schema checks, type/build, links, wrapper behavior and actual isolated PostgreSQL lifecycle/restore passed.
- Known warning: existing Starlette/httpx test-client deprecation.
- Known release blockers: no live provider acceptance; Gemini disabled; Claude experimental; cargo absent; native/clean-machine installer/update/rollback unqualified. Full wrapper reports missing cargo without skipping.
- Next action: mark M1-T01 IN_PROGRESS, inspect runtime discovery/transport/tests, implement truthful fail-closed capability reporting and validate.
- Continuation notes: use codex/project-delivery-foundation. Original empty read-only .codex file is preserved in ignored .local/codex-placeholder-2026-10-04. No remote Git action, provider sign-in/inference or application-library mutation occurred in M0; database tests used separate disposable clusters.
- Authorization: normal implementation and verified local commits; official/free sources first; explicit authenticated-subscription checks after deterministic validation. Pause for sign-in, quotas or extra charges. PR/push/merge/publishing require separate authorization.

## Evidence

Historical results keep their original dates: [2026-10-03 preview checks](docs/archive/2026-10-04/IMPLEMENTATION.md#verification-record-2026-10-03), [prior documentation audit](docs/archive/2026-10-04/IMPLEMENTATION.md#documentation-audit-2026-10-04). New results are in [foundation verification](docs/verification/2026-10-04-foundation.md). [TASKS](TASKS.md) owns actions; [EVALS](EVALS.md) commands and release requirements.
