# Technical Design Spec: Learn the Ticker — Citation-First Beginner U.S. Stock & ETF Research Assistant

**Document version:** v0.2 control-doc alignment
**Product stage:** MVP / v1 planning  
**Related doc:** PRD v0.2 refined
**Source basis:** Current project proposal, PRD v0.2, and completed fixture-backed MVP slices.

---

## 1. Executive summary

This system is an accountless web app that lets a beginner search a U.S.-listed common stock or plain-vanilla U.S.-listed ETF, then returns a source-grounded educational page with beginner explanations, cited facts, recent developments, comparisons, glossary help, limited asset-specific grounded chat, and exportable learning outputs.

The core technical challenge is not simply generating good prose. The system must reliably separate:

1. **Canonical facts** — stable source-backed asset facts.
2. **Timely context** — recent news, filings, fee changes, earnings, or methodology updates.
3. **Teaching layer** — AI-written plain-English explanation and chat answers.

That three-layer knowledge architecture comes directly from the proposal and remains the backbone of this design. PRD v0.2 adds functional-MVP direction: pre-cache a high-demand launch universe, support on-demand ingestion for eligible assets, keep v1 accountless, expose export/download flows, and use caching plus freshness hashes to control API and LLM cost.

---

## 2. Design goals

### 2.1 Primary goals

| Goal | Design implication |
|---|---|
| Source-first explanations | Store raw source documents, normalized facts, chunks, and citation mappings before generating summaries. |
| Beginner-friendly language | Generate structured summaries using beginner-mode schemas and glossary terms. |
| Visible citations | Every important claim should map to a `source_document`, `document_chunk`, or normalized `fact`. |
| Stable facts separated from recent developments | Maintain separate data tables and UI sections for canonical facts and recent events. |
| Grounded asset-specific chat | Build an `asset_knowledge_pack` per asset and restrict chat retrieval to that pack. |
| Compare-first learning | Support side-by-side comparison using normalized facts and generated beginner summaries. |
| Education over advice | Add query classification, output validation, and safety filters to avoid buy/sell or allocation instructions. |
| Accountless v1 | Store shared cached artifacts and exportable outputs without requiring user accounts. |
| Cost-aware freshness | Use source checksums, TTLs, and freshness hashes to avoid unnecessary provider and LLM calls. |

### 2.2 Non-goals for v1

The system will not support brokerage trading, tax advice, options, crypto, international equities, portfolio optimization, leveraged ETFs, inverse ETFs, ETNs, complex exchange-traded products, user accounts, saved watchlists, saved assets, or personalized position sizing.

---

## 3. Key technical decisions

| Area | Decision | Rationale |
|---|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui | Fits interactive asset pages, source drawers, glossary popovers, and chat panel. |
| Backend | Python + FastAPI | Strong ecosystem for SEC ingestion, parsing, financial data processing, and LLM orchestration. |
| Database | PostgreSQL | Good fit for normalized facts, source metadata, audit logs, freshness state, and relational asset data. |
| Vector search | pgvector as primary retrieval layer | Keeps citations, freshness, asset filters, and chunk metadata under application control. |
| Cache / queues | Redis | Caching, job coordination, rate-limit counters, and short-lived API responses. |
| Object storage | S3-compatible bucket | Stores raw filings, PDF snapshots, HTML snapshots, parsed text, and generated artifacts. |
| LLM access | Provider abstraction | Allows OpenRouter, OpenAI, or another model provider without rewriting the product. |
| Structured generation | JSON-schema outputs where provider supports it | Produces predictable UI-renderable output and supports server-side validation. |
| Retrieval | Self-managed hybrid retrieval first; hosted file search optional | Self-managed retrieval gives stricter control over citation binding and freshness metadata. |
| Source freshness | Section-level freshness hashes | Summaries are invalidated when underlying facts, chunks, or recent events change. |
| Coverage model | Pre-cached high-demand universe plus on-demand ingestion | Improves launch latency while keeping the architecture open to all eligible supported assets. |
| User model | Accountless MVP | Defers identity, saved assets, and watchlists while preserving export/download workflows. |
| Export model | Server-shaped summaries and source lists | Lets users save learning outputs while respecting citation, freshness, and licensing constraints. |

---

## 4. High-level architecture

```text
                   ┌──────────────────────────┐
                   │        Next.js Web        │
                   │ Search, asset pages, chat │
                   └────────────┬─────────────┘
                                │
                                ▼
                   ┌──────────────────────────┐
                   │       FastAPI API         │
                   │ Auth, routing, responses  │
                   └────────────┬─────────────┘
                                │
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                        ▼
┌───────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Asset Service │       │ Compare Service │       │  Chat Service    │
│ overview/data │       │ normalized diff │       │ grounded Q&A     │
└───────┬───────┘       └────────┬────────┘       └────────┬────────┘
        │                        │                         │
        ▼                        ▼                         ▼
┌───────────────────────────────────────────────────────────────────┐
│                         Data Layer                                │
│ PostgreSQL + pgvector | Redis | Object Storage                    │
│ assets, facts, chunks, sources, events, summaries, jobs, metrics  │
└───────────────────────────────────────────────────────────────────┘
        ▲                        ▲                         ▲
        │                        │                         │
┌───────┴────────┐      ┌────────┴─────────┐      ┌────────┴─────────┐
│ Ingestion Jobs │      │ Retrieval Service│      │ LLM Orchestrator │
│ SEC, ETF docs, │      │ hybrid search,   │      │ extraction, page │
│ market data,   │      │ reranking, packs │      │ generation, chat │
│ news            │      └──────────────────┘      └──────────────────┘
└────────────────┘
```

---

## 5. Core services

