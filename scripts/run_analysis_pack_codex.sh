#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_CODEX=1
UPLOAD_ENDPOINT=""
LIVE_MODE=1
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR=".agent-runs/analysis-packs/$RUN_ID"
TICKERS=()

if [ "${CI:-}" = "true" ] || [ "${GITHUB_ACTIONS:-}" = "true" ] || [ "${BUILDKITE:-}" = "true" ] || [ -n "${JENKINS_URL:-}" ] || [ -n "${PYTEST_CURRENT_TEST:-}" ] || [ "${LTT_STATIC_EVALS_RUNNING:-}" = "true" ] || [ "${LTT_QUALITY_GATE_RUNNING:-}" = "true" ] || [ "${ANALYSIS_PACK_DETERMINISTIC:-}" = "true" ] || [ "${LTT_ANALYSIS_PACK_DETERMINISTIC:-}" = "true" ]; then
  LIVE_MODE=0
fi

usage() {
  cat <<'EOF'
Usage: bash scripts/run_analysis_pack_codex.sh [options]

Build a structured analysis-pack import bundle and optionally let Codex review
the draft under docs/ANALYSIS_PACK_CODEX_INSTRUCTIONS.md. Local operator runs
default to live mode outside CI/tests/evals. Use --deterministic for fixture
mode.

Options:
  --ticker <TICKER>        Include a high-demand ticker. Repeat for many.
  --output-dir <PATH>      Output directory. Default: .agent-runs/analysis-packs/<utc-run-id>
  --live                   Force live local adapters for news, Economic Indicators, and technical indicators.
  --deterministic          Force fixture/no-live mode.
  --skip-codex             Build and validate artifacts without invoking Codex.
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
    --live)
      LIVE_MODE=1
      shift
      ;;
    --deterministic)
      LIVE_MODE=0
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
AI_CONTEXT_PATH="$OUTPUT_DIR/ai_context.json"
PROMPT_PATH="$OUTPUT_DIR/codex-analysis-pack-prompt.md"
CODEX_LOG_PATH="$OUTPUT_DIR/codex-final.md"

TICKER_ARGS=()
for ticker in "${TICKERS[@]}"; do
  if [ -n "$ticker" ]; then
    TICKER_ARGS+=(--ticker "$ticker")
  fi
done

LIVE_ARGS=()
if [ "$LIVE_MODE" -eq 1 ]; then
  LIVE_ARGS+=(--live)
else
  LIVE_ARGS+=(--deterministic)
fi

python3 scripts/build_analysis_pack_bundle.py \
  "${TICKER_ARGS[@]}" \
  "${LIVE_ARGS[@]}" \
  --output "$BUNDLE_PATH" \
  --summary-output "$SUMMARY_PATH" \
  --technical-output "$TECHNICAL_PATH" \
  --macro-output "$MACRO_PATH" \
  --ai-context-output "$AI_CONTEXT_PATH" \
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
- AI context artifact: $AI_CONTEXT_PATH
- Live adapters enabled: $LIVE_MODE

Stage-gated tasks:
1. Stage 0 - Technical Artifact Gate:
   Inspect the generated bundle, summary, technical_data.json, macro_cache.json, and ai_context.json before changing analysis fields.
   Use only computed technical fields from technical_data.json and ai_context.json. Never treat ADX, DMI, true range, volume, or volume-change as prices.
   Do not claim divergence, support/resistance, breakouts, or historical highs/lows unless the exact supporting fields exist in the artifacts.
2. Stage 1 - Macro Data Gate:
   Use official U.S. historical actuals only. GDP/private investment normally need a completed-quarter lag; monthly indicators must use completed official periods; jobless claims use the latest completed official week.
   Cross-check primary agency values against source metadata. Prioritize BEA, BLS, Census, Department of Labor, Federal Reserve, Treasury, ISM, Cboe/EIA or approved market-data sources as documented; FRED is a cross-check/fallback unless it is the approved market-reference path.
   Preserve macro_cache.json with upsert behavior only; do not overwrite unrelated indicators or allow suspicious count drops.
3. Stage 2 - Tier-1 News Gate:
   Follow the required U.S. market searches in docs/ANALYSIS_PACK_CODEX_INSTRUCTIONS.md: Global Macro/Fed, Geopolitical Risks, and Energy Supply & Global Shipping.
   Use only approved Tier-1 or official sources such as Reuters, AP, Bloomberg, WSJ, FT, CNBC, Barron's, BBC, CNN, official government releases, company IR, SEC filings, and ETF issuer materials.
   Keep only source-verifiable items from the last seven days. Critical claims need Reuters/AP/Bloomberg/WSJ/FT priority or corroboration from at least two approved sources. Select up to 20 items only when evidence supports them.
4. Stage 3 - AI Comprehensive Analysis Gate:
   Use internal macro/policy, business or fund-quality, technical, sentiment/flow, and scenario-synthesis lenses, but keep visible labels product-native.
   Market AI should use sections such as What Changed This Week, Macro & Policy, Equity Market Drivers, AI / Technology / Semiconductors, Geopolitical & Energy Risks, Credit / Liquidity / Sentiment, Scenario Lens, and Practical Watchpoints.
   Ticker AI should use What Changed This Week, Market Context, Business/Fund Context, and Risk Context.
   Preserve citations and source-document IDs for every important generated claim. Numeric claims must match ai_context.json allowed_numeric_facts and include a descriptive label.
   Apply the yield-curve rule and geopolitical/supply-chain warning rule from docs/ANALYSIS_PACK_CODEX_INSTRUCTIONS.md.
   Do not use fixed template prose, unsupported causal claims, predictions, price targets, or buy/sell/hold/allocation advice.
5. Stage 4 - Final Validation Gate:
   Review/augment only JSON artifacts in this output directory. Do not write HTML or repo-tracked files.
   Do not store raw article text, raw provider payloads, hidden prompts, raw model reasoning, signed URLs, tokens, or secrets.
   Keep visible labels product-native: no Atlas, Sophia, Kenji, Crow, or Rain labels in user-facing fields.
   If you modify the bundle, run:
   python3 scripts/build_analysis_pack_bundle.py --validate-only --input "$BUNDLE_PATH" --summary-output "$SUMMARY_PATH"
   Inspect reason codes and fix failures before finishing. Artifacts must stay inside $OUTPUT_DIR.
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
