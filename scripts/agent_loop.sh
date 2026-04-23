#!/usr/bin/env bash
set -euo pipefail

COMMIT_FAILURES=0

usage() {
  cat <<'EOF'
Usage: bash scripts/agent_loop.sh [--commit-failures]

Runs the current TASKS.md task through Codex, the quality gate, and retry
attempts up to the iteration budget. Passing runs are committed. Failing runs
are left uncommitted by default for review.

Options:
  --commit-failures  Commit the final failing attempt as a WIP audit commit.
  -h, --help         Show this help.
EOF
}

current_task_line() {
  awk '
    /^## Current task/ { in_current = 1; next }
    in_current && /^## / { exit }
    in_current && /^### T-/ { print; exit }
  ' TASKS.md
}

ensure_agent_branch() {
  local context="$1"
  local current_branch
  local current_head

  current_branch="$(git branch --show-current || true)"
  if [ "$current_branch" = "$BRANCH" ]; then
    return 0
  fi

  current_head="$(git rev-parse --short HEAD)"
  echo "Branch drift detected during ${context}: expected ${BRANCH}, current branch is ${current_branch:-detached} at ${current_head}."

  if [ -n "$(git status --porcelain)" ]; then
    echo "Attempting to return to ${BRANCH} while preserving uncommitted attempt changes."
    if git switch "$BRANCH"; then
      current_branch="$(git branch --show-current || true)"
      if [ "$current_branch" = "$BRANCH" ]; then
        return 0
      fi
    fi
  fi

  echo "Could not safely recover the expected agent branch."
  echo "The attempt may have changed branches or committed on the wrong branch. Review git status before continuing."
  return 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --commit-failures)
      COMMIT_FAILURES=1
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

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# shellcheck source=scripts/activate_agent_env.sh
source "$ROOT/scripts/activate_agent_env.sh"
ltt_require_codex_toolchain

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
TASK_LINE="$(current_task_line)"

if [ -z "$TASK_LINE" ]; then
  TASK_ID="T-unknown"
  TASK_TITLE="current task"
else
  TASK_ID="$(echo "$TASK_LINE" | sed -E 's/^### ([^: ]+).*/\1/')"
  TASK_TITLE="$(echo "$TASK_LINE" | sed -E 's/^### [^: ]+:[[:space:]]*//')"
fi

if [ -z "$TASK_TITLE" ] || [ "$TASK_TITLE" = "$TASK_LINE" ]; then
  TASK_TITLE="current task"
fi

TASK_TITLE_LOWER="$(printf '%s' "$TASK_TITLE" | tr '[:upper:]' '[:lower:]')"
if printf '%s' "$TASK_TITLE_LOWER" | grep -Eq '(^|[^[:alnum:]])fix(es|ed)?([^[:alnum:]]|$)'; then
  COMMIT_TYPE="fix"
elif printf '%s' "$TASK_TITLE_LOWER" | grep -Eq '(^|[^[:alnum:]])(test|tests|eval|evals)([^[:alnum:]]|$)'; then
  COMMIT_TYPE="test"
elif printf '%s' "$TASK_TITLE_LOWER" | grep -Eq '(^|[^[:alnum:]])(doc|docs|documentation)([^[:alnum:]]|$)'; then
  COMMIT_TYPE="docs"
elif printf '%s' "$TASK_TITLE_LOWER" | grep -Eq '(^|[^[:alnum:]])(scaffold|prepare|setup|chore)([^[:alnum:]]|$)'; then
  COMMIT_TYPE="chore"
elif printf '%s' "$TASK_TITLE_LOWER" | grep -Eq '(^|[^[:alnum:]])refactor([^[:alnum:]]|$)'; then
  COMMIT_TYPE="refactor"
else
  COMMIT_TYPE="feat"
fi

TASK_COMMIT_SUBJECT="$(printf '%s%s' "$(printf '%s' "$TASK_TITLE" | cut -c1 | tr '[:upper:]' '[:lower:]')" "$(printf '%s' "$TASK_TITLE" | cut -c2-)")"

