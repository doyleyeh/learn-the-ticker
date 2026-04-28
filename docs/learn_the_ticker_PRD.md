# PRD: Learn the Ticker - Citation-First Beginner U.S. Stock & ETF Research Assistant

**Document version:** v0.6 product decision refresh
**Date:** 2026-04-28
**Product stage:** Side-project MVP / v1 planning  
**Primary audience:** Product, design, engineering, data/LLM, and compliance reviewers
**Source basis:** Original proposal, PRD v0.1, technical design spec v0.1, ETF manifest policy update, and resolved product decisions from current review.
**Documentation role:** Product source of truth. The proposal provides narrative vision; the technical design spec translates this PRD into implementation details.

---

## 1. Executive summary

Learn the Ticker is a web-based educational research assistant that helps beginner investors understand U.S.-listed common stocks and a manifest-approved set of currently U.S.-listed, non-leveraged, non-inverse, passive/index-based U.S. equity ETFs in plain English.

A user can search one ticker or asset name such as `VOO`, `QQQ`, `Apple`, or `AAPL` and receive a source-grounded explanation of:

- what the asset is
- what the company does or what the ETF holds
- why people consider it
- the top risks
- how it compares with similar assets
- what changed in Weekly News Focus
- which sources support important factual claims
- which terms a beginner should learn next

The product promise is:

> Help beginners understand what they are looking at, using cited sources and easy words.

The product should not promise:

> Tell users exactly what to buy, sell, hold, or how much to invest.

The strongest version of this product is not an AI stock picker. It is a calm, source-first financial learning product that combines beginner explanations, visible citations, comparison-capable learning, Weekly News Focus context separation, and limited asset-specific grounded chat.

The primary v1 journey is:

```text
Search one stock or ETF
-> Understand the asset in plain English
-> Inspect citations and freshness
-> Compare with another asset when useful
-> Ask grounded follow-up questions
-> Export learning output
```

The home page has one primary action: search for a single supported stock or ETF. Comparison is a separate but connected workflow, not the home page's main input pattern.

---

## 2. Resolved MVP decisions

This version resolves the previous open questions and makes the MVP direction explicit.

| Area                     | Decision                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Coverage universe        | Support a top-500-first U.S.-listed common stock universe plus a manifest-approved supported ETF universe. Supported ETF coverage is limited to currently U.S.-listed, non-leveraged, non-inverse, passive/index-based ETFs with primary U.S. equity exposure and validated issuer source packs. Pre-cache the existing curated high-demand universe for speed, testing, and reliability. Treat stocks outside the top 500 and ETFs outside the supported ETF manifest as future expansion unless explicitly approved. |
| Unsupported assets       | Block unsupported and out-of-scope assets from generated pages, chat, and comparisons. Search may show a recognized-but-unsupported or recognized-but-out-of-scope result with a clear explanation.                                                                                                                                                |
| Market/reference data    | Use a free-first approach: SEC EDGAR/XBRL, official issuer materials, free/reference metadata where available, provider adapters, deterministic mocks, and fixtures for tests. No paid provider keys are assumed for v1; paid market/reference providers may be added later behind adapters after licensing and export-rights review.                 |
| Golden Asset Source Handoff | Treat source handoff as the approval layer and API fetching as only the retrieval layer. A fetched API payload, endpoint, issuer page, or filing URL is not approved evidence until domain, source type, official-source status, storage rights, export rights, source-use policy, rationale, parser validity, freshness/as-of metadata, and review status are approved. |
| Weekly News Focus and analysis | Use a fixed Monday-Sunday market-week model plus current week-to-date through yesterday, based on U.S. Eastern dates. Use official filings, company investor relations releases, ETF issuer announcements, prospectus updates, and fact-sheet changes first, then broaden coverage with reputable third-party/news sources when source governance permits. Clearly label source type and official-vs-third-party status. AI Comprehensive Analysis starts with What Changed This Week and then Market Context, Business/Fund Context, and Risk Context, and appears only when at least two approved Weekly News Focus items exist. |
| Grounded chat timing     | Include asset-specific grounded chat in MVP as a beta feature. Local testing should exercise live AI chat fully so the operator can review quality. Public v1 keeps chat beta-limited, asset-bounded, citation-aware, and not a general finance chatbot.                                                                                                                                                                                                                                                                                                 |
| Citation strictness      | Require citations for important factual claims, not every sentence. Generic educational explanations do not require citations unless they include asset-specific facts.                                                                                                                                                                                                                                       |
| Frontend workflow        | The home page is single-asset search first. Comparison lives on `/compare` and is reachable from global navigation, asset pages, suggested comparisons, chat compare redirects, and natural `A vs B` search patterns. Glossary is contextual help in reading flows, not a primary home-page workflow for MVP. |
| Glossary depth           | Use a hybrid glossary: curated static definitions for core terms, plus optional asset-specific context grounded in the selected asset's data. In MVP, glossary appears primarily through inline contextual term cards on asset pages, comparison pages, and chat answers, not through one large standalone glossary section on an asset page. |
| User accounts            | Keep v1 fully accountless. Local/private testing is limited-user local operator testing, not an in-product account or auth surface. Store anonymous chat sessions with random IDs for grounded follow-ups and user-requested export. Browser local storage keeps only conversation metadata. Server-side chat TTL is 7 days from last activity, with user-delete support.                                                                                                                                  |
| Compliance stance        | Add persistent educational disclaimers and inline redirects for advice-like questions. Avoid buy/sell/hold, allocation, price-target, tax, and personalized recommendation language.                                                                                                                                                                                                                          |
| Mobile priority          | Build responsive web from v1. Mobile should prioritize Beginner Summary, Top 3 Risks, Key Facts, Weekly News Focus, AI Comprehensive Analysis, contextual glossary cards, chat, and source access. Source, glossary, and chat surfaces open as bottom sheets or full-screen panels where appropriate. |
| Deployment target        | Use a free-tier-oriented personal side-project deployment path: Vercel Hobby for the frontend, Google Cloud Run in `us-central1` for the API with request-based billing and `min-instances=0`, Cloud Run Jobs for manual ingestion first, Neon Free Postgres, private Google Cloud Storage, no production queue service beyond Postgres `ingestion_jobs`, and Google Cloud Logging/Error Reporting. |
| LLM runtime provider     | Keep deterministic mocks as the default for CI and ordinary local tests. Local fresh-data review should exercise live OpenRouter for generated features, especially grounded chat and AI Comprehensive Analysis when evidence thresholds are met. First deployment may enable live OpenRouter behind `LLM_LIVE_GENERATION_ENABLED=true` with an explicit free-model chain and DeepSeek V3.2 paid fallback only when paid fallback is enabled and the operator has configured OpenRouter platform/API-key limits; the repo does not enforce a separate spend cap. The browser must never call OpenRouter directly or receive the key. |
| Local provider secrets  | For local live-provider runs, `OPENROUTER_API_KEY`, `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FINNHUB_API_KEY`, `TIINGO_API_KEY`, and `EODHD_API_KEY` are expected to exist in the developer's WSL Bash environment. Key values must not be committed, copied into docs, exposed in frontend env vars, returned from APIs, or printed in logs. |
| MVP readiness            | Full MVP remains the v1 target. Implementation may be phased internally, but v1 is not ready until compare, limited grounded chat beta, exports, freshness, citations, glossary, and on-demand ingestion states pass the MVP acceptance checklist and strict quality gates.                                                                         |
| Public launch path       | Keep the current MVP/v1 structure. Before public deployment, validate locally with fresh data, live AI for generated features, and limited local users. Public v1 still requires the approved top-500 stock manifest, approved supported ETF manifest, source-backed golden assets, and launch/deploy smoke. |

---

### 2.1 Deployment and provider constraints

The MVP should optimize for a small personal side-project audience before scale. Deployment choices should minimize fixed monthly cost and avoid always-on paid services until usage proves a need.

- Frontend production default: Vercel Hobby, with `NEXT_PUBLIC_API_BASE_URL` pointing to the Cloud Run API.
- Backend production default: Cloud Run in `us-central1`, request-based billing, `min-instances=0`, conservative max instances, and Cloud Run's injected `PORT`.
- Jobs production default: Cloud Run Jobs run manually first; Cloud Scheduler is optional later.
- Database production default: Neon Free Postgres using the pooled connection URL with SSL.
- Storage production default: private Google Cloud Storage bucket in `us-central1`.
- Queue production default: no Redis, Pub/Sub, or paid queue; use the existing Postgres `ingestion_jobs` table.
- Monitoring production default: Google Cloud Logging and Error Reporting; Sentry Developer plan is optional later.
- OpenRouter production default: disabled unless server-side env vars, OpenRouter platform/API-key limits, and validation gates are configured. Mock provider remains the default for CI and ordinary local tests, while local operator review may intentionally enable live AI.
- Retrieval production default: keyword and metadata retrieval first, with embeddings and pgvector vector indexes disabled until citation quality justifies semantic retrieval.

OpenRouter first-deployment model chain:

| Tier | Order | Model |
| --- | ---: | --- |
| Free primary | 1 | `openai/gpt-oss-120b:free` |
| Free fallback | 2 | `google/gemma-4-31b-it:free` |
| Free fallback | 3 | `qwen/qwen3-next-80b-a3b-instruct:free` |
| Free fallback | 4 | `meta-llama/llama-3.3-70b-instruct:free` |
| Paid safety net | 5 | `deepseek/deepseek-v3.2` |

Flow: free model chain, schema/citation/safety validation, one repair retry, DeepSeek fallback when paid fallback is enabled and OpenRouter platform/API-key limits are set, validation again, then cache only validated output. Raw model reasoning is never stored or shown; the product may show only a short cited `reasoning_summary`.

These deployment choices do not relax product safety. Generated and exported output remains educational only and must preserve citation, freshness, uncertainty, and no-advice guardrails.

Provider API keys are configuration readiness only. `OPENROUTER_API_KEY`, `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FINNHUB_API_KEY`, `TIINGO_API_KEY`, and `EODHD_API_KEY` are server-side only; local live runs inherit them from WSL Bash, and production uses Secret Manager. Market/reference provider keys do not change source hierarchy or licensing constraints.

Golden Asset Source Handoff is required before any retrieved source can be stored as evidence, summarized, cited, used in generation, or exported. Retrieval tools include SEC/issuer fetch commands, API clients, provider endpoints, adapters, and downloaded payloads. Approval requires the source to be allowlisted or explicitly governed by review, compatible with the requested source type, classified for official-source status, assigned storage and export rights, given a source-use policy and rationale, parsed successfully, and labeled with freshness/as-of metadata. Sources missing from the allowlist, carrying unclear rights, failing parser validation, or coming from hidden/internal endpoints default to `pending_review` or `rejected` and must not support generated output.

### 2.2 Top-500 Universe Definition

The authoritative source for the top-500 stock universe is a versioned manifest, not a live provider response at request time.

- Manifest path: `data/universes/us_common_stocks_top500.current.json`.
- Production mirror: a private GCS object referenced by `TOP500_UNIVERSE_MANIFEST_URI`.
- Each entry includes ticker, name, CIK when available, exchange, rank, rank basis, provider/source provenance, snapshot date, generated checksum, and approval timestamp.
- External providers may supply provenance inputs, but the manifest is the runtime source of truth. Runtime coverage must never be resolved directly from a live ETF holdings file or provider response.
- Refresh cadence is monthly by default. Ad hoc refreshes require a development-log entry explaining source, checksum, and reason.
- The manifest is operational coverage metadata, not an endorsement, recommendation, or model portfolio.
- Stocks outside the manifest return `out_of_scope` unless explicitly added to the approved on-demand ingestion queue.
- Local validation may use golden assets and smaller reviewed test manifests, but public v1 requires the full approved top-500 manifest and private production mirror.

Monthly refresh workflow:

- Use official iShares Russell 1000 ETF (`IWB`) holdings as the primary source input. Rank valid U.S. common-stock rows by IWB portfolio weight and set `rank_basis = "iwb_weight_proxy"`.
- If IWB fails, is stale, cannot be parsed, or yields too few validated common-stock rows, use official S&P 500 ETF holdings from `SPY`, `IVV`, and `VOO` as fallback inputs and set `rank_basis = "sp500_etf_weight_proxy_fallback"`.
- Write monthly candidates to `data/universes/us_common_stocks_top500.candidate.YYYY-MM.json`; promote only an approved candidate to `data/universes/us_common_stocks_top500.current.json`.
- Candidate rows must include source provenance, source snapshot date, source checksum, rank, rank basis, CIK, exchange, validation status, and warnings.
- Normalize tickers and remove cash, futures, options, swaps, index rows, ETFs, preferred shares, warrants, rights, units, funds, and other non-common-stock rows before ranking.
- Validate candidate rows against SEC `company_tickers_exchange.json` and Nasdaq Trader symbol-directory fields such as `ETF` and `Test Issue`. Rows that cannot be validated are review warnings, not silent inclusions.
- Produce a diff report before approval with added tickers, removed tickers, rank changes, missing CIKs, Nasdaq validation failures, source used, source dates, and checksum.
- Require manual approval when fallback sources are used, source snapshots are stale or unparseable, validation coverage is below threshold, many tickers change, or top-ranked names disappear.

### 2.3 ETF Supported Universe Definition

The authoritative source for v1 supported ETF coverage is a versioned manifest, not live provider lookup, exchange directory search, issuer search results, or a generic ETF flag.

