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

## DEC-012 Access review cannot expand research policy

Date: 2026-10-04.
Context: the installed v2 protocol exposes command, file-change and permission grants that exceed this app's research tool restrictions.
Options: expose arbitrary vendor accept/amendment payloads; invent a permissive scope; or preserve the policy and provide bounded review/denial/cancellation.
Chosen approach: bind sanitized memory-only reviews to the active job/thread/turn and offer deny/continue or cancel. Never accept session grants, permission overlays, command amendments or frontend-defined scopes. Unknown/foreign/replayed requests fail closed. Term explanations cannot request access at all.
Reason: implementing a review UI is not authorization to expand tools or bypass isolation. No research use case currently needs these grants; future positive grants require a separately defined, qualified scope.
Consequences: 60-second review timeout and three requests per operation bound waiting/repetition. No new dependency or persisted record/schema change. Normalized review contracts are additive; generic progress events contain no review token or vendor arguments. Live behavior is unqualified until M1-T05, and production approval capabilities remain disabled. The protocol was inspected from the installed exact-version generated schemas for CommandExecutionRequestApprovalResponse, FileChangeRequestApprovalResponse and PermissionsRequestApprovalResponse; it supports decline/cancel or empty turn-scoped permissions.

## DEC-013 Own provider descendants before execution

Date: 2026-10-04.
Context: killing only a CLI launcher can leave its native runtime descendants alive; a failed or reconnected stream must never replay inference.
Options: discover and kill processes by name/PID ancestry; attach a job after execution starts; or create suspended and establish ownership first.
Chosen approach: on Windows, create each provider launcher suspended with no console, assign it to an anonymous non-inheritable kill-on-close Job Object without breakaway, then resume its one verified initial thread. Fail startup if assignment/thread verification fails. Close the owned job even when its leader already exited, and let OS handle closure terminate descendants if the service crashes. POSIX process groups support deterministic development/CI only; non-Windows release remains deferred.
Reason: this removes the launch-to-assignment race and avoids cleanup that discovers or kills unrelated processes. Job Objects manage lifecycle; they are not a substitute for the provider's sandbox/tool policy.
Consequences: no new dependency (stdlib ctypes and documented Windows APIs); packaged Windows behavior still requires M9/M11 validation. Cancellation attempts a bounded current-turn interrupt before closing the tree. Generator consumers close streams immediately on validation failure; events must match the active thread/turn. Pending reviews withdraw on leader exit. Reconnect creates a new explicit ephemeral run with app-owned history; interrupted jobs and state reads never replay inference. See [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects), [suspended creation](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags), and [process assignment](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject).

## DEC-014 Live probes remain separate from qualification

Date: 2026-10-04.
Context: deterministic compatibility evidence cannot certify billing, model entitlement or live tool enforcement.
Options: enable a production version after fixtures; infer quota from credits/percentages; or separate explicit probes from reviewed qualification.
Chosen approach: require the pinned protocol's account-validated ordinaryUsageAllowed=true immediately before every turn. Unknown/false permission stops; balances and percentages do not override it. A no-inference preflight and optional script-only live probes never modify the qualification registry. The interactive sign-in helper reuses provider-managed keyring authentication in the same dedicated app profile; main developer profiles and their subdirectories are rejected by the helpers.
Reason: the user's plan requires pausing for sign-in, quotas or charges, and completion requires actual acceptance evidence. A candidate URL/refused canary prompt is insufficient proof of source admission/sandbox enforcement.
Consequences: unknown included-usage status is a deliberate compatibility blocker, even if a provider might otherwise generate. Script-only probes may exercise a protocol-only version after explicit --live, but preserve authentication, model, tool, usage and lifecycle guards. They record sanitized observations and still require manual acceptance before any production capability change. No dependency or SQL change; scripts are not imported by the packaged application entrypoint. Protocol reference: installed 0.158.0-alpha.2.1 GetAccountRateLimitsResponse schema and [pinned App Server definitions](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/app-server-protocol/src/protocol/v2/account.rs).

## DEC-015 Keep permitted search separate from model-selected code mode

