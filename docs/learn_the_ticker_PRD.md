# PRD: Citation-First Beginner U.S. Stock & ETF Research Assistant

**Document version:** v0.1  
**Product stage:** Side-project MVP / v1 planning  
**Source basis:** Current project proposal: *Citation-First Beginner U.S. Stock & ETF Research Assistant*.

---

## 1. Product summary

The product is a web-based educational research assistant for beginner investors who want to understand U.S. stocks and plain-vanilla ETFs before making their own decisions.

A user can search for a ticker such as `VOO`, `QQQ`, or `AAPL` and receive a plain-English explanation of:

- what the asset is
- what the company does or what the ETF holds
- why people consider it
- the top risks
- how it compares with similar assets
- what changed recently
- which sources support the key claims

The product should feel like a patient teacher with receipts: beginner-friendly explanations, visible citations, clear freshness labels, and strict separation between stable facts and recent developments.

---

## 2. Product positioning

### Positioning statement

**A beginner-friendly, source-grounded stock and ETF learning assistant for U.S. investors.**

### What this product is

An educational research product that helps users understand assets using official and structured sources first, then uses AI to explain those facts in plain English.

### What this product is not

The product is not:

- a stock picker
- a trading bot
- a brokerage app
- a portfolio optimizer
- a personalized financial advisor
- a tool that tells users exactly what to buy or how much to allocate

This distinction is central to the product’s trust model and UX. The source proposal frames the app as “education over advice” and says the system should explain suitability rather than give buy, sell, or allocation commands.

---

## 3. Problem statement

Beginner investors face three connected problems.

First, most finance tools assume prior knowledge. They show ratios, prices, holdings, and charts, but they often do not explain what those things mean in simple language.

Second, beginners struggle to compare similar assets. They may know tickers like `VOO`, `SPY`, `QQQ`, `VTI`, `AAPL`, or `MSFT`, but they may not understand differences in benchmark, concentration, sector exposure, fees, business model, valuation, or portfolio role.

Third, generic AI answers can sound confident even when weakly grounded. In financial education, unsupported confidence is a trust problem. The system must separate source-backed facts from model-written explanations and make citations visible throughout the user experience.

---

## 4. Product vision

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

The product should make users feel more informed, not more pressured to trade.

---

## 5. Goals and non-goals

### 5.1 Goals

#### G1. Explain stocks and ETFs in beginner language

Every asset page should start with a plain-English summary that explains the asset without assuming finance knowledge.

#### G2. Make citations part of the core experience

Important claims should be backed by source citations. Citations should not be hidden in a footer; they should appear as inline citation chips, source drawers, and as-of labels.

#### G3. Separate stable facts from recent developments

The product must clearly distinguish between “what this asset is” and “what happened recently.” Recent developments should add context, not redefine the asset.

#### G4. Make comparison a flagship workflow

Users should be able to compare two assets and understand the real difference in simple language.

#### G5. Provide asset-specific grounded chat

Users should be able to ask questions about the selected asset, with answers grounded in the asset’s source-backed knowledge pack.

#### G6. Avoid investment advice

The product should support education and understanding, not provide buy/sell recommendations, price targets, personalized allocations, or individualized tax guidance.

### 5.2 Non-goals for v1

The following are out of scope for v1:

- brokerage trading
- personalized allocation advice
- tax guidance
- options
- crypto
- international equities
- leveraged ETFs
- inverse ETFs
- portfolio optimization
- automated buy/sell signals
- real-time trading recommendations

The source proposal limits v1 to U.S.-listed common stocks and plain-vanilla U.S.-listed ETFs, with search, explain, compare, recent developments, grounded chat, glossary, and source visibility as the core scope.

---

## 6. Target users

### 6.1 Beginner ETF learner

This user has heard of broad ETFs such as `VOO`, `SPY`, `VTI`, or `QQQ`, but does not fully understand concepts like diversification, expense ratio, index tracking, overlap, concentration, or sector exposure.

#### Primary needs

- Understand what an ETF actually holds
- Learn whether it is broad or narrow
- Compare similar ETFs
- Understand fees and concentration
- Identify simpler alternatives

