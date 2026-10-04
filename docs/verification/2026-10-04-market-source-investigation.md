# Market data source investigation — 2026-10-04

M4-T01 is blocked on a permitted and accessible source for daily prices, dividends/splits and compatible historical valuation inputs. The five registered source rules cover SEC documents/concepts and OpenFIGI identity metadata, not market prices or action completeness. Existing issuer observations cannot establish instrument returns. Positive calculation and actual source acceptance remain required; missing-state UI is not completion.

Official pages reviewed:

- [Alpha Vantage documentation](https://www.alphavantage.co/documentation/): full daily history and the daily-adjusted endpoint are premium; the latter supplies prices/dividends/splits. No account, API key, paid service or dataset rights were established. Demo responses would not qualify general access.
- [Twelve Data individual pricing](https://twelvedata.com/pricing) and [terms](https://twelvedata.com/terms): the free plan describes internal non-display use; display, caching and redistribution depend on tier/add-ons/third-party terms. This review does not establish the app's required local display, retained evidence and portable archive permissions.
- [Nasdaq Data Link terms](https://data.nasdaq.com/terms): rights depend on the applicable order/data agreement; the page announces an upcoming November 2026 update. No dataset-specific grant or user entitlement was established. Do not infer rights from older WIKI dataset descriptions or the future terms.
- [Stooq terms endpoint](https://stooq.com/terms.html): no substantive permission text was available through the research tool. An accessible CSV or an unofficial downloader is not a license review.

This is a scoped investigation, not a conclusion that no free source exists. No market dataset was imported, no source rule was widened, and no account/billing change was made. Next: identify an official/free source with documented historical/action semantics and adequate local storage/display/backup rights, or review an existing user-provided entitlement; then implement independent instrument mapping, typed numeric admission, exact decimal/action-aligned calculations and a separate live qualification. User information about an existing dataset/account was requested asynchronously.

Independent work continues as M4-T02a: existing-job discovery and reconnect/recovery require the already verified research lifecycle and issuer UI, not market data. Parent M4-T02 and milestone completion retain their original prerequisites/acceptance.
