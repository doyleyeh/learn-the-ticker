# Market data source investigation — 2026-10-04

M4-T01 is blocked on a permitted and accessible source for daily prices, dividends/splits and compatible historical valuation inputs. The five registered source rules cover SEC documents/concepts and OpenFIGI identity metadata, not market prices or action completeness. Existing issuer observations cannot establish instrument returns. Positive calculation and actual source acceptance remain required; missing-state UI is not completion.

Official pages reviewed:

- [Alpha Vantage documentation](https://www.alphavantage.co/documentation/): full daily history and the daily-adjusted endpoint are premium; the latter supplies prices/dividends/splits. No account, API key, paid service or dataset rights were established. Demo responses would not qualify general access.
- [Twelve Data individual pricing](https://twelvedata.com/pricing) and [terms](https://twelvedata.com/terms): the free plan describes internal non-display use; display, caching and redistribution depend on tier/add-ons/third-party terms. This review does not establish the app's required local display, retained evidence and portable archive permissions.
- [Nasdaq Data Link terms](https://data.nasdaq.com/terms): rights depend on the applicable order/data agreement; the page announces an upcoming November 2026 update. No dataset-specific grant or user entitlement was established. Do not infer rights from older WIKI dataset descriptions or the future terms.
- [Stooq terms endpoint](https://stooq.com/terms.html): no substantive permission text was available through the research tool. An accessible CSV or an unofficial downloader is not a license review.

This is a scoped investigation, not a conclusion that no free source exists. No market dataset was imported, no source rule was widened, and no account/billing change was made. Next: identify an official/free source with documented historical/action semantics and adequate local storage/display/backup rights, or review an existing user-provided entitlement; then implement independent instrument mapping, typed numeric admission, exact decimal/action-aligned calculations and a separate live qualification. User information about an existing dataset/account was requested asynchronously.

Independent work continues as M4-T02a: existing-job discovery and reconnect/recovery require the already verified research lifecycle and issuer UI, not market data. Parent M4-T02 and milestone completion retain their original prerequisites/acceptance.

## Follow-up after source-review delivery

The original investigation above remains dated and scoped. M4-T02a/b/c are now verified; this follow-up found a useful but incomplete free path:

- Taiwan's [daily stock dataset 11549](https://data.gov.tw/dataset/11549) and [ex-dividend announcement dataset 89748](https://data.gov.tw/dataset/89748) explicitly list Open Government Data License 1.0 and no charge. The [license](https://data.gov.tw/license) permits reuse/derivatives with its required attribution. This is a dataset-specific positive rights finding, not a license for every exchange webpage.
- The [official OpenAPI schema](https://openapi.twse.com.tw/v1/swagger.json) lists `/exchangeReport/STOCK_DAY_ALL` and `/exchangeReport/TWT48U_ALL` without historical-date parameters. Two bounded, read-only endpoint samples on 2026-10-04 found 1,380 price rows all dated ROC 1151002 (2026-10-02), and 58 announcement rows dated ROC 1151005–1151028 (2026-10-05–28). Only aggregate coverage/field metadata was retained; no prices were imported or registered as app evidence. A first console rendering of Chinese schema summaries had encoding loss; endpoint names/parameter arrays were intact and the official web rendering was checked separately.
- These samples do not establish five-year price backfill, completed dividend/split coverage or aligned historical valuation. An upcoming ex-dividend announcement is not proof of every completed corporate action. The [TWSE website terms](https://www.twse.com.tw/en/terms/use.html) distinguish expressly released government open data from other content and restrict automated downloads except agreed methods/consent. Do not infer permission for undocumented website-history scraping from the OpenAPI license.

M4-T01 remains blocked on a documented, accessible historical source with compatible action coverage and required rights, or an existing permitted user entitlement. No paid signup, contact message or rule expansion occurred. Continue independent M4-T03a repeatable browser coverage for already admitted sections/recovery/review; price/return integration remains an explicit later acceptance gate.
