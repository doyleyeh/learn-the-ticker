# EVALS.md

## Main Quality Gate

Run for every task:

```bash
bash scripts/run_quality_gate.sh
```

The quality gate must stay deterministic. Normal CI must not require live provider, news, market-data, or LLM calls.

## Task-Specific Checks

When a task spans multiple categories, run every relevant focused check plus the main quality gate.

### Frontend UI And `apps/web` Tasks

Use for asset pages, comparison pages, citation chips, source drawer, freshness labels, glossary UI, export controls, chat UI, responsive layout, and frontend workspace moves.

Required checks:

```bash
npm test
npm run typecheck
npm run build
bash scripts/run_quality_gate.sh
```

Verify:

- root npm scripts delegate to `apps/web`
- `apps/web` scripts work from the workspace
- home page has one primary action: search for a single supported stock or ETF
- home page does not present comparison or glossary as the primary MVP workflow
- clear `A vs B` home-search patterns redirect to the comparison workflow instead of producing a multi-asset home result
- search/autocomplete rows show stock vs ETF identity, exchange or issuer, and support-state chips
- exact unsupported tickers and no-match searches show distinct blocked/no-result states
- citation chips remain visible near supported claims
- source drawer/source metadata exposes title, type, publisher, URL, dates, freshness, source-use policy where available, related claim, and allowed supporting excerpt
- source drawer supports desktop drawer behavior and mobile bottom-sheet behavior
- freshness, stale, unknown, unavailable, partial, and insufficient-evidence states are visible where relevant
- asset pages visibly distinguish backend/API timeout, invalid-contract, unavailable, and no-API-base fallback states from verified `no_high_signal` or empty Weekly News Focus states
- supported asset pages show a progressive loading shell or section-local loading placeholders for normal slow backend responses instead of the old whole-page temporary-unavailable state
- supported asset stable-overview mode does not wait on live LLM generation before rendering source-labeled facts; live-generation provenance belongs inline with the generated section
- asset pages show section-state notices inside their owning sections and do not render orphan status notes between panels
- asset pages do not render redundant standalone Glossary context, Economic Indicators, Asset details, or Source drawer status panels
- repeated freshness/as-of/retrieved/provider/source-use metadata is available through compact section or row source icons instead of repeated visible tags
- Economic Indicators keeps one visible section and folds period/as-of/retrieved row metadata into the Source column's source icon instead of a standalone `Period / as of` column
- source-labeled lightweight local evidence is not shown as a page-level fallback card, while deterministic fixture or backend-failure content remains labeled where displayed
- Beginner Summary, Deep Dive summaries, Market AI, and ticker AI expose inline generation-state notes for live generation, deterministic fallback, timeout fallback, insufficient evidence, or backend error
- Economic Indicators appears as one visible section with inline live/imported/fixture source-state copy
- beginner copy avoids buy/sell/hold, allocation, price-target, tax, and brokerage language
- Market News Focus, ticker-specific Weekly News Focus, and AI Comprehensive Analysis remain visually separate from stable facts and from each other
- contextual glossary supports desktop hover/click/focus popovers and mobile tap bottom-sheet behavior
- asset-specific chat remains a helper feature and supports mobile bottom-sheet or full-screen behavior
- frontend chat, export, and comparison calls use the configured backend API base or a documented Next `/api` proxy instead of silently relying on missing Next API routes
- comparison UI covers empty, one-side-selected, two-side-selected, partial, pending, unsupported, and out-of-scope states
- stock-vs-ETF comparison uses relationship badges and the special single-company-vs-ETF-basket structure
- mobile and desktop layouts keep Beginner section, source access, glossary, chat, and comparison flows usable

### Backend API, Schema, Retrieval, And Comparison Tasks

Use for FastAPI routes, response models, retrieval fixtures, comparison generation, overview generation, source metadata, data-contract changes, and knowledge-pack behavior.

Required checks:

