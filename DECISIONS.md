# Significant decisions

These decisions preserve the approved desktop reboot and the user's 2026-10-04 delivery instructions. [SPEC.md](SPEC.md) owns product requirements, [technical design](TECHNICAL_DESIGN_SPEC.md) mechanisms, and [STATUS.md](STATUS.md) actual progress. The [original architecture](docs/archive/2026-10-04/NEW_STRUCTURE.md) remains historical evidence.

## DEC-001 Local desktop ownership

Date: accepted before 2026-10-04; carried forward 2026-10-04.
Context: users need a durable personal evidence library rather than a transient hosted chat.
Options: retain hosted Next.js/backend; reboot as an owned local application.
Chosen approach: one user/library per installation, no hosted account/backend or telemetry; React/TypeScript/Vite in Tauri 2, FastAPI packaged per OS using PyInstaller, private PostgreSQL with SQLAlchemy 2/Alembic.
Reason: local ownership, reusable research and controlled lifecycle.
Consequences: native host owns the service and single instance; sidecar owns the database/providers. Docker remains optional development support. Preserve CSS/components; Tailwind/shadcn are not required. Distribute Apache-2.0 source and GitHub release artifacts.

## DEC-002 Private transport and lifecycle

Date: accepted before 2026-10-04; carried forward 2026-10-04.
Context: local subprocesses still need authentication and bounded ownership.
Options: broad frontend native access or narrow bootstrap IPC.
Chosen approach: native host creates an in-memory credential and passes it on stdin before API startup; authenticated loopback HTTP and normalized WebSockets; WebSocket credential in its first frame after Origin validation, never in URL; validate Host/Origin. Durable app secrets use OS credential storage.
Reason: keep secrets and process privileges out of React.
Consequences: lock library, initialize/recover only its private cluster, check schema, migrate compatibly after restore-tested backup, verify authenticated readiness, then expose endpoint. Bounded startup/shutdown; never alter system PostgreSQL, remove unknown PID files or kill unrelated processes. Close hides to tray; Quit/parent-pipe closure stops owned work and services. Start-at-login is optional/off by default.

## DEC-003 Subscription adapters

Date: accepted before 2026-10-04; live-check authorization confirmed 2026-10-04.
Context: reuse user subscriptions while isolating provider-specific protocols and permissions.
Options: subscription runtimes, API-key fallback, consumer-site automation.
Chosen approach: AIRuntime with Codex App Server first, Gemini CLI, and supported Claude Code/Agent SDK subscription integration. All three are required for Windows public v1. One selected provider/model; app-owned scope/history; normalized discovery/auth/capabilities/session/stream/approval/cancellation.
Reason: preserve provider-managed authentication and avoid billing surprises.
Consequences: never scrape consumer sites, copy cookies, inherit developer MCP/hooks/instructions, accept overages, or silently switch/bill APIs. Pin and qualify exact versions/capabilities. Unsupported tools/versions fail closed. Safe no-browsing adapters explain admitted cached/imported evidence only. Explicit live checks may run with existing authenticated subscriptions after deterministic checks; pause for sign-in, quotas or additional charges. Check current official integration documentation when qualifying, not archived claims.

## DEC-004 Dynamic research and source admission

Date: accepted before 2026-10-04; source strategy confirmed 2026-10-04.
Context: fixed launch universes and plausible model citations cannot establish facts.
Options: Top-500/pre-ingestion gate; dynamic identity and evidence admission.
Chosen approach: resolve identity/scope, inspect cache/freshness, use permitted official/free structured sources, investigate gaps, independently validate, persist evidence, then explain progressively.
Reason: broad asset coverage with explicit limits, rather than fabricated completeness.
Consequences: no golden-asset eligibility gate. Disambiguate listings/contracts/share classes; uncertain type suppresses type-dependent facts. No paid source is enabled without authorization. Source credibility and rights are separate; unknown rights allow links/metadata only. Policies remain full_text_allowed, summary_allowed, metadata_only, link_only and rejected. Admitted facts, reproducible calculations, interpretations and notes remain separate. Manual review is supported, not a way to bypass rights.

