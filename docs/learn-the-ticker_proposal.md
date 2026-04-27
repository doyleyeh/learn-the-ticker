# Learn the Ticker: Citation-First Beginner U.S. Stock & ETF Research Assistant

**Document type:** Detailed product proposal  
**Version:** v0.4 frontend/workflow update
**Last updated:** 2026-04-24
**Project stage:** Side-project MVP / v1 planning
**Documentation role:** Narrative product vision. The PRD is the product source of truth, and the technical design spec is the implementation source of truth.

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

A user can search one ticker or asset name such as `VOO`, `QQQ`, `Apple`, or `AAPL` and receive a plain-English explanation of:

- what the asset is;
- what the company does, or what the ETF holds;
- why people consider it;
- the main risks;
- how it compares with another supported asset when comparison is useful;
- what changed recently;
- which sources support the important claims.

The product should use official and structured sources as the factual backbone. The language model should not be treated as the source of truth. Instead, the model should translate verified facts, filings, prospectuses, holdings data, and other source-backed material into simple explanations for beginners.

Fetching a filing, issuer document, API endpoint, or provider payload is only retrieval. It is not evidence approval. Golden Asset Source Handoff is the approval layer that decides whether a retrieved source may be stored, summarized, cited, generated from, or exported.

The result should feel like a calm learning product with receipts: easy to understand, visibly sourced, and careful about the difference between education and investment advice. The home page should lead with single-asset search. Comparison should be easy to enter, but it should live in its own workflow rather than replacing the main search experience.

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

A comparison-capable product can help beginners learn faster because the differences become easier to understand when two assets are placed side by side. That does not mean the home page should be a comparison dashboard: the core home experience should remain searching one stock or ETF, with comparison available when the user asks for it.

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
- a comparison-capable learning tool;
- a source-grounded financial learning product;
- a guided way to understand risks, holdings, company basics, valuation context, Weekly News Focus, and AI Comprehensive Analysis.

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

For stocks such as `AAPL` and `NVDA`, that means SEC EDGAR, SEC XBRL company facts, and SEC filing documents form the canonical backbone. Company investor relations pages, earnings releases, and presentations can be official secondary sources for recent context and management explanations.

For ETFs such as `VOO`, `QQQ`, and `SOXX`, that means issuer materials form the canonical backbone: the official issuer page, fact sheet, prospectus, shareholder reports, holdings files, exposure files, and sponsor announcements.

Market/reference APIs and other provider payloads are retrieval and enrichment tools, not automatic evidence. Before any source can support product output, Golden Asset Source Handoff must approve its domain, source type, official-source status, storage rights, export rights, source-use policy, rationale, parser validity, and review status.

### 6.2 Plain English first

Every asset page should begin with a beginner summary. The first view should help the user understand the asset without requiring prior finance knowledge.

### 6.3 Comparison is connected

Beginners often learn faster by comparing assets than by reading one asset page in isolation. Comparison should be a flagship connected workflow, not the home page's primary action.

The product should support comparison from:

- global navigation;
- asset-page "Compare this asset" actions;
- suggested comparisons;
- chat compare redirects;
- natural search patterns such as `VOO vs QQQ`.

### 6.4 Stable facts, Weekly News Focus, and AI analysis must stay separate

The product must clearly distinguish between:

- what the asset is;
- what the company does or what the ETF holds;
- what happened in the current Weekly News Focus window.

Weekly News Focus and AI synthesis should add context. They should not redefine the asset.

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
- how Weekly News Focus may matter;
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

The first version should stay narrow and credible while still targeting the full MVP experience. Implementation may happen in phases, but v1 is not considered ready until the MVP acceptance checklist in the PRD and technical design spec passes.

### 8.1 In scope

The v1 product should support:

- the top 500 U.S.-listed common stocks first;
- non-leveraged U.S.-listed equity index, sector, and thematic ETFs;
- home-page single-asset ticker/name search;
- search and entity resolution;
- stock asset pages;
- ETF asset pages;
- beginner section;
- deep-dive section;
- dedicated comparison workflow for ETF-vs-ETF, stock-vs-stock, and stock-vs-ETF;
- Weekly News Focus and AI Comprehensive Analysis section;
- asset-specific grounded chat;
- contextual beginner glossary cards;
- source drawer with citations and freshness;
- Markdown/JSON exports for asset pages, comparisons, source lists, and chat transcripts;
- basic educational suitability summaries.

Stocks outside the top-500 MVP universe should not be promised as ready in v1. If a recognized stock is not in the launch universe, the product should show `pending_ingestion`, `unsupported`, `partial`, or `unavailable` based on deterministic classification and source availability.

### 8.1.1 Top-500 Universe Definition

The exact top-500 stock universe should come from a versioned manifest, not from a live provider query on each user request.

- Local source of truth: `data/universes/us_common_stocks_top500.current.json`.
- Production mirror: private GCS object configured through `TOP500_UNIVERSE_MANIFEST_URI`.
- Manifest entries should include ticker, name, CIK when available, exchange, rank, rank basis, provider/source provenance, snapshot date, generated checksum, and approval timestamp.
- External providers can supply ranking inputs, but the manifest is what the app trusts at runtime. Runtime coverage must never be resolved directly from a live ETF or provider holdings file.
- Refresh monthly by default. Ad hoc refreshes require a development-log entry.
- This universe is for operational coverage and testing only. It is not a recommendation list.

The monthly refresh should use official ETF holdings as source inputs, then produce a reviewed candidate manifest instead of directly overwriting runtime coverage.

- Primary source: official iShares Russell 1000 ETF (`IWB`) holdings. Rank valid U.S. common-stock rows by fund weight and record `rank_basis = "iwb_weight_proxy"`.
- Fallback source: official S&P 500 ETF holdings from `SPY`, `IVV`, and `VOO`. Use this only when IWB fails, is stale, cannot be parsed, or yields too few validated common-stock rows, and record `rank_basis = "sp500_etf_weight_proxy_fallback"`.
- Candidate output: `data/universes/us_common_stocks_top500.candidate.YYYY-MM.json`.
- Approved output: `data/universes/us_common_stocks_top500.current.json`, mirrored to the private GCS object used by production.
- Candidate manifests should include source provenance, source snapshot date, source checksum, rank, rank basis, CIK, exchange, validation status, and warnings.
- Normalize tickers and security rows before ranking. Exclude cash, futures, options, swaps, index rows, ETFs, preferreds, warrants, rights, units, funds, and other non-common-stock securities.
- Validate candidates against SEC `company_tickers_exchange.json` and Nasdaq Trader symbol-directory fields such as `ETF` and `Test Issue`. Rows that cannot be validated should be flagged for review instead of silently included.
- Generate a diff report before approval, including added tickers, removed tickers, rank changes, missing CIKs, Nasdaq validation failures, source used, source dates, and checksum.
- Require manual approval when fallback sources are used, source snapshots are stale or unparseable, validation coverage is below threshold, many tickers change, or top-ranked names disappear.

### 8.2 Out of scope for v1

The v1 product should not support:

- options;
- leveraged ETFs;
- inverse ETFs;
- ETNs;
- fixed income ETFs;
- commodity ETFs;
- active ETFs;
- multi-asset ETFs;
- tax guidance;
- personalized allocation advice;
- brokerage trading;
- international equities;
- crypto;
- preferred stocks;
- warrants;
- rights;
- portfolio optimization;
- automated buy/sell signals;
- unsupported price targets.

### 8.3 Scope rationale

The scope should be narrow because the product's value depends on trust. It is better to explain a smaller set of assets well than to support many complex asset types with weak sourcing or unclear guardrails.

---

## 9. Core Product Experience

## 9.1 Search and entity resolution

The home page is for one primary action:

> **Search for a single supported stock or ETF.**

Recommended home headline:

> **Understand a stock or ETF in plain English**

Recommended supporting copy:

> Search a U.S. stock or non-leveraged U.S. equity ETF to see beginner-friendly explanations, source citations, top risks, recent context, and grounded follow-up answers.

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

Search should support exact ticker, partial ticker, partial name, and issuer/provider matches where useful. Result rows should show ticker, name, asset type, exchange or issuer/provider, and a support status chip such as supported, pending ingestion, partial data, stale data, unsupported, out of scope, unavailable, or unknown.

After resolution, the user lands on the correct asset page only when the asset is supported or in a supported state that can show a safe page. Recognized-but-unsupported, out-of-scope, unavailable, and unknown states should not generate an asset page, chat answer, comparison output, Weekly News Focus, or AI Comprehensive Analysis.

The system should clearly distinguish between stocks and ETFs because the explanation template, source needs, risks, and metrics are different.

If the home search detects a clear comparison query such as `VOO vs QQQ`, it should show a special autocomplete result that opens `/compare?left=VOO&right=QQQ`. The home page should not become a comparison builder.

## 9.2 Asset page structure

Each asset page should be a learning page, not a data dump. The first screen should answer:

- What is this?
- Why do people look at it?
- What should a beginner be careful about?
- Where did this information come from?

Recommended section order:

1. **Asset Header**;
2. **Beginner Summary**;
3. **Top 3 Risks**;
4. **Key Facts**;
5. **What it does / What it holds**;
6. **Weekly News Focus**;
7. **AI Comprehensive Analysis**;
8. **Deep Dive**;
9. **Ask about this asset**;
10. **Sources**;
11. **Educational disclaimer**.

### 9.2.1 Beginner section

The Beginner section appears first on the asset page.

It should show:

- what the asset or company is;
- why people may look at it;
- the main thing to be careful about;
- top three risks;
- key facts;
- freshness;
- key sources;
- glossary support for important terms.

The goal is to help the user understand the asset quickly without overwhelming them.

### 9.2.2 Deep-Dive section

The Deep-Dive section expands the asset page for users who want more detail.

It should include:

- detailed financial metrics;
- business segment breakdowns for stocks;
- holdings and exposure breakdowns for ETFs;
- prospectus or filing-based nuance;
- peer comparison;
- methodology details;
- Weekly News Focus evidence and educational AI context;
- full source list and source dates;
- Markdown/JSON export controls.

The Deep-Dive section should add depth without changing the core beginner explanation.

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

The app should allow the user to open a glossary card exactly where the term appears. Glossary is contextual help inside asset pages, comparison pages, and chat answers. It should not be a major home-page workflow for MVP, and asset pages should not collect all glossary terms into one large standalone glossary section that users must scan separately from the content.

Important terms should be wrapped inline in their natural section: for example, P/E inside valuation context, AUM and expense ratio inside ETF snapshot or cost context, and tracking error inside fund construction or tracking context. The trigger should preserve the reading flow so users can learn the term without losing the surrounding claim, citation, or section.

Each glossary card should include:

- a simple definition;
- why the concept matters;
- a common beginner mistake;
- related terms;
- an optional link to a deeper explanation;
- optional asset-specific context when grounded in the selected asset's data.

The glossary should support learning in context. Desktop should support hover preview, click-to-pin, and keyboard focus from the inline term. Mobile should support tap to open a bottom sheet from the inline term; long tap may also open the sheet, but it should not be the only gesture.

## 9.4 Comparison page

Comparison should be a flagship connected workflow. It should be reachable from global navigation, asset-page CTAs, suggested comparisons, chat compare redirects, and natural search patterns such as `VOO vs QQQ`.

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
- Weekly News Focus and AI Comprehensive Analysis where relevant.

MVP should support ETF-vs-ETF, stock-vs-stock, and stock-vs-ETF templates. Stock-vs-ETF comparison needs a dedicated structure because a stock is one company and an ETF is a basket. The template should explicitly explain single-company risk vs basket risk, business model vs holdings exposure, company financials vs fund methodology, valuation metrics vs expense ratio and concentration, and idiosyncratic risk vs diversified sector exposure. `NVDA` vs `SOXX` should remain a golden-path cross-type example.

Stock-vs-ETF pages should show a relationship badge:

- direct holding comparison;
- related sector or theme exposure;
- broad-market context;
- weak relationship.

Weak relationships may be available as structural education when both assets are supported, but they should not be suggested prominently.

Each comparison should begin with:

> **Bottom line for beginners**

That section should explain the real difference in plain language without telling the user which one to buy.

## 9.5 Weekly News Focus and AI Comprehensive Analysis

Every asset page should include a clearly labeled Weekly News Focus module. This module should replace a generic recent-news feed with two source-grounded parts:

1. **Weekly News Focus**;
2. **AI Comprehensive Analysis**.

The Weekly News Focus should show a source-grounded weekly list of high-signal items for the selected asset. The default window should use the last completed Monday-Sunday market week plus the current week-to-date through yesterday, using U.S. Eastern dates. For example, if today is Wednesday, the module should include last Monday through Sunday plus this Monday and Tuesday.

It should show the configured maximum only when enough high-quality evidence exists. Fewer items are acceptable when the evidence set is limited, and many broad ETFs may legitimately show "No major Weekly News Focus items found for this window." The product should never pad the list with weak, duplicative, promotional, irrelevant, non-allowlisted, or license-disallowed items just to reach a target count.

Each Weekly News Focus item should include:

- source or publisher;
- headline or title;
- published date;
- one-sentence beginner-friendly summary;
- citation or source drawer link;
- freshness and source-quality metadata.

The AI Comprehensive Analysis should synthesize the Weekly News Focus into educational context. It should appear only when at least two high-signal Weekly News Focus items exist. The module should begin with **What Changed This Week**, then use three safer context sections:

- **Market Context**;
- **Business/Fund Context**;
- **Risk Context**.

These section names are product UI labels, not real people, advisors, or independent model identities. Each context section should be short, plain-English, and cited to the underlying Weekly News Focus items or canonical facts. It should explain what the news may mean for understanding the asset, without making predictions or recommendations.
Each analysis section should use a compact paragraph plus bullets, cite the underlying Weekly News Focus items and any canonical facts it uses, and include uncertainty notes when evidence is thin.

For stocks, Weekly News Focus items may include:

- earnings;
- guidance changes;
- major product announcements;
- mergers and acquisitions;
- leadership changes;
- major regulatory events;
- major legal events;
- capital allocation changes.

For ETFs, Weekly News Focus items may include:

- fee cuts;
- methodology changes;
- index changes;
- fund mergers;
- fund liquidations;
- meaningful sponsor updates.

This section should include high-signal events only. It should be treated as context, not the core definition of the asset. If no high-signal Weekly News Focus items exist, the UI should show a clear empty state and suppress AI Comprehensive Analysis. If only one high-signal item exists, the UI should show the item but mark AI Comprehensive Analysis as insufficient evidence.

V1 should be English-first. Traditional Chinese localization can be added later. Read-aloud or text-to-speech controls are not part of the v1 requirement.

## 9.6 Asset-specific grounded chat

After the user opens an asset page, they should see a chat module titled:

> **Ask about this asset**

The purpose is not to create a general market chatbot. The purpose is to let the user ask questions about the selected stock or ETF using a bounded evidence set. Chat is a helper feature: on desktop it can live in a helper rail or side panel, and on mobile it should open from a sticky Ask action as a bottom sheet or full-screen panel.

Example questions:

- What does this company actually sell?
- Why is this ETF different from VOO?
- What is the biggest risk here for a beginner?
- Why do people say this fund is concentrated?
- What happened recently?
- Is this broad or narrow exposure?

Every answer should contain:

- a direct answer in plain English;
- why it matters;
- sources;
- important uncertainty or missing context.

If a user asks about another ticker inside single-asset chat, the product should not answer as multi-asset chat. It should route to comparison so both assets can be grounded in their own source packs.

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

This section should not claim that a stock is "cheap" or "expensive" without context. It should explain valuation as a way to understand expectations and tradeoffs.

### 10.1.8 Suitability summary

The suitability summary should replace recommendation-style language with educational framing.

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

- whether the fund is broad/core-like, satellite-like, or narrow/specialized exposure;
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

The ETF suitability summary should avoid "buy" or "avoid" language.

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

Timely context captures Weekly News Focus and source-grounded events.

This layer includes:

- recent earnings and guidance;
- product launches;
- acquisitions;
- legal or regulatory events;
- methodology changes;
- fee changes;
- fund mergers;
- fund closures;
- other meaningful Weekly News Focus items.

This layer should never overwrite Layer 1. It should sit beside Layer 1 as Weekly News Focus and, when evidence is sufficient, AI Comprehensive Analysis.
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

The MVP should assume a free-first evidence strategy: SEC data, official issuer materials, curated free or RSS news sources, provider adapters, deterministic mocks, and fixtures for tests. Paid data providers may be added later behind adapters after licensing, pricing, and export rights are reviewed.

The source hierarchy is part of the product's trust model. Stable understanding should come from official and structured sources first. Weekly News Focus should add context, not define the asset.

Golden Asset Source Handoff is the approval layer between retrieval and evidence use. API clients, fetch adapters, SEC/issuer fetch commands, provider endpoints, and downloaded payloads belong to the retrieval layer. Approved evidence requires allowlisted domain, source type, official-source status, storage rights, export rights, source-use policy, rationale, parser validity, freshness/as-of metadata, and review status. A source that is missing from the allowlist, has unclear rights, fails parser validation, or comes from a hidden/internal endpoint should be marked `pending_review` or `rejected` rather than used as evidence.

Weekly News Focus should use a tiered allowlist. Official sources come first, including SEC filings, company investor relations releases, ETF issuer announcements, prospectus updates, fact-sheet updates, exchange notices, and issuer newsrooms. Reuters/AP-style and other reputable news publishers should be treated as license-gated, not as free full-content sources by default. Before content is stored, summarized, rendered, or exported, the app should know whether the source is `metadata_only`, `link_only`, `summary_allowed`, `full_text_allowed`, or `rejected`.

Allowlist governance should be config-only review. The allowlist lives in configuration, for example `config/source_allowlist.yaml`. A future agent may update it only when the domain, source type, source-use policy, rationale, and validation tests move together, and the development log records why the source changed. Automated scoring can rank already-allowed sources but cannot approve a new source.

Provider hierarchy for v1:

- Use SEC EDGAR and ETF issuer materials as the trust backbone for stable facts, source documents, and risk extraction.
- Use Financial Modeling Prep, Finnhub, Tiingo, Alpha Vantage, EODHD, yfinance, and similar services only as optional enrichment where licensing, rate limits, caching, attribution, display, and export rights allow. Provider data must not override official SEC or issuer evidence.
- Use official-first event sources for Weekly News Focus before any general news API.
- Treat yfinance as local-development and fallback-only, not production truth.
- Design the UI around `fresh`, `stale`, `partial`, and `unavailable` states instead of assuming every quote or reference field is present.

Provider roles:

- SEC EDGAR is best for stock identity, filings history, XBRL company facts, filing-derived business descriptions, and risk extraction. It is free, keyless, and updated throughout the day.
- Financial Modeling Prep is useful for reference enrichment such as quotes, volume, some aftermarket bid/ask data, statement convenience endpoints, AUM/net-assets-style ETF fields, ETF/fund holdings, and a broad endpoint surface. Public display or redistribution requires a specific FMP data display and licensing agreement, so product output must distinguish internal ingestion convenience from externally displayed/exported content.
- Alpha Vantage is useful for low-volume experiments and selected market/reference enrichment, but the standard free limit of 25 API requests per day is too restrictive for broad pre-caching or aggressive ingestion.
- Finnhub is useful for quote, fundamentals, and news-style enrichment in side-project prototypes, but its listed plans are personal-use unless explicitly approved and redistribution requires written approval.
- Tiingo is useful for end-of-day data, corporate actions, selected news/fundamentals endpoints, and ETF/mutual-fund fee metadata. It fits stable, non-tick-level historical series better than a product that implies guaranteed real-time quotes.
- EODHD is useful for light testing and selective enrichment where EOD-style history, delayed live data, and basic fundamentals are enough, but free access is small and public usage requires personal-use/commercial-use review.
- yfinance is useful for local development and fallback diagnostics only. It should not be used as production truth or as a redistributable public product data source.

Raw source text should use a rights-tiered policy. Official filings, issuer materials, and `full_text_allowed` sources may store raw text, parsed text, chunks, checksums, and private snapshots. `summary_allowed` sources may store metadata, links, checksums, and limited excerpts needed for summaries. `metadata_only` and `link_only` sources may store metadata, hashes, canonical URLs, timestamps, and diagnostics, but not full article text. `rejected` sources should not feed generated output. Missing or unclear rights should default to `pending_review` or `rejected`, not evidence.

The operational rule is: fetch only from allowlisted sources, store according to source-use policy, generate only from approved evidence, and export only what the policy permits. Automated scoring may rank already-approved sources, but it must not approve a new source by itself.

## 12.1 Stocks

For stocks, the source priority should be:

1. SEC EDGAR, SEC XBRL company facts, and SEC filing documents;
2. company investor relations pages;
3. earnings presentations and transcripts;
4. free or official reference metadata where available;
5. allowlisted reputable free news sources for Weekly News Focus context.

## 12.2 ETFs

For ETFs, the source priority should be:

1. ETF issuer official page;
2. ETF fact sheet;
3. summary prospectus and full prospectus;
4. shareholder reports;
5. issuer holdings files, exposure files, and official ETF website disclosures;
6. sponsor announcements and allowlisted reputable free news sources for Weekly News Focus context.

## 12.3 Source use by content type

Different content sections should use different source types.

| Content area              | Preferred sources                                     |
| ------------------------- | ----------------------------------------------------- |
| Stock identity            | SEC metadata, free/reference metadata                  |
| Stock business overview   | 10-K, 10-Q, company investor relations                |
| Stock financial trends    | SEC XBRL, approved structured enrichment data         |
| Stock risks               | 10-K and 10-Q risk factors                            |
| Stock Weekly News Focus events | 8-Ks, earnings releases, allowlisted news             |
| ETF identity              | issuer page, approved free/reference metadata         |
| ETF holdings              | issuer holdings file, fact sheet                      |
| ETF methodology           | prospectus, index methodology, issuer page            |
| ETF risks                 | prospectus, summary prospectus                        |
| ETF Weekly News Focus events | issuer announcements, sponsor updates, allowlisted news |

---

## 13. Retrieval and Generation Pipeline

## 13.1 High-level pipeline

The system pipeline should follow these steps:

1. resolve the entity;
2. retrieve canonical facts;
3. fetch source documents only from allowlisted sources;
4. pass retrieved sources through Golden Asset Source Handoff before evidence use;
5. store raw or parsed content only according to source-use policy;
6. chunk and index approved documents;
7. extract normalized facts;
8. retrieve official Weekly News Focus events and allowlisted source context;
9. assemble an asset knowledge pack from approved evidence;
10. generate page summaries, Weekly News Focus, and AI Comprehensive Analysis;
11. bind citations;
12. cache and refresh.

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

Fetched SEC metadata, XBRL facts, and filing documents still pass through Golden Asset Source Handoff before storage, chunking, citation, or export. SEC sources are official, but each retrieved URL, filing type, parser result, storage right, export right, and as-of date still needs a reviewed evidence record.

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

Add quote and reference fields from free or official sources where available, or from adapter-backed providers if configured. Free-first v1 must treat missing quote, valuation, or trading fields as partial data rather than inventing or inferring them.

Provider quote and reference fields are optional enrichment. They can fill convenience metadata or delayed/best-effort market fields only after rights and attribution are reviewed, and they must not override SEC-backed canonical facts.

Potential fields include:

- market cap;
- last close;
- sector;
- industry;
- valuation metrics;
- peer data.

### Step 6: Weekly News Focus and AI Comprehensive Analysis

Retrieve high-signal official events first, then licensed or allowlisted free-news or RSS event summaries. Deduplicate, score, and select up to the configured Weekly News Focus maximum only when enough evidence exists.

The system should avoid noisy, promotional, duplicated, or unrecognized news sources. Weekly News Focus items and AI Comprehensive Analysis claims should be relevant, cited, and separated from the core business definition.

Weekly News Focus scoring defaults:

| Field | Defaults |
| --- | --- |
| `source_quality_weight` | official `5`; allowlisted_reputable `3`; provider_metadata_only `1` |
| `event_type_weight` | earnings `5`; guidance `5`; fee_change `5`; methodology_change `5`; routine_press_release `1` |
| `recency_weight` | current_week_to_date `3`; previous_market_week `2`; older_but_relevant `1` |
| `asset_relevance_weight` | exact ticker/CIK/issuer match `3`; strong fund/company match `2`; sector/theme context only `1` |
| `duplicate_penalty` | exact duplicate `5`; near duplicate `3`; same story cluster after first item `2` |

Use `importance_score = source_quality_weight + event_type_weight + recency_weight + asset_relevance_weight - duplicate_penalty`, with `minimum_display_score = 7` and `minimum_ai_analysis_items = 2`. Source-use policy overrides score: rejected or license-disallowed sources never display.

### Step 7: Summary generation

Generate:

- beginner summary;
- top three risks;
- strengths summary;
- financial quality summary;
- Weekly News Focus;
- AI Comprehensive Analysis with What Changed This Week, Market Context, Business/Fund Context, and Risk Context sections;
- beginner Q&A context.

## 13.3 ETF pipeline

### Step 1: Identity resolution

Map ticker to:

- issuer;
- fund name;
- equity ETF category;
- exchange;
- asset class;
- supported asset status.

### Step 2: Official source retrieval

Fetch:

- issuer page;
- fact sheet;
- summary prospectus;
- full prospectus;
- shareholder reports where relevant;
- holdings files;
- exposure files;
- sponsor announcements where relevant.

Fetched issuer materials still pass through Golden Asset Source Handoff before storage, chunking, citation, or export. Official issuer status is necessary but not sufficient; domain, source type, parser validity, storage rights, export rights, and rationale must also be approved.

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

If free-first sources cannot verify one of these fields, the page should render verified sections only, label the missing section unavailable or stale, and suppress unsupported generated claims.

### Step 4: Weekly News Focus and AI Comprehensive Analysis

Add:

- sponsor announcements;
- fee changes;
- methodology changes;
- index changes;
- fund merger or closure news;
- other meaningful ETF updates from official or allowlisted sources.

The ETF Weekly News Focus workflow should follow the same two-part structure as stock pages: Weekly News Focus plus AI Comprehensive Analysis.

### Step 5: Summary generation

Generate:

- what this ETF is trying to do;
- what it really holds;
- why beginners use it;
- what people often misunderstand;
- simpler alternatives;
- Weekly News Focus;
- AI Comprehensive Analysis.

---

## 14. Asset Knowledge Pack and Grounded Chat

The asset knowledge pack is the central design for the chat feature and for source-grounded generation.

## 14.1 Asset knowledge pack contents

For every selected asset, the backend should build an asset knowledge pack containing:

- normalized fact table;
- key source documents;
- chunked evidence passages;
- Weekly News Focus snippets;
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

Because v1 is accountless, chat state should use anonymous sessions with random conversation IDs. The browser should store only `conversation_id`, ticker, `updated_at`, and `expires_at` in local storage. The server may store transcript state for grounded follow-up and user-requested export, with a 7-day TTL from last activity. Users should be able to delete a transcript, which clears local browser state and deletes or invalidates the server session.

Chat transcripts should not be included in product analytics, used for model training, or used for model evaluation in MVP. Product analytics should use aggregate events only, such as chat started, follow-up count, safety redirect, compare redirect, export requested, latency, and error state. IP address and user-agent logs may be retained only in short-lived abuse/security logs with a 7-day default retention.

## 14.3 Chat question classes

Supported classes include:

- definition;
- business model;
- holdings;
- risk;
- comparison;
- Weekly News Focus;
- AI Comprehensive Analysis;
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

- home-page single stock/ETF search;
- autocomplete with support states;
- asset header, Beginner Summary, Top 3 Risks, Key Facts, and Deep Dive;
- source drawer on desktop and source bottom sheet on mobile;
- citation chips;
- contextual glossary cards with desktop popovers and mobile bottom sheets;
- asset-specific chat panel as a helper feature;
- comparison builder and comparison pages;
- Markdown/JSON export controls;
- loading, partial, stale, unavailable, unsupported, and out-of-scope states.

The frontend should call the FastAPI backend only. Browser code should never call LLM providers, OpenRouter, market-data providers, news providers, or source-ingestion services directly.

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
- pgvector for optional semantic retrieval behind an adapter;
- Redis for local cache and job coordination only while the first production deployment remains Postgres-queue based;
- object storage for source snapshots, parsed files, generated artifacts, and Markdown/JSON exports, using local MinIO in Docker Compose and private Google Cloud Storage in production.

## 15.4 Services

The system should include:

- web app;
- API layer;
- LLM provider adapter with deterministic test mocks and environment-configured OpenAI-compatible or OpenRouter-compatible providers;
- ingestion worker;
- retrieval and LLM orchestration service;
- data store.

## 15.5 Provider flexibility

The LLM provider should be abstracted so the product is not locked into one model provider. The implementation should be adapter-first: tests should run with deterministic mocks, while runtime configuration chooses an OpenAI-compatible, OpenRouter-compatible, or other hosted provider.

The system should be able to use:

- OpenRouter-compatible models;
- OpenAI-compatible APIs;
- other hosted models;
- future local or open-source models if needed.

OpenRouter should be a runtime option, not a hard dependency. CI and local tests should keep using deterministic mocks. First deployment may use an explicit OpenRouter fallback chain only when server-side environment variables are present and `LLM_LIVE_GENERATION_ENABLED=true`.

Default live chain:

| Tier | Order | Model |
| --- | ---: | --- |
| Free primary | 1 | `openai/gpt-oss-120b:free` |
| Free fallback | 2 | `google/gemma-4-31b-it:free` |
| Free fallback | 3 | `qwen/qwen3-next-80b-a3b-instruct:free` |
| Free fallback | 4 | `meta-llama/llama-3.3-70b-instruct:free` |
| Paid safety net | 5 | `deepseek/deepseek-v3.2` |

The orchestration flow is free model chain, schema/citation/safety validation, one repair retry, paid DeepSeek fallback, validation again, then cache only validated output. Paid fallback is automatic when live generation is enabled. Raw model reasoning is never stored or shown; the UI may show only a short cited `reasoning_summary`. The system should store selected model, tier, usage, cost, latency, validation result, and attempt count when available.

For the current developer environment, local live-provider keys are expected to live in WSL Bash as `OPENROUTER_API_KEY`, `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FINNHUB_API_KEY`, `TIINGO_API_KEY`, and `EODHD_API_KEY`. The application should consume those variables only in server-side API or worker processes launched from that WSL shell. Key values should never be committed, copied into docs, exposed through `NEXT_PUBLIC_*` variables, returned to the browser, or printed in logs.

Market/reference provider keys are configuration readiness only. FMP, Alpha Vantage, Finnhub, Tiingo, and EODHD remain optional enrichment providers subject to licensing, rate-limit, display, and export-rights review before their data can appear in public product output.

## 15.6 Free-tier deployment target

The first deployment should be optimized for a personal side project with a small number of users and minimal fixed cost.

Recommended deployment target:

- frontend: Vercel Hobby, rooted at `apps/web`;
- API: Google Cloud Run in `us-central1`, request-based billing, `min-instances=0`, and conservative max instances;
- jobs: Cloud Run Jobs, triggered manually first, with Cloud Scheduler added later only if recurring ingestion is needed;
- database: Neon Free Postgres, using the pooled connection URL with SSL;
- storage: private Google Cloud Storage bucket in `us-central1`;
- queue: no production Redis, Pub/Sub, or paid queue at first; use the Postgres `ingestion_jobs` table;
- monitoring: Google Cloud Logging and Error Reporting, with optional Sentry Developer plan later;
- LLM: OpenRouter is server-side and environment-configured only; first deployment may use the explicit free-model chain plus automatic `deepseek/deepseek-v3.2` paid fallback behind `LLM_LIVE_GENERATION_ENABLED=true`, while mock remains the default for CI and local tests.

This deployment target is an operational constraint, not a product downgrade. The app must still keep stable facts, Weekly News Focus, and AI Comprehensive Analysis separate; preserve citations and uncertainty states; and avoid investment advice.

---

## 16. Suggested Internal APIs

```text
GET  /api/search?q=VOO
GET  /api/assets/{ticker}/overview
GET  /api/assets/{ticker}/details
GET  /api/assets/{ticker}/sources
GET  /api/citations/{citation_id}
GET  /api/assets/{ticker}/weekly-news
POST /api/compare
POST /api/assets/{ticker}/chat
GET  /api/assets/{ticker}/export?format=markdown|json
GET  /api/compare/export?left=VOO&right=QQQ&format=markdown|json
POST /api/admin/ingest/{ticker}
GET  /api/jobs/{job_id}
```

## 16.1 Search

```text
GET /api/search?q=VOO
```

Purpose:

- resolve ticker or name;
- return supported, unsupported, out-of-scope, pending, partial, stale, unavailable, or unknown asset states;
- identify asset type;
- route user to correct page.
- support partial ticker/name and issuer/provider search where useful.

## 16.2 Asset overview

```text
GET /api/assets/{ticker}/overview
```

Purpose:

- return Beginner section asset summary;
- show snapshot;
- show top risks;
- show Weekly News Focus and AI Comprehensive Analysis;
- include citations, section freshness, and per-section evidence state for partial pages.

## 16.3 Asset details

```text
GET /api/assets/{ticker}/details
```

Purpose:

- return Deep-Dive section content;
- include financial metrics or ETF exposure details;
- include source-backed nuance.

## 16.4 Sources

```text
GET /api/assets/{ticker}/sources
```

Purpose:

- return source list;
- include source type, title, URL, date, retrieved timestamp, and citation mapping.

## 16.5 Weekly News Focus and AI Comprehensive Analysis

```text
GET /api/assets/{ticker}/weekly-news
```

Purpose:

- return Weekly News Focus and AI Comprehensive Analysis;
- include the market-week window, current week-to-date bucket, source-use rights, citations, freshness, and uncertainty labels;
- keep Weekly News Focus and AI Comprehensive Analysis separate from canonical facts.

## 16.6 Compare

```text
POST /api/compare
```

Purpose:

- compare two assets;
- return side-by-side differences;
- include bottom line for beginners;
- include citations.

## 16.7 Asset chat

```text
POST /api/assets/{ticker}/chat
```

Purpose:

- answer asset-specific user questions;
- retrieve from the asset knowledge pack;
- return cited plain-English responses;
- redirect comparison-style questions with a second ticker to the compare workflow instead of generating a multi-asset answer inside single-asset chat.

## 16.8 Ingestion job

```text
POST /api/admin/ingest/{ticker}
GET  /api/jobs/{job_id}
```

Purpose:

- start asset ingestion or refresh;
- track job status.

Export endpoints should support Markdown and JSON only for v1. PDF export should remain post-MVP until licensing, rendering, and attribution behavior are reviewed.

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
- `checksum`;
- `source_use_policy`;
- `is_official`;
- `allowlist_status`;
- `approval_status`;
- `storage_rights`;
- `export_rights`;
- `approval_rationale`;
- `parser_status`;
- `freshness_state`.

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
- `confidence`;
- `valid_from`;
- `valid_to`;
- `source_version`;
- `source_accession_number`;
- `schema_version`;
- `is_current`;
- `superseded_by_fact_id`.

## 17.5 `recent_events`

Stores timely context separately from canonical facts.

Fields:

- `id`;
- `asset_id`;
- `event_type`;
- `summary`;
- `event_date`;
- `news_window_start`;
- `news_window_end`;
- `period_bucket`;
- `source_document_id`;
- `importance_score`;
- `source_use_policy`.

## 17.6 `summaries`

Stores generated outputs.

Fields:

- `id`;
- `asset_id`;
- `summary_type`;
- `output_json`;
- `model_name`;
- `freshness_hash`;
- `schema_version`;
- `language`;
- `section_key`;
- `generation_status`;
- `validation_error_json`;
- `superseded_at`.

## 17.7 Additional useful tables

As the product matures, it may also need:

- `holdings` for ETF holdings;
- `exposures` for sector, country, industry, or asset-class exposure;
- `financial_metrics` for normalized stock metrics;
- `claims` for generated claim text;
- `claim_citations` for many-to-many claim-to-evidence mapping;
- `chat_sessions` and `chat_messages` for anonymous accountless chat state with 7-day TTL;
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
| Price and reference data   | Free-source or configured-adapter TTL             |
| Weekly News Focus events   | Official-source checks plus allowlisted-source TTL |
| LLM summaries              | Invalidate when underlying fact hashes change     |

## 18.2 SEC data handling

SEC data should be fetched server-side, rate-limited, and cached aggressively rather than fetched on every user page load.

## 18.3 Summary invalidation

Generated summaries should be invalidated when:

- source document checksum changes;
- facts change;
- holdings change;
- Weekly News Focus events change;
- prompt version changes;
- model version changes;
- citation validation fails.

## 18.4 User-facing freshness states

The UI should show states such as:

- fresh;
- partial;
- stale;
- unknown;
- unavailable;
- out of scope;
- mixed evidence.

Quote and reference fields should be labeled as delayed, best-effort, stale, partial, or unavailable. The MVP should not imply real-time quote coverage, and missing quote data should not block the educational page when stable source-backed facts are available.

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

- public `citation_id`;
- source title;
- source type;
- official-source badge where applicable;
- publisher;
- published date;
- retrieved timestamp;
- URL;
- related claims;
- source-use policy;
- supporting excerpt or evidence passage where available.

On desktop, source details should open as a right-side drawer. On mobile, they should open as a bottom sheet.

The public `citation_id` should be opaque, such as `cit_...`, and should never expose raw database row IDs. Resolving a citation should return only approved source metadata and allowed excerpts: title, publisher, URL, source type, official-source status, source-use policy, published/as-of/retrieved dates, freshness state, normalized fact references where relevant, and claim role. It should never expose unrestricted provider payloads, full restricted article text, private raw PDF text, secrets, hidden prompts, raw model reasoning, or unrestricted raw source text.

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
- Weekly News Focus checked date;
- source retrieval timestamp.

## 19.5 Separate Weekly News Focus label

Weekly News Focus and AI Comprehensive Analysis should be visually separate from asset basics.

This prevents the user from confusing short-term news or AI synthesis with the asset's core structure or business model.

## 19.6 Contextual glossary cards

Glossary cards should help users understand important terms without leaving the page or jumping to a separate glossary section.

Cards should be attached to inline terms where they appear in the page, comparison, or chat answer. Examples include P/E in valuation context, AUM and expense ratio in ETF cost or snapshot context, and tracking error in fund-construction context. A page may fetch glossary context once, but the user-facing interaction should happen from each term's location rather than from an aggregated "glossary for this page" block.

Each card should include:

- simple definition;
- why it matters;
- common beginner mistake;
- related terms;
- optional asset-specific context when grounded and cited;
- optional deeper link.

On desktop, glossary cards should support hover preview, click-to-pin, and keyboard focus on the inline term. On mobile, tapping the inline term should open a bottom sheet. Glossary should not compete with search or comparison as a primary home-page workflow in MVP, and MVP asset pages should not rely on a single standalone glossary section as the primary way to explain terms.

## 19.7 Unknown and mixed-evidence states

Where evidence is missing, stale, conflicting, or incomplete, the product should say so clearly.

Examples:

- "We could not verify this from an official source."
- "Holdings data may be stale."
- "Weekly News Focus evidence is mixed."
- "No high-signal Weekly News Focus items found."
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
- distinguish stable facts from Weekly News Focus and AI Comprehensive Analysis;
- cite important claims;
- say "unknown" when evidence is missing;
- warn clearly when an ETF is unusually narrow or complex;
- redirect personalized advice questions into educational explanations;
- include prompt-injection defenses that treat retrieved source text as untrusted evidence;
- ignore instructions found inside retrieved documents;
- never let retrieved chunks override system or developer prompts;
- run citation validation after generation;
- block advice-like output even if a source contains promotional language;
- sanitize HTML and PDF content before rendering;
- use allowlisted domains or controlled URL resolution for ingestion fetchers to reduce SSRF risk.

## 20.3 Example safety pattern

If a user asks:

> Should I buy QQQ?

The product should not answer:

> Yes, buy QQQ.

A safer answer would be:

> I can't tell you whether to buy it. I can help you understand what QQQ is, what it holds, how concentrated it is, how it differs from a broader ETF like VOO, and what risks a beginner should understand before making their own decision.

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
| Understanding of "what this is"       | Whether the user understands the asset basics |
| Understanding of "why people use it"  | Whether the user understands common use cases without treating them as recommendations |
| Understanding of "main risks"         | Whether the user can name the main source-backed risks |
| Trust in citations and source display  | Whether citations increased confidence        |

## 21.3 Trust-oriented product goal

A good session is not necessarily one where a user trades. A good session is one where the user better understands the asset, the risks, the sources, and the tradeoffs.

---

## 22. Phased Roadmap

These phases describe internal implementation order. They do not redefine MVP readiness: v1 requires search, asset pages, comparison, limited grounded chat beta, exports, freshness, citations, glossary, and on-demand ingestion states.

The PRD priority semantics govern readiness: `P0` is a launch blocker for MVP/v1, `P1` is MVP-desired or beta-quality work that can ship after launch unless promoted, and `P2` is post-MVP. Any item required by the MVP acceptance checklist should be treated as `P0`.

## 22.1 Phase 1: Core asset pages

Phase 1 should include:

- search;
- stock page;
- ETF page;
- source drawer;
- glossary;
- basic Weekly News Focus and AI Comprehensive Analysis block;
- beginner section;
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
- richer Weekly News Focus retrieval.

## 22.4 Phase 4: Learning and retention workflows

Phase 4 should include:

- export/download flows for Markdown and JSON;
- cache and freshness-hash invalidation;
- pre-cache orchestration for the launch universe;
- learning paths;
- beginner lessons tied to asset pages;
- broader research workflows.

---

## 23. Final Thesis

The strongest version of this side project is not "AI for stock picking."
It is:

> **A source-first financial learning product for beginners, with single-asset learning, connected comparison workflows, stable facts, Weekly News Focus context, and grounded chat in one place.**

Its real differentiation is the combination of:

- beginner language;
- official-source grounding;
- visible citations;
- comparison-capable design;
- separate Weekly News Focus and AI Comprehensive Analysis layer;
- asset-specific tutor-style chat.

That combination makes the project more useful, more trustworthy, and more realistic to build.

The product should help users understand what they are looking at before they make their own decisions.

---

## 24. References

[1]: https://www.sec.gov/investor/pubs/sec-guide-to-mutual-funds.pdf "Mutual Funds and ETFs"
[2]: https://www.sec.gov/about/divisions-offices/division-investment-management/accounting-disclosure-information/adi-2025-15-website-posting-requirements "SEC.gov | ADI 2025-15 - Website posting requirements"
[3]: https://www.sec.gov/search-filings/edgar-application-programming-interfaces "SEC.gov | EDGAR Application Programming Interfaces (APIs)"
[4]: https://www.ishares.com/us/products/239707/ishares-russell-1000-etf "iShares Russell 1000 ETF"
[5]: https://www.ishares.com/us/products/239707/ishares-russell-1000-etf/?dataType=fund&fileName=IWB_holdings&fileType=csv "iShares IWB holdings CSV"
[6]: https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy "State Street SPDR S&P 500 ETF Trust"
[7]: https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf "iShares Core S&P 500 ETF"
[8]: https://institutional.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/fact-sheet/F0968.pdf "Vanguard S&P 500 ETF fact sheet"
[9]: https://www.sec.gov/file/company-tickers-exchange "SEC Company Tickers Exchange"
[10]: https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs "Nasdaq Trader Symbol Directory Definitions"
