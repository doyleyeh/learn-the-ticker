# ETF Manifest Handoff Operator Guide

> 2026-05-02 lightweight policy note: This guide now describes the audit-quality ETF source-pack and manifest workflow. It is no longer the default blocker for personal-project ETF page rendering. For the personal MVP, follow `docs/LIGHTWEIGHT_DATA_POLICY.md`: code should try official issuer/index sources automatically, fall back to reputable third-party/provider data when official data is incomplete, and show official/third-party/provider source labels plus partial/unavailable states in the UI.

This guide documents the reviewed handoff path for v1 ETF coverage. It is an operator workflow for producing and approving ETF recognition and supported ETF manifests; it is not a live ETF screener integration, investment recommendation, or automatic provider import.

## Runtime Policy

Audit-quality ETF coverage uses two manifests:

- `data/universes/us_etp_recognition.current.json` recognizes real exchange-traded products for search safety, including unsupported products.
- `data/universes/us_equity_etfs_supported.current.json` is the strict runtime authority for audit-quality supported ETF-generated experiences.

The recognition manifest may let search identify ETFs, ETNs, ETVs, closed-end funds, commodity products, active ETFs, fixed income ETFs, single-stock ETFs, option-income/buffer ETFs, leveraged ETFs, inverse ETFs, international equity ETFs, and other complex products. These rows can return blocked states such as `unsupported`, `out_of_scope`, `pending_review`, `unavailable`, or `pending_ingestion`.

In strict/audit-quality mode, the supported ETF manifest unlocks generated ETF asset pages, chat answers, comparisons, Weekly News Focus, AI Comprehensive Analysis, and exports only after every support gate passes. In lightweight personal-MVP mode, recognized U.S.-listed, active, non-leveraged, non-inverse ETFs may render educational pages from official-source automation or reputable third-party/provider fallback when source provenance, fallback labels, freshness, and partial states are shown. Live provider ETF flags, exchange listings, issuer search results, or recognition rows must still not unlock clearly unsupported complex products or unknown tickers by themselves.

## Supported ETF Scope

Strict/audit-quality supported ETFs must be:

- U.S.-listed and active;
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

The named public-v1 ETF target is ETF-500: around 500 reviewed U.S.-listed, active, non-leveraged, non-inverse, passive/index-based ETFs with primary U.S. equity exposure and validated issuer source packs. The practical acceptance range is 475-525 approved supported ETF rows after review quality gates. If only 470 ETFs pass all gates in a cycle, promote 470 and leave the rest as recognition-only, pending-review, unsupported, unavailable, or out-of-scope rows rather than padding the supported manifest.

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

ETF-500 candidate artifacts should use the next named paths:

```text
data/universes/us_equity_etfs_supported.candidate.2026-05.etf500.json
data/universes/us_etp_recognition.candidate.2026-05.json
data/universes/us_equity_etfs.candidate.2026-05.etf500.promotion-packet.json
```

Promote in batches so review defects surface early:

| Batch | Target supported count | Purpose |
| --- | ---: | --- |
| ETF-50 | 50 | Core parser validation across major issuers and categories |
| ETF-150 | 150 | Local support beyond golden ETFs |
| ETF-300 | 300 | Category-complete local coverage |
| ETF-500 | 475-525 | Full reviewed ETF-500 target |

The ETF-50 batch should start as a source-pack review packet, not a supported runtime manifest. Generate it from the ETF-500 review draft so the packet uses the same taxonomy and candidate filters as the broader pipeline:

```bash
python scripts/generate_etf50_source_pack_review_packet.py \
  --review-draft data/universes/us_equity_etfs_supported.candidate.2026-05.etf500.review-draft.json \
  --candidate-month 2026-05 \
  --generated-at 2026-04-30T00:00:00+00:00 \
  --output data/universes/us_equity_etfs_supported.candidate.2026-05.etf50.source-pack-review-packet.json \
  --review-output data/universes/us_equity_etfs_supported.candidate.2026-05.etf50.source-pack-review-packet.tsv
```

The generated packet is review-only. Every row must remain `promotion_allowed=false`, `source_pack_status=missing`, `parser_validated=false`, and `golden_source_handoff_approved=false` until an operator collects official issuer documents, approves Golden Asset Source Handoff, runs parser validation, and records manual approval.

After operator review updates the packet with approved issuer documents, parser results, source-handoff checks, scope checks, and supported-manifest metadata, run the promotion gate. The current missing-source packet should write a report only and should not write a supported candidate manifest:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect \
  --supported-path data/universes/us_equity_etfs_supported.current.json \
  --recognition-path data/universes/us_etp_recognition.current.json
```

The gate may write a supported ETF candidate manifest only for rows with approved source-pack status, passed parser validation, approved Golden Asset Source Handoff, passed scope checks, explicit row-level promotion permission, and complete supported-manifest metadata. It still does not mutate `data/universes/us_equity_etfs_supported.current.json`.

For ETF-50 source collection, generate the operator workbook from the source-pack packet and promotion-gate report. The workbook covers every ETF-50 row and every required/optional issuer document task, including issuer-domain allowlist status and empty operator fields for URLs, document IDs, as-of dates, checksums, source-use policy, parser status, and GASH status:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect \
  --supported-path data/universes/us_equity_etfs_supported.current.json \
  --recognition-path data/universes/us_etp_recognition.current.json
```

Issuer-domain gaps in this workbook are source-governance work. Add or change domains only through `config/source_allowlist.yaml`, source-use policy, rationale, validation tests, and development-log review; automated scoring or workbook generation must not approve new domains.

The committed ETF-50 workbook currently has allowlisted issuer domains for Vanguard, iShares, Invesco, State Street/SPDR, Schwab, VanEck, and Pacer rows. It also has reviewed official index-provider methodology domains for the ETF-50 benchmark set, including S&P Dow Jones Indices, CRSP, FTSE Russell/LSEG, MSCI, Nasdaq, MarketVector, Morningstar Indexes, ICE/NYSE, and Research Affiliates. That domain approval only covers source identity and source-use policy; it does not approve any individual ETF document, parser result, Golden Asset Source Handoff status, supported-manifest metadata, or runtime ETF support.

The ETF-500 review draft and ETF-50 workbook include deterministic screening fields for `exchange`, `asset_class`, `strategy`, `leverage_flag`, `inverse_flag`, and `etn_flag` so scope review can reject unsupported wrappers before evidence use. The ETF-50 source-pack packet keeps broad-core exposure data optional only when the issuer fund page or fact sheet carries reliable exposure fields; narrower size, concentrated, style, dividend, factor, alternative-weighted, sector, thematic, ESG, faith, and stewardship rows treat `exposure_or_sector_data` as conditional-required. `index_methodology_or_benchmark_source` tasks include `index_provider_guess` and `index_provider_domains` for operator collection, including known mappings for major S&P/Dow Jones, Nasdaq, CRSP, FTSE Russell, Morningstar, ICE/NYSE, MarketVector, Pacer, and RAFI-style index providers. TSV semicolon lists are emitted without spaces so parsers can split deterministically while still trimming defensively.

The ETF-500 generator also records ticker-alias policy and universe-completeness watchlist rows. For the 2026-05 draft, `SPLG -> SPYM` is tracked as a State Street/SPDR current-ticker alias effective 2025-10-31. If neither the prior nor current ticker appears in the local AUM ranking snapshot, the draft records `SPYM` in `universe_completeness_watchlist` instead of silently treating it as out of scope. Operators must refresh the ranking/exchange snapshots or add an explicitly reviewed source-rank exception before inserting that row into ETF-50.

Source-rank exceptions are review inputs, not source approval. The generator accepts them through `--source-rank-exceptions`; the committed 2026-05 input is `data/universes/us_equity_etfs_supported.candidate.2026-05.etf500.source-rank-exceptions.json`. That file records the operator-reviewed `SPYM` include decision using the official State Street fund page and ticker-change notice as screening references. Exception rows may enter the ETF-500 draft and ETF-50 source-pack packet, but they must still remain `promotion_allowed=false`, `source_pack_status=missing`, `parser_validated=false`, and `golden_source_handoff_approved=false` until official source collection, parser review, GASH review, scope checks, and final manual promotion approval pass.

