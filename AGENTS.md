# AGENTS.md

## Project identity

This project is a citation-first beginner U.S. stock and ETF learning assistant.

The product helps beginners understand U.S.-listed common stocks and manifest-approved U.S.-listed passive/index-based U.S. equity ETFs using:

- official or structured sources first
- plain-English explanations
- visible citations
- source freshness
- stable canonical facts separated from Weekly News Focus and AI Comprehensive Analysis
- educational framing instead of investment advice

This product is not:

- a stock picker
- a trading bot
- a brokerage app
- a portfolio optimizer
- a personalized financial advisor
- a general finance chatbot
- a market-news feed that lets recent news redefine an asset

Current frontend workflow baseline is Frontend Design and Workflow v0.4:

- the home page has one primary action: search for a single supported stock or ETF
- comparison is a separate connected workflow through `/compare`, global navigation, asset-page CTAs, suggested comparisons, chat compare redirects, and clear `A vs B` search patterns
- glossary is contextual help inside asset pages, comparison pages, and chat answers, not a major home-page workflow for MVP
- desktop glossary cards support hover, click, and keyboard focus; mobile glossary opens from tap or long-tap into a bottom sheet
- source drawer, glossary, and asset chat must be designed for mobile bottom-sheet or full-screen behavior where appropriate
- stock-vs-ETF comparison uses a special single-company-vs-ETF-basket template with relationship badges

## Required reading before work

Before changing code, read:

1. docs/learn_the_ticker_PRD.md
2. docs/learn_the_ticker_technical_design_spec.md
3. docs/learn-the-ticker_proposal.md
4. SPEC.md
5. TASKS.md
6. EVALS.md

If these files conflict, follow this order:

1. Safety and advice-boundary rules
2. docs/learn_the_ticker_PRD.md
3. docs/learn_the_ticker_technical_design_spec.md
4. docs/learn-the-ticker_proposal.md
5. SPEC.md
6. TASKS.md
7. EVALS.md

`SPEC.md`, `TASKS.md`, and `EVALS.md` are operational control docs. The updated PRD is the product source of truth, and the updated technical design spec is the engineering source of truth.

## Development loop

For every task:

1. Run `git status --short`.
2. Restate the current task and acceptance criteria.
3. Inspect relevant files before editing.
4. Make the smallest high-confidence change that satisfies the task.
5. Run the required tests/evals from EVALS.md.
6. If tests fail, diagnose the failure before editing again.
7. Write a short summary of changed files, tests run, results, and risks.

The harness script handles branch creation, journaling, tests, and routine task commits. The agent loop should keep tasks narrow enough for one cycle unless the user explicitly requests a larger rebase.

## Git rules

You may run:

- `git status`
- `git diff`
- `git log`
- `git branch`
- `git show`
- `git commit`
- `git push`

Do not run these unless the user or harness explicitly allows it:

- `git reset --hard`
- `git clean -fd`
- `git rebase`
- `git merge`
- `git checkout main`
- `git push --force`

Commit messages must follow Conventional Commits and describe the completed task, for example `feat(T-005): add source-backed retrieval fixtures`. Do not use vague subjects such as `implement current task`.

## Product guardrails

Never introduce:

- buy/sell/hold recommendations
- personalized allocation advice
- exact position sizing
- unsupported price targets
- tax advice
- brokerage/trading behavior
- unsupported claims presented as facts
- recent news that overwrites canonical facts
- general chatbot answers that ignore the selected asset knowledge pack

Advice-like user questions must be redirected into educational framing.

Example:

User: "Should I buy QQQ?"

Safe style:

"I can't tell you whether to buy it. I can help you understand what QQQ holds, how concentrated it is, how it differs from a broader ETF, and what risks a beginner should understand."

## MVP scope rules

V1 is accountless and English-first.

Supported MVP coverage is:

- top-500-first U.S.-listed common stocks from `data/universes/us_common_stocks_top500.current.json`
- manifest-approved U.S.-listed, active, non-leveraged, non-inverse, passive/index-based ETFs with primary U.S. equity exposure and validated issuer source packs
- pre-cached high-demand assets for reliable launch behavior
- explicit `pending_ingestion` only for eligible supported assets that are approved for on-demand ingestion

