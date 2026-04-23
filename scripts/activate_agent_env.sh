#!/usr/bin/env bash

# Source this file from Bash workflow scripts. It activates the local WSL conda
# environment used by the solo agent loop and provides focused preflight checks.

LTT_CONDA_ENV="${LTT_CONDA_ENV:-learn-the-ticker}"
LTT_CODEX_MODEL="${LTT_CODEX_MODEL:-gpt-5.3-codex-spark}"
LTT_CODEX_REASONING_EFFORT="${LTT_CODEX_REASONING_EFFORT:-high}"

ltt_is_wsl() {
  grep -qiE "(microsoft|wsl)" /proc/version 2>/dev/null
}

ltt_find_conda_sh() {
  local candidate

  if [ -n "${CONDA_EXE:-}" ]; then
    candidate="$(dirname "$(dirname "$CONDA_EXE")")/etc/profile.d/conda.sh"
    if [ -f "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  fi

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

ltt_activate_agent_env() {
  if [ "${LTT_SKIP_CONDA_ACTIVATE:-0}" = "1" ]; then
    return 0
  fi

  if ! ltt_is_wsl; then
    return 0
  fi

  if [ "${CONDA_DEFAULT_ENV:-}" = "$LTT_CONDA_ENV" ]; then
    return 0
  fi

  local conda_sh
  if ! conda_sh="$(ltt_find_conda_sh)"; then
    echo "WSL workflow expects conda env '$LTT_CONDA_ENV', but conda was not found." >&2
    echo "Install Miniconda in WSL, or set LTT_SKIP_CONDA_ACTIVATE=1 to manage PATH yourself." >&2
    return 1
  fi

  # shellcheck source=/dev/null
  source "$conda_sh"
  if ! conda activate "$LTT_CONDA_ENV"; then
    echo "Could not activate conda env '$LTT_CONDA_ENV'." >&2
    echo "Run: bash scripts/setup_wsl_agent_env.sh" >&2
    return 1
  fi
}

ltt_node_major() {
  node -p 'Number(process.versions.node.split(".")[0])' 2>/dev/null || printf '0\n'
}

ltt_require_frontend_toolchain() {
  if ! command -v node >/dev/null 2>&1; then
    echo "Node.js is required for frontend checks." >&2
    echo "Run: bash scripts/setup_wsl_agent_env.sh" >&2
    return 127
  fi

  local node_major
  node_major="$(ltt_node_major)"
  if [ "$node_major" -lt 18 ]; then
    echo "Node.js 18+ is required. Detected: $(node --version 2>/dev/null || echo unavailable)" >&2
    echo "Under WSL, install Node into conda env '$LTT_CONDA_ENV':" >&2
    echo "  bash scripts/setup_wsl_agent_env.sh" >&2
    return 1
  fi

  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required for frontend checks." >&2
    echo "Run: bash scripts/setup_wsl_agent_env.sh" >&2
    return 127
  fi

  case "$(command -v npm)" in
    /mnt/c/*)
      echo "npm resolves to a Windows path under WSL: $(command -v npm)" >&2
      echo "Install/use npm inside conda env '$LTT_CONDA_ENV' instead:" >&2
      echo "  bash scripts/setup_wsl_agent_env.sh" >&2
      return 1
      ;;
  esac
}

ltt_require_codex_toolchain() {
  ltt_require_frontend_toolchain || return $?

  if ! command -v codex >/dev/null 2>&1; then
    echo "Codex CLI is required for the agent loop." >&2
    echo "Run: bash scripts/setup_wsl_agent_env.sh" >&2
    return 127
  fi

  case "$(command -v codex)" in
    /mnt/c/*)
      echo "codex resolves to a Windows path under WSL: $(command -v codex)" >&2
      echo "Install/use Codex inside conda env '$LTT_CONDA_ENV' instead:" >&2
      echo "  bash scripts/setup_wsl_agent_env.sh" >&2
      return 1
      ;;
  esac

  if ! codex --version >/dev/null 2>&1; then
    echo "Codex CLI was found but could not start in this shell." >&2
    echo "Run: bash scripts/setup_wsl_agent_env.sh" >&2
    return 1
  fi
}

ltt_codex_exec() {
  codex \
    -m "$LTT_CODEX_MODEL" \
    -c "reasoning.effort=\"$LTT_CODEX_REASONING_EFFORT\"" \
    "$@"
}

ltt_activate_agent_env
