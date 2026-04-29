# MVP Launch Readiness Regression Matrix

Task: T-114

This matrix is the deterministic launch-readiness regression layer before production deployment work. It records what the current fixture-backed system must keep proving, without enabling live providers, recurring jobs, production databases, production object storage, paid market/news providers, or deployment wiring.

## Scope Boundary

- Home remains a single supported stock or ETF search first.
- Comparison remains a separate connected `/compare` workflow.
- Glossary remains contextual help inside asset, comparison, and chat reading flows.
- Source drawer, glossary, and asset chat preserve mobile bottom-sheet or full-screen behavior markers.
- Stock-vs-ETF comparison preserves relationship badges and the single-company-vs-ETF-basket structure.
- Weekly News Focus renders only the evidence-backed set, including smaller verified sets and empty states.
- Runtime stock support reads `data/universes/us_common_stocks_top500.current.json`; candidate Top-500 refresh work is a later reviewed workflow and must not replace the approved current manifest automatically.
- Supported ETF generated-output coverage reads `data/universes/us_equity_etfs_supported.current.json`; ETF-500 is the v1 supported ETF target, golden/pre-cache ETF tickers are regression assets only, and the manifest-defined eligible universe may expand across broad/core beta, market-cap and size/style, sector, industry/theme, dividend/shareholder-yield, factor/smart-beta/equal-weight, and ESG or values-screened ETFs after source-pack validation.
- Golden Asset Source Handoff remains the approval gate between retrieval and evidence use. Fetching a source is not permission to store it as evidence, cite it, summarize it, cache it, export it, or generate from it.

## Launch Pre-Cache Coverage

| Area | Deterministic coverage | Required regression checks | Follow-up boundary |
| --- | --- | --- | --- |
| Cached supported assets | `AAPL`, `VOO`, and `QQQ` have existing local knowledge packs and generated-output availability. | Search returns `cached_supported`; asset pages can render; chat, comparison, source drawer, glossary, and exports use fixture-backed approved metadata. | Broader generated content requires handoff-gated persisted source packs. |
| Eligible launch assets | Top-500 fixture stocks outside local packs and current supported-manifest ETFs such as `MSFT`, `NVDA`, `SPY`, `VTI`, `IVV`, `IWM`, `DIA`, `VGT`, `XLK`, `SOXX`, `SMH`, `XLF`, and `XLV` are `eligible_not_cached`; ETF-500 category coverage and broader eligible ETF categories and reference tickers such as `XLE` need reviewed source-pack readiness before runtime support. | Search and ingestion expose pending/running/failed pre-cache states with no generated page, chat answer, comparison, citations, source documents, or generated-output cache hit. | On-demand or pre-cache generation remains blocked until validated source packs exist. |
| Unsupported assets | Crypto, leveraged ETFs, inverse ETFs, fixed-income ETFs, commodity ETFs, active ETFs, multi-asset ETFs, and similar blocked products are recognized where fixture metadata exists. | Search, ingestion, pre-cache, chat, comparison, exports, and source drawer paths expose blocked capabilities and no generated output. | Adding a new supported asset class is out of scope for MVP readiness. |
| Out-of-scope assets | U.S. common stocks outside the current Top-500 manifest and ETN-style products are recognized as out of scope where fixture metadata exists. | `GME` and `VXX` remain blocked from generated pages, generated chat, generated comparisons, risk summaries, and source exports. | Top-500 monthly candidate refresh is reviewed later and does not change runtime truth. |
| Unknown or unavailable assets | Unknown tickers and unavailable fixture states return non-generated states. | Unknown/no-result copy says facts are not invented; unavailable pre-cache job status stays non-generated. | No live lookup is performed in normal CI. |

## Backend Route Matrix

| Surface | States covered | Regression expectations |
| --- | --- | --- |
| `/api/search` | supported, ambiguous, pending ingestion, unsupported, out of scope, unknown, unavailable-like gaps | Rows show stock-vs-ETF identity, support-state chips, generated capability flags, and blocked explanations where relevant. Runtime stock support is manifest-backed, not provider-ranked. |
| `/api/assets/{ticker}/overview` | supported, partial, stale, unknown, unavailable, insufficient evidence | Beginner Summary, Top 3 Risks, Key Facts, freshness labels, citations, and stable/timely separation remain visible when supported. Missing evidence stays labeled. |
| `/api/assets/{ticker}/weekly-news` | available selected set, limited verified set, empty/no-high-signal, suppressed analysis | U.S. Eastern market-week windows, official-source priority, configured-vs-selected counts, no padding, and AI Comprehensive Analysis threshold stay enforced. |
| `/api/compare` | ETF-vs-ETF, stock-vs-stock, stock-vs-ETF, unsupported, out of scope, pending, no local pack | Comparison output is generated only from available deterministic packs. Stock-vs-ETF uses relationship badges and special structure. |
| `/api/assets/{ticker}/chat` | educational answer, advice redirect, compare redirect, insufficient evidence, unsupported/unknown | Single-asset chat stays grounded in the selected asset pack and redirects second-ticker questions to `/compare`. |
| `/api/assets/{ticker}/sources` | available, unsupported, out of scope, unknown, eligible-not-cached | Source drawer returns approved metadata and allowed excerpts only; blocked states return no unrestricted text. |
| `/api/assets/{ticker}/glossary` | generic context, asset-specific context, unavailable term | Asset-specific context is same-asset cited; generic definitions do not invent asset facts. |

