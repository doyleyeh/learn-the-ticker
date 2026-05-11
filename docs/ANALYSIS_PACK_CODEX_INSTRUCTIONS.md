# Analysis Pack Codex Instructions

These instructions adapt the referenced investment-analysis workflow to Learn
the Ticker. The output is structured JSON for backend validation, not HTML.

## General Rules

- Generate English educational content for v1.
- Do not provide buy, sell, hold, allocation, tax, brokerage, or price-target
  advice.
- Do not inject HTML into app pages.
- Do not store raw article text, unrestricted provider payloads, hidden prompts,
  raw model reasoning, secrets, tokens, or signed URLs.
- Use citations and source-document IDs for important factual claims.
- Keep stable canonical facts separate from Economic Indicators, Market News
  Focus, ticker Weekly News Focus, and AI Comprehensive Analysis.
- Persona-style responsibilities may guide reasoning internally, but visible
  API/UI/export labels must not include Atlas, Sophia, Kenji, Crow, Rain, or
  other analyst-persona names.

## Producer Workflow

1. Build the deterministic seed bundle first:

   ```bash
   python3 scripts/build_analysis_pack_bundle.py \
     --ticker QQQ \
     --output .agent-runs/analysis-packs/manual/analysis-pack-bundle.json \
     --summary-output .agent-runs/analysis-packs/manual/analysis-pack-summary.json \
     --technical-output .agent-runs/analysis-packs/manual/technical_data.json \
     --macro-output .agent-runs/analysis-packs/manual/macro_cache.json \
     --print-summary
   ```

2. Improve only the JSON artifacts in `.agent-runs/analysis-packs/...` when
   operator-approved live research is available.
3. Validate before upload:

   ```bash
   python3 scripts/build_analysis_pack_bundle.py \
     --validate-only \
     --input .agent-runs/analysis-packs/manual/analysis-pack-bundle.json \
     --summary-output .agent-runs/analysis-packs/manual/analysis-pack-summary.json
   ```

4. Upload only after validation passes:

   ```bash
   python3 scripts/upload_analysis_pack_bundle.py \
     --bundle .agent-runs/analysis-packs/manual/analysis-pack-bundle.json
   ```

## Economic Indicators

Use `economic-indicators-pack-v1`.

- V1 is U.S.-only.
- Use official historical actuals for GDP, CPI, PPI, retail sales, nonfarm
  payrolls, unemployment, jobless claims, M2, credit card delinquency, private
  investment, and Treasury yields.
- Market references such as DXY, VIX, and WTI/oil must be source-labeled and
  allowed by source-use policy.
- Do not include forecasts, estimates, outlooks, or unsupported projections as
  factual indicator values.
- Every row must include value, unit, period/as-of date, published/retrieved
  dates, source metadata, freshness state, trend direction, citation IDs, and
  source document IDs.

## Market News And Market AI

Market News Focus is reusable market-wide context.

- Prefer approved reputable publishers and rights-safe metadata/snippets.
- Keep the last seven days and current freshness rules visible.
- Select up to 20 items only when evidence supports them; never pad weak news.
- Critical claims about Fed policy, war, sanctions, or market-moving events
  require high-quality source priority or corroboration.
- Market AI must use product labels such as What Changed This Week, Macro &
  Policy, Equity Market Drivers, AI / Technology / Semiconductors,
  Geopolitical & Energy Risks, Credit / Liquidity / Sentiment, Scenario Lens,
  and Practical Watchpoints.
- Scenario Lens is conditional education only, not prediction.

## Ticker Weekly News And Ticker AI

Ticker imported packs are high-demand only unless the backend allowlist changes:

```text
AAPL, MSFT, NVDA, AMZN, GOOGL, VOO, QQQ, SPY, VTI, IVV, XLK
```

- Prefer official filings, investor-relations releases, ETF issuer
  announcements, prospectus updates, and fact-sheet changes.
- Use reputable third-party/news items only when source-use policy permits and
  the item is clearly ticker-relevant.
- Weekly News Focus should show up to the configured maximum only when enough
  high-quality evidence exists.
- Ticker AI requires enough approved Weekly News Focus evidence and uses:
  What Changed This Week, Market Context, Business/Fund Context, and Risk
  Context.
- Generated claims may cite only selected Weekly News items and canonical facts.
- Longer candidate history may be used for dedupe/scoring diagnostics only; it
  must not support current generated claims.

## Technical Data

The current committed producer reserves `technical_data.json` fields for KD,
RSI, MACD, BIAS, DMI/ADX, moving averages, and volume change, but it does not
perform live price-series fetching in normal CI. A future live adapter may fill
those values only when source-use, licensing, freshness, and no-live-CI rules
are satisfied.

Never quote a technical number in generated analysis unless that number is
present in the validated fact repository or structured bundle.

## Validation Checklist

Before upload, confirm:

- `analysis-pack-import-bundle-v1` schema is valid.
- Bundle checksum validates.
- `generated_at` and `freshness_expires_at` are within the seven-day freshness
  policy.
- No raw article text or raw provider payload is present.
- No visible persona labels are present.
- No secrets, tokens, signed URLs, hidden prompts, or raw model reasoning are
  present.
- Citations point to source documents in the same bundle.
- Economic Indicators are U.S.-only and cite source metadata.
- Ticker packs are in the high-demand allowlist or are intentionally skipped.
