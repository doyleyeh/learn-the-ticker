#!/usr/bin/env bash
set -euo pipefail

MAIN_BRANCH="main"
PREPARE_NEXT=1
PUSH_MAIN=0
COMMIT_FAILURES=0
REPEAT=0
MAX_CYCLES=""
NEXT_TASK_PREPARED=0
CODEX_MODEL_OVERRIDE=""
CODEX_REASONING_EFFORT_OVERRIDE=""

usage() {
  cat <<'EOF'
Usage: bash scripts/run_task_cycle.sh [options]

Runs one or more full local task cycles:
  0. In repeat mode, prepare enough Backlog headings for the requested cycle count when safe.
  1. Run scripts/agent_loop.sh for the current TASKS.md task.
  2. Merge the completed agent/T-... branch into main with scripts/local_merge_task.sh.
  3. Ask Codex to prepare TASKS.md for the next backlog task, or finalize the task board when the backlog is empty.
  4. Run the quality gate and commit the TASKS.md update.

Options:
  --main <branch>       Main branch to merge into. Default: main.
  --no-prepare-next     Stop after local merge; do not update TASKS.md.
  --commit-failures     Pass --commit-failures through to agent_loop.sh.
  --model <model>       Override the Codex model for this task-cycle run. Default: gpt-5.4.
  --reasoning-effort <effort>
                        Override the Codex reasoning effort for this task-cycle run. Default: high.
  --repeat              Continue running prepared next tasks until stopped.
  --max-cycles <n>      Maximum task cycles to run. Implies --repeat when n > 1.
                        Default with --repeat: 3. Default without --repeat: 1.
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
    --model)
      CODEX_MODEL_OVERRIDE="${2:-}"
      if [ -z "$CODEX_MODEL_OVERRIDE" ]; then
        echo "--model requires a value."
        exit 2
      fi
      shift
      ;;
    --reasoning-effort)
      CODEX_REASONING_EFFORT_OVERRIDE="${2:-}"
      if [ -z "$CODEX_REASONING_EFFORT_OVERRIDE" ]; then
        echo "--reasoning-effort requires a value."
        exit 2
      fi
      shift
      ;;
    --repeat)
      REPEAT=1
      ;;
    --max-cycles)
      MAX_CYCLES="${2:-}"
      if ! printf '%s' "$MAX_CYCLES" | grep -Eq '^[1-9][0-9]*$'; then
        echo "--max-cycles requires a positive integer."
        exit 2
      fi
      if [ "$MAX_CYCLES" -gt 1 ]; then
        REPEAT=1
      fi
      shift
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

if [ -z "$MAX_CYCLES" ]; then
  if [ "$REPEAT" -eq 1 ]; then
    MAX_CYCLES=3
  else
    MAX_CYCLES=1
  fi
fi

if [ "$REPEAT" -eq 1 ] && [ "$PREPARE_NEXT" -ne 1 ]; then
  echo "--repeat requires next-task preparation. Remove --no-prepare-next or run one cycle only."
  exit 2
fi

require_clean_tree() {
  if [ -n "$(git status --porcelain)" ]; then
    git status --short
    echo "Working tree is not clean. Commit, stash, or discard unrelated changes before continuing."
    exit 1
  fi
}

current_task_line() {
  awk '
    /^## Current task/ { in_current = 1; next }
    in_current && /^## / { exit }
    in_current && /^### T-/ { print; exit }
  ' TASKS.md
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
    in_backlog && /^## / { exit }
    in_backlog && /^### T-/ { found = 1 }
    END { exit found ? 0 : 1 }
  ' TASKS.md
}

backlog_task_count() {
  awk '
    /^## Backlog/ { in_backlog = 1; next }
    in_backlog && /^## / { exit }
    in_backlog && /^### T-/ { count++ }
    END { print count + 0 }
  ' TASKS.md
}

planned_cycle_count() {
  local current_count=0
  local backlog_count

  if [ -n "$(current_task_line)" ]; then
    current_count=1
  fi

  backlog_count="$(backlog_task_count)"
  echo $((current_count + backlog_count))
}