- Supported ETF manifest path: `data/universes/us_equity_etfs_supported.current.json`.
- ETF/ETP recognition manifest path: `data/universes/us_etp_recognition.current.json`.
- The recognition manifest helps search identify real exchange-traded products, including unsupported ETFs, ETNs, ETVs, closed-end funds, commodity products, active ETFs, single-stock funds, option-income/buffer products, leveraged funds, inverse funds, and other complex wrappers.
- The supported ETF manifest is the only ETF runtime authority for generated asset pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, and exports.
- Supported ETF entries must be currently U.S.-listed, non-leveraged, non-inverse, passive/index-based ETFs with primary U.S. equity exposure and validated issuer source packs.
- Issuer source packs must pass Golden Asset Source Handoff and parser validation before an ETF is marked supported.
- Search may display recognized ETFs or ETPs outside the supported manifest as `unsupported`, `out_of_scope`, `pending_review`, `unavailable`, or `pending_ingestion`, but those states must block generated output.
- The supported ETF manifest is operational coverage metadata, not an endorsement, recommendation, model portfolio, or statement of suitability.

The supported ETF manifest should cover the reviewed eligible universe, not only a fixed launch list. Eligible scope includes broad U.S. index, total-market/large-cap, size/style, sector, industry/theme, dividend, value/growth, quality, momentum, low-volatility, equal-weight, and ESG index ETFs when they are U.S.-listed, non-leveraged, non-inverse, passive/index-based, primary U.S. equity funds with validated issuer source packs. Golden ETF tickers are pre-cache and regression assets only, not the full coverage limit.

ETF support expansion requires a reviewed candidate packet with exchange or regulatory recognition evidence, issuer source-pack references, source dates, checksums, wrapper classification, leverage/inverse flags, asset-class and geographic-exposure checks, passive/index validation, parser results, Golden Asset Source Handoff approval, exclusions, warnings, and manual approval notes.

## 3. Product positioning

### 3.1 Positioning statement

**A beginner-friendly, source-grounded stock and ETF learning assistant for U.S. investors.**

### 3.2 What this product is

The product is an educational research tool that uses official and structured sources as the truth backbone, then uses AI to explain those facts in beginner-friendly language.

It should feel like a patient teacher with receipts:

- simple explanation first
- sources visible when claims matter
- uncertainty shown honestly
- recent news separated from stable facts
- comparisons framed as learning, not advice

### 3.3 What this product is not

The product is not:

- a stock picker
- a trading bot
- a brokerage app
- a portfolio optimizer
- a personalized financial advisor
- a tax advisor
- a price-target generator
- a tool that tells users exactly what to buy, sell, hold, or allocate

---

## 4. Problem statement

Beginner investors face three connected problems.

First, most finance tools assume prior knowledge. They show prices, ratios, holdings, and charts, but often do not explain what those things mean in plain language.

Second, beginners struggle to compare similar assets. They may know tickers like `VOO`, `SPY`, `QQQ`, `VTI`, `AAPL`, or `MSFT`, but may not understand differences in benchmark, concentration, sector exposure, fees, business model, valuation, or role.

Third, generic AI answers can sound confident even when weakly grounded. In financial education, unsupported confidence is a trust problem. The system must separate source-backed facts from AI-written explanations and make citations visible throughout the product.

---

## 5. Product vision

Build the most trustworthy beginner-first explainer for U.S. stocks and ETFs.

The product should help users quickly answer:

- What is this asset?
- What does this company do, or what does this ETF hold?
- Why do people consider it?
- What are the biggest risks?
- Is it broad or narrow?
- What are simpler alternatives?
- What changed recently?
- How is it different from another stock or ETF?
- Which sources support these answers?
- What terms should I understand before going further?

The product should make users feel more informed, not more pressured to trade.

---

## 6. Goals and non-goals

### 6.1 Goals

#### G1. Explain stocks and ETFs in beginner language

Every asset page should start with a plain-English summary that explains the asset without assuming finance knowledge.

#### G2. Make citations part of the product experience

Important factual claims should be backed by visible citations. Citations should appear as citation chips, source drawers, and source/freshness metadata, not only in a footer.

#### G3. Separate stable facts from Weekly News Focus and AI analysis

The product must clearly distinguish "what this asset is" from "what happened this week." Weekly News Focus and AI Comprehensive Analysis should add cited context, not redefine the asset.

#### G4. Make comparison a flagship connected workflow

Users should be able to compare two assets on a dedicated comparison page and understand the real difference in simple language. Comparison should be easy to enter from search, asset pages, chat redirects, and global navigation, but it should not replace the home page's single-asset search.

#### G5. Provide limited asset-specific grounded chat in MVP

Users should be able to ask questions about the selected asset. Chat answers must be grounded in the asset's knowledge pack and must not rely on generic model memory.

#### G6. Teach financial vocabulary in context

Users should be able to hover, click, tap, or keyboard-focus terms such as "expense ratio," "AUM," "P/E," "operating margin," "concentration," or "tracking error" exactly where those terms appear and get short beginner explanations in context. Glossary is not a major home-page workflow for MVP, and asset pages should not require users to leave the section they are reading for a separate glossary block.

#### G7. Avoid investment advice

The product should support education and understanding, not buy/sell recommendations, price targets, personalized allocations, or individualized tax guidance.

#### G8. Reduce API and LLM cost through caching

The product should use server-side caching, data freshness rules, source checksums, and generated-summary freshness hashes so repeated requests for the same asset do not unnecessarily call APIs or LLMs.

### 6.2 Non-goals for v1

The following are out of scope for v1:

- brokerage trading
- personalized allocation advice
- tax guidance
- options
- crypto
- international equities
- leveraged ETFs
- inverse ETFs
- ETNs
- complex exchange-traded products
- portfolio optimization
- automated buy/sell signals
- guaranteed-return language
- unsupported price targets
- user accounts, saved assets, and saved comparisons
- native mobile apps

---

## 7. Target users

### 7.1 Beginner ETF learner

This user has heard of broad ETFs such as `VOO`, `SPY`, `VTI`, or `QQQ`, but does not fully understand diversification, expense ratio, index tracking, overlap, concentration, liquidity, or sector exposure.

Primary needs:

- Understand what an ETF actually holds
- Learn whether it is broad or narrow
- Compare similar ETFs
- Understand fees, concentration, and trading context
- Identify simpler alternatives

### 7.2 Beginner stock learner

This user knows company names such as Apple, Microsoft, Nvidia, or Tesla, but does not know how to read filings, understand revenue drivers, interpret risks, or evaluate financial quality.

Primary needs:

- Understand what the company actually does
- Learn how it makes money
- See top risks in simple language
- Understand recent earnings or major news
- Compare the company with a peer

### 7.3 Self-directed learner

This user does not want a direct trading signal. They want a reliable explainer that translates source material into understandable language.

Primary needs:

- Source-backed explanations
- Clear uncertainty when evidence is missing
- Glossary support for jargon
- Comparison-based learning
- No pressure to trade

---

## 8. MVP scope

### 8.1 In scope

#### Asset coverage

- Top 500 U.S.-listed common stocks first, based on a deterministic launch universe maintained by ingestion configuration
- Manifest-approved, currently U.S.-listed, non-leveraged, non-inverse, passive/index-based ETFs with primary U.S. equity exposure and validated issuer source packs
- Pre-cached high-demand stocks and ETFs for launch performance
- Limited on-demand ingestion only for assets that pass deterministic classification and are explicitly added to the supported queue

#### Core product features

- Search and entity resolution
- Supported/unsupported asset classification
- Stock asset page
- ETF asset page
- Beginner section
- Deep-Dive section
- Compare two supported assets
- Weekly News Focus and AI Comprehensive Analysis section
- Limited asset-specific grounded chat beta
- Hybrid beginner glossary
- Source drawer
- Inline citation chips
- Page and section freshness labels
- Educational suitability summary
- Export/download of page content, comparison output, source list, and chat transcript
- Server-side caching and freshness-based invalidation
- Responsive web UX for desktop and mobile

### 8.2 Out of scope

- Trading and brokerage integration
- Portfolio import
- Portfolio optimization
- Saved watchlists
- Saved assets and saved comparisons
- User accounts
- Personalized investment recommendations
- Tax advice
- Options, crypto, international equities, leveraged ETFs, inverse ETFs, ETNs, fixed income ETFs, commodity ETFs, active ETFs, multi-asset ETFs, single-stock ETFs, option-income/buffer ETFs, preferred stocks, warrants, rights, and other complex products
- Native iOS or Android app
- Read-aloud, text-to-speech, or generated audio for news and analysis
- Traditional Chinese localization

---

### 8.3 Priority semantics

Functional requirement priorities mean:

- `P0`: launch blocker for MVP/v1.
- `P1`: MVP-desired or beta-quality item that can ship after launch unless explicitly promoted.
- `P2`: post-MVP.

Any requirement needed by the MVP acceptance checklist is `P0`. Acceptance criteria and strict MVP quality gates override the table priority if a conflict is discovered; the table should then be corrected to `P0`.

---

## 9. Product principles

1. **Source first.** Important facts come from official or structured sources before AI writes explanations.
2. **Plain English first.** Every asset page begins with a beginner summary.
3. **Comparison is connected.** Beginners learn faster by comparing assets when useful, but the home page stays focused on one supported stock or ETF at a time.
4. **Stable facts, Weekly News Focus, and AI Comprehensive Analysis stay separate.** Users should not confuse asset basics with short-term news or AI synthesis.
5. **Citations are product UX.** Source visibility is part of the reading flow, not an appendix.
6. **Grounded chat only.** Chat answers should come from a bounded asset-specific knowledge pack.
7. **Education over advice.** The product explains tradeoffs without telling users what to buy.
8. **Uncertainty is acceptable.** The system should say "unknown," "not available," or "evidence is mixed" when sources do not support a confident answer.
9. **Accountless first.** V1 should minimize user-data overhead and use backend caching rather than user accounts for cost control.
10. **Responsive from v1.** The web experience should work well on desktop and mobile from the first release.

---

## 10. Core user journeys

### 10.1 Search one asset and understand it

1. User lands on the home page.
2. The home page shows one primary action: search for a single supported stock or ETF.
3. User searches `VOO`, `Apple`, or another ticker/name.
4. System resolves exact and partial ticker/name matches and shows stock/ETF type plus support status before routing.
5. User selects a supported result and lands on `/assets/[ticker]` with the Beginner Summary visible first.
6. User sees what the asset is, why people may look at it, the main thing to be careful about, exactly three top risks, key facts, freshness, Weekly News Focus, AI Comprehensive Analysis when available, and key sources.
7. User clicks a citation chip to open the source drawer, or taps it on mobile to open a bottom sheet.
8. User clicks or taps a contextual glossary term such as "expense ratio" or "operating margin" and sees a beginner-friendly card.
9. User asks the asset chat a grounded follow-up question.
10. User downloads the page summary and source list as Markdown or JSON.

Success outcome: the user can explain what the asset is, why people may study it, what its main limitations are, and where the important claims came from.

### 10.2 Compare two ETFs

1. User opens Compare from global navigation, an asset-page "Compare this asset" CTA, a suggested comparison, chat compare redirect, or a natural search pattern such as `QQQ vs VOO`.
2. System resolves both assets and routes to `/compare?left=QQQ&right=VOO`.
3. User sees a completed comparison page with "Bottom line for beginners" first.
4. User sees side-by-side snapshots, benchmark, provider, expense ratio, AUM, holdings count, top holdings, sector concentration, overlap when available, and broad/narrow role.
5. User opens the source drawer for supporting citations.
6. User downloads the comparison and source list as Markdown or JSON.

Success outcome: the user understands that two popular ETFs may serve very different roles even if both hold large U.S. companies.

### 10.3 Understand a stock

1. User searches `AAPL` or `Apple`.
2. System resolves ticker to company identity and CIK.
3. User lands on the stock asset page.
4. User sees what the company sells, how it makes money, financial quality trends, top 3 risks, valuation context, Weekly News Focus, AI Comprehensive Analysis when evidence is sufficient, and key sources.
5. User asks: "What is the biggest risk for a beginner?"
6. Chat responds with a direct answer, why it matters, citations, and uncertainty or missing context.

Success outcome: the user understands the company's business model and main risks without needing to read the full 10-K first.

### 10.4 Handle an unsupported ETF

1. User searches a leveraged ETF, inverse ETF, ETN, active ETF, commodity product, fixed income ETF, single-stock ETF, option-income/buffer ETF, international equity ETF, or complex exchange-traded product.
2. System recognizes the ticker when possible.
3. System does not generate a full page, chat answer, or comparison.
4. System shows a recognized-but-unsupported state.

Suggested copy:

> We found this ticker, but it is not supported in v1 because it appears to be leveraged, inverse, fixed income, commodity, active, multi-asset, international, single-stock, option-income/buffer, an ETN, or another complex or out-of-scope exchange-traded product. Learn the Ticker currently supports a top-500-first U.S. common-stock universe and a reviewed manifest of U.S.-listed passive/index-based U.S. equity ETFs only.

Success outcome: the product avoids explaining complex products in a way that could mislead beginners.

### 10.5 Learn a finance concept in context

1. User sees "operating margin" on a stock page, comparison page, or chat answer.
2. User hovers, clicks, taps, or keyboard-focuses the term.
3. A glossary popover opens on desktop, or a glossary bottom sheet opens on mobile.
4. User sees a simple definition, why it matters, common beginner mistake, and optional deeper explanation.

Success outcome: the user learns the concept at the moment they need it.

### 10.6 Ask an advice-like question safely

1. User asks: "Should I buy QQQ?"
2. Chat does not answer with buy/sell/hold guidance.
3. Chat redirects to educational framing.

Suggested response pattern:

> I can't tell you whether to buy, sell, hold, or how much to invest. I can help you understand what this asset is, what it holds or does, its main risks, how it compares with alternatives, and what questions a beginner may want to research before making their own decision.

Success outcome: the user gets useful education without the product crossing into personalized advice.

---

## 11. Functional requirements

### 11.1 Search and entity resolution