### 6.2 Beginner stock learner

This user knows company names like Apple, Microsoft, Nvidia, or Tesla, but does not know how to read filings, understand revenue drivers, interpret risks, or evaluate financial quality.

#### Primary needs

- Understand what the company actually does
- Learn how it makes money
- See top risks in simple language
- Understand recent earnings or major news
- Compare the company with a peer

### 6.3 Self-directed learner

This user does not want a direct trading signal. They want a reliable explainer that translates source material into understandable language.

#### Primary needs

- Source-backed explanations
- Clear uncertainty when evidence is missing
- Glossary support for jargon
- Comparison-based learning
- No pressure to trade

---

## 7. Core user journeys

### 7.1 Search and understand an ETF

1. User searches `VOO`.
2. System resolves ticker to canonical asset.
3. User lands on the VOO asset page in Beginner Mode.
4. User sees:
   - what VOO is
   - what index it tracks
   - expense ratio
   - top holdings
   - top risks
   - whether it is broad or narrow
   - recent developments
   - simpler alternatives
   - key sources
5. User clicks a citation chip to open the source drawer.
6. User clicks “expense ratio” and sees a glossary card.
7. User asks the chat: “Why do beginners use this?”

#### Success outcome

The user can explain what VOO is, why people use it, and what its main limitations are.

### 7.2 Compare two ETFs

1. User searches `QQQ vs VOO`.
2. System resolves both assets.
3. User lands on the comparison page.
4. User sees side-by-side differences:
   - benchmark
   - provider
   - expense ratio
   - number of holdings
   - top holdings
   - sector concentration
   - overlap
   - role: broad core vs narrower satellite
5. User sees a “Bottom line for beginners” summary.
6. User opens source drawer for supporting citations.

#### Success outcome

The user understands that two popular ETFs may serve very different roles even if both hold large U.S. companies.

### 7.3 Understand a stock

1. User searches `AAPL`.
2. System resolves ticker to company identity and CIK.
3. User lands on the stock asset page.
4. User sees:
   - what the company sells
   - how it makes money
   - business segments
   - financial quality trends
   - top 3 risks
   - valuation context
   - recent developments
   - key sources
5. User asks: “What is the biggest risk for a beginner?”
6. Chat responds with a direct answer, why it matters, source citations, and uncertainty or missing context.

#### Success outcome

The user understands the company’s business model and main risks without needing to read the full 10-K first.

### 7.4 Learn a finance concept in context

1. User sees “operating margin” on a stock page.
2. User clicks the term.
3. Glossary card opens.
4. User sees:
   - simple definition
   - why it matters
   - common beginner mistake
   - link to deeper explanation

#### Success outcome

The user learns the concept at the moment they need it.

---

## 8. V1 product scope

### 8.1 In scope

#### Asset coverage

- U.S.-listed common stocks
- Plain-vanilla U.S.-listed ETFs

#### Core features

- Search and entity resolution
- Stock asset page
- ETF asset page
- Beginner Mode
- Deep-Dive Mode
- Compare two assets
- Recent developments section
- Asset-specific grounded chat
- Beginner glossary
- Source drawer
- Inline citations
- Freshness labels
- Basic suitability summary framed as education, not advice

### 8.2 Out of scope

- Trading
- Portfolio optimization
- Personalized advice
- Tax advice
- Options
- Leveraged ETFs
- Inverse ETFs
- Crypto
- International equities
- Automated market predictions
- Unsupported price targets

---

## 9. Product principles

The product should follow these principles from the proposal:

1. **Source first:** important facts come from official or structured sources before AI writes explanations.
2. **Plain English first:** every asset page begins with a beginner summary.
3. **Comparison is core:** beginners learn faster by comparing similar assets.
4. **Stable facts and recent developments stay separate:** users should not confuse asset basics with short-term news.
5. **Citations are product UX:** source visibility is part of the experience, not an appendix.
6. **Grounded chat:** chat answers should come from a bounded asset-specific knowledge pack.
7. **Education over advice:** the product explains suitability and tradeoffs without telling users what to buy.

---