ITERATION_BUDGET="$(sed -nE 's/.*Max[[:space:]]+([0-9]+).*/\1/p' TASKS.md | head -n1)"
if [ -z "$ITERATION_BUDGET" ]; then
  ITERATION_BUDGET=3
fi

BRANCH="agent/${TASK_ID}-${RUN_ID}"
REAL_GIT="$(command -v git)"
AGENT_GIT_WRAPPER_DIR=".agent-runs/$RUN_ID/bin"

echo "== Agent run: $RUN_ID =="
echo "== Task: $TASK_ID =="
echo "== Task title: $TASK_TITLE =="
echo "== Branch: $BRANCH =="
echo "== Codex model: ${LTT_CODEX_MODEL} =="
echo "== Codex reasoning effort: ${LTT_CODEX_REASONING_EFFORT} =="
echo "== Commit subject: ${COMMIT_TYPE}(${TASK_ID}): ${TASK_COMMIT_SUBJECT} =="
echo "== Iteration budget: $ITERATION_BUDGET =="

if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree is not clean. Commit or stash your changes first."
  git status --short
  exit 1
fi

git checkout -b "$BRANCH"

mkdir -p ".agent-runs/$RUN_ID"
mkdir -p "docs/agent-journal"
mkdir -p "$AGENT_GIT_WRAPPER_DIR"

cat > "$AGENT_GIT_WRAPPER_DIR/git" <<EOF
#!/usr/bin/env bash
case "\${1:-}" in
  checkout|switch|commit|push|merge|rebase|reset|clean)
    echo "agent_loop blocks 'git \${1:-}' inside Codex attempts; leave branch, commit, merge, and push operations to the harness." >&2
    exit 2
    ;;
esac
exec "$REAL_GIT" "\$@"
EOF
chmod +x "$AGENT_GIT_WRAPPER_DIR/git"

QUALITY_STATUS=1
CODEX_STATUS=0

for ATTEMPT in $(seq 1 "$ITERATION_BUDGET"); do
  ATTEMPT_DIR=".agent-runs/$RUN_ID/attempt-$ATTEMPT"
  mkdir -p "$ATTEMPT_DIR"

  RETRY_CONTEXT=""
  if [ "$ATTEMPT" -gt 1 ]; then
    PREVIOUS_ATTEMPT=$((ATTEMPT - 1))
    RETRY_CONTEXT="
This is retry attempt ${ATTEMPT} of ${ITERATION_BUDGET}.
The previous attempt did not pass. Inspect these local logs before editing:
- .agent-runs/${RUN_ID}/attempt-${PREVIOUS_ATTEMPT}/codex-final.md
- .agent-runs/${RUN_ID}/attempt-${PREVIOUS_ATTEMPT}/quality-gate.log
- .agent-runs/${RUN_ID}/attempt-${PREVIOUS_ATTEMPT}/diff.patch
"
  fi

  cat > "$ATTEMPT_DIR/prompt.txt" <<EOF
You are working on this repository as a coding agent.

This is attempt ${ATTEMPT} of ${ITERATION_BUDGET}.

First read:
- AGENTS.md
- docs/learn_the_ticker_PRD.md
- docs/learn_the_ticker_technical_design_spec.md
- docs/learn-the-ticker_proposal.md
- SPEC.md
- TASKS.md
- EVALS.md

Work only on the current task in TASKS.md.

Rules:
- Follow safety and advice-boundary rules first, then the updated PRD, technical design spec, proposal, SPEC, TASKS, and EVALS in that order.
- Leave changes uncommitted for the harness commit step after the quality gate.
- Stay on the current agent branch; do not run git switch or git checkout.
- Do not push from inside a Codex attempt.
- Do not run git commit.
- Do not run git merge.
- Do not run git reset --hard.
- Do not run git clean -fd.
- Do not change unrelated files.
- Keep changes small.
- Run the required tests/evals from EVALS.md.
- If tests fail, make one focused revision and run them again.
- Stop after the iteration budget in TASKS.md.
${RETRY_CONTEXT}

Before finishing, write a concise Markdown summary to:
docs/agent-journal/${RUN_ID}.md

