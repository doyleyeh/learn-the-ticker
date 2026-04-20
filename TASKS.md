# TASKS.md

## Current task

### T-000: Create agentic development scaffold

Goal:
Set up the files, tests, eval folders, scripts, and CI workflow needed for Codex-assisted development.

Allowed files:

- AGENTS.md
- SPEC.md
- TASKS.md
- EVALS.md
- Makefile
- .gitignore
- requirements-dev.txt
- scripts/\*\*
- tests/\*\*
- evals/\*\*
- .github/\*\*
- docs/agent-journal/\*\*

Do not change:

- product requirements
- financial safety rules
- advice-boundary rules

Acceptance criteria:

- Core agent instruction files exist.
- Quality gate script exists.
- Agent loop script exists.
- Basic repo contract tests pass.
- Basic static evals pass.
- CI workflow runs the quality gate.
- Git commits are created by the harness, not directly by Codex.

Required commands:

- bash scripts/run_quality_gate.sh

Iteration budget:

- Max 3 Codex implementation loops before reporting blockers.

## Backlog

### T-001: Create backend FastAPI skeleton

Goal:
Create the initial backend service structure for search, asset overview, sources, compare, and chat endpoints.

### T-002: Create frontend Next.js skeleton

Goal:
Create the initial frontend structure for search, asset page, citation chips, source drawer, and glossary popovers.

### T-003: Add citation validation module

Goal:
Validate that generated claims map to valid source documents, chunks, or facts.

### T-004: Add safety guardrail tests

Goal:
Detect buy/sell language, personalized allocation advice, unsupported price targets, and certainty around future returns.
