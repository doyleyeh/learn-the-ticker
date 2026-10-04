# Codex message assembly — 2026-10-04

Scope: M1-T05a, an independent deterministic repair within incomplete M1. The parent live qualification task still requires account-side included-usage confirmation and remaining manual/live acceptance. No subscription request, credential access or native permission change is part of this checkpoint.

## Reproduction and repair

Source inspection found that the adapter forwarded every agent-message delta, ignoring phase metadata carried by item events. A synthetic commentary message followed by valid research JSON reproduced the failure: the normalized answer began with PRIVATE_PROGRESS_SENTINEL instead of the JSON object. The failing regression was run before implementation.

The installed 0.158.0-alpha.2.1 schema and [official App Server documentation](https://learn.chatgpt.com/docs/app-server#items) identify item/completed as authoritative and distinguish optional commentary/final_answer phases. The adapter now correlates and bounds message lifecycles, discards known commentary, prefers completed explicit final answers and retains unknown-phase compatibility when no final phase exists. It publishes candidate text only after successful turn completion. Existing schema/evidence gates remain intact; see [DEC-018](../../DECISIONS.md#dec-018-assemble-structured-answers-from-completed-codex-messages).

## Verification

Focused command: `.venv/Scripts/python.exe -m pytest tests/desktop/test_codex_messages.py tests/desktop/test_codex.py tests/desktop/test_approvals.py tests/desktop/test_runtime_recovery.py tests/desktop/test_terms.py tests/desktop/test_application.py -q` — **125 passed**. An initial new persistence assertion matched the term fixture's pre-existing UNVERIFIED_PRIVATE_NOTE; it was corrected to check the two exact synthetic provider sentinels, preserving that existing note and all persistence assertions. No implementation repair failures remain.

Coverage includes missing/null phases, explicit final precedence, authoritative completion text differing from deltas, malformed/conflicting phases, unknown/replayed/completed IDs, missing completions, aggregate text/item limits (including discarded commentary), provider failure/prohibited tools after an answer, and cancellation with a buffered answer. Synthetic research and cached-only term operations accept valid completed JSON, reject invalid completed JSON even when earlier deltas were valid, and exclude provider sentinels from events/library state. Existing approval, current-turn interruption and no-replay tests pass.

Milestone Q: the shared PowerShell `verify-milestone.ps1` wrapper passed **532 Python tests**, seven frontend tests, Ruff/ESLint, generated contracts, documentation/whitespace checks, static evaluations, TypeScript and production build. The existing Starlette/httpx deprecation remains. No contract, UI, database schema, native process or sandbox-policy implementation changed; B/D/native probes are not new acceptance requirements for this adapter-only checkpoint. This does not replace the outstanding milestone-level live/browser/native acceptance. Complete source/document/test diff reviewed before the local checkpoint; no secrets, raw provider payloads or unrelated files included.

## Limits

Fixtures certify deterministic normalization, not selected-model live behavior. Production qualification remains protocol_only, with generation disabled. No new dependency, API billing, runtime/model fallback, provider transcript, remote Git action or release-readiness claim.
