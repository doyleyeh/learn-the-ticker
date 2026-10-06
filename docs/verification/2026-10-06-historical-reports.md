# Historical reports and dated context

Date: 2026-10-06 (Asia/Taipei). Scope: M7-T02 and final M7 acceptance. The date selector was verified and committed as `0f40f01`; its [original evidence](2026-10-06-weekly-selection.md) is unchanged.

Historical reports preserve a selected completed original page regardless of recent-news availability. A separate dated context pack binds independently verified filing publications to the Eastern weekly window, retains sparse Earlier context outside weekly counts and shows a disclosed fixed app reading guide only at two weekly items. This guide is not AI synthesis. New creation makes no retrieval/inference call; current research refresh remains a separate explicit action. Coverage is limited to available independently verified saved filings. Reports do not reconstruct historical knowledge or feed canonical facts/charts.

Immutable publication and same-user archive validation bind the exact original fingerprint, dates, asset and citations. Personal JSON/Markdown exports reuse the original bundle export filter, preserving uncertainty and references while removing source bodies and restricted Yahoo content. Offline list/detail/export reads do not regenerate selection. UI routes retain the exact original page and show source age separately from report save time.

## Verification and repairs

- Focused backend/date/archive/schema suite: **55 passed**, including no-news financial history, two-item guide, old-version preservation, hostile report rewrites and reference substitution, interrupted publication, private-source export exclusion and reads/exports with generation patched to fail (`.local/m7-reports-targeted-final.log`).
- Initial TypeScript check found an optional generated ID passed to the strict download helper; the persisted result has a server-assigned ID and the call now asserts that invariant. A PowerShell-fed edit also hit the host default text encoding; all affected edits were reapplied explicitly as UTF-8. Repaired TypeScript and F passed (`.local/m7-ui-typecheck-repaired.log`, `.local/m7-reports-f.log`).
- Initial B had four existing workflows pass, but the new test received an empty Playwright response-body view after the JSON download. A first repair required GET to exclude preflight responses; the same failure remained, disproving that initial diagnosis (`.local/m7-reports-b.log`, `.local/m7-reports-b-repaired.log`). The final test verifies HTTP 200, successful download completion and the actual downloaded JSON/Markdown bytes, including exact original IDs and citations. The application download implementation was unchanged.
- Final B `npm run test:browser`: **five workflows passed** (37.3 seconds, `.local/m7-reports-b-download.log`), including actual JSON/Markdown downloads, original page links, sparse context, keyboard source navigation, offline reload, failed original-page reads, no new research/terms and exactly two explicit report creations. No external requests or browser errors.
- D `python -m scripts.verify database`: actual PostgreSQL rollback/restore/restart passed, retaining all three report records and 19 original evidence versions (`.local/m7-reports-d.log`).
- Visually reviewed normal and 640-pixel `report-wide.png`/`report-narrow.png` under ignored `output/playwright/automated/research-historical-report-f35d5-context-and-offline-exports/`. Publication/effective dates, separate Earlier context, source links and the app guide remain readable with no horizontal overflow.
- React review: independent list/detail fetches run concurrently, effects cancel and ignore late replies, version-keyed panels cannot flash another report, explicit submission is protected from double clicks, and no browser credential persistence or external read was introduced.
- Final Q `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1`: **1,987 Python/94 frontend tests passed**, plus lint, generated-contract equality, documentation, static evaluations, TypeScript and production build (`.local/m7-reports-q.log`). The post-review report suite also passed all 16 cases, including rejection of a valid but incomplete section checkpoint.

No dependency, source-policy expansion, paid activation, account change, live request or new native artifact. SQL/archive format versions are unchanged; existing installers predate this work and public release remains unqualified.

## Fresh M7 requirement review

| Requirement | Evidence |
| --- | --- |
| P-030 Eastern last completed week plus current week through yesterday | Typed selection with both DST transitions, Monday/year and inclusive/exclusive boundary tests; original UTC save time never replaces publication dates. |
| High-signal permitted official events and deduplication | Only independently proven SEC financial/material-event forms currently qualify; accession/body deduplication before counts, literal admitted quotes only, exact issuer and rights validation. Other news coverage is explicitly unavailable. |
| Fewer-than-three Earlier context and two-item weekly analysis | Available context within the previous 30 days is separate; zero/one/two/three/four tests, stored guide IDs exclude all earlier items, and hostile archive changes fail. |
| Historical reports independent of recent news | A zero-news financial page produces a saved report with exact financial history; UI displays the original values and suppresses only weekly analysis. |
| P-024 immutable originals and cited permitted exports | New asset versions do not alter reports. Actual database restore/restart preserves all records and references; downloaded JSON/Markdown retain original dates/citations and use the existing private-source filter. |
| P-014/P-021/P-025 source age, missing states and offline reads | Original page/source links, dates, partial coverage, unavailable originals, keyboard/responsive review and offline reopen/download passed without generation or external traffic. |

M7-T02 and M7 are complete within the reviewed desktop source workflow. This does not qualify new news feeds, model synthesis, native installers or public release; M8–M11 remain required.
