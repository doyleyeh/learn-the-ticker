# Retained daily quote fields and valuation gaps

Date: 2026-10-05. Task M4-T01g2. This is a display checkpoint; M4-T01g and public Windows v1 remain incomplete.

Charts and returns now exposes the latest retained daily open, low–high range, provider-reported volume and preceding retained close with its own date. These fields come directly from the already admitted immutable history. No ratio, session completeness, previous trading day or live/after-hours quote is inferred. The source link, currency, split-adjustment basis and historical/private labels apply to all fields; automatic cloud term selection remains disabled within the panel.

Statistics distinguishes missing price history from additional missing valuation inputs. Historical P/E requires independently compatible share-class/split bases and earnings intervals; retained annual diluted EPS alone is insufficient. Market capitalization cannot substitute period-weighted diluted shares for shares outstanding at the price date. Individual dividend events do not prove a complete trailing/forward yield period. Unknown/non-stock types retain the appropriate unavailable state. The display does not add valuations or calculation results offline.

## Verification

- Targeted frontend tests and TypeScript passed: **62 frontend cases**. Extended exact-value/citation tests and added meaningful single-row/no-prior-price, detached source, unknown type, retained EPS and latest EPS conflict scenarios.
- Q: `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` — **1,602 Python / 62 frontend passed**, lint/contracts/docs/static/TypeScript/build.
- B: `npm run test:browser` — the entire normal/640-pixel synthetic interaction workflow passed with no retry. Verified the dated low–high fields and disabled term selection in the new private block alongside original citations, source review, saved versions and offline behavior.
- Visually inspected `daily-quote-narrow.png`; values and dates wrap readably without page overflow. React review found no new fetch, calculated result, effect or state synchronization; existing source/number guards precede rendering.

Ignored logs are `.local/quote-fields-quality.log` and `quote-fields-browser.log`; images remain under `output/playwright/automated`. No failed verification in this checkpoint. Existing Starlette/httpx and browser color-environment warnings remain non-failing.

No backend, contract, database, dependency, source-policy or native change; D from the preceding `8549152` checkpoint remains the applicable unchanged backend evidence. No new live request is needed to display fields already qualified in the private market snapshot. Installer artifacts still predate these UI changes. Positive aligned historical valuation remains separate required work.
