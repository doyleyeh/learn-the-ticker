# Contributing

Read [AGENTS.md](AGENTS.md), [PRD](PRD.md), [architecture](NEW_STRUCTURE.md), [technical design](TECHNICAL_DESIGN_SPEC.md), [the backlog](docs/IMPLEMENTATION.md) and [testing](docs/TESTING.md). Work in small reviewable increments, keep safety and citation behavior tested, and update implementation status with evidence. Begin with `git status --short` and acceptance criteria; preserve existing user changes.

Use npm workspaces and a repository-local Python environment. Normal tests use synthetic/permitted-recorded data and must not invoke subscriptions, paid APIs or source retrieval. Do not commit credentials, source payloads without rights, or user research.

Run [the quality gate](docs/TESTING.md). Add behavioral tests for evidence admission, persistence, cancellation and security when changing those boundaries. Existing financial tests protect useful behavior while the migration is incomplete. Tests that hard-code removed repository layout are replaced, not kept as product requirements.

Document dependencies and schema changes, including alternatives and packaging/license impact. Generated TypeScript must come from the Python contracts. Database changes need a compatible migration and tested restore path. Do not use production data for tests.

Keep documentation aligned with its responsibility: requirements describe expected behavior, architecture records accepted decisions, technical design describes mechanisms and limitations, and the backlog owns current status and dated check results. Update setup/testing instructions when commands change. Settings fields, fixture adapters and build configuration alone never establish a completed feature. Check local Markdown links, documented paths and hidden review instructions as part of documentation changes; do not copy the backlog into competing plans.

Use the [manual review checklist](.github/codex/prompts/review.md) for an explicitly requested review. The automatic API-key PR-review workflow has been removed. Ordinary CI runs deterministic Windows/Ubuntu checks and generated-contract verification; live subscriptions, external retrieval, native packaging and release qualification are separate. Do not post review feedback, open PRs or merge automatically.

Use Conventional Commits. After three failed repair attempts, report the diagnosed blocker. Ask before opening a PR or merging. Do not resurrect the removed agent-loop framework or bypass a failed check.
