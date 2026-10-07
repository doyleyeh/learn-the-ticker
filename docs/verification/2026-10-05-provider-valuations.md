# Attributed private provider valuations

Date: 2026-10-05. M4-T01g3 implements and qualifies the user-approved DEC-045 supplied-valuation path. Final M4 parity review remains a separate acceptance step.

## Acceptance and method

Retrieve bounded Yahoo valuation observations through the pinned yfinance worker for independently matched listings. Retain seven supplied metrics, original dates, provider sampling/period labels, exact decimals and a separate immutable statistics source. These are attributed provider calculations, not SEC facts or app-reconstructed ratios. Annual/quarterly sampling does not establish the earnings denominator. Missing periods, values and monetary currency remain explicit. No interpolation or point-in-time claim.

Existing private boundaries remain: default-off opt-in, local display/cache and same-user backups; no values or derivatives in cloud prompts or shareable exports. Source review can select prices without valuations. Cancellation/revocation stop admission; a valuation failure preserves admitted prices without retry. Old snapshots retain their fingerprints and gain no new offline observations.

## Checks and repairs

- Q passed: 1,657 Python tests, 71 frontend tests, static evaluations, non-writing contracts, lint/docs and production build.
- Final F passed after the evidence and canonical-state updates: lint, generated-contract drift, Markdown links, whitespace and TypeScript. Live checks stayed outside deterministic verification.
- D passed: actual isolated PostgreSQL lifecycle, full restore/restart, exact valuation observations and citations, private context/export filtering and reset network opt-in.
- Initial candidate-only live retrieval succeeded at transport but the parser rejected the real shape. Bounded metadata diagnosis showed trailing period labels are `TTM`, ratios can lack currency, and two monetary observations lack currency. Parser tests now cover these cases; monetary amounts without a currency are withheld. No denial/quota was bypassed, and no automatic retry occurred. The subsequent packaged production check passed as detailed below.
- Browser build initially rejected a synthetic fixture cast; corrected to the existing fixture casting convention without changing the production contract. Three subsequent browser runs exposed assertion defects: the navigation label is `Statistics`; the latest value and its as-of date share one element; earlier price and newly opened valuation source drawers can both stay open. The page snapshot confirmed the expected values, missing states and two original sources. These were recorded acceptance blockers, not passed checks. The repaired final selector binds the drawer to the actual citation route's source ID. No checks were skipped or timeout increased. Final B passed the integrated workflow in 23.3 seconds (test body 13.3 seconds), including reload, opt-out cancellation, exact citations, values and keyboard interactions. Inspected normal/640-pixel screenshots: text is readable, exact values are preserved, the table scrolls inside its container, and the page has no horizontal overflow.
- Packaged checks passed: rebuilt frozen service startup/shutdown, all four import formats, actual market dependency imports and owned worker cancellation, exact valuation/issuer/private history restore and restart through the frozen API into isolated PostgreSQL. N passed the locked Tauri release build and NSIS assembly. No new dependency, SQL revision or archive format is introduced; existing native dependency advisory/public-release limits remain. No installer was installed or published.

## Actual supplied valuation coverage

After Q/D/B and packaged verification, ran `python -m scripts.qualify_market_research --live --asset-id FIGI:BBG000BBK0R0 --require-valuations --packaged-worker`. It passed independent OpenFIGI identity, the existing bounded EODHD-first/history fallback, frozen Yahoo price/valuation retrieval, application admission, progressive checkpoint and final publication in a discarded database. No model or durable user-library write occurred. Private content remained absent from model context and shareable exports. Only the worker was frozen; orchestration and the discarded database ran from source. This does not establish installed WebView or clean-machine acceptance.

The valuation dataset contains **127 observations, 125 available and two withheld for missing monetary currency**, across seven metrics. Each metric supplied four annual samples (2023-01-31, 2024-01-31, 2025-01-31, 2026-01-31) and five quarterly samples (2025-07-31, 2025-10-31, 2026-01-31, 2026-04-30, 2026-07-31). These are original provider observation dates, not rewritten issuer fiscal-period ends. Trailing-series coverage is 8–10 irregular observations per metric, through 2026-09-23. Historical P/E is positively available as an attributed provider calculation. The default five annual/twelve quarterly window remains the target; insufficient supplied coverage is visible and is not filled. A five-year request does not mean five years were returned.

| Original reference | Retrieval time (UTC) | SHA-256 |
| --- | --- | --- |
| [Yahoo NVDA valuation measures](https://finance.yahoo.com/quote/NVDA/key-statistics/) | 2026-10-05T06:16:43.575231+00:00 | `244a9c94881150da357febb6dbfb6bfbbb6780031369c6a54b64439e48c197ad` |
| [Yahoo NVDA daily history](https://finance.yahoo.com/quote/NVDA/history/) | 2026-10-05T06:16:37.554668+00:00 | `f88bd33a3e741c974a8b83e5b8b892c9285eaf18fd8ef8ad420b5437bfc95d0f` |

Daily history retained 1,259 rows and 21 actions, 2021-09-28 through 2026-10-02. YTD/1y/3y/5y/retained return windows remained available. The private record fingerprint is `d58401d37c65d81968e4f341cafb12555ccc7c5bdffec6af03218242f1696e2d`. Financial values and raw responses were not written to Git.

## Local artifacts and review

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| `dist/ltt-service.exe` | 56,764,393 | `99bb314f4a2bffaaf4029a5b1a08199017e6777fc56a91bbed041e11d897e0ec` |
| `learn-the-ticker.exe` | 11,108,864 | `7b82553cef92e00e0d3854886feaa75c1e3c538e0ad3beb14bd313f0db83e488` |
| `Learn the Ticker_0.2.0_x64-setup.exe` | 78,152,253 | `cf9bea2132134e266036adad2775fa9f943ff5ebb6c436d9039d7869233a0944` |

Reviewed the complete production/test/document diff: exact transport scope, original JSON precision, independently matched listing, separate source review, progressive publication, unchanged private operation filters, immutable old records, cancellation and same-user restore. The generated contract was checked without rewriting it. Existing tests retain their assertions; synthetic adapters make no live calls. The only live check explicitly opts in and prints metadata/counts rather than financial values or credentials. Artifacts are ignored developer outputs with no user library or credential material. Existing harmless optional PyInstaller hidden-import warnings and the Starlette/httpx test-client deprecation remain; actual packaged smoke checks passed.

## Remaining scope

Public permission and Windows release acceptance are unchanged. App-calculated cross-source P/E still requires compatible share bases; the separately attributed historical provider observations are now positively qualified within DEC-045. PLAN order is unchanged; the unrelated sequencing proposal remains unapproved.
