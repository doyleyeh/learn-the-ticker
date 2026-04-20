# Proposal: Citation-First Beginner U.S. Stock & ETF Research Assistant

## 1. Executive Summary

This project is a web-based educational research assistant for beginner investors who want to understand U.S. stocks and ETFs in plain English before making any decision. A user can search a ticker such as VOO, QQQ, or AAPL and see what it is, what it does or holds, its main risks, how it compares with similar choices, and which sources support each important claim.

The product should use official and structured sources as the truth backbone, then use the language model to explain those facts in simple language.

**Core promise:**

> “Help beginners understand what they are looking at, using cited sources and easy words.”

Not:

> “Tell beginners exactly what to buy.”

---

## 2. Problem Statement

Beginner investors face three key issues:

1. Tools assume prior knowledge and lack plain-English explanations  
2. Poor comparison understanding between assets (VOO vs SPY, etc.)  
3. AI responses may be ungrounded and overly confident  

The system must separate:

- **Source-backed facts**
- **Model-generated explanations**

---

## 3. Product Vision

Build a trustworthy beginner-first stock and ETF explainer.

Users should quickly understand:

- What is this asset?
- What does it do?
- Why do people consider it?
- What are the risks?
- How does it compare?
- What changed recently?

The product should feel like **a patient teacher with receipts**.

---

## 4. Product Positioning

**Positioned as:**
- Beginner-friendly learning assistant
- Source-grounded explainer

**Not:**
- Stock picker
- Trading bot
- Financial advisor

---

## 5. Product Principles

1. Source-first
2. Plain English
3. Comparison-first learning
4. Separate stable facts vs recent developments
5. Visible citations
6. Grounded chat
7. Education over advice

---

## 6. Target Users

### Beginner ETF Learner
Understands names (VOO, SPY) but not structure or risks.

### Beginner Stock Learner
Knows companies but not financial analysis.

### Self-Directed Learner
Wants explanations, not trading signals.

---

## 7. Scope (v1)

### In Scope
- U.S. stocks
- Plain ETFs
- Search & explain
- Compare assets
- Recent developments
- Grounded chat
- Glossary
- Citations

### Out of Scope
- Options
- Crypto
- Portfolio optimization
- Personalized advice

---

## 8. Core Product Experience

### 8.1 Search

User inputs ticker → system resolves:
- Name
- Type
- Exchange
- Identifiers

---

### 8.2 Asset Page

#### Beginner Mode
- What it is
- Why people consider it
- Top 3 risks
- Alternatives
- Recent developments

#### Deep Dive Mode
- Financials
- Breakdown
- Sources

---

### 8.3 Comparison Page

Examples:
- VOO vs SPY
- QQQ vs VGT

Ends with:

> **Bottom line for beginners**

---

### 8.4 Recent Developments

Separate section:
- Earnings
- M&A
- Fee changes
- News

**Important:** Context only, not core definition.

---

### 8.5 Grounded Chat

“Ask about this asset”

Answers must include:
- Direct answer
- Why it matters
- Citations
- Uncertainty

---

## 9. Content Model

### 9.1 Stock Page

- Snapshot
- Beginner summary
- Business overview
- Strengths
- Financial quality
- Risks
- Valuation
- Suitability

---

### 9.2 ETF Page

- Snapshot
- Beginner summary
- Holdings
- Construction
- Costs
- Risks
- Comparison
- Suitability

---

## 10. Knowledge Architecture

### Layer 1: Canonical Facts
Stable, source-backed

### Layer 2: Timely Context
News & updates

### Layer 3: Teaching Layer
LLM explanations

---

## 11. Source Hierarchy

### Stocks
1. SEC filings
2. IR pages
3. Earnings reports
4. Market data
5. News

### ETFs
1. Issuer site
2. Fact sheet
3. Prospectus
4. Reports
5. Market data
6. News

---

## 12. Pipeline

1. Resolve entity  
2. Retrieve facts  
3. Ingest documents  
4. Chunk + index  
5. Extract data  
6. Add news  
7. Build knowledge pack  
8. Generate summaries  
9. Add citations  
10. Cache  

---

## 13. Asset Knowledge Pack

Contains:
- Facts
- Documents
- Chunks
- News
- Glossary

Chat answers ONLY from this pack.

---

## 14. Technical Architecture

### Frontend
- Next.js
- TypeScript
- Tailwind

### Backend
- FastAPI
- Python

### Data Layer
- PostgreSQL
- pgvector
- Redis

---

## 15. APIs

GET  /search?q=VOO  
GET  /assets/{ticker}/overview  
POST /assets/{ticker}/chat  
POST /compare  

---

## 16. Data Model

Tables:
- assets
- source_documents
- document_chunks
- facts
- recent_events
- summaries

---

## 17. Freshness

Show:
- Last updated
- Source dates

Use caching + scheduled refresh.

---

## 18. UX Trust Features

- Citation chips
- Source badges
- Freshness labels
- Glossary cards

---

## 19. Safety

- No buy/sell advice
- No personalization
- Must cite sources
- Show uncertainty

---

## 20. Metrics

### Product
- Citation rate
- Completion rate
- Chat engagement

### Learning
- User understanding
- Risk awareness
- Trust level

---

## 21. Roadmap

### Phase 1
Core pages + glossary

### Phase 2
Comparison + risk improvements

### Phase 3
Grounded chat

### Phase 4
Learning paths

---

## 22. Final Thesis

> A source-first financial learning product for beginners.

Differentiation:
- Plain language
- Source grounding
- Visible citations
- Comparison-first
- Grounded chat
