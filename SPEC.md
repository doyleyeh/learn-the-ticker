# SPEC.md

## Product Success

Learn the Ticker helps beginners understand U.S.-listed common stocks and non-leveraged U.S.-listed equity ETFs through plain-English, source-backed explanations.

A successful answer or asset page helps the user understand:

- what the asset is
- what the company does or what the ETF holds
- why people may study it
- the top risks
- how it compares with another supported asset when the user enters the separate comparison workflow
- what changed in Weekly News Focus
- which sources support important claims
- which beginner terms are worth learning next

The product is educational. It is not a stock picker, trading tool, brokerage app, portfolio optimizer, tax tool, or personalized financial advisor.

## MVP Baseline

The updated PRD and technical design spec define the current MVP/v1 baseline.

MVP direction:

- accountless responsive web app
- Next.js frontend rooted at `apps/web`
- FastAPI backend rooted at `backend`
- local Docker Compose scaffold for web, API, ingestion-worker placeholder, Postgres/pgvector, Redis, and MinIO-compatible object storage
- Vercel Hobby frontend deployment target
- Cloud Run API in `us-central1` with request-based billing and `min-instances=0`
- Cloud Run Jobs for manual ingestion first
- Neon Free Postgres and private Google Cloud Storage for first deployment
- deterministic mocks and fixtures for CI

MVP product scope:

- top-500-first U.S.-listed common stocks from `data/universes/us_common_stocks_top500.current.json`
- non-leveraged U.S.-listed equity index, sector, and thematic ETFs
- pre-cached high-demand launch universe for reliability and latency
- explicit `pending_ingestion` states only for approved eligible supported assets outside the pre-cache set
- home page single-asset search first, with natural `A vs B` queries redirecting to comparison instead of turning home into a comparison builder
- stock and ETF asset pages with Beginner section first and Deep-Dive section available
- separate connected comparison workflow for supported stock-vs-stock, ETF-vs-ETF, and stock-vs-ETF pairs
- stock-vs-ETF comparison relationship badges and a special single-company-vs-ETF-basket structure
- Weekly News Focus and AI Comprehensive Analysis as separated timely context
- limited asset-specific grounded chat beta
- contextual glossary with curated core terms, desktop popovers, mobile bottom sheets, and grounded asset-specific context where supported
- Markdown/JSON export/download for asset pages, comparison output, source lists, and chat transcripts
- caching, source checksums, generated-summary freshness hashes, and section-level freshness labels

Unsupported and out-of-scope v1 assets include options, crypto, international equities, leveraged ETFs, inverse ETFs, ETNs, fixed income ETFs, commodity ETFs, active ETFs, multi-asset ETFs, preferred stocks, warrants, rights, and other complex products unless explicitly added later. Recognized-but-unsupported and out-of-scope assets may appear in search, but must not receive generated pages, generated chat answers, generated comparisons, or generated risk summaries.

## Current Implementation Direction

The repository is no longer planning-only. It is currently a deterministic, fixture-backed MVP scaffold with substantial backend and frontend surface area already in place.

Current implementation stage:

- backend contracts exist for search, overview/details, Weekly News Focus, AI Comprehensive Analysis, comparison, grounded chat, glossary, exports, ingestion states, provider adapters, trust metrics, and LLM runtime diagnostics
- frontend routes and components exist for home search, asset pages, comparison, chat, source metadata, glossary, and export controls
- CI and local checks are deterministic and fixture-backed; normal quality gates do not depend on live provider, market-data, news, or LLM calls

Near-term implementation priority order:

1. close Frontend Design and Workflow v0.4 UX gaps first, especially single-asset home search, search/autocomplete support states, natural comparison redirects, contextual glossary behavior, mobile source/glossary/chat bottom sheets, and stock-vs-ETF relationship badges
2. converge frontend rendering onto the richer deterministic backend contracts instead of expanding duplicate frontend-only fixture logic
3. close remaining MVP-visible contract gaps, especially Weekly News Focus and AI Comprehensive Analysis rendering, support-state parity, comparison-state parity, and source/freshness parity
4. defer live-provider, persistence, deployment-hardening, and broader ingestion work until deterministic contract parity and quality gates are stable

When choosing the next task, prefer improving PRD/TDS alignment of the current deterministic scaffold over adding new domains or speculative infrastructure.
The local agent-loop harness should default to `gpt-5.5` with `high` reasoning effort, while allowing explicit per-run overrides such as `gpt-5.3-codex-spark` when the operator requests it.

## Source And Freshness Rules

Stable facts must come from official or structured sources before model-written explanations.

Provider hierarchy for MVP planning:

- stock canonical facts: SEC EDGAR submissions, SEC XBRL company facts, SEC filings, then company investor relations
- ETF canonical facts: issuer pages, fact sheets, prospectuses, shareholder reports, holdings files, and exposure files
- structured enrichment: free-first reference data and optional provider adapters only where licensing, rate limits, caching, display, and export rights allow
- Weekly News Focus: official filings, investor-relations releases, issuer announcements, prospectus changes, fact-sheet changes, then license-compatible allowlisted news