The home page search box is single-asset-first. It searches for one stock or ETF by exact ticker, partial ticker, asset name, and issuer/provider name where useful.

Primary home copy:

```text
Understand a stock or ETF in plain English
```

Supporting copy:

```text
Search a U.S. stock or supported U.S. equity ETF to see beginner-friendly explanations, source citations, top risks, recent context, and grounded follow-up answers.
```

Primary search placeholder:

```text
Search a ticker or name, like VOO, QQQ, or Apple
```

Example chips may include `VOO`, `QQQ`, `AAPL`, `NVDA`, and `SOXX`, but they are examples only and must not be presented as recommendations.

The home page should not show two comparison inputs as the primary experience. If a user types a clear comparison pattern such as `VOO vs QQQ`, `AAPL vs MSFT`, or `NVDA vs SOXX`, autocomplete should show a special result such as "Compare VOO and QQQ" and route to `/compare?left=VOO&right=QQQ` when selected.

| ID   | Requirement                                                                                                                       | Priority |
| ---- | --------------------------------------------------------------------------------------------------------------------------------- | -------- |
| SR-1 | User can search by ticker, e.g. `VOO`, `QQQ`, `AAPL`.                                                                             | P0       |
| SR-2 | User can search by company or fund name, e.g. `Apple`, `Vanguard S&P 500 ETF`.                                                    | P0       |
| SR-3 | System resolves canonical ticker, name, asset type, exchange, issuer/provider/company, and relevant identifiers.                  | P0       |
| SR-4 | System distinguishes supported, unsupported, out-of-scope, pending ingestion, partial, stale, and unavailable states before page routing.   | P0       |
| SR-5 | System handles ambiguous names with a disambiguation state.                                                                       | P1       |
| SR-6 | System supports the top 500 U.S.-listed common stocks first and supported ETFs only through the approved stock and ETF manifests.    | P0       |
| SR-7 | System pre-caches a high-demand universe and labels out-of-cache supported assets as pending ingestion instead of pretending content is ready.                                                       | P0       |
| SR-8 | Autocomplete supports partial ticker, partial name, and issuer/provider matching where useful.                                    | P0       |
| SR-9 | Search result rows show ticker, name, asset type, exchange or issuer/provider, and support status.                               | P0       |
| SR-10 | Search status chips use a consistent set: `Supported`, `Pending ingestion`, `Partial data`, `Stale data`, `Unsupported`, `Out of scope`, `Unavailable`, and `Unknown`. | P0       |
| SR-11 | Natural comparison patterns route users to the comparison workflow without turning the home page into a comparison builder.       | P0       |

Acceptance criteria:

- Searching `AAPL` opens Apple's stock page.
- Searching `VOO` opens Vanguard S&P 500 ETF's ETF page only when `VOO` is in `data/universes/us_equity_etfs_supported.current.json` and has a validated source pack or safe ingestion state.
- Searching an unsupported crypto ticker, option, leveraged ETF, inverse ETF, ETN, fixed income ETF, commodity ETF, active ETF, multi-asset ETF, or international equity shows an unsupported or out-of-scope state.
- Searching a recognized ETF or ETP outside `data/universes/us_equity_etfs_supported.current.json` shows a blocked state rather than generated ETF content.
- Ambiguous name searches show likely matches instead of guessing silently.
- Exact recognized-but-unsupported ticker searches show "We found this ticker, but it is not supported in v1" and do not show generated summary, top risks, chat, comparison CTA, Weekly News Focus, or AI Comprehensive Analysis.
- No-result searches show "No supported stock or ETF found for `{query}`" and do not treat unknown searches as recognized unsupported assets.
- Supported, partial, stale, and pending-ingestion states route only to the state-appropriate page or job/status experience; unsupported, out-of-scope, unavailable, and unknown states do not generate asset content.

### 11.2 Supported and unsupported asset handling

| ID   | Requirement                                                                                                    | Priority |
| ---- | -------------------------------------------------------------------------------------------------------------- | -------- |
| UA-1 | Supported assets may proceed to asset pages, chat, and comparison.                                             | P0       |
| UA-2 | Unsupported and out-of-scope assets are blocked from generated pages, chat, and comparison.                    | P0       |
| UA-3 | Search may show a recognized-but-unsupported or recognized-but-out-of-scope result with a short explanation.   | P0       |
| UA-4 | Partial pages render verified sections only and label missing sections unavailable, stale, or unknown.         | P0       |
| UA-5 | Unsupported result pages should not include generated asset summaries, top risks, chat, comparison CTAs, Weekly News Focus, AI Comprehensive Analysis, or generated risk summaries. | P0       |
| UA-6 | System logs unsupported and out-of-scope asset searches for future product planning.                           | P2       |

Blocked asset types for v1 include:

- leveraged ETFs
- inverse ETFs
- ETNs
- fixed income ETFs
- commodity ETFs
- active ETFs
- multi-asset ETFs
- single-stock ETFs
- option-income or buffer ETFs
- options
- crypto assets
- international equities
- preferred stocks, warrants, rights, and other special securities unless explicitly added later

Deterministic classification rules:

- Do not use an LLM to decide whether an asset is supported. LLMs may explain a classification after deterministic rules have already decided it.
- If `fund_leverage > 1`, mark the asset `unsupported`.
- If `inverse_flag == true`, mark the asset `unsupported`.
- If `asset_class != equity`, mark the asset `unsupported`.
- If `strategy == active`, mark the asset `unsupported`.
- If an ETF is not present in `data/universes/us_equity_etfs_supported.current.json`, mark it `unsupported`, `out_of_scope`, `pending_review`, `unavailable`, or `pending_ingestion` based on deterministic recognition and review state.
- If an asset is not a U.S.-listed common stock in the top-500 launch universe or a manifest-approved U.S.-listed passive/index-based U.S. equity ETF, mark it `unsupported` or `out_of_scope` for MVP.
- If a supported asset passes classification but has not been ingested yet, return `pending_ingestion` and create or reuse a queued ingestion job.
- other complex or unsupported exchange-traded products

Required blocked-state copy:

```text
We found this ticker, but it is not supported in v1.

Learn the Ticker currently supports a top-500-first U.S. common-stock universe and ETFs listed in the approved supported ETF manifest.
```

For out-of-scope stocks:

```text
This stock is outside the current v1 coverage universe.

Learn the Ticker currently supports a top-500-first U.S. common stock universe and ETFs in the approved supported ETF manifest.
```

For pending ingestion:

```text
This asset is supported but still being prepared.

We need to collect and validate sources before generating an educational page.
```

The pending state may include "Check again" but must not promise a completion time.

### 11.3 Asset page: shared requirements

Every supported asset page is a learning page, not a data dump. The first screen should answer: what is this, why do people look at it, what should a beginner be careful about, and where did this information come from?

Recommended public routes:

```text
/assets/[ticker]
/assets/[ticker]/sources
```

Recommended high-level section order:

```text
1. Asset Header
2. Beginner Summary
3. Top 3 Risks
4. Key Facts
5. What it does / What it holds
6. Weekly News Focus
7. AI Comprehensive Analysis
8. Deep Dive
9. Ask about this asset
10. Sources
11. Educational disclaimer
```

Asset pages must support partial evidence states. If free-first sources cannot verify a section, the page should render verified sections only, label the missing section as unavailable, stale, unknown, or partial, and suppress generated claims that lack source support.

| ID    | Requirement                                                                                      | Priority |
| ----- | ------------------------------------------------------------------------------------------------ | -------- |
| AP-1  | Asset page places Beginner Summary, Top 3 Risks, and Key Facts before deep data.                  | P0       |
| AP-2  | Asset header includes ticker, canonical name, asset type, exchange, ETF issuer/provider or stock sector/industry when available, overall status, and page last updated. | P0       |
| AP-3  | Asset page starts with `BeginnerSummaryCard` using three short cards: what it is, why people look at it, and the main thing to be careful about. | P0       |
| AP-4  | Asset page includes exactly three top risks before expandable risk detail.                       | P0       |
| AP-5  | Asset page includes Weekly News Focus and AI Comprehensive Analysis separate from asset basics. | P0       |
| AP-6  | Asset page includes source citations for important factual claims.                               | P0       |
| AP-7  | Asset page includes a source drawer or mobile bottom sheet with source title, type, policy, freshness, dates, related claim, allowed excerpt, and URL. | P0       |
| AP-8  | Asset page includes contextual glossary terms for important beginner terms.                      | P0       |
| AP-9  | Asset page includes a Deep-Dive section for more detailed metrics and source context.             | P0       |
| AP-10 | Asset page allows users to export/download page content and source list.                         | P0       |
| AP-11 | Asset page includes a persistent educational disclaimer at the bottom.                           | P0       |
| AP-12 | Header actions include Compare this asset, Export, and View sources.                             | P0       |
| AP-13 | Desktop may use a right helper rail for Ask about this asset, Compare this asset, Freshness summary, and Key sources. | P1       |
| AP-14 | Mobile uses sticky actions for Ask, Compare, and Sources, with source, chat, and glossary surfaces as bottom sheets or full-screen panels. | P0       |
| AP-15 | Freshness near the top stays compact and includes page last updated, facts as of, Weekly News Focus checked, holdings as of for ETFs, and delayed/unavailable quote/reference copy when relevant. | P0       |

Acceptance criteria:

- A beginner can read the top section without needing advanced finance vocabulary.
- Important claims have visible citations.
- Weekly News Focus and AI Comprehensive Analysis are clearly labeled as timely context, separate from asset basics.
- Source drawer exposes where claims came from.
- Missing, stale, unavailable, or mixed evidence is displayed honestly.
- Quote/reference data never implies real-time coverage unless the backend can verify it.
- Partial pages show verified sections only and label missing sections as unavailable, stale, insufficient evidence, or could not verify from allowed sources.

### 11.4 Stock page

The stock page explains what a company does, how it makes money, its financial quality, risks, valuation context, Weekly News Focus, and AI Comprehensive Analysis. It should not turn valuation or risk context into advice.

| ID    | Requirement                                                                                                                              | Priority |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ST-1  | Show stock snapshot: name, ticker, sector, industry, exchange, market cap, price or last close, last updated.                            | P0       |
| ST-2  | Explain what the business does in beginner language.                                                                                     | P0       |
| ST-3  | Show main products and services.                                                                                                         | P0       |
| ST-4  | Show business segments when available.                                                                                                   | P1       |
| ST-5  | Show revenue drivers and geographic exposure when available.                                                                             | P1       |
| ST-6  | Summarize strengths in source-grounded language.                                                                                         | P1       |
| ST-7  | Show multi-year financial quality trends, not one quarter alone.                                                                         | P0       |
| ST-8  | Show exactly three top risks first.                                                                                                      | P0       |
| ST-9  | Provide expandable risk detail from filings or other source documents.                                                                   | P1       |
| ST-10 | Show valuation context such as P/E, forward P/E when sourced, price/sales, price/free cash flow, peer context, and own-history context.  | P1       |
| ST-11 | Provide a suitability summary using educational language, not buy/sell language.                                                         | P0       |
| ST-12 | Show Weekly News Focus items such as earnings, guidance, product announcements, M&A, leadership changes, legal events, or regulatory events. | P0       |
| ST-13 | Use `BusinessOverview` with the beginner-facing label "How this company makes money."                                                       | P0       |
| ST-14 | Use `FinancialTrendsTable` for multi-year trends rather than one-quarter-only metrics.                                                     | P0       |
| ST-15 | Use `ValuationContextCard` for P/E, forward P/E when sourced, price/sales, price/free cash flow, peer context, and own-history context when available. | P1       |

Acceptance criteria:

- Stock page answers "what does this company actually sell?"
- Top risks are understandable to a beginner.
- Financial metrics are explained, not merely displayed.
- Valuation context avoids saying a stock is cheap, expensive, undervalued, or overvalued as advice.
- Weekly News Focus and AI Comprehensive Analysis do not override stable company basics.

### 11.5 ETF page

The ETF page explains what the fund is trying to do, what it holds, how it is constructed, its costs, trading context, risks, and comparison context. ETF role language is educational classification, not personalized portfolio advice.

ETF pages are generated only for ETFs in `data/universes/us_equity_etfs_supported.current.json`. Recognition rows from `data/universes/us_etp_recognition.current.json`, live provider ETF flags, exchange listings, or issuer search results cannot unlock ETF page generation without supported-manifest approval and a validated issuer source pack.

| ID     | Requirement                                                                                                                                 | Priority |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ETF-1  | Show ETF snapshot: name, ticker, issuer/provider, category, asset class, passive/active, benchmark/index, expense ratio, AUM, last updated. | P0       |
| ETF-2  | Explain what the ETF is trying to do in beginner language.                                                                                  | P0       |
| ETF-3  | Explain why beginners may consider it.                                                                                                      | P0       |
| ETF-4  | Explain the main catch or beginner misunderstanding.                                                                                        | P0       |
| ETF-5  | Classify ETF role as broad/core-like exposure, satellite exposure, or specialized/narrow exposure, with caveats.                            | P1       |
| ETF-6  | Show number of holdings.                                                                                                                    | P0       |
| ETF-7  | Show top 10 holdings.                                                                                                                       | P0       |
| ETF-8  | Show top 10 concentration.                                                                                                                  | P0       |
| ETF-9  | Show sector breakdown.                                                                                                                      | P0       |
| ETF-10 | Show country breakdown when relevant.                                                                                                       | P1       |
| ETF-11 | Show weighting method and methodology details when available.                                                                               | P1       |
| ETF-12 | Show cost and trading context: expense ratio, AUM, bid-ask spread, average volume, and premium/discount where available.                    | P0       |
| ETF-13 | Show ETF-specific risks, including market, concentration, liquidity, complexity, interest-rate, credit, and currency risks where relevant.  | P0       |
| ETF-14 | Show similar ETFs and simpler alternatives.                                                                                                 | P0       |
| ETF-15 | Show whether the ETF adds diversification or overlaps heavily with a broad-market ETF.                                                      | P1       |
| ETF-16 | Show Weekly News Focus items such as fee changes, methodology changes, fund merger/liquidation news, or sponsor updates.                    | P0       |
| ETF-17 | Use `HoldingsTable` for holdings count, top 10 holdings, concentration, largest holding, holdings as-of date, and source.                   | P0       |
| ETF-18 | Use `ExposureChart` for sector, country, or asset-class exposure when supported, without letting charts dominate the beginner summary.       | P1       |
| ETF-19 | Use `CostAndTradingCard` for expense ratio, AUM, bid-ask spread, average volume, and premium/discount where available.                      | P1       |
| ETF-20 | Use `ETFRoleCard` to explain broad/core-like, satellite, specialized, or narrow exposure without telling the user what role it should play in their portfolio. | P1       |

