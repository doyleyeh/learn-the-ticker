# Personal market history retrieval — 2026-10-04

Scope: M4-T01e under DEC-037. The user selected EODHD first with yfinance for insufficient history; the five-year target is unchanged. This checkpoint qualifies bounded developer retrieval candidates, not financial admission, a production dashboard feed or the complete M4 milestone.

## Implementation and deterministic checks

Original EODHD/Yahoo JSON is bounded to 2 MiB and 2,000 daily rows, rejects duplicate fields/nonfinite numbers, preserves original decimal strings and hashes, validates OHLC/date/timezone/array consistency and retains split ratio components. Missing points are explicit and never filled. EODHD close is unadjusted; Yahoo close is split-adjusted even with `auto_adjust=False`. Adjusted close stays a separate field. Provider series are never spliced.

EODHD authentication uses the backend Authorization header only. The Yahoo worker runs behind an owned Windows Job Object with 1 GiB aggregate memory, a 55-second wall timeout, a fresh temporary cache, an allowlisted environment and discarded diagnostics. It admits only four possible GETs: anonymous cookie bootstrap, crumb, timezone chart and bounded daily history. No login-cookie import, consent POST, redirects, alternate endpoint after denial, price repair or paid/model fallback. The normal `fc.yahoo.com` cookie bootstrap's 404 is distinguished from a data-endpoint 404; auth/rate/server failures remain sticky. The parent closes the process before removing its workspace, including cancellation.

Targeted parser/transport/selection/worker tests: **91 passed**. One initial test-harness failure came from pytest deriving enormous IDs from oversized input bytes; explicit short case IDs fixed setup without changing parser acceptance. Q then passed **1,430 Python tests, 38 frontend tests**, Ruff/ESLint, schema/types, docs, whitespace, static evaluations and production frontend build. Existing Starlette/httpx deprecation remains. `pip check` passed compatibility checks; this is not a vulnerability audit. Normal tests made no live requests. No contracts, database schema, source registry, UI or native artifact changed in this slice, so D/B/packaged integration remains required when those paths are wired.

## Actual retrieval after Q

Command: `.venv/Scripts/python.exe -m scripts.qualify_market_history --live --symbol NVDA`.

Requested 2021-10-04 through 2026-10-03 (last completed Eastern date). One additional real-account EODHD request retrieved its entitled last-year window, followed by four anonymous Yahoo requests through pinned yfinance 1.7.0. No library mutation, model transmission, raw-response retention, paid-plan change or other data account query occurred.

| Result | EODHD primary | Yahoo via yfinance selected fallback |
| --- | --- | --- |
| Symbol | NVDA.US | NVDA |
| Daily rows | 250 | 1,255 |
| First / last date | 2025-10-06 / 2026-10-02 | 2021-10-04 / 2026-10-02 |
| Actions in this response | Not requested by this price-only primary | 21 dividends/splits |
| Currency / venue / type | Absent from price endpoint | USD / NMS / EQUITY |
| Exchange timezone | Absent | America/New_York |
| Close basis | Unadjusted | Split-adjusted |
| Original SHA-256 | `4ec031bcdb5d42e04dca5c45b4c2df8f9a0550582e29d79f6435b071e857b39b` | `e485e28fbb52c0a97ac64c655365e234fbe9543018f306403df0748b9eae4f68` |

The selected series passed boundary coverage; seven-day tolerance does not prove a complete exchange trading calendar. Both candidates explicitly retain `instrument_mapping_unverified`. EODHD's prior separate dividend/split preflight remains in [its original evidence](2026-10-04-eodhd-free-preflight.md); those responses are not silently attached to this price series. Original public references: [EODHD endpoint](https://eodhd.com/api/eod/NVDA.US), [Yahoo history](https://finance.yahoo.com/quote/NVDA/history/).

## Dependency inspection and remaining acceptance

`requirements-market-data.txt` pins optional developer yfinance 1.7.0, Apache-2.0. Its resolved packages were installed only in the developer virtual environment. Direct/transitive additions occupy approximately 139 MiB unpacked, including pandas/NumPy native binaries, curl_cffi and lxml. Metadata/notices inspected identify Apache-2.0 (yfinance/requests; multitasking Apache), BSD (pandas/lxml/protobuf/pycparser), NumPy's BSD/0BSD/MIT/Zlib/CC0 expression, MIT (curl_cffi/BeautifulSoup/peewee/platformdirs/pytz/charset-normalizer/soupsieve/urllib3/six), MIT-0 (cffi), and python-dateutil's dual license. Peewee's supplied LICENSE contains the MIT grant. This initial inventory does not qualify every bundled native notice/security update or installer redistribution. Normal setup/CI and production packaging do not import this optional adapter.

Exact installed versions: yfinance 1.7.0; beautifulsoup4 4.15.0; cffi 2.1.1; charset_normalizer 3.5.2; curl_cffi 0.16.3; lxml 6.1.3; multitasking 0.0.13; numpy 2.5.3; pandas 3.0.6; peewee 4.5.2; platformdirs 4.12.3; protobuf 7.36.2; pycparser 3.0; python-dateutil 2.9.0.post0; pytz 2026.5; requests 2.34.2; six 1.17.0; soupsieve 2.10; urllib3 2.8.0. Existing dependencies satisfied the remaining requirements. No optional price-repair extras were requested.

Next: independently associate vendor symbol/venue/type with the resolved instrument, establish operation-scoped permission handling, preserve immutable original source references, calculate compatible price/total returns and valuation inputs, integrate orchestration and dashboard, then run required D/B/Q and native checks. Personal retrieval success is neither permission for all storage/cloud/export operations nor public data redistribution. M4 and Windows public v1 remain incomplete.
