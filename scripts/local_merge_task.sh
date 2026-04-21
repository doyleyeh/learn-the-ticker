#!/usr/bin/env bash
set -euo pipefail

MAIN_BRANCH="main"
BRANCH=""

usage() {
  cat <<'EOF'
Usage: bash scripts/local_merge_task.sh [branch] [--main main]

Merges a completed agent/T-... task branch into main for solo local workflow.
The script runs the quality gate on the task branch, prepares a no-commit merge,
runs the quality gate again on the merged result, then creates the merge commit.
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
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [ -n "$BRANCH" ]; then
        echo "Only one task branch may be provided."
        usage
        exit 2
      fi
      BRANCH="$1"
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

task_id_from_branch() {
  printf '%s\n' "$1" | sed -nE 's#(^|.*/)agent/(T-[0-9]+)-.*#\2#p'
}

task_title_from_tasks() {
  local task_id="$1"
  sed -nE "s/^###[[:space:]]+${task_id}:[[:space:]]*(.+)$/\1/p" TASKS.md | head -n1
}

merge_subject_from_title() {
  local title="$1"
  local subject

  subject="$(printf '%s%s' "$(printf '%s' "$title" | cut -c1 | tr '[:upper:]' '[:lower:]')" "$(printf '%s' "$title" | cut -c2-)")"
  subject="$(printf '%s\n' "$subject" | sed -E 's/^(add|create|implement|update)[[:space:]]+//')"
  printf 'merge %s\n' "$subject"
}

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# shellcheck source=scripts/activate_agent_env.sh
source "$ROOT/scripts/activate_agent_env.sh"

command -v bash >/dev/null 2>&1 || {
  echo "bash is required."
  exit 127
}

require_clean_tree

if [ -z "$BRANCH" ]; then
  BRANCH="$(git branch --show-current)"
fi

if [ -z "$BRANCH" ]; then
  echo "Could not determine the current branch. Pass the task branch explicitly."
  exit 1
fi

TASK_ID="$(task_id_from_branch "$BRANCH")"
if [ -z "$TASK_ID" ]; then
  echo "Branch '$BRANCH' does not look like an agent task branch: agent/T-000-..."
  exit 1
fi

TASK_TITLE="$(task_title_from_tasks "$TASK_ID")"
if [ -z "$TASK_TITLE" ]; then
  echo "Could not find a TASKS.md heading for $TASK_ID."
  exit 1
fi

MERGE_SUBJECT="$(merge_subject_from_title "$TASK_TITLE")"
MERGE_MESSAGE="chore(${TASK_ID}): ${MERGE_SUBJECT}"
CURRENT_BRANCH="$(git branch --show-current)"

echo "== Local task merge =="
echo "== Task branch: $BRANCH =="
echo "== Main branch: $MAIN_BRANCH =="
echo "== Merge message: $MERGE_MESSAGE =="

git rev-parse --verify "${BRANCH}^{commit}" >/dev/null
git rev-parse --verify "${MAIN_BRANCH}^{commit}" >/dev/null

if [ "$BRANCH" = "$MAIN_BRANCH" ]; then
  echo "Task branch and main branch are the same."
  exit 1
fi

if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
  git switch "$BRANCH"
fi

require_clean_tree

echo "== Running quality gate on $BRANCH =="
bash scripts/run_quality_gate.sh

git switch "$MAIN_BRANCH"
require_clean_tree

if git merge-base --is-ancestor "$BRANCH" "$MAIN_BRANCH"; then
  echo "$BRANCH is already merged into $MAIN_BRANCH."
  exit 0
fi

echo "== Preparing no-commit merge =="
if ! git merge --no-ff --no-commit "$BRANCH"; then
  echo "Merge stopped before commit, likely because of conflicts."
  echo "Resolve conflicts and commit manually, or run: git merge --abort"
  exit 1
fi

echo "== Running quality gate on merged result =="
if ! bash scripts/run_quality_gate.sh; then
  echo "Quality gate failed on the uncommitted merge result."
  echo "Inspect the working tree. To cancel this merge, run: git merge --abort"
  exit 1
fi

echo "== Creating merge commit =="
git commit \
  -m "$MERGE_MESSAGE" \
  -m "Merged local branch: $BRANCH" \
  -m "Quality gate: passed"

echo "== Final status =="
git status --short
git log --oneline -5
