# PRD: Learn the Ticker — Citation-First Beginner U.S. Stock & ETF Research Assistant

**Document version:** v0.2 refined
**Date:** 2026-04-22
**Product stage:** Side-project MVP / v1 planning  
**Primary audience:** Product, design, engineering, data/LLM, and compliance reviewers
**Source basis:** Original proposal, PRD v0.1, technical design spec v0.1, and resolved product decisions from current review.

---

## 1. Executive summary

Learn the Ticker is a web-based educational research assistant that helps beginner investors understand U.S.-listed common stocks and plain-vanilla U.S.-listed ETFs in plain English.

A user can search a ticker such as `VOO`, `QQQ`, or `AAPL` and receive a source-grounded explanation of:

- what the asset is
- what the company does or what the ETF holds
- why people consider it
- the top risks
- how it compares with similar assets
- what changed recently
- which sources support important factual claims
- which terms a beginner should learn next

The product promise is:

> Help beginners understand what they are looking at, using cited sources and easy words.

The product should not promise:

> Tell users exactly what to buy, sell, hold, or how much to invest.

The strongest version of this product is not an AI stock picker. It is a source-first financial learning product that combines beginner explanations, visible citations, comparison-first learning, recent-context separation, and limited asset-specific grounded chat.

---

## 2. Resolved MVP decisions

This version resolves the previous open questions and makes the MVP direction explicit.

| Area                     | Decision                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Coverage universe        | Support all eligible U.S.-listed common stocks and plain-vanilla U.S.-listed ETFs through search and on-demand ingestion. Pre-cache a curated high-demand universe for speed and reliability.                                                                                                                                                                                                                 |
| Unsupported assets       | Block unsupported assets from generated pages, chat, and comparisons. Search may show a recognized-but-unsupported result with a clear explanation.                                                                                                                                                                                                                                                           |
| Market/reference data    | Use SEC EDGAR/XBRL and official issuer materials as canonical sources. Use a structured market/reference provider such as Massive, formerly Polygon.io, for ticker reference, prices, snapshots, volume, and trading metrics. For ETF-specific data, prefer official issuer data plus Massive + ETF Global where budget allows; Financial Modeling Prep may be used as a lower-cost fallback with validation. |
| News/recent developments | Use official filings, company investor relations releases, ETF issuer announcements, and prospectus updates first. Use a ticker-tagged provider such as Benzinga via Massive for structured news. Finnhub may be considered as a lower-cost supplement or fallback for company news.                                                                                                                          |
| Grounded chat timing     | Include limited asset-specific grounded chat in MVP as a beta feature. Do not ship a general finance chatbot.                                                                                                                                                                                                                                                                                                 |
| Citation strictness      | Require citations for important factual claims, not every sentence. Generic educational explanations do not require citations unless they include asset-specific facts.                                                                                                                                                                                                                                       |
| Glossary depth           | Use a hybrid glossary: curated static definitions for core terms, plus optional AI-generated asset-specific context grounded in the selected asset’s data.                                                                                                                                                                                                                                                    |
| User accounts            | Keep v1 accountless. Let users export/download page content, comparison output, source list, and chat transcript. Use server-side caching and freshness hashes to reduce repeated API and LLM calls.                                                                                                                                                                                                          |
| Compliance stance        | Add persistent educational disclaimers and inline redirects for advice-like questions. Avoid buy/sell/hold, allocation, price-target, tax, and personalized recommendation language.                                                                                                                                                                                                                          |
| Mobile priority          | Build responsive web from v1. Mobile should prioritize Beginner Mode, chat, glossary, and source access. Desktop should enhance deep research and comparisons.                                                                                                                                                                                                                                                |

---

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

#### G3. Separate stable facts from recent developments

The product must clearly distinguish “what this asset is” from “what happened recently.” Recent developments should add context, not redefine the asset.

#### G4. Make comparison a flagship workflow

Users should be able to compare two assets and understand the real difference in simple language.

#### G5. Provide limited asset-specific grounded chat in MVP

Users should be able to ask questions about the selected asset. Chat answers must be grounded in the asset’s knowledge pack and must not rely on generic model memory.

#### G6. Teach financial vocabulary in context

Users should be able to click terms such as “expense ratio,” “AUM,” “P/E,” “operating margin,” “concentration,” or “tracking error” and get short beginner explanations.

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

- All eligible U.S.-listed common stocks
- All eligible plain-vanilla U.S.-listed ETFs
- Pre-cached high-demand stocks and ETFs for launch performance
- On-demand ingestion for supported assets outside the pre-cached universe

#### Core product features

- Search and entity resolution
- Supported/unsupported asset classification
- Stock asset page
- ETF asset page
- Beginner Mode
- Deep-Dive Mode
- Compare two supported assets
- Recent developments section
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
- Options, crypto, international equities, leveraged ETFs, inverse ETFs, ETNs, and other complex products
- Native iOS or Android app

