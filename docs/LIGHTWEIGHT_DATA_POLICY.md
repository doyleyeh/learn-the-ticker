# Lightweight Data Policy

## Decision

Learn the Ticker is a personal educational side project and framework demo, not a production financial-data platform. The data pipeline should optimize for useful beginner explanations with visible source attribution, not for production-grade source-pack approval before every page can render.

This policy supersedes older strict source-pack, ETF-500 promotion, allowlist-only evidence, and Golden Asset Source Handoff gating language where the documents conflict for ordinary personal-project data display.

## Source Priority

Use this order for stocks, ETFs, and news:

1. Official and free sources first: SEC EDGAR/XBRL, issuer pages and documents, company investor relations pages, exchange/index-provider pages, and official fund downloads.
2. Reputable third-party or provider fallback when official sources are absent, incomplete, stale, difficult to parse, or not worth manual recovery for the personal MVP: Yahoo Finance or yfinance-derived metadata, Nasdaq/NYSE public pages, configured market-data provider adapters, and reputable news publishers.
3. Partial or unavailable states when neither official nor reputable fallback data can be resolved safely.

Third-party fallback data may be used for display, comparison, chat grounding, reusable Market News Focus, ticker-specific Weekly News Focus, and export summaries when the UI clearly labels the source. It should not be presented as official evidence. Deterministic Beginner Summary fallback may use a balanced, sentence-limited Yahoo/yfinance-derived company or fund description from normalized provider profile context, but it remains provider-derived fallback context rather than official SEC or issuer evidence and must exclude raw provider field names, quote/chart/volume/price-target facts, fixture/local wording, and recommendations.

## Automated Recovery

The code should do more of the collection work before asking an operator:

- resolve official locator/search pages into exact URLs when practical;
- follow bounded safe redirects;
- detect official PDFs, HTML pages, CSV/XLSX downloads, and API/provider records;
- extract `as_of_date`, `published_at`, or `retrieved_at` where available;
- try alternate official sources automatically;
- fall back to reputable third-party/provider data when official collection remains blocked;
- record source provenance, freshness, and confidence metadata;
- render partial pages instead of blocking the full asset when one section is missing.

Human review is useful for suspicious, high-impact, or launch-quality changes, but it is not the default blocker for local/personal data display.

## Repo Implementation Contract

The lightweight path is implemented as an explicit local fresh-data fetch boundary, not as a silent replacement for deterministic CI fixtures:

- `DATA_POLICY_MODE=lightweight` selects this policy.
- `LIGHTWEIGHT_LIVE_FETCH_ENABLED=true` enables live local fetching. Local runtime/manual review defaults to enabled when unset; explicit `env={}`, pytest, CI, and static eval paths remain deterministic/no-live unless explicitly enabled.
- `LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true` allows reputable provider fallback when official data is incomplete.
- `LIGHTWEIGHT_PROVIDER_SOURCE_USE_REVIEWED=false` does not skip configured provider API adapters for local lightweight display. It means the provider output is not strict/audit approved and cannot support source-pack approval or generated-output cache promotion.
- `LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED=true` enables local Weekly News metadata retrieval on the same server-side lightweight boundary. Local runtime/manual review defaults to enabled when unset; normal CI and explicit test envs stay fixture-backed.
- `MARKET_NEWS_FETCH_ENABLED=true` enables reusable Market News Focus live-source retrieval. Local runtime/manual review defaults to enabled when unset; normal CI uses fixtures/mocks and does not call RSS, GDELT, paid/keyed news providers, Yahoo/yfinance, market-data providers, or LLMs.
- `SEC_EDGAR_USER_AGENT` should identify the local SEC client; diagnostics may report only a redacted form.
- `GET /api/assets/{ticker}/fresh-data` exposes source-labeled fresh fetch results and returns `unavailable` unless live lightweight fetching is explicitly enabled.
- When live lightweight fetching is enabled, exact search can open source-labeled local-MVP pages for renderable eligible stocks and ETFs, including assets without deterministic cached packs.
- `GET /api/assets/{ticker}/overview`, `/details`, and `/sources` use the lightweight response to fill the existing page, detail, and source drawer contracts only when the fetch is renderable and raw payloads remain hidden.
- Asset pages, chat, comparison fallback, comparison export, asset export, Weekly News, and AI-analysis thresholds may use normalized lightweight fallback evidence for current stock manifest rows and supported ETF manifest rows when citations/source metadata are safe. Recognition-only, unsupported, out-of-scope, complex, and unknown rows remain blocked.
- `python3 scripts/run_lightweight_data_fetch_smoke.py --live --ticker AAPL --ticker VOO --json` is the local operator smoke for stock and ETF fetching.

