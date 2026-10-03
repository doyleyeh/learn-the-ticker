#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python_command="${PYTHON:-python3}"
if [ -x .venv/bin/python ]; then python_command=.venv/bin/python; fi
"$python_command" -m pytest tests -q
"$python_command" evals/run_static_evals.py
npm test
npm run typecheck
npm run build