Acceptance criteria:

- ETF page answers "what does this fund actually hold?"
- User can tell whether the ETF is broad or narrow.
- User can see cost, concentration, and trading-context tradeoffs.
- User can compare the ETF with simpler alternatives.
- ETF role copy avoids personalized allocation advice. Safe language says a fund is broader or narrower because of what it tracks or holds; unsafe language assigns a personalized portfolio role to the user.
- ETFs outside the supported ETF manifest never render generated summaries, risks, chat, comparison CTA output, Weekly News Focus, AI Comprehensive Analysis, or exports.

### 11.6 Comparison page

Comparison is a flagship workflow, but it is separate from the home page's single-asset search. Users should be able to compare two supported stocks, two supported ETFs, or one stock and one ETF in MVP.

Recommended public routes:

```text
/compare
/compare?left=AAPL
/compare?left=VOO&right=QQQ
```

Entry points:

- Global navigation: Compare
- Asset page: Compare this asset
- Asset page: suggested comparisons
- Chat: compare-route redirect
- Home search: detected `A vs B` query

| ID    | Requirement                                                                                                                      | Priority |
| ----- | -------------------------------------------------------------------------------------------------------------------------------- | -------- |
| CP-1  | User can compare two tickers from search or asset pages.                                                                         | P0       |
| CP-2  | Comparison page shows side-by-side snapshots.                                                                                    | P0       |
| CP-3  | Comparison page explains the most important differences in plain English.                                                        | P0       |
| CP-4  | Comparison page shows "Bottom line for beginners" first.                                                                        | P0       |
| CP-5  | ETF comparison includes benchmark, expense ratio, AUM, holdings count, concentration, sector exposure, and role.                 | P0       |
| CP-6  | Stock comparison includes business model, sector/industry, financial quality, valuation context, risks, and Weekly News Focus where relevant. | P0       |
| CP-7  | Cross-type comparison explains that a single stock and an ETF are structurally different.                                        | P0       |
| CP-8  | Important comparison claims include citations.                                                                                   | P0       |
| CP-9  | System suggests common comparisons such as `VOO vs SPY`, `VTI vs VOO`, `QQQ vs VGT`, `AAPL vs MSFT`, `NVDA vs SOXX`.             | P1       |
| CP-10 | User can export/download comparison output and source list.                                                                      | P0       |
| CP-11 | Stock-vs-ETF comparison includes a dedicated template for company risk vs basket risk, business model vs holdings exposure, financials vs methodology, valuation vs cost/concentration, and idiosyncratic vs diversified risk. | P0       |
| CP-12 | `/compare` shows an empty builder with two search inputs and common beginner comparisons labeled as learning examples, not recommendations. | P0       |
| CP-13 | `/compare?left=AAPL` shows a one-sided builder with suggested second assets and short labels explaining why each suggestion appears. | P0       |
| CP-14 | Invalid comparisons block generated output when one or both assets are unsupported, out of scope, pending ingestion, or missing minimum verified data. | P0       |
| CP-15 | Partial comparisons render verified sections only and label unavailable, stale, could-not-verify, or insufficient-evidence sections. | P0       |
| CP-16 | Comparison claims may cite left-asset sources, right-asset sources, and computed comparison sources; source drawer labels which side each citation supports. | P0       |

Acceptance criteria:

- A user comparing `VOO` and `QQQ` can understand broad-market exposure versus Nasdaq-100 concentration.
- A user comparing `AAPL` and `MSFT` can understand differences in business model and risk.
- A user comparing `NVDA` and `SOXX` can understand single-company exposure versus a semiconductor ETF basket.
- The bottom-line section is educational, not prescriptive.
- Important comparison claims have citations.
- ETF-vs-ETF, stock-vs-stock, and stock-vs-ETF each use a tailored template.
- Stock-vs-ETF uses a relationship badge: direct holding comparison, related exposure, broad-market context, or weak relationship.
- Weak stock-vs-ETF relationships may be available as structural education when both assets are supported, but they are not suggested prominently.
- Unsupported or out-of-scope assets cannot generate comparison output.

Stock-vs-ETF comparison must not look like a normal peer comparison. It must clearly explain that a stock is one company while an ETF is a basket, and it should answer: "Am I looking at one company or a basket, and how does that change the kind of risk and exposure I am learning about?"

### 11.7 Weekly News Focus and AI Comprehensive Analysis

Every asset page includes a clearly labeled Weekly News Focus module with two parts:

1. **Weekly News Focus**
2. **AI Comprehensive Analysis**

This section provides timely context but remains separate from stable asset facts. It is asset-specific, not a separate market brief page.

| ID   | Requirement                                                                                                                            | Priority |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| RD-1  | Asset page includes a clearly labeled Weekly News Focus and AI Comprehensive Analysis section.                                       | P0       |
| RD-2  | Weekly News Focus uses the last completed Monday-Sunday market week plus current week-to-date through yesterday, using U.S. Eastern dates. | P0       |
| RD-3  | Weekly News Focus shows the configured maximum only when enough high-quality evidence exists; fewer than 5 items or an empty state is valid when evidence is thin. | P0       |
| RD-4  | Stock events may include earnings, guidance, major product announcements, M&A, leadership changes, legal events, or regulatory events. | P0       |
| RD-5  | ETF events may include fee changes, methodology changes, index changes, fund mergers, liquidations, or sponsor updates.             | P0       |
| RD-6  | Each focus item shows source, headline/title, published date, one-sentence summary, citation/source link, freshness, and source-quality metadata. | P0       |
| RD-7  | Weekly News Focus does not replace or rewrite canonical asset facts.                                                                 | P0       |
| RD-8  | Weekly News Focus items are deduplicated across news, filings, and issuer releases.                                                        | P0       |
| RD-9  | Weekly event records include event type, freshness state, source-quality metadata, source-use rights, allowlist status, and citation links. | P0       |
| RD-10 | AI Comprehensive Analysis includes What Changed This Week, Market Context, Business/Fund Context, and Risk Context.                 | P0       |
| RD-11 | Each AI context section uses a compact paragraph plus bullets and cites underlying Weekly News Focus items and canonical facts.            | P0       |
| RD-12 | AI Comprehensive Analysis is suppressed unless at least two approved Weekly News Focus items exist.                              | P0       |
| RD-13 | "No major Weekly News Focus items found" is a normal empty state for slow-moving assets, especially broad ETFs.                                  | P0       |
| RD-14 | V1 news and analysis content is English-first; Traditional Chinese localization, read-aloud, TTS, and generated audio are post-MVP. | P0       |
| RD-15 | Asset pages place Weekly News Focus after stable facts and before AI Comprehensive Analysis. Stable facts remain canonical.        | P0       |
| RD-16 | Each Weekly News Focus item shows event title/headline, source or publisher, published date, one-sentence beginner summary, event type, period bucket, freshness, source quality/source-use metadata where useful, and citation/source link. | P0       |
| RD-17 | AI Comprehensive Analysis appears directly after Weekly News Focus and is suppressed unless the backend returns sufficient evidence. | P0       |
| RD-18 | Reputable third-party/news items are allowed when approved, but the UI labels them as third-party reporting and shows publisher, URL, published date, retrieved date, source type, event classification, and citation link. | P0       |
| RD-19 | Full third-party article text is not displayed, exported, or stored as public evidence unless the source policy explicitly permits full text use. | P0       |

Acceptance criteria:

- Weekly News Focus and AI Comprehensive Analysis are visually separate from the beginner summary.
- Each Weekly News Focus item has at least one citation or source link.
- AI analysis factual claims have citations or uncertainty labels.
- The AI analysis labels are educational UI labels, not claims that the system is a real advisor or person.
- Weekly News Focus items come from official sources first, then approved reputable third-party/news sources when source governance and rights policy permit the intended metadata, summary, storage, display, and export behavior.
- Third-party/news items are clearly labeled as non-official reporting in the section and source drawer.
- Low-quality, duplicate, promotional, irrelevant, unapproved, and rights-disallowed news is excluded.
- The section can say "No major Weekly News Focus items found for this window" when appropriate, and this is normal for many broad ETFs.
- Weekly News Focus appears as timely context after stable facts, not above or inside the canonical asset basics.

### 11.8 Asset-specific grounded chat beta

Each asset page includes a chat module titled **Ask about this asset**. The chat answers questions using a bounded asset-specific knowledge pack, not general model memory.

MVP chat is intentionally limited. It is not a general finance chatbot.

Chat is a helper feature, not the main page. On desktop it may appear in the right helper rail or a collapsible side panel. On mobile, a sticky "Ask" action opens a bottom sheet or full-screen panel.

Supported MVP chat intents:

- definition questions
- business model questions
- ETF holdings questions
- risk questions
- comparison-style questions about the selected asset, with second-ticker questions redirected to the comparison workflow
- Weekly News Focus questions
- glossary questions
- educational suitability questions
- advice-like questions requiring safe redirect

| ID    | Requirement                                                                                                     | Priority |
| ----- | --------------------------------------------------------------------------------------------------------------- | -------- |
| GC-1  | Asset page includes an "Ask about this asset" chat module.                                                      | P0       |
| GC-2  | Chat answers are grounded in the selected asset's knowledge pack.                                               | P0       |
| GC-3  | Chat supports definition, risk, selected-asset comparison context, Weekly News Focus, glossary, and suitability-education questions. | P0       |
| GC-4  | Every answer includes direct answer, why it matters, citations for important claims, and uncertainty or limits. | P0       |
| GC-5  | Chat avoids buy/sell/hold commands.                                                                             | P0       |
| GC-6  | Chat avoids personalized allocation advice.                                                                     | P0       |
| GC-7  | Chat can say it does not know when evidence is missing.                                                         | P0       |
| GC-8  | Chat stores anonymous conversational state for follow-up questions while staying grounded.                     | P0       |
| GC-9  | Chat provides starter prompts for beginner questions.                                                           | P1       |
| GC-10 | Single-asset chat returns a compare-route suggestion when the user asks about another ticker.                    | P0       |
| GC-11 | Chat does not generate multi-asset answers inside a single-asset endpoint.                                       | P0       |
| GC-12 | Starter prompts are asset-aware: stock prompts cover company/business/financial/risk/recent context, while ETF prompts cover holdings, breadth/concentration, expense ratio, and recent context. | P1       |
| GC-13 | Chat answers visibly use Direct answer, Why it matters, Sources, and Uncertainty or limits.                     | P0       |

Acceptance criteria:

- Asking "What does this company actually sell?" returns a cited answer.
- Asking "Should I buy this?" redirects to educational framing.
- Asking "How much should I put in this?" avoids position sizing and explains learning factors instead.
- Asking "What happened recently?" answers from the Weekly News Focus layer when sufficient approved evidence exists.
- Asking `Why is QQQ different from VOO?` inside single-asset chat returns a compare redirect instead of a multi-asset answer.
- Chat responses do not invent facts when sources are missing.
- Compare redirects show copy such as "This is a comparison question. Open the comparison page so both assets can be grounded in their own source packs" plus a CTA to `/compare?left=...&right=...`.
- Local fresh-data testing should exercise live AI chat for supported golden assets so the operator can review answer quality before public deployment.

#### Accountless chat privacy

MVP chat should support grounded follow-ups without creating accounts.

- Server stores anonymous chat sessions with random IDs.
- Browser local storage stores only `conversation_id`, asset ticker, `updated_at`, and `expires_at`.
- Server stores transcript state only for follow-up grounding and client-requested export.
- Chat session TTL is 7 days from last activity.
- Users can delete transcripts from the UI; deletion clears browser state and deletes or invalidates the server session.
- Chat transcripts are not included in product analytics.
- Chat messages are not used for model training.
- Chat messages are not used for model evaluation in MVP.
- Product analytics may track aggregate events only: chat started, follow-up count, safety redirect, compare redirect, export requested, latency, and error state.
- IP address and user-agent may be retained only in short-lived abuse/security logs with a 7-day default retention.
- Rate limits apply per IP and per conversation.

### 11.9 Hybrid glossary and concept learning

Users can learn finance terms in context on asset pages, comparison pages, and chat answers. Glossary is not a major home-page workflow for MVP. The primary MVP interaction is inline: users open the glossary card from the term inside the section they are already reading.

Glossary approach:

- Curated static definitions for core finance terms.
- Optional AI-generated contextual explanation for the selected asset.
- No uncited asset-specific facts in generated glossary context.
- Inline `GlossaryTerm` triggers in relevant content sections, such as P/E in valuation context, AUM and expense ratio in ETF snapshot or cost context, and tracking error in fund-construction content.
- No large standalone "Glossary for this page" section as the primary glossary experience on MVP asset pages.
- Desktop terms support hover previews, click-to-pin behavior, and keyboard focus.
- Mobile terms support tap to open a glossary bottom sheet; long tap may also open it, but long tap must not be the only gesture.