Lightweight records are not strict Golden Asset Source Handoff approval. Durable snapshot and knowledge-pack adapters may store source-labeled metadata, checksums, normalized facts, compact diagnostics, and allowed excerpts for local display, but they must keep `generated_output_cache_eligible=false`, hide raw provider payloads and unrestricted source text, and avoid strict cache/export/citation promotion when the source is pending-review, rejected, metadata-only, link-only, parser-invalid, or rights-limited.

Local Weekly News metadata uses a yfinance/Yahoo-style list shape only as a fallback structure. The product goal is not to clone a market-news feed. The local source shape is: headline/title, publisher, URL, published time, retrieved time, ticker match, event type, source label, source-use policy, and optional bounded summary/snippet. It excludes raw article body storage/display, unrestricted thumbnails/media, trade buttons, recommendation framing, production recurring ingestion, and generated-output cache promotion.

For local live ticker Weekly News, provider APIs and Yahoo/yfinance are discovery channels, not quality proof. The acquisition order remains official/company/issuer/index-provider sources first, then configured provider or news APIs, then Yahoo/yfinance fallback. Final selection is quality-ranked across the pooled candidates: ticker usefulness and event specificity first, publisher/source reputation second, and acquisition tier third after official sources. Generic market-regime or opinion pieces stay in Market News Focus unless they clearly connect to the selected stock, ETF, issuer, index exposure, holdings, flows, fees, distributions, products, earnings, regulatory events, customers, or supply chain. Lower-reputation publishers such as Seeking Alpha, Motley Fool, Benzinga, MarketBeat, Zacks, IBD, and similar sources are backfill only when strongly ticker-specific and non-advice-like.

Market News Focus uses a separate market-wide source shape: headline/title, publisher, URL, canonical URL where available, published time, retrieved time, topic bucket, entities, provider/source label, source-use policy, story-cluster metadata, selection rationale, and optional bounded summary/snippet. It selects up to 20 approved story clusters and may show fewer when evidence is limited. It is reused across ticker pages and does not become canonical asset identity.

Normal tests and CI must still run without live SEC, issuer, market-data, news, RSS, GDELT, keyed news-provider, yfinance, or LLM calls. The lightweight fetch response and Market News response must not expose unrestricted raw provider payloads. They return normalized facts/news metadata, source labels, freshness metadata, partial/unavailable gaps, and safe diagnostics only.

## Frontend Source Transparency

Every externally sourced fact should carry as much provenance as the pipeline knows:

- source label: `official`, `reputable_third_party`, `provider_derived`, `fallback`, `partial`, or `unavailable`;
- publisher or provider name;
- URL when available;
- `as_of_date`, `published_at`, and/or `retrieved_at` when available;
- section-level freshness state;
- short note when a field came from fallback data rather than an official source.

If a source does not provide a full as-of date, use the best available date metadata and show it honestly. Prefer `retrieved_at` plus a visible `as_of_date=unavailable` or `date_precision=unknown` state over blocking the page.

## Operator Role

Operators should review the code's proposed results, not manually build the data pipeline by hand.

The normal operator task is:

1. Check whether the displayed source label and freshness look reasonable.
2. Reject obvious wrong ticker matches, stale data, unrelated documents, or poor-quality news.
3. Ask Codex to improve the adapter, parser, fallback source, or UI label when a pattern repeats.
4. Reserve manual source-pack approval for audit-quality milestones, public launch hardening, or sources that look legally or technically risky.

## Guardrails Kept

The simpler data policy does not relax these boundaries:

- no buy/sell/hold recommendations, price targets, personalized allocation, portfolio-building, tax advice, or guaranteed-return language;
- keep stable canonical facts separate from Market News Focus, Weekly News Focus, and AI Comprehensive Analysis;
- never expose provider API keys to the frontend;
- never inspect, echo, log, copy, or commit real secret values;
- use server-side provider adapters only;
- do not show or export unrestricted raw paywalled/restricted source text, full provider payloads, hidden prompts, or raw model reasoning;
- clearly label uncertainty, stale data, unavailable fields, and fallback sources.

## Practical Implication

For the personal MVP, source quality should be a visible user-facing property, not a binary gate that prevents the product from being built. The preferred failure mode is:

```text
official fetch failed
-> code tries alternate official source
-> code tries reputable third-party/provider fallback
-> page renders with source/fallback labels and partial states
-> operator reviews suspicious patterns and asks Codex to improve automation
```
