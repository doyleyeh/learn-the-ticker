# Top-500 Manifest Operator Guide

> 2026-05-02 lightweight policy note: This guide now describes the audit-quality top-500 stock manifest workflow. It is no longer the default blocker for personal-project stock page rendering. For the personal MVP, follow `docs/LIGHTWEIGHT_DATA_POLICY.md`: code may resolve recognized U.S.-listed common stocks through SEC/exchange/provider fallback with visible source labels and partial states, while this manifest remains a useful seed/cache and public-launch hardening artifact.

This guide documents the reviewed handoff path for the C2 launch universe. It is an operator workflow for producing and approving `data/universes/us_common_stocks_top500.current.json`; it is not a live ranking integration, an investment recommendation, or an automatic provider import.

## Current Implementation Gap

The repo currently has a small checksum-validated fixture manifest at `data/universes/us_common_stocks_top500.current.json`. It is useful for parser, classification, and smoke validation, but it is not launch coverage.

Implemented C2 support includes the manifest loader, checksum validation, runtime production-size/provenance guards, preflight inspection, pending-ingestion job enqueueing, deterministic smoke checks, and an opt-in private-GCS mirror smoke. Still missing are:

- a deterministic candidate generator for official IWB holdings and reviewed SPY/IVV/VOO fallback snapshots;
- a candidate diff report generator;
- an operator-reviewed 500-entry candidate manifest;
- private GCS mirror validation against the approved 500-entry manifest;
- GitHub Actions scheduled and `workflow_dispatch` candidate-generation PR automation.

Future agents should implement the generator and diff tooling with fixture snapshots first if real reviewed source exports are unavailable. Do not hand-author or fabricate the 500-entry current manifest.

## Safety Boundaries

- Treat the manifest as coverage metadata only. It is not an endorsement, recommendation, model portfolio, or ranked list for users to follow.
- Do not put provider keys, service-account JSON, access tokens, private bucket credentials, or paid-provider payloads in manifests, logs, docs, or committed files.
- Preserve the committed and approved top-500 manifest as the strict/audit-quality runtime source of truth. In lightweight personal-MVP mode, recognized U.S.-listed common stocks may also resolve through SEC/exchange/provider fallback with visible provenance and partial/fallback labels.
- Use official or reviewed source provenance strings. Launch manifests must not reference fixture, mock, test, or local sources.
- Keep local and CI defaults fixture-safe. Production-like validation should reject fixture-sized and fixture-provenance launch manifests.
- In strict mode, do not use the manifest to unlock generated pages, chat, comparison, Weekly News Focus, or AI Comprehensive Analysis before source-backed ingestion has produced supported evidence. In lightweight mode, fallback/source-labeled data may render partial educational output while missing sections stay unavailable.

## Monthly Source Policy

Each monthly refresh produces a candidate manifest and review packet. It does not directly update production coverage.

- Primary source: official iShares Russell 1000 ETF (`IWB`) holdings. Rank valid U.S. common-stock rows by portfolio weight and set `rank_basis = "iwb_weight_proxy"`.
- Fallback source: official S&P 500 ETF holdings from `SPY`, `IVV`, and `VOO`. Use the fallback only when IWB fails, is stale, cannot be parsed, or yields too few validated common-stock rows; set `rank_basis = "sp500_etf_weight_proxy_fallback"`.
- Strict runtime truth: the approved `data/universes/us_common_stocks_top500.current.json` manifest and its private GCS mirror. Lightweight runtime services may also use SEC/exchange/provider fallback to identify recognized U.S.-listed common stocks with source labels.
- Automation v1: GitHub Actions scheduled monthly candidate generation, with `workflow_dispatch` for manual reruns, should open a pull request containing only the candidate manifest, diff report, and related review artifacts.
- Automation v1.1: Cloud Scheduler can trigger a Cloud Run Job later, after manual Cloud Run Jobs and the GitHub Actions PR path are reliable. That job should still produce candidates for review, not directly promote runtime coverage.

A future scheduled workflow may run monthly and may also be started manually. It should download reviewed official source snapshots, run the root candidate/review scripts, write the candidate manifest, diff report, and inspect summary, upload those files as review artifacts, and open a pull request on an `automation/top500-candidate-YYYY-MM` branch. The workflow must not edit or stage `data/universes/us_common_stocks_top500.current.json`; promotion to the runtime manifest remains a separate manual approval step.

Manual reruns may override the official source URLs. Fallback mode requires `use_fallback=true`, SPY/IVV/VOO holdings URLs, and a non-empty fallback reason so the review packet records why IWB was not used.