| ID   | Requirement                                                             | Priority |
| ---- | ----------------------------------------------------------------------- | -------- |
| GL-1 | Important terms render with `GlossaryTerm` as subtle contextual help, not aggressive highlighting. | P0       |
| GL-2 | Glossary card includes simple definition.                               | P0       |
| GL-3 | Glossary card explains why the concept matters.                         | P0       |
| GL-4 | Glossary card includes common beginner mistake.                         | P0       |
| GL-5 | Glossary card shows related terms and may link to a deeper explanation when available. | P2       |
| GL-6 | Glossary cards can include grounded asset-specific context when useful. | P2       |
| GL-7 | Desktop supports `GlossaryPopover`; mobile supports `GlossaryBottomSheet`. | P0       |
| GL-8 | Asset-specific glossary context uses citations for values, comparisons, holdings, metrics, or claims about the selected asset. | P0       |
| GL-9 | MVP asset pages do not collect every glossary term into one large standalone glossary section; term help opens from inline triggers in the relevant content. | P0       |

Initial curated glossary should include 50-100 core terms, including:

- expense ratio
- AUM
- market cap
- P/E ratio
- forward P/E
- dividend yield
- revenue
- gross margin
- operating margin
- EPS
- free cash flow
- debt
- benchmark
- index
- holdings
- top 10 concentration
- sector exposure
- country exposure
- tracking error
- tracking difference
- NAV
- premium/discount
- bid-ask spread
- liquidity
- rebalancing
- market risk
- concentration risk
- credit risk
- interest-rate risk

Acceptance criteria:

- User can click "expense ratio" and understand it without leaving the page.
- User can click "operating margin" and understand why it matters.
- Glossary explanations do not overwhelm the main workflow.
- Generated context does not add unsupported asset-specific facts.
- Mobile glossary bottom sheets are readable, dismissible, and return the user to the same page position after closing.

### 11.10 Sources, citations, and freshness

Trust features are part of the core product experience.

| ID   | Requirement                                                                                                | Priority |
| ---- | ---------------------------------------------------------------------------------------------------------- | -------- |
| SC-1 | Important factual claims include citation chips.                                                           | P0       |
| SC-2 | Citation chips open the source drawer.                                                                     | P0       |
| SC-3 | Source drawer shows source title, source type, URL, published date, retrieved date, and associated claims. | P0       |
| SC-4 | Official sources receive an "official source" badge.                                                       | P1       |
| SC-5 | Page shows overall freshness.                                                                              | P0       |
| SC-6 | Each major section shows freshness or as-of date.                                                          | P0       |
| SC-7 | System shows stale, unknown, unavailable, or mixed-evidence states where needed.                           | P0       |
| SC-8 | System preserves source hierarchy: official and structured sources before news.                            | P0       |
| SC-9 | Downloaded/exported output includes source list and as-of dates.                                           | P0       |
| SC-10 | Source drawer supports citations from Weekly News Focus items and AI Comprehensive Analysis claims.       | P0       |
| SC-11 | Public `citation_id` values are opaque IDs such as `cit_...`; they do not expose raw database IDs.        | P0       |
| SC-12 | Citation resolution returns only allowed source metadata and permitted excerpts based on source-use policy. | P0       |
| SC-13 | Desktop source drawer opens as a right-side drawer; mobile source drawer opens as a bottom sheet.         | P0       |
| SC-14 | Source drawer shows whether a citation supports canonical facts, Weekly News Focus, AI analysis, left comparison asset, right comparison asset, or computed comparison output. | P0       |
| SC-15 | Source list appears near the bottom of asset and comparison pages with source title, type, publisher, official/third-party badge, dates, freshness, URL, and supported claims. | P0       |

Acceptance criteria:

- User can see where a key claim came from.
- User can distinguish official source material from news or third-party data.
- User can tell when a page or section was last updated.
- Unsupported claims are removed, regenerated, or marked as uncertain.
- A public `citation_id` resolves only to approved source metadata: source title, publisher, URL, source type, official-source status, source-use policy, published/as-of/retrieved dates, freshness state, claim role, normalized fact references, and an allowed supporting excerpt.
- A public `citation_id` never resolves to unrestricted provider payloads, full restricted article text, private raw PDF text, secrets, hidden prompts, or unrestricted raw source text.
- Citation chips should be near the supported claim and compact enough not to clutter beginner reading.

### 11.11 Export and download

V1 remains accountless, so export is the main "save for later" workflow.

| ID   | Requirement                                                                                                             | Priority |
| ---- | ----------------------------------------------------------------------------------------------------------------------- | -------- |
| EX-1 | User can download asset page summary.                                                                                   | P0       |
| EX-2 | User can download comparison output.                                                                                    | P0       |
| EX-3 | User can download chat transcript.                                                                                      | P0       |
| EX-4 | User can download source list with source titles, URLs, dates, and retrieved timestamps.                                | P0       |
| EX-5 | Exported content includes the educational disclaimer.                                                                   | P0       |
| EX-6 | Export respects provider licensing and avoids exporting full paid news articles or restricted data where not permitted. | P0       |

Supported export formats for MVP:

- Markdown
- JSON

PDF is post-MVP unless licensing and rendering requirements are resolved. Copy-to-clipboard templates may be added later, but they are not required for MVP.

Export controls appear through `ExportMenu` on asset pages, comparison pages, chat transcripts, and source lists. Dropdown labels may include:

- Download page summary
- Download source list
- Download comparison
- Download chat transcript

Acceptance criteria:

- A user can save their learning output without creating an account.
- Export includes citations, freshness dates, uncertainty labels, and the educational disclaimer.
- Export includes Weekly News Focus and AI Comprehensive Analysis when they are present on the page.
- Export includes only approved citations, source titles, URLs, source types, freshness/as-of dates, normalized facts, uncertainty labels, and excerpts permitted by source-use policy.
- Export does not include content prohibited by data-provider licenses.
- Export never includes restricted source text, unrestricted provider payloads, hidden prompts, raw model reasoning, or secrets.

### 11.12 Responsive web UX

The product should support both desktop web and mobile web from v1.

| ID   | Requirement                                                                                                    | Priority |
| ---- | -------------------------------------------------------------------------------------------------------------- | -------- |
| UX-1 | Layout is responsive across desktop, tablet, and mobile web.                                                   | P0       |
| UX-2 | Mobile layout prioritizes Beginner Summary, Top 3 Risks, Key Facts, Weekly News Focus, AI Comprehensive Analysis, contextual glossary, chat, and sources. | P0       |
| UX-3 | Desktop layout supports a main reading column plus optional helper rail, side-by-side comparison, source drawer, and richer data tables. | P0       |
| UX-4 | Chat is usable on mobile as a bottom sheet or full-screen panel without covering core content permanently.     | P1       |
| UX-5 | Tables collapse, stack, or simplify on mobile; horizontal scrolling is avoided except for dense tables that cannot be simplified. | P1       |
| UX-6 | Mobile comparison uses stacked sections: bottom line, Asset A card, Asset B card, key differences, expandable details, and sources. | P0       |
| UX-7 | Loading states use skeletons for asset header, beginner cards, risk cards, and key facts; loading copy must not imply model memory. | P0       |
| UX-8 | Error states avoid exposing internal provider, model, API-key, infrastructure, or queue details.              | P0       |

Acceptance criteria:

- Beginner section is comfortable on a phone.
- Comparison is usable on desktop and acceptable on mobile through stacked sections.
- Source inspection works on both desktop and mobile.
- Home search loading says "Searching supported stocks and ETFs..."
- Chat loading says "Checking this asset's sources..."
- Source drawer loading says "Loading source details..."

### 11.13 Rate limits and abuse controls

The MVP should ship with conservative, environment-configurable defaults that protect the free-tier deployment and keep ingestion costs predictable.

| ID   | Requirement                                                                                                 | Priority |
| ---- | ----------------------------------------------------------------------------------------------------------- | -------- |
| RL-1 | Search is limited to `60/min/IP` by default.                                                                | P0       |
| RL-2 | Chat is limited to `20/hour/conversation` by default.                                                       | P0       |
| RL-3 | Ingestion requests are limited to `5/hour/IP` by default.                                                   | P0       |
| RL-4 | Rate-limit responses explain the educational product limit without exposing implementation internals.        | P1       |

Acceptance criteria:

- Search abuse does not trigger broad provider ingestion or LLM calls.
- Chat and ingestion limits are enforced before expensive provider, retrieval, or LLM work starts.
- Admin ingestion can use stricter authentication and quota rules than public search.

---

## 12. Content requirements

### 12.1 Stock page content model

Each stock page should include:

1. **Asset header and key facts**
   - name
   - ticker
   - sector
   - industry
   - exchange
   - market cap
   - delayed or best-effort price, last close, or a clear unavailable state
   - last updated

2. **Beginner summary**
   - what the business does
   - why people consider it
   - why beginners should be careful

3. **Business overview**
   - products and services
   - business segments
   - revenue drivers
   - geographic exposure
   - competitors

4. **Strengths**
   - competitive advantage
   - scale, brand, switching costs, technology, or other source-backed strengths
   - industry tailwinds where supported

5. **Financial quality**
   - revenue trend
   - EPS trend
   - gross margin
   - operating margin
   - free cash flow
   - debt
   - cash
   - ROIC or ROE where available

6. **Risks**
   - exactly three top risks first
   - expandable detail

7. **Valuation context**
   - P/E
   - forward P/E when sourced
   - price/sales
   - price/free cash flow
   - peer context
   - own-history context

8. **Weekly News Focus and AI Comprehensive Analysis**
   - earnings
   - guidance
   - major product announcements
   - M&A
   - leadership changes
   - regulatory or legal events

9. **Ask about this asset**
   - stock-specific starter prompts
   - direct answer / why it matters / sources / uncertainty answer shape
   - compare-route redirect for second-ticker questions

10. **Sources and export**
   - source list
   - source drawer metadata
   - Markdown/JSON export controls
   - educational disclaimer

### 12.2 ETF page content model

Each ETF page should include:

1. **Asset header and key facts**
   - name
   - ticker
   - issuer/provider
   - category
   - asset class
   - passive or active
   - benchmark/index
   - expense ratio
   - AUM
   - last updated

2. **Beginner summary**
   - what the ETF is trying to do
   - why beginners consider it
   - main catch or beginner misunderstanding

3. **ETF role**
   - broad/core-like, satellite, or specialized/narrow exposure
   - intended purpose
   - simpler alternatives

4. **What it holds**
   - number of holdings
   - top 10 holdings
   - top 10 concentration
   - sector breakdown
   - country breakdown when relevant
   - largest position

5. **Construction**
   - weighting method
   - rebalancing frequency
   - screening rules
   - notable methodology details

6. **Cost and trading**
   - expense ratio
   - bid-ask spread
   - average daily volume
   - AUM
   - premium/discount information where available

7. **Risks**
   - market risk
   - concentration risk
   - liquidity risk
   - complexity risk
   - interest-rate or credit risk when relevant
   - currency risk when relevant

8. **Comparison and overlap**
   - similar ETFs
   - simpler alternatives
   - overlap with broad-market ETF
   - whether it adds diversification

9. **Weekly News Focus and AI Comprehensive Analysis**
   - fee changes
   - methodology changes
   - index changes
   - fund merger or liquidation news
   - sponsor updates

10. **Ask about this asset**

- ETF-specific starter prompts
- holdings, breadth, expense ratio, concentration, and recent-context questions
- compare-route redirect for second-ticker questions

11. **Sources and export**

- source list
- source drawer metadata
- Markdown/JSON export controls
- educational disclaimer

---

## 13. Knowledge and source strategy

### 13.1 Three-layer knowledge model

The product should maintain a three-layer knowledge architecture.

#### Layer 1: Canonical facts

Stable source-backed asset facts.

For stocks:

- identity
- sector and industry
- filings-derived business summary
- multi-year financials
- balance sheet and cash flow trends
- filing-derived risk language

For ETFs:

- issuer/provider
- benchmark
- holdings
- sector and country exposure
- methodology
- expense ratio
- AUM
- trading-cost context

#### Layer 2: Timely context

Weekly News Focus developments and events.

Examples:

- earnings and guidance
- product launches
- acquisitions
- legal or regulatory events
- ETF methodology or fee changes
- fund merger or closure news
- sponsor announcements

This layer must never overwrite canonical facts.

#### Layer 3: Teaching and explanation

AI-generated plain-English explanation.

The model may:

- rewrite source material in beginner language
- answer beginner questions
- explain jargon
- compare two assets
- highlight what matters most for a beginner

The model must not become the source of truth.

### 13.2 Source hierarchy

#### For stocks

1. SEC EDGAR, SEC XBRL company facts, and SEC filing documents
2. Company investor relations pages
3. Earnings releases and presentations
4. Free/reference metadata or approved provider enrichment
5. Official sources and approved reputable third-party/news sources for Weekly News Focus

#### For ETFs

1. ETF issuer official page
2. ETF fact sheet
3. Summary prospectus and full prospectus
4. Shareholder reports
5. Issuer holdings files, exposure files, and official ETF website disclosures
6. Sponsor announcements, official sources, and approved reputable third-party/news sources for Weekly News Focus
7. Free/reference metadata or approved provider enrichment

### 13.3 Recommended market/reference data stack

Recommended MVP stack:

1. **Canonical stock filings and facts:** SEC EDGAR submissions API and XBRL company facts.
2. **Official ETF facts:** issuer page, fact sheet, holdings file, summary prospectus, full prospectus, shareholder reports.
3. **Free/reference metadata:** free exchange, SEC, issuer, and public metadata where available for ticker reference, delayed or best-effort prices, snapshots, volume, and trading context.
4. **Provider adapters:** adapter interfaces for paid or low-cost providers, disabled by default unless keys and licensing are configured.
5. **Fixtures and mocks:** deterministic fixtures for golden assets and provider mocks for CI, parser tests, and LLM evaluation.