### 5.1 Web app

**Responsibilities**

- Search UI.
- Asset page rendering.
- Beginner Mode / Deep-Dive Mode toggle.
- Citation chips.
- Source drawer.
- Glossary popovers.
- Comparison page.
- Asset-specific chat panel.
- Export/download controls for asset pages, comparisons, sources, and chat transcripts.
- Stale, unknown, and mixed-evidence states.

**Recommended routes**

```text
/                         Home + search
/assets/[ticker]           Asset page
/assets/[ticker]/sources   Source drawer deep link
/compare?left=VOO&right=QQQ
/glossary/[term]           Optional glossary detail page
```

### 5.2 API layer

**Responsibilities**

- Request validation.
- Asset routing.
- Cache lookup.
- Job creation.
- Response shaping.
- Safety checks.
- Rate limiting.
- Supported/unsupported asset classification.
- Export response shaping.
- Auth only if user accounts are added after v1.

**Suggested internal endpoints**

```text
GET  /api/search?q=VOO
GET  /api/assets/{ticker}/overview
GET  /api/assets/{ticker}/details
GET  /api/assets/{ticker}/sources
GET  /api/assets/{ticker}/recent
POST /api/compare
POST /api/assets/{ticker}/chat
GET  /api/assets/{ticker}/export
GET  /api/compare/export?left=VOO&right=QQQ
POST /api/admin/ingest/{ticker}
GET  /api/jobs/{job_id}
```

The proposal already suggests this API surface; this spec formalizes the response contracts, source binding, and pipeline behavior.

### 5.3 Ingestion worker

**Responsibilities**

- Resolve assets.
- Classify supported, unsupported, unknown, and pending states.
- Fetch source documents.
- Store raw source snapshots.
- Parse filings, fact sheets, issuer pages, and holdings files.
- Extract normalized facts.
- Chunk source text.
- Generate embeddings.
- Refresh stale assets.
- Support pre-cache jobs for the launch universe and on-demand jobs for eligible assets outside it.
- Track ingestion job status.

**Recommended queue model**

Use Redis Queue, Celery, Dramatiq, or Arq. For a side-project MVP, Arq or RQ is simpler; for larger scale, Celery gives more mature retry and scheduling behavior.

### 5.4 Retrieval service

**Responsibilities**

- Build asset-specific evidence sets.
- Run hybrid retrieval:
  - keyword search
  - semantic vector search
  - metadata filters
  - source-type boosts
  - recency boosts for recent-development questions
- Return chunks with source metadata.
- Return normalized facts with source IDs.
- Return glossary entries.
- Return computed comparison facts.

### 5.5 LLM orchestration service

**Responsibilities**

- Prompt assembly.
- Schema-constrained extraction.
- Schema-constrained summary generation.
- Asset-specific chat.
- Citation mapping.
- Safety redirection.
- Output validation.
- Retry / repair logic.

The LLM orchestration service should hide provider-specific details behind a small adapter interface. For strict UI-ready outputs, use structured responses where possible; otherwise use JSON-mode prompting plus Pydantic validation and repair.

---

## 6. Data sources

### 6.1 Stock sources

| Source category | Use | Priority |
|---|---|---|
| SEC submissions API | Company identity, filings history, CIK, ticker metadata | P0 |
| SEC XBRL company facts | Financial metrics and multi-year trends | P0 |
| SEC filings: 10-K, 10-Q, 8-K | Business overview, risks, MD&A, recent events | P0 |
| Company investor relations | Earnings releases, presentations, segment explanations | P1 |
| Structured market/reference provider | ticker reference, price, market cap, sector, industry, valuation fields, volume | P0 |
| Reputable ticker-tagged news provider | recent developments only, after official filings and investor-relations sources | P1 |

SEC EDGAR APIs should be used server-side, cached aggressively, and rate-limited. Stock ingestion should never depend on live user-page calls to SEC. PRD v0.2 names Massive, formerly Polygon.io, as the preferred structured market/reference provider direction, with lower-cost alternatives allowed only behind validation and licensing review.

### 6.2 ETF sources

| Source category | Use | Priority |
|---|---|---|
| ETF issuer official page | fund identity, objective, expense ratio, AUM, holdings link | P0 |
| ETF fact sheet | holdings, sector exposure, benchmark, fees | P0 |
| Summary prospectus / full prospectus | risks, methodology, objective, fees | P0 |
| Shareholder reports | official fund reporting context | P1 |
| Holdings CSV / JSON / Excel | top holdings, concentration, country/sector exposure | P0 |
| Structured market/reference provider | quote, AUM, average volume, spread data, ETF reference metadata | P0 |
| Sponsor press releases / reputable news | fee cuts, methodology changes, mergers, liquidations | P1 |

ETF issuer websites are especially important because ETF disclosure includes investor-facing items such as holdings, premium/discount information, and bid-ask spread disclosures. PRD v0.2 prefers official issuer data plus Massive and ETF Global where budget allows; lower-cost ETF data fallbacks must be validated against issuer sources.

---

## 7. Source hierarchy

The system should rank evidence using the hierarchy from the proposal. Stable facts should come from official or structured sources first; news should add recent context but should not redefine the asset.

### 7.1 Stock source ranking

1. SEC filings and XBRL data.
2. Company investor relations pages.
3. Earnings releases and presentations.
4. Structured market/reference data provider.
5. Reputable ticker-tagged news, used only for recent-development context.

### 7.2 ETF source ranking

1. ETF issuer official page.
2. ETF fact sheet.
3. Summary prospectus and full prospectus.
4. Shareholder reports.
5. Structured market/reference data provider.
6. Reputable ticker-tagged news, used only for recent-development context.

---

