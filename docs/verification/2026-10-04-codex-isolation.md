# Codex configuration and no-inference thread verification — 2026-10-04

Scope: M1-T02, P-040/P-041. M1 and public v1 remain incomplete. No account sign-in, model turn, billing change or remote Git action occurred.

## Findings and changes

The installed Codex 0.158.0-alpha.2.1 accepts initialize/account-read but rejects the former untrusted approval setting and readOnly thread-start value. Its generated protocol uses read-only in requests and a readOnly sandbox object in responses. A dynamicTools field would require experimentalApi negotiation; the app does not send it or expose client tools.

The exact-version source confirms unified_exec user overrides are insufficient to remove command tools; shell_tool gates both command execution and stdin. Model-dependent apply-patch tools can exist behind the read-only sandbox, so neither feature flags nor a fixture establish a web-only tool inventory. All access requests continue to fail closed. Links and rationale are in [DEC-011](../../DECISIONS.md#dec-011-verify-effective-codex-isolation-before-turns).

The adapter now verifies application-owned process configuration, effective feature state and thread permissions before turn/start. A root marker bounds project configuration discovery. Custom profile/workspace/system configuration and file credentials stop startup without being read into logs, overwritten or deleted. Keyring storage is required. Host execution/extensions/browser/desktop access, instruction/skill inheritance and telemetry are disabled in configuration. Sensitive provider details never enter user-facing failures; unexpected tool events abort.

## Verification

- Focused deterministic command: `.venv/Scripts/python.exe -m pytest tests/desktop/test_codex_policy.py tests/desktop/test_codex.py tests/desktop/test_runtime_policy.py tests/desktop/test_terms.py -q`: 108 passed. Covers policy drift, custom configuration before spawn, malformed/incomplete features, workspace/instruction/sandbox changes, preserved file credentials, process cleanup and unexpected tool activity.
- Explicit installed check: `.venv/Scripts/python.exe -m scripts.smoke_codex_protocol`: passed after the repairs below. Fresh profile, synthetic hostile parent instructions/MCP config, actual effective config/features, account-read, thread-start and single workspace/read-only network-disabled response. No inherited account or inference. Exact capability reporting remains protocol_only, with generation/browsing/approvals disabled.
- During implementation the expanded installed smoke failed on two current-documentation OTEL fields absent in the pinned version. Diagnosis used the exact-version schema; removed those fields, retaining all three exporters disabled. A subsequent comparison found two tool-setting fields omitted by config/read's ToolsV2 serialization. Those optional settings were removed; unsupported server requests remain denied. The repaired installed check passed; no failed check was relabeled as passed.
- Shared milestone gate: `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` passed: 354 Python tests (including two additional malformed-path cases), static evaluations, seven frontend tests, correctness lint, contract drift, documentation links, whitespace, TypeScript and production build. Existing Starlette/httpx deprecation warning remains. The installed smoke passed again after the final path-validation change.

## Limits and continuation

No live account/model entitlement, actual model tool inventory, inference sandbox enforcement, quotas, cancellation tree or installer evidence is claimed. The installed profile remains protocol-only in the code-owned registry. Complete M1-T03/T04, then the explicit live harness and M1-T05 account qualification. Custom managed environments require a future supported configuration policy; no admin requirement is bypassed.

The M0 exit paragraph was corrected to refer to foundation checks; live/native release checks remain in their owning milestones. This removes an accidental boilerplate contradiction without changing release requirements.
