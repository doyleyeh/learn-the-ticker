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

1. Build the bundle first. Local operator CLIs default to live mode outside CI,
   pytest, static evals, and quality gates:

   ```bash
   python3 scripts/build_analysis_pack_bundle.py \
     --ticker QQQ \
     --output .agent-runs/analysis-packs/manual/analysis-pack-bundle.json \
     --summary-output .agent-runs/analysis-packs/manual/analysis-pack-summary.json \
     --technical-output .agent-runs/analysis-packs/manual/technical_data.json \
     --macro-output .agent-runs/analysis-packs/manual/macro_cache.json \
     --ai-context-output .agent-runs/analysis-packs/manual/ai_context.json \
     --print-summary
   ```

2. Use deterministic mode for CI-safe rehearsal or fixture-only review:

   ```bash
   python3 scripts/build_analysis_pack_bundle.py \
     --deterministic \
     --ticker QQQ \
     --output .agent-runs/analysis-packs/manual/analysis-pack-bundle.json \
     --summary-output .agent-runs/analysis-packs/manual/analysis-pack-summary.json \
     --technical-output .agent-runs/analysis-packs/manual/technical_data.json \
     --macro-output .agent-runs/analysis-packs/manual/macro_cache.json \
     --ai-context-output .agent-runs/analysis-packs/manual/ai_context.json \
     --print-summary
   ```

3. The full operator script follows the same default:

   ```bash
   bash scripts/run_analysis_pack_codex.sh --ticker QQQ
   ```

   Add `--deterministic` only when the operator explicitly wants no-live
   fixture artifacts.

4. Improve only the JSON artifacts in `.agent-runs/analysis-packs/...` when
   operator-approved live research is available.
5. Validate before upload:

   ```bash
   python3 scripts/build_analysis_pack_bundle.py \
     --validate-only \
     --input .agent-runs/analysis-packs/manual/analysis-pack-bundle.json \
     --summary-output .agent-runs/analysis-packs/manual/analysis-pack-summary.json
   ```

6. Upload only after validation passes:

   ```bash
   python3 scripts/upload_analysis_pack_bundle.py \
     --bundle .agent-runs/analysis-packs/manual/analysis-pack-bundle.json
   ```

## Codex Research And Analysis Workflow

This is the stage-gated workflow the local Codex reviewer must follow after the
producer has created seed artifacts. It is the Learn the Ticker equivalent of
the reference repo's investment-analysis cycle, adapted to structured JSON,
U.S.-only coverage, English output, and visible citations.

### Stage 0: Technical Artifact Gate

- Inspect `analysis-pack-summary.json`, `technical_data.json`,
  `macro_cache.json`, `ai_context.json`, and `analysis-pack-bundle.json` before
  editing any generated analysis.
- Treat `technical_data.json` as the only technical evidence source. If a
  ticker is `not_computed`, `partial`, or missing a field, do not make a claim
  that depends on that field.
- Use ticker close price only from a `close` or explicitly labeled closing-price
  field. Do not use ADX, DMI, true range, volume, volume change, or indicator
  levels as price levels.
- Cite only computed KD, RSI, MACD, BIAS, DMI/ADX, moving-average, close-price,
  and volume-change facts that also appear in `ai_context.json`
  `allowed_numeric_facts`.
- Do not claim a technical divergence, breakout, support/resistance level, or
  historical high/low unless the exact supporting fields and comparison periods
  exist in the artifacts.

### Stage 1: Macro Data Gate

- Use U.S. official historical actuals only. Do not use forecasts, estimates,
  outlooks, nowcasts, consensus ranges, or analyst projections as indicator
  values.
- Data period rules are based on the operator run date in U.S. Eastern time:
  - GDP and private investment must normally be at least one completed quarter
    behind the current quarter unless the primary agency release explicitly
    publishes a newer official actual.
  - Monthly indicators such as CPI, PPI, retail sales, payrolls, unemployment,
    M2, and credit-card delinquency must use a completed official period before
    the current month.
  - Weekly jobless claims may use the latest completed official week from the
    Department of Labor.
  - Treasury yields, VIX, DXY, and WTI/oil are market references, not macro
    releases, and may use the latest available trading-day/as-of date when
    source-use policy allows.
- Primary source mapping:
  - BEA: GDP and private investment.
  - BLS: CPI, PPI, nonfarm payrolls, and unemployment.
  - Census: retail sales.
  - Department of Labor: initial jobless claims.
  - Federal Reserve: M2 and consumer-credit or credit-card delinquency series
    when available.
  - U.S. Treasury: 3-month, 10-year, and 30-year Treasury yields.
  - ISM: manufacturing index when available through an approved source path.
  - Cboe or approved market-data source: VIX.
  - ICE, FRED, or approved market-data source: DXY.
  - EIA, FRED, or approved market-data source: WTI/oil.
- FRED may be used as a structured cross-check or fallback. When a primary
  agency value and FRED disagree, prioritize the primary agency and record FRED
  as a cross-check with an explicit source role.
