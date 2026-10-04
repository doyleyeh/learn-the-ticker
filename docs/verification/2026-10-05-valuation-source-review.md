# Historical valuation source review and delivery-order proposal

Date: 2026-10-05. M4-T01g remains incomplete. This review does not activate a source, qualify a valuation, change source rights or change milestone dependencies.

## Concrete remaining gap

The app now has independently matched five-year private price history, retained return calculations, SEC issuer observations, same-filing net-income/revenue percentages, daily quote fields and explicit valuation gaps. It cannot yet show a positively qualified historical valuation. Dividing split-adjusted Yahoo closes by an independently retrieved issuer EPS series does not establish that both use the same share class and split basis. The latest filing date alone is not that proof. Weighted-average diluted shares also cannot stand in for shares outstanding at the price date.

This is an input/permission qualification gap, not a missing API key, compiler or user-agent contact. The accepted private-history exception remains sufficient for its existing scope; it is not being reopened. No new credential or paid upgrade is requested in this proposal.

## Existing provider candidates

Reviewed public primary documents only; no credential-bearing market/news account request, signup, billing change, provider message or new dataset persistence occurred during this review. Existing account plan labels are unverified user metadata, not rights evidence.

| Candidate | Observed public documentation | Implication for this app |
| --- | --- | --- |
| SEC + admitted Yahoo history | Existing typed SEC observations contain original issuer units/periods/filings; private market history records its price adjustment basis, but neither establishes common per-share compatibility. | A share-class and corporate-action proof/normalizer is still needed before historical P/E. Preserve separate original series. |
| EODHD | [Fundamentals documentation](https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds) distinguishes sample/demo tickers and free access limited to past-year EOD; [pricing](https://eodhd.com/pricing) separates fundamentals access. | Existing free price access does not establish fundamentals entitlement. No paid probe/upgrade or demo-as-production claim. |
| Tiingo | [Fundamentals docs](https://www.tiingo.com/documentation/fundamentals) describe daily P/E and market-cap data and limited free/evaluation coverage. [Terms section 1.6](https://app.tiingo.com/tos/) (updated 2026-08-05) prohibit Starter/Trial durable retention, including backups. Paid retention ends with the applicable subscription unless separately agreed. Non-reconstructable derived products have a separate narrow rule. | Free numerical data cannot populate this saved-fact/backup library under the current policy. A renamed field, ordinary ratio plus inputs, chart or encrypted archive does not resolve that restriction. Do not activate its stored-data adapter. |
| Finnhub | [Terms](https://finnhub.io/terms-of-service) require deletion when a data subscription ends and written approval for sharing data or derived results with third parties. | Existing indefinite saved-work and cloud-context paths need scoped permission/lifecycle treatment before activation. No account was queried. |
| FMP | [Terms](https://site.financialmodelingprep.com/terms-of-service) separate personal use from third-party display, require written approval for copying/downloading content, and restrict third-party sharing/derived services. | A stored personal-library adapter cannot be assumed qualified solely from a free key or attribution. No account was queried. |
| Alpha Vantage | [Terms](https://www.alphavantage.co/terms_of_service/) support private individual analysis; [API docs](https://www.alphavantage.co/documentation/#company-overview) offer company ratios and earnings history; the vendor also documents agent/MCP integration. Company Overview has no historical-date parameter and is generally refreshed around financial reports. | A promising candidate for separately attributed profile/current metrics, but this does not establish an aligned historical P/E series. Confirm operation-specific retention/backup/cloud behavior, source dates, adjustment semantics and secret-safe authentication before admission. No API key was sent in a URL or account call. |

These are conservative engineering admission conclusions under SPEC P-012, not a determination of every legal use or a claim that all alternatives are impossible. No new source exception is inferred. Detailed sources are linked so a later check can revisit changed terms or account-specific permission.

## SEC share-basis feasibility follow-up

The existing bounded SEC transport successfully retrieved NVIDIA's diluted-EPS concept and submissions index using the previously authorized process-local contact. It resolved the actual primary documents for the current five annual observations; no filename was guessed and no financial value or contact was written to Git. No inference, market-account request or application-library write occurred.

| Reporting interval | Current EPS accession | Filed | Primary filing |
| --- | --- | --- | --- |
| 2021-02-01 through 2022-01-30 | 0001045810-24-000029 | 2024-02-21 | [2024 Form 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm) |
| 2022-01-31 through 2023-01-29 | 0001045810-25-000023 | 2025-02-26 | [2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm) |
| 2023-01-30 through 2024-01-28 | 0001045810-26-000021 | 2026-02-25 | [2026 Form 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) |
| 2024-01-29 through 2025-01-26 | 0001045810-26-000021 | 2026-02-25 | Same 2026 filing |
| 2025-01-27 through 2026-01-25 | 0001045810-26-000021 | 2026-02-25 | Same 2026 filing |

The 2025 and 2026 filings identify Nasdaq NVDA common stock and explicitly describe retrospective adjustment of presented per-share amounts for the June 2024 ten-for-one split. The oldest retained EPS above comes from a filing preceding that event. This is concrete evidence that treating every retained EPS as having one adjustment basis is unsafe; it also identifies a possible official-source route to resolve the gap. Search found no split wording in the 2024 document, but absence of a phrase is not a machine-verifiable basis declaration.

The production transport independently retrieved the complete 2026 filing within its existing 2,000,000-byte limit (1,967,924 bytes); no limit or network policy changed. Merely finding disclosures in this review does not implement their admission or prove all required adjustments. Next implementation work must bind document/issuer/accession, exact EPS context and share class to an explicit basis; reconcile relevant corporate actions without applying already reflected splits twice; retain original input references and a versioned method; and reject unproven cases. A latest report can establish some comparative periods without proving the oldest period. No hard-coded NVIDIA exception or generated prose should authorize numerical inputs.

Read-only retrieval evidence (UTC; checks conducted on local 2026-10-05):

| Source | Retrieved | SHA-256 |
| --- | --- | --- |
| [SEC diluted-EPS concept](https://data.sec.gov/api/xbrl/companyconcept/CIK0001045810/us-gaap/EarningsPerShareDiluted.json) | 2026-10-04T16:52:20.822632+00:00 | `37b0d3d0359a2df943f80c4a4c3e959be3d6ec255ed39b8499364265d471759c` |
| [SEC submissions index](https://data.sec.gov/submissions/CIK0001045810.json) | 2026-10-04T16:54:38.556472+00:00 | `0b3ce6a0cd78c43d69b19b7efb9effcd79d0c6bd4c43606aac84d0f872cc9c73` |
| 2026 filing linked above | 2026-10-04T16:55:09.249881+00:00 | `5b4027bd6ba9682f6aedfda9387cf31a4c2ca8ba515ec99a64190699006a9a94` |

An initial helper invocation used an invalid relative Python module name and stopped before network access; corrected `runpy.run_path` invocation succeeded. This was not a source/admission failure or a bypass. The three successful bounded reads were not retried. Public-page browser inspection is corroborating research, not production evidence admission. Source/method qualification remains IN_PROGRESS, with no positive historical valuation result yet.

## Proposed delivery order — not yet approved

[PLAN.md](../../PLAN.md) currently says: “A blocked dependency prevents dependent milestones; independent tasks within the current milestone may continue.” M5 and M6 depend on M4; M7 also depends on M4. Consequently the unqualified positive historical valuation blocks their current milestone order even though much of their required evidence infrastructure is implemented.

Proposed limited change:

1. Keep M4-T01g and M4 overall open until positive aligned historical valuation and final parity acceptance pass. Do not mark unavailable-only valuation as complete.
2. Permit independent M5 conversation/learning, M6 comparison/offline and M7 report work to use the already verified identity, immutable evidence, financial/market and source boundaries. Each new slice must pass its own required checks.
3. Any workflow requiring missing valuation data continues to show a gap. Do not create model-implied prices/earnings or new offline calculations.
4. Preserve all SPEC requirements and the M11 dependency on completed M1–M10. Public release still cannot proceed with historical valuation, source permissions, providers, native lifecycle/update/rollback or clean-machine checks missing.
5. Keep valuation-source qualification active as an explicit work item. No new paid service, policy exception, API billing, public exposure or publication is authorized by this sequence adjustment.

This would change PLAN dependencies deliberately, not lower completion criteria. The alternative is to retain the current order and continue only M4 source/alignment qualification until that gate passes. No provider inquiry has been sent.

## Verification boundary

Current implementation checkpoint `93ea632` passed Q (1,602 Python/62 frontend) and B; `8549152` passed actual D and scoped live SEC. This source review adds documentation only. No live historical-valuation qualification has passed. Record any accepted ordering decision in DECISIONS and PLAN before starting dependent work.

For this documentation checkpoint, `.venv/Scripts/python.exe -m scripts.verify fast` passed correctness lint, non-writing contracts, all 74 local Markdown documents/anchors, whitespace and TypeScript. The complete documentation diff was reviewed. No code, schema, dependency, native artifact or source policy changed; Q/D/B results above retain their original checkpoint scope. The ordering question remains unanswered and M4-T01g3 remains IN_PROGRESS.
