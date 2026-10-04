# Delivery status

Updated: 2026-10-04. Public Windows v1 is **not ready**.

- Current milestone: M1 — Codex runtime qualification.
- Current task: M1-T05 **BLOCKED** on authoritative complete tool-inventory evidence from the installed runtime. The approved DEC-020 repair is implemented: same-model temporary catalog, strict tool/agent policy, deny/cancel-only permission requests and cleanup. Actual denial, cancellation, source/cached behavior and consent/disconnect checks passed; the former live denial blocker is resolved. M1-T05d records the verified repair slice. Production generation remains disabled.
- Completed milestones: M0 (commit 2ea989e). Prior application slices remain partial against M1–M11.
- Latest verification: [Restricted-catalog evidence](docs/verification/2026-10-04-codex-restricted-catalog.md): final Q passed **665 Python/seven frontend tests**, static evaluations, lint/contracts/docs/TypeScript/build; 65 new focused scenarios passed. D/PostgreSQL lifecycle and actual restore passed. Installed no-inference smoke/preflight passed; fresh actual extended sandbox enforcement preceded six bounded live turns covering deny/cancel, independent source support, cached behavior and consent/disconnect cleanup. Model-reported tool lists matched the intended research/empty cached sets but do not certify inventory. Earlier evidence retains its original dates/results; the [full dispatcher](docs/verification/2026-10-04-delivery-resume.md) still lacks cargo/native release acceptance.
- Known warning: existing Starlette/httpx test-client deprecation.
- Known release blockers: no live-qualified provider version; production inference fails closed while cached/synthetic features remain usable; cargo absent; native/clean-machine installer/update/rollback unqualified. Full wrapper reports missing cargo without skipping.
- Next action: obtain a supported complete model-facing tool-inventory attestation for the actual selected-model thread, or review a concrete runtime/transport change that supplies equivalent direct evidence without expanding permissions. The pinned protocol lacks that endpoint; debug prompt inspection and model self-reports are insufficient. Do not repeat equivalent self-report/refusal turns or waive acceptance. No further sign-in, OS setup or permission grant is needed for the completed repair. Keep installed WFP rules. M2–M11 remain dependent on incomplete M1.
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

M1-T05 continuation: [live source, consent and disconnect acceptance](docs/verification/2026-10-04-codex-live-acceptance.md). User's prior usage confirmation recorded; no administrator prompts or production capability change. Real approval denial/tool inventory remain blockers.

M1-T05c: [pending approval event ordering](docs/verification/2026-10-04-codex-pending-approvals.md). Full synthetic pending/request/denied sequence, rejection of execution output and no grant/configuration change; live denial remains unexercised.

M1-T05 investigation: [actual metadata, experimental protocol inspection, bounded live probe and restricted-catalog proposal](docs/verification/2026-10-04-codex-tool-policy-investigation.md). Model-catalog overrides passed no-inference compatibility. The subsequent explicit user approval is recorded in DEC-020 and fulfilled by M1-T05d below; full inventory acceptance remains outstanding.

M1-T05d: [restricted catalog and actual permission review](docs/verification/2026-10-04-codex-restricted-catalog.md). User approval is fulfilled; real denial/cancel and positive source/lifecycle checks passed on the same runtime/model/subscription. Complete authoritative inventory and public qualification remain outstanding.
