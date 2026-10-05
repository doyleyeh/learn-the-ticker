# Packaged market admission and M4 acceptance

Date: 2026-10-06 (Asia/Taipei). Original UTC retrieval timestamps are retained below. This follows the owner's request to fix the failed final history/analyst check. The previous [failed observation](2026-10-05-analyst-opinions.md) remains part of the record.

## Bounded diagnostic result

On unchanged production code and the previously verified frozen sidecar, the updated diagnostic helper passed one explicit attempt:

`python -m scripts.qualify_market_research --live --asset-id FIGI:BBG000BBK0R0 --packaged-worker --require-estimates`

Exit **0**, status **qualified**. Independent listing resolution, production source selection/retrieval, numerical admission, progressive checkpoint, final publication into the disposable test database, immutable checkpoint preservation, selected-agent context construction and shareable-export exclusion all passed. No model was called and no durable user library was changed.

| Dataset | Observation | Original retrieval time (UTC) | SHA-256 of original response |
| --- | --- | --- | --- |
| Yahoo history | 1,259 daily rows, 21 actions; 2021-09-28 through 2026-10-02; all five retained return windows available | 2026-10-05T16:41:58.194117+00:00 | `76fea61ef45ded325f72f9f41b5512ff27f76696192c8e2b755d745af4e3cd7d` |
| Yahoo supplied valuations | 127 observations, 125 usable; annual/quarterly/trailing series retain their distinct dates and gaps | 2026-10-05T16:42:03.937137+00:00 | `244a9c94881150da357febb6dbfb6bfbbb6780031369c6a54b64439e48c197ad` |
| Yahoo analyst estimates | Eight usable EPS/revenue opinions across 0q, +1q, 0y and +1y; USD/share and USD; publication time unknown | 2026-10-05T16:42:09.045303+00:00 | `cb8365dd9c01caf5ef728a99230bf1f1b9906189fc1673a420c912d9fa8e6ef0` |

Original citations are the NVDA [history](https://finance.yahoo.com/quote/NVDA/history/), [statistics](https://finance.yahoo.com/quote/NVDA/key-statistics/) and [analysis](https://finance.yahoo.com/quote/NVDA/analysis/) pages. The worker was `dist/ltt-service.exe`, SHA-256 `63c34c6c8aac4a93f885b1763bffa273097814a6e1f17244361d608553aedad6`, matching the previously qualified artifact. Orchestration used source code and a discarded in-memory test database; actual PostgreSQL/restore/native qualification is separately recorded.

The earlier failure did not reproduce. Its originating stage/code was not recorded at the time, so its root cause remains unknown. This successful observation resolves the positive-admission gate; it does **not** establish that a code repair fixed an identified defect or that providers will always be available. No production code, account plan, request budget, retries, access policy or fallback behavior changed. No additional live attempt was needed. Safe failure-stage diagnostics remain covered by deterministic tests for future failures.

## Independent M4 acceptance review

Reviewed the PLAN/SPEC acceptance against production components and executable scenarios, independently of task completion labels:

| Acceptance | Implementation and evidence |
| --- | --- |
| Useful financial sections, exact citations/dates/units/rights | `TickerDashboard`, `EvidenceSections`, `FinancialHistory`, `FinancialRatios`, `MarketHistory`, `ProviderValuations` and `AnalystInsights` present admitted listing, stock/fund sections, prices/returns, statistics, financials, filing context and separate analyst opinions. Original-version source routes and typed source validation remain enforced. [Section parity](2026-10-05-section-parity.md), [valuations](2026-10-05-provider-valuations.md), [opinions](2026-10-05-analyst-opinions.md) and the positive packaged result above cover the formerly missing slices. |
| Charts and returns use aligned admitted numeric evidence | Original decimal strings, units, dates, corporate actions and exact source links are retained. Chart geometry cannot create financial inputs; retained price return and provider-adjusted total-return estimate are distinct. Incompatible SEC filing/currency/period inputs and missing prices/baselines withhold calculations. [Returns](2026-10-04-market-returns.md) and [issuer percentages](2026-10-05-financial-ratios.md) cover these boundaries. Opinions are excluded from chart inputs. |
| Progressive sections, review and recovery | Independently admitted checkpoints preserve old versions before the final answer. Source subset/skip/cancel, consent revocation, reload/reconnect and no inference replay are exercised in the integrated browser workflow and deterministic publication tests. [Progressive evidence](2026-10-04-progressive-evidence.md), [source review](2026-10-04-source-review.md), [recovery](2026-10-04-research-job-recovery.md). |
| Honest missing/stale/partial/not-applicable states | Saved availability is distinct from source age. Unknown publication dates remain unknown; no live quote, complete live news feed, missing period or unsupported asset type is invented. Supplied valuations can satisfy historical valuation display without claiming app-calculated SEC/price compatibility. [Source age](2026-10-05-source-age-display.md), section parity and analyst browser scenarios cover these cases. |
| Normal/640-pixel layouts and keyboard access | The two browser workflows exercise section focus, risk/details disclosure, original source navigation, exact financial values, independently scrollable tables, private selection, source age, stock/fund/unknown views, cancellation and offline reuse; screenshots are inspected separately. |
| Context-aware learning | Explicit saved-page questions and term actions use original admitted context/citations with browsing disabled when explaining that snapshot. Scoped Codex live/offline reuse passed in [saved questions](2026-10-05-saved-questions.md) and analyst evidence; general conversations/comparisons remain in M5/M6. |

This review preserves partial source coverage and all release gates. It does not certify every ticker/provider, full live news, independent reconstruction of supplied ratios/adjustments, native WebView interactions, Gemini/Claude or clean-machine Windows release acceptance.

## Verification checkpoint

The affected diagnostic suite passed **29 tests** before the live attempt. An initial command used the wrong test directory, ran zero tests, and was corrected to `tests/desktop/test_market_research.py`; it was not a product/test failure or a repair attempt.

Final Q passed **1,842 Python / 86 frontend tests**, correctness lint, non-writing contracts/types, documentation/whitespace checks, static evaluations and production TypeScript/Vite build. Actual D passed isolated PostgreSQL startup/shutdown, lock/transaction/recovery tests and full-library restore/restart with original evidence, citations, interpretations and reset network consent. B passed **two workflows**, including positive opinions and the complete stock/fund/unknown, source review, progressive/recovery, source-age and saved-page flow at normal/640-pixel widths. Inspected the final wide/narrow analyst screenshots: exact values/units, readable attribution/date warnings, keyboard focus and independent horizontal table scrolling. No external browser requests or uncaught page errors were reported. Owned preview listeners exited.

Ignored logs: `.local/market-history-diagnostic-2026-10-06.log`, `.local/m4-final-q.log`, `.local/m4-final-d.log`, `.local/m4-final-b.log`. Screenshots: `output/playwright/automated/research-admitted-versions-89be9-at-normal-and-narrow-widths/estimates-wide.png` and `estimates-narrow.png`. Existing Starlette/httpx and browser color-environment warnings remain. No checks were weakened or skipped.

M4 acceptance is complete. Final documentation F passed before the reviewed local checkpoint. Previous packaged/native and scoped synthetic-agent checks remain valid for the unchanged production artifact, with their original dates in the linked analyst evidence. M5–M11 and public Windows v1 remain incomplete. No new dependency, schema, security/scope decision, provider activation, public publication or remote Git action occurred.
