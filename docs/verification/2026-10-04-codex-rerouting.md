# Codex model rerouting — 2026-10-04

Scope: M1-T05b, enforcing the existing selected-model/no-fallback requirement during generation. M1-T05a was verified and committed as 168ef15 before this task began. The parent live qualification remains blocked pending account-side included-usage confirmation and remaining acceptance; no inference was requested for this repair.

## Finding and repair

The installed 0.158.0-alpha.2.1 schema defines ModelReroutedNotification with threadId, turnId, fromModel, toModel and reason. The [official App Server event reference](https://learn.chatgpt.com/docs/app-server#events) describes the provider reporting a route to another model. The existing adapter rejected substituted models at thread creation but ignored this notification during a turn.

A new synthetic regression failed before implementation because a rerouted turn completed without RuntimeFailure. The adapter now correlates model/rerouted to the active thread/turn and stops on every such notification. Even missing/malformed routing detail or an equal from/to name cannot turn that notification into permission to continue. Failure exposes only fixed text; the existing finally path interrupts and closes the owned turn. Buffered answers are never emitted, settings remain unchanged and no automatic request or fallback follows. Ordinary safety-buffering telemetry alone remains informational.

## Verification

Focused command: `.venv/Scripts/python.exe -m pytest tests/desktop/test_codex_models.py tests/desktop/test_codex_messages.py tests/desktop/test_runtime_recovery.py -q --tb=short` — **84 passed**. Cases exercise reroutes before/after a buffered final answer, foreign thread/turn, missing/malformed/equal-model metadata, owned-turn cleanup, one request only and no raw values in normalized output. Synthetic app-service cases confirm failed rerouted research creates no bundle/asset, retains the original model snapshot/settings and excludes routing text from the job/events/library; safety-buffering telemetry without rerouting still completes.

Milestone Q: the shared PowerShell `verify-milestone.ps1` wrapper passed **546 Python tests**, seven frontend tests, Ruff/ESLint, generated contracts, documentation/whitespace checks, static evaluations, TypeScript and production build. The existing Starlette/httpx deprecation remains. Full source/test/document diff reviewed before the local checkpoint. No UI, contract, database schema, native process, sandbox or dependency change. This checkpoint therefore requires the deterministic Q/C/R lanes; prior D/native evidence retains its original scope/date. Live rerouting/model identity and the rest of subscription acceptance remain unqualified. The adapter can reject provider-reported changes; this is not proof of an unreported upstream model identity.

No provider credentials, raw provider diagnostics, billing changes, administrator prompts, remote Git operations or production capability promotion occurred.
