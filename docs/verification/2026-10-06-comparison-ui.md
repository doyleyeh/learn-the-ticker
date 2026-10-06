# Comparison UI and offline acceptance

Date: 2026-10-06 (Asia/Taipei). Scope: M6-T02 and final M6 acceptance. Backend checkpoint `d6d821a` retains its [original evidence](2026-10-06-comparison-storage.md). No public release or new native artifact is claimed.

The UI selects two fixed library/bookmarked page versions, opens immutable result URLs and original citations, displays exact decimals and explicit incompatibilities, and reads saved source dates/permissions independently. Source-detail/age failures cannot replace or regenerate the stored result. Offline controls disable new comparisons; reopening and local API reads remain available. No comparison endpoint invokes a provider or retrieves source data.

Integration review found that current fund pages use different section names from the retained fixture. DEC-053's v2 mapping adapts admitted holdings/construction/cost/risk/educational descriptions while preserving the original v1 validator. Unknown instrument type permits admitted general overview text, while type-dependent numeric fields remain suppressed. Archives keep both methods unchanged; summaries include a comparison count.

## Diagnostic checkpoint

Three initial B invocations failed with the other three existing workflows passing. Per the owner's persistence instruction, record the diagnosis and continue bounded repairs rather than treating these as an external blocker:

1. `.local/m6-comparison-b.log`: the test read the URL before asynchronous saved-page navigation completed. The resulting expected ID was null; the UI had correctly selected the page. Wait for the actual asset route before reading its ID.
2. `.local/m6-comparison-b-repair1.log`: exact implicit-label lookup did not match the populated select; the browser accessibility snapshot showed the correct combobox name and selected original version. Use its accessible role/name while retaining the exact selected-value assertion.
3. `.local/m6-comparison-b-repair2.log`: the checkbox helper demanded an immediate change, but the controlled checkbox updates after the settings API commits. The captured failure state was already offline. Click once, require the PUT response to succeed, then wait for the unchecked state; no repeated settings submission or relaxed offline expectation.

At the third run, original-version creation/citation navigation, exact two-sided values, period mismatch, mixed fund applicability, adapted descriptions and 640-pixel overflow checks had passed; offline reload/failed-read assertions were still unverified. The final rerun below resolves that diagnostic checkpoint. No required check was skipped or weakened.

## Verification

- Initial UI tests: 91 frontend checks and TypeScript passed. Focused backend/archive/schema: 46 passed before the additional unknown-type regression.
- Actual D passed (`.local/m6-comparison-ui-d.log`): both v1 and v2 comparisons retained their values, methods, original citations and counts through rollback/restore/restart. Final checks after review follow below.
- React best-practices review: independent local reads start without waiting for one another; each effect cancels/ignores late responses; result components are keyed by immutable version; the submission ref prevents double clicks; source links, selects and disclosures remain keyboard operable. No dependency, global state cache or browser credential persistence was added.

- Final Q: `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` passed **1,951 Python/91 frontend tests**, lint, generated-contract equality, 91-file documentation check, static evaluations, TypeScript and production build (`.local/m6-final-q.log`). Focused comparison tests: 28 passed.
- Final D: `python -m scripts.verify database` with isolated PostgreSQL 17 passed actual failure rollback, full-library restore and restart. All three original v1/v2 comparison records retained their exact values, references and method; the archive preview counts them (`.local/m6-final-d.log`).
- Final B: `npm run test:browser` passed all four workflows (35.6 seconds, `.local/m6-comparison-b-repair3.log`). The comparison scenario created exactly three explicitly requested results and made no new research/term requests or external calls. Offline reopen, reload and failed source-detail reads preserved the result without new generation. No browser errors occurred.
- Visually reviewed `comparison-wide.png`, `comparison-mixed-narrow.png` and `comparison-offline-narrow.png` under ignored `output/playwright/automated/research-saved-comparisons-64ea0-ibilities-and-offline-reads/`: exact values, original dates/citations and mixed-type gaps remain readable at normal width and 640 pixels. Keyboard source navigation/disclosure and no horizontal overflow passed.

## Fresh M6 requirement review

| Requirement | Implementation and acceptance |
| --- | --- |
| P-024/P-025 original cited context, no winner | Independently proven immutable pages; deterministic original values and admitted descriptions only; no ranking, inferred metric or provider call. Backend tamper/rights tests and browser original-version links passed. |
| Aligned mixed types, units, periods and methods | Explicit alignment states, missing/conflicted latest values, separate valuation sampling, unreconciled share bases and unknown/fund applicability; targeted and retained regressions passed. |
| Offline cached learning and comparisons | Read-only result/source routes, disabled creation plus backend settings enforcement; existing page/term/conversation workflows and new offline reload/failed-read scenario passed. |
| Durable results and compatibility | Immutable publication and exact original fingerprints; both method versions survive actual PostgreSQL rollback/restore/restart and schema generation. |
| Source age, safety and presentation | Original dates/permissions remain separate from saved time; source failures visible; responsive and keyboard checks plus visual review passed. |

M6-T02 and M6 are complete within source-level desktop acceptance. The existing native artifact predates M5/M6; M9–M11 native lifecycle/build/installer/update/rollback and M8's other live subscriptions remain required before public Windows v1. No dependency, billing, source permission or release qualification was broadened.