human_action_marker_present() {
  awk '
    /^## Current task/ { in_scope = 1; next }
    /^## Completed/ { in_scope = 0 }
    /^## Backlog/ { in_scope = 1; next }
    /^## / && !/^## Backlog/ && !/^## Current task/ { if (in_scope) in_scope = 0 }
    !in_scope { next }
    {
      line = tolower($0)
    }
    BEGIN { found = 0 }
    line ~ /human[[:space:]-]*(review|test|testing|action|approval|required)/ { found = 1 }
    line ~ /manual[[:space:]-]*(review|test|testing|validation|approval|required)/ { found = 1 }
    line ~ /needs[[:space:]-]*human/ { found = 1 }
    line ~ /requires[[:space:]-]*human/ { found = 1 }
    line ~ /stop[[:space:]-]*repeat/ { found = 1 }
    END { exit found ? 0 : 1 }
  ' TASKS.md
}

ensure_repeat_backlog_capacity() {
  local current_line
  local requested_cycles="$1"
  local planned_cycles
  local missing_count
  local prompt_path
  local changed_files

  if [ "$REPEAT" -ne 1 ] || [ "$PREPARE_NEXT" -ne 1 ]; then
    return 0
  fi

  require_clean_tree

  current_line="$(current_task_line)"
  if [ -z "$current_line" ]; then
    echo "Repeat backlog preflight skipped because TASKS.md has no current task."
    return 0
  fi

  planned_cycles="$(planned_cycle_count)"
  if [ "$planned_cycles" -ge "$requested_cycles" ]; then
    echo "== Repeat backlog preflight: ${planned_cycles}/${requested_cycles} cycles already planned =="
    return 0
  fi

  if human_action_marker_present; then
    echo "== Repeat backlog preflight stopped: TASKS.md contains a human/manual action marker. =="
    echo "== Planned cycles available: ${planned_cycles}/${requested_cycles}. =="
    return 0
  fi

  missing_count=$((requested_cycles - planned_cycles))
  prompt_path="$(mktemp)"
  cat > "$prompt_path" <<EOF
You are preparing lightweight Backlog headings for a local repeat-mode agent loop.

Read:
- AGENTS.md
- docs/learn_the_ticker_PRD.md
- docs/learn_the_ticker_technical_design_spec.md
- docs/learn-the-ticker_proposal.md
- SPEC.md
- TASKS.md
- EVALS.md

Only edit TASKS.md. Do not edit any other file. Do not run git commit or git push.

Repeat-mode request:
- requested cycles: ${requested_cycles}
- currently planned cycles from Current + Backlog: ${planned_cycles}
- new Backlog headings needed: ${missing_count}

Update TASKS.md as follows:
1. Append exactly ${missing_count} new Backlog task heading(s) under the existing Backlog section.
2. Use the next sequential T-### IDs after the highest task ID already present in TASKS.md.
3. Add only headings in this format: "### T-012: Short concrete task title".
4. Do not expand new Backlog tasks into full contracts; the cycle wrapper expands a task when it is promoted.
5. Do not modify the Current task or Completed tasks.
6. Choose small, high-confidence next tasks that advance the MVP in SPEC.md and the PRD.
7. Preserve product guardrails: no investment advice, no live external calls, citations for important claims, source-use rights, PRD/TDS-first authority after safety, and freshness/unknown/stale/unavailable/partial handling.
8. If the current project stage appears to require human review, manual browser testing, API keys, product decisions, deployment credentials, or other human action before more autonomous work is safe, do not add backlog tasks. Instead, leave TASKS.md unchanged.
EOF

  echo "== Repeat backlog preflight: preparing ${missing_count} backlog task(s) for ${requested_cycles} requested cycles =="
  set +e
  ltt_codex_exec -a never exec --sandbox workspace-write "$(cat "$prompt_path")"
  local codex_status=$?
  set -e
  rm -f "$prompt_path"

  if [ "$codex_status" -ne 0 ]; then
    echo "Repeat backlog preparation failed with status $codex_status."
    exit "$codex_status"
  fi

  changed_files="$(git diff --name-only)"
  if [ -z "$changed_files" ]; then
    echo "Repeat backlog preflight did not change TASKS.md. Continuing with ${planned_cycles}/${requested_cycles} planned cycle(s)."
    return 0
  fi

  if [ "$changed_files" != "TASKS.md" ]; then
    echo "Repeat backlog preparation changed files other than TASKS.md:"
    printf '%s\n' "$changed_files"
    echo "Review the working tree before continuing."
    exit 1
  fi

  planned_cycles="$(planned_cycle_count)"
  if [ "$planned_cycles" -lt "$requested_cycles" ]; then
    echo "Repeat backlog preparation left only ${planned_cycles}/${requested_cycles} planned cycle(s)."
    echo "Review TASKS.md before continuing."
    exit 1
  fi

  echo "== Running quality gate after repeat backlog preparation =="
  bash scripts/run_quality_gate.sh

  git add TASKS.md
  git commit \
    -m "chore(agent-loop): prepare repeat backlog" \
    -m "Requested cycles: ${requested_cycles}" \
    -m "Planned cycles after preparation: ${planned_cycles}" \
    -m "Quality gate: passed"

  if [ "$PUSH_MAIN" -eq 1 ]; then
    echo "== Pushing ${MAIN_BRANCH} after repeat backlog preparation =="
    git push origin "$MAIN_BRANCH"
  fi
}