```bash
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Also run a focused pytest slice for the changed module when one exists, for example:

```bash
python3 -m pytest tests/unit/test_retrieval_fixtures.py tests/unit/test_overview_generation.py -q
```

Verify:

- schema validation covers supported, unsupported, out-of-scope, pending-ingestion, partial, stale, unknown, unavailable, and insufficient-evidence states
- generated citations bind only to same-asset or same-comparison-pack evidence
- unsupported and out-of-scope assets are blocked from generated pages, generated chat, and generated comparisons
- normal CI uses local fixtures or mocks, not live external calls
- browser-facing direct backend calls are allowed only when FastAPI CORS is wired from explicit local/deployment origins

### Citation, Safety, Summaries, Suitability, And Chat Tasks

Use for citation validation, generated summaries, AI Comprehensive Analysis, grounded chat, suitability text, and advice-boundary copy.

Required checks:

```bash
python3 -m pytest tests/unit/test_safety_guardrails.py -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Verify:

- important factual claims have citations or explicit uncertainty
- Weekly News Focus and AI Comprehensive Analysis claims cite the correct evidence layer
- generated Beginner Summary, Deep Dive, Market AI, and ticker AI use curated `generation_context` instead of raw provider payloads
- generated-section diagnostics do not mask deterministic or timeout fallback as plain success; fallback analysis renders as partial and insufficient-evidence suppression is distinct from backend failure
- Beginner Summary explains the asset in plain English and does not depend on quote, chart, volume, price, or technical-indicator facts unless required for identity
- generated copy does not include internal or low-value wording such as fixtures, local MVP, available evidence, provider market-reference, raw provider keys like `regularMarketPrice`, or "this section uses..." phrasing
- Market AI synthesizes selected Market News Focus items with Economic Indicators and allowed numeric facts instead of only counting topic buckets or repeating headlines
- ticker AI connects selected Weekly News to the asset profile, holdings/exposure, market context, and technical context only when those inputs are supplied and validated
- stale sources are labeled stale or suppressed according to section behavior
- advice-like prompts redirect into educational framing before LLM calls
- no output tells the user to buy, sell, hold, allocate, trade, use a broker, rely on tax advice, or accept a price target
- chat remains grounded in the selected asset knowledge pack and does not use raw transcript text in analytics/training/evaluation

### Weekly News Focus And Source-Use Tasks

Use for market-week window logic, reusable Market News Focus, ticker-specific recent events, Economic Indicators, Codex-assisted analysis pack imports, source allowlists, Golden Asset Source Handoff, source-use policies, raw text policy, news/event scoring, and AI Comprehensive Analysis inputs.

Required checks:

