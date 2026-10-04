# Delivery status

Updated: 2026-10-04. Public Windows v1 is **not ready**.

- Current milestone: M1 — Codex runtime qualification.
- Current task: M1-T05 **BLOCKED** on account-side confirmation that earlier live probes consumed only included usage, plus remaining live/manual acceptance. Independent repairs M1-T05a/T05b are complete: commentary is excluded from structured answers and provider-reported model rerouting stops publication. See [message evidence](docs/verification/2026-10-04-codex-messages.md) (commit 168ef15) and [rerouting evidence](docs/verification/2026-10-04-codex-rerouting.md). Production generation remains disabled.
- Completed milestones: M0 (commit 2ea989e). Prior application slices remain partial against M1–M11.
- Latest verification: M1-T05b Q passed with 546 Python tests, seven frontend tests, static evaluations, lint/contracts/docs/TypeScript/build; 84 focused model/message/recovery regressions passed. [Rerouting evidence](docs/verification/2026-10-04-codex-rerouting.md) records scope and limits. Earlier [message evidence](docs/verification/2026-10-04-codex-messages.md) retains its 532-test Q result. [Repair evidence](docs/verification/2026-10-04-codex-loopback-repair.md) retains actual network/write denials, transactional filter lifecycle, D with actual restore, no-inference protocol smoke and authenticated gpt-6-astra preflight. The [earlier full dispatcher](docs/verification/2026-10-04-delivery-resume.md) stopped at missing cargo.
- Known warning: existing Starlette/httpx test-client deprecation.
- Known release blockers: no live-qualified provider version; production inference fails closed while cached/synthetic features remain usable; cargo absent; native/clean-machine installer/update/rollback unqualified. Full wrapper reports missing cargo without skipping.
- Next action: obtain the pending account-side included-usage confirmation before resuming explicit live/manual qualification with the selected gpt-6-astra model; the live harness repeats extended actual enforcement before inference. Include completed-message phase handling and model identity in the remaining acceptance. The supplement is already installed; do not re-provision or replace provider rules. Its shared native offline-account scope and explicit elevated removal are documented in DEC-017/README. Reboot/packaged/clean-machine behavior remains unqualified. The independent M1 repairs identified in this review are complete; M2–M11 depend on incomplete M1. Never infer release readiness or promote capabilities from these probes.
- Continuation notes: use codex/project-delivery-foundation. Original empty read-only .codex file is preserved in ignored .local/codex-placeholder-2026-10-04. No remote Git action, provider sign-in/inference or application-library mutation occurred in M0; database tests used separate disposable clusters.
- Authorization: normal implementation and verified local commits; official/free sources first; explicit authenticated-subscription checks after deterministic validation. User explicitly approved elevated Windows sandbox setup and then requested repair of the actual loopback failure; the scoped supplement and removal/reinstallation verification are complete. Pause for sign-in, quotas or extra charges. PR/push/merge/publishing require separate authorization.

## Evidence

Historical results keep their original dates: [2026-10-03 preview checks](docs/archive/2026-10-04/IMPLEMENTATION.md#verification-record-2026-10-03), [prior documentation audit](docs/archive/2026-10-04/IMPLEMENTATION.md#documentation-audit-2026-10-04). New results are in [foundation verification](docs/verification/2026-10-04-foundation.md). [TASKS](TASKS.md) owns actions; [EVALS](EVALS.md) commands and release requirements.

M1-T01 evidence: [runtime capabilities](docs/verification/2026-10-04-runtime-capabilities.md). M1 remains incomplete.

M1-T02 evidence: [configuration and thread isolation](docs/verification/2026-10-04-codex-isolation.md). Custom system/profile/workspace configuration and file credentials currently stop the isolated connection; no files are imported or removed.

M1-T03a evidence: [model catalogs and selection](docs/verification/2026-10-04-model-selection.md). Authenticated model entitlement and approval interactions remain unqualified.

M1-T03b evidence: [bounded access review](docs/verification/2026-10-04-access-review.md). Deny/cancel are supported within the current policy; command/file/network grants cannot be approved.

M1-T04 evidence: [owned process lifecycle and session recovery](docs/verification/2026-10-04-runtime-recovery.md). Native packaged-host and live-provider qualification remain separate.

M1-T05 partial evidence: [original harness/sign-in blocker](docs/verification/2026-10-04-live-preflight.md), followed by [successful sign-in, partial live observations and sandbox blocker](docs/verification/2026-10-04-authenticated-codex.md). No provider credentials were copied, and production generation remains disabled.

M1-T05 follow-up: [approved setup and actual enforcement](docs/verification/2026-10-04-codex-sandbox-enforcement.md). Setup passed; native loopback restriction failed. No inference was requested in this follow-up.

M1-T05 repair: [scoped native WFP supplement and verification](docs/verification/2026-10-04-codex-loopback-repair.md). The original loopback failure is resolved on this developer machine; complete subscription/native release qualification remains outstanding. No inference was requested during repair.

M1-T05a: [phase-aware completed message assembly](docs/verification/2026-10-04-codex-messages.md). Deterministic repair only; no inference, OS policy or production capability change.

M1-T05b: [provider-reported model rerouting rejection](docs/verification/2026-10-04-codex-rerouting.md). Deterministic repair only; selected settings retained, with no answer publication or automatic retry after rerouting.
