# Source Handoff Operator Guide

> 2026-05-02 lightweight policy note: This guide now describes the strict/audit-quality source handoff path. It is no longer the default blocker for ordinary personal-project page rendering. For the personal MVP, follow `docs/LIGHTWEIGHT_DATA_POLICY.md`: code should try official sources automatically, fall back to reputable third-party/provider data when official data is incomplete, show source provenance and freshness clearly, and render partial states instead of requiring an operator to approve every URL, checksum, parser result, and as-of date first.

This guide documents the reviewed source handoff path for the C3 source ingestion worker. It is an operator workflow, not an automatic live-provider integration.

Golden Asset Source Handoff is the audit-quality approval layer between retrieval and evidence use. API clients, SEC/issuer fetch commands, provider endpoints, and downloaded payloads are retrieval only in strict mode. In lightweight mode, a fetched or provider-derived source may support personal-project display when provenance, official-vs-third-party/provider labels, retrieved dates, available as-of dates or date precision, rights-safe output limits, and uncertainty/fallback states are preserved.

## Current Enforcement Status

The repo now enforces the core machine-readable Golden Asset Source Handoff fields for governed-source ingestion.

- Implemented: allowlist domain/source-type/source-quality checks, storage rights, export rights, source-use policy, allowlist review status, parser-validation requirement, freshness/as-of requirement, SSRF-style URL safety, SEC and issuer fetch CLIs, draft/finalized governed source manifests, governed manifest preflight, one-shot governed ingestion, persisted source documents/chunks, and deterministic source-handoff/worker smoke scripts.
- Enforced before governed ingestion: non-allowlisted URLs, rejected policies, incompatible source types, mismatched storage/export rights, non-approved review status, parser-invalid sources, and missing as-of metadata fail before jobs are claimed or source rows are persisted.
- Still missing for MVP: governed source artifacts for the full golden set, deployed/automated worker execution, governed-text normalized fact extraction, and proof that governed evidence drives golden API/frontend output.

Repo-native strict/audit command map:

- Handoff policy code lives in `backend/source_policy.py`, with reviewed domains and rights policy in `config/source_allowlist.yaml`.
- Source handoff packets use `source-handoff-manifest-v1` and are inspected or finalized through `scripts/inspect_source_handoff_manifest.py`.
- Inspect a draft or finalized packet with `TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py inspect path/to/source-handoff-manifest.json --strict`.
- Finalize a fully reviewed packet with `TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py finalize path/to/source-handoff-manifest.json --output path/to/finalized-source-handoff-manifest.json`.
- Run the full deterministic gate with `TMPDIR=/tmp bash scripts/run_quality_gate.sh`.

## Safety Boundaries

- Keep local and CI defaults mock-safe.
- Do not put provider keys or secrets in manifests, logs, docs, or committed files.
- Use SSRF-safe server-side retrieval/provider adapters. In strict mode, use only allowlisted or explicitly reviewed official sources with compatible source-use policy.
- Treat source discovery output as a review artifact, not investment advice.
- Do not pass unfinalized `draft=true` manifests to the worker.
- Do not store or export restricted raw source text through public routes.
- In strict mode, mark missing, unclear, hidden/internal, parser-invalid, or non-allowlisted sources as `pending_review` or `rejected` instead of using them as evidence.
- In lightweight mode, unresolved official-source gaps should trigger alternate official discovery, reputable fallback, or `partial`/`unavailable` labels rather than a whole-page block.

## Machine-Readable Handoff Checklist

The following fields are explicit in `config/source_allowlist.yaml` and governed source manifests:

- `domain`: the bare allowlisted domain or reviewed official source host.
- `source_type`: the approved source type, such as `sec_filing`, `etf_fact_sheet`, `etf_holdings`, `company_investor_relations`, or `provider_metadata`.
- `is_official`: whether the source is official for the asset and claim role.
- `storage_rights`: whether the product may store metadata only, links only, limited excerpts, parsed text, or full text.
- `export_rights`: whether exports may include URL/metadata only, allowed excerpts, summaries, or full text.
- `source_use_policy`: one of `metadata_only`, `link_only`, `summary_allowed`, `full_text_allowed`, or `rejected`.
- `rationale`: why this source is appropriate for the claimed evidence role.
- `parser_validated`: whether parser validity was checked before handoff approval.
- `freshness`: as-of date, published date where applicable, retrieved timestamp, and stale/unknown/unavailable state.
- `review_status`: `approved`, `pending_review`, or `rejected`.