```bash
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Verify:

- Golden Asset Source Handoff treats fetching as retrieval only, not approval
- evidence use requires approved domain/source identity, source type, official-source status, storage rights, export rights, source-use policy, rationale, parser status, freshness/as-of metadata, and review status
- unapproved, not-allowlisted, unclear-rights, parser-invalid, hidden/internal, pending-review, rejected, duplicate, promotional, irrelevant, and rights-disallowed sources cannot feed evidence storage, generation, citation, cache, export, Weekly News Focus, or AI Comprehensive Analysis
- Weekly News Focus uses the last completed Monday-Sunday market week plus current week-to-date through yesterday in U.S. Eastern dates
- Market News Focus uses the same market-week window, selects up to 20 approved story clusters, preserves topic bucket metadata, and never pads weak evidence to hit 20
- Market News Focus selection demotes low-relevance market items, opinion/pundit pieces, duplicate headlines, and demoted publishers unless they have a clear U.S. market relevance hook
- Market News Focus and AI Comprehensive Analysis: Market News Focus are reusable across supported ticker pages without regenerating per ticker
- `economic-indicators-pack-v1` is U.S.-only, cited, source-labeled, rights-safe, and rendered after stable asset facts but before Market News Focus
- `analysis-pack-import-bundle-v1` validates schema, freshness, checksums, citations/source IDs, source-use policy, no raw article/provider payload storage, no secret exposure, and no visible persona labels
- analysis-pack local operator CLIs default to live mode outside CI/tests/evals/quality gates, `--deterministic` forces fixture/no-live behavior, computed technical indicators come from source-labeled OHLCV metadata, durable imported bundles are written only through backend-owned storage, and normal CI remains deterministic
- file-backed analysis-pack imports append safe JSONL import history with bundle ID, timestamps, checksum, validation status, reason codes, source mode, included tickers, and optional operator label
- `ai_context.json` contains selected market stories, ticker Weekly News items, Economic Indicators, technical indicators, canonical fact citation IDs, source IDs, and allowed numeric facts
- numeric validation rejects unsupported generated numeric claims and technical field misuse such as treating ADX or volume as price
- `/api/economic-indicators`, `/api/market-news`, and `/api/assets/{ticker}/weekly-news` select fresh imported packs only when valid, otherwise falling back to deterministic fixtures or the existing backend runtime pipeline
- imported ticker packs are accepted only for high-demand supported assets: `AAPL`, `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `VOO`, `QQQ`, `SPY`, `VTI`, `IVV`, and `XLK`
- official filings, investor-relations releases, issuer announcements, prospectus updates, and fact-sheet changes rank before approved reputable third-party/news sources
- local live ticker Weekly News acquisition attempts official sources first, then configured provider/news APIs, then Yahoo/yfinance fallback, while final non-official selection quality-ranks the pooled candidates by ticker usefulness, publisher tier, source-use policy, recency, duplicate status, and beginner utility
- generic market-regime or opinion items are suppressed from ticker Weekly News unless they have a clear ticker, issuer, ETF, index exposure, holdings, flows, fees, distributions, products, earnings, regulatory, customer, or supply-chain hook
- demoted publishers such as Seeking Alpha, Motley Fool, Benzinga, MarketBeat, Zacks, IBD, and similar sources are backfill-only and selected only when strongly ticker-specific and non-advice-like
- Weekly News Focus shows the configured maximum only when evidence supports it, otherwise a smaller verified set or empty state
- ticker-specific Weekly News Focus keeps the existing max-8 official-first behavior and explicit `Weekly News Focus: {TICKER}` label
- source-use policy values cover `metadata_only`, `link_only`, `summary_allowed`, `full_text_allowed`, and `rejected`
- source-use policy wins over score
- AI Comprehensive Analysis is suppressed unless at least two approved Weekly News Focus items exist; approved reputable third-party items may count when labeled and source-governed
- AI Comprehensive Analysis: Market News Focus is suppressed unless at least five approved market items across at least three topic buckets exist
- generated analysis cites selected Weekly News Focus items and canonical facts only
- Market AI analysis cites selected market story clusters only, uses thematic lenses instead of named personas, and treats Scenario Lens as conditional education rather than prediction
- yfinance/Yahoo-style news lists are treated as a fallback metadata structure only, not broad production ingestion or canonical fact evidence
- local Weekly News source rows expose headline/title, publisher, URL, published time, retrieved time, ticker match, event type, source label, source-use policy, and optional bounded summary/snippet only
- Market News and local Weekly News source rows expose headline/title, publisher, URL, published time, retrieved time, topic/ticker match, source label, source-use policy, cluster/audit metadata, and optional bounded summary/snippet only
- longer ticker candidate history is allowed only for dedupe/scoring diagnostics; current generated claims cite selected Weekly News items and canonical facts only
- local Weekly News diagnostics report candidate and selected counts by acquisition source and publisher tier, plus suppression reasons such as `generic_market_context_for_ticker`, `opinion_or_column`, `advice_like`, `weak_ticker_relevance`, `demoted_publisher_backfill_only`, and `duplicate`
- raw article bodies, unrestricted thumbnails/media, provider payloads, trade UX, recommendation copy, secrets, and generated-output cache promotion are absent from Market News and local Weekly News output
- `LIGHTWEIGHT_WEEKLY_NEWS_FETCH_ENABLED`, `MARKET_NEWS_FETCH_ENABLED`, and `MARKET_NEWS_LIVE_SOURCE_REAL_FETCH_ENABLED` may default on for local runtime/manual review outside CI and tests, while normal CI, pytest, static evals, explicit `env={}` settings, and smoke opt-ins remain deterministic, fixture-backed, or skipped unless explicitly enabled