Weekly News Focus must use the last completed Monday-Sunday market week plus current week-to-date through yesterday, using U.S. Eastern dates. It should show the configured maximum only when enough quality evidence exists, fewer items when evidence is limited, and a clear empty state when no major Weekly News Focus items exist.

AI Comprehensive Analysis must be suppressed unless at least two high-signal Weekly News Focus items exist. When present, it starts with What Changed This Week, then Market Context, Business/Fund Context, and Risk Context. It must cite underlying Weekly News Focus items and canonical facts.

Source-use policy wins over scoring. Rejected or license-disallowed sources must not display, summarize, cache, or export. Raw source text storage is rights-tiered across `full_text_allowed`, `summary_allowed`, `metadata_only`, `link_only`, and `rejected`.

## Hard Product Rules

The product must:

- use source-backed facts before model-written explanations
- separate stable canonical facts from Weekly News Focus and AI Comprehensive Analysis
- show visible citations for important factual claims
- show freshness or as-of information at page and section level
- say unknown, stale, mixed evidence, unavailable, partial, or insufficient evidence when needed
- keep chat grounded in the selected asset knowledge pack
- block unsupported and out-of-scope assets from generated pages, generated chat, and generated comparisons
- frame suitability as education, not personalized advice
- preserve source hierarchy and source-use rights
- keep live provider, market-data, news, and LLM calls out of normal CI

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
- expose provider or LLM secrets to browser code, docs, logs, `/health`, or committed env files

Advice-like user questions must be redirected into educational framing.

Safe style:

> I can't tell you whether to buy, sell, hold, or how much to invest. I can help you understand what this asset is, what it holds or does, its main risks, how it compares with alternatives, and what questions a beginner may want to research before making their own decision.

## Technical Success

A task is complete only when:

- the requested behavior is implemented
- relevant unit tests pass
- relevant integration tests pass, if applicable
- relevant golden tests pass, if applicable
- citation validation passes when citations are touched
- safety evals pass when summaries, chat, suitability text, or advice-boundary copy are touched
- Weekly News Focus/source-use tests pass when timely context or source allowlists are touched
- frontend smoke/type/build checks pass when UI or frontend workspace layout is touched
- Bash and PowerShell workflow prompts stay aligned when agent-loop instructions are touched
- no unrelated behavior is changed
- normal CI remains deterministic and does not require live external calls
- placeholder env files contain no real secrets
- the final summary explains changed files, tests run, results, and remaining risks

## MVP Success Checklist

MVP is ready when:

- the home page has one primary action: search for a single supported stock or ETF
- the home page routes clear `A vs B` queries to `/compare?left=...&right=...` without becoming a comparison builder
- search resolves supported stocks and ETFs by ticker, partial ticker, name, and issuer/provider where useful
- search rows show ticker, name, stock/ETF identity, exchange or issuer, and support-state chips
- unsupported and out-of-scope assets show clear blocked states
- top-500 stock scope is driven by the versioned manifest, not live runtime provider queries
- stock and ETF pages render beginner summaries from source-backed evidence
- stock pages cover business overview, products/services, strengths, financial quality, risks, valuation context, Weekly News Focus, AI Comprehensive Analysis, and educational suitability
- ETF pages cover role, holdings/exposure, construction, cost/trading context, risks, comparison/overlap, Weekly News Focus, AI Comprehensive Analysis, and educational suitability
- partial pages render verified sections only and label missing evidence
- top risks show exactly three items first
- Weekly News Focus and AI Comprehensive Analysis are visually and structurally separate from stable facts
- Weekly News Focus includes source date or as-of date, event date where available, retrieved date, citation/source link, source quality, source-use policy, and freshness state
- key factual claims have visible citations or explicit uncertainty/unavailable labels
- source drawer shows source metadata, freshness, source-use policy, related claims, and allowed supporting excerpts
- comparison works as a separate connected workflow for ETF-vs-ETF, stock-vs-stock, and stock-vs-ETF pairs, with an educational beginner bottom line
- stock-vs-ETF comparison uses relationship badges and the single-company-vs-ETF-basket structure
- limited asset-specific chat answers only from the selected asset knowledge pack
- single-asset chat redirects second-ticker comparison questions to the comparison workflow
- accountless chat uses anonymous conversation IDs, 7-day TTL, deletion, minimal browser storage, and no raw transcript analytics/training/evaluation use
- glossary explains core beginner terms contextually through desktop popovers and mobile bottom sheets, and avoids uncited asset-specific facts
- source drawer, glossary, and asset chat remain usable on mobile through bottom sheets or full-screen panels
- safety guardrails block buy/sell/hold, price-target, tax, brokerage, and allocation advice
- users can export/download asset page content, comparison output, source lists, and chat transcripts as Markdown or JSON where licensing permits
- caching and freshness hashes prevent unnecessary repeated API and LLM work
- trust metrics can track citation coverage, unsupported claims, freshness accuracy, glossary usage, comparison usage, source drawer usage, safety redirects, export usage, and latency without raw user text