---

## 9. Product principles

1. **Source first.** Important facts come from official or structured sources before AI writes explanations.
2. **Plain English first.** Every asset page begins with a beginner summary.
3. **Comparison is core.** Beginners learn faster by comparing similar assets.
4. **Stable facts and recent developments stay separate.** Users should not confuse asset basics with short-term news.
5. **Citations are product UX.** Source visibility is part of the reading flow, not an appendix.
6. **Grounded chat only.** Chat answers should come from a bounded asset-specific knowledge pack.
7. **Education over advice.** The product explains tradeoffs without telling users what to buy.
8. **Uncertainty is acceptable.** The system should say “unknown,” “not available,” or “evidence is mixed” when sources do not support a confident answer.
9. **Accountless first.** V1 should minimize user-data overhead and use backend caching rather than user accounts for cost control.
10. **Responsive from v1.** The web experience should work well on desktop and mobile from the first release.

---

## 10. Core user journeys

### 10.1 Search and understand an ETF

1. User searches `VOO`.
2. System resolves the ticker to a supported plain-vanilla U.S.-listed ETF.
3. User lands on the VOO asset page in Beginner Mode.
4. User sees what VOO is, what index it tracks, expense ratio, AUM, top holdings, top risks, whether it is broad or narrow, recent developments, simpler alternatives, and key sources.
5. User clicks a citation chip to open the source drawer.
6. User clicks “expense ratio” and sees a glossary card.
7. User asks the chat: “Why do beginners use this?”
8. Chat answers using only the VOO asset knowledge pack.
9. User downloads the page summary and source list.

Success outcome: the user can explain what VOO is, why people use it, and what its main limitations are.

### 10.2 Compare two ETFs

1. User searches `QQQ vs VOO`.
2. System resolves both assets.
3. User lands on the comparison page.
4. User sees benchmark, provider, expense ratio, AUM, holdings count, top holdings, sector concentration, overlap, and broad/narrow role.
5. User sees a “Bottom line for beginners” section.
6. User opens the source drawer for supporting citations.
7. User downloads the comparison as Markdown or PDF.

Success outcome: the user understands that two popular ETFs may serve very different roles even if both hold large U.S. companies.

### 10.3 Understand a stock

1. User searches `AAPL`.
2. System resolves ticker to company identity and CIK.
3. User lands on the stock asset page.
4. User sees what the company sells, how it makes money, business segments, financial quality trends, top 3 risks, valuation context, recent developments, and key sources.
5. User asks: “What is the biggest risk for a beginner?”
6. Chat responds with a direct answer, why it matters, citations, and uncertainty or missing context.

Success outcome: the user understands the company’s business model and main risks without needing to read the full 10-K first.

### 10.4 Handle an unsupported ETF

1. User searches a leveraged ETF, inverse ETF, ETN, or complex exchange-traded product.
2. System recognizes the ticker when possible.
3. System does not generate a full page, chat answer, or comparison.
4. System shows a recognized-but-unsupported state.

Suggested copy:

> We found this ticker, but it is not supported in v1 because it appears to be a leveraged, inverse, ETN, or otherwise complex exchange-traded product. Learn the Ticker currently supports U.S.-listed common stocks and plain-vanilla ETFs only.

Success outcome: the product avoids explaining complex products in a way that could mislead beginners.

### 10.5 Learn a finance concept in context

1. User sees “operating margin” on a stock page.
2. User clicks the term.
3. Glossary card opens.
4. User sees a simple definition, why it matters, common beginner mistake, and optional deeper explanation.

Success outcome: the user learns the concept at the moment they need it.

### 10.6 Ask an advice-like question safely

1. User asks: “Should I buy QQQ?”
2. Chat does not answer with buy/sell/hold guidance.
3. Chat redirects to educational framing.

Suggested response pattern:

> I can’t tell you whether to buy, sell, hold, or how much to invest. I can help you understand what this asset is, what it holds or does, its main risks, how it compares with alternatives, and what questions a beginner may want to research before making their own decision.

Success outcome: the user gets useful education without the product crossing into personalized advice.

---

## 11. Functional requirements

### 11.1 Search and entity resolution

Users can search by ticker or asset name.