## 8. Data model

### 8.1 Core tables

#### `assets`

Stores canonical asset identity.

```sql
assets (
  id UUID PRIMARY KEY,
  ticker TEXT NOT NULL,
  name TEXT NOT NULL,
  asset_type TEXT NOT NULL, -- stock | etf
  exchange TEXT,
  cik TEXT,
  provider TEXT,
  issuer TEXT,
  status TEXT NOT NULL, -- supported | unsupported | unknown | pending | stale
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
```

#### `asset_identifiers`

Stores alternate identifiers.

```sql
asset_identifiers (
  id UUID PRIMARY KEY,
  asset_id UUID REFERENCES assets(id),
  id_type TEXT NOT NULL, -- cik | figi | isin | cusip | provider_id
  id_value TEXT NOT NULL,
  source TEXT,
  created_at TIMESTAMPTZ
)
```

#### `source_documents`

Stores official documents, issuer pages, filings, fact sheets, news articles, and snapshots.

```sql
source_documents (
  id UUID PRIMARY KEY,
  asset_id UUID REFERENCES assets(id),
  source_type TEXT NOT NULL,
  source_rank INT NOT NULL,
  title TEXT,
  url TEXT,
  publisher TEXT,
  published_at TIMESTAMPTZ,
  retrieved_at TIMESTAMPTZ NOT NULL,
  content_type TEXT, -- html | pdf | json | csv | xlsx | text
  storage_uri TEXT,
  checksum TEXT,
  parser_version TEXT,
  is_official BOOLEAN DEFAULT FALSE,
  freshness_state TEXT, -- fresh | stale | unknown | unavailable
  created_at TIMESTAMPTZ
)
```

#### `document_chunks`

Stores retrievable text chunks with embedding vectors.

```sql
document_chunks (
  id UUID PRIMARY KEY,
  source_document_id UUID REFERENCES source_documents(id),
  asset_id UUID REFERENCES assets(id),
  section_name TEXT,
  chunk_order INT,
  text TEXT NOT NULL,
  token_count INT,
  embedding VECTOR,
  char_start INT,
  char_end INT,
  created_at TIMESTAMPTZ
)
```

#### `facts`

Stores normalized facts used to render the page and feed generation.

```sql
facts (
  id UUID PRIMARY KEY,
  asset_id UUID REFERENCES assets(id),
  fact_type TEXT NOT NULL,
  field_name TEXT NOT NULL,
  value_json JSONB NOT NULL,
  unit TEXT,
  period TEXT,
  as_of_date DATE,
  source_document_id UUID REFERENCES source_documents(id),
  source_chunk_id UUID REFERENCES document_chunks(id),
  extraction_method TEXT, -- api | parser | llm | manual
  confidence NUMERIC,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
```

#### `holdings`

ETF-specific holdings table.

```sql
holdings (
  id UUID PRIMARY KEY,
  etf_asset_id UUID REFERENCES assets(id),
  holding_name TEXT NOT NULL,
  holding_ticker TEXT,
  holding_asset_id UUID REFERENCES assets(id),
  weight_percent NUMERIC,
  shares NUMERIC,
  market_value NUMERIC,
  as_of_date DATE,
  source_document_id UUID REFERENCES source_documents(id),
  created_at TIMESTAMPTZ
)
```

#### `exposures`

ETF sector, country, asset-class, or industry exposures.

```sql
exposures (
  id UUID PRIMARY KEY,
  asset_id UUID REFERENCES assets(id),
  exposure_type TEXT NOT NULL, -- sector | country | asset_class | industry
  label TEXT NOT NULL,
  weight_percent NUMERIC,
  as_of_date DATE,
  source_document_id UUID REFERENCES source_documents(id),
  created_at TIMESTAMPTZ
)
```

#### `financial_metrics`

Stock financial metric table.

```sql
financial_metrics (
  id UUID PRIMARY KEY,
  asset_id UUID REFERENCES assets(id),
  metric_name TEXT NOT NULL,
  value NUMERIC,
  unit TEXT,
  fiscal_period TEXT,
  fiscal_year INT,
  period_end DATE,
  source_document_id UUID REFERENCES source_documents(id),
  created_at TIMESTAMPTZ
)
```

#### `recent_events`

Stores recent developments separately from canonical facts.

```sql
recent_events (
  id UUID PRIMARY KEY,
  asset_id UUID REFERENCES assets(id),
  event_type TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  event_date DATE,
  source_document_id UUID REFERENCES source_documents(id),
  importance_score NUMERIC,
  freshness_state TEXT,
  created_at TIMESTAMPTZ
)
```

#### `summaries`

Stores generated page sections.

```sql
summaries (
  id UUID PRIMARY KEY,
  asset_id UUID REFERENCES assets(id),
  summary_type TEXT NOT NULL, -- beginner | deep_dive | risks | recent | suitability
  output_json JSONB NOT NULL,
  model_provider TEXT,
  model_name TEXT,
  prompt_version TEXT,
  freshness_hash TEXT NOT NULL,
  validation_status TEXT,
  created_at TIMESTAMPTZ
)
```

#### `claims`

Stores generated claims and citation mappings.

```sql
claims (
  id UUID PRIMARY KEY,
  summary_id UUID REFERENCES summaries(id),
  asset_id UUID REFERENCES assets(id),
  claim_text TEXT NOT NULL,
  claim_type TEXT, -- fact | interpretation | risk | recent | comparison
  source_document_id UUID REFERENCES source_documents(id),
  source_chunk_id UUID REFERENCES document_chunks(id),
  fact_id UUID REFERENCES facts(id),
  citation_required BOOLEAN DEFAULT TRUE,
  citation_status TEXT, -- valid | missing | weak | unsupported
  created_at TIMESTAMPTZ
)
```

