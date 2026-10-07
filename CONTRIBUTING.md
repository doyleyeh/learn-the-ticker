# Contributing

Start with [AGENTS](AGENTS.md), [SPEC](SPEC.md), [PLAN](PLAN.md), [TASKS](TASKS.md), [EVALS](EVALS.md), [STATUS](STATUS.md) and [DECISIONS](DECISIONS.md). Relevant mechanisms and compatibility are in [technical design](TECHNICAL_DESIGN_SPEC.md) and [migration](docs/MIGRATION.md). The [delivery skill](.codex/skills/project-delivery/SKILL.md) describes the execution loop.

Use a non-protected branch and preserve user changes. Recover repository state, state acceptance criteria, inspect before editing, implement one coherent task and run affected tests. Run the milestone gate before a checkpoint; database/native changes also require isolated PostgreSQL lifecycle/actual-restore checks. UI changes require source/citation/freshness/missing-state/readability checks at normal and 640-pixel widths.

Normal CI uses deterministic synthetic/permitted-recorded data and never calls live subscriptions or retrieval services. Explicit live checks remain separate. Never commit credentials, restricted source payloads, user research or raw runtime traces. Generate contracts from Pydantic; do not hand-edit generated TypeScript.

Document dependencies, alternatives, exact versions, licenses and packaging impact in DECISIONS. Keep requirements, milestone acceptance, tasks, current status and dated evidence in their owning documents. No completed milestone may have required failing validation. After three failed repairs, record diagnosis and continue bounded attempts supported by new evidence; the count is not an automatic stopping point. Record a blocker when an unresolved external prerequisite prevents meaningful repair; do not weaken checks or cross sign-in, quota, cost or approval boundaries.

Reviewed local conventional commits are authorized for delivery checkpoints. PR creation, push, merge, publishing and external review posting need explicit authorization. The [manual review prompt](.github/codex/prompts/review.md) is available when requested; automatic API-key PR review remains disabled.
