---
name: project-delivery
description: Recover and advance Learn the Ticker milestone delivery using its canonical repository documents, verification tiers and durable checkpoints. Use for this repository's implementation or delivery-status work.
---

# Project delivery

Read [AGENTS](../../../AGENTS.md), [SPEC](../../../SPEC.md), [PLAN](../../../PLAN.md), [TASKS](../../../TASKS.md), [EVALS](../../../EVALS.md), [STATUS](../../../STATUS.md) and [DECISIONS](../../../DECISIONS.md). The documents own requirements/state; this skill owns the procedure, not an alternative backlog.

Use [the delivery workflow](references/delivery-workflow.md) when implementing or recovering a task. Inspect git status and relevant code before editing. Select the highest-priority unblocked task, record it IN_PROGRESS and state observable acceptance.

Use scripts/verify-fast.ps1 or scripts/verify-fast.sh during coherent edits; run targeted tests as needed. Before a milestone checkpoint run verify-milestone, plus EVALS-required database/native/browser checks. verify-full requires the native packaging toolchain/resources and still does not substitute for live subscriptions or clean-machine acceptance. PowerShell is supported on native Windows; Bash wrappers support POSIX/Git Bash with the repository virtual environment.

Normal tests never contact providers. Existing authenticated-subscription live checks are authorized by the delivery request only after deterministic validation; stop for sign-in, quotas or extra charges. Three failed repairs require diagnosis and a recorded blocker. Continue independent work, never dependent work past a failing gate.

After passing checks, inspect the complete diff, update TASKS/STATUS and dated evidence, and create a coherent conventional local commit. Local checkpoint authorization does not authorize push/PR/merge/publication. No background scheduler or retired agent-loop automation is part of this skill.