The top-500 manifest is the runtime source of truth for stock coverage. The supported ETF manifest is the runtime source of truth for ETF generated-output coverage. Runtime support classification must never be resolved directly from a live ETF holdings file, provider holdings file, market-data response, exchange listing, issuer search result, recognition-only ETP row, or rank query.

ETF support work must preserve the v0.5 split:

- supported ETF generated-output coverage comes only from `data/universes/us_equity_etfs_supported.current.json`
- broader ETF/ETP recognition for blocked search states comes from `data/universes/us_etp_recognition.current.json`
- recognition rows may identify unsupported, out-of-scope, pending-review, unavailable, or pending-ingestion products, but must not unlock asset pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, or exports

Top-500 refresh work must:

- produce reviewed candidates at `data/universes/us_common_stocks_top500.candidate.YYYY-MM.json`
- use official IWB holdings as the primary ranking input with `rank_basis = "iwb_weight_proxy"`
- use official SPY, IVV, and VOO holdings only as fallback inputs with `rank_basis = "sp500_etf_weight_proxy_fallback"`
- validate candidates against SEC `company_tickers_exchange.json` and Nasdaq Trader symbol-directory fields
- preserve source provenance, source snapshot dates, checksums, rank basis, validation status, and warnings
- generate a diff report and require manual approval before replacing `data/universes/us_common_stocks_top500.current.json`

Unsupported or out-of-scope assets include options, crypto, international equities, leveraged ETFs, inverse ETFs, ETNs, fixed income ETFs, commodity ETFs, active ETFs, multi-asset ETFs, single-stock ETFs, option-income or buffer ETFs, preferred stocks, warrants, rights, and other complex products unless explicitly added later. Recognized-but-unsupported and out-of-scope assets may appear in search, but must not receive generated pages, generated chat answers, generated comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, or generated risk summaries.

Partial evidence is acceptable. If sources cannot verify a section, render verified sections only and label missing pieces as `partial`, `stale`, `unknown`, `unavailable`, or `insufficient_evidence`.

## Weekly News Focus rules

Weekly News Focus and AI Comprehensive Analysis are timely context layers. They must stay visually, structurally, and citation-wise separate from stable canonical facts.

Weekly News Focus must:

- use the last completed Monday-Sunday market week plus current week-to-date through yesterday, based on U.S. Eastern dates
- prefer official filings, investor-relations releases, ETF issuer announcements, prospectus updates, and fact-sheet changes before approved reputable third-party/news sources
- include only high-signal, deduplicated, license-compatible items
- show the configured maximum only when enough evidence supports it, and show fewer items or an empty state when evidence is thin
- never pad with weak, promotional, duplicate, unapproved, or rights-disallowed items

AI Comprehensive Analysis must:

- be generated only when at least two high-signal Weekly News Focus items exist
- start with What Changed This Week, then Market Context, Business/Fund Context, and Risk Context
- cite underlying Weekly News Focus items and canonical facts
- avoid predictions, recommendation language, and uncited claims

## Citation and source-use rules

Important factual claims must have citations.

A citation is valid only if:

- the source exists
- the source belongs to the same asset or comparison pack
- the source supports the claim
- Weekly News Focus claims cite Weekly News Focus sources
- stale sources are labeled stale or suppressed according to section behavior
- wrong-asset citations are rejected

If evidence is missing, say unknown, stale, mixed evidence, unavailable, partial, or insufficient evidence.

Stable facts should use official and structured sources before news. Source-use policy wins over scoring: `rejected` or rights-disallowed sources must not feed generated output, rendered summaries, caches, or exports.

Golden Asset Source Handoff is required between retrieval and evidence use. Fetching a filing, issuer page, holdings file, API payload, or provider response is only retrieval. It is not approval to store the source as evidence, cite it, summarize it, generate from it, cache it, or export it.

Golden Asset Source Handoff approval requires:

- approved, allowlisted, or explicitly reviewed domain/source identity
- source type and official-source status
- storage rights and export rights
- source-use policy and approval rationale
- parser validity or parser failure diagnostics
- freshness/as-of metadata
- review status of `approved`, `pending_review`, or `rejected`