Provider strategy:

- SEC EDGAR, SEC XBRL company facts, and SEC filing documents are the trust backbone for stocks such as `AAPL` and `NVDA`.
- Official issuer pages, fact sheets, prospectuses, shareholder reports, holdings files, exposure files, and sponsor announcements are the trust backbone for ETFs such as `VOO`, `QQQ`, and `SOXX`.
- Structured enrichment providers can improve convenience and coverage only when licensing, rate limits, caching, attribution, display, and export rights allow the intended product use.
- FMP, Finnhub, Tiingo, Alpha Vantage, EODHD, yfinance, and similar services are optional enrichment only. Their payloads must not override official SEC or issuer evidence, and unclear rights limit them to internal diagnostics, enrichment, or metadata-only use.
- Quote fields in the MVP are delayed or best-effort. The UI must label freshness and must show `unavailable` when quote data cannot be verified instead of implying real-time coverage.
- yfinance is allowed only for local development or fallback diagnostics and must not become production truth or a public redistributable data source.

Provider-selection requirements:

- Must support commercial use needed by the app before production use.
- Must permit the required display, caching, and export behavior.
- Must provide clear data freshness or as-of fields.
- Must support U.S.-listed stocks and manifest-approved supported U.S. equity ETFs at MVP scale.
- Must have documented rate limits and reliable API behavior.
- Must allow attribution/source labeling where required.

### 13.4 Recommended Weekly News Focus and analysis stack

Recommended MVP stack:

1. **Official first:** SEC filings, company IR releases, ETF issuer announcements, prospectus updates, fact-sheet updates, and sponsor notices.
2. **Approved reputable third-party/news sources:** curated sources with source metadata, dates, categories, ticker/entity matching, published timestamps, official-vs-third-party labels, and source-use rights. These sources broaden coverage but must not be presented as official.
3. **Weekly News Focus selection:** deduplicate, score, and select up to the configured maximum for the selected asset's Weekly News Focus pack; show fewer items or an empty state when evidence is thin.
4. **Rights-gated full text:** reputable news reputation does not automatically approve full article text. Full text storage, display, or export requires `full_text_allowed` or explicit reviewed rights.
5. **Rejected by default:** unrecognized or low-quality sources should not be used for Weekly News Focus until added to the allowlist.
6. **Paid future option:** ticker-tagged news APIs or premium news providers may be added later when budget and licensing justify them.

Source-use categories:

- `metadata_only`
- `link_only`
- `summary_allowed`
- `full_text_allowed`
- `rejected`

Approval statuses:

- `approved`
- `pending_review`
- `rejected`

Source allowlist governance:

- The source allowlist lives in config, e.g. `config/source_allowlist.yaml`.
- Config-only review means a future agent may update the allowlist only when source-use policy, source type, domain, official-source status, storage rights, export rights, rationale, and validation tests are updated together.
- Automated scoring cannot approve new sources. It only ranks sources already present in the allowlist.
- Allowlist records must include `source_use_policy`: `metadata_only`, `link_only`, `summary_allowed`, `full_text_allowed`, or `rejected`.

Operational source rule:

- Fetch only from allowlisted sources.
- Store according to source-use policy.
- Generate only from approved evidence.
- Export only what the policy permits.
- Always allow approved source metadata needed for attribution: headline/title, publisher, URL, published date, retrieved date, source type, official-vs-third-party label, topic/event classification, and citation link.
- Allow beginner summaries of approved reputable third-party/news items, but avoid reproducing full article text unless the source policy permits full text.
- Mark missing, unclear, hidden/internal, parser-invalid, or unapproved sources as `pending_review` or `rejected` instead of using them as evidence.

Weekly News Focus items should be filtered for:

- relevance to the asset
- source quality
- event importance
- recency
- non-duplication
- non-promotional tone
- allowlist status
- source-use rights

Weekly News Focus scoring defaults:

```text
importance_score =
  source_quality_weight
+ event_type_weight
+ recency_weight
+ asset_relevance_weight
- duplicate_penalty
```

| Scoring field | Defaults |
| --- | --- |
| `source_quality_weight` | official `5`; approved_reputable_third_party `3`; provider_metadata_only `1` |
| `event_type_weight` | earnings `5`; guidance `5`; fee_change `5`; methodology_change `5`; routine_press_release `1` |
| `recency_weight` | current_week_to_date `3`; previous_market_week `2`; older_but_relevant `1` |
| `asset_relevance_weight` | exact ticker/CIK/issuer match `3`; strong fund/company match `2`; sector/theme context only `1` |
| `duplicate_penalty` | exact duplicate `5`; near duplicate `3`; same story cluster after first item `2` |

Thresholds:

- `minimum_display_score = 7`
- `minimum_ai_analysis_items = 2`
- Source-use policy wins over score: rejected or rights-disallowed sources never display, regardless of `importance_score`.

AI Comprehensive Analysis should be generated only from the selected asset's Weekly News Focus pack and cited canonical facts. It requires at least two approved Weekly News Focus items, starts with What Changed This Week, then uses Market Context, Business/Fund Context, and Risk Context. It should not introduce uncited market predictions or recommendation language.

Local fresh-data validation should include assets and time windows where at least two approved Weekly News Focus items exist so the operator can review live AI Comprehensive Analysis quality before public deployment.

### 13.5 Raw source text policy

The MVP uses a rights-tiered raw source text policy.

- Official filings, issuer materials, and reviewed `full_text_allowed` sources may store raw text, parsed text, chunks, checksums, and source snapshots.
- `summary_allowed` sources may store metadata, checksums, links, source-provided snippets, generated summaries, and limited excerpts needed to support summaries. Third-party/news excerpts are capped at 90 words only when the source-use policy permits excerpts; length alone never approves full text.
- `metadata_only` and `link_only` sources may store metadata, hashes, canonical URLs, timestamps, and source-use diagnostics, but not full article text.
- `rejected` sources are not used for generated output and should keep only rejection diagnostics when needed for debugging.
- Exports and citation drawers must honor the same policy and never reveal unrestricted restricted text.

---

## 14. Citation policy

### 14.1 What requires citation

Citations are required for important factual claims, including:

- business description
- ETF objective and benchmark
- expense ratio
- AUM
- market cap
- price or last close
- holdings count
- top holdings
- top 10 concentration
- sector or country exposure
- valuation metrics
- revenue, EPS, margins, cash flow, debt, cash
- risk statements
- Weekly News Focus and AI Comprehensive Analysis
- comparison claims
- claims using words such as "largest," "cheaper," "broader," "narrower," "more concentrated," "higher," or "lower"

Claims may need multiple citations. Comparison claims should be able to cite left-side and right-side evidence separately, such as `comparison_left` and `comparison_right`, so statements like "VOO is broader than QQQ" are supported by both assets.

### 14.2 What does not require citation

Citations are not required for generic educational explanations that do not include asset-specific facts.

Examples:

- "An expense ratio is the annual fee charged by a fund."
- "Diversification means spreading exposure across multiple holdings."
- "A higher valuation can mean investors expect more future growth."
If a generic explanation includes a specific value or asset-specific comparison, it requires a citation.

### 14.3 Citation validation behavior

| Failure                              | Product behavior                                                     |
| ------------------------------------ | -------------------------------------------------------------------- |
| Missing citation for important claim | Regenerate once, then remove the claim or mark as uncited/uncertain. |
| Weak citation                        | Replace with stronger evidence or mark uncertainty.                  |
| Unsupported claim                    | Drop claim and log unsupported-claim event.                          |
| Stale citation                       | Show stale badge or suppress claim depending on importance.          |
| Wrong-asset citation                 | Reject and regenerate.                                               |
| Advice-like claim                    | Rewrite using safety redirect template.                              |

---

## 15. UX requirements

The frontend should feel like a calm learning product, not a trading dashboard. It should feel closer to source-grounded notes plus simple explanations and clean stock/ETF fact sheets than to a chart-first trading screen.

Recommended top-level routes:

```text
/                                  Home page: single stock/ETF search
/assets/[ticker]                   Stock or ETF asset page
/assets/[ticker]/sources           Optional source-list deep link
/compare                           Empty comparison builder
/compare?left=AAPL                 Comparison builder with first asset selected
/compare?left=VOO&right=QQQ        Completed comparison page
```

Optional post-MVP route:

```text
/glossary/[term]                   Optional post-MVP full glossary detail page
```

Recommended desktop navigation:

```text
Learn the Ticker        Search     Compare
```

Recommended mobile navigation:

```text
Learn the Ticker                         Menu
```

Mobile menu:

```text
Search
Compare
```

Do not make Glossary a primary top-nav item for MVP unless the project already has a glossary page. Glossary should primarily appear contextually when users interact with finance terms inside content.

### 15.1 Beginner section

The Beginner section is the first section on the asset page.

It should prioritize:

- `BeginnerSummaryCard`
- simple explanations
- three short summary cards
- `RiskCards` with exactly three top risks first
- `KeyFactsGrid`
- plain-language summaries
- contextual glossary terms
- visible citations
- minimal jargon
- clear next steps for learning

Acceptance criteria:

- User does not need to understand filings, ratios, or ETF methodology to get value.
- Advanced details are available but not forced into the first view.

### 15.2 Deep-Dive section

The Deep-Dive section expands the page for users who want more detail.

It should include:

- detailed financial metrics
- segment or exposure breakdowns
- source-specific nuance
- peer comparison
- methodology details
- full source list
- source dates and freshness
- export controls

Acceptance criteria:

- Deep-Dive section adds depth without changing the beginner summary.
- Users can inspect the evidence behind the summary.

### 15.3 Source drawer

`SourceDrawer` opens as a right-side drawer on desktop and a bottom sheet on mobile. It should show:

- citation ID
- source title
- source type
- official/third-party badge
- publisher
- published date
- as-of date where applicable
- retrieved timestamp
- source URL
- freshness state
- source-use policy
- related claims
- whether the citation supports canonical facts, Weekly News Focus, AI Comprehensive Analysis, left comparison asset, right comparison asset, or computed comparison output
- relevant excerpt or chunk where allowed

Acceptance criteria:

- User can trace important claims to sources.
- Official sources are visually distinguished from news or third-party data.
- Source drawer never shows unrestricted restricted article text, private raw PDF text, provider secrets, hidden prompts, raw model reasoning, or unrestricted provider payloads.

### 15.4 Citation chips

Citation chips should be:

- visible near the claim they support
- compact enough not to clutter beginner reading
- clickable
- connected to the source drawer

Acceptance criteria:

- User can inspect sources without losing reading flow.
- Claims without support are not given citation chips.

### 15.5 Glossary cards

Glossary cards should open as `GlossaryPopover` on desktop and `GlossaryBottomSheet` on mobile. `GlossaryTerm` rendering should use a subtle dotted underline, accessible focus style, and no aggressive highlighting.

`GlossaryTerm` should wrap the actual term text where it appears in the reading flow. Examples: P/E in valuation context, AUM and expense ratio in ETF snapshot or cost context, and tracking error in fund-construction content. MVP asset pages should not rely on a single "Glossary for this page" section as the main way to reference terms.

Each glossary card should include:

- simple definition
- why it matters
- common beginner mistake
- optional deeper link
- related terms
- optional grounded asset-specific context

Acceptance criteria:

- Glossary explanations are short and practical.
- Glossary cards help users continue the main task.
- Glossary cards open from inline term triggers inside the relevant section rather than from an aggregate glossary list.
- Desktop supports hover preview, click-to-pin, and keyboard focus.
- Mobile supports tap to open the bottom sheet; long tap may also open it, but it is not the only gesture.

### 15.6 Mobile and desktop behavior

Mobile should emphasize:

- Beginner Summary
- Top 3 Risks
- Key Facts
- Weekly News Focus and AI Comprehensive Analysis
- contextual glossary cards
- chat
- sources

Mobile sticky actions on asset pages:

```text
Ask
Compare
Sources
```

Mobile sticky actions on comparison pages:

```text
Swap
Change
Sources
```

Desktop should emphasize:

- main reading column plus optional helper rail
- Deep Dive
- side-by-side comparison
- source drawer as right panel
- tables and charts
- richer source inspection

Acceptance criteria:

- The same product works on mobile and desktop.
- Desktop gets more layout depth; mobile stays readable and practical.

### 15.7 Loading, skeleton, and error states

Required loading copy:

```text
Searching supported stocks and ETFs...
Checking Weekly News Focus...
Loading source details...
Checking this asset's sources...
```

Asset pages should use skeletons for Asset Header, Beginner Summary cards, RiskCards, and KeyFactsGrid. The UI must not show fake data. Error states should say:

```text
Something went wrong loading this section.

Try again, or review the available sources below.
```

Error states must not expose internal provider, model, API-key, infrastructure, queue, or secret details.

### 15.8 Frontend component inventory

Recommended components:

```text
SearchBox
AutocompleteResults
SearchResultRow
StatusChip
FreshnessBadge
AssetHeader
BeginnerSummaryCard
RiskCards
KeyFactsGrid
BusinessOverview
FinancialTrendsTable
ValuationContextCard
HoldingsTable
ExposureChart
CostAndTradingCard
ETFRoleCard
WeeklyNewsPanel
AIComprehensiveAnalysisPanel
CitationChip
SourceDrawer
SourceList
GlossaryTerm
GlossaryPopover
GlossaryBottomSheet
AssetChatPanel
CompareBuilder
CompareAssetInput
CompareSuggestionList
CompareHeader
CompareSnapshotCards
CompareKeyDifferences
ComparisonRelationshipBadge
StockVsStockComparison
EtfVsEtfComparison
StockVsEtfComparison
ExportMenu
UnsupportedAssetNotice
PendingIngestionNotice
PartialDataNotice
EducationalDisclaimer
```

