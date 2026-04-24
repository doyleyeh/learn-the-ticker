---
name: learn-the-ticker-automation-agent-loop
description: Review and operate the Learn the Ticker repo's local agent-loop workflow. Use when Codex needs to inspect repo status, read the repo control docs, decide whether the current worktree can be cleaned up with a safe Conventional Commit, prepare up to five narrow TASKS.md items when the current task or backlog is missing, choose between gpt-5.3-codex-spark and gpt-5.4 based on a reliable usage signal, and run scripts/run_task_cycle.sh from the learn-the-ticker WSL conda environment.
---

# Learn the Ticker Automation Agent Loop

Use this skill for repo-maintenance turns whose goal is to get the Learn the Ticker harness back into a runnable state and then launch the repeat-mode task cycle safely.

Read [references/repo-workflow.md](references/repo-workflow.md) first. Read [references/model-selection.md](references/model-selection.md) before choosing a model.

## Quick Start

1. Read `AGENTS.md`, `docs/learn_the_ticker_PRD.md`, `docs/learn_the_ticker_technical_design_spec.md`, `docs/learn-the-ticker_proposal.md`, `SPEC.md`, `TASKS.md`, and `EVALS.md`.
2. Run `git status --short` before making decisions.
3. Review the current task, backlog count, and worktree state.
4. Run `python codex-skills/learn-the-ticker-automation-agent-loop/scripts/task_cycle_preflight.py --repo-root . --max-cycles 5`.
5. If the repo is safe to continue autonomously and `TASKS.md` needs more planning, add or promote only the minimum needed, up to five total planned cycles.
6. Run the printed WSL command or the equivalent `bash scripts/run_task_cycle.sh --model <selected-model> --repeat --max-cycles 5 --push`.

## Workflow

### Review Project Status

- Start with `git status --short`.
- Read the required control docs in the repo's documented order.
- Inspect `TASKS.md` before inventing more work. Prefer continuing the current deterministic contract-convergence direction already described in `SPEC.md`.
- Skim the latest Completed entries in `TASKS.md` so new backlog items do not duplicate recent work.

### Clean Up the Worktree Carefully

- Inspect diffs before committing anything.
- Create a Conventional Commit only when the dirty tree is cohesive, understandable, and already validated by the checks required in `EVALS.md`.
- Do not sweep unrelated edits into a cleanup commit.
- Treat user-authored or ambiguous changes as protected. If the worktree mixes unrelated work, partial experiments, or conflicting directions, stop and ask instead of guessing.
- When a cleanup commit is appropriate, use a specific Conventional Commit subject that matches the actual change. Do not use generic messages.

### Prepare TASKS.md Only When Needed

- If `TASKS.md` already has a current task and enough backlog for the requested repeat run, leave it alone.
- If there is no current task or the planned cycles are fewer than the requested run, prepare only the minimum additional tasks needed.
- Never plan more than five total cycles for this automation pass.
- Keep new tasks narrow, sequential, deterministic, and within MVP scope.
- Do not add tasks that depend on live providers, secrets, deployment credentials, or manual browser work unless the repo has clearly reached that stage and the user asked for it.

### Choose the Model

- The repo defaults to `gpt-5.4` with `high` reasoning effort.
- Prefer `gpt-5.3-codex-spark` only when a reliable remaining-capacity signal says at least 30% remains.
- If only a used-percent signal exists, use Spark only when used percentage is 70 or lower.
- If no reliable Spark usage signal is available, fall back to `gpt-5.4`.
- Run `python codex-skills/learn-the-ticker-automation-agent-loop/scripts/task_cycle_preflight.py --repo-root . --max-cycles 5` to apply the rule consistently.

### Run from WSL

- Use the `learn-the-ticker` conda environment through `scripts/activate_agent_env.sh`.
- Preferred command pattern inside WSL:
  `bash scripts/run_task_cycle.sh --model <selected-model> --repeat --max-cycles 5 --push`
- When launching from Windows PowerShell, wrap the command with `wsl.exe bash -lc 'cd <repo> && source scripts/activate_agent_env.sh && bash scripts/run_task_cycle.sh ...'`.
- Do not print or copy secret values. Let the existing WSL environment provide them if needed.

### Report the Result

- Summarize the initial repo state, whether a cleanup commit was created, whether `TASKS.md` was changed, which model was selected and why, and what command was run.
- If the skill stops before execution, report the blocker instead of forcing the cycle.