## 10. Functional requirements

### 10.1 Search and entity resolution

#### Description

Users can search by ticker or asset name.

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| SR-1 | User can search by ticker, e.g. `VOO`, `QQQ`, `AAPL`. | P0 |
| SR-2 | User can search by company or fund name, e.g. `Apple`, `Vanguard S&P 500 ETF`. | P0 |
| SR-3 | System resolves canonical ticker, name, asset type, exchange, provider or company, and relevant identifiers. | P0 |
| SR-4 | System handles ambiguous names with a disambiguation state. | P1 |
| SR-5 | System distinguishes stocks from ETFs before routing to the correct page template. | P0 |
| SR-6 | System shows unsupported asset types with a clear message. | P0 |

#### Acceptance criteria

- Searching `AAPL` opens Apple’s stock page.
- Searching `VOO` opens Vanguard S&P 500 ETF’s ETF page.
- Searching a crypto ticker, option, leveraged ETF, inverse ETF, or unsupported international equity shows an unsupported-asset message.
- Ambiguous name searches show likely matches instead of guessing silently.

### 10.2 Asset page: shared requirements

#### Description

Every supported asset has a page with Beginner Mode and Deep-Dive Mode.

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| AP-1 | Asset page defaults to Beginner Mode. | P0 |
| AP-2 | Asset page includes canonical name, ticker, asset type, and last updated timestamp. | P0 |
| AP-3 | Asset page starts with a plain-English beginner summary. | P0 |
| AP-4 | Asset page includes exactly three top risks before expandable risk detail. | P0 |
| AP-5 | Asset page includes a recent developments section separate from asset basics. | P0 |
| AP-6 | Asset page includes source citations for key claims. | P0 |
| AP-7 | Asset page includes a source drawer with source title, type, date, retrieved timestamp, and URL. | P0 |
| AP-8 | Asset page includes glossary cards for important beginner terms. | P1 |
| AP-9 | Asset page includes Deep-Dive Mode for more detailed metrics and source context. | P1 |

#### Acceptance criteria

- A beginner can read the top section without needing to understand advanced finance terms.
- Key claims have visible citations.
- Recent developments are clearly labeled as recent context.
- Source drawer exposes where claims came from.
- Missing or stale data is displayed honestly instead of hidden.

### 10.3 Stock page

#### Description

The stock page explains what a company does, how it makes money, its financial quality, risks, valuation context, recent developments, and educational suitability.

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| ST-1 | Show stock snapshot: name, ticker, sector, industry, exchange, market cap, price or last close, last updated. | P0 |
| ST-2 | Explain what the business does in beginner language. | P0 |
| ST-3 | Show main products and services. | P0 |
| ST-4 | Show business segments when available. | P1 |
| ST-5 | Show revenue drivers and geographic exposure when available. | P1 |
| ST-6 | Summarize strengths in source-grounded language. | P1 |
| ST-7 | Show multi-year financial quality trends, not one quarter alone. | P1 |
| ST-8 | Show exactly three top risks first. | P0 |
| ST-9 | Provide expandable risk detail from filings or other source documents. | P1 |
| ST-10 | Show valuation context such as P/E, forward P/E when sourced, price/sales, price/free cash flow, peer context, and own-history context. | P1 |
| ST-11 | Provide a suitability summary using educational language, not buy/sell language. | P0 |
| ST-12 | Show recent developments such as earnings, guidance, product announcements, M&A, leadership changes, or regulatory events. | P0 |

#### Acceptance criteria

- Stock page answers “what does this company actually sell?”
- Top risks are understandable to a beginner.
- Financial metrics are explained, not merely displayed.
- Suitability summary avoids “buy,” “sell,” “hold,” or position-sizing instructions.
- Recent developments do not override stable company basics.

### 10.4 ETF page

#### Description