In strict/audit-quality mode, only `review_status=approved` sources with compatible storage/export rights, non-rejected source-use policy, `parser_validated=true`, and required freshness metadata may become evidence. Fetch commands and provider adapters may produce candidates, and governed ingestion still validates the manifest against the allowlist before claiming jobs. In lightweight mode, source metadata and normalized facts may be displayed with fallback/partial labels before full handoff approval.

## Approval vs Retrieval

Retrieval is a mechanical operation: dry-run discovery, SEC submissions lookup, SEC filing fetch, issuer fetch, or provider/API payload download. Approval is the Golden Asset Source Handoff decision that lets a retrieved source become product evidence.

For stocks such as `AAPL` and `NVDA`, approved canonical evidence should come first from SEC EDGAR, SEC XBRL company facts, and SEC filing documents. Company investor-relations pages, earnings releases, and presentations can be official secondary sources for recent context and management explanations.

For every supported ETF, including ETF-500 rows beyond `VOO`, `QQQ`, and `SOXX`, support has two gates. First, the ETF must be approved in `data/universes/us_equity_etfs_supported.current.json`; recognition-only rows in `data/universes/us_etp_recognition.current.json` can support blocked search states but cannot unlock generated output. Second, approved canonical evidence should come from issuer materials: official issuer page, fact sheet, prospectus or summary prospectus, shareholder reports, holdings files, exposure files, risk/methodology sources, and sponsor announcements.

V1 supported ETF source packs are limited to ETF-500: around 500 reviewed U.S.-listed, active, non-leveraged, non-inverse, passive/index-based U.S. equity ETFs with primary U.S. equity exposure and validated issuer source packs, with 475-525 accepted after review quality gates. Golden Asset Source Handoff must reject or leave pending review any issuer/provider payload for leveraged, inverse, active, fixed income, commodity, multi-asset, single-stock, option-income/buffer, ETN, ETV, CEF, crypto, international equity, or other unsupported exchange-traded products unless a future named scope expansion changes the product policy.

FMP, Finnhub, Tiingo, Alpha Vantage, EODHD, yfinance, and similar provider payloads are allowed fallback/enrichment for the personal MVP. They must stay server-side, preserve attribution/provenance, avoid unrestricted raw payload display/export, and not hide when official SEC or issuer evidence is unavailable. If licensing, caching rights, attribution, display rights, or export rights are unclear, prefer metadata, normalized facts, summaries, links, and clear provider labels over raw payload redistribution.

## Reviewed Issuer Handoff

Create or collect a draft without treating retrieval as approval, then inspect it with the repo-native manifest tool:

```bash
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py inspect \
  path/to/voo-source-handoff-draft.json \
  --strict
```

Review the draft, then add the required `text` and `retrieved_at` fields from the reviewed official source. Finalize the completed draft before worker use:

Completed drafts must also include `as_of_date`, `review_status=approved`, and `parser_validated=true`. The draft already carries suggested `storage_rights` and `export_rights` from the allowlist; operators must review those values before finalization.

```bash
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py finalize \
  path/to/completed-governed-source-draft.json \
  --output path/to/voo-reviewed-source-handoff.json \
  --finalized-at 2026-05-02T00:00:00Z
```

The finalized output is the worker-ingestable governed-source manifest. Draft manifests are rejected before the worker claims jobs.

## Explicit Issuer Fetch

When an operator intentionally chooses to fetch a reviewed issuer URL in strict/audit mode, keep the fetch outside default local and CI paths. The root repo currently records the reviewed result as a `source-handoff-manifest-v1` packet and validates it with the same inspect/finalize commands:

```bash
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py inspect \
  path/to/reviewed-issuer-source-handoff.json \
  --strict
```

The command emits a finalized governed-source manifest containing the fetched reviewed text. It still uses allowlist, SSRF, official-source, and full-text policy gates. The fetch is retrieval; the finalized governed manifest is the approval artifact consumed by ingestion.

## Explicit SEC Filing Fetch

When an operator has reviewed a CIK and wants recent SEC filing references in strict/audit mode, keep the SEC reference collection outside default local and CI paths. Record reviewed SEC metadata in a source-handoff packet and inspect it before finalization:

```bash
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py inspect \
  path/to/reviewed-sec-source-handoff.json \
  --strict
```

Review the emitted filing references, then use one selected reference with the explicit SEC fetch command. This command also stays outside default local, CI, Compose, and worker startup paths.

```bash
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py finalize \
  path/to/reviewed-sec-source-handoff.json \
  --output path/to/nvda-reviewed-sec-source-handoff.final.json
```

The command emits the same finalized governed-source manifest shape as the issuer fetch command. The fetch is retrieval; the finalized governed manifest is the approval artifact consumed by ingestion.

The SEC reference fields map directly into the reviewed filing fetch flags:

- `cik` -> `--cik`
- `accession_number` -> `--accession-number`
- `form` -> `--form`
- `filing_date` -> `--filing-date`
- `primary_document` -> `--primary-document`
- `source_url` -> `--url`
- `source_document_id` is generated again by the fetch command from the reference fields

## Multi-Source Manifests

The governed-text worker and one-shot ingestion helper can ingest more than one reviewed source for the same ticker in one job. This is the preferred local handoff shape when an operator has both a reviewed issuer source and a reviewed SEC filing for a supported asset.

For deterministic local validation, `app.services.golden_governed_fixtures.governed_manifest_from_fixture_catalog` converts the reviewed fixture catalog in `data/fixtures/source_documents/catalog.json` into a finalized governed manifest for `NVDA`, `AAPL`, `VOO`, `QQQ`, and `SOXX`. The worker smoke uses that manifest through governed-text mode so the golden set exercises the same handoff, queue, parsing, storage, and persistence contracts as operator-provided governed manifests without fetching live sources. This golden fixture proof is not ETF-500 coverage proof; ETF-500 readiness also requires reviewed issuer source packs and parser validation across the promoted supported ETF manifest.

Combine only finalized governed-source manifests. Do not combine dry-run drafts unless they have already passed through `finalize_governed_source_manifest`, and do not include secrets, hidden prompts, or restricted raw source text.

Every source in a finalized manifest must have an approved source-use policy. `full_text_allowed` sources may store raw text, parsed text, chunks, checksums, and private snapshots. `summary_allowed` sources may store metadata, links, checksums, and limited excerpts needed for summaries. `metadata_only` and `link_only` sources must not store full text. `rejected` sources must not feed generated output, citations, or exports.

MVP implementation should extend this shape so every source also carries explicit storage rights, export rights, parser status, freshness/as-of state, and review status. Until that schema exists, do not use finalized governed manifests for unreviewed provider payloads or hidden/internal endpoints.

Example combined manifest shape:

```json
{
  "schema_version": "1.0",
  "manifest_id": "nvda_reviewed_sec_and_issuer_sources",
  "review_note": "Operator-reviewed source handoff output; sources are not investment advice.",
  "sources": [
    {
      "source_document_id": "reviewed_nvda_10k_2025",
      "ticker": "NVDA",
      "title": "NVDA 10-K filing text",
      "url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm",
      "publisher": "SEC EDGAR",
      "source_type": "sec_filing",
      "source_use_policy": "full_text_allowed",
      "text": "Reviewed SEC filing text...",
      "retrieved_at": "2026-04-26T13:00:00Z",
      "as_of_date": "2025-03-01",
      "is_official": true,
      "storage_rights": "private_snapshot_allowed",
      "export_rights": "summary_or_excerpt_allowed",
      "review_status": "approved",
      "parser_validated": true
    },
    {
      "source_document_id": "reviewed_nvda_ir_profile",
      "ticker": "NVDA",
      "title": "NVDA investor relations source",
      "url": "https://investor.nvidia.com/",
      "publisher": "NVIDIA Investor Relations",
      "source_type": "company_investor_relations",
      "source_use_policy": "full_text_allowed",
      "text": "Reviewed issuer source text...",
      "retrieved_at": "2026-04-26T13:05:00Z",
      "as_of_date": "2026-04-26",
      "is_official": true,
      "storage_rights": "private_snapshot_allowed",
      "export_rights": "summary_or_excerpt_allowed",
      "review_status": "approved",
      "parser_validated": true
    }
  ]
}
```

Operational rules:

- One pending `governed_text_source_ingestion` job ingests all manifest sources for that ticker together.
- If one source parses and another fails, the job can complete as `partial` with `failed_source_document_ids`, `error_types`, and `failed_source_errors` diagnostics.
- A manifest can include multiple tickers, but operators should set `--job-count` high enough for the number of ticker jobs they intend to process.
- Reuse stable `source_document_id` values only for unchanged source text and URL. The helper rejects an existing ID with different content before claiming a job.
- Keep canonical source facts separate from Weekly News Focus event records; this manifest is for governed source documents and chunks, not recent-event synthesis.

## Strict Worker Execution

Strict governed-text worker execution is still deployment hardening for this repo. Before any worker-like run, inspect the finalized manifest:

```bash
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py inspect \
  path/to/finalized-governed-sources.json \
  --strict
```

Any future worker must claim only pending `governed_text_source_ingestion` jobs, select reviewed sources by ticker, persist source documents and chunks, and leave empty queues untouched.

Set `WORKER_EXTRACT_FACTS=true` with governed-text mode when the manifest contains source types supported by the deterministic fact extractor. Current deterministic coverage extracts stock facts from SEC-style sources and ETF facts from issuer-style sources, then exposes them through the persisted asset overview path. The worker smoke validates this for `NVDA` and `VOO` using the golden governed fixture manifest.

Before claiming jobs, inspect the finalized manifest:

```bash
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py inspect \
  path/to/finalized-governed-sources.json \
  --strict
```

The preflight command rejects drafts and invalid manifests, then reports manifest ID, ticker count, source count, source-type counts, source document IDs grouped by ticker, existing `source_document_id` content conflicts when `--check-existing` is set, and active governed-source jobs for manifest tickers when `--check-jobs` is set. It does not fetch network sources, create jobs, claim jobs, parse text, or write storage objects.

For a controlled one-shot local handoff, create or reuse pending jobs directly from a finalized manifest:

```bash
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
```

This deterministic rehearsal does not fetch network sources by default. It proves that strict source handoff gates, governed fixture evidence, generated-output cache records, source drawer/export surfaces, comparison/chat paths, and frontend smoke markers still work without approving new live sources.

Re-running the same finalized manifest with unchanged source text is safe: the helper creates or reuses a pending job, rewrites the same reviewed source snapshot, and upserts the same source document and chunks. Reusing an existing `source_document_id` with different text or URL is rejected before a job is claimed.

If a run processes no jobs, text output reports `statuses=none` and JSON output includes `empty_reason: no_pending_jobs_or_job_count_zero`. Check whether `--job-count` was set to `0` or whether there were no pending jobs for the requested job type.

## Credential-Gated GCS Smoke

Local and CI checks use mock storage or fake GCS uploaders. Run a real GCS smoke only from an operator shell or Cloud Run Job environment that already has permission to write to the private bucket. Do not put service-account JSON, access tokens, provider keys, or bucket credentials in manifests, docs, logs, or committed files.

Use a small finalized manifest with reviewed text that is safe to store under the rights-tiered raw source policy. Then run the one-shot helper with production-like storage settings:

```bash
LTT_REHEARSAL_DURABLE_REPOSITORIES_ENABLED=true \
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
```

Expected checks:

- The command exits successfully and reports `status` as `supported` or, for a mixed-quality manifest, `partial` with source-level diagnostics.
- The job diagnostics include `source_document_count` and `chunk_count` greater than zero for the processed ticker.
- The private bucket contains an object under `learn-the-ticker/smoke/live/sources/{TICKER}/{source_document_id}.txt`.
- The corresponding persisted source row has a `gs://` storage URI, parser diagnostics, checksum, and public source detail exposes only allowed metadata and excerpts.
- Re-running the same manifest is idempotent; changing text or URL for an existing `source_document_id` is rejected before a job is claimed.

Keep this smoke separate from default readiness checks until a deployed environment, private bucket, and IAM path are intentionally configured. The deterministic fake-uploader tests remain the CI guard for mock/GCS parity.

## Validation

Use these focused checks before relying on the handoff path:

```bash
TMPDIR=/tmp python3 -m pytest tests/unit/test_source_policy.py -q
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py inspect path/to/source-handoff-manifest.json --strict
TMPDIR=/tmp bash scripts/run_quality_gate.sh
```

The focused source-policy tests validate dry-run planning, draft creation, draft rejection, finalization, finalized-manifest loading, and source-use blocking without live network fetching.
