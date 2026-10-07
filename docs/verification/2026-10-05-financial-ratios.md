# Retained issuer percentages

Date: 2026-10-05 (Asia/Taipei). Task: M4-T01g1. Decision: DEC-044. M4 and Windows public v1 remain incomplete.

## Delivered scope

New SEC financial snapshots retain exact same-filing net-income/revenue percentages separately from reported observations. Each result carries the method, exact interval, individual input IDs, both original source references and either a rounded percentage or an explicit missing reason. Separate revenue concepts, units and annual/quarter intervals are not combined. Latest conflicts/differently filed inputs cannot fall back to older matching figures. Negative income is accepted; nonpositive revenue is withheld. No price/EPS/share-basis inference or model numerical input is introduced.

Statistics displays saved results with expandable exact inputs, original filing/accession/retrieval dates and version-specific source links. Older snapshots acquire no result on opening. Permitted SEC calculations survive factual-context reuse, Markdown/JSON exports and same-user backup/restore; private Yahoo values remain excluded from cloud/export context. No dependency, paid access, SQL migration, archive version or source-policy expansion.

## Verification

- Targeted: `.venv/Scripts/python.exe -m pytest tests/desktop/test_financial_ratios.py tests/desktop/test_financial_evidence.py tests/desktop/test_evidence_reuse.py -q` — **90 passed**. Includes 31 new ratio cases covering exact/ties-even/negative arithmetic, different currencies/filings/periods, conflicts, ambiguous same-value filings, restatements, history bounds, tampering, legacy versions, cited reuse, private-market filtering and authenticated exports.
- Q: `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` — **1,602 Python / 60 frontend tests passed**, lint, contracts, local docs, static evaluations, TypeScript and production build. Existing Starlette/httpx deprecation only. Generated schema/types match Pydantic.
- D: `.venv/Scripts/python.exe -m scripts.verify database` — authenticated service startup, private cluster transaction/recovery and actual second-cluster restore/restart passed. The restored 13-version library includes two available ratio periods plus explicit conflict/nonpositive gaps. Exact method/results/input/source IDs and factual context survived; existing saved/current versions, imports, private market results and opt-in reset still passed. No provider calls.
- B: `npm run test:browser` — full deterministic workflow passed, retries disabled; keyboard ratio disclosure, two original citations tied to the same saved version, filing dates, missing conflict state, normal/640-pixel layout and existing review/reconnect/offline/private workflows. Inspected `financial-ratios-narrow.png`: readable wrapped dates/accessions, no horizontal page overflow. Owned preview ports 1420/18764 were no longer listening after exit.
- React review: direct component imports, no new network requests/effects/state synchronization, stable keys, native keyboard-operable details, bounded input rendering and exact decimal-string presentation. The client shows stored calculations and guards references; it does not calculate a new ratio.

Ignored logs: `.local/financial-ratios-quality.log`, `financial-ratios-database.log`, `financial-ratios-browser.log`, `financial-ratios-live.json`. Browser screenshots remain under ignored `output/playwright/automated`.

## Bounded live SEC check

After Q, ran `.venv/Scripts/python.exe -m scripts.qualify_sec_financials --live --query FIGI:BBG000BBK0R0` with the previously authorized SEC contact supplied only to that process. Independently resolved instrument and issuer, retrieved nine registered concepts, attached/validated the numerical document and round-tripped it. **15 available / 17 unavailable** results; reasons: `different_filings`, `missing_income`. No library writes, inference, market-account call or Yahoo retrieval.

Original retrieval range: **2026-10-04T16:41:47.018042+00:00 through 2026-10-04T16:41:51.262149+00:00** (October 5 locally). Latest revenue/net-income reporting end 2026-07-26, filed 2026-08-26. The distinct customer-contract revenue concept ends 2022-01-30, filed 2022-03-18; it is not silently joined to newer revenue.

| Original concept URL | Original response SHA-256 |
| --- | --- |
| https://data.sec.gov/api/xbrl/companyconcept/CIK0001045810/us-gaap/Revenues.json | `a110a9c6472ec39a5a7d10c6064e9794f2285a5153ec77215b33736f2ff20a63` |
| https://data.sec.gov/api/xbrl/companyconcept/CIK0001045810/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax.json | `e9b2ce25e35f73f913d1a8d2f1f8daaf3c49ccab2e02e903f31943bc64447250` |
| https://data.sec.gov/api/xbrl/companyconcept/CIK0001045810/us-gaap/NetIncomeLoss.json | `adc6c1e85f24848df63d82926f0c9ca9fd55c4fd7d6babe5db57a4f197898685` |

The first invocation stopped at issuer association because this shell lacked the SEC contact variable; it fetched no concepts. Supplying the previously authorized process-local contact resolved it on one retry. No identifier-matching rule was weakened.

## Repairs and limits

Initial new synthetic payloads omitted required issuer name; corrected the fixture. A history-bound test initially supplied only three quarters per year, so the existing three-year window correctly retained ten; supplied four explicit quarters to test the twelve-quarter cap without inventing production data. TypeScript's bounded-array union required a Set for source membership. The first B selector used visible citation text instead of its existing accessible name; corrected it and added exact-version assertions. All affected checks passed; no skipped/weakened gate or repeated unresolved repair.

This is scoped financial-statistics acceptance, not full financial parity, historical P/E, live news/analyst coverage or public distribution. The existing native installer predates these ratio fields and is not qualified for this checkpoint. Historical valuation still needs independently compatible EPS/share-class/split bases. M4-T01g remains open.