The ETF page explains what the fund is trying to do, what it holds, how it is constructed, its costs, trading context, risks, comparable funds, and educational suitability.

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| ETF-1 | Show ETF snapshot: name, ticker, provider, category, asset class, passive/active, benchmark/index, expense ratio, AUM, last updated. | P0 |
| ETF-2 | Explain what the ETF is trying to do in beginner language. | P0 |
| ETF-3 | Explain why beginners may consider it. | P0 |
| ETF-4 | Explain the main catch or beginner misunderstanding. | P0 |
| ETF-5 | Classify ETF role as likely core, satellite, or specialized/narrow, with caveats. | P1 |
| ETF-6 | Show number of holdings. | P0 |
| ETF-7 | Show top 10 holdings. | P0 |
| ETF-8 | Show top 10 concentration. | P0 |
| ETF-9 | Show sector breakdown. | P0 |
| ETF-10 | Show country breakdown when relevant. | P1 |
| ETF-11 | Show weighting method and methodology details when available. | P1 |
| ETF-12 | Show cost and trading context: expense ratio, AUM, bid-ask spread or average volume where available. | P1 |
| ETF-13 | Show ETF-specific risks, including market, concentration, liquidity, complexity, interest-rate, credit, and currency risks where relevant. | P0 |
| ETF-14 | Show similar ETFs and simpler alternatives. | P0 |
| ETF-15 | Show whether the ETF adds diversification or overlaps heavily with a broad-market ETF. | P1 |
| ETF-16 | Show recent developments such as fee changes, methodology changes, fund merger/liquidation news, or sponsor updates. | P0 |

#### Acceptance criteria

- ETF page answers “what does this fund actually hold?”
- User can tell whether the ETF is broad or narrow.
- User can see the cost and concentration tradeoffs.
- User can compare the ETF with simpler alternatives.
- ETF suitability summary avoids personalized allocation advice.

### 10.5 Comparison page

#### Description

Comparison is a flagship feature. Users should be able to compare two supported stocks, two supported ETFs, or one stock and one ETF when meaningful.

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| CP-1 | User can compare two tickers from search or asset pages. | P0 |
| CP-2 | Comparison page shows side-by-side snapshots. | P0 |
| CP-3 | Comparison page explains the most important differences in plain English. | P0 |
| CP-4 | Comparison page ends with “Bottom line for beginners.” | P0 |
| CP-5 | ETF comparison includes benchmark, expense ratio, holdings count, concentration, sector exposure, and role. | P0 |
| CP-6 | Stock comparison includes business model, sector/industry, financial quality, valuation context, risks, and recent developments. | P1 |
| CP-7 | Cross-type comparison explains that a single stock and an ETF are structurally different. | P1 |
| CP-8 | Comparison claims include citations. | P0 |
| CP-9 | System suggests common comparisons such as `VOO vs SPY`, `VTI vs VOO`, `QQQ vs VGT`, `AAPL vs MSFT`, `NVDA vs SOXX`. | P1 |

#### Acceptance criteria

- A user comparing `VOO` and `QQQ` can understand broad-market exposure versus Nasdaq-100 concentration.
- A user comparing `AAPL` and `MSFT` can understand differences in business model and risk.
- The bottom-line section is educational, not prescriptive.
- Important comparison claims have citations.

### 10.6 Recent developments

#### Description

Every asset page includes a recent developments section. This section provides timely context but remains separate from stable asset facts.

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| RD-1 | Asset page includes a clearly labeled “Recent developments” section. | P0 |
| RD-2 | Recent developments include only high-signal events. | P0 |
| RD-3 | Stock events may include earnings, guidance, major product announcements, M&A, leadership changes, legal or regulatory events. | P0 |
| RD-4 | ETF events may include fee changes, methodology changes, fund mergers, liquidations, or sponsor updates. | P0 |
| RD-5 | Recent developments show event date, source date, and retrieved date. | P0 |
| RD-6 | Recent developments do not replace or rewrite canonical asset facts. | P0 |
| RD-7 | System indicates when there are no high-signal recent developments. | P1 |

#### Acceptance criteria

- Recent developments are visually separate from the beginner summary.
- Each recent development has at least one citation.
- Low-quality or irrelevant news is excluded.
- The section can say “No major recent developments found” when appropriate.

### 10.7 Asset-specific grounded chat

#### Description