| ID   | Requirement                                                                                                                       | Priority |
| ---- | --------------------------------------------------------------------------------------------------------------------------------- | -------- |
| SR-1 | User can search by ticker, e.g. `VOO`, `QQQ`, `AAPL`.                                                                             | P0       |
| SR-2 | User can search by company or fund name, e.g. `Apple`, `Vanguard S&P 500 ETF`.                                                    | P0       |
| SR-3 | System resolves canonical ticker, name, asset type, exchange, issuer/provider/company, and relevant identifiers.                  | P0       |
| SR-4 | System distinguishes supported assets from unsupported assets before page routing.                                                | P0       |
| SR-5 | System handles ambiguous names with a disambiguation state.                                                                       | P1       |
| SR-6 | System supports all eligible U.S.-listed common stocks and plain-vanilla U.S.-listed ETFs through search and on-demand ingestion. | P0       |
| SR-7 | System pre-caches a high-demand universe for low-latency launch experience.                                                       | P0       |

Acceptance criteria:

- Searching `AAPL` opens Apple’s stock page.
- Searching `VOO` opens Vanguard S&P 500 ETF’s ETF page.
- Searching an unsupported crypto ticker, option, leveraged ETF, inverse ETF, ETN, or international equity shows an unsupported state.
- Ambiguous name searches show likely matches instead of guessing silently.

### 11.2 Supported and unsupported asset handling

| ID   | Requirement                                                                                                    | Priority |
| ---- | -------------------------------------------------------------------------------------------------------------- | -------- |
| UA-1 | Supported assets may proceed to asset pages, chat, and comparison.                                             | P0       |
| UA-2 | Unsupported assets are blocked from generated pages, chat, and comparison.                                     | P0       |
| UA-3 | Search may show a recognized-but-unsupported result with a short explanation.                                  | P0       |
| UA-4 | Unsupported result pages should not include generated asset summaries, buy/sell commentary, or risk summaries. | P0       |
| UA-5 | System logs unsupported asset searches for future product planning.                                            | P2       |

Blocked asset types for v1 include:

- leveraged ETFs
- inverse ETFs
- ETNs
- options
- crypto assets
- international equities
- preferred stocks, warrants, rights, and other special securities unless explicitly added later
- other complex or unsupported exchange-traded products

### 11.3 Asset page: shared requirements

Every supported asset has a page with Beginner Mode and Deep-Dive Mode.

| ID    | Requirement                                                                                      | Priority |
| ----- | ------------------------------------------------------------------------------------------------ | -------- |
| AP-1  | Asset page defaults to Beginner Mode.                                                            | P0       |
| AP-2  | Asset page includes canonical name, ticker, asset type, exchange, and last updated timestamp.    | P0       |
| AP-3  | Asset page starts with a plain-English beginner summary.                                         | P0       |
| AP-4  | Asset page includes exactly three top risks before expandable risk detail.                       | P0       |
| AP-5  | Asset page includes a recent developments section separate from asset basics.                    | P0       |
| AP-6  | Asset page includes source citations for important factual claims.                               | P0       |
| AP-7  | Asset page includes a source drawer with source title, type, date, retrieved timestamp, and URL. | P0       |
| AP-8  | Asset page includes glossary cards for important beginner terms.                                 | P1       |
| AP-9  | Asset page includes Deep-Dive Mode for more detailed metrics and source context.                 | P1       |
| AP-10 | Asset page allows users to export/download page content and source list.                         | P1       |
| AP-11 | Asset page includes a persistent educational disclaimer at the bottom.                           | P0       |

Acceptance criteria:

- A beginner can read the top section without needing advanced finance vocabulary.
- Important claims have visible citations.
- Recent developments are clearly labeled as recent context.
- Source drawer exposes where claims came from.
- Missing, stale, unavailable, or mixed evidence is displayed honestly.

### 11.4 Stock page

The stock page explains what a company does, how it makes money, its financial quality, risks, valuation context, recent developments, and educational suitability.

| ID    | Requirement                                                                                                                              | Priority |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ST-1  | Show stock snapshot: name, ticker, sector, industry, exchange, market cap, price or last close, last updated.                            | P0       |
| ST-2  | Explain what the business does in beginner language.                                                                                     | P0       |
| ST-3  | Show main products and services.                                                                                                         | P0       |
| ST-4  | Show business segments when available.                                                                                                   | P1       |
| ST-5  | Show revenue drivers and geographic exposure when available.                                                                             | P1       |
| ST-6  | Summarize strengths in source-grounded language.                                                                                         | P1       |
| ST-7  | Show multi-year financial quality trends, not one quarter alone.                                                                         | P1       |
| ST-8  | Show exactly three top risks first.                                                                                                      | P0       |
| ST-9  | Provide expandable risk detail from filings or other source documents.                                                                   | P1       |
| ST-10 | Show valuation context such as P/E, forward P/E when sourced, price/sales, price/free cash flow, peer context, and own-history context.  | P1       |
| ST-11 | Provide a suitability summary using educational language, not buy/sell language.                                                         | P0       |
| ST-12 | Show recent developments such as earnings, guidance, product announcements, M&A, leadership changes, legal events, or regulatory events. | P0       |