### Ingestion, Provider, Caching, And Freshness Tasks

Use for provider adapters, on-demand ingestion, pre-cache workflows, Top-500 candidate manifest refreshes, Golden Asset Source Handoff execution, source checksums, freshness hashes, cache invalidation, and provider-secret handling.

Required checks:

```bash
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Verify:

- tests use mocked provider responses or local provider fixtures
- no API keys, paid-provider credentials, or live network calls are required in normal CI
- source acquisition separates retrieval from evidence approval through Golden Asset Source Handoff
- source snapshots, parser outputs, normalized packs, generated-output cache records, citations, source drawer responses, and exports carry source-use and approval metadata needed to block unapproved evidence
- source records missing approval metadata default closed to `pending_review`, `rejected`, `unavailable`, or `insufficient_evidence`
- unsupported and out-of-scope assets are blocked from generated pages, generated chat, and generated comparisons
- freshness fields include page-level and section-level dates or explicit unknown/stale/unavailable/partial states
- pre-cache and on-demand ingestion paths expose pending, running, succeeded, failed, unsupported, out-of-scope, unknown, unavailable, and stale states where relevant
- provider licensing and export/download constraints are documented before exposing paid or restricted content
- real secret values are never logged, echoed, copied into docs, exposed through `NEXT_PUBLIC_*`, returned from APIs, or committed

### Search, Support Classification, And Entity-Resolution Tasks

Use for ticker/name search, ambiguous-match states, supported/unsupported/out-of-scope classification, Top-500 runtime manifest behavior, Top-500 candidate refresh workflow, and on-demand ingestion routing.

Required checks:

```bash
python3 -m pytest tests -q
npm test
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Verify:

- supported U.S.-listed common stocks and manifest-approved ETF-500 scope U.S. equity ETFs resolve by exact ticker, partial ticker, asset name, and issuer/provider where useful
- supported ETF generated-output coverage reads only `data/universes/us_equity_etfs_supported.current.json`, while broader ETF/ETP recognition reads only `data/universes/us_etp_recognition.current.json`
- once the ETF-500 manifest is promoted, full-manifest smoke proves every supported row resolves through the supported ETF loader and recognition-only rows stay generated-output-ineligible
- clear comparison queries such as `VOO vs QQQ` show a comparison-route result instead of turning home search into a comparison builder
- top-500 stock support comes from `data/universes/us_common_stocks_top500.current.json`, not a live provider query at request time
- Top-500 refresh work writes reviewed candidates to `data/universes/us_common_stocks_top500.candidate.YYYY-MM.json` and never overwrites the approved current manifest without review
- candidate manifest rows preserve source provenance, source snapshot date, source checksum, rank, rank basis, CIK, exchange, validation status, and warnings
- IWB official holdings are the primary source input, SPY/IVV/VOO official holdings are fallback-only inputs, and SEC/Nasdaq validation failures are surfaced for review
- ambiguous searches show disambiguation instead of silently guessing
- recognized-but-unsupported and out-of-scope assets do not link to generated asset pages, chat, or comparisons
- unknown searches say unknown or unavailable without invented facts

### Glossary And Beginner-Education Tasks

Use for curated glossary terms, glossary popovers or bottom sheets, asset-specific glossary context, and beginner readability changes.

Required checks:

```bash
npm test
npm run typecheck
python3 -m pytest tests/unit/test_safety_guardrails.py -q
bash scripts/run_quality_gate.sh
```

