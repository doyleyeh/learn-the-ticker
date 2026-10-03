# Model discovery and selection — 2026-10-04

Scope: M1-T03a, P-040/P-041. M1-T03b approvals and the rest of M1 remain incomplete. No live subscription sign-in or inference occurred.

## Implemented

Normalized, bounded subscription catalogs; explicit selected-model persistence; current-default resolution; no model/provider fallback; rejection of malformed, ambiguous, hidden/non-text or removed entries as applicable. Authenticated local API and Connections expose status and catalog limitations. Settings changes are serialized and active-work checks repeat after asynchronous model discovery. Research and term jobs snapshot the selected settings; cached results remain usable independently of provider selection.

No new dependencies or SQL migration. [Migration compatibility](../MIGRATION.md#database-and-library-compatibility) records additive Settings handling and the unqualified older-app rollback boundary. The shared Pydantic/schema/TypeScript contract pipeline includes the new catalog types.

## Checks

- Focused provider/application/term suites: 124 passed before the final concurrency scenario. The final model suite passed 22 tests, including a request that becomes active while a settings update awaits the catalog. An initial fixture-construction TypeError was corrected; product assertions were unchanged.
- Database lane: `LTT_PG_BIN=C:/Program Files/PostgreSQL/17/bin python -m scripts.verify database` passed private-service, transaction/recovery and real full-library restore/restart checks. An explicit synthetic model survived restore and restart; cloud consent reset to off. No existing system cluster was modified.
- Installed no-inference protocol checks passed with model fallback disabled in thread-start. No live model entitlement is claimed.
- Browser: in-app Browser backend unavailable; used the Playwright CLI skill with its isolated ltt-models browser and synthetic preview. Missing saved selection remains visible with a warning; End/Enter selects and saves the alternate model. Provider change clears the old model. The 640-pixel viewport has no horizontal overflow; normal and narrow model panes were visually inspected. Cached asset citations still open the source details with original URL, retrieval date, rights and excerpt; unavailable sections and separate unverified notes remain explicit. Preview servers and browser were stopped afterward. Local screenshots: `.local/output/playwright/model-picker-640.png` and `.local/output/playwright/model-picker-normal.png` (ignored evidence, no live data).
- Final shared milestone gate: 376 Python tests, static evaluations, seven frontend tests, correctness lint, non-writing contract checks, documentation links, whitespace, TypeScript and production build passed. The repository contract test's exhaustive expected model list was extended for both new types; its equality assertion remains intact. Existing Starlette/httpx deprecation warning remains.

## Limitations

The production qualification registry still enables no generation. Authenticated catalog/live model access needs the user's dedicated sign-in and M1-T05 qualification. A catalog or stored setting does not satisfy those release gates. Gemini/Claude selection does not imply that those adapters are available. No approval/lifecycle/update/installer completion is claimed.