Acceptance criteria:

- Stock page answers “what does this company actually sell?”
- Top risks are understandable to a beginner.
- Financial metrics are explained, not merely displayed.
- Suitability summary avoids buy/sell/hold and position-sizing instructions.
- Recent developments do not override stable company basics.

### 11.5 ETF page

The ETF page explains what the fund is trying to do, what it holds, how it is constructed, its costs, trading context, risks, comparable funds, and educational suitability.

| ID     | Requirement                                                                                                                                 | Priority |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| ETF-1  | Show ETF snapshot: name, ticker, issuer/provider, category, asset class, passive/active, benchmark/index, expense ratio, AUM, last updated. | P0       |
| ETF-2  | Explain what the ETF is trying to do in beginner language.                                                                                  | P0       |
| ETF-3  | Explain why beginners may consider it.                                                                                                      | P0       |
| ETF-4  | Explain the main catch or beginner misunderstanding.                                                                                        | P0       |
| ETF-5  | Classify ETF role as likely core, satellite, or specialized/narrow, with caveats.                                                           | P1       |
| ETF-6  | Show number of holdings.                                                                                                                    | P0       |
| ETF-7  | Show top 10 holdings.                                                                                                                       | P0       |
| ETF-8  | Show top 10 concentration.                                                                                                                  | P0       |
| ETF-9  | Show sector breakdown.                                                                                                                      | P0       |
| ETF-10 | Show country breakdown when relevant.                                                                                                       | P1       |
| ETF-11 | Show weighting method and methodology details when available.                                                                               | P1       |
| ETF-12 | Show cost and trading context: expense ratio, AUM, bid-ask spread, average volume, and premium/discount where available.                    | P1       |
| ETF-13 | Show ETF-specific risks, including market, concentration, liquidity, complexity, interest-rate, credit, and currency risks where relevant.  | P0       |
| ETF-14 | Show similar ETFs and simpler alternatives.                                                                                                 | P0       |
| ETF-15 | Show whether the ETF adds diversification or overlaps heavily with a broad-market ETF.                                                      | P1       |
| ETF-16 | Show recent developments such as fee changes, methodology changes, fund merger/liquidation news, or sponsor updates.                        | P0       |

Acceptance criteria:

- ETF page answers “what does this fund actually hold?”
- User can tell whether the ETF is broad or narrow.
- User can see cost, concentration, and trading-context tradeoffs.
- User can compare the ETF with simpler alternatives.
- ETF suitability summary avoids personalized allocation advice.

### 11.6 Comparison page

Comparison is a flagship feature. Users should be able to compare two supported stocks, two supported ETFs, or one stock and one ETF when meaningful.

| ID    | Requirement                                                                                                                      | Priority |
| ----- | -------------------------------------------------------------------------------------------------------------------------------- | -------- |
| CP-1  | User can compare two tickers from search or asset pages.                                                                         | P0       |
| CP-2  | Comparison page shows side-by-side snapshots.                                                                                    | P0       |
| CP-3  | Comparison page explains the most important differences in plain English.                                                        | P0       |
| CP-4  | Comparison page ends with “Bottom line for beginners.”                                                                           | P0       |
| CP-5  | ETF comparison includes benchmark, expense ratio, AUM, holdings count, concentration, sector exposure, and role.                 | P0       |
| CP-6  | Stock comparison includes business model, sector/industry, financial quality, valuation context, risks, and recent developments. | P1       |
| CP-7  | Cross-type comparison explains that a single stock and an ETF are structurally different.                                        | P1       |
| CP-8  | Important comparison claims include citations.                                                                                   | P0       |
| CP-9  | System suggests common comparisons such as `VOO vs SPY`, `VTI vs VOO`, `QQQ vs VGT`, `AAPL vs MSFT`, `NVDA vs SOXX`.             | P1       |
| CP-10 | User can export/download comparison output and source list.                                                                      | P1       |

Acceptance criteria:

- A user comparing `VOO` and `QQQ` can understand broad-market exposure versus Nasdaq-100 concentration.
- A user comparing `AAPL` and `MSFT` can understand differences in business model and risk.
- The bottom-line section is educational, not prescriptive.
- Important comparison claims have citations.

### 11.7 Recent developments

Every asset page includes a recent developments section. This section provides timely context but remains separate from stable asset facts.