T-119 local web/API plumbing note: local browser smoke verifies that chat POSTs, export URLs, and comparison requests reach FastAPI through either `NEXT_PUBLIC_API_BASE_URL`/`API_BASE_URL` or the Next `/api/:path*` rewrite, and that direct browser calls are covered by `CORS_ALLOWED_ORIGINS`.

ETF split note: T-120 implemented the split between `data/universes/us_equity_etfs_supported.current.json` and `data/universes/us_etp_recognition.current.json`. Launch-readiness checks must preserve that recognition-only rows never unlock generated ETF pages, chat, comparisons, Weekly News Focus, AI Comprehensive Analysis, or exports.
| Export endpoints | asset page, source list, comparison, chat transcript, blocked/unavailable | Markdown and JSON exports include disclaimer, citations, freshness, uncertainty, source-use policy, and no restricted raw content. |
| Ingestion and pre-cache routes | pending, running, succeeded, failed, unsupported, out of scope, unknown, unavailable | Deterministic jobs do not create provider calls, source facts, citations, generated pages, generated chat, generated comparisons, risk summaries, or generated-output cache records unless an existing validated fixture already provides them. |

## Frontend Workflow Matrix

| Surface | Regression markers |
| --- | --- |
| Home search | One primary single-asset search action; no two-input comparison builder; no glossary primary workflow; `A vs B` search routes to `/compare?left=...&right=...`. |
| Search results | Stock/ETF identity, support-state chips, exact unsupported behavior, no-result copy, ambiguous disambiguation, and backend-preferred with deterministic fallback behavior. |
| Asset page | Beginner Summary before Top 3 Risks and Key Facts; citation chips; source-list access; Weekly News Focus and AI Comprehensive Analysis after stable facts; chat, glossary, and export controls remain available. |
| Source drawer | Desktop drawer and mobile bottom-sheet markers; source-use policy, allowlist status, freshness, related claims, and allowed excerpt notes. |
| Glossary | Inline term triggers; desktop hover/click/focus; mobile bottom-sheet; asset-specific citations only when grounded. |
| Asset chat | Helper role, selected-asset pack boundary, mobile bottom-sheet/full-screen marker, advice redirect, compare redirect, no raw transcript analytics. |
| Comparison | Empty builder, one-side-selected builder, two-side result, blocked/partial states, examples-not-recommendations, source-backed deterministic pack, stock-vs-ETF relationship badge and basket structure. |
| Exports | Markdown/JSON only; compact mobile behavior; citations, sources, freshness, disclaimer, and restricted-content exclusion markers. |

## Source-Use And Handoff Matrix

| Source state | Evidence storage | Generated output | Citation/source drawer | Generated-output cache | Export |
| --- | --- | --- | --- | --- | --- |
| Approved official or allowed fixture with compatible policy | Allowed according to storage rights | Allowed when parser/freshness/citation checks pass | Allowed metadata and permitted excerpt only | Allowed after validation | Allowed metadata and permitted excerpt only |
| Unapproved or not-governed | Blocked | Blocked | Blocked | Blocked | Blocked |
| Unclear rights | Blocked or pending review | Blocked | Metadata only if explicitly safe | Blocked | Blocked except safe metadata when policy permits |
| Parser-invalid | Blocked as evidence | Blocked | Diagnostics only when safe | Blocked | Blocked |
| Hidden/internal | Blocked | Blocked | Blocked | Blocked | Blocked |
| Pending review | Blocked | Blocked | Blocked except safe diagnostics | Blocked | Blocked |
| Rejected | Blocked | Blocked | Blocked | Blocked | Blocked |

## Weekly News And AI Analysis Matrix

| Case | Expected behavior |
| --- | --- |
| Enough approved selected Weekly News items | Show up to the configured maximum, cite selected items, label reputable third-party reporting, and allow AI Comprehensive Analysis only when threshold and canonical citations pass. |
| One selected item | Show the single verified item, label the limited set, and suppress AI Comprehensive Analysis as insufficient evidence. |
| Zero selected items | Show the normal empty state and suppress AI Comprehensive Analysis. |
| Duplicate, promotional, wrong-asset, weak, unapproved, rejected, or rights-disallowed items | Exclude from selected Weekly News Focus and from AI Comprehensive Analysis inputs. |
| Recent news conflicts with canonical facts | Keep Weekly News Focus visually and structurally separate; do not let it redefine stable asset identity. |

## Required Regression Commands

The T-114 quality gate runs:

```bash
npm test
npm run typecheck
npm run build
python3 -m pytest tests/integration/test_backend_api.py -q
python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_ingestion_jobs.py tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
git diff --check
```