## DEC-005 Versioned evidence and learning

Date: accepted before 2026-10-04; carried forward 2026-10-04.
Context: refreshes and provider switches must not rewrite cited saved work.
Options: mutable provider-owned transcripts or app-owned immutable evidence.
Chosen approach: PostgreSQL stores immutable bundles, conversations, term explanations, reports, jobs and normalized events; Pydantic generates JSON Schema and TypeScript.
Reason: repeatable citations, restore and provider independence.
Consequences: atomic evidence/job publication, interrupted jobs do not replay subscriptions after restart, original source dates/units persist through English/Traditional Chinese explanations. Term cache keys include evidence version/language/level; hover/focus reads only, click/selection may generate. Generic unsourced definitions disclose missing support. Offline supports cached material/previous comparisons only. Exports preserve citations/uncertainty and omit restricted raw content/credentials/reasoning.

## DEC-006 Data history retention and scheduling

Date: accepted before 2026-10-04; carried forward 2026-10-04.
Context: stable defaults are needed without implying universal data availability.
Options: arbitrary feed-dependent defaults or the agreed operating policy.
Chosen approach: preserve these defaults.
Reason: predictable research and retention behavior.
Consequences:

| Area | Default |
| --- | --- |
| Scale | 1,000 cached assets engineering target; no eligibility cap |
| Work | Two retrieval jobs, one inference |
| Statements | Five annual years and twelve quarters where available |
| Daily prices | Five years; longer on request |
| Returns | Price return and total return separately |
| Restatements/conflicts | Relevant period/unit, latest restatement, official/structured provenance, then freshness; retain superseded/conflicting evidence |
| ETF holdings | Current/month-end observations and available backfill |
| Historical valuation | Aligned historical inputs only; point-in-time analysis deferred |
| Event display | Twelve months |
| Saved reports/bookmarks | Until deletion |
| Unsaved conversations | Expire after 180 idle days unless bookmarked |
| Disposable cache | 10 GB; protect permitted evidence behind saved work |
| Weekly focus | Last completed Monday-Sunday plus current week through yesterday in America/New_York |
| Sparse weekly results | Fewer than three high-signal items triggers up-to-30-day Earlier context, separate from weekly counts |
| Weekly analysis | Requires two weekly items; broad historical research has no recent-news minimum |
| Performance | Measure baselines; numerical latency thresholds not approved |
| Updates | Notify/approve default; manual/automatic alternatives |

## DEC-007 Portability and Windows finish line

Date: accepted before 2026-10-04; scope confirmed 2026-10-04.
Context: developer previews do not establish installation or recovery.
Options: developer-only release or self-contained public desktop delivery.
Chosen approach: Windows public v1 requires all workflows and three qualified providers plus clean-machine core packaging, actual restore, verified updates and coordinated app/schema rollback.
Reason: ordinary beginners must not operate Python/Node/PostgreSQL themselves.
Consequences: reuse/provision reviewed provider prerequisites and allow cached use when unavailable. Backup excludes provider auth/credentials. Restore into a separate cluster and preserve newer research before switching; unknown schemas fail closed. Updater signatures and OS code signing are distinct. Native Windows first; macOS, WSL, Linux deferred in that order. Remote access, local inference and external app MCP hosting remain deferred.

## DEC-008 Canonical project memory and delivery

Date: 2026-10-04.
Context: the previous consolidation explicitly retired SPEC/TASKS/EVALS; the new user request intentionally replaces that documentation structure.
Options: retain previous hierarchy or migrate ownership into the seven requested canonical files.
Chosen approach: [AGENTS](AGENTS.md) defines each document's sole role; archive superseded documents with their original dates. Keep technical design and migration as subordinate references. Carry P/D identifiers forward.
Reason: durable autonomous recovery without duplicate sources of truth.
Consequences: repo-scoped project-delivery skill and local checkpoint commits; no resurrection of old agent-loop automation, paid PR review, automatic push or merge. Three repair attempts then diagnosis. Event-based checks; never complete a failing milestone.