| ID   | Requirement                                                                                                                            | Priority |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| RD-1 | Asset page includes a clearly labeled “Recent developments” section.                                                                   | P0       |
| RD-2 | Recent developments include only high-signal events.                                                                                   | P0       |
| RD-3 | Stock events may include earnings, guidance, major product announcements, M&A, leadership changes, legal events, or regulatory events. | P0       |
| RD-4 | ETF events may include fee changes, methodology changes, index changes, fund mergers, liquidations, or sponsor updates.                | P0       |
| RD-5 | Recent developments show event date, source date, and retrieved date.                                                                  | P0       |
| RD-6 | Recent developments do not replace or rewrite canonical asset facts.                                                                   | P0       |
| RD-7 | System indicates when there are no high-signal recent developments.                                                                    | P1       |
| RD-8 | Recent developments are deduplicated across news, filings, and issuer releases.                                                        | P1       |

Acceptance criteria:

- Recent developments are visually separate from the beginner summary.
- Each recent development has at least one citation.
- Low-quality, duplicate, promotional, or irrelevant news is excluded.
- The section can say “No major recent developments found” when appropriate.

### 11.8 Asset-specific grounded chat beta

Each asset page includes a chat module titled **Ask about this asset**. The chat answers questions using a bounded asset-specific knowledge pack, not general model memory.

MVP chat is intentionally limited. It is not a general finance chatbot.

Supported MVP chat intents:

- definition questions
- business model questions
- ETF holdings questions
- risk questions
- comparison questions using selected or supported assets
- recent-development questions
- glossary questions
- educational suitability questions
- advice-like questions requiring safe redirect

| ID    | Requirement                                                                                                     | Priority |
| ----- | --------------------------------------------------------------------------------------------------------------- | -------- |
| GC-1  | Asset page includes an “Ask about this asset” chat module.                                                      | P0       |
| GC-2  | Chat answers are grounded in the selected asset’s knowledge pack.                                               | P0       |
| GC-3  | Chat supports definition, risk, comparison, recent event, glossary, and suitability-education questions.        | P0       |
| GC-4  | Every answer includes direct answer, why it matters, citations for important claims, and uncertainty or limits. | P0       |
| GC-5  | Chat avoids buy/sell/hold commands.                                                                             | P0       |
| GC-6  | Chat avoids personalized allocation advice.                                                                     | P0       |
| GC-7  | Chat can say it does not know when evidence is missing.                                                         | P0       |
| GC-8  | Chat stores conversational state for follow-up questions while staying grounded.                                | P1       |
| GC-9  | Chat provides starter prompts for beginner questions.                                                           | P1       |
| GC-10 | Chat transcript can be exported/downloaded.                                                                     | P1       |

Acceptance criteria:

- Asking “What does this company actually sell?” returns a cited answer.
- Asking “Should I buy this?” redirects to educational framing.
- Asking “How much should I put in this?” avoids position sizing and explains learning factors instead.
- Asking “What happened recently?” answers from the recent developments layer.
- Chat responses do not invent facts when sources are missing.

### 11.9 Hybrid glossary and concept learning

Users can click finance terms and see short beginner-friendly explanations.

Glossary approach:

- Curated static definitions for core finance terms.
- Optional AI-generated contextual explanation for the selected asset.
- No uncited asset-specific facts in generated glossary context.

| ID   | Requirement                                                             | Priority |
| ---- | ----------------------------------------------------------------------- | -------- |
| GL-1 | Important terms appear as clickable glossary terms.                     | P1       |
| GL-2 | Glossary card includes simple definition.                               | P0       |
| GL-3 | Glossary card explains why the concept matters.                         | P0       |
| GL-4 | Glossary card includes common beginner mistake.                         | P1       |
| GL-5 | Glossary card links to deeper explanation when available.               | P2       |
| GL-6 | Glossary cards can include grounded asset-specific context when useful. | P2       |

Initial curated glossary should include 50–100 core terms, including:

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

- User can click “expense ratio” and understand it without leaving the page.
- User can click “operating margin” and understand why it matters.
- Glossary explanations do not overwhelm the main workflow.
- Generated context does not add unsupported asset-specific facts.

### 11.10 Sources, citations, and freshness

Trust features are part of the core product experience.

| ID   | Requirement                                                                                                | Priority |
| ---- | ---------------------------------------------------------------------------------------------------------- | -------- |
| SC-1 | Important factual claims include citation chips.                                                           | P0       |
| SC-2 | Citation chips open the source drawer.                                                                     | P0       |
| SC-3 | Source drawer shows source title, source type, URL, published date, retrieved date, and associated claims. | P0       |
| SC-4 | Official sources receive an “Official source” badge.                                                       | P1       |
| SC-5 | Page shows overall freshness.                                                                              | P0       |
| SC-6 | Each major section shows freshness or as-of date.                                                          | P1       |
| SC-7 | System shows stale, unknown, unavailable, or mixed-evidence states where needed.                           | P0       |
| SC-8 | System preserves source hierarchy: official and structured sources before news.                            | P0       |
| SC-9 | Downloaded/exported output includes source list and as-of dates.                                           | P1       |

Acceptance criteria:

