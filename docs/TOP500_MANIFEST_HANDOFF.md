# Top-500 Manifest Operator Guide

This guide documents the reviewed handoff path for the Top-500 launch universe. It is an operator workflow for producing and approving `data/universes/us_common_stocks_top500.current.json`; it is not a live ranking integration, investment recommendation, or automatic provider import.

## Current Implementation Status

The repo currently has a small checksum-validated fixture manifest at `data/universes/us_common_stocks_top500.current.json`. It is useful for parser, classification, and smoke validation, but it is not launch coverage.

Implemented support includes:

- manifest loader and checksum validation in `backend/data.py`;
- runtime search/support classification from the approved current manifest only;
- deterministic candidate and diff contract generation in `backend/top500_candidate_manifest.py`;
- fixture-backed script entrypoint at `scripts/generate_top500_candidate_manifest.py`;
- review-only operator packet generation and inspection at `scripts/review_launch_manifests.py`;
- candidate and diff fixtures at `data/universes/us_common_stocks_top500.candidate.2026-04.json` and `data/universes/us_common_stocks_top500.diff.2026-04.json`;
- tests proving candidate/diff artifacts do not replace runtime support truth.

Still missing for MVP:

- an operator-reviewed 500-entry candidate manifest from reviewed official source snapshots;
- production-sized reviewed source snapshots and private mirror validation;
- private mirror validation against the approved 500-entry manifest;
- scheduled or manually dispatched candidate-generation PR automation;
- source-backed ingestion coverage for the launch universe after manifest approval.

Do not hand-author or fabricate the 500-entry current manifest.

## Safety Boundaries

- Treat the manifest as coverage metadata only. It is not an endorsement, recommendation, model portfolio, or ranked list for users to follow.
- Do not put provider keys, service credentials, access tokens, private bucket credentials, or paid-provider payloads in manifests, logs, docs, or committed files.
- Preserve the committed and approved Top-500 manifest as the runtime source of truth. Do not replace it with a live ETF holdings file or provider ranking at request time.
- Use official or reviewed source provenance strings. Launch manifests must not reference fixture, mock, test, or local-only sources.
- Keep local and CI defaults fixture-safe. Production-like validation should reject fixture-sized and fixture-provenance launch manifests.
- Do not use the manifest alone to unlock generated pages, chat, comparison, Weekly News Focus, or AI Comprehensive Analysis before source-backed ingestion has produced supported evidence.

## Monthly Source Policy

Each monthly refresh produces a candidate manifest and review packet. It does not directly update production coverage.

- Primary source: official iShares Russell 1000 ETF (`IWB`) holdings. Rank valid U.S. common-stock rows by portfolio weight and set `rank_basis = "iwb_weight_proxy"`.
- Fallback source: official S&P 500 ETF holdings from `SPY`, `IVV`, and `VOO`. Use fallback only when IWB fails, is stale, cannot be parsed, or yields too few validated common-stock rows; set `rank_basis = "sp500_etf_weight_proxy_fallback"`.
- Runtime truth: the approved `data/universes/us_common_stocks_top500.current.json` manifest and its future private mirror. Runtime services must not read a live ETF holdings file to decide support status.
- Automation target: a future GitHub Actions workflow may open a pull request containing only the candidate manifest, diff report, and review artifacts. The current repo does not yet include that workflow.

## Normalize And Validate

Before ranking, normalize raw holdings rows and remove anything outside the v1 common-stock scope.

- Standardize ticker formats such as `BRK.B`, `BRK-B`, and provider-specific class-share symbols into the manifest's canonical ticker format.
- Exclude cash, futures, options, swaps, index rows, non-equity rows, ETFs, ETNs, preferred shares, warrants, rights, units, funds, crypto, leveraged products, inverse products, international listings, and other unsupported securities.
- Attach or confirm CIK, company name, ticker, and exchange using SEC `company_tickers_exchange.json`.
- Use Nasdaq Trader symbol-directory fields such as `ETF` and `Test Issue` to reject ETFs and test securities.
- Flag rows that cannot be validated. Do not silently include unvalidated rows just to reach 500 entries.

## Candidate Manifest Requirements

The approved launch candidate must satisfy these checks before it replaces the local fixture:

- schema version matches the Top-500 manifest schema expected by this repo;
- manifest ID identifies the reviewed snapshot;
- universe is U.S. common stocks and coverage scope is approved launch Top-500;
- manifest has at least 500 entries;
- candidate path uses `data/universes/us_common_stocks_top500.candidate.YYYY-MM.json`;
- approved runtime path remains `data/universes/us_common_stocks_top500.current.json`;
- ranks are unique and tied to either `iwb_weight_proxy` or `sp500_etf_weight_proxy_fallback`;
- each entry includes ticker, company name, exchange, rank, rank basis, source provenance, source snapshot date, source checksum, validation status, warnings, approval timestamp, generated checksum, and CIK when available;
- required golden stock tickers `AAPL`, `MSFT`, and `NVDA` are present;
- manifest contains no duplicate tickers and no unsupported security types.