## Normalize And Validate

Before ranking, normalize raw holdings rows and remove anything outside the v1 common-stock scope.

- Standardize ticker formats such as `BRK.B`, `BRK-B`, and provider-specific class-share symbols into the manifest's canonical ticker format.
- Exclude cash, futures, options, swaps, index rows, non-equity rows, ETFs, ETNs, preferred shares, warrants, rights, units, funds, crypto, leveraged products, inverse products, international listings, and other unsupported securities.
- Attach or confirm CIK, company name, ticker, and exchange using SEC `company_tickers_exchange.json`.
- Use Nasdaq Trader symbol-directory fields such as `ETF` and `Test Issue` to reject ETFs and test securities.
- Flag rows that cannot be validated. Do not silently include unvalidated rows just to reach 500 entries.

## Candidate Manifest Requirements

The approved launch candidate must satisfy these checks before it replaces the local fixture:

- `schema_version` matches the top-500 manifest schema expected by `app.services.universe`.
- `manifest_id` identifies the reviewed snapshot.
- `universe` is U.S. common stocks and `coverage_scope` is `approved_launch_top500`.
- The manifest has at least 500 entries.
- The candidate path uses `data/universes/us_common_stocks_top500.candidate.YYYY-MM.json`.
- The approved runtime path remains `data/universes/us_common_stocks_top500.current.json`.
- Ranks are unique, contiguous enough for review, and tied to either `iwb_weight_proxy` or `sp500_etf_weight_proxy_fallback`.
- Each entry includes ticker, company name, exchange, rank, rank basis, source provenance, source snapshot date, source checksum, validation status, warnings, approval timestamp, generated checksum, and CIK when available.
- Manifest-level and entry-level snapshot dates, rank basis, and approval timestamps agree.
- Required golden stock tickers `AAPL`, `MSFT`, and `NVDA` are present.
- The manifest contains no duplicate tickers and no unsupported security types such as preferred shares, rights, warrants, ETFs, ETNs, crypto, options, leveraged funds, inverse funds, or international listings.
- `generated_checksum` values are produced by the repo manifest loader and are stable for the approved content.

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

## Production Handoff Sequence

Start from reviewed official ETF holdings exports outside the repository. Keep raw source files uncommitted unless their license explicitly allows repository storage.

Generate the review-only candidate and diff report with the repo CLI. Primary IWB mode:

```bash
TMPDIR=/tmp python3 scripts/generate_top500_candidate_manifest.py \
  --candidate-month YYYY-MM \
  --rank-limit 500
```

Fallback SPY/IVV/VOO mode is allowed only when IWB is unavailable, stale, or unparseable, and it must carry the operator reason:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 generate \
  --candidate-month YYYY-MM \
  --rank-limit 500
```

The generator normalizes class-share ticker formats such as `BRK B`, rejects unsupported security rows before ranking, attaches SEC/Nasdaq validation warnings, writes `rank_basis = "iwb_weight_proxy"` or `rank_basis = "sp500_etf_weight_proxy_fallback"`, and never touches `us_common_stocks_top500.current.json`.

Create the monthly candidate JSON:

```bash
data/universes/us_common_stocks_top500.candidate.YYYY-MM.json
```

Keep the generated diff report next to the candidate manifest. It includes added and removed tickers, rank changes, missing CIKs, Nasdaq validation failures, exclusions, source mode, fallback reason when relevant, checksum, and manual-approval triggers.

Run the launch validator against the candidate. Do not pass `--allow-fixture-sized` for approval:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 inspect \
  --candidate-path data/universes/us_common_stocks_top500.candidate.YYYY-MM.json \
  --diff-path data/universes/us_common_stocks_top500.candidate.YYYY-MM.diff.json \
  --write-review-summary
```

Inspect the candidate and keep the JSON output with the operator review packet:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 inspect \
  --candidate-path data/universes/us_common_stocks_top500.candidate.YYYY-MM.json \
  --diff-path data/universes/us_common_stocks_top500.candidate.YYYY-MM.diff.json
```

After manual approval, promote the exact reviewed candidate content to the current manifest path:

```bash
data/universes/us_common_stocks_top500.current.json
```

Run the validator and preflight again on the promoted current manifest:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 inspect \
  --candidate-path data/universes/us_common_stocks_top500.current.json \
  --diff-path data/universes/us_common_stocks_top500.candidate.YYYY-MM.diff.json
```

```bash
TMPDIR=/tmp bash scripts/run_quality_gate.sh
```

