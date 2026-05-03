# SPEC.md

## Product Success

Learn the Ticker helps beginners understand U.S.-listed common stocks and manifest-approved ETF-500 scope U.S.-listed passive/index-based U.S. equity ETFs through plain-English, source-backed explanations.

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

- top-500-first U.S.-listed common stocks from `data/universes/us_common_stocks_top500.current.json` as the strict/audit-quality seed, plus source-labeled SEC/exchange/provider fallback for the personal lightweight MVP
- manifest-approved ETF-500 scope as the strict/audit-quality target, plus source-labeled lightweight rendering for recognized U.S.-listed, active, non-leveraged, non-inverse ETF pages when official automation or reputable provider fallback supplies enough normalized facts
- pre-cached high-demand stocks and ETF-500 entries for reliability and latency, without treating the pre-cache set as the ETF coverage ceiling
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

- backend contracts exist for search, overview/details, Weekly News Focus, AI Comprehensive Analysis, comparison, grounded chat, glossary, exports, ingestion states, provider adapters, trust metrics, generated-output cache writes, local durable repository reads/writes, and LLM runtime diagnostics
- frontend routes and components exist for home search, API-backed asset pages with deterministic fallback, comparison, chat, source metadata, glossary, and export controls
- local frontend/API plumbing exists for MVP smoke testing: browser helpers prefer the configured FastAPI base URL, the Next app can rewrite `/api/:path*` to the local backend, and FastAPI CORS is wired from `CORS_ALLOWED_ORIGINS`
- local durable repository execution has in-memory fallback, configured reader boundaries, and optional browser/API smoke coverage, but normal CI remains fixture-backed
- v0.5 ETF manifest split contracts are implemented: supported ETF generated-output coverage reads `data/universes/us_equity_etfs_supported.current.json`, while recognition-only blocked states read `data/universes/us_etp_recognition.current.json`; the legacy combined ETF fixture remains only for repo continuity
- repo-native source-handoff manifest tooling, governed golden API/frontend rendering proof, launch-manifest review packets, and the deterministic local fresh-data MVP rehearsal command are implemented as review-only/operator-safe layers
- opt-in official-source acquisition readiness exists for SEC stock, ETF issuer, and Weekly News golden paths, and the lightweight fresh-data fetch path now exposes `/api/assets/{ticker}/fresh-data` plus `scripts/run_lightweight_data_fetch_smoke.py` for local stock/ETF fetch validation; launch-sized governed source artifacts and ETF-500 source-pack approvals remain audit-quality hardening gaps
- v0.6 local validation expects operator-only live-AI review for grounded chat and AI Comprehensive Analysis when evidence thresholds are met, while CI and ordinary local tests remain deterministic mocks
- CI and local checks are deterministic and fixture-backed; normal quality gates do not depend on live provider, market-data, news, or LLM calls
- the local manual fresh-data readiness gate is review-only and reports `agent_work_remaining` until deterministic ETF-500 candidate review, ETF issuer source-pack planning, Top-500 SEC source-pack planning, local MVP thresholds, ingestion priority planning, governed golden rendering, frontend workflow markers, parser readiness, Golden Asset Source Handoff readiness, freshness/as-of metadata, and checksums are ready; it reports `manual_test_ready` only when the next action is explicit operator-run browser/API, durable repository, official-source retrieval, or live-AI validation, without starting services, fetching live sources, approving sources, promoting manifests, exposing secrets, or unlocking generated output

Near-term implementation priority order:

1. preserve the deterministic launch-readiness regression layer for search, support states, asset pages, comparison, source drawer, contextual glossary, grounded chat, exports, Weekly News Focus, AI Comprehensive Analysis, and mobile workflow markers
2. preserve the implemented v0.5 ETF manifest split so strict supported ETF generated-output coverage stays separate from ETF/ETP recognition-only blocked search states, while lightweight local fetches can show source-labeled partial data for in-scope ETFs
3. preserve Golden Asset Source Handoff enforcement for strict/audit-quality promotion across source allowlist records, source snapshots, knowledge packs, citations, generated-output cache entries, source drawer output, and exports
4. preserve the reviewed Top-500 candidate-manifest refresh workflow that uses official IWB holdings first, official SPY/IVV/VOO holdings only as fallback inputs, SEC/Nasdaq validation, checksums, and a diff report before current-manifest promotion
5. preserve optional browser E2E and local durable smoke for golden assets using the API-base/proxy/CORS path before production deployment work
6. expand ETF eligible-universe review outputs from the current fixture-sized packet into category, exclusion, source-pack, and generated-output eligibility packets for the ETF-500 reviewed local MVP scope
7. add stock and ETF source-pack readiness packets that prove SEC core stock evidence and issuer ETF evidence can unlock only source-backed sections with deterministic partial/failure states
8. add batchable, resumable local ingestion planning so high-demand assets run first, then supported ETFs and top-500 stocks by review priority, while normal CI remains deterministic
9. defer production deployment hardening, recurring jobs, broad paid-provider integrations, and post-MVP features until the local fresh-data path passes strict quality gates

