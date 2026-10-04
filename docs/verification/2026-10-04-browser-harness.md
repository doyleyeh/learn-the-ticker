# Deterministic research browser acceptance — 2026-10-04

M4-T03a supplies a repeatable B check for the already delivered financial evidence, progressive sections, optional source review and job recovery. It does not complete M4: positive historical price/return/valuation integration still lacks a permitted, accessible source. See [the source investigation](2026-10-04-market-source-investigation.md).

## Implementation and environment

`npm run test:browser` builds the production frontend and runs development-only Playwright Test 1.63.0 with Chromium headless shell 153.0.8010.12 (revision 1243). The pinned runner and transitive packages are Apache-2.0; purpose, alternatives and packaging boundaries are in [DEC-034](../../DECISIONS.md#dec-034-pin-a-local-deterministic-browser-acceptance-harness). Chromium/support downloads stay in the developer browser cache. No application runtime dependency or installer resource changed.

The runner owns a production Vite preview and the explicit `--financials-demo --source-review-demo` service, using the repository virtual environment and disposable in-memory data. Both bind loopback on 1420/18764. Existing-server reuse is disabled. One worker, no retries, bounded test/assertion/startup timeouts, no traces and blocked external browser requests make failures visible. The public synthetic credential is for this fixture only. The harness is linted/type-checked by Q; actual browser execution remains a separate B command. The manual full-evals workflow now has an explicit browser job; no remote CI execution is claimed.

## Verification

- Q: `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` passed **1,297 Python tests, 34 frontend tests**, Ruff/ESLint, non-writing schema/type checks, documentation/static evaluations, whitespace, TypeScript and production build. No provider or live source was contacted by these tests.
- B: final `npm run test:browser` passed one integrated workflow with five named steps in **13.4 seconds**, including owned server startup/teardown. An earlier complete run also passed before improving the wide screenshot's framing.
- Opened the five-year synthetic issuer history and explicitly expanded Revenue. Verified the exact displayed `9,007,199,254,740,992 USD` value, explicit unavailable price history and immutable bookmark.
- Selected only revenue from nine unchecked source options. Verified disabled empty selection, unknown-date disclosure and independently admitted `100 USD` while the issuer index still awaited review. Approved the index with keyboard Space, then the filing, and required a completed result without an incomplete-section label.
- Opened the final filing citation and checked its original SEC URL, publication **2026-09-17**, as-of **2026-09-15**, retrieval **2026-10-04T00:00:00Z**, full-text policy and verified-retrieval provenance. Reopened the original bookmarked version using keyboard Enter and required its original URL and exact value.
- Skipping all financial sources produced explicit missing-data text and no filing citation. Reloading/reconnecting during another review returned the same job/review, unchecked; cancellation displayed the terminal state. Exactly **three** explicit research POSTs occurred, with no replay on reload, no external browser request, no page error and no failed API response.
- Normal 1280-pixel source review and 640-pixel review/citation screenshots were visually inspected. Long original URLs and dates wrapped readably; narrow document width equaled viewport width. Ignored artifacts are under `output/playwright/automated/research-admitted-versions-89be9-at-normal-and-narrow-widths/`: `review-wide.png`, `review-narrow.png`, `original-citation-narrow.png`.
- After final success, neither test port had a listener and all recorded backend/frontend/test worker process IDs had exited. Actual PostgreSQL restoration, packaged/native checks and live-provider qualification were not rerun for this test-only checkpoint; their original dated evidence remains unchanged.

## Repairs and review

Initial startup failed because Windows command parsing did not accept the relative Python path with forward slashes; the configuration now selects the platform-appropriate path. Initial value assertions failed because Revenue was collapsed, then because the assertion omitted displayed thousands separators. The test now opens the real disclosure and asserts the exact formatted value. No production behavior or evidence guard was changed or weakened. Visual inspection also showed the first wide screenshot retained a previous scroll position; the final screenshot targets the entire review region and the complete workflow passed again.

The existing Starlette/httpx deprecation and Playwright child-process color-environment warnings remain non-failing diagnostics. Full test/configuration/dependency/workflow/document diffs were reviewed. Output, browser downloads, raw data and contact information are excluded from Git. M4-T03a is complete; M4-T01, final M4-T02 integration, M4-T03 financial parity and dependent milestones remain incomplete.