- User can see where a key claim came from.
- User can distinguish official source material from news or third-party data.
- User can tell when a page or section was last updated.
- Unsupported claims are removed, regenerated, or marked as uncertain.

### 11.11 Export and download

V1 remains accountless, so export is the main “save for later” workflow.

| ID   | Requirement                                                                                                             | Priority |
| ---- | ----------------------------------------------------------------------------------------------------------------------- | -------- |
| EX-1 | User can download asset page summary.                                                                                   | P1       |
| EX-2 | User can download comparison output.                                                                                    | P1       |
| EX-3 | User can download chat transcript.                                                                                      | P1       |
| EX-4 | User can download source list with source titles, URLs, dates, and retrieved timestamps.                                | P1       |
| EX-5 | Exported content includes the educational disclaimer.                                                                   | P0       |
| EX-6 | Export respects provider licensing and avoids exporting full paid news articles or restricted data where not permitted. | P0       |

Supported export formats for MVP:

- Markdown
- PDF
- copy-to-clipboard for summary sections

Acceptance criteria:

- A user can save their learning output without creating an account.
- Export includes citations and freshness dates.
- Export does not include content prohibited by data-provider licenses.

### 11.12 Responsive web UX

The product should support both desktop web and mobile web from v1.

| ID   | Requirement                                                                                                    | Priority |
| ---- | -------------------------------------------------------------------------------------------------------------- | -------- |
| UX-1 | Layout is responsive across desktop, tablet, and mobile web.                                                   | P0       |
| UX-2 | Mobile Beginner Mode uses stacked cards, concise summaries, glossary popovers, and bottom-sheet source drawer. | P0       |
| UX-3 | Desktop Deep-Dive Mode supports side-by-side tables, source drawer, comparison views, and richer data tables.  | P0       |
| UX-4 | Chat is usable on mobile without covering core content permanently.                                            | P1       |
| UX-5 | Tables collapse or scroll horizontally only where unavoidable.                                                 | P1       |

Acceptance criteria:

- Beginner Mode is comfortable on a phone.
- Comparison is usable on desktop and acceptable on mobile through stacked sections.
- Source inspection works on both desktop and mobile.

---

## 12. Content requirements

### 12.1 Stock page content model

Each stock page should include:

1. **Snapshot**
   - name
   - ticker
   - sector
   - industry
   - exchange
   - market cap
   - price or last close
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

8. **Recent developments**
   - earnings
   - guidance
   - major product announcements
   - M&A
   - leadership changes
   - regulatory or legal events

9. **Educational suitability summary**
   - who may want to learn more about this
   - who may prefer a diversified ETF instead
   - what would change the view
   - what the user should learn next

### 12.2 ETF page content model

Each ETF page should include:

1. **Snapshot**
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
   - core, satellite, or specialized/narrow
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

9. **Recent developments**
   - fee changes
   - methodology changes
   - index changes
   - fund merger or liquidation news
   - sponsor updates

10. **Educational suitability summary**

- who may want to learn more about this
- when it may be too narrow
- when broader or cheaper ETFs may be worth comparing
- what would make it a poor fit

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

Recent developments and events.

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

1. SEC filings and XBRL data
2. Company investor relations pages
3. Earnings releases and presentations
4. Structured market/reference data provider
5. Reputable news sources

#### For ETFs

1. ETF issuer official page
2. ETF fact sheet
3. Summary prospectus and full prospectus
4. Shareholder reports
5. Structured market/reference data provider
6. Reputable news sources

### 13.3 Recommended market/reference data stack

Recommended MVP stack:

1. **Canonical stock filings and facts:** SEC EDGAR submissions API and XBRL company facts.
2. **Official ETF facts:** issuer page, fact sheet, holdings file, summary prospectus, full prospectus, shareholder reports.
3. **Structured market/reference provider:** Massive, formerly Polygon.io, for prices, snapshots, volume, ticker reference, and trading metrics.
4. **ETF structured data:** Massive + ETF Global if budget allows, especially for ETF holdings, profiles, exposure data, metadata, and analytics.
5. **Lower-cost fallback:** Financial Modeling Prep for ETF/fund information, holdings, expense ratio, AUM, and related data, validated against issuer sources when possible.

Provider-selection requirements:

- Must support commercial use needed by the app.
- Must permit the required display, caching, and export behavior.
- Must provide clear data freshness or as-of fields.
- Must support U.S.-listed stocks and ETFs at MVP scale.
- Must have documented rate limits and reliable API behavior.
- Must allow attribution/source labeling where required.

### 13.4 Recommended news/recent developments stack

Recommended MVP stack:

