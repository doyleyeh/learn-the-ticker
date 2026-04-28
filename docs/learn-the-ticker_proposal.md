# Learn the Ticker: Citation-First Beginner U.S. Stock & ETF Research Assistant

**Document type:** Detailed product proposal  
**Version:** v0.7 product decision refresh
**Last updated:** 2026-04-28
**Project stage:** Side-project MVP / v1 planning
**Documentation role:** Narrative product vision and product-thesis document. The PRD is the product source of truth, the technical design spec is the implementation source of truth, and the implementation plan plus handoff docs own execution details.

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

ETF support is also a runtime coverage decision, not a descriptive product phrase. V1 ETF coverage must come from a reviewed supported ETF manifest plus deterministic rules, while broader ETF/ETP recognition may help search identify real but unsupported products.

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

For ETFs such as `VOO`, `QQQ`, and `SOXX`, that means two gates must pass before the product can generate output: the ETF must be in the approved supported ETF manifest, and issuer materials must form the canonical evidence backbone. Issuer evidence includes the official issuer page, fact sheet, prospectus, shareholder reports, holdings files, exposure files, and sponsor announcements.

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

Local validation may use a smaller reviewed test set and the golden assets, but public v1 still requires the full approved top-500 stock manifest, approved supported ETF manifest, fresh-data validation, and deployment smoke. Private testing before public launch is a local operator exercise with limited users in the developer's local environment; it should not add product accounts, login flows, or a private-auth product surface.

### 8.1 In scope

The v1 product should support:

- the top 500 U.S.-listed common stocks first;
- U.S.-listed, active, non-leveraged, non-inverse, passive/index-based equity ETFs with primary U.S. equity exposure and validated issuer source packs;
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

The exact top-500 stock universe should come from a reviewed, versioned manifest, not from a live provider query at request time. The proposal-level product rule is simple: runtime stock coverage is operational metadata, not a recommendation list, and unsupported or not-yet-ingested stocks must render honest blocked, pending, partial, stale, unavailable, or out-of-scope states.

Top-500 coverage remains a hard public-v1 requirement. Golden assets and smaller local test manifests are useful for operator validation, but they are not sufficient for public launch.

The PRD owns the coverage requirement. The technical design spec owns manifest fields, validation, private-GCS behavior, and runtime loading. The implementation plan and `docs/TOP500_MANIFEST_HANDOFF.md` own the monthly candidate, diff, review, and promotion workflow.

### 8.1.2 ETF Supported Universe Definition

The exact supported ETF universe should come from a reviewed, versioned supported ETF manifest. A separate ETF/ETP recognition universe may help search identify real but unsupported exchange-traded products, but recognition is not support.

The proposal-level product rule is that v1 generated ETF experiences are unlocked only for reviewed U.S.-listed, active, non-leveraged, non-inverse, passive/index-based U.S. equity ETFs with validated issuer source packs. Live provider ETF flags, exchange listings, issuer search results, and recognition-only rows may help candidate discovery or blocked search states, but they must not unlock ETF pages, chat, comparison output, Weekly News Focus, AI Comprehensive Analysis, or exports.

The v1 supported ETF manifest should start with the golden ETF set from the PRD:

- Broad ETFs: `VOO`, `SPY`, `VTI`, `IVV`, `QQQ`, `IWM`, `DIA`.
- Sector/theme ETFs: `VGT`, `XLK`, `SOXX`, `SMH`, `XLF`, `XLV`, `XLE`.

The PRD owns the supported ETF product scope. The technical design spec owns ETF support and recognition manifest fields, validators, and runtime authority. `docs/ETF_MANIFEST_HANDOFF.md` owns candidate packet, source-pack, parser-validation, and manual-promotion workflow details.

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

> Search a U.S. stock or supported U.S. equity ETF to see beginner-friendly explanations, source citations, top risks, recent context, and grounded follow-up answers.

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

It should show the configured maximum only when enough high-quality evidence exists. Fewer items are acceptable when the evidence set is limited, and many broad ETFs may legitimately show "No major Weekly News Focus items found for this window." The product should never pad the list with weak, duplicative, promotional, irrelevant, non-reviewed, or rights-disallowed items just to reach a target count.

Weekly News Focus should be official-first while still allowing reputable third-party/news sources to broaden coverage when they pass source governance and relevance checks. The UI must clearly label whether each item is official, issuer/company-provided, or third-party reporting, and source details should show publisher, URL, published date, retrieval date, source type, topic/event classification, and citation link.

Each Weekly News Focus item should include:

- source or publisher;
- headline or title;
- published date;
- one-sentence beginner-friendly summary;
- citation or source drawer link;
- official-vs-third-party source label;
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

AI Comprehensive Analysis should be reviewed with live AI during local testing when the evidence threshold is met. If live generation fails schema, citation, source-use, or safety validation, the generated section should be suppressed or marked unavailable rather than replaced with uncited text.

V1 should be English-first. Traditional Chinese localization can be added later. Read-aloud or text-to-speech controls are not part of the v1 requirement.

## 9.6 Asset-specific grounded chat

After the user opens an asset page, they should see a chat module titled:

> **Ask about this asset**

The purpose is not to create a general market chatbot. The purpose is to let the user ask questions about the selected stock or ETF using a bounded evidence set. Chat is a helper feature: on desktop it can live in a helper rail or side panel, and on mobile it should open from a sticky Ask action as a bottom sheet or full-screen panel.

During local testing, grounded chat should be fully functional with live AI so the operator can review answer quality. For public v1, chat remains beta-limited and asset-specific: it is not a general market chatbot, it must cite important claims, and it should return an honest unavailable or insufficient-evidence state when validation fails.

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

The MVP should assume a free-first evidence strategy: SEC data for stocks, official issuer materials for ETFs, official-first Weekly News Focus sources, reputable third-party/news sources where source governance permits, deterministic mocks, fixtures, and provider adapters only where rights and attribution allow.

The source hierarchy is part of the product's trust model. Stable understanding should come from official and structured sources first. Weekly News Focus should add context, not define the asset. Provider payloads are optional enrichment and must not override official SEC or issuer evidence.

Golden Asset Source Handoff remains the approval layer between retrieval and evidence use. Fetching a filing, issuer page, provider endpoint, PDF, HTML page, or news-like item is retrieval only. A retrieved source should not be stored as evidence, cited, summarized, generated from, or exported unless the handoff policy approves its domain, source type, official-source status, rights, rationale, parser result, freshness/as-of metadata, and review status. For reputable third-party/news sources, metadata and beginner summaries may be used when approved; full article text storage, public display, or export remains rights-gated and should not be assumed by reputation alone.

The proposal-level operating rule is:

> Fetch only from governed sources, store according to source-use policy, generate only from approved evidence, and export only what policy permits.

The PRD owns product-level source requirements and source-use states. The technical design spec owns provider roles, raw-text policy, allowlist behavior, retrieval modes, and source-handoff fields. `docs/SOURCE_HANDOFF.md`, `config/source_allowlist.yaml`, and the implementation plan own execution details and validation expectations.

## 12.1 Stocks

For stocks, the source priority should be:

1. SEC EDGAR, SEC XBRL company facts, and SEC filing documents;
2. company investor relations pages;
3. earnings presentations and transcripts;
4. free or official reference metadata where available;
5. reputable third-party/news sources for Weekly News Focus context when approved and labeled as non-official.

## 12.2 ETFs

For ETFs, the source priority should be:

1. approved supported ETF manifest entry;
2. ETF issuer official page;
3. ETF fact sheet;
4. summary prospectus and full prospectus;
5. shareholder reports;
6. issuer holdings files, exposure files, and official ETF website disclosures;
7. sponsor announcements and reputable third-party/news sources for Weekly News Focus context when approved and labeled as non-official.

## 12.3 Source use by content type

Different content sections should use different source types.

| Content area              | Preferred sources                                     |
| ------------------------- | ----------------------------------------------------- |
| Stock identity            | SEC metadata, free/reference metadata                  |
| Stock business overview   | 10-K, 10-Q, company investor relations                |
| Stock financial trends    | SEC XBRL, approved structured enrichment data         |
| Stock risks               | 10-K and 10-Q risk factors                            |
| Stock Weekly News Focus events | 8-Ks, earnings releases, approved reputable third-party/news sources |
| ETF identity              | issuer page, approved free/reference metadata         |
| ETF holdings              | issuer holdings file, fact sheet                      |
| ETF methodology           | prospectus, index methodology, issuer page            |
| ETF risks                 | prospectus, summary prospectus                        |
| ETF Weekly News Focus events | issuer announcements, sponsor updates, approved reputable third-party/news sources |

