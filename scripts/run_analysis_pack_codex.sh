#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_CODEX=1
UPLOAD_ENDPOINT=""
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR=".agent-runs/analysis-packs/$RUN_ID"
TICKERS=()

usage() {
  cat <<'EOF'
Usage: bash scripts/run_analysis_pack_codex.sh [options]

Build a structured analysis-pack import bundle and optionally let Codex review
the draft under docs/ANALYSIS_PACK_CODEX_INSTRUCTIONS.md.

Options:
  --ticker <TICKER>        Include a high-demand ticker. Repeat for many.
  --output-dir <PATH>      Output directory. Default: .agent-runs/analysis-packs/<utc-run-id>
  --skip-codex             Build and validate deterministic artifacts only.
  --upload-endpoint <URL>  Upload the final bundle after validation.
  -h, --help               Show this help.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --ticker)
      TICKERS+=("${2:-}")
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --skip-codex)
      RUN_CODEX=0
      shift
      ;;
    --upload-endpoint)
      UPLOAD_ENDPOINT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

source scripts/activate_agent_env.sh

mkdir -p "$OUTPUT_DIR"
BUNDLE_PATH="$OUTPUT_DIR/analysis-pack-bundle.json"
SUMMARY_PATH="$OUTPUT_DIR/analysis-pack-summary.json"
TECHNICAL_PATH="$OUTPUT_DIR/technical_data.json"
MACRO_PATH="$OUTPUT_DIR/macro_cache.json"
PROMPT_PATH="$OUTPUT_DIR/codex-analysis-pack-prompt.md"
CODEX_LOG_PATH="$OUTPUT_DIR/codex-final.md"

TICKER_ARGS=()
for ticker in "${TICKERS[@]}"; do
  if [ -n "$ticker" ]; then
    TICKER_ARGS+=(--ticker "$ticker")
  fi
done

python3 scripts/build_analysis_pack_bundle.py \
  "${TICKER_ARGS[@]}" \
  --output "$BUNDLE_PATH" \
  --summary-output "$SUMMARY_PATH" \
  --technical-output "$TECHNICAL_PATH" \
  --macro-output "$MACRO_PATH" \
  --print-summary

cat > "$PROMPT_PATH" <<EOF
You are preparing a Learn the Ticker analysis pack import bundle.

Read and follow:
- AGENTS.md
- docs/ANALYSIS_PACK_CODEX_INSTRUCTIONS.md
- docs/ANALYSIS_PACK_OPERATOR_GUIDE.md
- docs/learn_the_ticker_PRD.md
- docs/learn_the_ticker_technical_design_spec.md

Working files for this run:
- Bundle: $BUNDLE_PATH
- Summary: $SUMMARY_PATH
- Technical artifact: $TECHNICAL_PATH
- Macro artifact: $MACRO_PATH

Tasks:
1. Inspect the generated bundle and summary.
2. Keep output as structured JSON only. Do not write HTML.
3. Do not store raw article text, raw provider payloads, hidden prompts, raw model reasoning, or secrets.
4. Keep visible labels product-native: no Atlas, Sophia, Kenji, Crow, or Rain labels in user-facing fields.
5. Preserve citations and source-document IDs for every important generated claim.
6. If you modify the bundle, run:
   python3 scripts/build_analysis_pack_bundle.py --validate-only --input "$BUNDLE_PATH" --summary-output "$SUMMARY_PATH"
7. Leave repo-tracked files unchanged. Artifacts must stay inside $OUTPUT_DIR.
EOF

if [ "$RUN_CODEX" -eq 1 ]; then
  ltt_require_codex_toolchain
  ltt_codex_exec -a never exec --sandbox workspace-write "$(cat "$PROMPT_PATH")" | tee "$CODEX_LOG_PATH"
fi

python3 scripts/build_analysis_pack_bundle.py \
  --validate-only \
  --input "$BUNDLE_PATH" \
  --summary-output "$SUMMARY_PATH" \
  --print-summary

if [ -n "$UPLOAD_ENDPOINT" ]; then
  python3 scripts/upload_analysis_pack_bundle.py \
    --bundle "$BUNDLE_PATH" \
    --endpoint "$UPLOAD_ENDPOINT"
fi

echo "Analysis pack artifacts written to $OUTPUT_DIR"