Verify:

- core term definitions are generic, beginner-readable, and do not need citations unless they include asset-specific facts
- asset-specific glossary context is grounded in the selected asset knowledge pack
- glossary appears contextually inside asset pages, comparison pages, and chat answers rather than as a primary home-page workflow
- desktop glossary behavior supports hover, click-to-pin, and keyboard focus
- mobile glossary behavior supports tap and may also support long tap, opening a bottom sheet that preserves page position
- glossary UI does not obscure citations, source access, chat, or primary page content on mobile

### Export And Download Tasks

Use for asset-page exports, comparison exports, source-list exports, chat transcript exports, Markdown/JSON output, and export licensing rules. PDF export remains post-MVP unless licensing and rendering requirements are resolved.

Required checks:

```bash
python3 -m pytest tests -q
npm test
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Verify:

- exported content includes citations, source metadata, freshness or as-of dates, uncertainty labels, and the educational disclaimer
- exports preserve advice boundaries
- MVP exports are Markdown and JSON only
- source-list exports include allowed source titles, URLs, dates, retrieved timestamps, attribution, and source-use policy where available
- paid news or restricted provider content is omitted or summarized unless redistribution rights are documented
- raw full article text, unrestricted provider payloads, hidden prompts, raw model reasoning, and secrets are not exported

### Agent Loop, Environment, And Deployment-Scaffold Tasks

Use for `AGENTS.md`, `SPEC.md`, `TASKS.md`, `EVALS.md`, scripts, CI, Docker Compose, env examples, workspace layout, and agent-loop process changes.

Required checks:

```bash
python3 -m pytest tests/unit/test_repo_contract.py -q
npm test
bash scripts/run_quality_gate.sh
```

For the local fresh-data MVP rehearsal command, also run:

```bash
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
```

Also run when available:

```bash
docker compose config
```

Verify:

- task instructions are narrow enough for one agent-loop cycle
- `TASKS.md` has a current task or backlog when continuous agent work is expected
- backlog headings are small, sequential, and aligned with MVP scope
- near-term task sequencing preserves the single-asset-first frontend workflow, keeps the implemented ETF manifest split intact, then closes repo-native handoff tooling, local live-AI validation, governed golden evidence, and launch-manifest automation gaps before production deployment expansion
- agent prompts keep the v0.4 baseline visible: single-asset home search, separate comparison workflow, contextual glossary, mobile source/glossary/chat bottom sheets, stock-vs-ETF relationship badges, and evidence-backed Weekly News Focus limits
- agent prompts keep the manifest-owned Top-500 rule and Golden Asset Source Handoff rule visible
- agent prompts keep ETF-500 scope, golden/pre-cache ETF regression status, and the supported ETF manifest versus ETF/ETP recognition manifest split visible
- Bash and PowerShell agent loops default to `gpt-5.5` with `high` reasoning effort, and allow explicit script-argument overrides such as `gpt-5.3-codex-spark`
- agent prompts read proposal, PRD, technical design, SPEC, TASKS, and EVALS
- PRD/TDS/proposal are treated as the current baseline after safety rules
- root npm scripts delegate to `apps/web`
- local web/API smoke instructions cover `NEXT_PUBLIC_API_BASE_URL`, `API_BASE_URL`, `CORS_ALLOWED_ORIGINS`, and the Next `/api/:path*` rewrite behavior
- local fresh-data rehearsal output distinguishes `pass`, `skipped`, and `blocked` states while keeping deterministic defaults fixture-backed and optional browser, durable repository, official-source retrieval, and live-AI modes explicitly gated
- Docker Compose scaffolding remains local-only and is not required for CI
- env examples use placeholders only and contain no real secrets
- docs do not contradict safety, citation, freshness, source-use, secret-handling, or no-live-calls rules
- docs hygiene avoids mojibake, stale AI labels, stale weekly-window wording, and duplicate PRD requirement IDs
