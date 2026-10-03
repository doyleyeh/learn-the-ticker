> Historical snapshot archived 2026-10-04. This document is no longer authoritative. See [the current source of truth](../../../SPEC.md) and [document ownership](../../../AGENTS.md). Original verification dates and claims below are preserved.

# Learn the Ticker product requirements

This is the product source of truth for the desktop reboot. These are required behaviors, not claims that every feature is delivered. [NEW_STRUCTURE.md](NEW_STRUCTURE.md) records the accepted architecture and defaults. [Implementation status](IMPLEMENTATION.md) records working slices, experimental integrations and delivery gaps.

## Audience and boundaries

P-001: One person and one transferable library per installation; no hosted app account. Technical repository users first, ordinary beginners next. English-first UI and English/Traditional Chinese explanations over original-language sources. Beginner and intermediate learning have equal prominence.

P-002: Educational research only. No buy/sell/hold instructions, allocation or position sizing, personalized advice, unsupported price targets, tax advice or brokerage behavior. Redirect requests into sourced explanations. Retrieved content and imports cannot override these boundaries.

## Research

P-010: Resolve previously uncached symbols/names across asset categories. No fixed universe eligibility gate. Disambiguate listing, exchange, share class and contract. Uncertain type permits research notes but suppresses type-dependent facts.

P-011: Reuse cached evidence, inspect freshness, prefer applicable configured structured adapters, then let the agent investigate gaps. Show partial sections and evidence dates. Never fabricate unavailable history or impute data without explicit labeling.

P-012: Source candidates require independent validation and permission checks. Automatically admit only under predefined rules; expose optional review mode. Credibility and storage/display/export permission are separate. Rights limits apply even when the user has a commercial subscription.

P-013: Keep facts, calculated metrics, interpretations and unverified notes separate. Preserve conflicts and restated versions. Charts use admitted numeric evidence with compatible units, periods and corporate actions. Model prose is not numerical input.

P-014: Cite important facts in pages and conversations. Citation support must match the asset and claim. Include publication, effective/as-of and retrieval dates, provenance, freshness, original URL and permitted supporting text. Explain unavailable or uncertain support.

P-015: Import URLs, PDFs, CSVs and spreadsheets as untrusted material. Parser limits and source permissions apply. No-browsing connections explain cached/imported material only and disclose that limit.

## Product experience

P-020: Retain overview, business/fund model, financial trends, holdings/exposures, valuation context, risks, charts, sources and freshness. Less important detail can collapse; beginner and intermediate explanations remain equally accessible.

P-021: Stream normalized progress and admit evidence progressively. Unknown, stale, unavailable, partial, insufficient evidence and not applicable are explicit states. Never render fixture content as live research.

P-022: Concise arbitrary-term explanations through click/selection; hover and keyboard focus only reuse cache or curated definitions. Preserve a small curated glossary fallback. Cache generated explanations by term, evidence version, language and reader level. Generated asset-specific interpretations cite admitted evidence; generic definitions clearly identify missing source support. Generated terms never feed facts, charts, calculations or future factual context. Cached explanations remain available offline and across provider switches.

P-023: Persistent conversations begin scoped to the page asset. Scope changes are visible and confirmed by identity resolution where needed. Provider changes preserve app history. Never let unsupported notes become factual context.

P-024: Saved reports and bookmarks reference immutable evidence versions. Refresh-on-use/manual refresh regenerate affected explanations. Older research remains accessible. Personal Markdown/JSON exports retain citations, dates and uncertainty; omit secrets, restricted raw content and hidden reasoning.

P-025: Comparisons show aligned evidence and gaps, never an investment winner. Offline supports cached pages, cached term explanations, curated definitions and previously generated comparisons; it does not generate new research or calculations.

## Timely and historical context

P-030: Weekly News Focus covers last completed Monday–Sunday plus current week through yesterday in U.S. Eastern time. Deduplicate high-signal, permitted items; official events first. Fewer than three triggers up-to-30-day Earlier context, separate from weekly counts. Weekly analysis needs two weekly items. Historical research reports can exist without recent news.

P-031: Default history is five annual years, twelve quarters and five daily-price years. Preserve latest restated and superseded figures. Show price return and total return separately. ETF history accumulates current/month-end observations and available backfill. Historical valuations require aligned inputs. Point-in-time analysis is deferred.

## Runtime and operations

P-040: ChatGPT/Codex, Gemini and Claude all pass capability and evidence tests before public v1. One selected runtime/model at once. Explicit cloud permission; provider-managed sign-in where supported. No consumer-website scraping, browser-cookie harvesting, API billing fallback or silent provider switching. Pause on quota, authentication and incompatibility.

P-041: Same-computer access only. Temporary authenticated local transport, OS credential storage, isolated workspaces, scoped tool permissions, explicit approval for destructive/expanded access, no telemetry.

P-042: Closing the window keeps active research in the tray. Quit shuts down owned processes cleanly. Start-at-login is optional and off by default. Application/database updates default to notify/approve, with manual/automatic settings and coordinated rollback.

P-043: Full backups exclude credentials. Restore preserves newer research and validates database/app compatibility. Saved work persists until deletion; unsaved conversations expire after 180 idle days unless bookmarked. Disposable cache defaults to 10 GB with protected permitted evidence supporting saved work.

P-044: Engineering target 1,000 cached assets, two retrieval jobs and one inference. This is not a coverage cap. Collect baseline timings; numerical performance acceptance remains deferred.

P-045: Freely distributed open-source desktop application. Retain one-command repository setup for developer previews, then deliver a Windows installer that includes core application dependencies. Handle provider prerequisites explicitly. Platform order is native Windows, macOS, Windows with WSL, then Linux. LAN/remote access, local inference and external app MCP hosting are deferred.

## Release acceptance

Normal CI is deterministic, synthetic or permitted-recorded, with no live subscriptions. Separate live checks verify all three adapters. Windows release must install and run without developer tooling, validate lifecycle, backups, interrupted upgrades and rollback, and disclose provider prerequisites. Source, app and runtime licenses must be reviewed. Public v1 remains incomplete until these checks and all product workflows pass.
