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
- beginner copy avoids buy/sell/hold, allocation, price-target, tax, and brokerage language
- Weekly News Focus and AI Comprehensive Analysis remain visually separate from stable facts
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
- stale sources are labeled stale or suppressed according to section behavior
- advice-like prompts redirect into educational framing before LLM calls
- no output tells the user to buy, sell, hold, allocate, trade, use a broker, rely on tax advice, or accept a price target
- chat remains grounded in the selected asset knowledge pack and does not use raw transcript text in analytics/training/evaluation

### Weekly News Focus And Source-Use Tasks

Use for market-week window logic, recent events, source allowlists, Golden Asset Source Handoff, source-use policies, raw text policy, news/event scoring, and AI Comprehensive Analysis inputs.

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
- official filings, investor-relations releases, issuer announcements, prospectus updates, and fact-sheet changes rank before approved reputable third-party/news sources
- Weekly News Focus shows the configured maximum only when evidence supports it, otherwise a smaller verified set or empty state
- source-use policy values cover `metadata_only`, `link_only`, `summary_allowed`, `full_text_allowed`, and `rejected`
- source-use policy wins over score
- AI Comprehensive Analysis is suppressed unless at least two high-signal weekly items exist
- generated analysis cites selected Weekly News Focus items and canonical facts only

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

- supported U.S.-listed common stocks and manifest-approved supported U.S. equity ETFs resolve by exact ticker, partial ticker, asset name, and issuer/provider where useful
- supported ETF generated-output coverage reads only `data/universes/us_equity_etfs_supported.current.json`, while broader ETF/ETP recognition reads only `data/universes/us_etp_recognition.current.json`
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
- agent prompts keep the supported ETF manifest and ETF/ETP recognition manifest split visible
- Bash and PowerShell agent loops default to `gpt-5.5` with `high` reasoning effort, and allow explicit script-argument overrides such as `gpt-5.3-codex-spark`
- agent prompts read proposal, PRD, technical design, SPEC, TASKS, and EVALS
- PRD/TDS/proposal are treated as the current baseline after safety rules
- root npm scripts delegate to `apps/web`
- local web/API smoke instructions cover `NEXT_PUBLIC_API_BASE_URL`, `API_BASE_URL`, `CORS_ALLOWED_ORIGINS`, and the Next `/api/:path*` rewrite behavior
- Docker Compose scaffolding remains local-only and is not required for CI
- env examples use placeholders only and contain no real secrets
- docs do not contradict safety, citation, freshness, source-use, secret-handling, or no-live-calls rules
- docs hygiene avoids mojibake, stale AI labels, stale weekly-window wording, and duplicate PRD requirement IDs