ETF-50 is category-balanced, not a pure top-by-AUM cut. The source-pack packet records `selection_audit.unselected_higher_rank_rows` for eligible source-rank rows above the packet tail that were deferred because their category target was already filled. Rows such as `SCHB`, `IUSG`, `VXF`, and `MDY` remain ETF-500 review candidates when deferred by this audit; they are not unsupported unless a separate scope/source review rejects them.

The workbook separates issuer and product brand. For example, State Street/SPDR rows use `issuer_guess=State Street Investment Management` and `brand=SPDR`, while Vanguard, iShares, Invesco, Schwab, VanEck, and Pacer rows carry the same visible product brand as their issuer family. Issuer domains stay separate from index-provider domains. Adding index-provider domains beyond the reviewed ETF-50 set remains source-governance work; suggested methodology domains in future workbooks are collection hints until the corresponding domain is reviewed in `config/source_allowlist.yaml`.

When an operator has reviewed the ETF-50 workbook template, workbook document tasks may use `review_status=operator_workbook_reviewed_pending_source_collection`. This status means the collection worksheet was reviewed, not that any source document is approved evidence. The workbook fills `source_use_policy` from the reviewed source allowlist when every suggested domain for the task is allowlisted; otherwise it uses `pending_source_use_policy_review`. Individual source documents still need URLs, source document IDs, as-of dates, checksums, parser status, Golden Asset Source Handoff approval, scope checks, and manual approval before promotion.

After the workbook is reviewed, generate the ETF-50 source-collection draft as the operator work queue for URL and checksum collection. Candidate URLs in this draft are official-domain locators, not verified source documents; exact PDFs, holdings files, methodology pages, checksums, as-of dates, parser results, and Golden Asset Source Handoff status still need operator collection and validation:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect \
  --supported-path data/universes/us_equity_etfs_supported.current.json \
  --recognition-path data/universes/us_etp_recognition.current.json
```

To reduce manual URL hunting, generate automated source-collection review candidates from the official locator URLs. This command fetches only allowlisted official locator pages, scans for exact document/file links and full as-of dates, and writes a review-candidate JSON/TSV for operator inspection. It does not approve source evidence, parser output, Golden Asset Source Handoff, promotion, or runtime ETF support:

```bash
DATA_POLICY_MODE=lightweight \
LIGHTWEIGHT_LIVE_FETCH_ENABLED=true \
LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true \
TMPDIR=/tmp python3 scripts/run_lightweight_data_fetch_smoke.py --live --ticker VOO --json
```

The generated file uses `review_kind=automated_source_collection_suggestions` and `approval_status=requires_operator_review`. The source-collection review applier rejects that file until an operator reviews the suggestions, fixes locator/date/domain blockers, and explicitly changes `approval_status` to `operator_approved`. This keeps automation on the collection side only: code can propose exact URLs, as-of dates, and conditional coverage notes, but it cannot silently become approval evidence.

The auto-review generator may use issuer-specific discovery adapters when the source-collection draft starts from an official issuer search or locator page. The iShares and State Street/SPDR adapters follow allowlisted official search or fund-finder results to the matching official product page before scanning for exact fact sheet, prospectus, holdings-download, and exposure-download candidates. The fetcher follows only bounded redirects whose destination still passes the same allowlist and expected-source-type checks. Adapter output is still only an automated suggestion: exact URL detection, full as-of-date detection, and `ready_for_operator_approval` status do not approve the source document, checksum, parser result, Golden Asset Source Handoff, scope, supported-manifest metadata, promotion, or runtime ETF support.

When measuring live issuer locators, write auto-review outputs to `/tmp` unless an operator has explicitly reviewed and requested committed artifacts. A small ETF-50 measurement subset can use `--ticker VOO --ticker IVV --ticker SPY --ticker QQQ` with issuer fund page, fact sheet, prospectus, holdings, and exposure document-type filters. Treat the counts as triage signals only: live 404/301 behavior, JavaScript-only fund finders, generic privacy links, or product-family redirects are collection blockers, not approval evidence.

After the operator verifies source-collection rows, apply the required-source verification audit to a copy of the source-collection draft. This records verified URLs, as-of metadata when known, exact-document versus locator-only blockers, allowlist status, and retrieval-ready flags. It still does not fetch content, record checksums, approve parser output, approve Golden Asset Source Handoff, approve scope, write a supported ETF candidate manifest, or unlock runtime ETF support:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect \
  --supported-path data/universes/us_equity_etfs_supported.current.json \
  --recognition-path data/universes/us_etp_recognition.current.json
```

