# SPEC.md

## Product success

Learn the Ticker helps beginners understand U.S.-listed common stocks and plain-vanilla U.S.-listed ETFs using plain-English, source-backed explanations.

A successful answer or asset page must help the user understand:

- what the asset is
- what the company does or what the ETF holds
- why people consider it
- the top risks
- how it compares with similar choices
- what changed recently
- which sources support the important claims
- which beginner terms are worth learning next

## MVP direction

The next milestone is a functional MVP, not a stock picker or trading tool.

MVP direction:

- accountless v1
- responsive web experience
- search and supported/unsupported classification for eligible U.S.-listed common stocks and plain-vanilla U.S.-listed ETFs
- pre-cached high-demand launch universe for reliability and latency
- on-demand ingestion path for supported assets outside the pre-cached universe
- stock and ETF asset pages with Beginner Mode first and Deep-Dive Mode baseline
- comparison workflow for supported pairs
- limited asset-specific grounded chat beta
- hybrid glossary with curated core terms and grounded asset-specific context where supported
- export/download for asset pages, comparison output, source lists, and chat transcripts
- server-side caching, source checksums, generated-summary freshness hashes, and section-level freshness labels

Provider hierarchy for MVP planning:

- canonical stock facts: SEC EDGAR submissions, SEC XBRL company facts, SEC filings, then company investor relations
- canonical ETF facts: issuer pages, fact sheets, prospectuses, shareholder reports, holdings files, and exposure files
- structured market/reference data: provider-backed ticker reference, snapshots, prices, volume, valuation, AUM, and trading metrics
- recent developments: official filings, investor-relations releases, issuer announcements, prospectus changes, then reputable ticker-tagged news

No live external API, market-data, news, or LLM calls should be required in normal CI. Provider and ingestion work must use mocks, fixtures, or explicit manual-only paths until credentials, licensing, and deployment constraints are settled.

## Hard product rules

The product must:

- use source-backed facts before model-written explanations
- separate stable canonical facts from recent developments
- show visible citations for important factual claims
- show freshness or as-of information at page and section level
- say unknown, stale, mixed evidence, unavailable, or insufficient evidence when needed
- keep chat grounded in the selected asset knowledge pack
- block unsupported assets from generated pages, generated chat, and generated comparisons
- frame suitability as education, not personalized advice
- preserve source hierarchy: official and structured sources before news

The product must not:

- tell users what to buy
- tell users what to sell
- tell users what to hold
- tell users how much to allocate
- provide tax advice
- provide unsupported price targets
- provide brokerage or trading execution behavior
- present recent news as stable asset identity
- invent facts when evidence is missing
- present unsupported claims as facts

Advice-like user questions must be redirected into educational framing.

Safe style:

> I can't tell you whether to buy it or how much to allocate. I can help you understand what it is, what it holds or does, how concentrated it is, how it compares with similar assets, and what risks a beginner should understand before making their own decision.

## Technical success

A task is complete only when:

- the requested behavior is implemented
- relevant unit tests pass
- relevant integration tests pass, if applicable
- relevant golden tests pass, if applicable
- citation validation passes when citations are touched
- safety evals pass when summaries, chat, suitability text, or advice-boundary copy are touched
- frontend smoke/type/build checks pass when UI is touched
- no unrelated behavior is changed
- normal CI remains deterministic and does not require live external calls
- the final summary explains changed files, tests run, results, and remaining risks

## MVP success checklist

MVP is ready when:

- search resolves supported stocks and ETFs by ticker and name
- unsupported assets show a clear recognized-but-unsupported or unknown state
- stock and ETF pages render beginner summaries
- stock pages cover business overview, strengths, financial quality, risks, valuation context, recent developments, and educational suitability
- ETF pages cover role, holdings/exposure, construction, cost/trading context, risks, comparison/overlap, recent developments, and educational suitability
- top risks show exactly three items first
- recent developments are visually separate from stable facts
- recent developments include event date, source date or as-of date, retrieved date, citation, and a no-high-signal state when needed
- key factual claims have visible citations
- source drawer shows source metadata, freshness, related claims, and supporting passages
- page and major sections show freshness labels or unknown/stale/unavailable states
- comparison works for supported stock and ETF pairs, with an educational beginner bottom line
- limited asset-specific chat answers only from the selected asset knowledge pack
- safety guardrails block buy/sell/hold, price-target, tax, brokerage, and allocation advice
- users can export/download asset page content, comparison output, source lists, and chat transcripts where licensing permits
- caching and freshness hashes prevent unnecessary repeated API and LLM work
- trust metrics can track citation coverage, unsupported claims, freshness accuracy, source drawer usage, safety redirects, and export usage
