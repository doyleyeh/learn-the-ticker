# Technical Design Spec: Learn the Ticker - Citation-First Beginner U.S. Stock & ETF Research Assistant

**Document version:** v0.2 control-doc alignment
**Product stage:** MVP / v1 planning  
**Related doc:** PRD v0.2 refined
**Source basis:** Current project proposal, PRD v0.2, and resolved implementation-readiness decisions.
**Documentation role:** Engineering source of truth for implementation. The PRD remains the product source of truth, and this repo is currently planning-only.

---

## 1. Executive summary

This system is an accountless web app that lets a beginner search a U.S.-listed common stock or non-leveraged U.S.-listed equity index, sector, or thematic ETF, then returns a source-grounded educational page with beginner explanations, cited facts, Weekly News Focus, AI Comprehensive Analysis, comparisons, glossary help, limited asset-specific grounded chat, and exportable learning outputs.

The core technical challenge is not simply generating good prose. The system must reliably separate:

1. **Canonical facts** - stable source-backed asset facts.
2. **Timely context** - Weekly News Focus, filings, fee changes, earnings, or methodology updates.
3. **Teaching layer** - AI-written plain-English explanation and chat answers.

That three-layer knowledge architecture comes directly from the proposal and remains the backbone of this design. PRD v0.2 adds functional-MVP direction: pre-cache the high-demand launch universe, support the top 500 U.S.-listed common stocks first, expose explicit ingestion states for approved on-demand assets, keep v1 accountless, expose Markdown/JSON export flows, and use caching plus freshness hashes to control API and LLM cost.

---

## 2. Design goals

### 2.1 Primary goals

| Goal | Design implication |
|---|---|
| Source-first explanations | Store raw source documents, normalized facts, chunks, and citation mappings before generating summaries. |
| Beginner-friendly language | Generate structured summaries using schemas for the Beginner section and glossary terms. |
| Visible citations | Every important claim should map to a `source_document`, `document_chunk`, or normalized `fact`. |
| Stable facts separated from Weekly News Focus and analysis | Maintain separate data tables and UI sections for canonical facts, Weekly News Focus, and AI Comprehensive Analysis. |
| Grounded asset-specific chat | Build an `asset_knowledge_pack` per asset and restrict chat retrieval to that pack. |
| Compare-first learning | Support side-by-side comparison using normalized facts and generated beginner summaries. |
| Education over advice | Add query classification, output validation, and safety filters to avoid buy/sell or allocation instructions. |
| Accountless v1 | Store shared cached artifacts and exportable outputs without requiring user accounts. |
| Cost-aware freshness | Use source checksums, TTLs, and freshness hashes to avoid unnecessary provider and LLM calls. |

### 2.2 Non-goals for v1

The system will not support brokerage trading, tax advice, options, crypto, international equities, portfolio optimization, leveraged ETFs, inverse ETFs, ETNs, fixed income ETFs, commodity ETFs, active ETFs, multi-asset ETFs, preferred stocks, warrants, rights, complex exchange-traded products, user accounts, saved watchlists, saved assets, PDF exports, or personalized position sizing.

---

## 3. Key technical decisions

| Area | Decision | Rationale |
|---|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui | Fits interactive asset pages, source drawers, glossary popovers, and chat panel. |
| Backend | Python + FastAPI | Strong ecosystem for SEC ingestion, parsing, financial data processing, and LLM orchestration. |
| Local infrastructure | Docker Compose for Next.js, FastAPI, PostgreSQL with pgvector, Redis, and S3-compatible object storage | Gives implementation a reproducible local stack before managed deployment choices are made. |
| Production deployment | Vercel Hobby, Cloud Run, Cloud Run Jobs, Neon Free Postgres, private Google Cloud Storage | Keeps the first personal side-project deployment low fixed-cost while leaving room to scale later. |
| Database | PostgreSQL | Good fit for normalized facts, source metadata, audit logs, freshness state, and relational asset data. |
| Vector search | pgvector extension may be installed, but vector indexes and embedding jobs stay disabled by default | Keeps semantic retrieval available later without making embeddings a blocker for the first deterministic implementation. |
| Cache / queues | Local Redis; production Postgres `ingestion_jobs` first | Avoids always-on queue cost for the first deployment. Redis can return later when scale requires it. |
| Object storage | Local MinIO; production private Google Cloud Storage | Stores raw filings, PDF snapshots, HTML snapshots, parsed text, and generated artifacts. |
| LLM access | Adapter-first provider abstraction with deterministic mocks and feature-flagged OpenRouter fallback chain | Allows first deployment to use explicit free models plus automatic DeepSeek fallback server-side while CI/local tests stay mock-safe. |
| Structured generation | JSON-schema outputs where provider supports it | Produces predictable UI-renderable output and supports server-side validation. |
| Retrieval | Keyword and metadata retrieval first; embeddings later | Self-managed keyword-first retrieval gives stricter control over citation binding and freshness metadata before adding model cost. |
| Source freshness | Section-level freshness hashes | Summaries are invalidated when underlying facts, chunks, or Weekly News Focus event records change. |
| Coverage model | Top-500-first U.S. common stock manifest plus supported ETFs and explicit ingestion states | Improves launch reliability while keeping future expansion queue-backed and source-aware. |
| User model | Accountless MVP | Defers identity, saved assets, and watchlists while preserving export/download workflows. |
| Export model | Server-shaped Markdown and JSON summaries and source lists | Lets users save learning outputs while respecting citation, freshness, uncertainty labels, and licensing constraints. |

---

## 4. High-level architecture

```text
+-------------------------+
| Next.js Web             |
| Search, asset pages,    |
| compare, chat, exports  |
+------------+------------+
             |
+------------v------------+
| FastAPI API             |
| routing, response       |
| shaping, validation     |
+------------+------------+
             |
+------------+------------+----------------+
|            |                             |
+------------v--+   +-----v---------+   +---v-------------+
| Asset Service |   | Compare       |   | Chat Service    |
| overview/data |   | normalized    |   | grounded Q&A    |
| Weekly News Focus | | differences   |   | compare redirect|
+-------+-------+   +-------+-------+   +--------+--------+
        |                   |                    |
+-------v-------------------v--------------------v--------+
| Data Layer                                             |
| PostgreSQL + pgvector | Redis | Object Storage         |
| assets, facts, chunks, sources, events, summaries, jobs|
+-------+-------------------+--------------------+--------+
        |                   |                    |
+-------v-------+   +-------v---------+   +------v--------+
| Ingestion Jobs|   | Retrieval       |   | LLM           |
| SEC, ETF docs,|   | hybrid search,  |   | Orchestrator  |
| market data,  |   | reranking,      |   | extraction,   |
| Weekly News Focus | | evidence packs  |   | page/chat     |
+---------------+   +-----------------+   +---------------+
```

---

## 5. Core services

### 5.1 Web app

**Responsibilities**