After approval and promotion, enqueue pending ingestion jobs through the backend ingestion scheduler in a controlled operator run. The root review script remains review-only and does not mutate runtime manifests or create jobs:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 inspect \
  --candidate-path data/universes/us_common_stocks_top500.current.json \
  --diff-path data/universes/us_common_stocks_top500.candidate.YYYY-MM.diff.json
```

Confirm the pending-job coverage before moving to governed source ingestion:

```bash
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
```

In production-like shells, inspect the explicitly configured private mirror instead of relying on the local default path:

```bash
TOP500_UNIVERSE_MANIFEST_URI=gs://<private-gcs-bucket>/universe/us_common_stocks_top500.current.json \
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
```

`--from-env` fails when `TOP500_UNIVERSE_MANIFEST_URI` is unset, so operators do not accidentally preflight the committed fixture while intending to inspect the private mirror.

After the approved file is mirrored to private GCS and the operator shell has read access, run the credential-gated mirror smoke:

```bash
TOP500_MANIFEST_GCS_SMOKE_ENABLED=true \
TOP500_UNIVERSE_MANIFEST_URI=gs://<private-gcs-bucket>/universe/us_common_stocks_top500.current.json \
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
```

The default smoke skips this live check. When enabled, it requires `TOP500_UNIVERSE_MANIFEST_URI` to be a `gs://` URI and fails unless the mirrored manifest is launch-approved, not fixture-only, and has zero launch-readiness errors.

Run the deterministic smoke before relying on the handoff:

```bash
TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 generate --candidate-month YYYY-MM
TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 inspect \
  --candidate-path data/universes/us_common_stocks_top500.candidate.YYYY-MM.json \
  --diff-path data/universes/us_common_stocks_top500.candidate.YYYY-MM.diff.json
TMPDIR=/tmp bash scripts/run_quality_gate.sh
```

For production, mirror the exact approved file to the private GCS object configured by `TOP500_UNIVERSE_MANIFEST_URI`. Do not make the object public. After deployment, start the API or worker in a production-like environment and confirm startup uses the mirrored manifest rather than falling back to the local fixture.

## Official Source References

- IWB official page: https://www.ishares.com/us/products/239707/ishares-russell-1000-etf
- IWB official holdings CSV: https://www.ishares.com/us/products/239707/ishares-russell-1000-etf/?dataType=fund&fileName=IWB_holdings&fileType=csv
- SPY official page: https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy
- IVV official page: https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf
- VOO official Vanguard fact sheet: https://institutional.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/fact-sheet/F0968.pdf
- SEC company tickers exchange: https://www.sec.gov/file/company-tickers-exchange
- Nasdaq Trader symbol-directory definitions: https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs
- GitHub Actions scheduled workflows: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- GitHub Actions manual workflow runs: https://docs.github.com/actions/how-tos/managing-workflow-runs-and-deployments/managing-workflow-runs/manually-running-a-workflow
- `peter-evans/create-pull-request`: https://github.com/peter-evans/create-pull-request
- Cloud Run Jobs on a schedule: https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule
- Cloud Scheduler pricing: https://cloud.google.com/scheduler/pricing

## Review Packet

Record the following in the development log and operator notes:

- Source export names, dates, checksums, and reviewer.
- Whether the candidate used IWB primary sourcing or SPY/IVV/VOO fallback sourcing.
- Rank basis and snapshot date.
- Manifest ID, entry count, and generated checksum.
- Candidate path and diff report path.
- Validation command output.
- Preflight summary with required golden ticker coverage.
- Production mirror preflight summary from `--from-env`.
- Pending-job coverage summary after enqueue.
- GCS object URI for the private mirror, without credentials.
- Any excluded tickers and the reason, such as unsupported security type or missing review evidence.
- Confirmation that the manifest is coverage metadata, not investment advice.

## When To Stop

Stop and do not promote the manifest if any of these are true:

- The launch validator reports readiness errors.
- The candidate has fewer than 500 entries.
- Provenance refers to fixture, mock, test, local-only, or unreviewed sources.
- Required golden tickers are missing.
- The source license does not allow storing the reviewed manifest fields needed by the product.
- The candidate includes unsupported or out-of-scope securities.
- Fallback was used without explicit reviewer approval.
- Validation coverage is below the review threshold or top-ranked names disappear without an explained source reason.
- Operator review cannot explain the rank basis, snapshot date, approval timestamp, and checksum.

## Relationship To C3

C2 is complete only when backend search and classification use the approved manifest as the authority for supported pending-ingestion stocks. C3 can then use the enqueued jobs and governed source manifests to fetch, parse, chunk, and persist source-backed evidence for golden assets.