---

## 13. Retrieval and Generation Pipeline

This proposal treats the pipeline as a product promise, not an implementation recipe:

1. resolve the asset and support state;
2. retrieve official or governed source material;
3. approve evidence through Golden Asset Source Handoff;
4. extract canonical facts;
5. retrieve timely Weekly News Focus evidence separately;
6. assemble an asset knowledge pack from approved evidence;
7. generate beginner explanations, comparison context, chat answers, and AI Comprehensive Analysis only from that pack;
8. validate citations, safety, freshness, and source-use policy before display or export.

For stocks, the pipeline should prioritize SEC identity, filings, XBRL facts, filing-derived business and risk language, official company materials, and optional rights-reviewed enrichment. For ETFs, it should prioritize the supported ETF manifest, issuer pages, fact sheets, prospectuses, holdings/exposure files, and sponsor announcements.

The detailed pipeline, scoring, repository behavior, worker orchestration, retries, caches, and endpoint contracts belong in the technical design spec and implementation plan. The proposal's durable requirement is that retrieval, evidence approval, canonical facts, timely context, and teaching/generation remain separate all the way to the user interface.

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

The technical architecture should serve the product promise: source-first retrieval, governed evidence approval, citation-first rendering, separated canonical facts and timely context, bounded chat, connected comparison, contextual glossary, and exportable learning outputs.

At the proposal level, the architecture has four durable constraints:

- browser code should call the backend, not LLM providers, market/reference providers, news providers, or ingestion services directly;
- source ingestion and generated output should pass through Golden Asset Source Handoff, citation validation, source-use policy, freshness, and safety checks;
- deterministic mocks and fixtures should remain the default for local development and CI;
- first deployment should stay free-tier oriented unless the user explicitly approves a cost tradeoff.

The PRD owns product requirements such as supported workflows, MVP readiness, and user-facing states. The technical design spec owns stack choices, service boundaries, provider adapters, retrieval mode, data-layer details, LLM runtime configuration, and deployment architecture. The implementation plan and deployment docs own operational sequencing, validation gates, environment templates, and smoke checks.

---

## 16. Suggested Internal APIs

The proposal should describe API intent, not freeze endpoint design. The backend should expose product surfaces for search, asset overview/detail, sources and citations, Weekly News Focus, comparison, asset-bounded chat, ingestion jobs, and Markdown/JSON exports.

The technical design spec owns canonical endpoint names, request and response contracts, compatibility aliases, rate limits, export behavior, and public citation safety. The implementation plan owns migration sequencing, MVP readiness gates, and any temporary compatibility behavior.

---

## 17. Data Model

The proposal-level data model is conceptual:

- assets and identifiers;
- governed source documents and allowed evidence chunks;
- normalized canonical facts;
- separate Weekly News Focus event records;
- generated summaries and citation mappings;
- holdings, exposures, financial metrics, glossary terms, comparison facts, exports, ingestion jobs, and accountless chat sessions where needed.

The important product boundary is separation: canonical facts, timely context, and generated teaching outputs should remain distinguishable in storage, API responses, UI labels, citations, and exports.

The technical design spec owns table shapes, field names, indexes, public IDs, migrations, freshness hashes, source-use policy fields, and persistence details.

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
| Weekly News Focus events   | Official-source checks plus approved reputable third-party/news source TTL |
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

Detailed external-source references, provider constraints, endpoint contracts, manifest fields, and handoff workflows live in the PRD, technical design spec, implementation plan, and specialized handoff docs:

- `docs/learn_the_ticker_PRD.md`
- `docs/learn_the_ticker_technical_design_spec.md`
- `SPEC.md`
- `docs/SOURCE_HANDOFF.md`
- `docs/TOP500_MANIFEST_HANDOFF.md`
- `docs/ETF_MANIFEST_HANDOFF.md`