- Cross-verify every updated indicator by matching value, unit, period/as-of
  date, published date when available, source URL/series ID, and publisher.
- Preserve `macro_cache.json` with upsert logic. Update newer validated rows,
  keep existing unrelated rows, and reject any update that causes a suspicious
  indicator-count decrease.

### Stage 2: Tier-1 News Gate

- Use approved Tier-1 or official sources only. For U.S. English v1, the
  default market-news allowlist is Reuters, AP, Bloomberg, WSJ, FT, CNBC,
  Barron's, BBC, CNN, official government releases, exchange releases, company
  investor-relations releases, SEC filings, and ETF issuer materials. Other
  reputable sources require an existing source-use policy approval before they
  can support generated output.
- Required U.S. market searches:
  - Global Macro/Fed.
    Example queries: `Reuters Federal Reserve inflation Treasury yields last 7
    days`, `Bloomberg Fed policy jobs CPI market last 7 days`.
  - Geopolitical Risks.
    Example queries: `Reuters Middle East Red Sea sanctions oil shipping last 7
    days`, `FT Hormuz conflict supply disruption last 7 days`.
  - Energy Supply & Global Shipping.
    Example queries: `Reuters WTI oil supply shipping freight last 7 days`,
    `CNBC oil prices global shipping supply chain last 7 days`.
- Optional searches may cover U.S. equity earnings, AI infrastructure,
  semiconductors, credit/liquidity, and ETF flows when the required searches do
  not provide enough high-quality coverage.
- Every selected item must have a publisher, title, URL/source metadata,
  publication date in `YYYY-MM-DD` form, retrieved date, concise rights-safe
  summary, citation ID, source-document ID, and freshness state.
- Keep only items published within the last seven days. If publication date is
  missing, outside the window, ambiguous, or not source-verifiable, reject the
  item.
- Critical claims about Fed policy, inflation, war, sanctions, energy supply,
  market disruption, large company events, or ETF methodology changes require
  Reuters/AP/Bloomberg/WSJ/FT-level priority or corroboration from at least two
  approved sources.
- Select up to 20 Market News items only when evidence supports them. Do not
  pad weak, duplicate, promotional, opinion-only, stale, rights-disallowed, or
  single-source critical stories.
- U.S. English v1 does not require the reference repo's Traditional Chinese
  translation rule or Taiwan 70/30 mix. Keep output English and product-native.
- Store source metadata, short summaries/snippets, links, hashes, clusters, and
  citations only. Never store raw article bodies or unrestricted provider
  payloads.

### Stage 3: AI Comprehensive Analysis Gate

- Use these internal lenses when writing analysis, but do not expose persona
  names or persona labels:
  - Macro and policy lens: official economic indicators, Fed-sensitive news,
    Treasury yields, VIX, DXY, oil, credit/liquidity, and market breadth
    context where available.
  - Business or fund-quality lens: for stocks, canonical business facts,
    filings, revenue/margin/ROE/PEG only when present; for ETFs, issuer facts,
    benchmark, holdings concentration, expense ratio, sector exposure, and
    methodology only when present.
  - Technical lens: close price, KD, RSI, MACD, BIAS, DMI/ADX, moving averages,
    and volume change only from validated technical artifacts.
  - Sentiment and flow lens: VIX, DXY, volume/volume-change, approved fund-flow
    or positioning data, and selected market/ticker news only when present.
  - Scenario synthesis lens: conditional educational scenarios and watchpoints,
    not predictions, trading instructions, or price targets.
- Market AI must use product-native section labels, such as What Changed This
  Week, Macro & Policy, Equity Market Drivers, AI / Technology /
  Semiconductors, Geopolitical & Energy Risks, Credit / Liquidity / Sentiment,
  Scenario Lens, and Practical Watchpoints.
- Ticker AI must use What Changed This Week, Market Context,
  Business/Fund Context, and Risk Context.
- Required inputs by section:
  - What Changed This Week cites selected Market News or ticker Weekly News
    items and avoids unsupported background claims.
  - Macro & Policy or Market Context uses Economic Indicators, Treasury yields,
    VIX, DXY, and selected market stories from `ai_context.json`.
  - Business/Fund Context uses canonical facts plus ticker Weekly News; it does
    not let recent news redefine stable asset facts.
  - Risk Context uses selected news, canonical risk facts, Economic Indicators,
    and technical context when supported.
  - Scenario Lens and Practical Watchpoints use conditional language and cite
    the facts that define the scenarios.
- Anti-template rule: write a natural professional narrative based on the
  evidence. Do not use fixed mad-lib sentence structures or repeat the same
  wording across tickers.
- Fact-only rule: do not invent historical highs/lows, drawdowns, trend changes,
  causal links, forecasts, or dramatic verbs unless the exact supporting facts
  exist in `ai_context.json`.
- Numeric-description rule: every numeric claim must include a plain-English
  label, such as `VIX volatility index`, `U.S. 10-year Treasury yield`,
  `ticker closing price`, `RSI momentum indicator`, or `ADX trend-strength
  indicator`.
