# Delivery status

Updated: 2026-10-04. Public Windows v1 is **not ready**.

- Current milestone: M1 — Codex runtime qualification.
- Current task: M1-T05 **BLOCKED** on actual native network enforcement and account-side usage confirmation. User-approved elevated setup completed at 2026-10-04T01:34:49.9381996Z; fresh readiness and authenticated no-inference preflight passed. Actual inside/outside file writes were denied, but a readOnly/networkAccess=false command reached a disposable loopback listener, reproduced with matching sandbox-account firewall rules. Do not enable production generation or run further live probes until resolved. See [sandbox enforcement evidence](docs/verification/2026-10-04-codex-sandbox-enforcement.md). Prior authenticated search/cancellation/reconnect observations remain partial evidence; 695a8fc records that implementation checkpoint.
- Completed milestones: M0 (commit 2ea989e). Prior application slices remain partial against M1–M11.
- Latest verification: [sandbox enforcement evidence](docs/verification/2026-10-04-codex-sandbox-enforcement.md) records approved setup/readiness, actual write denials and the unresolved loopback failure. Final shared gate passed with 465 Python tests, seven frontend tests, static evaluations, lint/contracts/docs/TypeScript/build. Prior Windows process/PostgreSQL restore/browser results retain their own records; the [earlier full dispatcher](docs/verification/2026-10-04-delivery-resume.md) stopped at missing cargo.
- Known warning: existing Starlette/httpx test-client deprecation.
- Known release blockers: no live-qualified provider version; production inference fails closed while cached/synthetic features remain usable; cargo absent; native/clean-machine installer/update/rollback unqualified. Full wrapper reports missing cargo without skipping.
- Next action: resolve the installed runtime/platform's loopback enforcement gap through a reviewed supported mechanism or runtime fix, keeping the failing probe intact. Firewall profiles/block rules are enabled and the sandbox identity matches the rule; setup retry alone is not an established repair. Then rerun actual enforcement and required live/manual acceptance, including account-side usage confirmation. No independent unblocked M1 task remains; M2–M11 depend on incomplete M1. Do not weaken the sandbox, alter broad Windows firewall policy, silently change runtime/model or promote capabilities.
- Continuation notes: use codex/project-delivery-foundation. Original empty read-only .codex file is preserved in ignored .local/codex-placeholder-2026-10-04. No remote Git action, provider sign-in/inference or application-library mutation occurred in M0; database tests used separate disposable clusters.
- Authorization: normal implementation and verified local commits; official/free sources first; explicit authenticated-subscription checks after deterministic validation. User explicitly approved the dedicated elevated Windows sandbox setup, now completed. Pause for sign-in, quotas or extra charges. PR/push/merge/publishing require separate authorization.

## Evidence

Historical results keep their original dates: [2026-10-03 preview checks](docs/archive/2026-10-04/IMPLEMENTATION.md#verification-record-2026-10-03), [prior documentation audit](docs/archive/2026-10-04/IMPLEMENTATION.md#documentation-audit-2026-10-04). New results are in [foundation verification](docs/verification/2026-10-04-foundation.md). [TASKS](TASKS.md) owns actions; [EVALS](EVALS.md) commands and release requirements.

M1-T01 evidence: [runtime capabilities](docs/verification/2026-10-04-runtime-capabilities.md). M1 remains incomplete.

M1-T02 evidence: [configuration and thread isolation](docs/verification/2026-10-04-codex-isolation.md). Custom system/profile/workspace configuration and file credentials currently stop the isolated connection; no files are imported or removed.

M1-T03a evidence: [model catalogs and selection](docs/verification/2026-10-04-model-selection.md). Authenticated model entitlement and approval interactions remain unqualified.

M1-T03b evidence: [bounded access review](docs/verification/2026-10-04-access-review.md). Deny/cancel are supported within the current policy; command/file/network grants cannot be approved.

M1-T04 evidence: [owned process lifecycle and session recovery](docs/verification/2026-10-04-runtime-recovery.md). Native packaged-host and live-provider qualification remain separate.

M1-T05 partial evidence: [original harness/sign-in blocker](docs/verification/2026-10-04-live-preflight.md), followed by [successful sign-in, partial live observations and sandbox blocker](docs/verification/2026-10-04-authenticated-codex.md). No provider credentials were copied, and production generation remains disabled.

M1-T05 follow-up: [approved setup and actual enforcement](docs/verification/2026-10-04-codex-sandbox-enforcement.md). Setup passed; native loopback restriction failed. No inference was requested in this follow-up.