prepare_next_task() {
  local completed_task_id="$1"
  local completed_task_title="$2"
  local task_branch="$3"
  local merge_commit="$4"
  local prompt_path
  local changed_files
  local has_next_task=0
  local next_line
  local next_task_id
  local next_task_title
  local next_subject

  NEXT_TASK_PREPARED=0

  if has_backlog_task; then
    has_next_task=1
  fi

  prompt_path="$(mktemp)"
  cat > "$prompt_path" <<EOF
You are preparing TASKS.md for the next local agent-loop cycle.

Read:
- AGENTS.md
- docs/learn_the_ticker_PRD.md
- docs/learn_the_ticker_technical_design_spec.md
- docs/learn-the-ticker_proposal.md
- SPEC.md
- TASKS.md
- EVALS.md

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
4. If a Backlog task exists, promote the first Backlog task into Current task.
5. If no Backlog task exists, replace Current task with a short note that no current task is prepared and the backlog is empty. Do not invent a new task.
6. When a task is promoted, expand it into a full task contract with:
   - Goal
   - task-scope paragraph
   - Allowed files
   - Do not change
   - detailed Acceptance criteria
   - Required commands
   - Iteration budget
7. Preserve product guardrails: no investment advice, no live external calls, citations for important claims, source-use rights, PRD/TDS-first authority after safety, and freshness/unknown/stale/unavailable/partial handling.
8. Keep any promoted next task narrow enough for one agent loop.
EOF

  echo "== Preparing next task in TASKS.md =="
  set +e
  ltt_codex_exec -a never exec --sandbox workspace-write "$(cat "$prompt_path")"
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

  echo "== Running quality gate after next-task preparation =="
  bash scripts/run_quality_gate.sh

  git add TASKS.md

  if [ "$has_next_task" -eq 1 ]; then
    next_line="$(current_task_line)"
    if [ -z "$next_line" ]; then
      echo "Expected next task to be promoted from Backlog, but Current task is empty."
      exit 1
    fi

    next_task_id="$(printf '%s\n' "$next_line" | task_id_from_line)"
    next_task_title="$(printf '%s\n' "$next_line" | task_title_from_line)"
    next_subject="$(commit_subject_from_title "$next_task_title")"

    git commit \
      -m "chore(${next_task_id}): prepare ${next_subject} task" \
      -m "Previous task: ${completed_task_id}" \
      -m "Merged branch: ${task_branch}" \
      -m "Quality gate: passed"

    NEXT_TASK_PREPARED=1
  else
    git commit \
      -m "chore(${completed_task_id}): finalize task board" \
      -m "Completed task: ${completed_task_title}" \
      -m "Merged branch: ${task_branch}" \
      -m "Quality gate: passed" \
      -m "No backlog task was available to promote."
  fi
}