Each asset page includes a chat module titled something like **Ask about this asset**. The chat answers questions using a bounded asset-specific knowledge pack, not general model memory.

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| GC-1 | Asset page includes an “Ask about this asset” chat module. | P1 for v1, P0 for chat release |
| GC-2 | Chat answers are grounded in the selected asset’s knowledge pack. | P0 |
| GC-3 | Chat supports definition, risk, comparison, recent event, glossary, and suitability questions. | P0 |
| GC-4 | Every answer includes direct answer, why it matters, citations, and uncertainty or limits. | P0 |
| GC-5 | Chat avoids buy/sell commands. | P0 |
| GC-6 | Chat avoids personalized allocation advice. | P0 |
| GC-7 | Chat can say it does not know when evidence is missing. | P0 |
| GC-8 | Chat stores conversational state for follow-up questions while staying grounded. | P1 |
| GC-9 | Chat provides starter prompts for beginner questions. | P1 |

#### Acceptance criteria

- Asking “What does this company actually sell?” returns a cited answer.
- Asking “Should I buy this?” redirects to educational framing.
- Asking “How much should I put in this?” avoids position sizing and explains factors to consider.
- Asking “What happened recently?” answers from the recent developments layer.
- Chat responses do not invent facts when sources are missing.

### 10.8 Glossary and concept learning

#### Description

Users can click finance terms and see short beginner-friendly explanations.

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| GL-1 | Important terms appear as clickable glossary terms. | P1 |
| GL-2 | Glossary card includes simple definition. | P0 |
| GL-3 | Glossary card explains why the concept matters. | P0 |
| GL-4 | Glossary card includes common beginner mistake. | P1 |
| GL-5 | Glossary card links to deeper explanation when available. | P2 |
| GL-6 | Glossary cards are context-aware when possible. | P2 |

#### Acceptance criteria

- User can click “expense ratio” and understand it without leaving the page.
- User can click “operating margin” and understand why it matters.
- Glossary explanations do not overwhelm the main workflow.

### 10.9 Sources, citations, and freshness

#### Description

Trust features are part of the core product experience.

#### Requirements

| ID | Requirement | Priority |
|---|---|---|
| SC-1 | Important claims include citation chips. | P0 |
| SC-2 | Citation chips open the source drawer. | P0 |
| SC-3 | Source drawer shows source title, source type, URL, published date, retrieved date, and associated claims. | P0 |
| SC-4 | Official sources receive an “Official source” badge. | P1 |
| SC-5 | Page shows overall freshness. | P0 |
| SC-6 | Each major section shows freshness or as-of date. | P1 |
| SC-7 | System shows stale, unknown, or mixed-evidence states where needed. | P0 |
| SC-8 | System preserves source hierarchy: official and structured sources before news. | P0 |

#### Acceptance criteria

- User can see where a key claim came from.
- User can distinguish official source material from news or third-party data.
- User can tell when a page or section was last updated.
- Unsupported claims are either removed or marked as uncertain.

---

## 11. Content requirements

### 11.1 Stock page content model

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

8. **Suitability summary**
   - who this may fit
   - who may prefer an ETF instead
   - what would change the view
   - what the user should learn next

### 11.2 ETF page content model

Each ETF page should include:

1. **Snapshot**
   - name
   - ticker
   - provider
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
   - core or satellite
   - intended purpose
   - simpler alternatives

4. **What it holds**
   - number of holdings
   - top 10 holdings
   - top 10 concentration
   - sector breakdown
   - country breakdown
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

9. **Suitability summary**
   - who this may fit
   - when it may be too narrow
   - when broader or cheaper ETFs may be better
   - what would make it a poor fit

---

## 12. UX requirements

### 12.1 Beginner Mode

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

#### Acceptance criteria

- User does not need to understand filings, ratios, or ETF methodology to get value.
- Advanced details are available but not forced into the first view.

### 12.2 Deep-Dive Mode

Deep-Dive Mode expands the page for users who want more detail.

It should include:

- detailed financial metrics
- segment or exposure breakdowns
- source-specific nuance
- peer comparison
- methodology details
- full source list
- source dates and freshness

#### Acceptance criteria

