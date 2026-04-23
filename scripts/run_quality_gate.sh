#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/activate_agent_env.sh
source "$ROOT/scripts/activate_agent_env.sh"

if [ -n "${PYTHON:-}" ]; then
  PYTHON_BIN="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python is required, but neither python3 nor python was found on PATH."
  exit 127
fi

echo "== Quality gate started =="
if [ -n "${CONDA_DEFAULT_ENV:-}" ]; then
  echo "== Conda env: ${CONDA_DEFAULT_ENV} =="
fi
echo "== Python: $($PYTHON_BIN --version) =="

export PYTHONDONTWRITEBYTECODE=1

run_pytest() {
  if "$PYTHON_BIN" -c "import pytest" >/dev/null 2>&1; then
    "$PYTHON_BIN" -m pytest "$@"
  else
    echo "pytest is not installed; using scripts/mini_pytest.py fallback."
    "$PYTHON_BIN" scripts/mini_pytest.py "$@"
  fi
}

echo "== Python tests =="
run_pytest tests -q

echo "== Static evals =="
if "$PYTHON_BIN" -c "import yaml" >/dev/null 2>&1; then
  "$PYTHON_BIN" evals/run_static_evals.py
else
  echo "PyYAML is not installed; using scripts/yaml.py fallback."
  PYTHONPATH="$ROOT/scripts${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" evals/run_static_evals.py
fi

if [ -f package.json ]; then
  echo "== Frontend checks =="
  ltt_require_frontend_toolchain
  if [ -f apps/web/package.json ]; then
    echo "== Frontend workspace: apps/web =="
  fi
  npm run lint --if-present
  npm run test --if-present
  npm run typecheck --if-present
  npm run build --if-present
fi

if [ -d backend ]; then
  echo "== Backend checks =="
  run_pytest backend tests -q
fi

echo "== Quality gate passed =="
