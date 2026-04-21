#!/usr/bin/env bash
set -euo pipefail

MAIN_BRANCH="main"
PREPARE_NEXT=1
PUSH_MAIN=0
COMMIT_FAILURES=0

usage() {
  cat <<'EOF'
Usage: bash scripts/run_task_cycle.sh [options]

Runs one full local task cycle:
  1. Run scripts/agent_loop.sh for the current TASKS.md task.
  2. Merge the completed agent/T-... branch into main with scripts/local_merge_task.sh.
  3. Ask Codex to prepare TASKS.md for the next backlog task.
  4. Run the quality gate and commit the next-task preparation.

Options:
  --main <branch>       Main branch to merge into. Default: main.
  --no-prepare-next     Stop after local merge; do not update TASKS.md.
  --commit-failures     Pass --commit-failures through to agent_loop.sh.
  --push                Push main after the local merge and next-task prep commit.
  -h, --help            Show this help.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --main)
      MAIN_BRANCH="${2:-}"
      if [ -z "$MAIN_BRANCH" ]; then
        echo "--main requires a branch name."
        exit 2
      fi
      shift
      ;;
    --no-prepare-next)
      PREPARE_NEXT=0
      ;;
    --commit-failures)
      COMMIT_FAILURES=1
      ;;
    --push)
      PUSH_MAIN=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 2
      ;;
  esac
  shift
done

require_clean_tree() {
  if [ -n "$(git status --porcelain)" ]; then
    git status --short
    echo "Working tree is not clean. Commit, stash, or discard unrelated changes before continuing."
    exit 1
  fi
}

current_task_line() {
  grep -m1 '^### T-' TASKS.md || true
}

task_id_from_line() {
  sed -E 's/^### ([^: ]+).*/\1/'
}

task_title_from_line() {
  sed -E 's/^### [^: ]+:[[:space:]]*//'
}

commit_subject_from_title() {
  local title="$1"
  printf '%s%s' "$(printf '%s' "$title" | cut -c1 | tr '[:upper:]' '[:lower:]')" "$(printf '%s' "$title" | cut -c2-)"
}

has_backlog_task() {
  awk '
    /^## Backlog/ { in_backlog = 1; next }
    in_backlog && /^### T-/ { found = 1 }
    END { exit found ? 0 : 1 }
  ' TASKS.md
}

prepare_next_task() {
  local completed_task_id="$1"
  local completed_task_title="$2"
  local task_branch="$3"
  local merge_commit="$4"
  local prompt_path
  local changed_files
  local next_line
  local next_task_id
  local next_task_title
  local next_subject

  if ! has_backlog_task; then
    echo "No backlog task found. Skipping next-task preparation."
    return 0
  fi

  prompt_path="$(mktemp)"
  cat > "$prompt_path" <<EOF
You are preparing TASKS.md for the next local agent-loop cycle.

Read:
- AGENTS.md
- SPEC.md
- TASKS.md
- EVALS.md
- docs/learn_the_ticker_PRD.md
- docs/learn_the_ticker_technical_design_spec.md

Only edit TASKS.md. Do not edit any other file. Do not run git commit or git push.

Current completed task:
- id: ${completed_task_id}
- title: ${completed_task_title}
- local merge commit: ${merge_commit}
- merged branch: ${task_branch}

Update TASKS.md as follows:
1. Move the completed current task into the top of the Completed section.
2. Summarize completion using concrete implementation details from the task branch commit, tests, evals, and docs/agent-journal if present. Do not invent unsupported details.
3. Include completion commits, including the implementation commit(s) and local merge commit.
4. Promote the first Backlog task into Current task.
5. Expand the promoted task into a full task contract with:
   - Goal
   - task-scope paragraph
   - Allowed files
   - Do not change
   - detailed Acceptance criteria
   - Required commands
   - Iteration budget
6. Preserve product guardrails: no investment advice, no live external calls, citations for important claims, freshness/unknown/stale handling.
7. Keep the next task narrow enough for one agent loop.
EOF

  echo "== Preparing next task in TASKS.md =="
  set +e
  codex -a never exec --sandbox workspace-write "$(cat "$prompt_path")"
  local codex_status=$?
  set -e
  rm -f "$prompt_path"

  if [ "$codex_status" -ne 0 ]; then
    echo "Codex next-task preparation failed with status $codex_status."
    exit "$codex_status"
  fi

  changed_files="$(git diff --name-only)"
  if [ -z "$changed_files" ]; then
    echo "Codex did not change TASKS.md. Skipping next-task preparation commit."
    return 0
  fi

  if [ "$changed_files" != "TASKS.md" ]; then
    echo "Next-task preparation changed files other than TASKS.md:"
    printf '%s\n' "$changed_files"
    echo "Review the working tree before continuing."
    exit 1
  fi

  next_line="$(current_task_line)"
  next_task_id="$(printf '%s\n' "$next_line" | task_id_from_line)"
  next_task_title="$(printf '%s\n' "$next_line" | task_title_from_line)"
  next_subject="$(commit_subject_from_title "$next_task_title")"

  echo "== Running quality gate after next-task preparation =="
  bash scripts/run_quality_gate.sh

  git add TASKS.md
  git commit \
    -m "chore(${next_task_id}): prepare ${next_subject} task" \
    -m "Previous task: ${completed_task_id}" \
    -m "Merged branch: ${task_branch}" \
    -m "Quality gate: passed"
}

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# shellcheck source=scripts/activate_agent_env.sh
source "$ROOT/scripts/activate_agent_env.sh"
ltt_require_codex_toolchain

require_clean_tree

TASK_LINE="$(current_task_line)"
if [ -z "$TASK_LINE" ]; then
  echo "Could not find a current task in TASKS.md."
  exit 1
fi

TASK_ID="$(printf '%s\n' "$TASK_LINE" | task_id_from_line)"
TASK_TITLE="$(printf '%s\n' "$TASK_LINE" | task_title_from_line)"

echo "== Task cycle =="
echo "== Current task: ${TASK_ID}: ${TASK_TITLE} =="
echo "== Main branch: ${MAIN_BRANCH} =="
echo "== Prepare next: ${PREPARE_NEXT} =="
echo "== Push main: ${PUSH_MAIN} =="

AGENT_ARGS=()
if [ "$COMMIT_FAILURES" -eq 1 ]; then
  AGENT_ARGS+=(--commit-failures)
fi

echo "== Running agent loop =="
bash scripts/agent_loop.sh "${AGENT_ARGS[@]}"

TASK_BRANCH="$(git branch --show-current)"
if ! printf '%s\n' "$TASK_BRANCH" | grep -Eq "^agent/${TASK_ID}-"; then
  echo "Expected to be on agent/${TASK_ID}-... after agent loop, but current branch is: $TASK_BRANCH"
  exit 1
fi

echo "== Merging completed task branch =="
bash scripts/local_merge_task.sh "$TASK_BRANCH" --main "$MAIN_BRANCH"

MERGE_COMMIT="$(git rev-parse --short HEAD)"

if [ "$PREPARE_NEXT" -eq 1 ]; then
  prepare_next_task "$TASK_ID" "$TASK_TITLE" "$TASK_BRANCH" "$MERGE_COMMIT"
fi

if [ "$PUSH_MAIN" -eq 1 ]; then
  echo "== Pushing ${MAIN_BRANCH} =="
  git push origin "$MAIN_BRANCH"
fi

echo "== Task cycle complete =="
git status --short
git log --oneline -5
