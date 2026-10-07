#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
python_command="${PYTHON:-python3}"
if [ -x .venv/bin/python ]; then python_command=.venv/bin/python; elif [ -f .venv/Scripts/python.exe ]; then python_command=.venv/Scripts/python.exe; fi
exec "$python_command" -m scripts.verify full "$@"