- Yield-curve rule: mention flattening or inversion only when the validated
  spread among 3-month, 10-year, and 30-year Treasury yields is under 25 bps or
  inverted. If all validated gaps are at least 25 bps and positive, do not
  discuss yield-curve flatness or inversion.
- Geopolitical and supply-chain warning rule: add a dedicated warning only when
  selected news contains configured risk keywords such as Middle East, Red Sea,
  Hormuz, Suez, Iran, sanctions, blockade, conflict, disruption, oil supply,
  freight, shipping, or supply chain. Explain immediate market psychology and
  possible chain reactions as educational context, not forecasts.
- Advice-boundary rule: do not tell users to buy, sell, hold, trade, allocate,
  rebalance, time entries, set stop losses, or follow a price target.

### Stage 4: Final Validation Gate

- Run validate-only after every JSON edit:

  ```bash
  python3 scripts/build_analysis_pack_bundle.py \
    --validate-only \
    --input .agent-runs/analysis-packs/<run-id>/analysis-pack-bundle.json \
    --summary-output .agent-runs/analysis-packs/<run-id>/analysis-pack-summary.json
  ```

- Inspect `analysis-pack-summary.json` reason codes before upload.
- Do not upload until schema validation, checksum validation, source-use guards,
  freshness checks, citation/source consistency, no-raw-payload checks,
  no-visible-persona checks, `ai_context.json` alignment, macro-cache upsert
  checks, and numeric-integrity validation all pass.

## Economic Indicators

Use `economic-indicators-pack-v1`.

- V1 is U.S.-only.
- Use official historical actuals for GDP, CPI, PPI, retail sales, nonfarm
  payrolls, unemployment, jobless claims, M2, credit card delinquency, private
  investment, Treasury yields, and ISM when available.
- Record primary source metadata from BEA, BLS, Census, Department of Labor,
  Federal Reserve, Treasury, or ISM where applicable. FRED may be used as a
  structured cross-check/fallback, but the row must make that source role
  explicit.
- Update macro caches with upsert logic only: preserve existing indicator rows,
  update only rows with newer validated data, and block suspicious large count
  drops instead of overwriting the entire cache.
- Market references such as DXY, VIX, and WTI/oil must be source-labeled and
  allowed by source-use policy.
- Do not include forecasts, estimates, outlooks, or unsupported projections as
  factual indicator values.
- Every row must include value, unit, period/as-of date, published/retrieved
  dates, source metadata, freshness state, trend direction, citation IDs, and
  source document IDs.

## Market News And Market AI

Market News Focus is reusable market-wide context.

- Use Tier-1 or approved reputable publishers and rights-safe metadata/snippets.
- Required U.S. market research searches:
  - Global Macro/Fed.
  - Geopolitical Risks.
  - Energy Supply & Global Shipping.
- Keep the last seven days and current freshness rules visible.
- Select up to 20 items only when evidence supports them; never pad weak news.
- Critical claims about Fed policy, war, sanctions, or market-moving events
  require Reuters/AP/Bloomberg/WSJ/FT-level priority or corroboration from at
  least two approved reputable sources.
- Do not copy article bodies. Store source metadata, dates, links, publisher
  labels, bounded summaries/snippets, cluster metadata, and citations only.
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
- Ticker AI may use Economic Indicators and technical indicators only through
  validated `ai_context.json` records and must cite the relevant context or
  Weekly News evidence.

## Technical Data

Deterministic mode reserves `technical_data.json` fields for KD, RSI, MACD,
BIAS, DMI/ADX, moving averages, and volume change without external calls.
Live operator mode fetches Yahoo chart OHLCV metadata and computes those
indicators into the technical artifact. Store only computed indicator values
and source metadata, not raw provider payloads.

Never quote a technical number in generated analysis unless that number is
present in the validated fact repository or structured bundle. Do not describe
ADX, DMI, volume, or volume-change fields as price levels.

## AI Context And Numeric Integrity

Every producer run writes `ai_context.json`.

The context must include:

- selected Market News items and citation/source IDs
- selected ticker Weekly News items and citation/source IDs
- Economic Indicators rows and citation/source IDs
- technical indicator rows and citation/source IDs
- canonical fact citation IDs
- allowed numeric facts with value, unit, label, tolerance, aliases, and source
  IDs

AI analysis must cite only this context. Numeric claims for VIX, DXY, U.S.
10-year Treasury yield, ticker close price, KD, RSI, MACD, BIAS, ADX, moving
averages, and volume change must match the allowed numeric facts. Yield-curve
flattening or inversion may be mentioned only when the validated spread between
3-month, 10-year, and 30-year yields is under 25 bps or inverted. Geopolitical
and supply-chain warning language may appear only when selected news contains
configured risk keywords such as Middle East, Red Sea, Hormuz, Suez, Iran,
sanctions, blockade, conflict, or disruption.

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
- `ai_context.json` is present, checksummed, and aligned with the bundle.
- Macro cache updates are upsert-safe.
- Numeric integrity validation passes.