Sources that are missing from the allowlist, unclear-rights, parser-invalid, hidden/internal, or rejected must default to `pending_review` or `rejected` and must not support generated output, citation support, exported content, or generated-output cache entries.

Raw source text storage is rights-tiered:

- official filings, issuer materials, and `full_text_allowed` sources may store raw text, parsed text, chunks, checksums, and private snapshots
- `summary_allowed` sources may store metadata, links, checksums, and limited allowed excerpts
- `metadata_only` and `link_only` sources may store metadata, hashes, canonical URLs, timestamps, and diagnostics, but not full article text
- `rejected` sources must not feed generated output

Source allowlist changes must update source-use policy, source type, domain, official-source status, storage rights, export rights, rationale, validation tests, and development-log rationale together. Automated scoring can rank already-allowed sources but cannot approve a new source.

## Provider, secret, and environment rules

Normal CI must be deterministic and must not require live provider, news, market-data, or LLM calls.

OpenRouter and market/reference providers are runtime options only:

- `LLM_LIVE_GENERATION_ENABLED` must be `true` before live model calls are allowed
- deterministic mocks remain the default for CI and local tests
- OpenRouter keys stay server-side only and must never appear in browser code, `NEXT_PUBLIC_*`, `/health`, docs, logs, or committed env files
- optional provider keys such as `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `FINNHUB_API_KEY`, `TIINGO_API_KEY`, and `EODHD_API_KEY` are configuration readiness only until licensing, caching, display, and export rights are reviewed

Local live-provider runs may inherit placeholder-named variables from the developer's WSL Bash environment. Do not inspect, echo, commit, or copy actual secret values.

## Repo layout

- `apps/web` is the Next.js frontend and Vercel project root.
- `backend` is the FastAPI package and stays at the repository root for now.
- Root npm scripts must continue to delegate to the frontend workspace.
- Docker Compose scaffolding is local development support only and must not be required for CI.

## Testing expectations

When touching retrieval, summaries, chat, citations, Weekly News Focus, source-use policy, or safety, run:

- citation evals
- safety evals
- golden asset tests
- the full quality gate

When touching Top-500 manifest workflow or Golden Asset Source Handoff behavior, verify:

- runtime stock support still reads `data/universes/us_common_stocks_top500.current.json`
- candidate manifests do not overwrite the approved current manifest without review
- manifest refresh inputs are official-source inputs that pass source handoff before being used as evidence or provenance
- unapproved, not-allowlisted, unclear-rights, parser-invalid, hidden/internal, pending-review, and rejected sources cannot feed persistence-as-evidence, generation, citation, cache, or export paths
- source drawer, citation, export, generated-output cache, and knowledge-pack records expose only approved source metadata and allowed excerpts

When touching frontend UI, verify:

- home search remains the primary home-page action for one supported stock or ETF
- comparison remains a separate connected workflow, not a two-input home-page primary experience
- glossary remains contextual in reading flows, not a primary home-page workflow
- search results show stock vs ETF identity, support-state chips, exact unsupported behavior, and clear no-result copy
- citation chips
- source drawer, including desktop drawer and mobile bottom-sheet behavior
- freshness labels
- stale/unknown/unavailable/partial states
- stock-vs-ETF comparison relationship badges and special structure when comparison UI is touched
- contextual glossary desktop hover/click/focus and mobile tap bottom-sheet behavior
- asset chat desktop helper placement and mobile bottom-sheet or full-screen behavior
- beginner readability
- mobile and desktop usability

When touching backend APIs, verify:

- schema validation
- unit tests
- endpoint tests
- no live external calls in normal CI

When touching agent-loop, environment, or workspace layout, verify:

- root npm scripts still work
- `apps/web` workspace scripts work
- v0.5 ETF support classification stays split between the supported ETF manifest and the ETF/ETP recognition manifest
- Bash and PowerShell agent prompts stay aligned
- placeholder env files contain no real secrets
- Docker scaffolding validates when Docker is available

## Dependency policy

Do not add production dependencies without explaining:

- why the dependency is needed
- alternatives considered
- security/licensing risk
- whether it affects deployment