## DEC-009 Correctness-only lint foundation

Date: 2026-10-04.
Context: tests/type checks exist but no dedicated lint configuration.
Options: leave lint absent; mass-format/rewrite legacy code; add narrow correctness checks.
Chosen approach: development-only Ruff 0.16.10 (MIT), ESLint 10.12.0 (MIT), and @typescript-eslint/parser 8.71.0 (MIT), with exact direct versions and npm lockfile. Ruff selects E9/F63/F7/F82; ESLint selects no-async-promise-executor/no-unsafe-finally/no-constant-binary-expression.
Reason: catch suspicious execution without unrelated formatting churn. The first installation exposed ESLint 9 end-of-support; use supported ESLint 10 with Node 22.13+ (22.x) or 24+ and a compatible parser. The local Node 22.14.0 meets this requirement.
Consequences: inspect lockfile/audit, exclude generated files/build artifacts, do not use autofix in checks. Python lint is in requirements-dev only; frontend lint dependencies never enter the runtime bundle. Ruff is explicitly excluded from sidecar packaging. Formatting is whitespace validation only; a broad formatter baseline remains optional, not a silently claimed capability. See [Ruff](https://docs.astral.sh/ruff/linter/), [ESLint](https://eslint.org/docs/latest/rules/), and [parser](https://typescript-eslint.io/packages/parser/).

## DEC-010 Capability qualification is explicit

Date: 2026-10-04.
Context: version detection advertised generation and approvals before live compatibility or permission isolation was proven.
Options: infer support from installation/authentication, or require exact reviewed capability records.
Chosen approach: preserve full version identity and use a code-owned qualification registry. Authentication remains a separate observation. Protocol-only checks permit diagnostics, not inference; stream entrypoints enforce capabilities before inference.
Reason: installed binaries and signed-in accounts cannot certify model access, billing, tools or implemented approval behavior.
Consequences: no production version is live-enabled yet. Existing preview inference now fails closed until M1/M8 qualification; cached/synthetic workflows remain usable. Live qualification must add dated evidence before changing the registry. Model catalogs are not entitlement proof; retain request-level failure handling. Provider-managed ChatGPT device authorization remains the selected flow, not externally supplied tokens. References: [App Server authentication](https://learn.chatgpt.com/docs/app-server#authentication) and [model catalog limits](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server).

## DEC-011 Verify effective Codex isolation before turns

Date: 2026-10-04.
Context: installation and initialize/account-read checks missed invalid thread parameters and inherited tool defaults.
Options: trust prompts/launch flags alone, inherit developer settings, or validate application-owned configuration and actual thread permissions.
Chosen approach: an app workspace root marker bounds project discovery; reject custom profile/workspace/system startup files without changing them. Require keyring credentials and strict configuration, disable execution/extension/browser/desktop tools and telemetry, disable inherited skill/instruction context, inspect effective config/features and validate the thread's single workspace, read-only network-disabled sandbox and user-reviewed approvals before a turn. All server access requests still stop the run until the bounded approval workflow lands. Unexpected tool events fail closed as defense in depth, not as the primary permission boundary.
Reason: the exact installed version rejects the old untrusted approval mode and requires read-only as the thread-start sandbox value. Its unified_exec feature remains enabled despite user overrides; the version's source gates both command tools on shell_tool. Disabling unified_exec is therefore not claimed as a security control.
Consequences: managed/custom configurations and file-backed connection credentials require separate compatibility work; no settings or credentials are imported/deleted. No new dependency. Feature/config checks and a no-inference thread start pass for the recorded version; actual sandbox enforcement, live tool access, account/model permissions and native process cleanup still need M1-T04/T05 evidence. Model-selected apply-patch tools may exist behind the read-only sandbox; the app never authorizes their requests. Do not claim a model-facing web-only tool inventory from feature flags alone. Sources: [exact-version command-tool gate](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/core/src/tools/spec_plan.rs), [exact-version configuration schema](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/core/config.schema.json), and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
