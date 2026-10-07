# SEC financial observation checkpoint — 2026-10-04

M2-T02a component checkpoint after [public identity qualification](2026-10-04-public-identity-registries.md), commit `79a00e2`. M2-T02 and the M2 milestone remain incomplete. This adapter retrieves/normalizes issuer observations; it is not yet attached to the research publication path, persisted numeric contracts or charts.

## Scope

`SecFinancialAdapter` obtains instrument identity from the registered resolver and issuer identity separately from SEC. DEC-025 permits a narrow association only for current independent common-stock records with exactly matching normalized full names/symbols and reviewed NYSE/Nasdaq venue correspondence. Country composites, near names, uncertain types, multiple issuer matches and stale/changed proofs fail closed. Both identities/proofs remain separate; the adapter never adds a model-supplied CIK to an instrument.

Nine registered US-GAAP concepts cover assets, liabilities, equity, two distinct revenue concepts, net income, operating cash flow, diluted EPS and diluted weighted-average shares. Concept URLs and issuer CIKs are code-constructed after scope checking. Original concept/unit/period/accession/form/filed date and content hash remain attached to every observation. Decimal text prevents binary-float rounding. No currency conversion, concept splicing, imputed quarter, split adjustment, price, return or valuation is generated.

Annual/quarter/other duration follows actual start/end dates; fiscal labels are preserved as reported and do not redefine comparative periods. History windows preserve five annual years/twelve quarters and their versions, with gaps explicit. Instant observations retain up to twenty dates within five years. Latest reported values supersede earlier versions, while conflicting values on the latest filing date remain unresolved. This does not infer that every change was formally described as a restatement by the issuer.

Parsing rejects wrong CIK/taxonomy/concept, malformed dates/numbers, nonfinite/excessive decimal expansion, duplicate keys and deep/oversized responses. Limits remain 2 MB per response, 10,000 observations per concept and 128 revisions per period. Unknown units/forms are excluded with explicit gaps. Access/rate/server errors stop remaining requests; a missing concept can leave other registered concepts available. Cancellation stops follow-up requests and returns no partial result. HTTP status is retained only for control flow; raw source errors/bodies/headers never enter reports.

No dependency, SQL, wire-contract, archive format, frontend, runtime qualification or native permission changed. D/B evidence from the preceding checkpoint remains separate; financial persistence requires new contract and actual restore evidence before completion. The SEC contact was process-local and is absent from Git, source reports and distribution artifacts.

## Verification

- Initial parser: **30 tests passed**. Parser/adapter/admission: **98 passed**.
- Full Q initially passed **950 Python/seven frontend tests**. Review found and repaired a clock ordering issue before the live financial probe: proof age must be checked after network retrieval rather than against the earlier start time. An advancing-clock regression passed.
- Added controlled rate/access/server stop behavior, missing-concept continuation and malformed/deep/decimal/revision bounds. All targeted checks passed; no failing repair cycle occurred. Final parser/adapter suite: **59 passed**.
- Final `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1`: **961 Python/seven frontend tests**; Ruff/ESLint, non-writing contracts, documentation/whitespace checks, static evals, TypeScript and Vite build passed. Existing Starlette/httpx deprecation remains.
- Normal tests used synthetic identities/transports only. No live inference, account setup, financial database mutation or paid API service was used.

## Explicit live result

After Q, `python -m scripts.qualify_sec_financials --live --query FIGI:BBG000BPHFS9` passed on 2026-10-04. The venue ID was discovered through the real MSFT lookup, not added to production eligibility. The user-authorized SEC contact was provided only to that process. The helper reports counts/units/dates/hashes, not numeric values or source bodies.

Instrument identity SHA-256: `be6f3811383bd023c45997492890adce4a42e9c813e6ce455d9b7f274919e4ef`.
Issuer identity SHA-256: `33eed38bb9828b585d4306ac746e2e77758a1edd4d8fb0e298c92d2a955773d9`.

All sources are official SEC company-concept JSON for CIK `0000789019` under `https://data.sec.gov/api/xbrl/companyconcept/CIK0000789019/us-gaap/CONCEPT.json`. Counts include retained versions, not distinct periods.

| Concept | Observations | Units | Latest period / filing | Response SHA-256 |
| --- | --- | --- | --- | --- |
| Assets | 36 | USD | 2026-06-30 / 2026-07-29 | 2ff0b2139f5069216b2a099b8e565e79e88866b4287a519f83764d7fa8d5af08 |
| Liabilities | 36 | USD | 2026-06-30 / 2026-07-29 | 41c215d0012c8b25ed3860f8acfa0a5b11729e83e7d3cb97593269e96becd735 |
| StockholdersEquity | 51 | USD | 2026-06-30 / 2026-07-29 | 17e9edd9aad2025df1babd17245b7263f2e56fdaa30c91db7fe49211468d8b31 |
| Revenues | 23 | USD | 2010-12-31 / 2011-01-27 | 522057d949b70b538388f1e853fec8836a28af2ff011a3ab758f3af748ce11f2 |
| RevenueFromContractWithCustomerExcludingAssessedTax | 29 | USD | 2026-06-30 / 2026-07-29 | 5d82a226a193327e8ab7b39abc9a0950b1b3d72ca705fb4a0f8829cd1372d4dd |
| NetIncomeLoss | 29 | USD | 2026-06-30 / 2026-07-29 | f250857067216c551629feb1fe2ca30bc60a9cf5e4198780554c4b1e951012f9 |
| NetCashProvidedByUsedInOperatingActivities | 29 | USD | 2026-06-30 / 2026-07-29 | 43a1a63247191154ff40b0d15fe21e258468eac8918492742bf766403fe2621e |
| EarningsPerShareDiluted | 29 | USD/shares | 2026-06-30 / 2026-07-29 | 25e40e12d3e814b0ecf6f651ad3f4a51f83e035b2acd3bf91285187e7d3195a7 |
| WeightedAverageNumberOfDilutedSharesOutstanding | 29 | shares | 2026-06-30 / 2026-07-29 | 7875bdb1a20c14ee6e3117810d65c544a8e89ee4b27f392a193e4acdfdf87ecd |

The old Revenues concept stayed separate and visibly old; a recent download did not make it current. Most duration concepts reported incomplete quarterly history because no quarter was derived from annual/YTD data. Unsupported forms, other-duration periods and the short old annual revenue series stayed explicit. Prices and corporate actions were unavailable. This positive partial check does not qualify complete history, every instrument, current market data, numeric publication or M2-T03 online orchestration.

Primary references and rights review are in DEC-025 and the source registry. The [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) establishes whole-entity data scope; [published exchange-code metadata](https://www.openfigi.com/docs/OpenFIGI-exchange-codes.csv) supplies the narrowly reviewed venue correspondence. Neither source establishes a universal issuer/security crosswalk.

## Next acceptance

M2-T02b must introduce typed persisted numeric evidence with validated source/scope/version references, retain it through real backup/restore, and prove that unverified candidates cannot supply numerical/chart inputs. Expand applicable permitted adapters/history where available and keep unavailable price/corporate-action data explicit. M2-T03 then connects structured-first orchestration and separately qualifies current-source search/read/follow-up behavior. No dependent milestone or public release is complete from this component result.