### 15.9 Frontend analytics events

Track aggregate product events only, such as:

```text
search_started
search_result_selected
unsupported_asset_viewed
asset_page_viewed
beginner_section_viewed
deep_dive_opened
citation_chip_clicked
source_drawer_opened
glossary_term_hovered
glossary_term_opened
compare_started
compare_completed
compare_suggestion_clicked
chat_started
chat_message_sent
chat_safety_redirect
chat_compare_redirect
export_requested
partial_data_notice_viewed
```

Do not log raw chat transcript content, unrestricted source text, hidden prompts, raw model reasoning, restricted provider payloads, provider secrets, personal portfolio details, or allocation information.

---

## 16. Safety and compliance guardrails

### 16.1 Product stance

The product is educational and informational. It does not provide personalized investment, financial, legal, or tax advice.

### 16.2 Required guardrails

| ID    | Guardrail                                                                     | Priority |
| ----- | ----------------------------------------------------------------------------- | -------- |
| SG-1  | Do not use direct buy/sell/hold language.                                     | P0       |
| SG-2  | Do not provide personalized allocation or position sizing.                    | P0       |
| SG-3  | Do not provide unsupported price targets.                                     | P0       |
| SG-4  | Distinguish stable facts from Weekly News Focus and AI Comprehensive Analysis. | P0       |
| SG-5  | Cite important claims.                                                        | P0       |
| SG-6  | Say "unknown," "not available," or show uncertainty when evidence is missing. | P0       |
| SG-7  | Block unsupported complex products from generated pages and chat.             | P0       |
| SG-8  | Avoid market prediction phrased as certainty.                                 | P0       |
| SG-9  | Redirect personalized questions into educational frameworks.                  | P0       |
| SG-10 | Include disclaimer in page footer and exported content.                       | P0       |
| SG-11 | Treat retrieved source text as untrusted evidence and ignore instructions inside retrieved documents. | P0       |
| SG-12 | Run citation validation after generation before rendering or export.          | P0       |
| SG-13 | Block advice-like output even when source text contains promotional language. | P0       |
| SG-14 | Sanitize HTML/PDF content before rendering.                                   | P0       |
| SG-15 | Use allowlisted domains or controlled URL resolution for ingestion fetchers to reduce SSRF risk. | P0       |

Source evidence must never override system or developer instructions. Retrieved chunks can support facts, but they cannot change safety policy, citation policy, source policy, or output format requirements.

### 16.3 Suggested persistent disclaimer

Use this or a legally reviewed variation:

> This page is for educational and research purposes only. It is not investment, financial, legal, or tax advice and is not a recommendation to buy, sell, or hold any security. Content is generated from public filings, issuer materials, market/reference data, and news sources where available. Data may be delayed, incomplete, inaccurate, or outdated. Please review the cited sources and consider consulting a qualified professional before making financial decisions.

### 16.4 Suggested advice-like question redirect

Use this pattern in chat and other interactive flows:

> I can't tell you whether to buy, sell, hold, or how much to invest. I can help you understand what this asset is, what it holds or does, its main risks, how it compares with alternatives, and what questions a beginner may want to research before making their own decision.

### 16.5 Compliance review requirement

Before public launch, the product should receive legal/compliance review for:

- disclaimer wording
- advice boundaries
- recommendation-risk language
- data-provider licensing
- export/download behavior
- source attribution
- Golden Asset Source Handoff approval criteria
- chat safety behavior

---

## 17. Caching, freshness, and accountless v1

### 17.1 Accountless v1

V1 should not require user accounts.

Users can still save learning outputs by downloading:

- asset page summary
- comparison output
- chat transcript
- source list
- citation/freshness metadata

Saved assets, saved comparisons, watchlists, and user profiles should be deferred.

### 17.2 Cost reduction through backend caching

API and LLM cost reduction should be handled through shared server-side caching, not user accounts.

Example:

- User A opens `QQQ` at 10:00 AM.
- The system generates or refreshes the asset page.
- User B opens `QQQ` at 10:10 AM.
- If freshness rules still pass, User B gets the cached result.

Recommended mechanisms:

- data TTLs by source type
- source-document checksums
- freshness hashes for generated summaries
- cache invalidation when source facts change
- versioned facts and generated summaries so superseded values remain audit-readable
- cached knowledge packs for popular assets
- pre-cached high-demand universe

### 17.3 Freshness display

The system should show:

- page last updated
- section last updated
- facts as of date
- holdings as of date
- Weekly News Focus checked at
- retrieved timestamp for sources

Example:

```text
Page last updated: Apr 22, 2026
Holdings as of: Apr 21, 2026
Weekly News Focus checked: Apr 22, 2026
```

---

## 18. Success metrics

### 18.1 Product metrics

| Metric                             | Definition                                                                           | Target direction |
| ---------------------------------- | ------------------------------------------------------------------------------------ | ---------------- |
| Search success rate                | Percentage of searches that resolve to a supported or clear unsupported state        | Increase         |
| Unsupported asset rate             | Percentage of searches for unsupported assets                                        | Monitor          |
| Asset-page completion rate         | Percentage of users who read or interact past the beginner summary                   | Increase         |
| Compare-page usage                 | Percentage of sessions using comparison                                              | Increase         |
| Chat follow-up rate                | Percentage of chat users asking at least one follow-up                               | Increase         |
| Glossary usage                     | Percentage of sessions using glossary cards                                          | Increase         |
| Source drawer open rate            | Percentage of sessions opening at least one source                                   | Increase         |
| Export usage                       | Percentage of sessions downloading page, comparison, source list, or chat transcript | Increase         |
| Latency to first meaningful result | Time from search to initial useful asset page content                                | Decrease         |

### 18.2 Trust metrics

| Metric                      | Definition                                                     | Target direction |
| --------------------------- | -------------------------------------------------------------- | ---------------- |
| Citation coverage rate      | Percentage of important claims with citations                  | Increase         |
| Unsupported claim rate      | Percentage of generated claims without source support          | Decrease         |
| Weak citation rate          | Percentage of citations judged insufficient                    | Decrease         |
| Freshness accuracy          | Percentage of displayed freshness labels matching source state | Increase         |
| Safety redirect rate        | Rate of advice-like questions redirected safely                | Monitor          |
| Hallucination incident rate | Verified unsupported factual outputs reaching users            | Decrease         |
| Stale data incident rate    | Verified stale data shown without warning                      | Decrease         |

### 18.3 User-learning metrics

| Metric                            | Measurement approach                                           |
| --------------------------------- | -------------------------------------------------------------- |
| Understanding of "what this is"          | Post-page quick prompt or feedback survey                      |
| Understanding of "why people use it"     | Post-page quick prompt or feedback survey                      |
| Understanding of "main risks"            | Post-page quick prompt or feedback survey                      |
| Trust in citations                | Source drawer usage and trust survey                           |
| Confidence without overconfidence | Survey asking whether user feels informed, not told what to do |

---

## 19. Release plan

### 19.1 MVP / v1

Objective: Ship a credible, source-grounded, accountless beginner explainer for the top 500 U.S.-listed common stocks first and the manifest-approved supported U.S. equity ETF universe.

The phases below describe MVP scope and delivery milestones. They do not relax the acceptance checklist or safety, citation, source-use, freshness, and no-advice requirements.

Before public deployment, the operator should validate the full product locally with fresh data, the approved golden assets, live AI enabled for generated features, and a small number of limited local users. This is a local/private-test practice, not an in-product account system or release stage. Public v1 remains fully accountless and requires the full approved top-500 stock manifest plus approved supported ETF manifest.

Included:

- Search and entity resolution
- Home page with one primary action: search one stock or ETF
- Supported/unsupported asset classification
- Stock page
- ETF page
- Beginner section
- Deep-Dive section baseline
- Compare two assets
- Dedicated comparison builder and comparison pages
- Basic ETF overlap/concentration indicators
- Weekly News Focus and AI Comprehensive Analysis block
- Source drawer
- Citation chips
- Hybrid glossary baseline
- Contextual glossary cards in asset pages, comparison pages, and chat answers
- Limited asset-specific grounded chat beta
- Markdown/JSON export/download for page, comparison, sources, and chat transcript
- Educational disclaimer and safety redirects
- Server-side caching and freshness labels
- Responsive web UX

Not included:

- User accounts
- Saved assets and saved comparisons
- Watchlists
- Portfolio tools
- Trading
- Tax guidance
- Native mobile app
- Full general-purpose finance chatbot
- PDF exports

### 19.2 Post-MVP / v1.1

Objective: Improve trust, performance, and coverage quality.

Potential additions:

- Better comparison recommendations
- Improved ETF overlap analysis
- More robust issuer parsers
- Richer source-state handling
- Better glossary coverage
- Expanded export templates
- Evaluation dashboard for citation quality and safety

### 19.3 Phase 2

Objective: Expand learning and retention workflows after MVP is trustworthy.

Potential additions:

- User accounts
- Saved assets
- Saved comparisons
- Watchlists
- Learning paths
- Beginner lessons tied to asset pages
- More advanced comparison workflows

### 19.4 Phase 3

Objective: Expand from limited asset-specific chat to richer grounded tutoring.

Potential additions:

- Multi-asset chat sessions
- Guided learning paths
- Deeper explain-like-I'm-new content
- More sophisticated retrieval and citation validation
- Optional user preferences if accounts exist

---

## 20. MVP acceptance checklist

The MVP is ready when:

- User can search a supported top-500 U.S.-listed common stock or a manifest-approved supported U.S. equity ETF.
- Public v1 uses a full approved top-500 stock manifest; smaller golden or local reviewed test sets are acceptable only for local validation.
- ETF support is controlled by `data/universes/us_equity_etfs_supported.current.json`; `data/universes/us_etp_recognition.current.json` can identify unsupported ETPs for blocked search states only.
- Home page has one primary action: search one stock or ETF.
- Home page does not present comparison or Glossary as a primary workflow.
- Search autocomplete supports partial ticker/name/issuer matches and support-state chips.
- Natural `A vs B` search patterns route to comparison.
- System resolves the asset correctly.
- Unsupported assets are blocked clearly.
- Exact recognized-but-unsupported ticker searches show a blocked state rather than generated content.
- Golden Asset Source Handoff blocks unapproved, unclear-rights, parser-invalid, hidden/internal, and rejected sources from storage as evidence, generation, citation, and export.
- User lands on the correct stock or ETF page.
- Asset pages show the Beginner Summary first.
- Exactly three top risks are shown first.
- Weekly News Focus and AI Comprehensive Analysis are separated from stable facts.
- Important factual claims have visible citations.
- Citation chips open a source drawer or mobile bottom sheet.
- Source drawer shows source metadata, freshness, source-use policy, related claim, and allowed excerpt.
- Glossary terms appear contextually inside asset, comparison, and chat content.
- Desktop glossary supports hover, click, and keyboard focus; mobile glossary supports tap and opens as a bottom sheet.
- Page and sections show freshness/as-of dates.
- Product avoids buy/sell/hold and allocation advice.
- User can compare stock-vs-stock, ETF-vs-ETF, and stock-vs-ETF supported assets.
- Comparison includes a non-prescriptive beginner bottom line.
- Stock-vs-ETF uses a special single-company-vs-ETF-basket template with relationship badges.
- Weak stock-vs-ETF comparisons are allowed only as structural education and are not suggested prominently.
- Limited asset-specific chat answers from the selected asset knowledge pack.
- Advice-like chat questions are redirected safely.
- Single-asset chat redirects second-ticker questions to the comparison page.
- User can export page, comparison, source list, and chat transcript.
- Product analytics track aggregate citation coverage, unsupported claims, glossary usage, comparison usage, source drawer usage, export usage, safety redirects, and freshness accuracy without raw chat transcript content.
- Weekly News Focus renders the configured maximum only when enough high-quality approved evidence exists, fewer when evidence is limited, and zero when no major Weekly News Focus items exist.
- Weekly News Focus labels official and third-party/news sources distinctly and exposes publisher, URL, dates, source type, event classification, and citation details.
- AI Comprehensive Analysis includes What Changed This Week, Market Context, Business/Fund Context, and Risk Context with citations or uncertainty labels when at least two approved Weekly News Focus items exist.
- Live AI generation for grounded chat and AI Comprehensive Analysis has been validated locally against fresh data before public deployment.
- Mobile layouts are readable and use bottom sheets for sources, glossary, and chat where appropriate.
- Exports support Markdown and JSON and include disclaimer, citations, freshness metadata, uncertainty labels, source list, Weekly News Focus, and AI Comprehensive Analysis when present.
- Accountless chat sessions use random IDs, 7-day TTL, user deletion, and no chat-message analytics, training, or model-evaluation use in MVP.

Strict MVP quality gates:

- 100% of important factual claims in golden-path generated outputs have valid citations or explicit uncertainty/unavailable labels.
- Zero known buy/sell/hold, allocation, tax, guaranteed-return, or unsupported price-target violations in golden tests.
- Cached search, asset pages, comparison pages, source drawer, and chat meet the performance targets in the technical design spec.
- CI includes unit, integration, schema, citation validation, safety, export, and golden asset tests.
- Golden tests verify that `AAPL` and `NVDA` canonical facts prefer SEC EDGAR/XBRL/filing documents, while supported golden ETF canonical facts prefer the supported ETF manifest plus issuer materials.
- Golden tests verify that duplicate, promotional, irrelevant, unapproved, and rights-disallowed news is excluded from Weekly News Focus.
- Golden tests verify that reputable third-party/news items can appear when approved, clearly labeled, summarized safely, and not exported as full article text unless `full_text_allowed`. Permitted excerpts remain bounded, with a maximum of 90 words for third-party/news sources.
- Golden tests verify Monday-Sunday plus current week-to-date through yesterday windowing.
- Golden tests verify prompt-injection, source-sanitization, SSRF-defense, chat privacy, rate-limit, many-citation, fact-versioning, and stock-vs-ETF comparison scenarios.
- Documentation hygiene scans verify no mojibake, private-use corruption, stale AI labels, duplicate requirement IDs, or stale weekly-window language remains.