- Search UI.
- Asset page rendering.
- Beginner section and Deep-Dive section navigation.
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
GET  /api/citations/{citation_id}
GET  /api/assets/{ticker}/weekly-news
POST /api/compare
POST /api/assets/{ticker}/chat
GET  /api/assets/{ticker}/export
GET  /api/compare/export?left=VOO&right=QQQ
POST /api/admin/ingest/{ticker}
GET  /api/jobs/{job_id}
```

The proposal already suggests this API surface; this spec formalizes the response contracts, source binding, and pipeline behavior.

**Default public rate limits**

| Surface | Default |
|---|---:|
| Search | `60/min/IP` |
| Chat | `20/hour/conversation` |
| Ingestion | `5/hour/IP` |

Rate limits must be environment-configurable and enforced before expensive provider, retrieval, ingestion, or LLM work begins.

Runtime feature defaults:

- `RETRIEVAL_MODE=keyword`
- `EMBEDDINGS_ENABLED=false`
- `RAW_SOURCE_TEXT_POLICY=rights_tiered`
- `LLM_LIVE_GENERATION_ENABLED=false` for local and CI; first deployment may set it to `true` with the explicit OpenRouter free-model chain and automatic DeepSeek fallback.
- `LLM_VALIDATION_RETRY_COUNT=1`
- `LLM_REASONING_SUMMARY_ONLY=true`

### 5.3 Ingestion worker

**Responsibilities**

- Resolve assets.
- Classify supported, unsupported, out-of-scope, `pending_ingestion`, partial, stale, unknown, and unavailable states.
- Fetch source documents.
- Store raw source snapshots.
- Parse filings, fact sheets, issuer pages, and holdings files.
- Extract normalized facts.
- Chunk source text.
- Generate embeddings when the embedding adapter is enabled.
- Refresh stale assets.
- Support pre-cache jobs for the top-500-first launch universe and explicit `pending_ingestion` states for approved on-demand assets outside it.
- Track ingestion job status.

**Recommended queue model**

Use the Postgres `ingestion_jobs` table as the first production queue to avoid always-on queue cost. Local Redis can support development experiments, and Redis Queue, Dramatiq, Arq, or Celery can be added later only when scale justifies another moving part.

### 5.4 Retrieval service

**Responsibilities**

- Build asset-specific evidence sets.
- Run hybrid retrieval:
  - keyword search
  - metadata filters
  - source-type boosts
  - recency boosts for Weekly News Focus questions
  - optional semantic vector search when embeddings are available
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

The LLM orchestration service should hide provider-specific details behind a small adapter interface. Tests should use deterministic mocks. Runtime providers should be configured by environment and may use OpenAI-compatible, OpenRouter-compatible, or other hosted APIs. For strict UI-ready outputs, use structured responses where possible; otherwise use JSON-mode prompting plus Pydantic validation and repair.

---

## 6. Data sources

Priority labels in engineering tables follow the PRD: `P0` is a launch blocker for MVP/v1, `P1` is MVP-desired or beta-quality work that can ship after launch unless promoted, and `P2` is post-MVP. If an acceptance checklist item depends on a `P1` row, the row should be corrected to `P0`.

### 6.1 Stock sources

| Source category | Use | Priority |
|---|---|---|
| SEC submissions API | Company identity, filings history, CIK, ticker metadata | P0 |
| SEC XBRL company facts | Financial metrics and multi-year trends | P0 |
| SEC filings: 10-K, 10-Q, 8-K | Business overview, risks, MD&A, recent events | P0 |
| Company investor relations | Earnings releases, presentations, segment explanations | P1 |
| Free/reference metadata or configured provider adapter | ticker reference, delayed or best-effort price, market cap, sector, industry, valuation fields, volume where available | P0 |
| Allowlisted free/RSS/news source | Weekly News Focus only, after official filings and investor-relations sources | P1 |

SEC EDGAR APIs should be used server-side, cached aggressively, and rate-limited. Stock ingestion should never depend on live user-page calls to SEC. V1 is free-first and assumes no paid provider keys; provider integrations must be optional adapters with fixtures and mocks for tests.

### 6.2 ETF sources

| Source category | Use | Priority |
|---|---|---|
| ETF issuer official page | fund identity, objective, expense ratio, AUM, holdings link | P0 |
| ETF fact sheet | holdings, sector exposure, benchmark, fees | P0 |
| Summary prospectus / full prospectus | risks, methodology, objective, fees | P0 |
| Shareholder reports | official fund reporting context | P1 |
| Holdings CSV / JSON / Excel | top holdings, concentration, country/sector exposure | P0 |
| Free/reference metadata or configured provider adapter | delayed or best-effort quote, AUM, average volume, spread data, ETF reference metadata where available | P0 |
| Sponsor press releases / allowlisted free/RSS/news sources | fee cuts, methodology changes, mergers, liquidations | P1 |

ETF issuer websites are especially important because ETF disclosure includes investor-facing items such as holdings, premium/discount information, and bid-ask spread disclosures. V1 should support non-leveraged U.S.-listed equity index, sector, and thematic ETFs first. Paid ETF data providers are optional future adapters and must be validated against issuer sources before production use.

News and RSS sources use a tiered allowlist. Official sources have the highest rank. Reuters/AP-style and similar publishers are license-gated: the source registry must record whether each source is `metadata_only`, `link_only`, `summary_allowed`, `full_text_allowed`, or `rejected` before ingestion output can be displayed, summarized, stored, or exported.

### 6.3 Top-500 stock universe manifest

The top-500 U.S. common stock universe is resolved from a versioned manifest.

- Local path: `data/universes/us_common_stocks_top500.current.json`.
- Production URI: `TOP500_UNIVERSE_MANIFEST_URI`, mirrored to private GCS.
- Required entry fields: ticker, name, CIK when available, exchange, rank, rank basis, provider/source provenance, snapshot date, generated checksum, and approval timestamp.
- Monthly refresh is the default. Ad hoc refresh requires a development-log entry.
- The manifest is operational coverage metadata, not advice or a recommendation list.
- Resolver behavior: a U.S. common stock outside the manifest returns `out_of_scope` unless it is explicitly added to an approved on-demand ingestion queue.

### 6.4 Source allowlist governance and raw text policy

The source allowlist lives in configuration, e.g. `config/source_allowlist.yaml`. Config-only review means future agents may update it when source-use policy, source type, domain, rationale, validation tests, and development-log rationale are updated together. Automated scoring can rank only already-allowed sources; it cannot approve new sources.

The raw source text policy is rights-tiered:

- Official filings, issuer materials, and `full_text_allowed` sources may store full raw text, parsed text, chunks, checksums, and snapshots.
- `summary_allowed` sources may store metadata, checksums, links, and excerpts needed to support summaries.
- `metadata_only` and `link_only` sources may store metadata, hashes, canonical URLs, timestamps, and diagnostics, but not full article text.
- `rejected` sources must not feed generated output and should retain only rejection diagnostics when needed.

### 6.5 Provider roles and constraints

- SEC EDGAR is the stock trust backbone for identity, filing history, XBRL company facts, filing-derived business descriptions, and risk extraction. It is free, keyless, and updated throughout the day.
- ETF issuer materials are the ETF trust backbone for identity, holdings, fees, methodology, exposures, and fund risks.
- Financial Modeling Prep can enrich quotes, volume, aftermarket bid/ask, statement convenience data, AUM/net-assets-style ETF reference fields, and ETF/fund holdings, but public display or redistribution requires a specific FMP data display and licensing agreement.
- Alpha Vantage is acceptable for low-volume experiments and selected enrichment; the standard free limit of 25 API requests per day is not enough for broad ingestion.
- Finnhub can enrich quotes, fundamentals, and news-style context, but listed plans are personal-use unless explicitly approved and redistribution requires written approval.
- Tiingo can enrich end-of-day data, corporate actions, selected news/fundamentals endpoints, and ETF/mutual-fund fee metadata. Prefer it for stable non-tick workflows.
- EODHD can support light testing, EOD-style history, delayed live data, and basic fundamentals, but free access is small and public usage requires personal-use/commercial-use review.
- yfinance may be used only for local development or fallback diagnostics. It must not be production truth.
- UI and API contracts must expose `fresh`, `stale`, `partial`, and `unavailable` states for quote/reference data; do not imply real-time coverage.

---

## 7. Source hierarchy

The system should rank evidence using the hierarchy from the proposal. Stable facts should come from official or structured sources first; Weekly News Focus and AI Comprehensive Analysis should add context but should not redefine the asset.

### 7.1 Stock source ranking

1. SEC filings and XBRL data.
2. Company investor relations pages.
3. Earnings releases and presentations.
4. Free/reference metadata or configured provider adapter.
5. Official and allowlisted free-news sources, used only for Weekly News Focus context.

### 7.2 ETF source ranking

1. ETF issuer official page.
2. ETF fact sheet.
3. Summary prospectus and full prospectus.
4. Shareholder reports.
5. Free/reference metadata or configured provider adapter.
6. Official and allowlisted free-news sources, used only for Weekly News Focus context.

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
  status TEXT NOT NULL, -- supported | unsupported | out_of_scope | pending_ingestion | partial | stale | unknown | unavailable
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
  source_quality TEXT, -- official | allowlisted | provider | fixture | rejected | unknown
  allowlist_status TEXT, -- allowed | rejected | not_applicable | pending_review
  source_use_policy TEXT, -- metadata_only | link_only | summary_allowed | full_text_allowed | rejected
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
  valid_from TIMESTAMPTZ,
  valid_to TIMESTAMPTZ,
  source_version TEXT,
  source_accession_number TEXT,
  schema_version TEXT NOT NULL,
  is_current BOOLEAN DEFAULT TRUE,
  superseded_by_fact_id UUID REFERENCES facts(id),
  extraction_method TEXT, -- api | parser | llm | manual
  confidence NUMERIC,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
```

