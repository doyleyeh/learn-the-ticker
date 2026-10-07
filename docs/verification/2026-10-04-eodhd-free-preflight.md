# EODHD free-tier preflight — 2026-10-04

M4-T01d follows the user's existing-API preference and local credential setup. It is a bounded account/coverage investigation, not production adapter or market-calculation qualification. M4-T04 was committed at `3d46e2d`; its deterministic Q/B checks passed before these separate live requests.

## Actual observations

All ten allowlisted data/news credentials are now present in Windows Credential Manager. Hidden plan labels were classified against a fixed free/starter/trial vocabulary; arbitrary labels and key values were never printed. Only EODHD was contacted with a real credential in this checkpoint.

Two preliminary EODHD requests used its public `demo` identifier for a two-day AAPL sample. Header-only and public-demo-query forms both returned HTTP 200. Those status-only results alone did not establish payload validity or real account entitlement.

The real credential was loaded inside a native Python process and sent only in an HTTPS `Authorization: Bearer` header to `eodhd.com`, never in a URL, command argument, file, log, frontend or provider prompt. Requests used verified TLS, no environment proxy configuration, no redirects/retries, 20-second timeouts and bounded in-memory bodies. Fixed error output and allowlisted summary fields suppressed raw provider diagnostics, subscriber identity, payment fields and any echoed key. No payload was written to disk or admitted to the app library.

The [User API](https://eodhd.com/financial-apis/user-api) returned a JSON object with dailyRateLimit **20**, apiRequests **0**, extraLimit **0**. This was a point-in-time account observation, not a promise of remaining quota after the subsequent calls or a complete entitlement listing.

Three requests then used the provider symbol `NVDA.US` and the explicit date range 2025-10-04 through 2026-10-04:

| Endpoint | Response | Bounded observation |
| --- | --- | --- |
| EOD prices | HTTP 200 | 250 rows, 2025-10-06 through 2026-10-02; date/OHLC/adjusted-close/volume fields present |
| Dividends | HTTP 200 | Four rows, 2025-12-04 through 2026-09-10; date/value fields present |
| Splits | HTTP 200 | Empty array; not proof of wider-history completeness or absence of prior actions |

These responses establish limited endpoint access, not independent instrument mapping, full numeric validation, corporate-action consistency, production freshness, return accuracy or five-year coverage. There were four real-account read-only requests in total and two public-demo requests. No signup, upgrade, payment, extra-call buffer, subscription change, permission message, model invocation or production source activation occurred.

## Current published scope and remaining decision

The [pricing comparison](https://eodhd.com/pricing) and [EOD documentation](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes) limit the free plan to one year and 20 daily calls. The pricing page says free dividends/splits may require support activation; this account's bounded requests succeeded, so that specific access is observed rather than assumed. No attempt was made to evade the history limit, concatenate alternate accounts or query a paid/denied endpoint.

[Terms](https://eodhd.com/financial-apis/terms-conditions) expressly cover a non-professional individual's private storage/manipulation/analysis, while restricting third-party sharing/access. [Official MCP documentation](https://eodhd.com/financial-apis/mcp-server-for-financial-data-by-eodhd) explicitly describes personal-key access from ChatGPT, Claude and custom AI agents. This is relevant positive evidence for AI use and narrows the earlier blanket uncertainty; it does not turn the dataset into public/open data or authorize bundling a developer key with a distributed app. No MCP server, vendor trading prompt or extra tool was added to the qualified subscription runtime.

The one-year responses cannot satisfy the current minimum five-year milestone. Asked about that scope gap, the user directed using yfinance first or EODHD first with yfinance filling insufficient data. Continue with EODHD first and yfinance gap retrieval, preserving the five-year target and each source's dates/adjustment/provenance. This is authorization to implement the fallback for the personal learning app, not to buy another plan, bundle credentials/data or publish a dataset. Full account-specific storage/export/backup/cloud treatment, reliable instrument mapping and a tested adapter remain required before source activation; the API's response alone is not a universal permission grant.

## Verification boundary

No source code changed after the dashboard's Q **1,339 Python/38 frontend** and B pass. F validates the resulting documentation/task/status checkpoint. The live observations were separate explicit operations outside deterministic tests and CI; no real key or vendor response was made a fixture. This report preserves the earlier pre-setup missing-credential observation as historical evidence rather than rewriting it.
