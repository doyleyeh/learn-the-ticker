# Delivery status

Updated: 2026-10-04. Public Windows v1 is **not ready**.

- Current milestone: M1 — Codex runtime qualification.
- Current task: M1-T05 **BLOCKED** pending scope approval for the [restricted-catalog/request-only repair](docs/verification/2026-10-04-codex-tool-policy-investigation.md#proposed-repair--awaiting-scope-approval). Actual selected-model metadata confirms code-mode/patch/async-input exposure despite disabled features; documented prompt inspection and the full experimental schema do not expose the complete inventory. A no-inference restricted-catalog prototype passed both browsing modes without changing model or sandbox. One further guarded live code-cell probe produced no attempted call or approval and remains unqualified. Production generation remains disabled.
- Completed milestones: M0 (commit 2ea989e). Prior application slices remain partial against M1–M11.
- Latest verification: Q again passed 600 Python/seven frontend tests, static evaluations, lint/contracts/docs/TypeScript/build before the 03:00:09 UTC code-cell probe; fresh actual extended sandbox enforcement passed first. That turn did not exercise a tool denial. Restricted-catalog browsing/cached thread checks passed without inference; no production or OS policy changed. See [current investigation](docs/verification/2026-10-04-codex-tool-policy-investigation.md). Earlier [live evidence](docs/verification/2026-10-04-codex-live-acceptance.md) retains Q 569 and the eight prior turns, distinguishing disposable SQLite service checks from PostgreSQL/native acceptance. [Sandbox repair evidence](docs/verification/2026-10-04-codex-loopback-repair.md) retains D/restore and native results. The [earlier full dispatcher](docs/verification/2026-10-04-delivery-resume.md) stopped at missing cargo.
- Known warning: existing Starlette/httpx test-client deprecation.
- Known release blockers: no live-qualified provider version; production inference fails closed while cached/synthetic features remain usable; cargo absent; native/clean-machine installer/update/rollback unqualified. Full wrapper reports missing cargo without skipping.
- Next action: resolve the pending user approval for the concrete restricted-catalog/request-only tool change; do not enable it until approved. If approved, implement catalog lifecycle/strict validation and deny-only permission requests, add behavioral regressions, run Q and no-inference checks, then bounded actual denial/cancel/search/inventory acceptance. No new grant or acceptance waiver is proposed. If declined, retain current policy and blocker. Do not repeat equivalent refusal prompts or promote from prototype/source evidence. Keep installed WFP rules; no setup is needed. M2–M11 remain dependent on incomplete M1.
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

M1-T05 investigation: [actual metadata, experimental protocol inspection, bounded live probe and restricted-catalog proposal](docs/verification/2026-10-04-codex-tool-policy-investigation.md). Model-catalog overrides passed no-inference compatibility; enabling permission-request exposure awaits explicit scope approval under AGENTS.