Fact updates should create new rows and supersede old rows rather than silently overwriting history. Current page reads should filter to `is_current = TRUE`; audit and comparison/debug views may read superseded facts by validity window.

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

Stores Weekly News Focus events separately from canonical facts.

```sql
recent_events (
  id UUID PRIMARY KEY,
  asset_id UUID REFERENCES assets(id),
  event_type TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  event_date DATE,
  published_at TIMESTAMPTZ,
  news_window_start DATE,
  news_window_end DATE,
  period_bucket TEXT, -- previous_market_week | current_week_to_date
  source_document_id UUID REFERENCES source_documents(id),
  importance_score NUMERIC,
  focus_rank INT,
  source_quality TEXT,
  allowlist_status TEXT,
  source_use_policy TEXT,
  freshness_state TEXT,
  citation_ids TEXT[],
  created_at TIMESTAMPTZ
)
```

#### `summaries`

Stores generated page sections.

```sql
summaries (
  id UUID PRIMARY KEY,
  asset_id UUID REFERENCES assets(id),
  summary_type TEXT NOT NULL, -- beginner | deep_dive | risks | weekly_news_focus | news_analysis | suitability
  output_json JSONB NOT NULL,
  model_provider TEXT,
  model_name TEXT,
  prompt_version TEXT,
  schema_version TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'en',
  section_key TEXT NOT NULL,
  freshness_hash TEXT NOT NULL,
  evidence_state TEXT, -- complete | partial | stale | unavailable | unknown
  generation_status TEXT, -- pending | succeeded | failed | suppressed
  validation_status TEXT,
  validation_error_json JSONB,
  superseded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ
)
```

Summary regeneration should create a new summary row and mark prior rows with `superseded_at` when their inputs, schema, language, prompt, or validation state changes.

#### `claims`

Stores generated claim text and validation state. Supporting evidence is stored in `claim_citations` because many claims require multiple citations.

```sql
claims (
  id UUID PRIMARY KEY,
  summary_id UUID REFERENCES summaries(id),
  asset_id UUID REFERENCES assets(id),
  claim_text TEXT NOT NULL,
  claim_type TEXT, -- fact | interpretation | risk | weekly_news | news_analysis | comparison
  citation_required BOOLEAN DEFAULT TRUE,
  citation_status TEXT, -- valid | missing | weak | unsupported
  created_at TIMESTAMPTZ
)
```

#### `claim_citations`

Stores all supporting evidence for generated claims.

```sql
claim_citations (
  id UUID PRIMARY KEY,
  claim_id UUID REFERENCES claims(id),
  source_document_id UUID REFERENCES source_documents(id),
  source_chunk_id UUID REFERENCES document_chunks(id),
  fact_id UUID REFERENCES facts(id),
  citation_role TEXT, -- primary | supporting | comparison_left | comparison_right
  created_at TIMESTAMPTZ
)
```

#### `chat_sessions`

Stores anonymous accountless chat session state for grounded follow-ups and user-requested export.

```sql
chat_sessions (
  id UUID PRIMARY KEY,
  conversation_id TEXT UNIQUE NOT NULL,
  asset_id UUID REFERENCES assets(id),
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ,
  deletion_status TEXT -- active | user_deleted | expired
)
```

#### `chat_messages`

Stores accountless chat transcript messages for the session TTL.

```sql
chat_messages (
  id UUID PRIMARY KEY,
  chat_session_id UUID REFERENCES chat_sessions(id),
  role TEXT NOT NULL, -- user | assistant
  message_text TEXT NOT NULL,
  safety_classification TEXT,
  citation_ids TEXT[],
  uncertainty_json JSONB,
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

### 8.1 Database constraints and indexes

The PostgreSQL schema should include explicit constraints and indexes so data quality is not left only to application code.

Check constraints for enum-like fields:

- `assets.asset_type`: `stock`, `etf`, `unknown`
- `assets.support_status`: `supported`, `unsupported`, `out_of_scope`, `pending_ingestion`, `partial`, `stale`, `unknown`, `unavailable`
- `source_documents.use_policy`: `metadata_only`, `link_only`, `summary_allowed`, `full_text_allowed`, `rejected`
- `claim_citations.role`: `canonical_fact`, `recent_event`, `comparison_left`, `comparison_right`, `glossary_context`
- `claims.state`: `cited`, `uncertain`, `unavailable`, `stale`, `partial`
- `ingestion_jobs.status`: `queued`, `running`, `succeeded`, `failed`, `cancelled`
- `recent_events.event_type`: stock and ETF event types listed in the Weekly News Focus section

Unique constraints:

- `assets.ticker`
- `(asset_identifiers.asset_id, identifier_type, identifier_value)`
- `source_documents.provider_document_id`
- `document_chunks.chunk_key`
- `(claim_citations.claim_id, source_document_id, role)`
- `chat_sessions.conversation_id`
- `glossary_terms.term`

Indexes:

- `facts(asset_id, fact_key) WHERE is_current = true`
- `recent_events(asset_id, event_date DESC, importance_score DESC)`
- `source_documents(asset_id, source_type, retrieved_at DESC)`
- `ingestion_jobs(status, created_at)`
- `chat_sessions(expires_at) WHERE deleted_at IS NULL`
- PostgreSQL full-text GIN index on `document_chunks.text` or a generated `tsvector` column for keyword-first retrieval

pgvector can remain installed for future migration compatibility, but vector indexes and embedding jobs stay disabled until retrieval moves beyond keyword-first.

---

## 9. Ingestion pipeline

### 9.1 Universal ingestion flow

```text
1. Resolve asset using SEC/issuer metadata and the top-500 manifest.
2. Classify asset as supported, unsupported, out-of-scope, `pending_ingestion`, partial, stale, unknown, or unavailable.
3. Fetch source documents for supported assets
4. Save raw snapshots
5. Parse source documents
6. Chunk parsed text
7. Run keyword/metadata indexing; generate embeddings only when `EMBEDDINGS_ENABLED=true`.
8. Extract normalized facts
9. Retrieve high-signal Weekly News Focus events
10. Mark section-level evidence states for partial pages
11. Build or refresh asset knowledge pack
12. Generate or invalidate summaries
13. Validate citations
14. Mark freshness state
15. Update shared cache entries and freshness hashes
```

MVP should support pre-cache ingestion for the top-500-first launch universe and explicit `pending_ingestion` states for approved on-demand assets outside that universe. Unsupported and out-of-scope assets should return a recognized-but-unsupported or recognized-but-out-of-scope state from search and must not trigger generated pages, generated chat, or generated comparisons. Supported assets with incomplete evidence should return partial pages instead of invented content.

### 9.1.1 Deterministic asset classification

Asset classification is deterministic application logic. The LLM must never decide whether an asset is supported, and LLM output must never override classification fields produced by resolver/provider data.

Rules:

- If `fund_leverage > 1`, return `unsupported`.
- If `inverse_flag == true`, return `unsupported`.
- If `asset_class != equity`, return `unsupported`.
- If `strategy == active`, return `unsupported`.
- If the asset is outside U.S. common stock or non-leveraged U.S.-listed passive equity ETF scope, return `unsupported` or `out_of_scope`.
- If a stock is outside the top-500 MVP universe, return `out_of_scope` unless it has been explicitly added to the approved on-demand ingestion queue.
- If an asset passes deterministic classification but lacks an asset pack, return `pending_ingestion`.
- If an asset has verified facts but missing sections, return `partial`, `stale`, or `unavailable` section states rather than generating unsupported claims.

Classification inputs should come from SEC metadata, the top-500 manifest, issuer/provider metadata, and normalized fund fields. If a required field is missing, classify conservatively and record parser diagnostics.

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

Resolution should use SEC metadata and free/reference metadata where available. Configured provider adapters may add fields, but missing provider data must not block SEC-backed stock ingestion.

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
- Weekly News Focus
- AI Comprehensive Analysis
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
  "category": "Large Blend",
  "supported_scope": "non_leveraged_equity_etf"
}
```