#### `glossary_terms`

```sql
glossary_terms (
  id UUID PRIMARY KEY,
  term TEXT NOT NULL,
  simple_definition TEXT NOT NULL,
  why_it_matters TEXT,
  beginner_mistake TEXT,
  related_terms TEXT[],
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
```

#### `ingestion_jobs`

```sql
ingestion_jobs (
  id UUID PRIMARY KEY,
  asset_id UUID REFERENCES assets(id),
  job_type TEXT NOT NULL, -- pre_cache | on_demand | refresh | repair
  status TEXT NOT NULL, -- queued | running | succeeded | failed | cancelled
  priority INT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  error_json JSONB,
  created_at TIMESTAMPTZ
)
```

---

## 9. Ingestion pipeline

### 9.1 Universal ingestion flow

```text
1. Resolve asset
2. Classify asset as supported, unsupported, unknown, pending, or stale
3. Fetch source documents for supported assets
4. Save raw snapshots
5. Parse source documents
6. Chunk parsed text
7. Generate embeddings
8. Extract normalized facts
9. Retrieve high-signal recent developments
10. Build or refresh asset knowledge pack
11. Generate or invalidate summaries
12. Validate citations
13. Mark freshness state
14. Update shared cache entries and freshness hashes
```

MVP should support both pre-cache ingestion for the launch universe and on-demand ingestion for eligible assets outside that universe. Unsupported assets should return a recognized-but-unsupported state from search and must not trigger generated pages, generated chat, or generated comparisons.

### 9.2 Stock ingestion flow

#### Step 1: Resolve ticker

Input:

```json
{
  "query": "AAPL"
}
```

Output:

```json
{
  "ticker": "AAPL",
  "name": "Apple Inc.",
  "asset_type": "stock",
  "cik": "0000320193",
  "exchange": "NASDAQ"
}
```

Resolution should use a market/reference provider plus SEC metadata where available.

#### Step 2: Fetch SEC data

Fetch:

- submissions history
- latest 10-K
- latest 10-Q
- recent 8-Ks
- company facts / XBRL

#### Step 3: Parse filings

Extract:

- business overview
- products and services
- risk factors
- MD&A
- segment information
- financial statements
- footnotes where relevant

#### Step 4: Normalize financials

Normalize into `financial_metrics`:

- revenue
- gross profit
- operating income
- net income
- diluted EPS
- operating cash flow
- capital expenditures
- free cash flow
- cash
- debt
- gross margin
- operating margin
- ROE or ROIC where available

#### Step 5: Generate stock summaries

Generate:

- beginner summary
- business overview
- top 3 risks
- strengths summary
- financial quality summary
- valuation context
- recent developments
- suitability summary

All generated sections must include citation mappings or uncertainty notes.

### 9.3 ETF ingestion flow

#### Step 1: Resolve ETF

Input:

```json
{
  "query": "VOO"
}
```

Output:

```json
{
  "ticker": "VOO",
  "name": "Vanguard S&P 500 ETF",
  "asset_type": "etf",
  "issuer": "Vanguard",
  "category": "Large Blend"
}
```

#### Step 2: Fetch official ETF sources

Fetch:

- issuer page
- fact sheet
- summary prospectus
- full prospectus
- shareholder reports when relevant
- holdings file
- sector / country exposure file

#### Step 3: Normalize ETF facts

Normalize into `facts`, `holdings`, and `exposures`:

- benchmark
- expense ratio
- AUM
- holdings count
- top 10 holdings
- top 10 concentration
- sector exposure
- country exposure
- passive / active classification
- weighting method
- rebalancing frequency
- bid-ask spread
- premium / discount information

#### Step 4: ETF risk extraction

Extract and classify:

- market risk
- concentration risk
- tracking risk
- liquidity risk
- trading-cost risk
- interest-rate risk
- credit risk
- currency risk
- complexity risk

#### Step 5: Generate ETF summaries

Generate:

- what the ETF is trying to do
- why beginners consider it
- main catch or beginner misunderstanding
- broad vs narrow exposure
- top 3 risks
- simpler alternatives
- recent developments
- suitability summary

### 9.4 Recent developments ingestion

Recent developments should never overwrite canonical facts. They are stored in `recent_events`.

#### Stock event types

```text
earnings
guidance
product_announcement
merger_acquisition
leadership_change
regulatory_event
legal_event
capital_allocation
other
```

#### ETF event types

```text
fee_change
methodology_change
index_change
fund_merger
fund_liquidation
sponsor_update
large_flow_event
other
```

#### Importance scoring

A simple MVP scoring formula:

```text
importance_score =
  source_quality_weight
+ event_type_weight
+ recency_weight
+ asset_relevance_weight
- duplicate_penalty
```

Only events above a configured threshold should appear on the asset page.

---

## 10. Asset knowledge pack

The `asset_knowledge_pack` is the bounded evidence set used for page generation and chat.

### 10.1 Pack contents

```json
{
  "asset": {
    "ticker": "QQQ",
    "name": "Invesco QQQ Trust",
    "asset_type": "etf"
  },
  "canonical_facts": [],
  "financial_metrics": [],
  "holdings": [],
  "exposures": [],
  "risk_chunks": [],
  "recent_events": [],
  "source_documents": [],
  "glossary_terms": [],
  "freshness": {}
}
```

### 10.2 Retrieval rules

The retrieval service must:

- filter by `asset_id`
- boost official sources
- boost exact ticker/name matches
- retrieve from both `facts` and `document_chunks`
- include source metadata with every retrieved item
- avoid stale sources unless clearly labeled
- include recent events only when the question asks about recent context or the page section is “Recent developments”

