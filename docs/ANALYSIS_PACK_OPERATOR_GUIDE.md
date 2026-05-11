# Analysis Pack Operator Guide

This guide explains the Codex-assisted analysis pack flow for Learn the Ticker.
The current implementation supports structured JSON import through the backend,
local live-by-default operator adapters, optional backend-owned durable bundle
storage through `ANALYSIS_PACK_REPOSITORY_PATH`, and append-only import history.

It does not yet support cryptographic signed-bundle verification, production
admin auth hardening, rollback controls, or a cloud-native database/object-store
adapter beyond the file-backed durable store. Those are future hardening items
for a broader production deployment.

## Current Pipeline

The analysis pack path is a structured-data workflow, not an HTML injection
workflow.

1. A local operator or local Codex workflow prepares an
   `analysis-pack-import-bundle-v1` JSON object.
2. The backend imports the bundle through `POST /api/admin/analysis-packs/import`.
3. The backend validates schema version, validator version, checksum, freshness,
   source-use policy, citation/source IDs, raw payload guards, secret-like values,
   visible persona labels, and required U.S. Economic Indicators rows.
4. If `ANALYSIS_PACK_REPOSITORY_PATH` or `LTT_ANALYSIS_PACK_REPOSITORY_PATH` is
   set before backend startup, the accepted bundle is also written to a durable
   backend-owned JSON store and can be reloaded after process restart. The same
   import appends a safe JSONL history record beside the active store.
5. Runtime routes read a fresh imported pack first. If the imported pack is
   missing, invalid, expired, or outside the ticker allowlist, the backend falls
   back to the existing deterministic/runtime generation path.

Affected runtime routes:

```text
GET  /api/economic-indicators
GET  /api/market-news
GET  /api/assets/{ticker}/weekly-news
POST /api/admin/analysis-packs/import
```

Current imported bundle contents may include:

- `economic_indicators`: `economic-indicators-pack-v1`
- `market_context_pack`: reusable market-wide `MarketNewsResponse`
- `ticker_packs`: optional high-demand ticker `WeeklyNewsResponse` entries
- source documents, citations, validation metadata, checksums, `prompt_version`,
  `generated_at`, and `freshness_expires_at`
- `ai_context.json` metadata and checksum in `validation_metadata`

Imported packs are fresh only while both conditions hold:

- the bundle is no more than 7 days old
- current time is before `freshness_expires_at`

## Local Commands

Start the backend with the repo's normal local backend command. One simple local
example is:

```bash
uvicorn backend.main:app --reload
```

Start the backend with durable imported-pack storage:

```bash
ANALYSIS_PACK_REPOSITORY_PATH=/tmp/learn-the-ticker-analysis-pack-store.json \
uvicorn backend.main:app --reload
```

Build a live producer artifact set without invoking Codex. This is the local
operator default outside CI/tests/evals:

```bash
bash scripts/run_analysis_pack_codex.sh \
  --skip-codex \
  --ticker QQQ \
  --ticker VOO
```

This writes the following files under `.agent-runs/analysis-packs/<run-id>/`:

- `analysis-pack-bundle.json`
- `analysis-pack-summary.json`
- `technical_data.json`
- `macro_cache.json`
- `ai_context.json`

Build a deterministic producer artifact set without invoking Codex:

```bash
bash scripts/run_analysis_pack_codex.sh \
  --deterministic \
  --skip-codex \
  --ticker QQQ \
  --ticker VOO
```

Live mode uses server-side adapters only:

- Market News: RSS, Google News RSS, GDELT, Yahoo Finance search, and optional
  keyed providers when configured.
- Ticker Weekly News: official/provider/Yahoo metadata through the lightweight
  weekly-news adapter.
- Economic Indicators: FRED CSV time-series records for U.S. official
  historical actuals and source-labeled market references.
- Technical data: Yahoo chart OHLCV metadata, then computed KD, RSI, MACD,
  BIAS, DMI/ADX, moving averages, and volume change.

Live mode stores computed values, source metadata, bounded summaries, citations,
and checksums only. It does not store raw article bodies, unrestricted provider
payloads, hidden prompts, raw model reasoning, or secrets.

Run the Codex-assisted operator flow. This builds live seed artifacts first,
then asks Codex to review and improve the JSON artifacts under the documented
research-reviewer rules:

```bash
bash scripts/run_analysis_pack_codex.sh \
  --ticker QQQ \
  --ticker VOO
```

The script builds initial artifacts, gives Codex the instructions in
`docs/ANALYSIS_PACK_CODEX_INSTRUCTIONS.md`, and validates the final bundle.
Codex must leave repo-tracked files unchanged and keep generated artifacts under
`.agent-runs/analysis-packs/...`. It should review Tier-1 market news, official
macro source metadata, Economic Indicators, technical indicators, and AI
analysis context, but it must not store raw article bodies or raw provider
payloads.

The local Codex prompt embeds the same stage gates as the instruction doc:
Technical Artifact Gate, Macro Data Gate, Tier-1 News Gate, AI Comprehensive
Analysis Gate, and Final Validation Gate. Operators should treat a run as
incomplete if Codex changes JSON without re-running validate-only and inspecting
the updated summary reason codes.

Generate a fixture-shaped bundle for local import testing:

```bash
python3 - <<'PY' > /tmp/analysis-pack-fixture.json
import json
from backend.analysis_packs import build_fixture_analysis_pack_import_bundle

bundle = build_fixture_analysis_pack_import_bundle(
    bundle_id="local-fixture-2026-05-10",
    generated_at="2026-05-10T12:00:00Z",
    freshness_expires_at="2026-05-17T12:00:00Z",
    ticker="QQQ",
)
print(json.dumps(bundle.model_dump(mode="json"), indent=2))
PY
```

Import the bundle:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/admin/analysis-packs/import \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/analysis-pack-fixture.json
```

Or upload a generated bundle with local validation first:

```bash
python3 scripts/upload_analysis_pack_bundle.py \
  --bundle .agent-runs/analysis-packs/<run-id>/analysis-pack-bundle.json
```

Verify route behavior:

```bash
curl -sS http://127.0.0.1:8000/api/economic-indicators
curl -sS http://127.0.0.1:8000/api/market-news
curl -sS http://127.0.0.1:8000/api/assets/QQQ/weekly-news
```

Expected local behavior after a successful import:

- `/api/economic-indicators` returns imported local-pack metadata.
- `/api/market-news` returns imported local-pack metadata.
- `/api/assets/QQQ/weekly-news` returns imported local-pack metadata.
- unsupported or non-allowlisted ticker packs are ignored or fall back.

## Producer Artifacts

`analysis-pack-bundle.json` is the only artifact accepted by the backend import
endpoint. The other artifacts are operator diagnostics:

- `analysis-pack-summary.json` reports included tickers, skipped tickers,
  validation status, source/citation counts, source mode, live/fixture status,
  technical-indicator status, and remaining limitations.
- `technical_data.json` computes KD, RSI, MACD, BIAS, DMI/ADX, moving averages,
  and volume-change fields in live mode. Deterministic mode still reserves
  those fields without live fetching.
- `macro_cache.json` mirrors the U.S. Economic Indicators pack in an upsert-safe
  cache shape. Existing rows are preserved, newer validated rows are updated,
  and suspicious count drops are blocked.
- `ai_context.json` is the validated context that market and ticker AI analysis
  may cite. It contains selected news, Economic Indicators, technical facts,
  canonical citation/source IDs, and allowed numeric facts.

The current producer can assemble Market News Focus, Market AI, high-demand
ticker Weekly News Focus, ticker AI, Economic Indicators, and technical
indicator diagnostics. Live adapters are operator-approved runtime paths, not
normal CI behavior.

## Ticker Pack Scope

The current local upload path is intentionally high-demand only.

Current allowlist:

```text
AAPL, MSFT, NVDA, AMZN, GOOGL, VOO, QQQ, SPY, VTI, IVV, XLK
```

Recommended cloud rollout limits:

- Start with the existing 11-ticker seed.
- Expand to around 25 tickers only after the operator workflow is smooth.
- Treat 50 tickers as the practical hard cap for this local upload path.
- Do not use local upload for 500 stocks plus 500 ETFs.

Bundle size is usually not the main constraint when raw article text and raw
provider payloads are prohibited. The larger operational risks are validation
time, review quality, partial failure handling, multi-instance consistency,
rollback, audit history, and operator mistakes.

For broad coverage, use backend workers and durable storage rather than one
large local upload bundle.

## Current Limitations

The current implementation is suitable for local validation and development
contract testing, but it is not production-complete.

Current limitations:

- Imported bundles are in-memory unless `ANALYSIS_PACK_REPOSITORY_PATH` or
  `LTT_ANALYSIS_PACK_REPOSITORY_PATH` is configured before backend startup.
- The durable implementation is file-backed JSON. It is enough for local runs,
  a mounted private volume, or a simple object-store bridge, but it is not a
  full cloud database implementation.
- Multi-instance cloud deployments need shared storage or a DB-backed adapter.
- Validation uses a deterministic checksum, not cryptographic signature
  verification. This is intentional for MVP/v1 because the data is not
  confidential, but it is not a malicious-actor security boundary.
- The admin import endpoint does not yet include production auth hardening. For
  MVP/v1 personal deployment, keep it local/private or environment-gated.
- Append-only import history exists for file-backed storage, but there is no
  rollback command; re-uploading a prior bundle is the manual recovery path.
- Operator identity is optional metadata only through `operator_label`.
- There is no packaged operator CLI for prepare, validate, sign, upload,
  verify, and rollback.

## Production Hardening Roadmap

Before using this path as a production cloud operator workflow, add:

- durable backend-owned storage for accepted bundles
- production-grade import history with required operator identity, review state,
  and audit querying
- rollback or promotion controls for the active bundle
- cryptographic signed JSON or detached-signature verification
- `signing_key_id`, public-key lookup, and server-side signature validation
- authenticated and authorized admin import access
- maximum bundle-size limits and clear rejection messages
- partial-failure handling for ticker packs
- an operator CLI that can prepare, validate, sign, upload, and verify bundles

Until those pieces exist, document signed JSON as the intended next hardening
step, not as current behavior.