---

## 21. Key risks and mitigations

### 21.1 Hallucinated or unsupported claims

Risk: the model may generate claims not supported by sources.

Mitigation:

- Use source-backed knowledge packs.
- Require citations for important claims.
- Validate citation IDs and numeric values.
- Regenerate, remove, or mark unsupported claims.
- Track unsupported claim rate.

### 21.2 Users mistake education for advice

Risk: beginners may interpret explanations as recommendations.

Mitigation:

- Avoid buy/sell/hold language.
- Use educational suitability framing.
- Include persistent disclaimer.
- Add inline redirects for advice-like questions.
- Do legal/compliance review before public launch.

### 21.3 Stale data reduces trust

Risk: financial data, holdings, fees, prices, and news can become stale.

Mitigation:

- Show page and section freshness.
- Cache with explicit refresh rules.
- Invalidate summaries when source facts change.
- Show stale states clearly.

### 21.4 Source quality varies

Risk: issuers, filings, and third-party sources may provide inconsistent or incomplete information.

Mitigation:

- Use source hierarchy.
- Prefer official and structured sources.
- Separate news from canonical facts.
- Display uncertainty or mixed-evidence states.

### 21.5 Provider licensing limits downloads

Risk: market/news provider licenses may restrict caching, redistribution, or export.

Mitigation:

- Treat API fetching as retrieval only, not approval.
- Review provider contracts before launch.
- Keep provider data optional enrichment that cannot override official SEC or issuer evidence.
- Export only allowed fields and excerpts.
- Include attribution where required.
- Avoid exporting full paid news articles.

### 21.6 Scope creep

Risk: the product could become a trading, portfolio, or advice product.

Mitigation:

- Keep v1 focused on education for stocks and manifest-approved supported U.S. equity ETFs.
- Block unsupported products.
- Defer user accounts and portfolio features.
- Evaluate every feature against the core promise: help beginners understand what they are looking at.

---

## 22. Appendix A: External source notes for provider decisions

These sources support the provider and compliance direction in this PRD. V1 is free-first and assumes no paid provider keys. Paid provider notes below are optional future integration references and require pricing, reliability, coverage, caching, export, and licensing review before production use.

Provider role summary:

- SEC EDGAR, SEC XBRL company facts, and SEC filing documents are the primary official sources for stock identity, filings history, filing-derived business descriptions, financial facts, and risk extraction.
- Official ETF issuer materials are the primary source for ETF identity, holdings, fees, methodology, exposures, and fund risks.
- The supported ETF manifest is the primary runtime policy for ETF coverage; issuer materials are the primary evidence source after manifest approval.
- Financial Modeling Prep, Finnhub, Tiingo, Alpha Vantage, EODHD, yfinance, and similar providers may be used only as enrichment where licensing, rate limits, attribution, display, caching, and export rights allow; unclear rights restrict usage to internal diagnostics, enrichment, or metadata-only use.
- Official filings, company investor relations, ETF issuer updates, and approved reputable third-party/news sources should feed Weekly News Focus before general news APIs.
- yfinance is a local-development and emergency fallback tool only, not production truth.

1. SEC EDGAR APIs provide JSON APIs for submissions history and XBRL financial-statement data, do not require authentication or API keys, and are updated throughout the day as submissions are disseminated.
   Reference: https://www.sec.gov/search-filings/edgar-application-programming-interfaces

2. Massive announced that Polygon.io was renamed Massive.com effective October 30, 2025.
   Reference: https://massive.com/blog/polygon-is-now-massive/

3. Massive describes stock market data APIs for real-time and historical data via REST and WebSockets.
   Reference: https://massive.com/

4. Massive and ETF Global provide ETF constituents, fund flows, analytics, profiles, exposure data, and metadata through Massive APIs.
   Reference: https://massive.com/partners/etf-global

5. Financial Modeling Prep documents ETF and mutual fund information, including ticker, expense ratio, and assets under management, as well as ETF/fund holdings.
   Reference: https://site.financialmodelingprep.com/developer/docs/stable/information

6. Benzinga's Newsfeed API supports structured financial news with filtering by tickers, ISINs, CUSIPs, channels/topics, date ranges, updated timestamps, content types, and importance.
   Reference: https://docs.benzinga.com/api-reference/news-api/overview

7. Finnhub documents company news endpoints and North American company news coverage.
   Reference: https://finnhub.io/docs/api/company-news

8. SEC ETF website disclosure guidance includes daily holdings and market information requirements, including portfolio holdings used for NAV calculation and related ETF website disclosures.
   Reference: https://www.sec.gov/about/divisions-offices/division-investment-management/accounting-disclosure-information/adi-2025-15-website-posting-requirements

8a. NYSE's listings directory distinguishes exchange-traded funds from exchange-traded vehicles, exchange-traded notes, and closed-end funds. This supports keeping broad ETP recognition separate from supported ETF generation.
    Reference: https://www.nyse.com/listings_directory/etf

8b. NYSE Regulation describes exchange-traded product oversight for ETFs and ETNs and notes product-specific approvals. This supports treating exchange listing evidence as recognition and review input, not runtime support by itself.
    Reference: https://www.nyse.com/regulation/exchange-traded-products

8c. Nasdaq Trader symbol-directory definitions include fields such as `ETF` and `Test Issue`, useful for validation and test-issue rejection.
    Reference: https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs

8d. Nasdaq-listed exchange-traded product data includes `Type`, `Bucket Label`, and `Investment Strategy Group`, which can help identify single-stock and derivatives-strategy products before support review.
    Reference: https://www.nasdaqtrader.com/Trader.aspx?id=etf_definitions

8e. Cboe describes U.S. ETF listings as part of broader exchange-traded product listings, including ETFs, ETNs, CEFs, and other innovative investment vehicles. This supports recognition without automatic support.
    Reference: https://www.cboe.com/listings/us/etf/

9. FINRA describes Regulation Best Interest as establishing a best-interest standard for broker-dealers when making recommendations to retail customers about securities transactions or investment strategies. This supports the product's conservative boundary against recommendations.
   Reference: https://www.finra.org/rules-guidance/key-topics/regulation-best-interest

10. Google Cloud documents Free Tier resources and region-specific free usage considerations. The MVP deployment plan uses Cloud Run request-based billing and a private regional Google Cloud Storage bucket in an eligible U.S. region for a low-cost side-project setup.
    Reference: https://docs.cloud.google.com/free/docs/free-cloud-features

11. Google Cloud documents the Cloud Run container runtime contract, including listening on the `PORT` environment variable. The API container should respect this contract with a local fallback.
    Reference: https://docs.cloud.google.com/run/docs/container-contract

12. Google Cloud documents Cloud Run Jobs for containerized tasks. The MVP ingestion worker should use manually triggered Cloud Run Jobs first, with Cloud Scheduler only if recurring jobs become necessary.
    Reference: https://docs.cloud.google.com/run/docs/execute/jobs

13. Vercel documents monorepo project setup and builds. The frontend deployment target is a Vercel Hobby project rooted at `apps/web`.
    Reference: https://vercel.com/docs/monorepos

14. Neon documents its pricing and free plan. Neon Free Postgres is acceptable for the first personal deployment, but usage, storage, connection limits, and upgrade needs must be monitored.
    Reference: https://neon.com/pricing

15. OpenRouter documents API authentication and OpenAI-compatible API access. The MVP should keep OpenRouter server-side only and enable it through environment configuration rather than hard-coding a provider or model.
    Reference: https://openrouter.ai/docs/api/reference/authentication

15a. OpenRouter documents model fallbacks through the `models` array and the Free Models Router (`openrouter/free`). Production should use the explicit ordered free-model chain plus DeepSeek fallback so validation, costs, and selected-model logging are predictable; `openrouter/free` remains an optional manual override, not the default production strategy.
    Reference: https://openrouter.ai/docs/guides/routing/routers/free-models-router

16. Financial Modeling Prep offers broad reference, quote, statement, ETF/fund, and holdings endpoints, but its own pricing and terms state that displaying or redistributing FMP-sourced data requires a specific Data Display and Licensing Agreement. FMP should therefore be treated as optional enrichment, not as a default public display/export source.
    References: https://site.financialmodelingprep.com/developer/docs, https://site.financialmodelingprep.com/developer/docs/pricing, https://site.financialmodelingprep.com/terms-of-service

17. Alpha Vantage is suitable for low-volume experiments and selected enrichment. Its standard free usage limit is 25 API requests per day, which is too restrictive for broad pre-caching or aggressive multi-source ingestion.
    Reference: https://www.alphavantage.co/premium/

18. Finnhub provides market data, fundamentals, estimates, and alternative data, but its terms restrict listed plans to personal use unless explicitly approved and prohibit redistribution or sharing of data or derived results without written approval. Finnhub should be enrichment-only until usage rights are reviewed.
    Reference: https://finnhub.io/terms-of-service

19. Tiingo is useful for end-of-day data, corporate-action-aware historical refreshes, news/fundamentals endpoints, and ETF/mutual-fund fee metadata. It is better suited to stable, non-tick-level enrichment than to a product that implies guaranteed real-time quotes.
    References: https://www.tiingo.com/kb/article/the-fastest-method-to-ingest-tiingo-end-of-day-stock-api-data/, https://status.tiingo.com/

20. EODHD is useful for light testing, EOD-style history, delayed live data, fundamentals, and basic enrichment. Its free access is small, and personal-use versus commercial-use limits must be reviewed before public display, caching, or export.
    Reference: https://eodhd.com/pricing

21. yfinance is not affiliated with Yahoo, is intended for research/educational use, and points users to Yahoo terms for rights to downloaded data. It must remain local-development or fallback-only and should not be treated as production truth.
    Reference: https://github.com/ranaroussi/yfinance

22. iShares describes IWB as exposure to large U.S. companies, access to about 1,000 domestic stocks, and an ETF seeking to track large- and mid-capitalization U.S. equities. IWB official holdings are the preferred monthly top-500 ranking proxy.
    References: https://www.ishares.com/us/products/239707/ishares-russell-1000-etf, https://www.ishares.com/us/products/239707/ishares-russell-1000-etf/?dataType=fund&fileName=IWB_holdings&fileType=csv

23. State Street's official SPY page exposes S&P 500 ETF holdings and a daily holdings download. SPY may be used only as a fallback source input for a reviewed candidate manifest, not as runtime truth.
    Reference: https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy

24. iShares describes IVV as seeking to track the S&P 500 Index, with official holdings and portfolio characteristics. IVV may be used only as a fallback source input for a reviewed candidate manifest.
    Reference: https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf

25. Vanguard publishes official VOO fund materials describing the Vanguard S&P 500 ETF and its index-tracking objective. VOO may be used as a fallback source input when its official materials can be parsed and reviewed.
    Reference: https://institutional.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/fact-sheet/F0968.pdf

26. SEC publishes `company_tickers_exchange.json` for company name, CIK, ticker, and exchange associations. Top-500 candidate rows should use it to attach or confirm stock identity metadata.
    Reference: https://www.sec.gov/file/company-tickers-exchange

27. Nasdaq Trader symbol-directory definitions include fields such as `ETF` and `Test Issue`. Top-500 candidate validation should use these fields to reject ETFs and test issues.
    Reference: https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs

28. GitHub Actions supports scheduled workflows and manual `workflow_dispatch` runs. Scheduled workflows run from the default branch, making GitHub Actions a good first automation path for reviewable monthly candidate-manifest PRs.
    References: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule, https://docs.github.com/actions/how-tos/managing-workflow-runs-and-deployments/managing-workflow-runs/manually-running-a-workflow

29. The `peter-evans/create-pull-request` action is designed to commit workspace changes to a branch and open or update a pull request, which fits the reviewed candidate-manifest workflow.
    Reference: https://github.com/peter-evans/create-pull-request

30. Google Cloud documents executing Cloud Run Jobs on a schedule with Cloud Scheduler. This should be a later production automation option after the GitHub Actions PR workflow and manual Cloud Run Jobs are proven useful.
    Reference: https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule

31. Cloud Scheduler has a small free tier measured per billing account, but scheduled jobs are still billable resources after the free tier. Keep scheduler usage minimal and reviewed.
    Reference: https://cloud.google.com/scheduler/pricing

---

## 23. Appendix B: Suggested first pre-cached universe

The product supports the top 500 U.S.-listed common stocks first and the manifest-approved supported ETF universe. Launch reliability improves if a smaller high-demand universe is pre-cached.

Suggested MVP pre-cache set:

- Broad ETFs: `VOO`, `SPY`, `VTI`, `IVV`, `QQQ`, `IWM`, `DIA`
- Sector/theme ETFs: `VGT`, `XLK`, `SOXX`, `SMH`, `XLF`, `XLV`, `XLE`
- Large stocks: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `BRK.B`, `JPM`, `UNH`
- Common comparison pairs: `VOO/SPY`, `VTI/VOO`, `QQQ/VOO`, `QQQ/VGT`, `VGT/SOXX`, `AAPL/MSFT`, `NVDA/SOXX`

This list is not a recommendation list. It is an operational pre-cache list for product testing and latency control.

---

## 24. One-sentence product thesis

**Learn the Ticker helps beginner investors understand U.S. stocks and ETFs through plain-English explanations, visible citations, comparison-capable learning, separated Weekly News Focus context, educational AI analysis, and limited grounded asset-specific education without becoming a stock picker or financial advisor.**