- Deep-Dive Mode adds depth without changing the beginner summary.
- Users can inspect the evidence behind the summary.

### 12.3 Source drawer

The source drawer should show:

- source title
- source type
- official/third-party badge
- published date
- retrieved timestamp
- source URL
- related claims
- relevant excerpt or chunk when available

#### Acceptance criteria

- User can trace key claims to sources.
- Official sources are visually distinguished from news or third-party data.

### 12.4 Citation chips

Citation chips should be:

- visible near the claim they support
- compact enough not to clutter beginner reading
- clickable
- connected to the source drawer

#### Acceptance criteria

- User can inspect sources without losing reading flow.
- Claims without support are not given citation chips.

### 12.5 Glossary cards

Glossary cards should open inline or as lightweight popovers.

Each glossary card should include:

- simple definition
- why it matters
- common beginner mistake
- optional deeper link

#### Acceptance criteria

- Glossary explanations are short and practical.
- Glossary cards help users continue the main task.

---

## 13. Safety and compliance guardrails

### 13.1 Product stance

The product is educational and informational. It does not provide personalized investment, legal, or tax advice.

### 13.2 Required guardrails

| ID | Guardrail | Priority |
|---|---|---|
| SG-1 | Do not use direct buy/sell language. | P0 |
| SG-2 | Do not provide personalized allocation or position sizing. | P0 |
| SG-3 | Do not provide unsupported price targets. | P0 |
| SG-4 | Distinguish stable facts from recent developments. | P0 |
| SG-5 | Cite important claims. | P0 |
| SG-6 | Say “unknown” or show uncertainty when evidence is missing. | P0 |
| SG-7 | Warn clearly when an ETF is narrow, concentrated, complex, leveraged, inverse, or unsupported. | P0 |
| SG-8 | Avoid market prediction phrased as certainty. | P0 |
| SG-9 | Redirect personalized questions into educational frameworks. | P0 |

### Example safe response pattern

For “Should I buy QQQ?”

The product should not answer:

> Yes, buy QQQ.

It should answer in the style of:

> I can’t tell you whether to buy it. I can help you understand what QQQ is, what it holds, how concentrated it is, how it differs from a broader ETF like VOO, and what risks a beginner should understand before making their own decision.

---

## 14. Success metrics

### 14.1 Product metrics

| Metric | Definition | Target direction |
|---|---|---|
| Citation coverage rate | Percentage of important claims with citations | Increase |
| Unsupported claim rate | Percentage of generated claims without source support | Decrease |
| Asset-page completion rate | Percentage of users who read or interact past the beginner summary | Increase |
| Compare-page usage | Percentage of sessions using comparison | Increase |
| Chat follow-up rate | Percentage of chat users asking at least one follow-up | Increase |
| Glossary usage | Percentage of sessions using glossary cards | Increase |
| Freshness accuracy | Percentage of displayed freshness labels matching source state | Increase |
| Latency to first meaningful result | Time from search to initial useful asset page content | Decrease |

### 14.2 User-learning metrics

| Metric | Measurement approach |
|---|---|
| Understanding of “what this is” | Post-page quick prompt or thumbs-up survey |
| Understanding of top risks | User feedback or comprehension check |
| Understanding of comparison | Compare-page usefulness rating |
| Trust in citations | Citation drawer open rate and trust survey |
| Confidence without overconfidence | Survey asking whether user feels informed, not told what to do |

The source proposal emphasizes measuring trust and comprehension rather than just clicks, including citation coverage, unsupported claim rate, compare usage, glossary usage, and user understanding of top risks and asset differences.

---

## 15. Release plan

### 15.1 MVP / Phase 1

#### Objective

Ship a credible source-grounded asset explainer for a narrow set of U.S. stocks and ETFs.

#### Included

- Search
- Entity resolution
- Stock page
- ETF page
- Beginner Mode
- Source drawer
- Citation chips
- Basic glossary
- Basic recent developments block
- Safety guardrails

#### Not included

- Full grounded chat
- Advanced overlap analysis
- Watchlists
- Learning paths
- Portfolio tools

