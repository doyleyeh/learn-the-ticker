# Repo Workflow

## Required Reads

Read these files before changing anything:

1. `AGENTS.md`
2. `docs/learn_the_ticker_PRD.md`
3. `docs/learn_the_ticker_technical_design_spec.md`
4. `docs/learn-the-ticker_proposal.md`
5. `SPEC.md`
6. `TASKS.md`
7. `EVALS.md`

Follow the repo order: safety and advice-boundary rules first, then PRD, technical design spec, proposal, `SPEC.md`, `TASKS.md`, and `EVALS.md`.

## Status Review

- Run `git status --short`.
- Review the current task and backlog state in `TASKS.md`.
- Count planned cycles as `1` for an existing current task plus the number of backlog task headings.
- Skim recent Completed entries before preparing more tasks.

## Worktree Cleanup Rule

Create a cleanup commit only when all of the following are true:

- The diff has one clear purpose.
- The purpose is already understandable from the changed files and repo context.
- The required checks from `EVALS.md` have already passed for that change.
- The commit can be described with a specific Conventional Commit subject.

Do not create a cleanup commit when:

- The tree contains mixed-purpose changes.
- The changes appear to be user work in progress.
- The work needs more review before it should be preserved.
- You cannot tell which tests or evals are required.

## TASKS.md Planning Rule

- If a current task exists and the planned cycles already cover the requested run, do not add more tasks.
- If planning is needed, add only small sequential tasks aligned with the repo's current deterministic MVP direction.
- Keep the automation pass capped at five total planned cycles.
- Do not create speculative infrastructure tasks when the repo still needs deterministic contract convergence.

## WSL Run Rule

Use the repo's WSL path and activate the `learn-the-ticker` conda environment with `scripts/activate_agent_env.sh` before running the cycle.

Preferred cycle command:

```bash
bash scripts/run_task_cycle.sh --model <selected-model> --repeat --max-cycles 5 --push
```

Launch from Windows PowerShell with:

```powershell
wsl.exe bash -lc 'cd <repo-wsl-path> && source scripts/activate_agent_env.sh && bash scripts/run_task_cycle.sh --model <selected-model> --repeat --max-cycles 5 --push'
```
