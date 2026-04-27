# Local Fresh-Data Ingest-To-Render Runbook

Task: T-118

This runbook describes the local golden-asset smoke path before production deployment work. Normal CI uses deterministic fixtures, mocked official-source acquisition, and in-memory repositories. It must not require real SEC, issuer, market-data, broad news, storage, database, Redis, RSS, or LLM calls.

Fetching alone is retrieval, not evidence approval. A retrieved source can support snapshots, normalized facts, citations, generated-output cache records, exports, or rendered UI only after Golden Asset Source Handoff approves source identity, source type, official-source status, storage rights, export rights, source-use policy, parser status, freshness/as-of metadata, and review status.

## Local Modes

Use one of these local modes:

- `in_memory`: deterministic smoke mode. Uses injected in-memory ledgers and repositories. This is the CI-safe path.
- `local_durable`: optional operator-only local repository mode. Use placeholder-only local connection settings and never print credential values. This mode is for manual inspection only and is not required by CI.
- `operator_live_experiment`: optional local experiment mode. Keep it disabled by default. Any real retrieval must still pass source handoff before evidence use and must not be committed as fixtures or logs.

Suggested placeholder-only environment for local frontend/API rendering:

```bash
export LTT_LOCAL_REPOSITORY_MODE=in_memory
export LTT_LOCAL_SOURCE_MODE=mocked_official_sources
export API_BASE_URL=http://127.0.0.1:8000
export NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Do not add provider credentials, production storage paths, signed links, public bucket links, raw provider payloads, raw source text, hidden prompts, raw model reasoning, raw user text, or transcript text to environment examples, fixtures, logs, diagnostics, or committed files.

## Deterministic Smoke Path

1. Start from a clean worktree and install the normal local dependencies.
2. Create a manual pre-cache job for a golden asset such as `VOO` through the backend route:

```bash
curl -s -X POST http://127.0.0.1:8000/api/admin/pre-cache/VOO
```

3. Execute the local worker in deterministic mode with mocked official-source acquisition. The smoke test uses:
   - mocked issuer acquisition for the golden asset
   - parser diagnostics marked `parsed`
   - Golden Asset Source Handoff marked `approved`
   - private source snapshot metadata only
   - normalized knowledge-pack records from deterministic fixtures
   - Weekly News Focus evidence records from deterministic official-source candidates
   - generated-output cache records that already passed citation, source-use, freshness, and safety validation

4. Verify the job status:

```bash
curl -s http://127.0.0.1:8000/api/admin/pre-cache/jobs/pre-cache-launch-voo
```

Expected result: `job_state` is `succeeded`, generated output is available only for supported cached golden assets, and diagnostics remain compact and sanitized.

5. Verify backend route reads:

```bash
curl -s http://127.0.0.1:8000/api/assets/VOO/overview
curl -s http://127.0.0.1:8000/api/assets/VOO/weekly-news
curl -s http://127.0.0.1:8000/api/assets/VOO/sources
curl -s http://127.0.0.1:8000/api/assets/VOO/glossary?term=expense%20ratio
curl -s http://127.0.0.1:8000/api/assets/VOO/export?export_format=json
```

Expected result:

- overview, sources, glossary, and exports use validated persisted records before fixture fallback where that surface supports persisted reads
- citation chips and source drawer metadata expose approved source metadata and allowed excerpts only
- Weekly News Focus shows the evidence-backed item count and may show fewer than the configured maximum
- AI Comprehensive Analysis is suppressed below two high-signal Weekly News Focus items and available only when the threshold is met
- unsupported, out-of-scope, pending-ingestion, partial, stale, unknown, unavailable, pending-review, rejected-source, parser-invalid, wrong-asset, hidden/internal, unclear-rights, and insufficient-evidence states stay blocked or labeled according to section behavior

6. Verify frontend rendering with the API base configured:

```bash
npm run dev
```

Open `http://127.0.0.1:3000/assets/VOO`. The page should preserve Frontend Design and Workflow v0.4:

- home remains single stock/ETF search first
- comparison remains a separate connected `/compare` workflow
- glossary appears as contextual help
- source drawer, glossary, and chat remain mobile bottom-sheet or full-screen surfaces where appropriate
- stock-vs-ETF comparison keeps relationship badges and the single-company-vs-ETF-basket structure
- Weekly News Focus renders only the evidence-backed set

## Cleanup

For `in_memory`, stop the API and frontend processes. Records disappear with the process.

For optional `local_durable`, remove only local throwaway data created for the smoke run. Do not touch production databases, buckets, deployment resources, current Top-500 manifests, candidate manifests, or diff reports.

## Troubleshooting

- If an overview falls back to fixtures, check that both the persisted knowledge-pack reader and generated-output cache reader are configured.
- If generated-output cache reuse is rejected, check freshness hashes, same-asset citation bindings, source-use policy, parser status, and handoff metadata.
- If Weekly News Focus has fewer items than expected, treat that as valid when evidence is thin. Do not pad the section.
- If source drawer or export output is empty, verify that sources are allowlisted, parser-valid, same-asset, and excerpt-allowed.
- If frontend rendering uses local fallback, confirm `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` points to the local backend.

The deterministic regression for this runbook is `test_t118_local_fresh_data_ingest_to_render_smoke_path_is_deterministic` in `tests/integration/test_backend_api.py`.
