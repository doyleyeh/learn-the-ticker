# ETF Manifest Handoff Operator Guide

This guide documents the reviewed handoff path for v1 ETF coverage. It is an operator workflow for producing and approving ETF recognition and supported ETF manifests; it is not a live ETF screener integration, investment recommendation, or automatic provider import.

## Runtime Policy

ETF coverage uses two manifests:

- `data/universes/us_etp_recognition.current.json` recognizes real exchange-traded products for search safety, including unsupported products.
- `data/universes/us_equity_etfs_supported.current.json` is the only runtime authority for supported ETF-generated experiences.

The recognition manifest may let search identify ETFs, ETNs, ETVs, closed-end funds, commodity products, active ETFs, fixed income ETFs, single-stock ETFs, option-income/buffer ETFs, leveraged ETFs, inverse ETFs, international equity ETFs, and other complex products. These rows can return blocked states such as `unsupported`, `out_of_scope`, `pending_review`, `unavailable`, or `pending_ingestion`.

The supported ETF manifest unlocks generated ETF asset pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, and exports only after every support gate passes. Live provider ETF flags, exchange listings, issuer search results, or recognition rows must not unlock generated output by themselves.

## Supported ETF Scope

V1 supported ETFs must be:

- currently U.S.-listed and active as exchange-traded listings;
- non-leveraged and non-inverse;
- passive/index-based;
- primary U.S. equity exposure;
- not single-stock, derivatives-first, option-income/buffer, fixed income, commodity, crypto, active, multi-asset, ETN, ETV, CEF, or international equity products;
- backed by an official issuer source pack that passed Golden Asset Source Handoff;
- parser-validated for the minimum required facts, citations, freshness, and section states.

The supported ETF manifest should be an eligible-universe workflow, not a fixed launch list. It may include reviewed U.S.-listed passive/index-based primary-U.S.-equity ETFs across broad U.S. index, total-market/large-cap, size/style, sector, industry/theme, dividend, value/growth, quality, momentum, low-volatility, equal-weight, and ESG index categories once issuer source packs validate.

Golden/pre-cache tickers such as `VOO`, `QQQ`, and the broader regression reference set are only reliability and regression assets. They are not the ETF coverage ceiling.

The manifest is operational coverage metadata only. It is not an endorsement, recommendation, model portfolio, allocation, or statement of suitability.

## ETF-500 Coverage Target

The named public-v1 ETF target is ETF-500: around 500 reviewed, currently U.S.-listed, non-leveraged, non-inverse, passive/index-based ETFs with primary U.S. equity exposure and validated issuer source packs. The practical acceptance range is 475-525 approved supported ETF rows after review quality gates. If only 470 ETFs pass all gates in a cycle, promote 470 and leave the rest as recognition-only, pending-review, unsupported, unavailable, or out-of-scope rows rather than padding the supported manifest.

ETF-500 should be category-complete enough for beginner comparison workflows:

| ETF bucket | Target count | Selection intent |
| --- | ---: | --- |
| Broad/core U.S. equity beta | 45 | S&P 500, total market, Russell-style, Nasdaq-100, Dow, and broad equal-weight exposure |
| Market-cap and size/style | 95 | Large/mid/small, growth/value/blend, Russell/S&P/CRSP-style exposures |
| Sector ETFs | 120 | Multiple issuer families across the main U.S. equity sectors |
| Industry/theme passive U.S. equity | 105 | Semiconductors, biotech, banks, homebuilders, software, cybersecurity, transportation, and similar passive U.S.-equity-primary themes |
| Dividend and shareholder-yield index ETFs | 55 | Dividend growth, high dividend, quality dividend, aristocrats-style, and shareholder-yield index funds |
| Factor, smart beta, and equal-weight | 60 | Quality, momentum, value, low/minimum volatility, multifactor, equal-weight, and fundamental index exposure |
| ESG / values-screened U.S. equity index | 20 | Broad U.S. equity ESG or values-screened passive funds with clear methodology |

ETF-500 candidate artifacts should use the following named paths:

```text
data/universes/us_equity_etfs_supported.candidate.YYYY-MM.etf500.json
data/universes/us_etp_recognition.candidate.YYYY-MM.json
data/universes/us_equity_etfs.candidate.YYYY-MM.etf500.promotion-packet.json
```

Promote in batches so review defects surface early:

| Batch | Target supported count | Purpose |
| --- | ---: | --- |
| ETF-50 | 50 | Core parser validation across major issuers and categories |
| ETF-150 | 150 | Local support beyond golden ETFs |
| ETF-300 | 300 | Category-complete local coverage |
| ETF-500 | 475-525 | Full reviewed ETF-500 target |

## Current Runtime Implementation

The local runtime now includes fixture-backed split ETF manifest loaders and classification enforcement. The current committed supported ETF manifest is a golden fixture, not ETF-500 launch coverage:

- `backend/etf_universe.py` loads `data/universes/us_equity_etfs_supported.current.json` for generated-output support.
- `backend/etf_universe.py` loads `data/universes/us_etp_recognition.current.json` for blocked or pending recognition states.
- `backend/etf_universe.py` builds review-only launch packet summaries for the supported and recognition manifests without promoting runtime manifests.
- `scripts/review_launch_manifests.py` exposes the repo-native ETF manifest inspection command.
- The current implementation uses `EQUITY_ETF_UNIVERSE_MANIFEST_URI` as the production mirror metadata field for ETF manifest records. Future work may split this into separate supported and recognition mirror variables, but the current code does not yet do that.
- Backend search merges persisted assets, reviewed classifications, supported ETF rows, Top-500 stock rows, recognition-only blocked ETF/ETP rows, and exact unknowns without letting recognition-only rows unlock generated output.
- Persisted ETF rows marked supported are blocked unless their ticker is present in the supported ETF manifest.
- Route and coverage tests prove recognition-only, unsupported, out-of-scope, unavailable, pending-ingestion, and unknown states remain generated-output-ineligible.
- The legacy `data/universes/us_equity_etfs.current.json` file remains for repository continuity and historical fixtures, not as runtime authority for generated ETF support.

Repo-native validation commands:

```bash
TMPDIR=/tmp python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_provider_adapters.py tests/unit/test_repo_contract.py -q
TMPDIR=/tmp python3 evals/run_static_evals.py
```

