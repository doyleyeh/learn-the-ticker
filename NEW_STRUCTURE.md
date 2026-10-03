# Learn the Ticker: revised desktop architecture and migration plan

This is the architecture decision record for the approved local-first reboot. It describes the target; [implementation status](docs/IMPLEMENTATION.md) distinguishes working code from unfinished release requirements. It replaces the generic desktop proposal previously in this file. The implemented preview includes durable evidence, conversations, terms and portable backups; it does not yet satisfy the live-provider, full financial workflow or native release requirements below.

This file is the canonical entry point for the accepted plan of the same name. Read it with [PRD.md](PRD.md) for required behavior, [TECHNICAL_DESIGN_SPEC.md](TECHNICAL_DESIGN_SPEC.md) for implementation mechanisms, [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) for the ordered backlog and verified status, and [docs/TESTING.md](docs/TESTING.md) and [docs/MIGRATION.md](docs/MIGRATION.md) for verification and migration. Together these documents preserve the plan for future contributors and Codex agents without requiring the originating conversation. Update them in place instead of creating a competing plan.

## Product and ownership

Learn the Ticker is a freely distributed, Apache-2.0, citation-first research and learning application. The first users are technically comfortable repository users; ordinary beginners follow with the Windows installer. Beginner and intermediate explanations have equal prominence. Priorities are understanding one asset, conversational research, then comparing assets.

One person owns one local library per installation. PostgreSQL stores app-owned evidence, conversations, jobs and versioned research. Providers do inference and, where supported, research with the user's subscription. Provider authentication is separate from a Learn the Ticker account: the app requires no hosted account or central research backend. Global permission explains outbound source retrieval and selected-provider inference. Telemetry is absent.

## Stack and repository

| Layer | Choice |
| --- | --- |
| Window and native supervisor | Tauri 2 |
| Frontend | React, TypeScript and Vite in apps/desktop |
| Styling | Preserve existing CSS and reusable components; introduce Tailwind/shadcn only when needed |
| Business service | FastAPI in backend/app, packaged per OS with PyInstaller |
| Storage | Private PostgreSQL, SQLAlchemy 2, Alembic |
| Transport | Authenticated HTTP and normalized WebSocket events |
| Shared contracts | Pydantic -> JSON Schema -> generated TypeScript |
| Distribution | GitHub source and GitHub Releases |

Keep npm workspaces. Root commands delegate to apps/desktop. Docker is optional development support. The release application uses packaged core services, not Next.js, Vite, Python from PATH or a user-operated database. The source preview still requires development tools. Provider runtimes have their own prerequisites, including a compatible Node runtime for Gemini CLI. Setup must reuse supported installations or provision reviewed private runtimes. Report missing prerequisites and offer cached use while they are resolved; an unavailable adapter does not satisfy public-v1 acceptance.

## Process and security boundaries

Tauri owns the sidecar process and application instance. Its bootstrap command supplies the endpoint and temporary credential only; React has no generic shell or filesystem capability. The sidecar owns a private cluster and provider subprocesses. The native host creates the credential before service startup and transmits it over stdin.

Startup: enforce a single application instance; locate private storage and acquire its library lock; generate the temporary credential before API availability; initialize/recover the private cluster; choose loopback ports; verify PostgreSQL; check schema compatibility; perform a compatible migration with a restore-tested backup when required; start FastAPI; verify authenticated readiness; expose the endpoint to the window. The preview initializes revision 0001 and rejects incompatible existing schemas; upgrade orchestration is still required. Use bounded retries. Never reconfigure an existing system database, delete an unknown PID file, or kill unrelated processes.

Close hides the window in the tray. Explicit Quit cancels/checkpoints research, stops provider processes and FastAPI, then stops PostgreSQL. Parent-pipe closure also triggers shutdown. Start-at-login is opt-in and must not be advertised until implemented and tested.

PostgreSQL and FastAPI bind only to loopback. HTTP requires a bearer credential; WebSocket sends the credential in its first frame after origin validation, never in its URL. Validate Origin and Host. Session secrets stay in memory. OS credential storage holds application-owned durable secrets; provider-owned authentication remains with the provider. Logs and exports omit credentials, reasoning traces and arbitrary tool payloads.

Research workspaces are isolated. Provider tools are explicitly restricted; prompt instructions alone are not a sandbox. Expanded access needs a real approval flow. Until that flow is implemented, deny the request and explain the limitation. Do not inherit arbitrary developer MCP servers, hooks or instructions into production research.

## Provider adapters

The AIRuntime boundary owns discovery, supported-version checks, authentication, capabilities, sessions, streaming, approvals, interruption and cancellation. Normalize message updates, tool activity, evidence registration and run state. React does not parse vendor events.

| Connection | Mechanism | Public v1 requirement |
| --- | --- | --- |
| ChatGPT/Codex | Codex App Server and supported subscription authorization | Required |
| Gemini | Gemini CLI and provider-managed Google authentication | Required |
| Claude | Claude Code/Agent SDK and supported subscription authentication | Required |

Use one selected provider/model at a time. Store conversational scope and history in the app. Switching providers retains that history but re-evaluates capabilities. Never scrape consumer websites, copy browser cookies, silently enable API-key billing, accept paid overages, or automatically switch providers. Pause on unsupported versions, quota or authentication failures. A runtime without safe research tools may explain cached/imported evidence only. Installation does not prove authentication or subscription entitlement.

