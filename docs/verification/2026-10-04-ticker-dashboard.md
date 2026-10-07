# Ticker dashboard — 2026-10-04

M4-T04 organizes already admitted evidence under DEC-035. It is independent of the missing historical market-data adapter and does not close M4 or M5/M6 acceptance.

## Behavior

The ticker page has keyboard-accessible overview, charts/returns, statistics, financials, news/context, analyst, sources and learning navigation. Section buttons scroll and move focus while preserving the original bundle URL; they do not submit research. The listing panel preserves original identity authority/URL/check time and unknown currency/venue. Existing stock/fund/unknown-type sections and notes remain separated.

Statistics reuse `financialSeries` admission and exact decimal strings. Concepts, units and reporting periods stay separate. If the newest retained period is conflicted or superseded without a current value, the statistic remains unavailable; an older observation is not substituted. Figures retain publisher, original filing/period/retrieval dates and exact-version source links. No new ratios, annualization, price or return calculations were added. Annual/quarterly/instant/other-duration filters operate on original series; a missing period has no invented chart.

The page labels quote/session/delay, price/total-return/valuation inputs and qualified analyst material as unavailable. Dated filing/context material remains readable with original references and publication/as-of/retrieval dates, without claiming a current or complete news feed. Term controls now follow the evidence with a section shortcut and explicit saved-asset/date context. The existing permitted term context path still uses the exact saved bundle, with no inference on hover/focus. Full conversation version/scope transitions, comparisons and general API sufficiency orchestration remain in their owning work; this UI does not qualify them.

No new dependency, schema, migration, credential path, provider invocation or installer change. The old inline evidence renderer was moved into `TickerDashboard.tsx`, not retained as a second implementation. The React review checked keyed version resets, derived state, bounded numeric display, accessible headings/focus and direct imports.

## Verification

- `npm test`: **38 frontend tests passed**, including four new cases for exact statistics/citations, latest conflicts, source/prose exclusion and old snapshots/unknown listing fields.
- `npm run test:browser`: production frontend and isolated synthetic backend, **one integrated workflow passed in 13.7 seconds**. It covers the new dashboard plus prior review/subset/skip/cancel/reconnect/bookmark behavior, original source URLs/dates, keyboard section focus and saved-version term lookup. No external browser request or generation on dashboard navigation/focus; exactly the three intentional synthetic research submissions remain. Owned loopback ports 1420/18764 were no longer listening after the run.
- The first browser attempt failed because its new assertion expected an expanded price-independent revenue chart immediately after a filter change. The first default series is EPS, whose chart is correctly withheld without corporate-action compatibility. The repaired scenario explicitly expands Revenue before asserting the chart; no production gate was weakened. The next browser run passed.
- Normal and 640-pixel captures under ignored `output/playwright/automated` were inspected: readable listing metadata, long exact figures, withheld conflicted statistics, wrapped citations and section controls without horizontal document overflow.
- Q (`powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1`) passed **1,339 Python/38 frontend tests**, static evaluations, lint, contracts/generated files, documentation/whitespace checks, TypeScript and production build. F passed after final documentation updates. This front-end-only change does not alter database retention or require a new D/native/live run. Earlier evidence retains its original verification dates and scope.

During this checkpoint, a presence-only local vault check found all ten data/news credentials configured. A bounded classification of the hidden plan labels identified all as free/starter/trial; no raw key or arbitrary label was printed. Account access, actual plan entitlement and data coverage have not yet been queried or qualified. This supersedes the earlier assessment's pre-setup missing-credential observation without rewriting that historical result.