When choosing the next task, prefer improving PRD/TDS alignment of the current deterministic scaffold over adding new domains or speculative infrastructure.
The local agent-loop harness should default to `gpt-5.5` with `high` reasoning effort, while allowing explicit per-run overrides such as `gpt-5.3-codex-spark` when the operator requests it.

## Source And Freshness Rules

Stable facts must come from official or structured sources before model-written explanations.

Provider hierarchy for MVP planning:

- stock canonical facts: SEC EDGAR submissions, SEC XBRL company facts, SEC filings, then company investor relations
- ETF canonical facts: issuer pages, fact sheets, prospectuses, shareholder reports, holdings files, and exposure files
- structured enrichment: free-first reference data and optional provider adapters only where licensing, rate limits, caching, display, and export rights allow
- Weekly News Focus: official filings, investor-relations releases, issuer announcements, prospectus changes, fact-sheet changes, then approved reputable third-party/news sources where rights permit

Weekly News Focus must use the last completed Monday-Sunday market week plus current week-to-date through yesterday, using U.S. Eastern dates. It should show the configured maximum only when enough quality evidence exists, fewer items when evidence is limited, and a clear empty state when no major Weekly News Focus items exist.

AI Comprehensive Analysis must be suppressed unless at least two approved Weekly News Focus items exist. Approved reputable third-party items may count when source governance permits them and they are clearly labeled as third-party reporting. When present, the analysis starts with What Changed This Week, then Market Context, Business/Fund Context, and Risk Context. It must cite underlying Weekly News Focus items and canonical facts.

Source-use policy wins over scoring. Rejected or rights-disallowed sources must not display, summarize, cache, or export. Raw source text storage is rights-tiered across `full_text_allowed`, `summary_allowed`, `metadata_only`, `link_only`, and `rejected`.

Golden Asset Source Handoff is the approval layer between retrieval and strict/audit-quality evidence use. Fetching from SEC, issuer sites, ETF holdings files, APIs, or provider adapters does not approve strict evidence by itself. Before a source is promoted into governed evidence storage, generated-output cache entries, or audit-quality exports, it must have approved domain/source identity, source type, official-source status, storage rights, export rights, source-use policy, approval rationale, parser status, freshness/as-of metadata, and review status. In lightweight personal-MVP mode, source-labeled normalized facts may support local display and local smoke validation before full handoff approval when raw payloads remain hidden and partial/unavailable states are visible.

Top-500 stock coverage must be manifest-owned. The approved runtime manifest is `data/universes/us_common_stocks_top500.current.json`; monthly refresh work produces a candidate manifest and diff report before review. Official IWB holdings are the primary source input; official SPY, IVV, and VOO holdings are fallback inputs only. Live holdings or provider responses may inform candidates, but they must never become runtime coverage truth directly.

ETF strict/audit-quality coverage remains manifest-owned. The implemented v0.5 runtime authority for strict generated ETF output is `data/universes/us_equity_etfs_supported.current.json`; the recognition-only authority for blocked ETF/ETP search states is `data/universes/us_etp_recognition.current.json`. ETF-500 is the named audit-quality target. Lightweight local fetches may render partial educational data for recognized in-scope ETFs from manifest/scope signals and reputable provider fallback, but recognition rows, live listings, provider flags, and issuer search results must still block clearly unsupported complex products and unknown tickers.

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
- run Golden Asset Source Handoff before evidence storage, generation, citation, cache, or export use
- resolve top-500 stock support from the approved manifest rather than live runtime provider data
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
- Top-500 manifest and Golden Asset Source Handoff checks pass when coverage, ingestion, source policy, citations, caches, or exports are touched
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
- Top-500 candidate refreshes produce reviewed candidate files, source provenance, checksums, validation warnings, and diff reports before promotion
- ETF-500 supported ETF scope is driven by the supported ETF manifest, while ETF/ETP recognition rows remain blocked from generated pages, chat, comparisons, Weekly News Focus, AI Comprehensive Analysis, and exports
- Golden Asset Source Handoff blocks unapproved, unclear-rights, parser-invalid, hidden/internal, pending-review, and rejected sources from evidence storage, generation, citation, cache, and export paths
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