### 10.3 Comparison knowledge pack

For comparison pages, build a merged pack:

```json
{
  "left_asset_pack": {},
  "right_asset_pack": {},
  "computed_differences": {},
  "overlap_metrics": {},
  "comparison_sources": []
}
```

For ETF-to-ETF comparisons, compute:

- benchmark difference
- expense ratio difference
- holdings overlap
- top-holding overlap
- sector difference
- concentration difference
- broad vs narrow classification

For stock-to-stock comparisons, compute:

- business model difference
- sector / industry difference
- financial trend difference
- valuation context difference
- risk overlap
- recent-development difference

---

## 11. Generation design

### 11.1 Generation stages

```text
Stage A: Fact extraction
Stage B: Fact validation
Stage C: Page section generation
Stage D: Claim-to-citation binding
Stage E: Safety validation
Stage F: Persist summary
```

### 11.2 LLM provider abstraction

```python
class LLMClient:
    def generate_structured(
        self,
        *,
        task_name: str,
        system_prompt: str,
        user_payload: dict,
        output_schema: dict,
        temperature: float,
        metadata: dict
    ) -> dict:
        ...
```

The provider adapter should support:

- OpenAI Responses API.
- OpenRouter-compatible chat-completion APIs.
- Local or open-source models later.
- Retry and validation.
- Prompt versioning.
- Model fallback.

When a provider supports strict JSON-schema output, use it. When it does not, prompt for JSON and validate with Pydantic server-side.

### 11.3 Page summary schema

Example simplified schema:

```json
{
  "type": "object",
  "required": [
    "beginner_summary",
    "top_risks",
    "recent_developments",
    "suitability_summary",
    "claims"
  ],
  "properties": {
    "beginner_summary": {
      "type": "object",
      "required": ["what_it_is", "why_people_consider_it", "main_catch"],
      "properties": {
        "what_it_is": {"type": "string"},
        "why_people_consider_it": {"type": "string"},
        "main_catch": {"type": "string"}
      }
    },
    "top_risks": {
      "type": "array",
      "minItems": 3,
      "maxItems": 3,
      "items": {
        "type": "object",
        "required": ["title", "plain_english_explanation", "citation_ids"],
        "properties": {
          "title": {"type": "string"},
          "plain_english_explanation": {"type": "string"},
          "citation_ids": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "recent_developments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "summary", "event_date", "citation_ids"],
        "properties": {
          "title": {"type": "string"},
          "summary": {"type": "string"},
          "event_date": {"type": "string"},
          "citation_ids": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "suitability_summary": {
      "type": "object",
      "required": ["may_fit", "may_not_fit", "learn_next"],
      "properties": {
        "may_fit": {"type": "string"},
        "may_not_fit": {"type": "string"},
        "learn_next": {"type": "string"}
      }
    },
    "claims": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["claim_id", "claim_text", "citation_ids"],
        "properties": {
          "claim_id": {"type": "string"},
          "claim_text": {"type": "string"},
          "citation_ids": {"type": "array", "items": {"type": "string"}}
        }
      }
    }
  }
}
```

### 11.4 Chat answer schema

```json
{
  "type": "object",
  "required": [
    "direct_answer",
    "why_it_matters",
    "citations",
    "uncertainty",
    "safety_classification"
  ],
  "properties": {
    "direct_answer": {"type": "string"},
    "why_it_matters": {"type": "string"},
    "citations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["claim", "source_document_id", "chunk_id"],
        "properties": {
          "claim": {"type": "string"},
          "source_document_id": {"type": "string"},
          "chunk_id": {"type": "string"}
        }
      }
    },
    "uncertainty": {
      "type": "array",
      "items": {"type": "string"}
    },
    "safety_classification": {
      "type": "string",
      "enum": [
        "educational",
        "personalized_advice_redirect",
        "unsupported_asset_redirect",
        "insufficient_evidence"
      ]
    }
  }
}
```

---

## 12. Citation binding

Citation binding is the most important trust mechanism.

### 12.1 Citation lifecycle

```text
1. Source document is fetched.
2. Source document is parsed.
3. Source text is chunked.
4. Normalized facts are linked to source document and chunk IDs.
5. LLM receives facts/chunks with stable IDs.
6. LLM generates claims with citation IDs.
7. Validator checks every citation ID.
8. UI renders citation chips.
9. Source drawer opens exact source metadata and supporting passage.
```

### 12.2 Citation validation rules

A generated output is valid only if:

- every important factual claim has at least one citation
- every citation ID exists
- cited source belongs to the same asset or comparison pack
- cited source is not stale unless labeled stale
- numeric claims match the cited fact value
- quoted or paraphrased claims are supported by cited chunks
- recent-development claims cite a recent-event source
- suitability statements are framed as educational tradeoffs, not advice

### 12.3 Failed citation behavior

| Failure | System behavior |
|---|---|
| Missing citation | Regenerate once; if still missing, remove claim or label as uncited. |
| Weak citation | Replace with stronger retrieved evidence or mark uncertainty. |
| Unsupported claim | Drop claim and log unsupported-claim event. |
| Stale citation | Show stale badge or suppress claim depending on section. |
| Wrong asset citation | Reject output and regenerate. |
| Advice-like claim | Rewrite through safety redirect template. |

---

## 13. Safety and compliance guardrails

### 13.1 Query classification

Every chat question should be classified before answer generation.

```text
definition
business_model
holdings
risk
comparison
recent_development
glossary
valuation_context
suitability_education
personalized_advice
unsupported_asset
unknown
```

### 13.2 Advice boundary

Blocked or redirected user intents:

- “Should I buy this?”
- “How much should I put in this?”
- “Is this guaranteed to go up?”
- “Give me a price target.”
- “Build my portfolio.”
- “Is this right for my taxes?”

Safe replacement behavior:

```text
I can’t tell you whether to buy it or how much to allocate.
I can explain what it is, what it holds or does, the main risks,
how it compares with similar assets, and what factors beginners
usually consider before making their own decision.
```

### 13.3 Output safety checks

Before returning a generated answer:

- scan for buy/sell/hold commands
- scan for position sizing
- scan for certainty around future returns
- scan for unsupported price targets
- require citations for factual claims
- require uncertainty when evidence is incomplete

---

## 14. API response contracts

### 14.1 Search

#### Request

```http
GET /api/search?q=VOO
```

#### Response

```json
{
  "results": [
    {
      "ticker": "VOO",
      "name": "Vanguard S&P 500 ETF",
      "asset_type": "etf",
      "exchange": "NYSE Arca",
      "issuer": "Vanguard",
      "supported": true,
      "status": "supported"
    }
  ]
}
```

### 14.2 Asset overview

#### Request

```http
GET /api/assets/VOO/overview?mode=beginner
```

#### Response

```json
{
  "asset": {
    "ticker": "VOO",
    "name": "Vanguard S&P 500 ETF",
    "asset_type": "etf"
  },
  "freshness": {
    "page_last_updated_at": "2026-04-19T14:30:00Z",
    "facts_as_of": "2026-04-18",
    "holdings_as_of": "2026-04-17",
    "recent_events_as_of": "2026-04-19"
  },
  "snapshot": {
    "issuer": "Vanguard",
    "benchmark": "S&P 500 Index",
    "expense_ratio": {
      "value": 0.03,
      "unit": "%",
      "citation_ids": ["c_expense_ratio"]
    }
  },
  "beginner_summary": {
    "what_it_is": "VOO is an ETF that aims to track the S&P 500...",
    "why_people_consider_it": "...",
    "main_catch": "..."
  },
  "top_risks": [],
  "recent_developments": [],
  "citations": [],
  "source_documents": []
}
```

### 14.3 Compare

#### Request

```http
POST /api/compare
```

```json
{
  "left_ticker": "VOO",
  "right_ticker": "QQQ",
  "mode": "beginner"
}
```

#### Response

```json
{
  "left_asset": {},
  "right_asset": {},
  "comparison_type": "etf_vs_etf",
  "key_differences": [
    {
      "dimension": "Exposure",
      "plain_english_summary": "VOO is broader; QQQ is more concentrated...",
      "citation_ids": ["c1", "c2"]
    }
  ],
  "bottom_line_for_beginners": {
    "summary": "VOO is closer to a broad U.S. large-company core fund, while QQQ is a narrower growth-heavy fund.",
    "citation_ids": ["c3", "c4"]
  },
  "citations": []
}
```

### 14.4 Asset chat

#### Request

```http
POST /api/assets/QQQ/chat
```

```json
{
  "question": "Why is this more concentrated than VOO?",
  "conversation_id": "optional-conversation-id"
}
```

#### Response

```json
{
  "direct_answer": "QQQ is more concentrated because it tracks a narrower index and has more weight in its largest holdings.",
  "why_it_matters": "Concentration can help when those large holdings perform well, but it can also make the fund less diversified.",
  "citations": [
    {
      "claim": "QQQ has more weight in its largest holdings.",
      "source_document_id": "src_123",
      "chunk_id": "chk_456"
    }
  ],
  "uncertainty": [],
  "safety_classification": "educational"
}
```

### 14.5 Export

Export endpoints should return server-shaped educational outputs, not raw unrestricted provider payloads.

Supported MVP export shapes:

- asset page summary with citation IDs and freshness metadata
- comparison output with source list
- source list with URLs, publisher, source type, dates, retrieved timestamp, and allowed excerpts
- chat transcript with safety classification, citations, uncertainty notes, and source metadata

Export behavior must respect provider licensing. Paid news or restricted provider content should be summarized or omitted unless redistribution rights are confirmed.

Exported outputs should include the persistent educational disclaimer and should preserve the same citation, freshness, uncertainty, and advice-boundary labels shown in the UI.

---

## 15. Frontend design

### 15.1 Main components

| Component | Purpose |
|---|---|
| `SearchBox` | Ticker/name search with autocomplete. |
| `AssetHeader` | Name, ticker, asset type, exchange, freshness. |
| `BeginnerSummaryCard` | Plain-English overview. |
| `RiskCards` | Exactly three top risks first. |
| `HoldingsTable` | ETF top holdings. |
| `ExposureChart` | ETF sector/country exposure. |
| `FinancialTrendsTable` | Stock financial trend view. |
| `RecentDevelopmentsPanel` | Recent context separated from basics. |
| `CompareTable` | Side-by-side comparison. |
| `CitationChip` | Inline source reference. |
| `SourceDrawer` | Source metadata and supporting text. |
| `GlossaryPopover` | Simple finance definitions. |
| `AssetChatPanel` | Grounded chat for selected asset. |

### 15.2 Source drawer behavior

When a user clicks a citation chip, open a drawer showing:

- source title
- source type
- official-source badge
- publisher
- published date
- retrieved date
- freshness state
- related claim
- supporting excerpt
- source URL

### 15.3 Freshness display

Every page should show:

```text
Page last updated: Apr 19, 2026
Holdings as of: Apr 17, 2026
Recent developments checked: Apr 19, 2026
```

Freshness should be section-specific, not just page-level.

---

## 16. Freshness, caching, and invalidation

MVP cost control should come from shared server-side caching, source-document checksums, and freshness hashes rather than user accounts. Repeated requests for the same asset should reuse cached source packs and generated summaries while freshness rules still pass.