ChatGPT/Codex is the first internal milestone. All three integrations must pass before public v1. Local inference and external app MCP hosting are deferred.

## Research and evidence

Resolve identity and scope -> inspect cache/freshness -> configured structured sources -> agent investigation -> application validation -> durable evidence -> explanations and progressive UI.

There is no Top-500, golden ticker or pre-ingestion eligibility gate. Support resolvable assets across stocks, funds, ETFs, bonds, international listings, crypto and derivatives. Type-specific missing fields remain unavailable/not applicable. Ambiguous listings, contracts and share classes require disambiguation. Classification-dependent facts wait for classification. Broad coverage does not guarantee free or complete data.

Source URLs returned by agents are candidates. Verify identity, retrieval, dates, source permissions, claim support, units and calculations independently. Official status does not imply redistribution permission. Predefined rules may automatically admit verified official sources; users can require review. Unknown-rights sources remain links/metadata until a rule permits excerpts or summaries. Rights tiers remain full_text_allowed, summary_allowed, metadata_only, link_only and rejected.

Separate admitted facts, reproducible calculations, attributed interpretations and unverified notes. Unverified notes are readable, clearly marked, and never become chart inputs or factual context for another generation. Keep conflicting evidence and document the preferred-value rule: relevant period/unit, latest restatement, then official/structured provenance, then freshness. Do not erase earlier evidence.

Cite important claims in pages, chat and exports. Sources show original URL, publisher, publication/as-of/retrieval dates, freshness and allowed support. English and Traditional Chinese explanations preserve original numbers, units and citations. Safety boundaries apply to every asset class.

## UI and retained behavior

Preserve the asset header, overview, charts where supported, business/fund context, financial trends, holdings, valuation context, risks, sources, comparison, glossary and exports. Beginner and intermediate views are peers. Collapse less important detail. Research progressively reports progress and evidence gaps.

Term click/selection can request a concise explanation; hover/focus only reuses saved explanations or curated definitions. Cache generated terms by evidence version, language and reader level, preserving their dates, provider attribution and citations. Generic definitions with no supplied citation must say so. Generated terms remain interpretations and never feed canonical evidence. Conversations start with the current asset and show scope changes. Save persistent conversations, bookmarks and versioned reports. Refresh updates affected explanations without rewriting saved snapshots. Offline supports cached pages, cached explanations and previous comparisons; generating a new comparison remains online-only.

## Operating defaults

| Area | Default |
| --- | --- |
| Scale | 1,000 cached assets as an engineering target, not a coverage cap |
| Concurrent work | Two retrieval jobs, one inference |
| Statements | Five annual years and twelve quarters |
| Daily price history | Five years; longer on request |
| Returns | Price return and total return separately |
| Restatements | Latest figures, superseded evidence retained |
| Point-in-time analysis | Deferred |
| ETF holdings history | Current and month-end observations; backfill when available |
| Historical valuation | Only aligned historical inputs |
| Event display | Twelve months |
| Saved reports and bookmarks | Until deletion |
| Unsaved conversations | 180 idle days; bookmarking prevents expiry |
| Disposable cache | 10 GB; protect permitted evidence behind saved work |
| Updates | Notify/approve, with manual and automatic alternatives |
| Development repairs | Three attempts, then diagnosis/report |

Weekly News Focus uses the last completed Monday–Sunday plus current week through yesterday in America/New_York. Fewer than three high-signal items triggers a search up to 30 days for separately labeled Earlier context. Older items do not count toward the minimum two weekly items for weekly analysis. General historical research has no recent-news minimum. Never pad weak, duplicate or disallowed items.

## Portability and release sequence

Full backup/restore excludes credentials and provider authentication. Test actual restoration; a readable archive listing is not restore verification. Migrations and application versions must roll back together. Restore into another cluster and preserve newer research before switching. Unknown/future schemas fail closed. Updates require verified artifacts; updater signatures and OS code signing are different controls.

Milestones: local foundation; complete Codex research; product parity; Gemini/Claude parity; clean-machine Windows installer; macOS; WSL; Linux. One-command developer setup precedes installer claims. Public v1 requires all three live integrations and packaged lifecycle, backup, update and rollback validation.

See [PRD](PRD.md), [technical design](TECHNICAL_DESIGN_SPEC.md), [backlog](docs/IMPLEMENTATION.md), [testing](docs/TESTING.md), and [migration](docs/MIGRATION.md).

## Official integration references

Integration reference entry points, not compatibility certifications. Pin and qualify exact runtime versions before release; local verification evidence belongs in [IMPLEMENTATION.md](docs/IMPLEMENTATION.md).

- [Codex App Server](https://learn.chatgpt.com/docs/app-server)
- [ChatGPT plan integration](https://developers.openai.com/siwc/token-sharing-open-source)
- [Gemini headless mode](https://geminicli.com/docs/cli/headless/)
- [Gemini installation](https://geminicli.com/docs/get-started/installation/)
- [Claude CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Tauri sidecars](https://v2.tauri.app/develop/sidecar/)
- [PyInstaller](https://pyinstaller.org/en/latest/)
