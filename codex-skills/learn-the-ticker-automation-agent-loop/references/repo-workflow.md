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

- Before starting another loop, check for active Codex/task-cycle/agent-loop work. Inspect running processes when available, current terminal output when available, `git status --short --branch`, recent branch/task-cycle state, and obvious in-progress artifacts under `.agent-runs/`.
- If another Codex agent or task-cycle process appears active, stop immediately and report that the automation skipped the run because active work was detected. Do not modify files, commit, push, or start another loop.
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

The activation script is part of the environment contract. It should resolve Node, npm, Python, and Codex from the WSL conda environment, normalize WSL temp variables to a Linux temp directory so pytest does not inherit Windows `/mnt/c/.../Temp` paths, and provide a standard Windows `PATHEXT` for Windows tools launched from WSL.

Recommended local Git settings for the WSL worktree:

```bash
git config --local core.autocrlf input
git config --local core.eol lf
git config --local core.ignorecase false
git config --local core.filemode true
```

Preferred cycle command:

```bash
bash scripts/run_task_cycle.sh --model <selected-model> --repeat --max-cycles 5 --push
```

Launch from Windows PowerShell with:

```powershell
wsl.exe bash -lc 'cd <repo-wsl-path> && source scripts/activate_agent_env.sh && bash scripts/run_task_cycle.sh --model <selected-model> --repeat --max-cycles 5 --push'
```

## Docker Compose Check

`docker compose config` is an optional scaffold validation check when Docker is available. If it fails in WSL with Docker Desktop's WSL integration message, the normal deterministic quality gate can still pass; enable Docker Desktop WSL integration for the distro or install Docker Engine inside WSL before rerunning the Docker-specific check.