### 16.1 Freshness hash

Every generated summary should store a `freshness_hash`.

```text
freshness_hash = hash(
  asset_id
  + canonical_fact_versions
  + source_document_checksums
  + recent_event_ids
  + prompt_version
  + model_name
)
```

If any input changes, regenerate the affected summary.

Cache keys should include the asset or comparison pack, mode, source freshness state, prompt version where generation is involved, and schema version. Cached outputs must preserve citation IDs, source metadata, section-level freshness, and stale/unknown/unavailable labels.

### 16.2 Suggested refresh rules

| Data type | Refresh cadence | Invalidation trigger |
|---|---:|---|
| SEC submissions | daily + on-demand | new filing detected |
| SEC XBRL facts | daily + on-demand | new 10-K / 10-Q / 8-K |
| Stock price/reference data | vendor-dependent | TTL expiration |
| ETF holdings | daily on market days | holdings date changes |
| ETF fact sheet | daily or weekly | checksum change |
| ETF prospectus | weekly or monthly | checksum change |
| Recent news/events | 1–6 hours | new high-signal event |
| LLM summaries | on input hash change | freshness hash mismatch |

SEC data should be fetched server-side with caching and fair-access rate limiting rather than on every user page view.

---

## 17. Performance targets

| Operation | Target |
|---|---:|
| Search autocomplete | p95 < 300 ms |
| Cached asset overview | p95 < 1.5 s |
| Cached comparison page | p95 < 2.0 s |
| Chat first token / initial response | p95 < 5.0 s |
| Full grounded chat answer | p95 < 12.0 s |
| On-demand asset ingestion | async job; page should show pending state |
| Source drawer open | p95 < 500 ms |

For MVP, pre-ingest a curated universe of common assets so users do not frequently wait for full ingestion.

---

## 18. Observability

### 18.1 Product metrics

Track:

- asset page views
- search success rate
- unsupported asset rate
- compare usage
- source drawer open rate
- glossary usage
- chat follow-up rate
- stale-page rate

### 18.2 Trust metrics

Track:

- citation coverage rate
- unsupported claim rate
- weak citation rate
- generated output validation failure rate
- safety redirect rate
- freshness accuracy
- source retrieval failure rate

These trust and comprehension metrics are directly aligned with the proposal’s recommendation to measure citation coverage, unsupported claim rate, comparison usage, glossary usage, freshness accuracy, and user understanding.

### 18.3 Technical logs

For each generated output, log:

```json
{
  "asset_id": "...",
  "request_type": "asset_summary",
  "model_provider": "...",
  "model_name": "...",
  "prompt_version": "...",
  "retrieved_chunk_ids": [],
  "source_document_ids": [],
  "freshness_hash": "...",
  "schema_valid": true,
  "citation_coverage_rate": 0.96,
  "safety_status": "passed",
  "latency_ms": 4200
}
```

---

## 19. Testing strategy

### 19.1 Unit tests

- ticker normalization
- asset type detection
- SEC CIK formatting
- source checksum logic
- parser output validation
- fact normalization
- freshness hash generation
- citation ID validation
- safety phrase detection

### 19.2 Integration tests

- SEC submissions ingestion
- SEC XBRL ingestion
- issuer fact sheet parsing
- ETF holdings parsing
- vector retrieval
- asset overview endpoint
- comparison endpoint
- chat endpoint

### 19.3 Golden asset tests

Use a small stable set:

```text
Stocks: AAPL, MSFT, NVDA, TSLA
ETFs: VOO, SPY, VTI, QQQ, VGT, SOXX
```

For each golden asset, maintain expected checks:

- correct asset type
- correct canonical name
- top risks have exactly 3 items
- ETF holdings table exists
- stock financial trend table exists
- citations exist for key claims
- no buy/sell language appears
- recent developments are separate from asset basics

### 19.4 LLM evaluation tests

Evaluate generated outputs for:

- schema validity
- citation coverage
- citation support
- beginner readability
- no personalized advice
- no unsupported price targets
- correct separation of stable facts and recent developments

---

## 20. Security and data governance

### 20.1 Secrets

Store API keys in a secret manager or environment-managed deployment secret store.

Do not expose:

- market data provider keys
- news provider keys
- LLM provider keys
- object storage credentials
- admin ingestion endpoints

### 20.2 Source sanitization

External HTML and PDF content should be sanitized before display. Never render arbitrary source HTML directly in the app.

### 20.3 User data

MVP should be accountless. Users can download asset summaries, comparison output, source lists, and chat transcripts without creating accounts. These exports should include citations and freshness metadata, and should omit or summarize restricted provider content unless redistribution rights are confirmed.

If accounts are added later, store only minimal user data:

- saved tickers
- saved comparisons
- chat conversation IDs
- preferences

Do not collect brokerage credentials or portfolio holdings in v1.

### 20.4 Admin protection

Admin ingestion endpoints should require authentication and rate limiting.

---

## 21. Deployment design

### 21.1 Recommended MVP deployment

| Component | Suggested deployment |
|---|---|
| Frontend | Vercel, Netlify, or containerized Next.js |
| API | Containerized FastAPI service |
| Worker | Separate containerized worker process |
| Database | Managed PostgreSQL with pgvector |
| Cache / queue | Managed Redis |
| Object storage | S3-compatible storage |
| Monitoring | Sentry + OpenTelemetry + provider logs |
| CI/CD | GitHub Actions |

### 21.2 Environments

```text
local
staging
production
```

### 21.3 CI/CD checks

Before deploy:

- type checks
- unit tests
- API schema tests
- DB migration tests
- parser tests
- sample LLM schema validation
- linting
- security scan