run_one_cycle() {
  local cycle_number="$1"
  local task_line
  local task_id
  local task_title
  local task_branch
  local merge_commit
  local agent_args=()

  require_clean_tree

  task_line="$(current_task_line)"
  if [ -z "$task_line" ]; then
    echo "Could not find a current task in TASKS.md."
    if has_backlog_task; then
      echo "Backlog tasks exist, but none is promoted. Prepare TASKS.md before running the cycle."
    else
      echo "Backlog is empty. Add a new Backlog task before running the cycle."
    fi
    exit 1
  fi

  task_id="$(printf '%s\n' "$task_line" | task_id_from_line)"
  task_title="$(printf '%s\n' "$task_line" | task_title_from_line)"

  echo "== Task cycle ${cycle_number}/${MAX_CYCLES} =="
  echo "== Current task: ${task_id}: ${task_title} =="
  echo "== Main branch: ${MAIN_BRANCH} =="
  echo "== Prepare next: ${PREPARE_NEXT} =="
  echo "== Repeat: ${REPEAT} =="
  echo "== Push main: ${PUSH_MAIN} =="

  if [ "$COMMIT_FAILURES" -eq 1 ]; then
    agent_args+=(--commit-failures)
  fi
  if [ -n "$CODEX_MODEL_OVERRIDE" ]; then
    agent_args+=(--model "$CODEX_MODEL_OVERRIDE")
  fi
  if [ -n "$CODEX_REASONING_EFFORT_OVERRIDE" ]; then
    agent_args+=(--reasoning-effort "$CODEX_REASONING_EFFORT_OVERRIDE")
  fi

  echo "== Running agent loop =="
  bash scripts/agent_loop.sh "${agent_args[@]}"

  task_branch="$(git branch --show-current)"
  if ! printf '%s\n' "$task_branch" | grep -Eq "^agent/${task_id}-"; then
    echo "Expected to be on agent/${task_id}-... after agent loop, but current branch is: $task_branch"
    exit 1
  fi

  echo "== Merging completed task branch =="
  bash scripts/local_merge_task.sh "$task_branch" --main "$MAIN_BRANCH"

  merge_commit="$(git rev-parse --short HEAD)"

  if [ "$PREPARE_NEXT" -eq 1 ]; then
    prepare_next_task "$task_id" "$task_title" "$task_branch" "$merge_commit"
  else
    NEXT_TASK_PREPARED=0
  fi

  if [ "$PUSH_MAIN" -eq 1 ]; then
    echo "== Pushing ${MAIN_BRANCH} =="
    git push origin "$MAIN_BRANCH"
  fi

  echo "== Task cycle ${cycle_number}/${MAX_CYCLES} complete =="
  git status --short
  git log --oneline -5

  if [ "$PREPARE_NEXT" -eq 1 ] && [ "$NEXT_TASK_PREPARED" -eq 1 ]; then
    return 0
  fi

  return 1
}

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# shellcheck source=scripts/activate_agent_env.sh
source "$ROOT/scripts/activate_agent_env.sh"
ltt_set_codex_preferences "$CODEX_MODEL_OVERRIDE" "$CODEX_REASONING_EFFORT_OVERRIDE"
ltt_require_codex_toolchain

ensure_repeat_backlog_capacity "$MAX_CYCLES"

CYCLE=1
while [ "$CYCLE" -le "$MAX_CYCLES" ]; do
  if run_one_cycle "$CYCLE"; then
    CAN_CONTINUE=1
  else
    CAN_CONTINUE=0
  fi

  if [ "$REPEAT" -ne 1 ]; then
    break
  fi

  if [ "$CAN_CONTINUE" -ne 1 ]; then
    echo "== Repeat stopped: no prepared next task is available. =="
    break
  fi

  CYCLE=$((CYCLE + 1))
done

if [ "$REPEAT" -eq 1 ] && [ "$CYCLE" -gt "$MAX_CYCLES" ]; then
  echo "== Repeat stopped: reached max cycles (${MAX_CYCLES}). =="
fi

echo "== Task cycle run complete =="
git status --short
git log --oneline -5