The reviewed partial collection is still blocked for promotion. Rows marked `retrieval_ready=true` have an allowlisted official verified URL and a full `YYYY-MM-DD` as-of date. Locator-only holdings rows, document-center rows, unallowlisted domains such as unresolved rightprospectus/RAFI aliases, missing as-of dates, partial month-only as-of values, parser-not-run rows, and GASH-not-started rows must remain blocked.

After the operator has applied URL verification, run governed retrieval to fetch only retrieval-ready verified allowlisted URLs and emit an operator source-pack draft with checksums. This still does not approve parser output, Golden Asset Source Handoff, source-pack rows, or runtime ETF support:

```bash
DATA_POLICY_MODE=lightweight \
LIGHTWEIGHT_LIVE_FETCH_ENABLED=true \
LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true \
TMPDIR=/tmp python3 scripts/run_lightweight_data_fetch_smoke.py --live --ticker VOO --json
```

After governed retrieval, run parser diagnostics against the same verified source-collection draft. The diagnostics command refetches only verified, allowlisted official URLs, runs the paragraph parser, and writes parser counts and statuses only. It does not store raw source text or chunks, approve Golden Asset Source Handoff, update the source-pack packet, or unlock runtime ETF support:

```bash
TMPDIR=/tmp python3 -m pytest tests/unit/test_search_classification.py -q
```

Parser diagnostics are proof-of-parse metadata only. A passed parser diagnostic does not set `parser_validated=true` on an ETF row and does not approve a source document as evidence. Operators must still review the exact parsed source, approve Golden Asset Source Handoff, fill required source-pack fields, pass scope checks, and manually approve promotion before any supported ETF manifest can be written.

After an operator reviews parser diagnostics for exact source documents, apply a parser-review input to a copy of the operator-draft packet. The parser review must bind each approved parser result to the same ticker, document type, URL, source document ID, checksum, and as-of date already recorded in the packet. The applier rejects diagnostics that include raw source text or chunks, rejects checksum mismatches between retrieval and parser diagnostics, and still leaves Golden Asset Source Handoff, manual review, source-pack approval, and runtime ETF support blocked:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect
```

A parser-reviewed packet should still fail the promotion gate until every required source document has approved review status, approved Golden Asset Source Handoff status, passed scope checks, supported-manifest metadata, row-level promotion permission, and final manual approval. Parser review only records that the selected fetched document was parseable and operator-reviewed for parser status.

After an operator completes Golden Asset Source Handoff review for parser-reviewed documents, apply a GASH review input to a copy of the parser-reviewed packet. The GASH review must bind each approved source to the same ticker, document type, URL, source document ID, checksum, as-of date, source-use policy, and raw-source-text policy already recorded in the packet. It also requires every row-level Golden Asset Source Handoff check to be explicitly approved. This step approves source handoff only; it still leaves scope review, supported-manifest metadata, final manual approval, row-level promotion permission, and runtime ETF support blocked:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect
```

A GASH-reviewed packet should still fail the promotion gate until every scope check passes, supported-manifest metadata is complete and deterministic, `manual_review_decision=approved`, `promotion_allowed=true` is set on the row by final manual promotion review, and the source-pack status is advanced to `approved`. The GASH applier must not be used to write `data/universes/us_equity_etfs_supported.current.json`.

For local parser and promotion-gate validation, fixture-only source-pack reviews may be applied to a copy of the ETF-50 packet. This path is for regression proof only and must not be treated as production source approval:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect
```

The fixture-reviewed packet can then be passed to the source-pack promotion gate to prove that approved rows become a candidate manifest and unreviewed rows stay blocked. Do not commit fixture-reviewed packets as production review evidence, and do not promote them to `us_equity_etfs_supported.current.json`.

For real operator collection, use an operator source metadata draft to record official URLs, source document IDs, as-of dates, retrieval timestamps, and checksums on a copy of the ETF-50 packet without approving those documents:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect
```

