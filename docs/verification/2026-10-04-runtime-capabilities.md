# Runtime capability verification — 2026-10-04

Task: M1-T01. Foundation checkpoint: 2ea989e.

## Change and evidence

RuntimeCapabilities distinguishes exact version, authentication and unqualified/protocol_only/live qualification. Streaming/cancellation defaults are disabled. A code-owned registry recognizes installed Codex 0.158.0-alpha.2.1 for protocol-only diagnostics; no runtime has production live capabilities. Discovery is bounded/sanitized and retains prerelease/build identity. Codex and CLI stream entrypoints reject unqualified inference and reject browsing for cached-only capabilities.

Focused runtime/Codex/term suite: 64 passed. New scenarios cover malformed/oversized/nonzero version processes, exact prerelease identity, false capabilities despite installation/sign-in, synthetic reviewed capability limits, unsupported versions before protocol/inference launch, and cached-only browsing denial.

The installed protocol smoke passed initialize/account-read against a fresh isolated profile with browsing disabled. Authentication was required; generation, browsing and approvals remained false. No login, device-code request, model inference or account borrowing occurred.

Full PowerShell milestone gate passed 308 Python tests, static evaluations, seven frontend tests, Ruff/ESLint, non-writing schema/TypeScript checks, Markdown links, whitespace, TypeScript and Vite build. Generated schema and TypeScript were deliberately regenerated with the new capability field. Existing Starlette/httpx deprecation remains.

## Limits and next task

M1-T01 is complete; M1 is not. No live generation, model entitlement, billing, complete tool isolation, interactive approvals or process-tree qualification is claimed. No UI layout, database schema or library format was changed. No new dependency was added.

Next is M1-T02: inspect effective provider configuration/tools and harden process isolation against inherited hooks/MCP/instructions before any live qualification. Current official references: [App Server](https://learn.chatgpt.com/docs/app-server), [configuration](https://learn.chatgpt.com/docs/config-file/config-reference), and [model catalog versus access](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server). Local generated protocol schemas are ignored inspection artifacts, not committed vendor copies.
