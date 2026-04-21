#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${LTT_CONDA_ENV:-learn-the-ticker}"

find_conda_sh() {
  local candidate
  for candidate in \
    "$HOME/miniconda3/etc/profile.d/conda.sh" \
    "$HOME/anaconda3/etc/profile.d/conda.sh" \
    "/opt/conda/etc/profile.d/conda.sh"; do
    if [ -f "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  if command -v conda >/dev/null 2>&1; then
    candidate="$(conda info --base 2>/dev/null)/etc/profile.d/conda.sh"
    if [ -f "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  fi

  return 1
}

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

CONDA_SH="$(find_conda_sh || true)"
if [ -z "$CONDA_SH" ]; then
  echo "Could not find conda in WSL. Install Miniconda first, then rerun this script."
  exit 1
fi

# shellcheck source=/dev/null
source "$CONDA_SH"

if ! conda env list | awk '{print $1}' | grep -Fxq "$ENV_NAME"; then
  echo "Creating conda env: $ENV_NAME"
  conda create -y -n "$ENV_NAME" --override-channels -c conda-forge python=3.12 nodejs=22
else
  echo "Using existing conda env: $ENV_NAME"
  conda install -y -n "$ENV_NAME" --override-channels -c conda-forge nodejs=22
fi

conda activate "$ENV_NAME"

echo "== Installing Python dependencies =="
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
if [ -f requirements.txt ]; then
  python -m pip install -r requirements.txt
fi

echo "== Installing frontend dependencies =="
npm ci

echo "== Installing Codex CLI into the conda env =="
npm install -g @openai/codex

echo "== Toolchain =="
python --version
node --version
npm --version
codex --version

echo "WSL agent environment is ready."