Repo-native review-only inspection command:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect
```

The command inspects `data/universes/us_equity_etfs_supported.current.json` and `data/universes/us_etp_recognition.current.json` as separate launch-review packets. It reports support-state, wrapper/scope, exclusion flags, eligible category coverage, excluded product counts, pending-review rows, source-pack readiness, source provenance, generated checksums, approval timestamps, evidence/freshness/source-use metadata, parser or handoff metadata where available, blocked-state reasons, and explicit `pass`, `review_needed`, or `blocked` status.

The command is deterministic by default and makes no live provider, issuer, market-data, news, database, storage, browser, or LLM calls. It does not write or promote runtime manifests.

Run the full deterministic gate before relying on a manifest change:

```bash
TMPDIR=/tmp bash scripts/run_quality_gate.sh
```

## Candidate Discovery

Candidate discovery may use official and free-first inputs, but no input approves support automatically.

- Nasdaq Trader symbol-directory fields such as `ETF` and `Test Issue` help validate symbols and reject test issues.
- Nasdaq-listed ETP data fields such as `Type`, `Bucket Label`, and `Investment Strategy Group` help identify single-stock, derivatives-strategy, fixed income, emerging market, crypto, or multi-asset products before support review.
- NYSE listings distinguish ETFs from exchange-traded vehicles, exchange-traded notes, and closed-end funds.
- Cboe U.S. ETF listings are useful recognition inputs because Cboe lists ETFs, ETNs, CEFs, and other exchange-traded products.
- SEC ETF website posting requirements support requiring official issuer holdings, market information, bid-ask spread, premium/discount, and related disclosures where applicable.

Provider/reference data may enrich candidate review only after source-use rights are understood. It must not override official exchange, regulatory, or issuer evidence.

## Supported Manifest Entry Expectations

Each supported ETF entry should include enough metadata for deterministic runtime classification and review:

- ticker and fund name;
- issuer and primary exchange;
- wrapper type;
- support scope;
- active/listing status;
- passive/index flag and benchmark/index when available;
- leverage and inverse flags;
- asset class and primary geographic exposure;
- disqualifier flags for single-stock, derivatives-first, option-income/buffer, fixed income, commodity, crypto, active, multi-asset, ETN, ETV, CEF, and international equity scope;
- issuer source-pack references;
- Golden Asset Source Handoff approval status;
- parser validation status and diagnostics;
- snapshot date, source dates, checksums, generated checksum, approval timestamp, reviewer, and review notes.

Recognition manifest rows can be lighter, but they must still include ticker, name, wrapper or product type when known, exchange when known, recognition sources, review state, support/block reason, snapshot date, and generated checksum.

## Support Gates

Do not promote an ETF to `us_equity_etfs_supported.current.json` unless every gate passes:

1. Exchange or regulatory recognition confirms the ticker is real and not a test issue.
2. Wrapper review confirms the product is an ETF and not an ETN, ETV, CEF, fund closed to creation, or other unsupported wrapper.
3. Product review confirms currently U.S.-listed, passive/index-based, primary U.S. equity exposure.
4. Disqualifier review rejects leverage, inverse exposure, single-stock structure, derivatives-first strategy, option-income/buffer strategy, fixed income, commodity, crypto, active, multi-asset, international equity, or other unsupported scope.
5. Issuer source pack includes official issuer page, fact sheet, prospectus or summary prospectus, holdings file, exposure or sector data when available, risk/methodology source, and sponsor announcements where relevant.
6. Golden Asset Source Handoff approves source identity, source type, official-source status, storage rights, export rights, source-use policy, rationale, parser validity, freshness/as-of metadata, and review status.
7. Parser validation proves minimum ETF facts, holdings, risks, citations, freshness labels, and partial/unavailable states can be produced without invented claims.
8. Manual approval records source dates, checksums, warnings, exclusions, reviewer, and rationale.

## Promotion Rules

- Candidate manifests are review artifacts only. They must not replace runtime manifests automatically.
- Promotion to `data/universes/us_equity_etfs_supported.current.json` is manual and should later be mirrored to the private production object recorded in manifest metadata as `EQUITY_ETF_UNIVERSE_MANIFEST_URI`.
- Promotion to `data/universes/us_etp_recognition.current.json` can broaden search recognition, but it cannot unlock generated ETF experiences. Production recognition promotion should use the current ETF manifest mirror metadata field, `EQUITY_ETF_UNIVERSE_MANIFEST_URI`, unless a future implementation explicitly splits the mirror variables.
- Any ETF expansion beyond the v1 supported scope requires a named product decision with new source requirements, risk templates, parser coverage, and acceptance tests.
- Do not commit raw restricted source text, provider payloads with unclear rights, service credentials, access tokens, or provider keys.

## Review Packet Stop Conditions

Stop and do not promote ETF manifests when the review packet reports any of these conditions:

- fixture-sized, fixture, mock, test, local-only, unreviewed, pending-review, rejected, or unclear-rights source provenance;
- parser-invalid, hidden/internal, stale, partial, unknown, unavailable, or insufficient-evidence source states;
- intended supported ETF candidate tickers missing from the supported manifest;
- generated checksum mismatch in either manifest;
- recognition-only rows attempting to unlock generated pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, exports, or generated risk summaries;
- unsupported/out-of-scope products lacking blocked-state reasons or exclusion flags;
- missing manual review or missing source-pack Golden Asset Source Handoff approval.

Golden Asset Source Handoff remains the approval layer before any retrieved ETF issuer evidence can be stored as evidence, cited, summarized, generated from, cached, or exported. This review command does not approve new sources or relax source-use rights.

## Remaining Implementation

Future tasks should add:

- launch-sized operator manifests once official issuer source packs and Golden Asset Source Handoff evidence are available;
- private mirror validation for launch-sized manifests;
- full-manifest local tests proving supported rows resolve through the supported ETF loader and recognition-only rows stay generated-output-ineligible;
- tests that preserve official-vs-third-party Weekly News labels and rights-gated full-text behavior.

## References

- NYSE listings directory: https://www.nyse.com/listings_directory/etf
- NYSE ETP regulation: https://www.nyse.com/regulation/exchange-traded-products
- Nasdaq Trader symbol-directory definitions: https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs
- Nasdaq-listed ETP data definitions: https://www.nasdaqtrader.com/Trader.aspx?id=etf_definitions
- Cboe U.S. ETF listings: https://www.cboe.com/listings/us/etf/
- SEC ETF website posting requirements: https://www.sec.gov/about/divisions-offices/division-investment-management/accounting-disclosure-information/adi-2025-15-website-posting-requirements
