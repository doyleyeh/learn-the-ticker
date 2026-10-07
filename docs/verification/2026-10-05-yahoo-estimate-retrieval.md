# User-run Yahoo estimate retrieval

Date: 2026-10-05. M4-T01g8c; DEC-050. Source qualification only; analyst library/UI/native admission remains incomplete.

## Architecture and scope

The owner explicitly confirmed that users clone/install the open-source framework and run retrieval, storage and learning on their own computers. There is no project-operated Yahoo data service, shared dataset or public finance API. The [yfinance project metadata](https://pypi.org/project/yfinance/) identifies an Apache-2.0 developer library for research/education and separately points users to Yahoo's data terms. This supports the software/data distinction, not a blanket data license. Existing notices remain in the dependency inventory. The prior general-terms access question and public-release qualification remain recorded; they do not reopen private implementation approval.

The official [earnings estimate](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.get_earnings_estimate.html) and [revenue estimate](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.get_revenue_estimate.html) APIs identify four forecast labels and average/low/high/analyst-count fields. Inspected pinned 1.7.0 `scrapers/analysis.py` uses the earningsTrend quoteSummary module. Reuse that request through the existing isolated anonymous session, parsing captured original JSON with Decimal instead of its dataframe. The dataframe omits forecast end dates and can reuse currency across rows; the new parser keeps each metric's own currency. Unknown currency/date withholds amounts; no issuer/price-currency inference or formatted-number scaling.

Only EPS/revenue current/next quarter/year candidates are returned. Ignore long-term growth and never request recommendation/target modules. Forecast dates do not establish publication/as-of time, which remains unknown. These candidates cannot publish factual claims or enter the library by themselves. No new dependency, account, service, SQL change or model tool is introduced.

## Deterministic verification

- Targeted `test_market_estimates.py`, `test_market_valuations.py`, `test_market_transport.py`: **105 passed**, including 45 new estimate cases.
- Q `verify-milestone.ps1`: **1,792 Python / 75 frontend passed**, lint, contract/schema checks, local links, static evals, TypeScript/build and diff checks. Existing Starlette/httpx deprecation only.
- Original precision, negative EPS, per-metric missing currency/date/value, unknown periods, mismatched symbol, duplicate fields/rows, nonfinite/oversized data and analyst-count bounds are covered.
- Exact HTTPS module/symbol/path/parameters, separate existing history/valuation policies, response capture and sticky access/quota/redirect denial are covered. Normal tests perform no network calls.
- Reviewed all code/doc changes. No failing verification or repair attempt in this slice. F passed after the checkpoint documents were finalized.

## Bounded live observation

After Q, called `scripts.qualify_yahoo_estimates.qualify('NVDA')` once with an allowlisted-error reporting wrapper. At **2026-10-05T15:23:49.495813+00:00**, the owned yfinance worker returned **8 points / 8 usable**, periods `0q`, `+1q`, `0y`, `+1y`, currencies `USD`, no missing-field reasons, **3 HTTP requests** including anonymous bootstrap. Original response SHA-256: `cb8365dd9c01caf5ef728a99230bf1f1b9906189fc1673a420c912d9fa8e6ef0`.

Only counts, field categories, retrieval time and hash were reported. No financial payload, cookie, credential or raw diagnostic was written to Git or a library. No agent call, billing activation, user login, retry or source-rule activation occurred. The original forecast dates/currencies passed parser checks; the observation proves compatible candidate access, not point-in-time consensus history or analyst accuracy.

Continue with independently mapped opinion admission, selected-source review, immutable citations and private context/export boundaries, actual restore, browser readability and packaged/live verification. M4 remains incomplete. The previously observed Alpha Vantage currency/scale gap remains specific to that candidate.
