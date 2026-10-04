# Codex tool-policy investigation — 2026-10-04

Scope: resume M1-T05 after fd6bfea. The user requested repair of the remaining inventory/denial blockers. No production policy, credentials, selected model, qualification registry or Windows filtering rules were changed.

## Observations

The documented `codex debug models` command, run with the dedicated application profile and the app's restrictive configuration, returned exactly one gpt-6-astra metadata entry. Only these normalized nonsecret fields were retained:

| Field | Observed value |
| --- | --- |
| tool_mode | code_mode_only |
| apply_patch_tool_type | freeform |
| shell_type | unified_exec |
| use_responses_lite | true |
| supports_search_tool | true |
| experimental_supported_tools | send_user_message_async, clock |

This explains why disabling feature flags is not a complete model-facing tool allowlist. Pinned source in core/src/tools/spec_plan.rs adds patch/clock/async-input tools from model metadata, and tools/mod.rs gives a model-selected tool mode precedence over the feature switches. The execution host remains disabled by the current policy; advertising a tool does not establish execution authority.

`codex debug prompt-input` returned only four message items, without final tool schemas or authoritative tool-namespace metadata. It cannot certify the requested inventory. Both debug commands reject root --strict-config; the successful diagnostic runs first passed the ordinary strict App Server preflight, then omitted that unsupported diagnostic-only flag. The production launch and its validation were unchanged. Full model/prompt output stayed in bounded process memory and was not printed or retained.

Generated the exact installed binary's full protocol schema with `app-server generate-json-schema --experimental`. Neither regular nor experimental request schemas expose the internal ToolPolicy allowlist or a complete built-in tool inventory endpoint. `server/diagnostics` exposes process/gauge observations, not tool schemas. `experimentalRawEvents` describes internal raw response events, not inventory, and was not enabled. `thread/shellCommand` explicitly runs unsandboxed; it was rejected as a test approach and never invoked.

## Fresh verification and bounded live check

The PowerShell project-delivery milestone wrapper passed **600 Python tests**, seven frontend tests, Ruff/ESLint, contracts, documentation/whitespace, static evaluations, TypeScript and the build. Existing Starlette/httpx warning only.

At **2026-10-04 03:00:09 UTC**, a fresh strict preflight and actual extended write/IPv4/IPv6 TCP/UDP enforcement checks preceded one bounded subscription turn. The unchanged gpt-6-astra profile was asked to invoke one code cell emitting a synthetic marker, without shell/files/network/other tools or retries. No actual function-output item, executed marker or approval request was observed; no adapter rejection occurred, and the owned process closed. This remains **unexercised denial**, not passing evidence. It did not repeat the earlier file-write prompt. Fresh ordinaryUsageAllowed=true was required; no model/provider fallback, API billing or additional permission was enabled. Do not continue spending turns on equivalent refusal prompts.

## Restricted-catalog prototype

An ignored, no-inference prototype used the documented startup-only model_catalog_json setting with temporary metadata for the same selected model. It changed only tool_mode=direct, apply_patch_tool_type=null, shell_type=disabled, experimental_supported_tools=[] and supports_search_tool=false, plus tools.update_plan.enabled=false and tools.experimental_request_user_input.enabled=false. All other selected-model metadata was retained temporarily; the file was removed when the probe finished. No modified catalog was installed in the application profile or committed.

Initial prototype validation found that config/read omits the tools table from its normalized Config object, although its strict highest-priority sessionFlags layer preserves both enabled=false values. After verifying those exact flags in that layer and all existing effective policy fields, **both browsing-disabled and browsing-enabled thread handshakes passed**, preserving gpt-6-astra and ready native sandbox status. No turn/start was sent. This establishes configuration compatibility only, not final inventory, live search or approval acceptance.

## Proposed repair — awaiting scope approval

| Component | Concrete change | Authority retained |
| --- | --- | --- |
| Model tool metadata | Add an app-owned, bounded temporary catalog derived from the explicitly selected provider model; remove execution/patch/clock/async-input metadata and select direct tool mode. Validate catalog identity and policy at startup; reject malformed or changed metadata. | Same gpt-6-astra, ChatGPT account, entitlement/usage gates and no fallback. |
| Research tool exposure | Keep permitted web search and expose request_permissions solely to exercise and support the existing deny/cancel review. Disable all tools for cached-evidence operations. | No positive grants: only empty turn-scoped permissions, denial or cancellation; no shell, patch, code host, MCP, browser or desktop execution. |
| Validation | Add deterministic metadata/flag drift, malformed catalog, cleanup and approval tests. Run Q, repeat no-inference checks, then bounded live search, real denial/cancel and inventory review. | Unknown or missing evidence still blocks qualification; no automatic registry promotion. |

Enabling even a request-only tool changes the currently disabled tool surface. AGENTS requires an established decision or user approval for scope/security changes; DEC-012 authorizes denial handling but does not explicitly authorize exposing a previously disabled permission-request tool. This proposal therefore stops before changing production policy or running an inference with that new exposure. Approval would authorize this specific restricted-catalog/request-only approach, not additional execution permissions or a waived acceptance requirement. If the pinned runtime cannot provide sufficient inventory evidence after this repair, retain the blocker rather than claiming completion.

No new dependency, paid service, public network exposure, provider replacement, model switch, database migration or packaging change is proposed. Remaining unknowns are documented instead of weakening EVALS. Local documentation/evidence may be checkpointed; push/PR/merge/publication remain unauthorized.

References: [official developer diagnostics](https://learn.chatgpt.com/docs/developer-commands), [model catalog configuration](https://learn.chatgpt.com/docs/config-file/config-reference), [App Server permission requests](https://learn.chatgpt.com/docs/app-server#approvals), and the locally reviewed exact-version generated schemas/source identified above.
