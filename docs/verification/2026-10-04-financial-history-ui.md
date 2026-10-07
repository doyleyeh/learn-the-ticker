# Admitted financial history presentation

Date: 2026-10-04. M4-T01a checkpoint; M4 remains incomplete.

## Implemented scope

The production evidence view now renders typed admitted issuer observations with exact decimal values, actual reporting periods, units, filing dates/accessions, retrieval times and immutable bundle/source citations. Separate concepts, currencies and annual/quarter/instant periods remain separate series. Only current unconflicted versions supply points; prior versions and unresolved conflicts remain inspectable. BigInt arithmetic converts values only into bounded screen coordinates, avoiding numeric precision loss. The default history is bounded to five annual periods/twelve quarters; retained filings are paginated separately.

Stock/fund section headings and three-risk disclosure reuse retained product behavior without importing fixture facts. Unknown types suppress type-dependent sections. Notes and model numeric claims never supply chart data. Share-based trends without established corporate-action compatibility and nonstandard durations disclose their limits. Price history, price return, total return and aligned historical valuation remain unavailable; their positive implementation/qualification is still M4-T01 work. Progressive evidence publication/review and repeatable interaction coverage remain M4-T02/T03.

## Verification

- Q: `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` passed with **1,151 Python and 25 frontend tests**, lint, generated-contract checks, documentation/static checks and TypeScript/Vite build. Existing Starlette/httpx deprecation remains.
- D: `python -m scripts.verify database` with PostgreSQL 17 passed isolated lifecycle, authenticated API upload, transaction/recovery and actual separate-cluster restore/restart. Original financial/source/citation records survive restoration. This change adds no database/schema migration.
- B: the preferred in-app browser backend was unavailable; the Playwright CLI fallback inspected the actual Vite production UI against the disposable synthetic preview server with `--financials-demo`. No provider or external financial request occurred. Online research stayed off.
- Normal-width inspection showed negative/zero-baseline/positive bars and an explicit withheld latest conflict. Share-based charts remained unavailable. Keyboard Enter opened/closed a series disclosure.
- At **640 pixels**, document width was **640**, without horizontal overflow. Exact latest `9,007,199,254,740,992` and superseded `9,007,199,254,740,993` remained distinct in filing history. The selected superseded observation's citation navigated within the same immutable bundle to the original registered SEC concept URL, showing original publication/as-of/retrieval dates and full-text/structured-adapter policy. No live URL was fetched.
- React review checked hook ordering, stable bundle/series keys, bounded disclosure rendering, semantic controls, escaped text and absence of fixture dependencies in production imports.

Screenshots are local ignored artifacts under `output/playwright`; they contain synthetic data only. Native installer/selection and positive price-return/total-return calculations are not established by these checks.

## Review and follow-up

Reviewed all changed/new UI, fixture and documentation files for decimal rounding, unsupported chart inputs, source/version loss, misleading dates, credential leakage and generated artifacts. No new dependency or provider permission was introduced. Finish remaining M4 acceptance separately. The user authorized free Windows native build prerequisite installation during this checkpoint; installation status and native results are recorded separately, not counted as financial-view evidence.
