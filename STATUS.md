# Delivery status

Updated: 2026-10-04. Public Windows v1 is **not ready**.

- Current milestone: M1 — Codex runtime qualification.
- Current task: M1-T05 **BLOCKED on dedicated ChatGPT sign-in**. Harness/preflight and included-usage guard are implemented; actual live acceptance has not run. M1-T04 committed as 4e7263b; M1-T03b as ccff14e; M1-T03a as 456412b; M1-T02 as 2cf7208; M1-T01 as 70cdaa8.
- Completed milestones: M0 (commit 2ea989e). Prior application slices remain partial against M1–M11.
- Latest verification: [qualification preflight evidence](docs/verification/2026-10-04-live-preflight.md): milestone gate passed 422 Python tests, static evaluations, seven frontend tests, lint/schema/links/type/build. Actual no-inference preflight stopped at missing dedicated sign-in. The full dispatcher stopped at missing cargo. Prior real Windows process, PostgreSQL/restore and browser evidence retains its own records.
- Known warning: existing Starlette/httpx test-client deprecation.
- Known release blockers: no live-qualified provider version; production inference fails closed while cached/synthetic features remain usable; cargo absent; native/clean-machine installer/update/rollback unqualified. Full wrapper reports missing cargo without skipping.
- Next action: user completes Connections sign-in or runs `.venv/Scripts/python.exe -m scripts.connect_codex` interactively; rerun `python -m scripts.qualify_codex`, then explicit --live probes and manual acceptance. Stop on quota/charges/unknown included usage. M2–M11 remain TODO behind incomplete M1; do not treat the harness as live qualification.
- Continuation notes: use codex/project-delivery-foundation. Original empty read-only .codex file is preserved in ignored .local/codex-placeholder-2026-10-04. No remote Git action, provider sign-in/inference or application-library mutation occurred in M0; database tests used separate disposable clusters.
- Authorization: normal implementation and verified local commits; official/free sources first; explicit authenticated-subscription checks after deterministic validation. Pause for sign-in, quotas or extra charges. PR/push/merge/publishing require separate authorization.

## Evidence

Historical results keep their original dates: [2026-10-03 preview checks](docs/archive/2026-10-04/IMPLEMENTATION.md#verification-record-2026-10-03), [prior documentation audit](docs/archive/2026-10-04/IMPLEMENTATION.md#documentation-audit-2026-10-04). New results are in [foundation verification](docs/verification/2026-10-04-foundation.md). [TASKS](TASKS.md) owns actions; [EVALS](EVALS.md) commands and release requirements.

M1-T01 evidence: [runtime capabilities](docs/verification/2026-10-04-runtime-capabilities.md). M1 remains incomplete.

M1-T02 evidence: [configuration and thread isolation](docs/verification/2026-10-04-codex-isolation.md). Custom system/profile/workspace configuration and file credentials currently stop the isolated connection; no files are imported or removed.

M1-T03a evidence: [model catalogs and selection](docs/verification/2026-10-04-model-selection.md). Authenticated model entitlement and approval interactions remain unqualified.

M1-T03b evidence: [bounded access review](docs/verification/2026-10-04-access-review.md). Deny/cancel are supported within the current policy; command/file/network grants cannot be approved.

M1-T04 evidence: [owned process lifecycle and session recovery](docs/verification/2026-10-04-runtime-recovery.md). Native packaged-host and live-provider qualification remain separate.

M1-T05 partial evidence: [harness and blocked live preflight](docs/verification/2026-10-04-live-preflight.md). The user was asked to complete the required sign-in; no provider credentials were copied, and generation remains disabled.
