# Source Handoff Operator Guide

This guide documents the Golden Asset Source Handoff path for this repo. It is an operator workflow and implementation contract, not an automatic live-provider integration.

Golden Asset Source Handoff is the approval layer between retrieval and evidence use. API clients, SEC/issuer fetch commands, provider endpoints, and downloaded payloads are retrieval only. A fetched source is not approved evidence until the handoff confirms source identity, source type, official-source status, storage rights, export rights, source-use policy, rationale, parser validity, freshness/as-of metadata, and review status.

## Current Enforcement Status

Implemented in the current repo:

- source policy registry at `config/source_allowlist.yaml`;
- deterministic source-policy resolution and Golden Asset Source Handoff validation in `backend/source_policy.py`;
- repo-native governed-source manifest inspection and finalization smoke tooling at `scripts/inspect_source_handoff_manifest.py`;
- SEC stock, ETF issuer, and Weekly News acquisition boundaries under `backend/provider_adapters/` and `backend/repositories/weekly_news.py`;
- deterministic worker, source snapshot, knowledge-pack, Weekly News evidence, generated-output cache, source drawer, citation, and export contract tests;
- optional local browser and durable smoke paths that keep normal CI fixture-safe.

Still missing for MVP:

- governed source artifacts for the full golden set;
- proof that governed evidence, rather than fixture fallback, drives golden API responses and frontend rendering end to end;
- deployed or automated worker execution;
- local live-AI validation for grounded chat and AI Comprehensive Analysis when evidence thresholds are met.

## Safety Boundaries

- Keep local and CI defaults mock-safe.
- Do not put provider keys, service credentials, tokens, raw restricted text, hidden prompts, or model reasoning in manifests, logs, docs, or committed files.
- Use only approved or explicitly reviewed sources with compatible source-use policy.
- Treat source discovery output as a review artifact, not investment advice.
- Do not store or export restricted raw source text through public routes.
- Mark missing, unclear, hidden/internal, parser-invalid, unapproved, pending-review, or rejected sources as blocked from evidence use.
- Fetch only from governed sources, store according to source-use policy, generate only from approved evidence, and export only what policy permits.

## Machine-Readable Handoff Checklist

The following fields are explicit in source policy records and source evidence models:

- `source_identity`: stable URL, fixture ID, provider ID, or source document ID.
- `source_type`: approved source type such as `sec_filing`, `etf_fact_sheet`, `etf_holdings`, `company_investor_relations`, or `provider_metadata`.
- `is_official`: whether the source is official for the asset and claim role.
- `storage_rights`: whether the product may store metadata, links, limited excerpts, parsed text, or full text.
- `export_rights`: whether exports may include URL/metadata, allowed excerpts, summaries, or full text.
- `source_use_policy`: one of `metadata_only`, `link_only`, `summary_allowed`, `full_text_allowed`, or `rejected`.
- `approval_rationale`: why this source is appropriate for the claimed evidence role.
- `parser_status`: parser result plus failure diagnostics when parsing fails.
- `freshness`: as-of date, published date where applicable, retrieved timestamp, and stale/unknown/unavailable state.
- `review_status`: `approved`, `pending_review`, or `rejected`.

Only approved sources with compatible storage/export rights, non-rejected source-use policy, parser-valid evidence, and required freshness metadata may become evidence. Fetch commands and provider adapters may produce candidates, but evidence storage, citation support, generated-output cache use, source drawer output, and exports must validate handoff metadata first.

## Current Repo-Native Checks

Use the repo-native manifest smoke tool to inspect a reviewed governed-source packet:

```bash
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py inspect path/to/source-handoff.json
```

Use strict inspection when a packet is expected to be evidence-ready. Strict mode exits non-zero if any source is blocked from generated claim support, generated-output cache use, or Markdown/JSON section export:

```bash
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py inspect path/to/source-handoff.json --strict
```

Finalize only packets that pass strict handoff validation:

```bash
TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py finalize path/to/source-handoff.json --output path/to/source-handoff.finalized.json --finalized-at 2026-04-28T19:43:57Z
```

The manifest shape is intentionally small and repo-native:

```json
{
  "schema_version": "source-handoff-manifest-v1",
  "manifest_id": "aapl-governed-sources-2026-04",
  "manifest_status": "draft",
  "sources": [
    {
      "source_id": "sec-aapl-10k",
      "source_identity": "https://www.sec.gov/Archives/edgar/data/320193/example.htm",
      "source_type": "sec_filing",
      "is_official": true,
      "source_quality": "official",
      "allowlist_status": "allowed",
      "source_use_policy": "full_text_allowed",
      "permitted_operations": {
        "can_store_metadata": true,
        "can_store_raw_text": true,
        "can_display_metadata": true,
        "can_display_excerpt": true,
        "can_summarize": true,
        "can_cache": true,
        "can_export_metadata": true,
        "can_export_excerpt": true,
        "can_export_full_text": false,
        "can_support_generated_output": true,
        "can_support_citations": true,
        "can_support_canonical_facts": true,
        "can_support_recent_developments": true
      },
      "storage_rights": "raw_snapshot_allowed",
      "export_rights": "excerpts_allowed",
      "review_status": "approved",
      "approval_rationale": "Reviewed SEC filing source for canonical stock evidence.",
      "parser_status": "parsed",
      "freshness_state": "fresh",
      "as_of_date": "2026-04-01",
      "retrieved_at": "2026-04-25T00:00:00Z"
    }
  ]
}
```

Inspection covers draft, finalized, approved, pending-review, rejected, parser-invalid, missing-freshness, unclear-rights, and hidden/internal source cases. Finalization refuses any source that cannot pass Golden Asset Source Handoff for evidence, cache, and export use.

Use these existing deterministic commands to validate the current handoff layer:

```bash
TMPDIR=/tmp python3 -m pytest tests/unit/test_source_policy.py tests/unit/test_ingestion_worker.py tests/unit/test_repo_contract.py -q
TMPDIR=/tmp python3 -m pytest tests/unit/test_source_policy.py tests/unit/test_source_snapshot_repository.py tests/unit/test_knowledge_pack_repository.py tests/unit/test_cache_contracts.py tests/unit/test_exports.py -q
TMPDIR=/tmp python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_ingestion_worker.py tests/unit/test_weekly_news.py -q
TMPDIR=/tmp python3 -m pytest tests/integration/test_backend_api.py::test_t118_local_fresh_data_ingest_to_render_smoke_path_is_deterministic -q
```

Run the full deterministic gate before relying on a change:

```bash
TMPDIR=/tmp bash scripts/run_quality_gate.sh
```

These checks do not fetch live sources, create production jobs, write production storage, or call live models.

## Operator Workflow

For local implementation work:

1. Inspect reviewed governed-source packets with `scripts/inspect_source_handoff_manifest.py inspect`.
2. Use `--strict` before treating a packet as evidence-ready.
3. Finalize only packets that pass strict handoff validation.
4. Keep source discovery, source review, and source approval separate from evidence use.
5. Add or update source policy records only when domain/source identity, source type, official-source status, storage rights, export rights, source-use policy, rationale, validation tests, and development-log rationale move together.
6. Route approved evidence through existing repository boundaries before generated output, citations, source drawer records, cache entries, or exports can use it.
7. Keep canonical source facts separate from Weekly News Focus event records.

## Asset-Specific Handoff Notes

For stocks such as `AAPL` and `NVDA`, approved canonical evidence should come first from SEC EDGAR, SEC XBRL company facts, and SEC filing documents. Company investor-relations pages, earnings releases, and presentations can be official secondary sources for recent context and management explanations.

For ETFs such as `VOO`, `QQQ`, and `SOXX`, support has two gates. First, the ETF must be approved in `data/universes/us_equity_etfs_supported.current.json`; recognition-only rows in `data/universes/us_etp_recognition.current.json` can support blocked search states but cannot unlock generated output. Second, approved canonical evidence should come from issuer materials: official issuer page, fact sheet, prospectus, shareholder reports, holdings files, exposure files, and sponsor announcements.

Provider payloads are optional enrichment only. They must not override official SEC or issuer evidence. If licensing, caching rights, attribution, display rights, or export rights are unclear, provider payloads are limited to internal diagnostics, enrichment, or metadata-only use.

## When To Stop

Stop and do not use a source as evidence if any of these are true:

- source identity is missing or not governed;
- source type or official-source status is unclear;
- storage or export rights are unclear;
- source-use policy is rejected or incompatible with the intended action;
- parser status is failed or pending review;
- freshness/as-of metadata is missing;
- review status is not approved;
- source text is hidden/internal, unsafe to fetch, restricted beyond the intended use, or not same-asset evidence.