ETF resolution must reject or mark out of scope fixed income, commodity, active, multi-asset, leveraged, inverse, ETN, and other complex products before generated pages, chat, or comparison run.

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

If a free-first source cannot verify a field, mark that section `partial`, `stale`, `unknown`, or `unavailable` and keep generating only from verified facts.

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
- Weekly News Focus
- AI Comprehensive Analysis
- suitability summary

### 9.4 Weekly News Focus and AI Comprehensive Analysis ingestion

Weekly News Focus and AI Comprehensive Analysis should never overwrite canonical facts. Raw events are stored in `recent_events`; generated Weekly News Focus and AI Comprehensive Analysis outputs are stored in `summaries`.

The Weekly News Focus pipeline should prefer official sources, then curated allowlisted free/RSS/news sources. Reuters/AP-style and similar publishers are license-gated and should not be treated as free full-content sources by default. Unrecognized sources are rejected until added to the allowlist with a source-use policy of `metadata_only`, `link_only`, `summary_allowed`, `full_text_allowed`, or `rejected`. Events must store source-quality metadata, source-use policy, allowlist status, event type, freshness state, and citation links.

#### Weekly News Focus flow

```text
1. Collect official and allowlisted news for the selected asset.
2. Deduplicate by canonical URL, headline similarity, source, and event date.
3. Score relevance, source quality, event importance, and recency.
4. Assign each event to `previous_market_week` or `current_week_to_date`.
5. Select 5-8 focus items only when enough high-quality evidence exists.
6. Generate one-sentence beginner-friendly summaries for selected items.
7. Generate AI Comprehensive Analysis only when at least two high-signal Weekly News Focus items exist.
8. Validate citations, safety, source allowlist status, source-use policy, and freshness labels.
```

The default UI copy should say **Weekly News Focus**. The implementation uses the last completed Monday-Sunday market week plus current week-to-date through yesterday for `news_window_start` and `news_window_end`, using U.S. Eastern dates. For example, if today is Wednesday, include last Monday-Sunday plus this Monday and Tuesday.

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

Default weights:

| Scoring field | Defaults |
| --- | --- |
| `source_quality_weight` | official `5`; allowlisted_reputable `3`; provider_metadata_only `1` |
| `event_type_weight` | earnings `5`; guidance `5`; fee_change `5`; methodology_change `5`; routine_press_release `1` |
| `recency_weight` | current_week_to_date `3`; previous_market_week `2`; older_but_relevant `1` |
| `asset_relevance_weight` | exact ticker/CIK/issuer match `3`; strong fund/company match `2`; sector/theme context only `1` |
| `duplicate_penalty` | exact duplicate `5`; near duplicate `3`; same story cluster after first item `2` |

Thresholds:

- `minimum_display_score = 7`
- `minimum_ai_analysis_items = 2`
- Source-use policy wins over score: rejected or license-disallowed sources never display.

Only events above a configured threshold should appear on the asset page. If fewer than 5 valid items exist, return the smaller verified set with an evidence note. Do not pad with weak news to reach 5-8 items. If no valid items exist, show a "No major Weekly News Focus items found" empty state. Suppress AI Comprehensive Analysis unless at least two high-signal Weekly News Focus items exist.

#### AI Comprehensive Analysis sections

The generated analysis should include **What Changed This Week** followed by three educational context sections:

- `Market Context`
- `Business/Fund Context`
- `Risk Context`

Section labels are UI labels only. They are not real advisors, model identities, or independent sources. Each section must include a compact plain-English paragraph, bullets, citation IDs, and uncertainty notes when evidence is thin. Analysis must not include buy/sell/hold, allocation, tax, guaranteed-return, or price-target advice.

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
- start with keyword and metadata filtering
- use embeddings only after `EMBEDDINGS_ENABLED=true`, the embedding adapter is configured, and a pgvector index exists
- include source metadata with every retrieved item
- avoid stale sources unless clearly labeled
- include Weekly News Focus events only when the question asks about Weekly News Focus or the page section is Weekly News Focus and AI Comprehensive Analysis

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

Single-asset chat must not silently build this merged pack. If a user asks about a second ticker inside `POST /api/assets/{ticker}/chat`, return a compare-route suggestion instead.

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
- Weekly News Focus difference

For stock-to-ETF comparisons, use a dedicated cross-type template and compute:

- single-company risk vs basket risk
- business model vs holdings exposure
- company financials vs fund methodology
- valuation metrics vs expense ratio and concentration
- idiosyncratic risk vs diversified sector exposure

`NVDA` vs `SOXX` should be a golden stock-vs-ETF comparison scenario.

---

## 11. Generation design

### 11.1 Generation stages

```text
Stage A: Fact extraction
Stage B: Fact validation
Stage C: Page section generation
Stage D: Section evidence-state labeling
Stage E: Claim-to-citation binding
Stage F: Safety validation
Stage G: Persist summary
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
- Deterministic mock responses for CI and local tests.
- Local or open-source models later.
- Retry and validation.
- Prompt versioning.
- Model fallback.

When a provider supports strict JSON-schema output, use it. When it does not, prompt for JSON and validate with Pydantic server-side.

OpenRouter runtime configuration:

- `LLM_PROVIDER=openrouter`
- `LLM_LIVE_GENERATION_ENABLED=true` for first deployment live generation
- `LLM_VALIDATION_RETRY_COUNT=1`
- `LLM_REASONING_SUMMARY_ONLY=true`
- `LLM_CHAT_CACHE_TTL_SECONDS=86400`
- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
- `OPENROUTER_MODEL` optional single-model override, blank by default
- `OPENROUTER_FREE_MODEL_ORDER=openai/gpt-oss-120b:free,google/gemma-4-31b-it:free,qwen/qwen3-next-80b-a3b-instruct:free,meta-llama/llama-3.3-70b-instruct:free`
- `OPENROUTER_PAID_FALLBACK_MODEL=deepseek/deepseek-v3.2`
- `OPENROUTER_PAID_FALLBACK_ENABLED=true`
- `OPENROUTER_SITE_URL`
- `OPENROUTER_APP_TITLE=Learn the Ticker`

The OpenRouter API key must stay server-side. The web app should call the FastAPI backend, not OpenRouter. Local live testing may read `OPENROUTER_API_KEY` from the developer's WSL Bash environment when the API or worker is launched from WSL. The key value must not be committed, copied into `.env.example`, exposed through `NEXT_PUBLIC_*`, returned from `/health`, or printed in logs. `/health` may report `llm_provider=openrouter` but must not expose secret values.

Default live flow:

```text
Free model chain
  -> schema/citation/safety validation
  -> one repair retry
  -> DeepSeek V3.2 paid fallback
  -> validation again
  -> cache only validated output
