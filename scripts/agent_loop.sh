#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if ! command -v codex >/dev/null 2>&1; then
  echo "Codex CLI is required. Install it or add it to PATH before running the agent loop."
  exit 127
fi

if command -v node >/dev/null 2>&1; then
  NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])' 2>/dev/null || echo 0)"
else
  NODE_MAJOR=0
fi

if [ "$NODE_MAJOR" -lt 18 ]; then
  echo "Codex CLI requires a modern Node.js runtime in this shell."
  echo "Detected Node major version: $NODE_MAJOR"
  echo "Use Node 18+ in Bash/WSL, or run scripts/agent_loop.ps1 from PowerShell where Codex already works."
  exit 1
fi

if ! codex --version >/dev/null 2>&1; then
  echo "Codex CLI was found but could not start. Check the Node.js runtime used by this shell."
  exit 1
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
TASK_LINE="$(grep -m1 '^### T-' TASKS.md || true)"

if [ -z "$TASK_LINE" ]; then
  TASK_ID="T-unknown"
else
  TASK_ID="$(echo "$TASK_LINE" | sed -E 's/^### ([^: ]+).*/\1/')"
fi

BRANCH="agent/${TASK_ID}-${RUN_ID}"

echo "== Agent run: $RUN_ID =="
echo "== Task: $TASK_ID =="
echo "== Branch: $BRANCH =="

if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree is not clean. Commit or stash your changes first."
  git status --short
  exit 1
fi

git checkout -b "$BRANCH"

mkdir -p ".agent-runs/$RUN_ID"
mkdir -p "docs/agent-journal"

cat > ".agent-runs/$RUN_ID/prompt.txt" <<EOF
You are working on this repository as a coding agent.

First read:
- AGENTS.md
- SPEC.md
- TASKS.md
- EVALS.md
- docs/learn_the_ticker_PRD.md if present
- docs/learn_the_ticker_technical_design_spec.md if present

Work only on the current task in TASKS.md.

Rules:
- Do not run git commit.
- Do not run git push.
- Do not run git reset --hard.
- Do not run git clean -fd.
- Do not change unrelated files.
- Keep changes small.
- Run the required tests/evals from EVALS.md.
- If tests fail, make one focused revision and run them again.
- Stop after the iteration budget in TASKS.md.

Before finishing, write a concise Markdown summary to:
docs/agent-journal/${RUN_ID}.md

The summary must include:
- task id
- files changed
- tests/evals run
- pass/fail status
- remaining risks
EOF

echo "== Running Codex =="
codex exec \
  --sandbox workspace-write \
  --ask-for-approval never \
  "$(cat ".agent-runs/$RUN_ID/prompt.txt")" \
  | tee ".agent-runs/$RUN_ID/codex-final.md"

echo "== Running quality gate =="
set +e
bash scripts/run_quality_gate.sh > ".agent-runs/$RUN_ID/quality-gate.log" 2>&1
QUALITY_STATUS=$?
set -e

cat ".agent-runs/$RUN_ID/quality-gate.log"

echo "== Capturing Git status =="
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

See local ignored logs:

- .agent-runs/${RUN_ID}/codex-final.md
- .agent-runs/${RUN_ID}/quality-gate.log
- .agent-runs/${RUN_ID}/diff.patch
EOF
fi

git add -A

if git diff --cached --quiet; then
  echo "No changes to commit."
  exit "$QUALITY_STATUS"
fi

if [ "$QUALITY_STATUS" -eq 0 ]; then
  git commit \
    -m "agent(${TASK_ID}): implement current task" \
    -m "Run ID: ${RUN_ID}" \
    -m "Quality gate: passed"
else
  git commit \
    -m "wip(${TASK_ID}): agent attempt with failing quality gate" \
    -m "Run ID: ${RUN_ID}" \
    -m "Quality gate: failed. Review before merge."
fi

echo "== Final status =="
git status --short
git log --oneline -5

exit "$QUALITY_STATUS"