### 15.2 Phase 2

#### Objective

Make comparison a flagship learning workflow.

#### Included

- Compare page
- ETF overlap analysis
- Improved risk summaries
- Freshness indicators
- Better source state handling

### 15.3 Phase 3

#### Objective

Launch asset-specific grounded chat.

#### Included

- Ask-about-this-asset chat module
- Beginner starter prompts
- Structured cited answers
- Follow-up state
- Richer recent-context retrieval

### 15.4 Phase 4

#### Objective

Expand learning and retention workflows.

#### Included

- Watchlist
- Saved assets
- Saved comparisons
- Learning paths
- Beginner lessons tied to asset pages

---

## 16. Key risks and mitigations

### 16.1 Hallucinated or unsupported claims

#### Risk

The model may generate claims not supported by sources.

#### Mitigation

- Use source-backed knowledge packs.
- Require citations for important claims.
- Validate output against structured schemas.
- Show uncertainty when evidence is missing.
- Track unsupported claim rate.

### 16.2 Users mistake education for advice

#### Risk

Beginners may interpret explanations as recommendations.

#### Mitigation

- Avoid buy/sell language.
- Use suitability framing.
- Include educational disclaimers in high-risk flows.
- Redirect personalized allocation questions.
- Make “not financial advice” stance visible but not intrusive.

### 16.3 Stale data reduces trust

#### Risk

Financial data, holdings, fees, and news can become stale.

#### Mitigation

- Show page and section freshness.
- Cache with explicit refresh rules.
- Invalidate summaries when underlying facts change.
- Show stale states clearly.

### 16.4 Source quality varies

#### Risk

Different issuers, filings, and third-party sources may provide inconsistent or incomplete information.

#### Mitigation

- Use source hierarchy.
- Prefer official and structured sources.
- Separate news from canonical facts.
- Display uncertainty or mixed-evidence states.

### 16.5 Scope creep

#### Risk

The product could become a trading, portfolio, or advice product.

#### Mitigation

- Keep v1 focused on U.S. common stocks and plain-vanilla ETFs.
- Exclude trading, tax, options, crypto, and portfolio optimization.
- Evaluate every feature against the core promise: “understand what you are looking at.”

---

## 17. Open questions

1. **Coverage universe:** Should MVP support all U.S.-listed stocks and ETFs immediately, or start with a curated set of high-demand tickers?
2. **Market data provider:** Which structured market/reference data provider should be used for price, market cap, AUM, valuation, and ETF trading metrics?
3. **News provider:** Which source should power recent developments?
4. **Chat timing:** Should grounded chat be included in MVP, or launched in Phase 3 as proposed?
5. **Citation strictness:** Should every sentence require citation mapping, or only important factual claims?
6. **Glossary depth:** Should glossary content be static, generated, or hybrid?
7. **Unsupported ETFs:** Should leveraged and inverse ETFs be blocked entirely, or shown with a warning and no summary?
8. **User accounts:** Does v1 need saved assets and saved comparisons, or should it remain accountless?
9. **Compliance review:** What wording should be used for educational disclaimers and advice boundaries?
10. **Mobile priority:** Should the first UX be desktop-first for research depth or mobile-first for beginner accessibility?

---

## 18. MVP acceptance checklist

The MVP is ready when:

- A user can search a supported stock or ETF.
- The system resolves the asset correctly.
- The user lands on the correct stock or ETF page.
- Beginner Mode explains the asset in simple language.
- Top 3 risks are shown.
- Recent developments are separated from stable facts.
- Key claims have visible citations.
- Source drawer shows source metadata and freshness.
- Unsupported assets are handled clearly.
- The product avoids buy/sell and allocation advice.
- Users can compare two supported assets, or comparison is clearly marked as coming in Phase 2 if deferred.
- Product analytics track citation coverage, glossary usage, comparison usage, and user comprehension signals.

---

## 19. One-sentence product thesis

**This product helps beginner investors understand U.S. stocks and ETFs through plain-English explanations, visible citations, comparison-first learning, separated recent context, and grounded asset-specific education — without becoming a stock picker or financial advisor.**