## Repo-Native Candidate Fixture Command

The current script is fixture-backed and review-only. It is useful for testing the contract, not for producing a launch manifest:

```bash
python3 scripts/generate_top500_candidate_manifest.py --candidate-month 2026-04 --rank-limit 10
```

The launch review packet command writes the candidate manifest, diff report, and operator review summary without touching the approved current manifest:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 generate --candidate-month 2026-04 --rank-limit 10
```

To inspect an existing candidate and diff packet without regenerating fixture inputs:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 inspect \
  --candidate-path data/universes/us_common_stocks_top500.candidate.2026-04.json \
  --diff-path data/universes/us_common_stocks_top500.diff.2026-04.json
```

Both commands are deterministic by default, make no live provider calls, and report `pass`, `review_needed`, or `blocked` states. Fixture-sized, mock, local-only, unreviewed, parser-invalid, hidden/internal, unclear-rights, pending-review, rejected, stale, partial, unknown, unavailable, insufficient-evidence, fallback-source, low-validation-coverage, missing-golden-ticker, missing-review, and checksum-mismatch conditions are stop conditions for launch approval.

The generated operator review summary path follows:

```text
data/universes/us_common_stocks_top500.review.YYYY-MM.json
```

This summary is an operator artifact only. It is not a promotion path and is not investment advice.

Focused validation:

```bash
TMPDIR=/tmp python3 -m pytest tests/unit/test_top500_candidate_manifest.py tests/unit/test_search_classification.py tests/unit/test_repo_contract.py -q
```

Full validation:

```bash
TMPDIR=/tmp bash scripts/run_quality_gate.sh
```

## Candidate Diff Report

Every candidate must be reviewed against the current approved manifest before promotion. The diff report should include:

- source used, source snapshot dates, and source checksums;
- added tickers and removed tickers;
- rank changes, including large moves;
- rows with missing CIKs;
- rows that failed Nasdaq validation;
- rows excluded during normalization and the reason;
- validation coverage percentage;
- manifest ID, entry count, and generated checksum.

Manual approval is required when fallback sources are used, source snapshots are stale or unparseable, validation coverage is below threshold, many tickers change, or top-ranked names disappear.

## Promotion Rules

After manual approval, promote the exact reviewed candidate content to:

```text
data/universes/us_common_stocks_top500.current.json
```

Promotion must be a separate reviewed change. Candidate generation must never overwrite the current manifest automatically.

For production, mirror the exact approved file to the private object configured by `TOP500_UNIVERSE_MANIFEST_URI`. Do not make the object public. After deployment, start the API or worker in a production-like environment and confirm startup uses the mirrored manifest rather than falling back to the local fixture.

## Review Packet

Record the following in the development log and operator notes:

- source export names, dates, checksums, and reviewer;
- whether the candidate used IWB primary sourcing or SPY/IVV/VOO fallback sourcing;
- rank basis and snapshot date;
- manifest ID, entry count, and generated checksum;
- candidate path and diff report path;
- validation command output;
- preflight summary with required golden ticker coverage;
- private mirror URI without credentials;
- any excluded tickers and the reason;
- confirmation that the manifest is coverage metadata, not investment advice.

## When To Stop

Stop and do not promote the manifest if any of these are true:

- launch validation reports readiness errors;
- candidate has fewer than 500 entries;
- provenance refers to fixture, mock, test, local-only, or unreviewed sources;
- required golden tickers are missing;
- source license does not allow storing reviewed manifest fields needed by the product;
- candidate includes unsupported or out-of-scope securities;
- fallback was used without explicit reviewer approval;
- validation coverage is below the review threshold or top-ranked names disappear without an explained source reason;
- operator review cannot explain rank basis, snapshot date, approval timestamp, and checksum.

## Relationship To Governed Evidence

Top-500 coverage is complete for launch only when backend search and classification use the approved manifest as the authority for supported pending-ingestion stocks. Governed source ingestion then needs reviewed source packs to fetch, parse, chunk, persist, cite, generate, cache, export, and render evidence for those assets.

## Official Source References

- IWB official page: https://www.ishares.com/us/products/239707/ishares-russell-1000-etf
- IWB official holdings CSV: https://www.ishares.com/us/products/239707/ishares-russell-1000-etf/?dataType=fund&fileName=IWB_holdings&fileType=csv
- SPY official page: https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy
- IVV official page: https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf
- VOO official Vanguard fact sheet: https://institutional.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/fact-sheet/F0968.pdf
- SEC company tickers exchange: https://www.sec.gov/file/company-tickers-exchange
- Nasdaq Trader symbol-directory definitions: https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs
