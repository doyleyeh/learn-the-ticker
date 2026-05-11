# Analysis Pack Operator Guide

This guide explains the Codex-assisted analysis pack flow for Learn the Ticker.
The current implementation supports structured JSON import through the backend.
It does not yet support cryptographic signed-bundle verification or durable cloud
storage for imported bundles.

## Current Pipeline

The analysis pack path is a structured-data workflow, not an HTML injection
workflow.

1. A local operator or local Codex workflow prepares an
   `analysis-pack-import-bundle-v1` JSON object.
2. The backend imports the bundle through `POST /api/admin/analysis-packs/import`.
3. The backend validates schema version, validator version, checksum, freshness,
   source-use policy, citation/source IDs, raw payload guards, secret-like values,
   visible persona labels, and required U.S. Economic Indicators rows.
4. Runtime routes read a fresh imported pack first. If the imported pack is
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

Imported packs are fresh only while both conditions hold:

- the bundle is no more than 7 days old
- current time is before `freshness_expires_at`

## Local Commands

Start the backend with the repo's normal local backend command. One simple local
example is:

```bash
LTT_FORCE_COMPAT_FASTAPI=1 uvicorn backend.main:app --reload
```

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

- Imported bundles are held in an in-memory repository.
- Imported bundles are lost when the backend process restarts.
- Multi-instance cloud deployments will not share imported bundles.
- Validation uses a deterministic checksum, not cryptographic signature
  verification.
- The admin import endpoint does not yet include production auth hardening.
- There is no packaged operator CLI for prepare, validate, sign, and upload.

## Production Hardening Roadmap

Before using this path as a production cloud operator workflow, add:

- durable backend-owned storage for accepted bundles
- import history with bundle ID, operator identity, timestamps, validation
  result, checksum, and reason codes
- rollback or promotion controls for the active bundle
- cryptographic signed JSON or detached-signature verification
- `signing_key_id`, public-key lookup, and server-side signature validation
- authenticated and authorized admin import access
- maximum bundle-size limits and clear rejection messages
- partial-failure handling for ticker packs
- an operator CLI that can prepare, validate, sign, upload, and verify bundles

Until those pieces exist, document signed JSON as the intended next hardening
step, not as current behavior.