Date: 2026-10-04.
Context: two authenticated probes preserved fixture citations but did not exercise search. The selected model's metadata chose code_mode_only, which overrides false feature flags and hides nested web tools.
Options: enable code execution; switch model silently; or expose only the already-permitted web namespace directly.
Chosen approach: set features.code_mode.enabled=false and direct_only_tool_namespaces=["web"] only for browsing operations. Keep features.code_mode_host.enabled=false and disable_in_process_fallback=false. The pinned source selects an execution host when that latter setting is true, so its name must not be mistaken for a stronger restriction. Validate configuration and effective flags before use.
Reason: preserve the selected model and existing hosted-search scope without enabling code execution. The repaired live probe observed webSearch and an official candidate URL.
Consequences: no new dependency, model fallback or production capability promotion. This does not certify the whole advertised tool inventory or sandbox. Source: [pinned tool configuration](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/core/src/tools/mod.rs), [direct namespace override](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/core/src/tools/spec_plan.rs), [host selection](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/core/src/thread_manager.rs), and [disabled session provider](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/code-mode/src/remote_session.rs).

## DEC-016 Require native sandbox readiness independently of thread policy

Date: 2026-10-04.
Context: a readOnly thread response did not establish that native Windows sandboxing was selected/provisioned. Readiness returned notConfigured; explicitly selecting elevated mode returned updateRequired for the dedicated profile.
Options: trust the thread response; weaken to a fallback sandbox; or require elevated readiness and separate administrator-approved setup.
Chosen approach: pin windows.sandbox=elevated on Windows and require ready before any inference, including qualification. The setup helper defaults to inspection. Explicit interactive --apply requests provider-managed elevated setup without project write roots, waits for successful completion, then reopens and validates configuration/readiness. Failure/timeout preserves any completed OS provisioning and never retries or falls back automatically. OS setup requires user approval under AGENTS; none was performed in this checkpoint.
Reason: a model refusing a canary prompt is not actual sandbox evidence; missing native prerequisites must stop further generation.
Consequences: narrowly amend DEC-011's blanket profile-config rejection to accept only the provider-persisted elevated setting (bounded valid TOML, plain path, matching dedicated user layer). Extra settings, foreign layers and all other custom startup files remain forbidden. No dependencies, provider binaries or credential files are added to Git or packaging; Windows provider prerequisite provisioning and packaged acceptance remain unqualified. Source: [official Windows sandbox setup and effects](https://learn.chatgpt.com/docs/windows/windows-sandbox), [pinned readiness/setup processor](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/app-server/src/request_processors/windows_sandbox_processor.rs), and [pinned setup persistence](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/core/src/windows_sandbox.rs).

## DEC-017 Supplement native offline sandbox loopback restrictions