```

OpenRouter requests should use the `models` array for the free chain in this order:

1. `openai/gpt-oss-120b:free`
2. `google/gemma-4-31b-it:free`
3. `qwen/qwen3-next-80b-a3b-instruct:free`
4. `meta-llama/llama-3.3-70b-instruct:free`

If the free chain errors, rate-limits, cannot satisfy strict structured output, or fails validation after one repair retry, the API automatically falls back to `deepseek/deepseek-v3.2`. Persist selected model, tier `free|paid|mock`, usage, cost, latency, validation result, and attempt count when available. Raw model reasoning, `reasoning_details`, hidden prompts, unrestricted source text, and failed raw responses must not be stored or shown. Public responses may expose only a short cited `reasoning_summary`.

`openrouter/free` remains an optional manual override for experiments, not the default production strategy.

### 11.2.1 LLM orchestration and cache

The `LlmOrchestrator` sits above provider adapters and performs validation-aware fallback. It builds a cache key from task, ticker or conversation scope, knowledge-pack hash, prompt version, schema version, safety-policy version, source freshness hash, and model-chain version. Chat cache TTL defaults to 24 hours. Asset analysis cache invalidates when freshness hash, prompt version, schema version, or source pack changes.

The orchestrator caches only validated outputs. It returns `answer_state=complete` for validated generations and `answer_state=partial` or `answer_state=unavailable` when all attempts fail validation. Advice-like prompts are blocked before LLM calls, and advice-like generated content fails validation even when schema and citations appear valid.

### 11.3 Page summary schema

Example simplified schema:

```json
{
  "type": "object",
  "required": [
    "beginner_summary",
    "top_risks",
    "weekly_news_focus",
    "ai_comprehensive_analysis",
    "suitability_summary",
    "section_states",
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
    "section_states": {
      "type": "object",
      "description": "Per-section evidence and freshness state for complete or partial pages."
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
    "weekly_news_focus": {
      "type": "object",
      "required": ["news_window_start", "news_window_end", "window", "items", "freshness"],
      "properties": {
        "news_window_start": {"type": "string"},
        "news_window_end": {"type": "string"},
        "window": {
          "type": "object",
          "required": ["previous_market_week", "current_week_to_date", "timezone"],
          "properties": {
            "previous_market_week": {"type": "object"},
            "current_week_to_date": {"type": "object"},
            "timezone": {"type": "string"}
          }
        },
        "freshness": {"type": "object"},
        "items": {
          "type": "array",
          "minItems": 0,
          "maxItems": 8,
          "items": {
            "type": "object",
            "required": ["source", "title", "published_at", "summary", "event_type", "period_bucket", "citation_ids", "source_quality", "allowlist_status", "source_use_policy"],
            "properties": {
              "source": {"type": "string"},
              "title": {"type": "string"},
              "published_at": {"type": "string"},
              "summary": {"type": "string"},
              "event_type": {"type": "string"},
              "period_bucket": {"type": "string"},
              "citation_ids": {"type": "array", "items": {"type": "string"}},
              "source_quality": {"type": "string"},
              "allowlist_status": {"type": "string"},
              "source_use_policy": {"type": "string"}
            }
          }
        }
      }
    },
    "ai_comprehensive_analysis": {
      "type": "object",
      "required": ["what_changed_this_week", "sections"],
      "properties": {
        "what_changed_this_week": {
          "type": "object",
          "required": ["analysis", "bullets", "citation_ids", "uncertainty"],
          "properties": {
            "analysis": {"type": "string"},
            "bullets": {"type": "array", "items": {"type": "string"}},
            "citation_ids": {"type": "array", "items": {"type": "string"}},
            "uncertainty": {"type": "array", "items": {"type": "string"}}
          }
        },
        "sections": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["label", "analysis", "bullets", "citation_ids", "uncertainty"],
            "properties": {
              "label": {"type": "string"},
              "analysis": {"type": "string"},
              "bullets": {"type": "array", "items": {"type": "string"}},
              "citation_ids": {"type": "array", "items": {"type": "string"}},
              "uncertainty": {"type": "array", "items": {"type": "string"}}
            }
          }
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
        "compare_route_redirect",
        "insufficient_evidence"
      ]
    },
    "compare_route_suggestion": {
      "type": ["object", "null"],
      "properties": {
        "left_ticker": {"type": "string"},
        "right_ticker": {"type": "string"},
        "route": {"type": "string"}
      }
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
7. `claim_citations` stores one or more supporting citations for each claim.
8. Validator checks every citation ID.
9. UI renders citation chips.
10. Source drawer opens exact source metadata and supporting passage.
```

### 12.2 Citation validation rules

A generated output is valid only if:

- every important factual claim has at least one citation
- or, if evidence is missing, the claim is suppressed and the section carries an explicit uncertainty, unavailable, stale, or partial label
- every citation ID exists
- cited source belongs to the same asset or comparison pack
- cited source is not stale unless labeled stale
- numeric claims match the cited fact value
- quoted or paraphrased claims are supported by cited chunks
- Weekly News Focus and AI-analysis claims cite recent-event sources or canonical facts
- comparison claims can cite both sides through `comparison_left` and `comparison_right` citation roles
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
compare_route_redirect
weekly_news_focus
news_analysis
glossary
valuation_context
suitability_education
personalized_advice
unsupported_asset
out_of_scope_asset
unknown
```

### 13.2 Advice boundary

Blocked or redirected user intents:

- "Should I buy this?"
- "How much should I put in this?"
- "Is this guaranteed to go up?"
- "Give me a price target."
- "Build my portfolio."
- "Is this right for my taxes?"

Safe replacement behavior:

```text
I can't tell you whether to buy it or how much to allocate.
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
- redirect second-ticker comparison questions from single-asset chat to the comparison workflow

### 13.4 Prompt-injection and source defenses

Retrieved source text is untrusted evidence. Prompt templates must instruct the model to ignore instructions inside retrieved documents, and retrieved chunks must never override system prompts, developer prompts, source policy, citation policy, output schemas, or safety guardrails.

The generation pipeline must:

- wrap retrieved evidence in an explicit untrusted-evidence boundary
- pass only source IDs, metadata, and sanitized text excerpts to the model
- run citation validation after generation
- block advice-like output even if source text contains promotional language
- sanitize external HTML and PDF content before rendering
- reject unsafe redirects, localhost targets, private IP ranges, suspicious protocols, and non-allowlisted domains in ingestion fetchers

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

Allowed `status` values are `supported`, `unsupported`, `out_of_scope`, `pending_ingestion`, `partial`, `stale`, and `unavailable`.

### 14.2 Citation resolution

#### Request

```http
GET /api/citations/cit_abc123
```

#### Response

```json
{
  "citation_id": "cit_abc123",
  "source_document_id": "src_sec_0000320193_10k_2025",
  "source_title": "Apple Inc. 2025 Form 10-K",
  "publisher": "SEC EDGAR",
  "url": "https://www.sec.gov/...",
  "source_type": "10-k",
  "source_use_policy": "full_text_allowed",
  "published_at": "2025-10-31",
  "as_of_date": "2025-09-27",
  "retrieved_at": "2026-04-22T13:00:00Z",
  "freshness_state": "fresh",
  "claim_role": "canonical_fact",
  "allowed_supporting_excerpt": "Short excerpt allowed by source-use policy."
}
```

`citation_id` is public and opaque. It must not expose raw database row IDs. Citation resolution must never return unrestricted provider payloads, full restricted article text, private raw PDF text, secrets, hidden prompts, or unrestricted raw source text.

### 14.3 Asset overview

#### Request

```http
GET /api/assets/VOO/overview?section=beginner
```

#### Response

```json
{
  "asset": {
    "ticker": "VOO",
    "name": "Vanguard S&P 500 ETF",
    "asset_type": "etf",
    "status": "partial"
  },
  "section_states": {
    "snapshot": {"evidence_state": "complete", "freshness_state": "fresh"},
    "holdings": {"evidence_state": "partial", "freshness_state": "stale"},
    "weekly_news_focus": {"evidence_state": "complete", "freshness_state": "fresh"}
  },
  "freshness": {
    "page_last_updated_at": "2026-04-19T14:30:00Z",
    "facts_as_of": "2026-04-18",
    "holdings_as_of": "2026-04-17",
    "weekly_news_as_of": "2026-04-22"
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
  "weekly_news_focus": {
    "news_window_start": "2026-04-13",
    "news_window_end": "2026-04-21",
    "window": {
      "previous_market_week": {"start": "2026-04-13", "end": "2026-04-19"},
      "current_week_to_date": {"start": "2026-04-20", "end": "2026-04-21"},
      "timezone": "America/New_York"
    },
    "freshness": {"checked_at": "2026-04-22T14:30:00Z"},
    "items": [
      {
        "source": "Issuer press release",
        "title": "Example weekly item title",
        "published_at": "2026-04-17T12:00:00Z",
        "summary": "One-sentence beginner-friendly explanation of why this item matters.",
        "event_type": "sponsor_update",
        "period_bucket": "previous_market_week",
        "citation_ids": ["c_news_1"],
        "source_quality": "official",
        "allowlist_status": "allowed",
        "source_use_policy": "summary_allowed"
      }
    ]
  },
  "ai_comprehensive_analysis": {
    "what_changed_this_week": {
      "analysis": "Compact cited summary of the main changes in the Weekly News Focus pack.",
      "bullets": ["One concise cited change."],
      "citation_ids": ["c_news_1"],
      "uncertainty": []
    },
    "sections": [
      {
        "label": "Market Context",
        "analysis": "Compact cited synthesis of market-relevant Weekly News Focus.",
        "bullets": ["One concise implication for understanding the asset."],
        "citation_ids": ["c_news_1"],
        "uncertainty": []
      },
      {
        "label": "Business/Fund Context",
        "analysis": "Compact cited synthesis of asset fundamentals or ETF exposure context.",
        "bullets": ["One concise implication for the business or fund structure."],
        "citation_ids": ["c_news_1"],
        "uncertainty": []
      },
      {
        "label": "Risk Context",
        "analysis": "Compact cited synthesis of risk signals in the Weekly News Focus pack.",
        "bullets": ["One concise risk consideration."],
        "citation_ids": ["c_news_1"],
        "uncertainty": []
      }
    ]
  },
  "citations": [],
  "source_documents": []
}
```

### 14.4 Compare

#### Request

```http
POST /api/compare
```

```json
{
  "left_ticker": "VOO",
  "right_ticker": "QQQ",
  "section": "beginner"
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

### 14.5 Asset chat

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
  "conversation_id": "generated-random-id",
  "expires_at": "2026-04-29T14:30:00Z",
  "direct_answer": "This question compares QQQ with VOO, so use the comparison workflow to keep both assets grounded in their own evidence packs.",
  "why_it_matters": "Single-asset chat only answers from the selected asset pack. A comparison page can load both assets, compute differences, and cite both source sets.",
  "answer_state": "complete",
  "reasoning_summary": "The answer is grounded in the selected asset pack and routed to comparison because a second ticker was detected.",
  "generation": {
    "tier": "mock",
    "cached": false,
    "attempt_count": 0
  },
  "citations": [],
  "uncertainty": [],
  "safety_classification": "compare_route_redirect",
  "compare_route_suggestion": {
    "left_ticker": "QQQ",
    "right_ticker": "VOO",
    "route": "/compare?left=QQQ&right=VOO"
  }
}
```

Accountless chat session behavior:

- If `conversation_id` is omitted, create a random anonymous session ID.
- Browser local storage keeps only `conversation_id`, ticker, `updated_at`, and `expires_at`.
- Server stores transcript state for grounded follow-up and client-requested export.
- Session TTL is 7 days from last activity.
- Deleting a transcript clears browser state and deletes or invalidates the server session.
- Rate limits apply per conversation. The MVP default is 20 chat requests per hour per conversation; IP-level chat and burst limits may be added later, but must remain environment-configurable.

### 14.6 Export

Export endpoints should return server-shaped educational outputs, not raw unrestricted provider payloads.

Supported MVP formats:

- `format=markdown`
- `format=json`

PDF export is post-MVP.

Supported MVP export shapes:

- asset page summary with citation IDs and freshness metadata
- Weekly News Focus and AI Comprehensive Analysis with citations, freshness metadata, and uncertainty labels
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
| `WeeklyNewsPanel` | Weekly News Focus after stable facts and before AI Comprehensive Analysis, separated from basics. |
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
- whether the citation supports a Weekly News Focus item or an AI Comprehensive Analysis claim

### 15.3 Freshness display

Every page should show:

```text
Page last updated: Apr 19, 2026
Holdings as of: Apr 17, 2026
Weekly News Focus checked: Apr 19, 2026
```

Freshness should be section-specific, not just page-level.

Quote/reference display must include source and freshness metadata. MVP quote data is delayed or best-effort; if a quote or quote timestamp is unavailable, the API should return `unavailable` and the UI should say so rather than implying real-time coverage.

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
  + weekly_news_event_ids
  + prompt_version
  + model_name
)
```

If any input changes, regenerate the affected summary.

Cache keys should include the asset or comparison pack, section, source freshness state, prompt version where generation is involved, and schema version. Cached outputs must preserve citation IDs, source metadata, section-level freshness, and stale/unknown/unavailable labels.

### 16.2 Suggested refresh rules

| Data type | Refresh cadence | Invalidation trigger |
|---|---:|---|
| SEC submissions | daily + on-demand | new filing detected |
| SEC XBRL facts | daily + on-demand | new 10-K / 10-Q / 8-K |
| Stock price/reference data | delayed or best-effort free-source/configured-adapter TTL | TTL expiration or unavailable quote state |
| ETF holdings | daily on market days | holdings date changes |
| ETF fact sheet | daily or weekly | checksum change |
| ETF prospectus | weekly or monthly | checksum change |
| Weekly News Focus events | 1-6 hours where sources permit | new high-signal event or source checksum change |
| LLM summaries | on input hash change | freshness hash mismatch |

For v1, the Weekly News Focus cadence applies only to official sources and curated allowlisted free/RSS/news sources. Unrecognized free-news sources are rejected by default.

Weekly News Focus and AI Comprehensive Analysis should use the same freshness rules. The UI should expose `news_window_start`, `news_window_end`, and the checked timestamp for the Weekly News Focus pack.

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
| On-demand asset ingestion | async job; page should show `pending_ingestion` state |
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
- Weekly News Focus render rate
- AI news analysis validation failure rate

These trust and comprehension metrics are directly aligned with the proposal's recommendation to measure citation coverage, unsupported claim rate, comparison usage, glossary usage, freshness accuracy, and user understanding.

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
  "weekly_news_event_ids": [],
  "news_window_start": "2026-04-13",
  "news_window_end": "2026-04-21",
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
- deterministic asset classification for leverage, inverse funds, non-equity funds, active strategy, and top-500 stock scope
- status mapping for `supported`, `unsupported`, `out_of_scope`, `pending_ingestion`, `partial`, `stale`, and `unavailable`
- export format validation for Markdown and JSON
- Weekly News Focus market-week window calculation
- rate-limit defaults for search, chat, and ingestion
- delayed, best-effort, stale, partial, and unavailable quote/reference states
- `claim_citations` role validation
- fact and summary versioning state transitions
- chat session TTL and deletion state

### 19.2 Integration tests

- SEC submissions ingestion
- SEC XBRL ingestion
- issuer fact sheet parsing
- ETF holdings parsing
- hybrid-light retrieval
- asset overview endpoint
- comparison endpoint
- chat endpoint
- chat compare-route redirect
- allowlisted Weekly News Focus event ingestion and rejection of unrecognized news sources
- Weekly News Focus selection with 5-8 items when enough high-quality evidence exists
- AI Comprehensive Analysis generation from the selected asset's Weekly News Focus pack
- Markdown and JSON export endpoints
- source-use policy enforcement for metadata-only, link-only, summary-allowed, full-text-allowed, and rejected sources
- prompt-injection rejection from retrieved source text
- HTML/PDF sanitization and SSRF-defense checks
- accountless chat continuation, expiry, deletion, and rate limiting

### 19.3 Golden asset tests

Use the launch pre-cache universe as the golden asset set:

```text
Broad ETFs: VOO, SPY, VTI, IVV, QQQ, IWM, DIA
Sector/theme ETFs: VGT, XLK, SOXX, SMH, XLF, XLV, XLE
Large stocks: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, BRK.B, JPM, UNH
Comparison pairs: VOO/SPY, VTI/VOO, QQQ/VOO, QQQ/VGT, VGT/SOXX, AAPL/MSFT, NVDA/SOXX
```

For each golden asset, maintain expected checks:

- correct asset type
- correct canonical name
- top risks have exactly 3 items
- ETF holdings table exists
- stock financial trend table exists
- citations exist for key claims
- no buy/sell language appears
- Weekly News Focus and AI Comprehensive Analysis are separate from asset basics
- Weekly News Focus renders for `AAPL`, `VOO`, and `QQQ` when allowlisted evidence exists
- Weekly News Focus shows 5-8 items when enough high-quality items exist, fewer when evidence is limited, and zero when no major Weekly News Focus items exist
- Weekly News Focus uses last Monday-Sunday plus current week-to-date through yesterday
- AI Comprehensive Analysis includes What Changed This Week, Market Context, Business/Fund Context, and Risk Context sections when at least two high-signal items exist
- every AI-analysis factual claim has citations or an uncertainty label
- duplicate, promotional, irrelevant, non-allowlisted, and license-disallowed news is excluded
- QQQ vs VOO opens comparison, while the same question inside single-asset chat returns a compare redirect
- NVDA vs SOXX uses the stock-vs-ETF template and explains structural differences
- missing ETF holdings or stale sources produce partial-page states
- leveraged ETF, inverse ETF, ETN, fixed income ETF, and crypto searches return unsupported or out-of-scope states
- free-news sources outside the allowlist are rejected
- anonymous chat sessions continue via `conversation_id`, expire after TTL, delete correctly, and never put raw transcript text in analytics
- claims can resolve multiple citations through `claim_citations`
- current fact queries use `is_current`, while superseded facts and summaries remain audit-readable
- Markdown and JSON exports include disclaimer, citations, freshness, and uncertainty metadata

### 19.4 LLM evaluation tests

Evaluate generated outputs for:

- schema validity
- citation coverage
- citation support
- beginner readability
- no personalized advice
- no buy/sell/hold language
- no allocation, tax, guaranteed-return, or unsupported price-target language
- no unsupported price targets
- correct separation of stable facts from Weekly News Focus and AI Comprehensive Analysis
- AI Comprehensive Analysis uses only selected Weekly News Focus items and cited canonical facts
- OpenRouter free-stage requests use `models` in the configured order, paid fallback requests use `model=deepseek/deepseek-v3.2`, and only validated outputs are cached
- raw `reasoning_details`, hidden prompts, failed raw responses, and unrestricted source text are never persisted or returned; only cited `reasoning_summary` may appear in public responses
- section labels remain UI labels and are not framed as real people, advisors, or independent sources
- retrieved source text is treated as untrusted evidence and cannot alter instructions or safety policy

Strict MVP gates:

- 100% of important factual claims in golden-path generated outputs have valid citations or explicit uncertainty/unavailable labels.
- Zero known advice-boundary violations in golden tests.
- CI includes unit, integration, schema, citation validation, safety, export, and golden asset tests.

---

## 20. Security and data governance

### 20.1 Secrets

Store API keys in a secret manager or environment-managed deployment secret store.

For the planned free-tier deployment, use Google Secret Manager for Cloud Run and Cloud Run Jobs secrets. For local live provider testing, the developer's WSL Bash environment may provide `OPENROUTER_API_KEY`, `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FINNHUB_API_KEY`, `TIINGO_API_KEY`, and `EODHD_API_KEY`; processes that need them should be launched from that WSL environment. Do not inspect, echo, log, or copy actual values.

Do not expose:

- market data provider keys
- news provider keys
- LLM provider keys
- object storage credentials
- admin ingestion endpoints

Do not commit filled production env files. `deploy/env/*.example.env`, `apps/web/.env.production.example`, and `.env.example` may contain placeholders only.

FMP, Alpha Vantage, Finnhub, Tiingo, and EODHD keys are configuration readiness only. Live adapters and public display/export use require provider-specific licensing and rate-limit review.

### 20.2 Source sanitization

External HTML and PDF content should be sanitized before display. Never render arbitrary source HTML directly in the app. Sanitization should remove scripts, event handlers, unsafe links, embedded active content, and hidden prompt-like instructions from rendered views.

Ingestion fetchers must use allowlisted domains or controlled URL resolution. They should reject unsafe redirects, localhost targets, private IP ranges, non-HTTP(S) protocols, and suspicious content types to reduce SSRF risk.

### 20.3 User data

MVP should be accountless. Users can download asset summaries, comparison output, source lists, and chat transcripts without creating accounts. These exports should be Markdown or JSON and include citations, freshness metadata, uncertainty labels, and the educational disclaimer. They should omit or summarize restricted provider content unless redistribution rights are confirmed.

Accountless chat uses anonymous random conversation IDs, not user accounts. The browser stores only `conversation_id`, asset ticker, `updated_at`, and `expires_at`; the server stores transcript state for follow-up grounding and client-requested export. Chat sessions expire 7 days after last activity. A user delete action must clear the local browser reference and delete or invalidate the server-side session.

Chat transcripts are not included in product analytics, not used for model training, and not used for model evaluation in MVP. Product analytics may log only aggregate events such as chat started, follow-up count, safety redirect, compare redirect, export requested, latency, and error state. IP address and user-agent logs may be retained only in short-lived abuse/security logs with a 7-day default retention.

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

### 21.1 Local MVP stack

Local development should use Docker Compose with:

- Next.js web app
- FastAPI API
- ingestion worker
- PostgreSQL with pgvector enabled
- Redis
- S3-compatible object storage such as MinIO

### 21.2 Recommended MVP deployment

| Component | Suggested deployment |
|---|---|
| Frontend | Vercel Hobby project rooted at `apps/web` |
| API | Google Cloud Run in `us-central1`, request-based billing, `min-instances=0`, conservative max instances |
| Worker | Cloud Run Jobs, manually triggered first |
| Database | Neon Free Postgres with pooled SSL connection URL and pgvector enabled when needed |
| Cache / queue | No production Redis or Pub/Sub at first; use Postgres `ingestion_jobs` |
| Object storage | Private Google Cloud Storage regional bucket in `us-central1` |
| Monitoring | Google Cloud Logging and Error Reporting; optional Sentry Developer plan later |
| LLM runtime | Feature-flagged explicit OpenRouter free-model chain with automatic DeepSeek V3.2 paid fallback for first deployment; deterministic mock for CI/local tests |
| CI/CD | GitHub Actions quality gates first; manual deploy commands before deploy automation |

Cloud Run API requirements:

- Container must listen on Cloud Run's `PORT` environment variable, with local fallback to `8000`.
- `CORS_ALLOWED_ORIGINS` must list the Vercel production URL and any allowed preview URLs.
- Secrets such as `DATABASE_URL`, `OPENROUTER_API_KEY`, and storage credentials must come from Secret Manager or deployment-managed secrets.
- Billing guardrails should include a budget alert, `min-instances=0`, and a conservative max-instance limit.

Cloud Run Jobs requirements:

- Use the same API/worker image family and production env settings where possible.
- Use the Postgres `ingestion_jobs` table as the job ledger and queue for v1.
- Add Cloud Scheduler later only after manual job execution is reliable and recurring ingestion is needed.

Storage requirements:

- Production source snapshots and generated artifacts should use private GCS object URIs.
- Suggested object key families: `raw/`, `parsed/`, `generated/`, and `diagnostics/`.
- Do not make source snapshots public.

OpenRouter requirements:

- Keep the key server-side in `OPENROUTER_API_KEY`.
- First deployment uses `OPENROUTER_FREE_MODEL_ORDER` plus `OPENROUTER_PAID_FALLBACK_MODEL=deepseek/deepseek-v3.2`; use env configuration rather than hard-coding it in application code.
- Require `LLM_LIVE_GENERATION_ENABLED=true` before making live model calls.
- Capture selected model, tier, usage/cost metadata, latency, validation result, and attempt count where available without logging raw chat transcripts.
- Keep deterministic mocks for CI and tests.
- Run one repair retry after free-model validation failure, then use DeepSeek fallback automatically. Fall back to partial/unavailable generated sections when all attempts fail schema/citation/safety validation.
- Never store or show raw model reasoning; expose only cited `reasoning_summary`.

### 21.3 Environments

```text
local
staging
production
```

### 21.4 CI/CD checks

Before deploy:

- type checks
- unit tests
- API schema tests
- DB migration tests
- parser tests
- sample LLM schema validation
- Weekly News Focus schema validation
- AI Comprehensive Analysis schema validation
- citation validation tests
- safety guardrail tests
- Markdown/JSON export tests
- golden asset tests
- documentation hygiene scan for double-question-mark mojibake, private-use corruption, stale AI labels, duplicate PRD requirement IDs, and stale weekly-window wording
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
| News provider returns noisy results | Bad Weekly News Focus items | Importance scoring, source allowlist, source-use policy, deduplication. |
| Stale holdings | Misleading ETF page | Holdings freshness label and stale warning. |
| Market data outage | Missing prices/valuation | Show delayed, best-effort, stale, partial, or unavailable state; do not block educational page. |
| User asks for advice | Compliance/trust issue | Safety classifier and educational redirect. |

---

## 23. Phased implementation plan

These phases describe implementation order only. Full MVP remains the v1 target and is not ready until the complete acceptance checklist and strict quality gates pass.

### Phase 0: Foundation

- Create repo structure.
- Set up Docker Compose for Next.js, FastAPI, PostgreSQL with pgvector, Redis, and S3-compatible object storage.
- Set up Next.js app.
- Set up FastAPI service.
- Define Pydantic schemas.
- Add migrations.
- Build LLM provider abstraction with deterministic test mocks.
- Build source-document storage.

### Phase 1: Stock and ETF asset pages

- Implement search.
- Implement asset resolution.
- Implement stock ingestion from SEC.
- Implement equity ETF ingestion from issuer and free-first sources.
- Implement source documents and chunks.
- Implement normalized facts.
- Implement beginner asset overview.
- Implement Weekly News Focus and AI Comprehensive Analysis.
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

- Add Markdown/JSON export/download flows for asset pages, comparisons, source lists, and chat transcripts.
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
- Unsupported and out-of-scope assets return clear blocked states.
- Stock pages render from normalized SEC and reference data.
- Equity ETF pages render from official issuer and free-first evidence where available.
- Partial pages render verified sections only and label missing evidence as unavailable, stale, unknown, or partial.
- Every page shows freshness labels.
- Every important claim has a citation or uncertainty note.
- Source drawer displays source metadata and supporting passages.
- Top risks show exactly three items first.
- Weekly News Focus and AI Comprehensive Analysis are stored and rendered separately from canonical facts.
- Weekly News Focus returns 5-8 items when enough high-quality allowlisted evidence exists, fewer when evidence is limited, and zero with a clear empty state when no major Weekly News Focus items exist.
- Weekly News Focus uses the last completed Monday-Sunday market week plus current week-to-date through yesterday.
- AI Comprehensive Analysis includes What Changed This Week, Market Context, Business/Fund Context, and Risk Context when at least two high-signal weekly items exist.
- Comparison works for ETF-vs-ETF, stock-vs-stock, and stock-vs-ETF.
- Chat answers only from the selected asset knowledge pack.
- Single-asset chat redirects second-ticker comparison questions to the comparison workflow.
- Safety guardrails prevent buy/sell, price-target, and allocation advice.
- Prompt-injection defenses treat retrieved text as untrusted evidence and ignore instructions inside retrieved documents.
- Source sanitization and SSRF defenses are covered for HTML/PDF rendering and ingestion fetchers.
- Accountless chat uses anonymous conversation IDs, 7-day TTL, deletion, minimal local storage, and no raw transcript analytics/training/evaluation use in MVP.
- Users can export asset pages, comparison output, source lists, and chat transcripts as Markdown or JSON with citations, freshness metadata, uncertainty labels, and the educational disclaimer.
- Hybrid glossary support covers core beginner terms and does not introduce uncited asset-specific facts.
- Shared server-side caching, source checksums, and freshness hashes avoid repeated provider and LLM work while preserving freshness labels.
- Citation coverage, unsupported claim rate, latency, glossary usage, export usage, safety redirects, and freshness accuracy are logged.
- 100% of important factual claims in golden-path generated outputs have valid citations or explicit uncertainty/unavailable labels.
- Zero known advice-boundary violations remain in golden tests.
- CI includes unit, integration, schema, citation validation, safety, export, and golden asset tests.
- CI covers many-citation claims, fact/summary versioning, chat privacy, rate limits, and `NVDA` vs `SOXX` stock-vs-ETF comparison.
- Cached search, asset pages, comparison pages, source drawer, and chat meet the performance targets in this spec.

---

## 25. Resolved MVP planning assumptions

1. Market/reference data should use free-first official and public sources first. No paid provider keys are assumed for v1; paid market, ETF, or news providers are optional future adapters after validation and licensing review.
2. MVP should pre-cache a top-500-first high-demand launch universe from `data/universes/us_common_stocks_top500.current.json`, mirror it through `TOP500_UNIVERSE_MANIFEST_URI`, and support explicit `pending_ingestion` states only for approved eligible supported assets outside it.
3. Retrieval should remain keyword/metadata first so citation binding, source freshness, and asset filters stay under application control. Embeddings and pgvector retrieval are optional behind adapters until stable.
4. Citation strictness is per important factual claim, not per sentence.
5. Weekly News Focus should prefer official filings, company investor-relations releases, ETF issuer announcements, prospectus updates, and fact-sheet changes before curated allowlisted free/RSS/news sources; Reuters/AP-style sources require source-use rights review.
6. V1 should be accountless, with anonymous chat sessions, 7-day TTL, user deletion, minimal browser storage, and no raw chat transcript analytics/training/evaluation use in MVP.
7. Markdown/JSON export/download is the v1 save-for-later workflow; exported output must include citations, freshness metadata, uncertainty labels, and the educational disclaimer while respecting provider licensing.
8. Server-side caching, source-document checksums, generated-summary freshness hashes, and pre-cached knowledge packs should reduce provider and LLM calls.
9. ETF issuer parser maintenance remains an implementation risk; parsers should store raw snapshots, checksums, and parser diagnostics.
10. Leveraged ETFs, inverse ETFs, ETNs, fixed income ETFs, commodity ETFs, active ETFs, multi-asset ETFs, crypto, options, international equities, preferred stocks, warrants, rights, and complex products are unsupported or out of scope for generated pages, chat, and comparisons unless explicitly added later.
11. Local implementation should start with Docker Compose for Next.js, FastAPI, PostgreSQL with pgvector, Redis, and S3-compatible object storage.
12. LLM integration should be adapter-first with deterministic mocks for tests and a feature-flagged explicit OpenRouter free-model chain plus automatic DeepSeek V3.2 paid fallback for the first live deployment.
13. Weekly News Focus is an asset-page feature with a fixed Monday-Sunday market-week window plus current week-to-date through yesterday; it is not a separate market brief page.
14. Source allowlist changes use config-only review with validation and a development-log rationale; scoring never auto-approves a new source.
15. Raw source text storage is rights-tiered across official, full-text-allowed, summary-allowed, metadata-only, link-only, and rejected sources.
16. V1 is English-first. Traditional Chinese localization and read-aloud/TTS are post-MVP.

---

## 26. Technical thesis

The strongest architecture is a **source-first retrieval and generation system**, not a generic finance chatbot.

The system should:

- ingest official and structured sources
- normalize facts
- preserve source documents and chunks
- generate beginner explanations from bounded evidence
- validate citations before display
- separate Weekly News Focus context and AI analysis from stable facts
- avoid personalized investment advice
- expose freshness and uncertainty directly in the UI

That design matches the proposal's central idea: a financial learning product with beginner language, visible citations, comparison-first workflows, Weekly News Focus context separation, and asset-specific grounded chat.
