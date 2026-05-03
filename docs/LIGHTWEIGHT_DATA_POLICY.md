# Lightweight Data Policy

## Decision

Learn the Ticker is a personal educational side project and framework demo, not a production financial-data platform. The data pipeline should optimize for useful beginner explanations with visible source attribution, not for production-grade source-pack approval before every page can render.

This policy supersedes older strict source-pack, ETF-500 promotion, allowlist-only evidence, and Golden Asset Source Handoff gating language where the documents conflict for ordinary personal-project data display.

## Source Priority

Use this order for stocks, ETFs, and news:

1. Official and free sources first: SEC EDGAR/XBRL, issuer pages and documents, company investor relations pages, exchange/index-provider pages, and official fund downloads.
2. Reputable third-party or provider fallback when official sources are absent, incomplete, stale, difficult to parse, or not worth manual recovery for the personal MVP: Yahoo Finance or yfinance-derived metadata, Nasdaq/NYSE public pages, configured market-data provider adapters, and reputable news publishers.
3. Partial or unavailable states when neither official nor reputable fallback data can be resolved safely.

Third-party fallback data may be used for display, comparison, chat grounding, Weekly News Focus, and export summaries when the UI clearly labels the source. It should not be presented as official evidence.

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
- `LIGHTWEIGHT_LIVE_FETCH_ENABLED=true` opts into live local fetching.
- `LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true` allows reputable provider fallback when official data is incomplete.
- `SEC_EDGAR_USER_AGENT` should identify the local SEC client; diagnostics may report only a redacted form.
- `GET /api/assets/{ticker}/fresh-data` exposes source-labeled fresh fetch results and returns `unavailable` unless live lightweight fetching is explicitly enabled.
- When live lightweight fetching is enabled, exact search can open source-labeled local-MVP pages for renderable eligible stocks and ETFs, including assets without deterministic cached packs.
- `GET /api/assets/{ticker}/overview`, `/details`, and `/sources` use the lightweight response to fill the existing page, detail, and source drawer contracts only when the fetch is renderable and raw payloads remain hidden.
- `python3 scripts/run_lightweight_data_fetch_smoke.py --live --ticker AAPL --ticker VOO --json` is the local operator smoke for stock and ETF fetching.

Normal tests and CI must still run without live SEC, issuer, market-data, news, or LLM calls. The lightweight fetch response must not expose unrestricted raw provider payloads. It returns normalized facts, source labels, freshness metadata, partial/unavailable gaps, and safe diagnostics only.

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
- keep stable canonical facts separate from Weekly News Focus and AI Comprehensive Analysis;
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