Date: 2026-10-04; user requested repair after approving native sandbox provisioning.
Context: the exact runtime's ready, read-only, network-disabled sandbox reached a controlled localhost listener despite its matching enabled firewall rules. A temporary WFP session blocked the same attempted connection without affecting ordinary-user connectivity.
Options: repeat ineffective setup; weaken/skip the probe; replace the runtime; or supplement the existing restriction through documented Windows filtering APIs.
Chosen approach: a developer qualification helper installs two persistent application-owned WFP filters at ALE_AUTH_CONNECT_V4/V6. Both require the exact local CodexSandboxOffline account descriptor AND IS_LOOPBACK, with BLOCK action. It uses a dedicated sublayer, requests highest priority and accepts BFE's nearest available priority only within the top 256 values. Installation/readback/removal are transactional; missing/partial/conflicting identities or policy objects fail closed. Elevated interactive --apply is explicit; --remove targets only the three validated application-owned objects. No automatic installation, elevation, runtime replacement, vendor-rule mutation or global firewall change.
Reason: enforce the already-required network-disabled boundary with an independently observed socket test, preserving hosted search/authentication in the unsandboxed provider service. The offline account is shared across native Codex profiles, so these filters also restrict loopback in other sessions using that account, including sessions that otherwise allow local binding. They do not target the normal Windows user, CodexSandboxOnline or WSL.
Consequences: no new dependency or bundled driver; stdlib ctypes calls the OS-provided WFP APIs. No third-party source is vendored. Windows x64 developer qualification only; packaging, reboot/BFE restart and clean-machine acceptance remain M9/M11 work. Removal requires the original local account/descriptor still to match; account replacement/partial policy drift needs manual review, not broad deletion. WFP inspection may require elevation; the actual non-inference enforcement probe runs as the normal user. Every explicit live qualification run first repeats actual file-write and IPv4/IPv6 TCP/UDP denials with reachable host controls. Production capability records remain disabled.
Sources: [Microsoft ALE layers](https://learn.microsoft.com/en-us/windows/win32/fwp/ale-layers), [user filtering](https://learn.microsoft.com/en-us/windows/win32/fwp/permitting-and-blocking-applications-and-users), [transactional installation and nearest available sublayer priority](https://learn.microsoft.com/en-us/windows/win32/fwp/installing-a-provider), and [persistent filter state](https://learn.microsoft.com/en-us/windows/win32/api/fwpmtypes/ns-fwpmtypes-fwpm_filter0). Provider comparison: [pinned firewall rules](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/windows-sandbox-rs/src/setup_provisioning/firewall.rs) and [pinned supplemental WFP rules](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/windows-sandbox-rs/src/wfp/filter_specs.rs).

## DEC-018 Assemble structured answers from completed Codex messages

Date: 2026-10-04.
Context: the adapter concatenated every agent-message delta, so progress commentary could invalidate a correct JSON answer. Message deltas have no phase; item lifecycle events carry optional commentary/final_answer metadata.
Options: strip arbitrary prose from generated output; trust all deltas; or correlate message items and use their authoritative completion text.
Chosen approach: require each message start/delta/completion to belong to the active turn and a single unreplayed item lifecycle. Accept at most 256 messages and one million characters each for the aggregate streamed and completed text, including discarded commentary. Retain only non-commentary completion text, emit it after a successful turn, and prefer explicit final_answer messages in item-start order. If no explicit final phase exists, concatenate completed unknown-phase messages for legacy compatibility; never infer a phase from prose. A known phase cannot change to a conflicting known value; null/omitted metadata preserves any known phase. Invalid/incomplete/replayed/oversized sequences fail with fixed diagnostics and existing owned-turn cleanup.
Reason: completed items are authoritative in the reviewed protocol. Existing structured schema, identity, citation and evidence admission remain mandatory; phase metadata cannot establish factual correctness. Delaying candidate text does not delay admitted UI sections because raw provider text was already withheld by the research and term services.
Consequences: no new dependency, contract, database schema, frontend behavior or native permission change. Normal tests use synthetic events only; this does not qualify live subscriptions or enable production generation. Reference: installed 0.158.0-alpha.2.1 ThreadItem, MessagePhase and AgentMessageDeltaNotification definitions, plus [official App Server item lifecycle](https://learn.chatgpt.com/docs/app-server#items).

## DEC-019 Recognize pending access declarations without permitting execution

Date: 2026-10-04.
Context: command/file access reviews follow an item/started declaration. The adapter rejected that declaration before the existing DEC-012 deny/cancel workflow could receive the request.
Options: retain the unreachable review; permit arbitrary command/file events; or track only a bounded pending/denied/completed lifecycle.
Chosen approach: recognize at most three unique inProgress command/file declarations per research turn, without output or exit status. Require the following access request to match its item kind and ID, in addition to the existing thread/turn/RPC correlation. Only a normal denial allows the matching declined completion; cancellation, expiry and consent revocation stop the run. Reject unmatched, repeated, executed, output-producing or unresolved activity before any candidate answer is released. Cached-evidence term operations still reject all command/file activity and access requests. Permission requests retain their existing empty turn-scoped denial behavior.
Reason: a pending declaration must reach the established denial workflow, but is not execution authorization or evidence that sandbox restrictions held. Launch configuration and actual OS enforcement remain the primary boundaries; event validation is defense in depth.
Consequences: no scope, grant, provider/model, dependency, license, contract, database, frontend or packaging change. The adapter never issues command execution or grants access. Deterministic full-sequence tests do not replace real live denial or model-facing tool inventory acceptance; production capabilities remain disabled. Reference: installed 0.158.0-alpha.2.1 event/request schemas and the [official App Server approval ordering](https://learn.chatgpt.com/docs/app-server#approvals).

## DEC-020 Restrict selected-model metadata and expose denial-only requests

Date: 2026-10-04; explicitly approved by the user after reviewing the concrete proposal and its security scope.
Context: selected-model metadata enables code-mode, patch and asynchronous-input tools despite disabled feature flags. The installed protocol has no final built-in tool inventory endpoint. The no-inference prototype accepted a same-model restricted catalog in both browsing modes.
Options: retain the qualification blocker; switch runtime/model; or narrow an app-owned temporary catalog for the already-selected model and exercise the existing denial workflow through its dedicated request tool.
Chosen approach: read bounded model metadata in the isolated authenticated profile, preserve the selected identity and non-tool metadata, and narrow tool mode to direct, shell to disabled, patch to null, experimental tools to empty and tool discovery to false. Strictly disable plan/input/time and other auxiliary tools in configuration. Research may advertise hosted web and request_permissions; the latter can only receive empty turn-scoped permissions or terminate on cancellation/expiry. Cached explanations advertise no tools. Validate identity, metadata shape, policy layers and temporary-file integrity before inference; clean up owned processes and catalog files on terminal paths. No permission grant, extra network/shell/file access, provider/model switch, API billing or administrator setup is authorized.
Reason: make advertised tools agree with the existing execution boundary and obtain actual denial/cancellation evidence without allowing execution. Configuration/source inspection alone does not qualify the live integration; Q, actual no-inference checks and bounded live inventory/denial/cancellation/source acceptance remain required.
Consequences: no new dependency, vendored provider source, license, database schema or frontend contract. Temporary provider metadata stays outside the library and Git. Production qualification remains disabled until required acceptance passes. See [investigation and proposal](docs/verification/2026-10-04-codex-tool-policy-investigation.md) and the official [model catalog configuration](https://learn.chatgpt.com/docs/config-file/config-reference), [diagnostic commands](https://learn.chatgpt.com/docs/developer-commands) and [permission request protocol](https://learn.chatgpt.com/docs/app-server).

## DEC-021 Measure the installed tool declaration without account traffic

Date: 2026-10-04.
Context: the pinned App Server cannot return its finalized built-in tool registry; prompt-input diagnostics omit it, and model self-reports cannot certify it.
Options: persist sensitive request traces; proxy authenticated traffic; replace the runtime; or inspect installed-binary request serialization using a credential-free local test transport.
Chosen approach: obtain the restricted selected-model catalog and provider capability flags through the authenticated no-inference connection, then close that process. Launch the same native executable in fresh credential-free profiles with identical catalog/tool policy and a transport-only provider pointing to an authenticated loopback peer. Verify no account, matching typed capabilities, effective policy/layers and selected thread model. Read one bounded synthetic request in memory, validate the complete Responses Lite additional_tools declaration, retain only allowlisted names/schema hashes and reject with an empty HTTP error. Close listeners, processes, catalogs and profiles. Never forward requests, supply account credentials, execute tools or produce model output.
Reason: direct installed-binary serialization supplies the missing measurement. Pinned-source review establishes limited equivalence: the same OpenAI provider identity and capability flags select the same serializer; account-dependent history/image tools are disabled; cloud skills, message-board, plugins, agents and other auxiliary contributors are disabled. Real subscription inference, source capture and denial/cancellation remain separate live evidence. A local transport does not perform live inference.
Consequences: no new dependency, vendored runtime/source, license, database or installer change. Production retains its subscription transport. The helper never promotes qualification. Any reviewed enablement must be limited to the measured Windows binary, selected model/catalog and policy; this evidence does not cover another OS, model, binary or tool configuration. See [inventory evidence](docs/verification/2026-10-04-codex-wire-inventory.md) for hashes, equivalence review and verification.

## DEC-022 Bind live qualification to the measured runtime scope

Date: 2026-10-04.
Context: direct inventory and separate live acceptance cover one Windows binary/model/catalog/policy, while the original qualification registry distinguished versions only.
Options: enable every installation/model reporting that version; retain a blanket block despite passing evidence; or enforce the actual reviewed scope.
Chosen approach: keep version-only discovery protocol_only, require native Windows executable content identity before capability enablement, and require provider-managed ChatGPT authentication. Immediately before production turns, check the measured model, catalog content/integrity, executable digest, typed provider capability tuple and normalized policy digest against reviewed constants. Model/provider fallback, API billing and permission grants remain prohibited. New binaries/models/catalogs/policies require new affected evidence and a reviewed code change; never populate qualification from settings, provider output or successful probe exit.
Reason: enable only behavior supported by combined direct inventory, deterministic negative tests and separate live acceptance. Normalized streaming describes application events and completed answer delivery, not exposing raw reasoning or progress prose.
Consequences: no dependency, SQL, frontend contract, license or packaging change. The default model can be used only if it resolves to the measured model; other discovered models remain unsupported for generation. WSL and other platforms remain unqualified. The explicit --live --production developer check exercises the normal production path after Q and fresh enforcement, with no qualification bypass. See [scope and M1 review](docs/verification/2026-10-04-codex-scoped-qualification.md). Native/public release acceptance remains at its owning milestones.

## DEC-023 Bind research to independent identity and document permissions

Date: 2026-10-04.
Context: the preview accepted model-defined identities, domain-wide permissions and recently created bundles as current evidence. Matching a name in a document did not establish listing/contract scope, and a new retrieval did not refresh old underlying facts.
Options: retain model attestation; add fixed ticker eligibility; or introduce independently retrieved identity records, document-scoped permissions and conservative cache reuse.
Chosen approach: verify all identity attributes against an application-owned resolver before publishing new evidence. The initial SEC listing adapter uses its public, changing exchange/ticker/CIK map with bounded parsing, exact matching and no inferred instrument type/currency. Store a content fingerprint and complete identity fingerprint. Ambiguous, unavailable, stale or changed scopes stop publication; other categories require their own independently reviewed adapters. Explicit code-owned document rules carry rights references/review dates independently of credibility. Unknown rights retain links/metadata only; raw text and claimed derivatives cannot enter notes under narrower rights. Filing paths must match the independent issuer CIK. Manual/failure paths clear model verification, dates, excerpts and hashes.
Reason: implement the existing DEC-004 admission boundary without a fixture universe or treating a model's output as identity evidence. Current SEC coverage is a first adapter, not all-category qualification. Unknown type permits general overview evidence but suppresses type-dependent facts.
Consequences: no new dependency, provider change, permission grant or SQL migration. Optional bundle reader level and identity proof preserve old saved versions with unknown defaults. Online cache reuse requires exact scope/language/level, an independent identity recheck, current registered rights and source dates; latest requests always recheck until adapter-specific coverage can prove currency. Undated evidence remains readable but cannot satisfy fresh online reuse. SEC requests require an explicitly configured local contact and share a five-starts/second bound; no email is inferred from subscriptions, retained in evidence or supplied by the project. Explicit live qualification remains required. Developer-only environment configuration must receive packaged onboarding before release.
Sources: [SEC listing metadata and fair access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), [SEC API identity metadata](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), and [SEC text reuse policy](https://www.sec.gov/about/privacy-information). These permissions do not cover artwork or arbitrary external sites.

## DEC-024 Add free FIGI metadata without merging identity namespaces

Date: 2026-10-04.
Context: SEC's listing map does not establish instrument type, share-class identifiers or derivative contracts. The user supplied a contact for the developer SEC check; public distribution of that personal address is not authorized by this check.
Options: infer missing attributes from model output; require a paid reference-data service; or add a bounded public identifier registry while preserving uncertainty.
Chosen approach: use unauthenticated OpenFIGI v3 mapping/search for exact FIGIs, tickers and names. Preserve listing/composite/share-class identifiers and source descriptions. Validate check digits and complete response shape; incomplete pages, missing metadata, duplicates, errors and excessive ambiguity require selection before inference. Conservative classification leaves ETP-versus-ETF, generic contracts and unreviewed kinds unknown. Currency and current trading status are not inferred. General queries retain separate SEC and FIGI choices; qualified IDs select one registry. No ticker/name-based merging or automatic CIK attachment.
Reason: independently retrieved metadata can establish a source-specific instrument identity without claiming financial evidence or complete source coverage. Source permissions register only identity metadata, not arbitrary website content or logos. The FAQ describes metadata reuse; terms dedicate identifiers to the public domain. Their accuracy is not guaranteed.
Consequences: no dependency, API key, subscription, charge, SQL or archive-format change. Only two fixed read-only lookup endpoints accept bounded JSON POST through the existing pinned-address HTTPS transport. Shared process limits stay below anonymous quotas, with no automatic retry or credential fallback. Cache is bounded and expires after one hour. Raw API errors/cursors remain outside application results. Public app SEC contact/onboarding and source notices remain release work; the supplied personal address remains process-local.
Sources: [API and anonymous limits](https://www.openfigi.com/api/documentation), [reuse FAQ](https://www.openfigi.com/about/faq), [identifier terms](https://www.openfigi.com/docs/terms-of-service), [check digit](https://www.openfigi.com/docs/figi-check-digit.pdf), and [current type vocabulary](https://api.openfigi.com/v3/mapping/values/securityType2). Live category coverage must be recorded separately from deterministic classification tests.

## DEC-025 Keep issuer financial observations separate from instrument identity

Date: 2026-10-04.
Context: instrument metadata is insufficient for numerical research, and SEC company-concept observations cover the filing entity rather than a share class. Historical fiscal labels can describe the filing containing a comparative period.
Options: attach issuer numbers by ticker alone; infer missing units/quarters from prose; or retrieve bounded official observations only after explicit registry concordance.
Chosen approach: initially associate only independently resolved common-stock venue records whose full normalized issuer name, symbol and reviewed venue mapping exactly match one current SEC listing record. Preserve both proofs and identities separately; never mutate the instrument's identifiers or merge its namespace. Country composites, near names, multiple matches and unreviewed types remain unconfirmed. This supplements DEC-024 with a narrow, explicit issuer association; it does not permit name/ticker-only CIK attachment. The first reviewed venue vocabulary covers NYSE and three Nasdaq listing tiers from OpenFIGI's published exchange-code metadata.
Reason: SEC's source supplies the issuer CIK; the separate FIGI source establishes a specific instrument/venue and common-stock type. The concordance remains limited by both sources' accuracy and cannot establish other instruments, current trading status or security-level financial applicability automatically.
Consequences: the initial adapter parses registered US-GAAP concepts using decimal text, original units, exact dates, accession/form and content hash. Duration length determines annual/quarter/other presentation; reported fiscal labels are retained without reassignment. Preserve latest reported and superseded observations; simultaneous latest conflicts stay unresolved. Similar concepts/currencies never splice; no derived Q4, split adjustment, prices, total return or historical valuation without independent inputs. Default windows preserve five annual years/twelve quarters and revisions with missing periods explicit. Sources/errors/cancellation are bounded and use existing SEC fair-access controls. No dependency, API key, charge, SQL or archive-format change in the parsing/adapter slice. Persisted numeric admission and research orchestration still require their own checks.
Sources: [SEC whole-entity API scope and units](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [SEC issuer identifiers](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), and [OpenFIGI exchange-code metadata](https://www.openfigi.com/docs/OpenFIGI-exchange-codes.csv), reviewed on the decision date. The registry covers official concept JSON only; no price/news rights are implied.

## DEC-026 Persist exact issuer observations outside model claims

Date: 2026-10-04.
Context: Claim.value uses a floating-point wire number and cannot safely represent original financial precision or filing revisions. Provider output must not certify its own numeric evidence.
Options: overload model claims; add a separate SQL table/migration; or add a typed optional financial document to immutable evidence snapshots.
Chosen approach: an optional `financials` document retains the independent issuer proof, the association checkpoint, exact decimal strings, units/periods, filing provenance, source references, revisions and explicit gaps. Only the structured adapter admission path constructs it; ResearchResult has no such field. EvidenceBundle validation recomputes scope/source/value/period/revision consistency at publication, restore and use. Current unconflicted observations may become factual context; notes/model numbers and superseded/conflicting values cannot become current numeric inputs.
Consequences: generated schema/TypeScript change; no dependency or SQL revision. Archive format 1 remains readable by the newer app, with absent financial fields defaulting to unknown/null. Old apps may reject new fields; rollback remains unqualified until M10. Archive hashes establish consistency rather than source authenticity, and restored dates never become current verification. JSON/Markdown exports retain all versions and gaps. Price/corporate-action coverage stays unavailable. Online numeric cache reuse remains disabled until the structured refresh policy lands. Research scheduling/publication integration and chart compatibility remain separate acceptance tasks.

## DEC-027 Bind filing dates to independent SEC submission metadata

Date: 2026-10-04.
Context: downloading an old page today does not establish current information. Model dates and generic date-like text cannot certify a filing's publication/report period.
Options: accept model dates; scrape arbitrary page dates; or corroborate exact registered filing URLs against the official issuer submissions index before page support checks.
Chosen approach: retrieve the bounded SEC submissions index for an independently verified issuer. Match exact CIK/name and correlated columns, then construct canonical issuer/accession/document URLs for reviewed financial/event forms. Preserve filing date separately from the filing's report date. The first twenty metadata candidates inform gap research; metadata alone cannot admit narrative claims. Independently read at most the two newest indexed documents before inference and provide their exact permitted excerpts/IDs. Model copies cannot overwrite these sources; alias citations reuse the verified page. Failed prefetched pages are not retried within that research job. An independently read supported filing receives a typed index fingerprint/date proof. Model-supplied proof fields are discarded. Unknown dates, unsupported forms/pages and missing current news/price coverage remain explicit.
Consequences: one index request and up to two prefetched document requests per applicable research job, using existing SEC contact/rate/size/cancellation controls. Access/rate/server failure stops remaining prefetched documents. No dependency, account, API key or broader source permission. Optional Source metadata is generated into contracts and preserved through archive validation/export/actual restore, with legacy null defaults and no SQL/archive version change. Official filings are partial event coverage, not a complete news or quote feed. Source identity, rights, temporal and proof references are revalidated; internal archive consistency does not authenticate externally rewritten data. A separate production-path live helper requires observed search, page opening, follow-up activity and independently dated claim support; it cannot promote runtime capabilities or certify other providers.
Reference: [SEC submissions API structure and update behavior](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), reviewed 2026-10-04. Runtime web action categories come from the locally inspected installed app-server protocol schema; raw queries, page text and provider diagnostics are not qualification report fields.

## DEC-028 Separate browsing observation from fact admission and reuse original citations

Date: 2026-10-04. Authorization: the user explicitly approved observing agent browsing/citations with independent fact checks and requested original sources alongside reused database facts.
Context: the last M2 gate incorrectly treated completed web-event results as the model-visible page body. In pinned Codex, response.results becomes event metadata, while response.output is passed separately to the model. Matching a quotation against arbitrary strings in event metadata cannot establish what the model read. Historical failures remain historical failures.
Chosen approach: observe completed search, absolute-URL page navigation and subsequent investigation. Correlate a navigated URL with independently verified dated cited evidence; collect bounded returned URL references and structured failure indicators when exposed, without retaining raw results. Describe unavailable content-level telemetry explicitly. Separately require independent identity, rights, support, dates, financial units/periods and freshness checks. Normal paraphrases remain cited explanations/notes; only independently admitted facts and structured observations become factual context or numeric inputs. This replaces the invalid event-body quotation check, not the fact-admission boundary.
Persistence: reuse immutable evidence snapshots already storing claims and their complete source records. Include original version/date/source metadata in bounded same-identity conversation context, with version-specific citation IDs to prevent collisions. Never hydrate notes as facts or change historical source dates. Reusing an old URL in a newly published fact still requires independent verification; unavailable pages leave the original saved answer accessible without certifying a new fact.
Consequences: no new dependency, service, permission, billing path, SQL migration or archive-format change. Existing version-specific source navigation and exports remain authoritative. A new Q/D and explicit live result are required before M2 acceptance; no retrospective pass or runtime capability expansion.
Sources: pinned [web tool projection](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/ext/web-search/src/tool.rs) and [model output construction](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/ext/web-search/src/output.rs), reviewed on the decision date.
