# Learn the Ticker: Citation-First Beginner U.S. Stock & ETF Research Assistant

**Document type:** Detailed product proposal  
**Version:** v0.2  
**Last updated:** 2026-04-20  
**Project stage:** Side-project MVP / v1 planning

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Core Product Promise](#2-core-product-promise)
3. [Problem Statement](#3-problem-statement)
4. [Product Vision](#4-product-vision)
5. [Product Positioning](#5-product-positioning)
6. [Product Principles](#6-product-principles)
7. [Target Users](#7-target-users)
8. [Scope for v1](#8-scope-for-v1)
9. [Core Product Experience](#9-core-product-experience)
10. [Product Content Model](#10-product-content-model)
11. [Knowledge Architecture](#11-knowledge-architecture)
12. [Source Hierarchy](#12-source-hierarchy)
13. [Retrieval and Generation Pipeline](#13-retrieval-and-generation-pipeline)
14. [Asset Knowledge Pack and Grounded Chat](#14-asset-knowledge-pack-and-grounded-chat)
15. [Technical Architecture](#15-technical-architecture)
16. [Suggested Internal APIs](#16-suggested-internal-apis)
17. [Data Model](#17-data-model)
18. [Freshness and Caching](#18-freshness-and-caching)
19. [UX Trust Features](#19-ux-trust-features)
20. [Safety and Product Guardrails](#20-safety-and-product-guardrails)
21. [Success Metrics](#21-success-metrics)
22. [Phased Roadmap](#22-phased-roadmap)
23. [Final Thesis](#23-final-thesis)
24. [References](#24-references)

---

## 1. Executive Summary

Learn the Ticker is a web-based educational research assistant for beginner investors who want to understand U.S. stocks and ETFs before making their own decisions.

A user can search a ticker such as `VOO`, `QQQ`, or `AAPL` and receive a plain-English explanation of:

- what the asset is;
- what the company does, or what the ETF holds;
- why people consider it;
- the main risks;
- how it compares with similar assets;
- what changed recently;
- which sources support the important claims.

The product should use official and structured sources as the factual backbone. The language model should not be treated as the source of truth. Instead, the model should translate verified facts, filings, prospectuses, holdings data, and other source-backed material into simple explanations for beginners.

The result should feel like a patient teacher with receipts: easy to understand, visibly sourced, and careful about the difference between education and investment advice.

---

## 2. Core Product Promise

The product promise is:

> **Help beginners understand what they are looking at, using cited sources and easy words.**

The product should not promise:

> **Tell beginners exactly what to buy.**

This distinction is central to the product, user experience, system design, and safety model.

The product should explain assets, risks, tradeoffs, comparisons, and source context. It should not give direct buy/sell commands, personalized allocation instructions, unsupported price targets, or tax guidance.

---

## 3. Problem Statement

Beginner investors usually face three problems at the same time.

### 3.1 Finance tools assume too much knowledge

Most investing tools show prices, ratios, charts, holdings, valuation metrics, and performance data, but they often assume the user already understands the vocabulary.

A beginner may see terms such as:

- expense ratio;
- tracking difference;
- operating margin;
- free cash flow;
- concentration risk;
- premium/discount;
- sector exposure;
- market capitalization.

The problem is not just that these terms are unfamiliar. The bigger problem is that many tools display the data without explaining why it matters.

### 3.2 Beginners compare assets poorly

Beginners often compare assets by name recognition rather than structure.

For example, they may know common tickers such as:

- `VOO`;
- `SPY`;
- `VTI`;
- `QQQ`;
- `VGT`;
- `AAPL`;
- `MSFT`;
- `NVDA`;
- `SOXX`.

However, they may not understand differences in:

- benchmark;
- concentration;
- sector exposure;
- holdings overlap;
- cost;
- fund construction;
- business model;
- portfolio role;
- risk profile.

A comparison-first product can help beginners learn faster because the differences become easier to understand when two assets are placed side by side.

### 3.3 Generic AI answers can sound confident but weakly grounded

Generic AI responses may sound fluent and confident even when the underlying evidence is incomplete, stale, or missing.

In a finance education product, that is a serious trust problem. The system should reduce hallucination risk by separating:

- **raw source-backed facts**; and
- **model-written explanations**.

The source-backed facts should come first. The model should then explain those facts in beginner-friendly language and cite the supporting sources.

---

## 4. Product Vision

The product vision is to build a trustworthy beginner-first stock and ETF explainer for U.S. investors.

A user should be able to answer these questions quickly:

- What is this asset?
- What does this company do, or what does this ETF hold?
- Why do people consider it?
- What are the biggest risks?
- Is it broad or narrow?
- What are simpler alternatives?
- What changed recently?
- How is it different from another stock or ETF?
- Which sources support these answers?

The user should leave the product feeling more informed, not pressured to trade.

The product should be educational, calm, source-grounded, and clear about uncertainty.

---

## 5. Product Positioning

### 5.1 Positioning statement

**A beginner-friendly, source-grounded stock and ETF learning assistant for U.S. investors.**

### 5.2 What the product is

The product is:

- an educational research assistant;
- a plain-English stock and ETF explainer;
- a comparison-first learning tool;
- a source-grounded financial learning product;
- a guided way to understand risks, holdings, company basics, valuation context, and recent developments.

### 5.3 What the product is not

The product is not:

- a stock picker;
- a trading bot;
- a brokerage app;
- a portfolio optimizer;
- a personalized financial advisor;
- a tax advisor;
- a tool that tells users exactly what to buy or how much to allocate.

This framing is better for trust, easier for scope control, and more consistent with the educational purpose of the product.

---

## 6. Product Principles

### 6.1 Source first

Important facts must come from official or structured sources before the model writes explanations.

For stocks, that means sources such as SEC filings, XBRL data, company investor relations materials, earnings materials, structured market/reference data, and reputable news for recent context.

For ETFs, that means sources such as issuer pages, fact sheets, prospectuses, shareholder reports, holdings files, market/reference data, and reputable news for recent context.

### 6.2 Plain English first

Every asset page should begin with a beginner summary. The first view should help the user understand the asset without requiring prior finance knowledge.

### 6.3 Comparison is core

Beginners often learn faster by comparing similar assets than by reading one asset page in isolation. Comparison should be a main workflow, not a secondary feature.

### 6.4 Stable facts and recent developments must stay separate

The product must clearly distinguish between:

- what the asset is;
- what the company does or what the ETF holds;
- what changed recently.

Recent news should add context. It should not redefine the asset.

### 6.5 Citations are part of the product

Citations should be visible in the user flow. They should not be hidden at the bottom of the page.

The product should use citation chips, source drawers, source badges, and freshness labels so users can see why they should trust a claim.

### 6.6 The chat must be grounded

The chat experience should answer questions from a bounded asset-specific knowledge pack. It should not rely on vague model memory.

### 6.7 Education over advice

The product should explain suitability, tradeoffs, and risks. It should not tell users what to buy, when to sell, or how much money to allocate.

---

## 7. Target Users

### 7.1 Beginner ETF learner

This user has heard of broad ETFs such as `VOO`, `SPY`, `VTI`, or `QQQ`, but does not yet understand concepts such as:

- diversification;
- concentration;
- expense ratios;
- fund overlap;
- index tracking;
- sector exposure;
- core versus satellite holdings.

#### Primary needs

This user needs to understand:

- what an ETF actually holds;
- whether the ETF is broad or narrow;
- how it compares with similar ETFs;
- what fees and concentration mean;
- whether there are simpler alternatives.

### 7.2 Beginner stock learner

This user knows company names such as Apple, Microsoft, Nvidia, or Tesla, but does not know how to read a 10-K, think about business quality, or interpret risks.

#### Primary needs

This user needs to understand:

- what the company actually sells;
- how the company makes money;
- what the main revenue drivers are;
- what the major risks are;
- how recent events may matter;
- how the stock compares with a peer or an ETF alternative.

### 7.3 Self-directed learner

This user does not want a direct trading signal. They want a reliable explainer that translates source material into understandable language.

#### Primary needs

This user needs:

- source-backed explanations;
- visible citations;
- clear uncertainty when evidence is missing;
- simple definitions for jargon;
- comparisons that explain real differences;
- education without pressure to trade.

---

## 8. Scope for v1

The first version should stay narrow and credible.

### 8.1 In scope

The v1 product should support:

- U.S.-listed common stocks;
- plain-vanilla U.S.-listed ETFs;
- ticker and name search;
- search and entity resolution;
- stock asset pages;
- ETF asset pages;
- beginner mode;
- deep-dive mode;
- comparison of two assets;
- recent developments section;
- asset-specific grounded chat;
- beginner glossary;
- source drawer with citations and freshness;
- basic educational suitability summaries.

### 8.2 Out of scope for v1

The v1 product should not support:

- options;
- leveraged ETFs;
- inverse ETFs;
- tax guidance;
- personalized allocation advice;
- brokerage trading;
- international equities;
- crypto;
- portfolio optimization;
- automated buy/sell signals;
- unsupported price targets.

### 8.3 Scope rationale

The scope should be narrow because the product’s value depends on trust. It is better to explain a smaller set of assets well than to support many complex asset types with weak sourcing or unclear guardrails.

---

## 9. Core Product Experience

## 9.1 Search and entity resolution

The user enters a ticker or name such as:

- `VOO`;
- `QQQ`;
- `AAPL`;
- `Apple`;
- `Vanguard S&P 500 ETF`.

The system resolves:

- canonical name;
- ticker;
- asset type;
- provider or exchange;
- CIK where relevant;
- issuer where relevant;
- other identifiers where useful.

After resolution, the user lands on the correct asset page.

The system should clearly distinguish between stocks and ETFs because the explanation template, source needs, risks, and metrics are different.

## 9.2 Asset page structure

Each asset page should have two modes:

1. **Beginner Mode**;
2. **Deep-Dive Mode**.

### 9.2.1 Beginner Mode

Beginner Mode is the default view.

It should show:

- what the asset is;
- why people consider it;
- top three risks;
- whether the exposure is broad or narrow;
- recent developments;
- simpler alternatives;
- key sources;
- glossary support for important terms.

The goal is to help the user understand the asset quickly without overwhelming them.

### 9.2.2 Deep-Dive Mode

Deep-Dive Mode expands the asset page for users who want more detail.

It should include:

- detailed financial metrics;
- business segment breakdowns for stocks;
- holdings and exposure breakdowns for ETFs;
- prospectus or filing-based nuance;
- peer comparison;
- methodology details;
- full source list and source dates.

Deep-Dive Mode should add depth without changing the core beginner explanation.

## 9.3 Concept learning

When the user sees a term such as:

- expense ratio;
- tracking difference;
- operating margin;
- free cash flow;
- concentration risk;
- bid-ask spread;
- premium/discount;
- return on invested capital;
- price/free cash flow.

The app should allow the user to open a glossary card.

Each glossary card should include:

- a simple definition;
- why the concept matters;
- a common beginner mistake;
- an optional link to a deeper explanation.

The glossary should support learning in context. The user should not need to leave the asset page to understand the term.

## 9.4 Comparison page

Comparison should be a flagship feature.

Typical beginner comparisons include:

- `VOO` vs `SPY`;
- `QQQ` vs `VGT`;
- `VTI` vs `VOO`;
- `AAPL` vs `MSFT`;
- `NVDA` vs `SOXX`.

The comparison page should explain:

- what each asset is;
- how the assets are structurally different;
- what each one holds or does;
- key risk differences;
- cost differences where relevant;
- exposure differences where relevant;
- valuation or financial quality differences where relevant;
- recent developments where relevant.

Each comparison should end with:

> **Bottom line for beginners**

That section should explain the real difference in plain language without telling the user which one to buy.

## 9.5 Recent developments section

Every asset page should include a clearly labeled recent developments section.

Possible section titles:

- Recent developments;
- What changed recently;
- Why this asset is in the news.

For stocks, recent developments may include:

- earnings;
- guidance changes;
- major product announcements;
- mergers and acquisitions;
- leadership changes;
- major regulatory events;
- major legal events;
- capital allocation changes.

For ETFs, recent developments may include:

- fee cuts;
- methodology changes;
- index changes;
- fund mergers;
- fund liquidations;
- meaningful sponsor updates.

This section should include high-signal events only. It should be treated as context, not the core definition of the asset.

## 9.6 Asset-specific grounded chat

After the user opens an asset page, they should see a chat module titled:

> **Ask about this asset**

The purpose is not to create a general market chatbot. The purpose is to let the user ask questions about the selected stock or ETF using a bounded evidence set.

Example questions:

- What does this company actually sell?
- Why is this ETF different from VOO?
- What is the biggest risk here for a beginner?
- Why do people say this fund is concentrated?
- What happened recently?
- Is this more like a core holding or a narrow bet?

Every answer should contain:

- a direct answer in plain English;
- why it matters;
- source citations;
- important uncertainty or missing context.

---

## 10. Product Content Model

## 10.1 Stock page content

### 10.1.1 Snapshot

The stock snapshot should include:

- name;
- ticker;
- sector;
- industry;
- exchange;
- market cap;
- price or last close;
- last updated timestamp.

### 10.1.2 Beginner summary

The beginner summary should explain:

- what the business does;
- why people consider it;
- why beginners should be careful.

This summary should avoid jargon where possible. When jargon is necessary, it should connect to glossary support.

### 10.1.3 Business overview

The business overview should cover:

- main products and services;
- business segments;
- main revenue drivers;
- geographic exposure;
- main competitors.

The product should prefer filing-derived and company-provided sources for this section.

### 10.1.4 Strengths

The strengths section should explain source-backed strengths such as:

- competitive advantage;
- scale;
- brand;
- switching costs;
- technology;
- industry tailwinds.

This section should avoid unsupported hype. Each major claim should be supported by citations.

### 10.1.5 Financial quality

The financial quality section should use multi-year trends, not one quarter alone.

Relevant metrics include:

- revenue trend;
- EPS trend;
- gross margin;
- operating margin;
- free cash flow;
- debt;
- cash;
- ROIC or ROE where available.

The product should explain what these metrics mean for a beginner rather than simply displaying them.

### 10.1.6 Risks

The page should show exactly three top risks first, with expandable detail.

Risk explanations should be:

- plain-English;
- source-grounded;
- specific to the company where possible;
- careful about uncertainty.

### 10.1.7 Valuation context

The valuation context section may include:

- P/E;
- forward P/E when sourced;
- price/sales;
- price/free cash flow;
- peer context;
- own-history context.

This section should not claim that a stock is “cheap” or “expensive” without context. It should explain valuation as a way to understand expectations and tradeoffs.

### 10.1.8 Suitability summary

The suitability summary should replace “buy now” or “avoid” language with educational framing.

It should explain:

- who this may fit;
- who may prefer an ETF instead;
- what would change the view;
- what the user should learn next.

## 10.2 ETF page content

### 10.2.1 Snapshot

The ETF snapshot should include:

- name;
- ticker;
- provider;
- category;
- asset class;
- passive or active classification;
- benchmark or index;
- expense ratio;
- AUM;
- last updated timestamp.

### 10.2.2 Beginner summary

The beginner summary should explain:

- what the ETF is trying to do;
- why beginners consider it;
- the main catch or common beginner misunderstanding.

### 10.2.3 ETF role

The ETF role section should explain:

- whether the fund is closer to a core holding, satellite holding, or narrow/specialized exposure;
- intended purpose;
- simpler alternatives.

This section should avoid personalized advice. It should describe general roles and tradeoffs.

### 10.2.4 What it holds

The holdings section should include:

- number of holdings;
- top 10 holdings;
- top 10 concentration;
- sector breakdown;
- country breakdown where relevant;
- largest position.

For beginners, this section is critical because the name of an ETF may not clearly communicate what the fund actually owns.

### 10.2.5 Construction

The construction section should explain:

- weighting method;
- rebalancing frequency;
- screening rules;
- notable methodology details.

This helps users understand why two ETFs with similar names may behave differently.

### 10.2.6 Cost and trading

The cost and trading section should include:

- expense ratio;
- bid-ask spread;
- average daily volume;
- AUM;
- premium/discount information where available.

This is especially useful for ETFs because ETF disclosures and issuer resources often include holdings, market information, premium/discount information, and bid-ask spread information.

### 10.2.7 Risks

ETF risks may include:

- market risk;
- concentration risk;
- liquidity risk;
- complexity risk;
- interest-rate risk where relevant;
- credit risk where relevant;
- currency risk where relevant;
- tracking risk where relevant.

The product should explain which risks matter most for the specific ETF.

### 10.2.8 Comparison and overlap

The ETF page should explain:

- similar ETF 1;
- similar ETF 2;
- why this ETF may be better for some educational use cases;
- why another ETF may be better for some educational use cases;
- overlap with a broad-market ETF;
- whether the ETF truly adds diversification.

### 10.2.9 Suitability summary

The ETF suitability summary should avoid “buy” or “avoid” language.

It should explain:

- who this may fit;
- when it may be too narrow;
- when a broader or cheaper ETF may be better;
- what would make it a poor fit.

---

## 11. Knowledge Architecture

The proposal should use a three-layer knowledge system.

## 11.1 Layer 1: Canonical facts

Canonical facts are stable source-backed facts.

For stocks, canonical facts include:

- identity;
- sector and industry;
- filing-derived business summary;
- multi-year financials;
- balance sheet and cash flow trends;
- filing-derived risk language.

For ETFs, canonical facts include:

- provider;
- benchmark;
- holdings;
- sector exposure;
- country exposure;
- methodology;
- fee;
- AUM;
- trading-cost context.

These facts should come from official or structured sources first.

## 11.2 Layer 2: Timely context

Timely context captures recent developments.

This layer includes:

- recent earnings and guidance;
- product launches;
- acquisitions;
- legal or regulatory events;
- methodology changes;
- fee changes;
- fund mergers;
- fund closures;
- other meaningful recent developments.

This layer should never overwrite Layer 1. It should sit beside Layer 1 as “recent developments” or “what changed recently.”

## 11.3 Layer 3: Teaching and explanation

This is where the model adds value.

The model should:

- rewrite source material in plain English;
- answer beginner questions;
- explain jargon;
- compare two assets;
- highlight what matters most for a beginner.

The model should not become the source of truth.

---

## 12. Source Hierarchy

The source hierarchy is part of the product’s trust model. Stable understanding should come from official and structured sources first. News should add recent context, not define the asset.

## 12.1 Stocks

For stocks, the source priority should be:

1. SEC filings and XBRL data;
2. company investor relations pages;
3. earnings presentations and transcripts;
4. structured market/reference data provider;
5. reputable news sources.

## 12.2 ETFs

For ETFs, the source priority should be:

1. ETF issuer official page;
2. ETF fact sheet;
3. summary prospectus and full prospectus;
4. shareholder reports;
5. structured market/reference data provider;
6. reputable news sources.

## 12.3 Source use by content type

Different content sections should use different source types.

| Content area              | Preferred sources                                     |
| ------------------------- | ----------------------------------------------------- |
| Stock identity            | SEC metadata, structured reference data               |
| Stock business overview   | 10-K, 10-Q, company investor relations                |
| Stock financial trends    | SEC XBRL, structured financial data                   |
| Stock risks               | 10-K and 10-Q risk factors                            |
| Stock recent developments | 8-Ks, earnings releases, reputable news               |
| ETF identity              | issuer page, structured reference data                |
| ETF holdings              | issuer holdings file, fact sheet                      |
| ETF methodology           | prospectus, index methodology, issuer page            |
| ETF risks                 | prospectus, summary prospectus                        |
| ETF recent developments   | issuer announcements, sponsor updates, reputable news |

---

## 13. Retrieval and Generation Pipeline

## 13.1 High-level pipeline

The system pipeline should follow these steps:

1. resolve the entity;
2. retrieve canonical facts;
3. ingest source documents;
4. chunk and index those documents;
5. extract normalized facts;
6. retrieve recent-context news or events;
7. assemble an asset knowledge pack;
8. generate page summaries;
9. bind citations;
10. cache and refresh.

## 13.2 Stock pipeline

### Step 1: Identity resolution

Map the ticker to company identity and CIK.

The system should determine:

- ticker;
- company name;
- exchange;
- CIK;
- sector;
- industry;
- supported asset status.

### Step 2: SEC ingestion

Fetch submissions history and XBRL-backed company facts.

SEC EDGAR data can support filings history and extracted XBRL data. This should be fetched server-side, rate-limited, and cached.

### Step 3: Filing retrieval

Locate the latest:

- 10-K;
- 10-Q;
- relevant recent 8-Ks.

### Step 4: Structured extraction

Extract:

- business overview;
- risk factors;
- management discussion;
- financial statement trends;
- segment information when available.

### Step 5: Reference data

Add quote and reference fields from the selected market-data provider.

Potential fields include:

- market cap;
- last close;
- sector;
- industry;
- valuation metrics;
- peer data.

### Step 6: Recent developments

Retrieve high-signal news and event summaries.

The system should avoid noisy or low-quality news. Recent developments should be relevant, cited, and separated from the core business definition.

### Step 7: Summary generation

Generate:

- beginner summary;
- top three risks;
- strengths summary;
- financial quality summary;
- recent developments summary;
- beginner Q&A context.

## 13.3 ETF pipeline

### Step 1: Identity resolution

Map ticker to:

- issuer;
- fund name;
- category;
- exchange;
- asset class;
- supported asset status.

### Step 2: Official source retrieval

Fetch:

- issuer page;
- fact sheet;
- summary prospectus;
- full prospectus;
- shareholder reports where relevant.

### Step 3: Holdings and exposure retrieval

Retrieve:

- holdings;
- top 10 holdings;
- concentration;
- sector allocations;
- country allocations;
- AUM;
- expense ratio;
- spread or trading metrics.

### Step 4: Recent developments

Add:

- sponsor announcements;
- fee changes;
- methodology changes;
- index changes;
- fund merger or closure news;
- other meaningful ETF updates.

### Step 5: Summary generation

Generate:

- what this ETF is trying to do;
- what it really holds;
- why beginners use it;
- what people often misunderstand;
- simpler alternatives;
- recent developments summary.

---

## 14. Asset Knowledge Pack and Grounded Chat

The asset knowledge pack is the central design for the chat feature and for source-grounded generation.

## 14.1 Asset knowledge pack contents

For every selected asset, the backend should build an asset knowledge pack containing:

- normalized fact table;
- key source documents;
- chunked evidence passages;
- recent developments snippets;
- glossary entries relevant to that asset;
- optional comparison data.

The chat should answer only from this pack.

That means the system does not rely on what the model already knows. It relies on retrieved, bounded, source-backed knowledge for the specific asset.

## 14.2 Chat flow

For each user question, the system should:

1. classify the question;
2. retrieve the most relevant chunks from the asset knowledge pack;
3. generate a structured answer in plain English with citations;
4. store conversational state so follow-up questions remain grounded.

## 14.3 Chat question classes

Supported classes include:

- definition;
- business model;
- holdings;
- risk;
- comparison;
- recent event;
- glossary;
- valuation context;
- suitability education;
- unsupported asset;
- personalized advice redirect.

## 14.4 Chat answer rules

Every answer should include:

- direct answer;
- why it matters;
- source citations;
- uncertainty or limits.

Every answer should avoid:

- buy/sell commands;
- personalized allocation advice;
- unsupported claims;
- free-form market prediction;
- certainty about future returns.

## 14.5 Example chat request

```json
{
  "ticker": "QQQ",
  "question": "Why is this more concentrated than VOO?"
}
```

## 14.6 Example chat response

```json
{
  "answer": "QQQ is more concentrated because it focuses on the Nasdaq-100, which is heavily weighted toward large technology and communications companies.",
  "why_it_matters": "That can make returns stronger in some periods, but it can also make the fund less diversified than a broad market ETF.",
  "citations": [
    { "claim_id": "c1", "source_id": "s12" },
    { "claim_id": "c2", "source_id": "s18" }
  ],
  "uncertainty": []
}
```

---

## 15. Technical Architecture

## 15.1 Frontend

Recommended frontend stack:

- Next.js;
- TypeScript;
- Tailwind CSS;
- shadcn/ui;
- lightweight charting library.

The frontend should support:

- search;
- beginner mode;
- deep-dive mode;
- source drawer;
- citation chips;
- glossary cards;
- asset-specific chat panel;
- comparison page.

## 15.2 Backend

Recommended backend stack:

- Python;
- FastAPI;
- background workers for ingestion and refresh;
- orchestration layer for retrieval and LLM calls.

The backend should handle:

- ticker resolution;
- source ingestion;
- source parsing;
- fact extraction;
- retrieval;
- summary generation;
- citation validation;
- freshness management;
- safety guardrails.

## 15.3 Data layer

Recommended data layer:

- PostgreSQL for normalized data;
- pgvector for semantic retrieval;
- Redis for cache and job coordination;
- object storage for saved PDFs, HTML snapshots, parsed files, and source artifacts.

## 15.4 Services

The system should include:

- web app;
- API layer;
- LLM provider integration, such as OpenRouter Free LLM model API for MVP;
- ingestion worker;
- retrieval and LLM orchestration service;
- data store.

## 15.5 Provider flexibility

The LLM provider should be abstracted so the product is not locked into one model provider.

The system should be able to use:

- OpenRouter-compatible models;
- OpenAI-compatible APIs;
- other hosted models;
- future local or open-source models if needed.

---

## 16. Suggested Internal APIs

```text
GET  /search?q=VOO
GET  /assets/{ticker}/overview
GET  /assets/{ticker}/details
GET  /assets/{ticker}/sources
GET  /assets/{ticker}/recent
POST /compare
POST /assets/{ticker}/chat
POST /ingest/{ticker}
GET  /jobs/{job_id}
```

## 16.1 Search

```text
GET /search?q=VOO
```

Purpose:

- resolve ticker or name;
- return supported asset matches;
- identify asset type;
- route user to correct page.

## 16.2 Asset overview

```text
GET /assets/{ticker}/overview
```

Purpose:

- return beginner-mode asset summary;
- show snapshot;
- show top risks;
- show recent developments;
- include citations and freshness.

## 16.3 Asset details

```text
GET /assets/{ticker}/details
```

Purpose:

- return deep-dive mode content;
- include financial metrics or ETF exposure details;
- include source-backed nuance.

## 16.4 Sources

```text
GET /assets/{ticker}/sources
```

Purpose:

- return source list;
- include source type, title, URL, date, retrieved timestamp, and citation mapping.

## 16.5 Recent developments

```text
GET /assets/{ticker}/recent
```

Purpose:

- return recent developments only;
- keep recent context separate from canonical facts.

## 16.6 Compare

```text
POST /compare
```

Purpose:

- compare two assets;
- return side-by-side differences;
- include bottom line for beginners;
- include citations.

## 16.7 Asset chat

```text
POST /assets/{ticker}/chat
```

Purpose:

- answer asset-specific user questions;
- retrieve from the asset knowledge pack;
- return cited plain-English responses.

## 16.8 Ingestion job

```text
POST /ingest/{ticker}
GET  /jobs/{job_id}
```

Purpose:

- start asset ingestion or refresh;
- track job status.

---

## 17. Data Model

Core entities should include the following tables or equivalent data structures.

## 17.1 `assets`

Stores canonical asset identity.

Fields:

- `id`;
- `ticker`;
- `name`;
- `asset_type`;
- `cik`;
- `provider`;
- `exchange`.

## 17.2 `source_documents`

Stores official documents, issuer pages, filings, fact sheets, news articles, and source snapshots.

Fields:

- `id`;
- `asset_id`;
- `source_type`;
- `title`;
- `url`;
- `published_at`;
- `retrieved_at`;
- `checksum`.

## 17.3 `document_chunks`

Stores retrievable evidence chunks.

Fields:

- `id`;
- `source_document_id`;
- `section_name`;
- `text`;
- `embedding`;
- `chunk_order`.

## 17.4 `facts`

Stores normalized facts used for rendering and generation.

Fields:

- `id`;
- `asset_id`;
- `field_name`;
- `value_json`;
- `unit`;
- `period`;
- `as_of_date`;
- `source_document_id`;
- `extraction_method`;
- `confidence`.

## 17.5 `recent_events`

Stores timely context separately from canonical facts.

Fields:

- `id`;
- `asset_id`;
- `event_type`;
- `summary`;
- `event_date`;
- `source_document_id`;
- `importance_score`.

## 17.6 `summaries`

Stores generated outputs.

Fields:

- `id`;
- `asset_id`;
- `summary_type`;
- `output_json`;
- `model_name`;
- `freshness_hash`.

## 17.7 Additional useful tables

As the product matures, it may also need:

- `holdings` for ETF holdings;
- `exposures` for sector, country, industry, or asset-class exposure;
- `financial_metrics` for normalized stock metrics;
- `claims` for claim-to-citation mapping;
- `glossary_terms` for concept learning;
- `ingestion_jobs` for background job tracking.

---

## 18. Freshness and Caching

Freshness is part of trust.

The system should show:

- page freshness;
- section freshness;
- source date;
- retrieval timestamp.

## 18.1 Suggested refresh rules

| Data type                  | Suggested refresh behavior                        |
| -------------------------- | ------------------------------------------------- |
| SEC filings and XBRL facts | Scheduled refresh plus on-demand refresh          |
| ETF holdings and exposure  | Daily refresh or refresh when source dates change |
| Price and reference data   | Vendor-dependent TTL                              |
| Recent news and events     | Shorter TTL                                       |
| LLM summaries              | Invalidate when underlying fact hashes change     |

## 18.2 SEC data handling

SEC data should be fetched server-side, rate-limited, and cached aggressively rather than fetched on every user page load.

## 18.3 Summary invalidation

Generated summaries should be invalidated when:

- source document checksum changes;
- facts change;
- holdings change;
- recent events change;
- prompt version changes;
- model version changes;
- citation validation fails.

## 18.4 User-facing freshness states

The UI should show states such as:

- fresh;
- stale;
- unknown;
- mixed evidence;
- unavailable.

The product should never hide missing or stale data when that information matters to user understanding.

---

## 19. UX Trust Features

The product should make trust visible.

## 19.1 Citation chips

Citation chips should appear near important factual claims.

They should be:

- visible;
- clickable;
- compact;
- connected to the source drawer.

## 19.2 Source drawer

The source drawer should show:

- source title;
- source type;
- official-source badge where applicable;
- publisher;
- published date;
- retrieved timestamp;
- URL;
- related claims;
- supporting excerpt or evidence passage where available.

## 19.3 Official source badges

Official sources should be labeled clearly.

Examples:

- SEC filing;
- issuer page;
- fact sheet;
- prospectus;
- company investor relations.

## 19.4 As-of dates

The UI should show:

- page last updated;
- facts as of date;
- holdings as of date;
- recent developments checked date;
- source retrieval timestamp.

## 19.5 Separate recent developments label

Recent developments should be visually separate from asset basics.

This prevents the user from confusing short-term news with the asset’s core structure or business model.

## 19.6 Glossary hover cards

Glossary cards should help users understand important terms without leaving the page.

Each card should include:

- simple definition;
- why it matters;
- common beginner mistake;
- optional deeper link.

## 19.7 Unknown and mixed-evidence states

Where evidence is missing, stale, conflicting, or incomplete, the product should say so clearly.

Examples:

- “We could not verify this from an official source.”
- “Holdings data may be stale.”
- “Recent developments are mixed.”
- “No high-signal recent developments found.”

---

## 20. Safety and Product Guardrails

## 20.1 Product stance

The product is educational. It is not personalized investment advice.

The product can explain:

- what an asset is;
- what it holds or does;
- what risks matter;
- how it compares with alternatives;
- what factors a beginner may want to understand.

The product should not tell users:

- whether to buy or sell;
- how much to allocate;
- what price target to use;
- what is guaranteed to happen;
- how to structure taxes.

## 20.2 Required guardrails

The product should:

- avoid direct buy/sell language;
- avoid personalized position sizing;
- avoid unsupported price targets;
- distinguish stable facts from recent developments;
- cite important claims;
- say “unknown” when evidence is missing;
- warn clearly when an ETF is unusually narrow or complex;
- redirect personalized advice questions into educational explanations.

## 20.3 Example safety pattern

If a user asks:

> Should I buy QQQ?

The product should not answer:

> Yes, buy QQQ.

A safer answer would be:

> I can’t tell you whether to buy it. I can help you understand what QQQ is, what it holds, how concentrated it is, how it differs from a broader ETF like VOO, and what risks a beginner should understand before making their own decision.

---

## 21. Success Metrics

The product should measure trust and comprehension, not just clicks.

## 21.1 Product metrics

| Metric                             | Meaning                                                      |
| ---------------------------------- | ------------------------------------------------------------ |
| Citation coverage rate             | Percentage of important claims with citations                |
| Unsupported claim rate             | Percentage of generated claims without source support        |
| Asset-page completion rate         | Percentage of users who continue beyond the beginner summary |
| Compare-page usage                 | Percentage of sessions using comparison                      |
| Chat follow-up rate                | Percentage of chat users asking at least one follow-up       |
| Glossary usage                     | Percentage of sessions using glossary cards                  |
| Freshness accuracy                 | Whether displayed freshness labels match source state        |
| Latency to first meaningful result | Time from search to useful page content                      |

## 21.2 User-learning metrics

| Metric                                 | Meaning                                       |
| -------------------------------------- | --------------------------------------------- |
| Understanding of “what this is”        | Whether the user understands the asset basics |
| Understanding of top risks             | Whether the user can identify major risks     |
| Understanding of how two assets differ | Whether comparison helped the user learn      |
| Trust in citations and source display  | Whether citations increased confidence        |

## 21.3 Trust-oriented product goal

A good session is not necessarily one where a user trades. A good session is one where the user better understands the asset, the risks, the sources, and the tradeoffs.

---

## 22. Phased Roadmap

## 22.1 Phase 1: Core asset pages

Phase 1 should include:

- search;
- stock page;
- ETF page;
- source drawer;
- glossary;
- basic recent developments block;
- beginner mode;
- initial citation support.

## 22.2 Phase 2: Comparison and risk improvements

Phase 2 should include:

- compare page;
- ETF overlap analysis;
- improved risk summaries;
- freshness indicators;
- better source states.

## 22.3 Phase 3: Grounded chat

Phase 3 should include:

- asset-specific grounded chat;
- starter prompts for beginners;
- richer recent-context retrieval;
- saved assets and saved comparisons.

## 22.4 Phase 4: Learning and retention workflows

Phase 4 should include:

- watchlist;
- learning paths;
- beginner lessons tied to asset pages;
- broader research workflows.

---

## 23. Final Thesis

The strongest version of this side project is not “AI for stock picking.”

It is:

> **A source-first financial learning product for beginners, with stable facts, recent context, and grounded chat in one place.**

Its real differentiation is the combination of:

- beginner language;
- official-source grounding;
- visible citations;
- comparison-first design;
- separate recent-developments layer;
- asset-specific tutor-style chat.

That combination makes the project more useful, more trustworthy, and more realistic to build.

The product should help users understand what they are looking at before they make their own decisions.

---

## 24. References

[1]: https://www.sec.gov/investor/pubs/sec-guide-to-mutual-funds.pdf "Mutual Funds and ETFs"
[2]: https://www.sec.gov/about/divisions-offices/division-investment-management/accounting-disclosure-information/adi-2025-15-website-posting-requirements "SEC.gov | ADI 2025-15 – Website posting requirements"
[3]: https://www.sec.gov/search-filings/edgar-application-programming-interfaces "SEC.gov | EDGAR Application Programming Interfaces (APIs)"