An operator-draft packet should still fail the promotion gate. It records source metadata only; `review_status`, parser status, Golden Asset Source Handoff status, row promotion permission, and runtime unlock must stay pending or false until the real approval work is complete.

## Current Runtime Implementation

The local runtime now includes fixture-backed split ETF manifest loaders and classification enforcement. The current committed supported ETF manifest is a golden fixture, not ETF-500 launch coverage:

- `backend/etf_universe.py` loads `data/universes/us_equity_etfs_supported.current.json` for generated-output support.
- `backend/etf_universe.py` loads `data/universes/us_etp_recognition.current.json` for blocked or pending recognition states.
- `scripts/review_launch_manifests.py` exposes the repo-native ETF candidate inspection command.
- `scripts/run_local_fresh_data_rehearsal.py` validates local manifest loading, production fixture-scope blocking, frontend/API smoke markers, and optional local readiness checks.
- The current ETF production mirror setting is `EQUITY_ETF_UNIVERSE_MANIFEST_URI`; future split mirror settings may be added only with matching tests and docs.
- Backend search merges persisted assets, reviewed classifications, supported ETF rows, Top-500 stock rows, recognition-only blocked ETF/ETP rows, and exact unknowns without letting recognition-only rows unlock generated output.
- Persisted ETF rows marked supported are blocked unless their ticker is present in the supported ETF manifest.
- Route and coverage tests prove recognition-only, unsupported, out-of-scope, unavailable, pending-ingestion, and unknown states remain generated-output-ineligible.
- The legacy `data/universes/us_equity_etfs.current.json` file remains for repository continuity and historical fixtures, not as runtime authority for generated ETF support.

Repo-native validation commands:

```bash
TMPDIR=/tmp python3 -m pytest tests/unit/test_search_classification.py -q
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect
```

Repo-native review-only candidate inspection command:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect \
  --supported-path data/universes/us_equity_etfs_supported.current.json \
  --recognition-path data/universes/us_etp_recognition.current.json
```

The command compares candidate manifests against `data/universes/us_equity_etfs_supported.current.json` and `data/universes/us_etp_recognition.current.json` as separate runtime authorities. It reports additions, removals, status changes, overlap errors, checksum validity, and promotion-packet metadata without writing runtime manifests.

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
3. Product review confirms U.S.-listed, active, passive/index-based, primary U.S. equity exposure.
4. Disqualifier review rejects leverage, inverse exposure, single-stock structure, derivatives-first strategy, option-income/buffer strategy, fixed income, commodity, crypto, active, multi-asset, international equity, or other unsupported scope.
5. Issuer source pack includes official issuer page, fact sheet, prospectus or summary prospectus, holdings file, exposure or sector data when available, risk/methodology source, and sponsor announcements where relevant.
6. Golden Asset Source Handoff approves source identity, source type, official-source status, storage rights, export rights, source-use policy, rationale, parser validity, freshness/as-of metadata, and review status.
7. Parser validation proves minimum ETF facts, holdings, risks, citations, freshness labels, and partial/unavailable states can be produced without invented claims.
8. Manual approval records source dates, checksums, warnings, exclusions, reviewer, and rationale.

## Promotion Rules

- Candidate manifests are review artifacts only. They must not replace runtime manifests automatically.
- Promotion to `data/universes/us_equity_etfs_supported.current.json` is manual and should later be mirrored to the private production object configured by `SUPPORTED_ETF_MANIFEST_URI`.
- Promotion to `data/universes/us_etp_recognition.current.json` can broaden search recognition, but it cannot unlock generated ETF experiences. Production recognition promotion should be mirrored to the private object configured by `ETP_RECOGNITION_MANIFEST_URI`.
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

- ETF-500 launch-sized operator manifests once official issuer source packs and Golden Asset Source Handoff evidence are available;
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