1. **Official first:** SEC filings, company IR releases, ETF issuer announcements, prospectus updates, fact-sheet updates, and sponsor notices.
2. **Structured news second:** Benzinga via Massive for ticker-tagged recent developments, dates, categories, source metadata, and filtering.
3. **Fallback/supplement:** Finnhub company news for North American company coverage if cost or coverage requires it.
4. **Premium future option:** Reuters, Dow Jones, FactSet, RavenPack, or similar services when budget and licensing justify them.

Recent developments should be filtered for:

- relevance to the asset
- source quality
- event importance
- recency
- non-duplication
- non-promotional tone

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
- recent developments
- comparison claims
- claims using words such as “largest,” “cheaper,” “broader,” “narrower,” “more concentrated,” “higher,” or “lower”

### 14.2 What does not require citation

Citations are not required for generic educational explanations that do not include asset-specific facts.

Examples:

- “An expense ratio is the annual fee charged by a fund.”
- “Diversification means spreading exposure across multiple holdings.”
- “A higher valuation can mean investors expect more future growth.”

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

### 15.1 Beginner Mode

Beginner Mode is the default experience.

It should prioritize:

- simple explanations
- short sections
- top risks
- plain-language summaries
- glossary support
- visible citations
- minimal jargon
- clear next steps for learning

Acceptance criteria:

- User does not need to understand filings, ratios, or ETF methodology to get value.
- Advanced details are available but not forced into the first view.

### 15.2 Deep-Dive Mode

Deep-Dive Mode expands the page for users who want more detail.

It should include:

- detailed financial metrics
- segment or exposure breakdowns
- source-specific nuance
- peer comparison
- methodology details
- full source list
- source dates and freshness

Acceptance criteria:

- Deep-Dive Mode adds depth without changing the beginner summary.
- Users can inspect the evidence behind the summary.

### 15.3 Source drawer

The source drawer should show:

- source title
- source type
- official/third-party badge
- publisher
- published date
- retrieved timestamp
- source URL
- freshness state
- related claims
- relevant excerpt or chunk where allowed

Acceptance criteria:

- User can trace important claims to sources.
- Official sources are visually distinguished from news or third-party data.

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

Glossary cards should open inline, as popovers, or as mobile bottom sheets.

Each glossary card should include:

- simple definition
- why it matters
- common beginner mistake
- optional deeper link
- optional grounded asset-specific context

Acceptance criteria:

- Glossary explanations are short and practical.
- Glossary cards help users continue the main task.

### 15.6 Mobile and desktop behavior

Mobile should emphasize:

- Beginner Mode
- summary cards
- top 3 risks
- recent developments
- glossary popovers/bottom sheets
- chat
- source drawer as bottom sheet

Desktop should emphasize:

- Deep-Dive Mode
- side-by-side comparison
- source drawer as right panel
- tables and charts
- richer source inspection

Acceptance criteria:

- The same product works on mobile and desktop.
- Desktop gets more layout depth; mobile stays readable and practical.

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
| SG-4  | Distinguish stable facts from recent developments.                            | P0       |
| SG-5  | Cite important claims.                                                        | P0       |
| SG-6  | Say “unknown,” “not available,” or show uncertainty when evidence is missing. | P0       |
| SG-7  | Block unsupported complex products from generated pages and chat.             | P0       |
| SG-8  | Avoid market prediction phrased as certainty.                                 | P0       |
| SG-9  | Redirect personalized questions into educational frameworks.                  | P0       |
| SG-10 | Include disclaimer in page footer and exported content.                       | P0       |

### 16.3 Suggested persistent disclaimer

Use this or a legally reviewed variation:

> This page is for educational and research purposes only. It is not investment, financial, legal, or tax advice and is not a recommendation to buy, sell, or hold any security. Content is generated from public filings, issuer materials, market/reference data, and news sources where available. Data may be delayed, incomplete, inaccurate, or outdated. Please review the cited sources and consider consulting a qualified professional before making financial decisions.

### 16.4 Suggested advice-like question redirect

Use this pattern in chat and other interactive flows:

> I can’t tell you whether to buy, sell, hold, or how much to invest. I can help you understand what this asset is, what it holds or does, its main risks, how it compares with alternatives, and what questions a beginner may want to research before making their own decision.

### 16.5 Compliance review requirement

Before public launch, the product should receive legal/compliance review for:

- disclaimer wording
- advice boundaries
- recommendation-risk language
- data-provider licensing
- export/download behavior
- source attribution
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
- cached knowledge packs for popular assets
- pre-cached high-demand universe

### 17.3 Freshness display

The system should show:

- page last updated
- section last updated
- facts as of date
- holdings as of date
- recent developments checked at
- retrieved timestamp for sources

Example:

```text
Page last updated: Apr 22, 2026
Holdings as of: Apr 21, 2026
Recent developments checked: Apr 22, 2026
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
| Understanding of “what this is”   | Post-page quick prompt or feedback survey                      |
| Understanding of top risks        | Feedback prompt or comprehension check                         |
| Understanding of comparison       | Compare-page usefulness rating                                 |
| Trust in citations                | Source drawer usage and trust survey                           |
| Confidence without overconfidence | Survey asking whether user feels informed, not told what to do |

---

## 19. Release plan

### 19.1 MVP / v1

Objective: Ship a credible, source-grounded, accountless beginner explainer for eligible U.S.-listed common stocks and plain-vanilla ETFs.

Included:

- Search and entity resolution
- Supported/unsupported asset classification
- Stock page
- ETF page
- Beginner Mode
- Deep-Dive Mode baseline
- Compare two assets
- Basic ETF overlap/concentration indicators
- Recent developments block
- Source drawer
- Citation chips
- Hybrid glossary baseline
- Limited asset-specific grounded chat beta
- Export/download for page, comparison, sources, and chat transcript
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
- Deeper explain-like-I’m-new mode
- More sophisticated retrieval and citation validation
- Optional user preferences if accounts exist

---

## 20. MVP acceptance checklist

The MVP is ready when:

- User can search a supported U.S.-listed common stock or plain-vanilla U.S.-listed ETF.
- System resolves the asset correctly.
- Unsupported assets are blocked clearly.
- User lands on the correct stock or ETF page.
- Beginner Mode explains the asset in simple language.
- Top 3 risks are shown.
- Recent developments are separated from stable facts.
- Important factual claims have visible citations.
- Source drawer shows source metadata and freshness.
- Page and sections show freshness/as-of dates.
- Product avoids buy/sell/hold and allocation advice.
- User can compare two supported assets.
- Comparison includes a beginner bottom line.
- Limited asset-specific chat answers from the selected asset knowledge pack.
- Advice-like chat questions are redirected safely.
- User can export page, comparison, source list, and chat transcript.
- Product analytics track citation coverage, unsupported claims, glossary usage, comparison usage, source drawer usage, export usage, safety redirects, and freshness accuracy.

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

- Review provider contracts before launch.
- Export only allowed fields and excerpts.
- Include attribution where required.
- Avoid exporting full paid news articles.

### 21.6 Scope creep

Risk: the product could become a trading, portfolio, or advice product.

Mitigation:

- Keep v1 focused on education for stocks and plain-vanilla ETFs.
- Block unsupported products.
- Defer user accounts and portfolio features.
- Evaluate every feature against the core promise: help beginners understand what they are looking at.

---

## 22. Appendix A: External source notes for provider decisions

These sources support the provider and compliance direction in this PRD. Final provider selection still requires pricing, reliability, coverage, and licensing review.

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

6. Benzinga’s Newsfeed API supports structured financial news with filtering by tickers, ISINs, CUSIPs, channels/topics, date ranges, updated timestamps, content types, and importance.
   Reference: https://docs.benzinga.com/api-reference/news-api/overview

7. Finnhub documents company news endpoints and North American company news coverage.
   Reference: https://finnhub.io/docs/api/company-news

8. SEC ETF website disclosure guidance includes daily holdings and market information requirements, including portfolio holdings used for NAV calculation and related ETF website disclosures.
   Reference: https://www.sec.gov/about/divisions-offices/division-investment-management/accounting-disclosure-information/adi-2025-15-website-posting-requirements

9. FINRA describes Regulation Best Interest as establishing a best-interest standard for broker-dealers when making recommendations to retail customers about securities transactions or investment strategies. This supports the product’s conservative boundary against recommendations.
   Reference: https://www.finra.org/rules-guidance/key-topics/regulation-best-interest

---

## 23. Appendix B: Suggested first pre-cached universe

The product supports all eligible U.S.-listed common stocks and plain-vanilla ETFs, but launch reliability improves if a high-demand universe is pre-cached.

Suggested MVP pre-cache set:

- Broad ETFs: `VOO`, `SPY`, `VTI`, `IVV`, `QQQ`, `IWM`, `DIA`
- Sector/theme ETFs: `VGT`, `XLK`, `SOXX`, `SMH`, `XLF`, `XLV`, `XLE`
- Large stocks: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `BRK.B`, `JPM`, `UNH`
- Common comparison pairs: `VOO/SPY`, `VTI/VOO`, `QQQ/VOO`, `QQQ/VGT`, `VGT/SOXX`, `AAPL/MSFT`, `NVDA/SOXX`

This list is not a recommendation list. It is an operational pre-cache list for product testing and latency control.

---

## 24. One-sentence product thesis

**Learn the Ticker helps beginner investors understand U.S. stocks and ETFs through plain-English explanations, visible citations, comparison-first learning, separated recent context, and limited grounded asset-specific education — without becoming a stock picker or financial advisor.**