---

## 22. Failure modes and mitigations

| Failure mode | Impact | Mitigation |
|---|---|---|
| SEC rate limit hit | Stock ingestion delayed | Redis token bucket, backoff, nightly bulk where useful. |
| ETF issuer page changes | ETF parsing fails | Store raw snapshots, parser alerts, fallback market-data provider. |
| PDF parse failure | Missing prospectus/fact sheet detail | Try alternate parser, show partial-data state. |
| LLM returns invalid JSON | UI cannot render | Structured outputs when available, Pydantic validation, retry. |
| LLM creates unsupported claim | Trust issue | Citation validator, regenerate, drop unsupported claim. |
| News provider returns noisy results | Bad recent developments | Importance scoring, source whitelist, deduplication. |
| Stale holdings | Misleading ETF page | Holdings freshness label and stale warning. |
| Market data outage | Missing prices/valuation | Show unavailable state; do not block educational page. |
| User asks for advice | Compliance/trust issue | Safety classifier and educational redirect. |

---

## 23. Phased implementation plan

### Phase 0: Foundation

- Create repo structure.
- Set up Next.js app.
- Set up FastAPI service.
- Set up PostgreSQL, pgvector, Redis, object storage.
- Define Pydantic schemas.
- Add migrations.
- Build LLM provider abstraction.
- Build source-document storage.

### Phase 1: Stock and ETF asset pages

- Implement search.
- Implement asset resolution.
- Implement stock ingestion from SEC.
- Implement ETF ingestion from issuer/provider sources.
- Implement source documents and chunks.
- Implement normalized facts.
- Implement beginner asset overview.
- Implement citation chips and source drawer.
- Add freshness labels.

### Phase 2: Comparison

- Add `/compare`.
- Implement ETF-to-ETF comparison.
- Implement stock-to-stock comparison.
- Add beginner bottom-line summary.
- Add overlap metrics for ETFs.
- Add comparison citation validation.

### Phase 3: Grounded chat

- Add chat panel.
- Build asset knowledge pack retrieval.
- Add query classifier.
- Add chat answer schema.
- Add safety redirects.
- Add citation validation for chat.
- Add starter prompts.

### Phase 4: MVP reliability and accountless learning features

- Add export/download flows for asset pages, comparisons, source lists, and chat transcripts.
- Add cache and freshness-hash invalidation.
- Add pre-cache orchestration for the high-demand launch universe.
- Add on-demand ingestion job states for eligible supported assets outside the pre-cache set.
- Add hybrid glossary baseline and richer glossary pages.
- Add evaluation dashboard.

Saved assets, saved comparisons, watchlists, learning paths, and user accounts are post-MVP features and should not be required for v1.

---

## 24. MVP acceptance checklist

MVP is technically ready when:

- Search resolves supported stocks and ETFs.
- Unsupported assets return a clear unsupported state.
- Stock pages render from normalized SEC and reference data.
- ETF pages render from official issuer/provider data.
- Every page shows freshness labels.
- Every important claim has a citation or uncertainty note.
- Source drawer displays source metadata and supporting passages.
- Top risks show exactly three items first.
- Recent developments are stored and rendered separately from canonical facts.
- Comparison works for at least ETF-vs-ETF and stock-vs-stock.
- Chat answers only from the selected asset knowledge pack.
- Safety guardrails prevent buy/sell, price-target, and allocation advice.
- Users can export asset pages, comparison output, source lists, and chat transcripts with citations, freshness metadata, and the educational disclaimer.
- Hybrid glossary support covers core beginner terms and does not introduce uncited asset-specific facts.
- Shared server-side caching, source checksums, and freshness hashes avoid repeated provider and LLM work while preserving freshness labels.
- Citation coverage, unsupported claim rate, latency, glossary usage, export usage, safety redirects, and freshness accuracy are logged.

---

## 25. Resolved MVP planning assumptions

1. Market/reference data should use official and structured sources first. PRD v0.2 prefers Massive for market/reference data and Massive plus ETF Global for ETF data where budget allows, with lower-cost fallbacks only after validation and licensing review.
2. MVP should pre-cache a high-demand launch universe and support on-demand ingestion for eligible supported assets outside it.
3. Retrieval should remain self-managed first so citation binding, source freshness, and asset filters stay under application control.
4. Citation strictness is per important factual claim, not per sentence.
5. Recent developments should prefer official filings, company investor-relations releases, ETF issuer announcements, and prospectus updates before reputable ticker-tagged news.
6. V1 should be accountless.
7. Export/download is the v1 save-for-later workflow; exported output must include citations, freshness metadata, and the educational disclaimer while respecting provider licensing.
8. Server-side caching, source-document checksums, generated-summary freshness hashes, and pre-cached knowledge packs should reduce provider and LLM calls.
9. ETF issuer parser maintenance remains an implementation risk; parsers should store raw snapshots, checksums, and parser diagnostics.
10. Leveraged ETFs, inverse ETFs, ETNs, crypto, options, international equities, preferred stocks, warrants, rights, and complex products are unsupported for generated pages, chat, and comparisons unless explicitly added later.

---

## 26. Technical thesis

The strongest architecture is a **source-first retrieval and generation system**, not a generic finance chatbot.

The system should:

- ingest official and structured sources
- normalize facts
- preserve source documents and chunks
- generate beginner explanations from bounded evidence
- validate citations before display
- separate recent context from stable facts
- avoid personalized investment advice
- expose freshness and uncertainty directly in the UI

That design matches the proposal’s central idea: a financial learning product with beginner language, visible citations, comparison-first workflows, recent-context separation, and asset-specific grounded chat.