The summary must include:
- task id
- files changed
- tests/evals run
- pass/fail status
- remaining risks
EOF

  echo "== Running Codex attempt $ATTEMPT/$ITERATION_BUDGET =="
  set +e
  PATH="$ROOT/$AGENT_GIT_WRAPPER_DIR:$PATH" ltt_codex_exec -a never exec \
    --sandbox workspace-write \
    "$(cat "$ATTEMPT_DIR/prompt.txt")" \
    | tee "$ATTEMPT_DIR/codex-final.md"
  CODEX_STATUS=$?
  set -e

  if [ "$CODEX_STATUS" -ne 0 ]; then
    echo "Codex exited with status $CODEX_STATUS."
    echo "Quality gate skipped because Codex exited with status $CODEX_STATUS." > "$ATTEMPT_DIR/quality-gate.log"
    QUALITY_STATUS=$CODEX_STATUS
  elif ! ensure_agent_branch "attempt ${ATTEMPT}"; then
    echo "Quality gate skipped because the Codex attempt did not leave the repo on ${BRANCH}." > "$ATTEMPT_DIR/quality-gate.log"
    QUALITY_STATUS=1
  else
    echo "== Running quality gate for attempt $ATTEMPT/$ITERATION_BUDGET =="
    set +e
    bash scripts/run_quality_gate.sh > "$ATTEMPT_DIR/quality-gate.log" 2>&1
    QUALITY_STATUS=$?
    set -e

    cat "$ATTEMPT_DIR/quality-gate.log"
  fi

  echo "== Capturing Git status for attempt $ATTEMPT/$ITERATION_BUDGET =="
  git status --short | tee "$ATTEMPT_DIR/git-status.txt"
  git diff > "$ATTEMPT_DIR/diff.patch" || true

  if [ "$QUALITY_STATUS" -eq 0 ]; then
    echo "== Quality gate passed on attempt $ATTEMPT/$ITERATION_BUDGET =="
    break
  fi

  if [ "$ATTEMPT" -lt "$ITERATION_BUDGET" ]; then
    echo "== Quality gate failed; retrying with diagnostics from attempt $ATTEMPT =="
  fi
done

echo "== Capturing final Git status =="
git status --short | tee ".agent-runs/$RUN_ID/git-status.txt"
git diff > ".agent-runs/$RUN_ID/diff.patch" || true

if [ ! -f "docs/agent-journal/${RUN_ID}.md" ]; then
  cat > "docs/agent-journal/${RUN_ID}.md" <<EOF
# Agent run ${RUN_ID}

Task: ${TASK_ID}

## Result

Codex completed a run, but did not create a detailed journal entry.

## Quality gate

Exit status: ${QUALITY_STATUS}
Iteration budget: ${ITERATION_BUDGET}

See local ignored logs:

- .agent-runs/${RUN_ID}/attempt-*/codex-final.md
- .agent-runs/${RUN_ID}/attempt-*/quality-gate.log
- .agent-runs/${RUN_ID}/diff.patch
EOF
fi

if [ "$QUALITY_STATUS" -ne 0 ] && [ "$COMMIT_FAILURES" -ne 1 ]; then
  echo "Quality gate failed after ${ITERATION_BUDGET} attempt(s)."
  echo "Leaving changes uncommitted and unstaged for review."
  echo "Rerun with --commit-failures to create a WIP audit commit."
  exit "$QUALITY_STATUS"
fi

ensure_agent_branch "final commit"

git add -A

if git diff --cached --quiet; then
  echo "No changes to commit."
  exit "$QUALITY_STATUS"
fi

if [ "$QUALITY_STATUS" -eq 0 ]; then
  git commit \
    -m "${COMMIT_TYPE}(${TASK_ID}): ${TASK_COMMIT_SUBJECT}" \
    -m "Run ID: ${RUN_ID}" \
    -m "Quality gate: passed"
else
  git commit \
    -m "chore(${TASK_ID}): record failed ${TASK_COMMIT_SUBJECT} attempt" \
    -m "Run ID: ${RUN_ID}" \
    -m "Quality gate: failed. Review before merge."
fi

echo "== Final status =="
git status --short
git log --oneline -5

exit "$QUALITY_STATUS"
