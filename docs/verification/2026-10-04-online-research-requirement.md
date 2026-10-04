# Autonomous online research requirement checkpoint

Date: 2026-10-04. Documentation clarification requested by the user; no runtime, permission, subscription transport, dependency or packaging change.

## Required behavior

The user explicitly requires agents to retain autonomous search and browsing for current market, ticker and news information alongside financial/news APIs. SPEC P-011 now states live search, public page reading and follow-up research within cloud consent and qualified scope. PLAN M2, TASKS M2-T03/M8, EVALS, README and review guidance carry the corresponding positive acceptance and freshness checks. Public source-page retrieval does not require giving the model control of the user's local browser or a general shell.

## Observed implementation and limits

- `backend/app/codex_policy.py` retains `web_search=live` and the direct web namespace for research, while cached-only turns disable web search. Local browser/computer tools remain disabled.
- The [complete installed inventory](2026-10-04-codex-wire-inventory.md) observed `web.run` and denial-only `request_permissions` for the exact reviewed research scope. The separately inspected pinned web tool source handles search, open-page and find-in-page actions. Source/configuration inspection is not a substitute for exercising each action live.
- [Scoped production acceptance](2026-10-04-codex-scoped-qualification.md) passed live source search/support, denial/cancellation and cached preservation. Its source probe did not separately establish an open-page/follow-up sequence; do not retroactively claim that coverage.
- The current research cache still has a general 24-hour reuse path. Source-specific freshness, latest-request refresh, structured financial/news orchestration and complete page-reading acceptance remain M2 work. Gemini/Claude adapters remain unqualified and require their own M8 evidence.
- No new cloud inference, sign-in or financial/news retrieval was performed for this documentation checkpoint. Existing runtime scope and milestone states are preserved.

## Verification

- `.venv/Scripts/python.exe -m scripts.verify milestone` passed: **755 Python tests**, **seven frontend tests**, Ruff/ESLint, schema/type drift, local Markdown links, whitespace, static evaluations and TypeScript/production build. Only the existing Starlette/httpx deprecation warning remains.
- Reviewed the documentation diff for requirement ownership, consistency with current implementation and honest separation of required versus verified behavior. No runtime/tool policy or qualification constants changed.
- Final document-link and whitespace checks passed after recording the results. No additional live, database, browser or native acceptance was claimed for this documentation-only change.

This checkpoint does not complete M2 or establish new live capability. Continue with M2-T01 before the dependent M2-T03 research workflow.
