# Private price and return presentation

Date: 2026-10-04. M4-T01f5. Source-mode UI work; native packaging remains M4-T01f6.

Implementation adds saved daily chart windows, exact OHLC/volume/action detail, retained price returns versus provider-adjusted total-return estimates, original citation/date/method/gap labels, default-off Connections opt-in and automatic-selection restrictions for private content and transitive derivatives. No new data request or calculation occurs when opening a saved page.

## Repair diagnosis and acceptance blocker

The first TypeScript check found tuple-union `.includes` inference, repaired with `.some`; the JSON test fixture also required an explicit unknown-to-contract cast and now has a separate backend Pydantic validation. An EOF whitespace failure was repaired. No acceptance was weakened.

Browser attempts found an ambiguous Connections link selector (scoped to primary navigation), then an asynchronous controlled checkbox (click followed by an awaited saved-state assertion). The next run timed out in the existing bookmarked-version flow, before the new private section. Its bookmark had disappeared; an earlier failure capture also showed transient default/off settings. Repeated browser failures block UI acceptance and are recorded here rather than treated as a pass.

Diagnosis: the preview server's `sqlite://` StaticPool shares one DBAPI connection across concurrent FastAPI requests. A read session can see another transaction's uncommitted changes and roll it back on closing. Production uses PostgreSQL; this fixture cannot establish a production storage fault. Repair the explicit preview with a disposable file-backed SQLite database, separate connections and cleanup. A targeted concurrent read/write regression must verify isolation and preservation of a committed bookmark/settings. Then rerun the unchanged original browser assertions plus private opt-in/chart/source/reload/opt-out cases. No live/provider data or user's library is involved.

The race was reproduced independently against the old fixture: another thread observed uncommitted settings and its read closure removed an uncommitted bookmark. The file-backed disposable preview repair passed `test_preview_database.py`: concurrent reads see only committed records and cannot roll back the writer. The full B flow then passed with its original bookmark/financial/source/recovery assertions intact. This resolves the recorded fixture blocker.

## Verification

Eleven initial frontend market checks passed for exact decimals beyond JavaScript precision, original source/version links, distinct price/adjusted returns, missing boundaries, old snapshots without new calculations, detached/incomplete results, geometry/gaps and leap/month window boundaries. A twelfth case checks legacy Yahoo URL restrictions and transitive derivatives. The committed synthetic JSON fixture also passes the production backend numerical contract.

`npm run test:browser` passed the expanded integrated flow (12.8-second scenario; 20.2-second total) with no retries and no external browser requests. It uses the real frontend, authenticated API and production research service with explicit synthetic source/runtime boundaries. Connections begins unchecked, persists opt-in, private source review begins unchecked, a selected source publishes history, period selection keeps original values, and exact volume/dividend strings remain inspectable. Price return `27.272727%` and adjusted estimate `40%` are synthetic examples, never live market figures. Missing one/three/five-year and YTD baselines remain visibly unavailable.

Original citation navigation preserves bundle ID, Yahoo URL, original as-of/retrieval dates and usage scope. Reload preserves the saved chart/returns without submitting research. Automatic selection from the private price is withheld while ordinary term selection works. Revoking opt-in during the next pending job cancels that job and leaves saved history readable. Normal/640-pixel screenshots were inspected: chart/date/method labels, wrapping return cards, missing states and exact-value detail are readable; the wide numeric table has a bounded keyboard-focusable scroll region without page overflow. Ignored captures are `private-history-wide.png` and `private-history-narrow.png` under `output/playwright/automated/research-admitted-versions-89be9-at-normal-and-narrow-widths/`.

React review: bounded, memoized chart preparation; exact BigInt coordinate differences; stable source/date keys; labelled SVG/select/table controls; no inferred financial calculations or provider calls during render; explicit selection-range intersection checks. No dependency, contract, SQL schema or archive format change. Production database/native code is unchanged; D's original 2026-10-04 orchestration/restore evidence remains in the preceding checkpoint. No new live financial/model request was made. Final Q/F results are recorded when complete.

Q passed **1,561 Python/51 frontend tests**, Ruff/ESLint, contracts/docs/whitespace/static evaluations, TypeScript and production build. Existing Starlette/httpx and browser color-environment warnings remain. Both loopback preview listener ports were confirmed closed after B. An additional final B run checks cross-panel selection and reading saved prices with cloud consent switched off; F follows final documentation.

The final expanded B run passed (12.8-second scenario, 20.8-second total), including cross-panel selection exclusion and saved chart/return reading with cloud consent off. No automatic financial refresh, new return computation or model call occurred.

Final F passed at the 2026-10-05 checkpoint after documentation updates. Complete source changes and staged inventory were reviewed; synthetic fixture values are explicitly test-only and absent from the production entry/bundle. No credentials, live responses, temporary database or build artifact is committed.
