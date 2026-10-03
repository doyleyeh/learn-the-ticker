# AGENTS.md

Learn the Ticker is a citation-first local desktop research and learning application for beginner and intermediate users.

The accepted implementation baseline is [Learn the Ticker: revised desktop architecture and migration plan](NEW_STRUCTURE.md). Continue that plan using docs/IMPLEMENTATION.md for current progress, dependencies and remaining acceptance checks. The repository documents carry the plan; agents must not depend on prior chat history or treat the target architecture as already delivered.

Read NEW_STRUCTURE.md, PRD.md, TECHNICAL_DESIGN_SPEC.md, docs/IMPLEMENTATION.md and docs/TESTING.md before changes. Follow safety boundaries, then PRD, technical design and architecture decisions. The approved reboot supersedes old Top-500, hosted Next.js and agent-loop requirements.

For each task: git status --short; state acceptance criteria; inspect before editing; implement a coherent change; run relevant checks and the quality gate; report changes, results and limitations. Three repair attempts, then diagnose and report. Keep implementation status honest. Never mark a live provider or installer complete based solely on fixtures.

Never produce buy/sell/hold advice, allocation/position sizing, tax advice, unsupported targets or trading behavior. Cite important facts and label uncertainty. Unverified notes never feed facts/charts/calculations. Verify source identity, claim support, freshness and usage rights; a subscription does not grant source redistribution rights.

Normal CI is deterministic with no live external provider calls. Explicit live smoke runs are separate. Secrets remain out of frontend bundles, logs, URLs, exports, backups and committed files. Provider transport must restrict tools in code/configuration, not only in prompts.

Root npm scripts delegate to apps/desktop. Production enters backend/app, not the fixture API. Preserve reusable financial UI/logic until migrated; remove superseded routes/configuration once checks establish their replacement. Git preserves history; do not keep duplicate legacy trees.

Keep docs synchronized with their roles: PRD requirements, NEW_STRUCTURE architecture, technical design mechanisms/limitations, IMPLEMENTATION delivery status, TESTING reproducible checks and MIGRATION compatibility. Update README commands and hidden review guidance when affected. Store dated verification evidence in IMPLEMENTATION; do not describe target behavior, stored settings or fixtures as shipped functionality.

Explain new dependency need, alternatives, security/licensing and packaging impact. Use conventional commits. PR creation and merging need user approval. Never use git reset --hard, git clean -fd, git push --force, destructive rebase or discard user changes without explicit authorization. No automatic agent-loop commits, pushes or merges.

Run the PowerShell or Bash quality gate. For UI changes verify citations, source inspection, freshness, missing evidence, readability and responsive layouts. For database/native changes add private-PostgreSQL lifecycle/restore tests. Public v1 needs all three subscription integrations, complete feature parity and a clean-machine Windows installer.
