# Local Fresh-Data Ingest-To-Render Runbook

Task: T-118, updated by T-119 through T-130 local API, manifest, durable-smoke, v0.6 handoff alignment, and the local MVP rehearsal command

This runbook describes the local golden-asset smoke path before production deployment work. Normal CI uses deterministic fixtures, mocked official-source acquisition, and in-memory repositories. It must not require real SEC, issuer, market-data, broad news, storage, database, Redis, RSS, or LLM calls.

Fetching alone is retrieval, not evidence approval. A retrieved source can support snapshots, normalized facts, citations, generated-output cache records, exports, or rendered UI only after Golden Asset Source Handoff approves source identity, source type, official-source status, storage rights, export rights, source-use policy, parser status, freshness/as-of metadata, and review status.

ETF support note: T-120 implemented the split between supported ETF generated-output coverage and ETF/ETP recognition-only blocked states. Local smoke should verify supported ETF output comes from `data/universes/us_equity_etfs_supported.current.json` and recognition-only rows from `data/universes/us_etp_recognition.current.json` never unlock generated output.

## Local Modes

Use one of these local modes:

- `in_memory`: deterministic smoke mode. Uses injected in-memory ledgers and repositories. This is the CI-safe path.
- `local_durable`: optional operator-only local repository mode. Use placeholder-only local connection settings and never print credential values. This mode is for manual inspection only and is not required by CI.
- `operator_live_experiment`: optional local experiment mode. Keep it disabled by default. Any real retrieval or live-AI review must still pass source handoff, citation, source-use, freshness, and safety validation before evidence or generated output can be used. Do not commit fetched payloads, generated answers, logs, or diagnostics from this mode.

## One-Command MVP Rehearsal

Task: T-130.

Use the local rehearsal before production hardening work:

```bash
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
```

The default rehearsal is deterministic and fixture-backed. It checks:

- Golden Asset Source Handoff approval and blocked states before evidence use.
- governed golden API reads for overview, source drawer, exports, comparison, chat, Weekly News Focus, and AI Comprehensive Analysis threshold suppression.
- unsupported, out-of-scope, pending-ingestion, and unknown asset blocking.
- launch-manifest review packets without promotion or launch approval.
- v0.4 frontend smoke markers for single-asset home search, separate comparison, contextual glossary, mobile source/glossary/chat surfaces, stock-vs-ETF relationship structure, citation/source export scope, and evidence-limited Weekly News Focus.

The JSON output reports each check as `pass`, `skipped`, or `blocked`. Optional checks are skipped unless their rehearsal flag is set:

```bash
LTT_REHEARSAL_BROWSER_SERVICES_ENABLED=true \
LTT_REHEARSAL_DURABLE_REPOSITORIES_ENABLED=true \
LTT_REHEARSAL_OFFICIAL_SOURCE_RETRIEVAL_ENABLED=true \
LTT_REHEARSAL_LIVE_AI_REVIEW_ENABLED=true \
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
```

Optional-mode meanings:

- browser services: checks already-running localhost web/API services and local CORS/proxy behavior.
- durable repositories: checks local durable repository prerequisites and reports sanitized blockers when the local DSN or private object namespace is missing or unsafe.
- official-source retrieval: checks live acquisition readiness flags only; it does not execute retrieval or approve sources.
- live-AI review: delegates to the operator-only live-AI validation smoke and reports sanitized pass or blocker states.

Stop when any required deterministic check is `blocked`, or when an opted-in optional check is `blocked`. The rehearsal does not start production services, approve sources, promote manifests, write production storage, require live calls by default, or make fixture-sized/local-only data launch-approved.

## Local Live-AI Validation Smoke

Task: T-127.

The local live-AI validation smoke is operator-only and disabled by default. It validates one supported golden grounded-chat case and one AI Comprehensive Analysis case where two high-signal Weekly News Focus items are available. It does not approve sources, does not relax Golden Asset Source Handoff, does not write generated-output cache records, and does not print raw user text, prompts, source text, model reasoning, transcripts, generated live responses, or secret values.

Prerequisites:

- a server-side live provider key is already present in the operator shell
- local opt-in is intentional for this shell only
- live generation is explicitly enabled for this one command
- source evidence remains fixture-safe or already handoff-approved

Command:

```bash
LTT_LIVE_AI_SMOKE_ENABLED=true \
LLM_PROVIDER=<server-side-live-provider> \
LLM_LIVE_GENERATION_ENABLED=true \
TMPDIR=/tmp python3 scripts/run_live_ai_validation_smoke.py --json
```

Expected results:

- without `LTT_LIVE_AI_SMOKE_ENABLED=true`, both smoke cases report `skipped`
- without live-generation readiness or a server-side key, both smoke cases report `blocked`
- with readiness and valid output, cases report `pass`
- failed schema, citation, source-use, freshness, safety, evidence-threshold, or cache-eligibility checks report `blocked`

Stop conditions:

- any blocked validation result
- fewer than two high-signal Weekly News Focus items for the AI Comprehensive Analysis case
- any diagnostic or log path that would expose raw user text, prompts, source text, generated live responses, model reasoning, transcripts, unrestricted provider payloads, or secret values
- any attempt to treat local live-AI review as source approval or a Golden Asset Source Handoff override

Suggested placeholder-only environment for local frontend/API rendering:

```bash
export LTT_LOCAL_REPOSITORY_MODE=in_memory
export LTT_LOCAL_SOURCE_MODE=mocked_official_sources
export API_BASE_URL=http://127.0.0.1:8000
export NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
export CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

For optional T-122 local-durable smoke, run with the same API/base wiring and these prerequisite flags:

```bash
export DATABASE_URL=<local durable repository DSN, placeholder-only>
export LOCAL_DURABLE_REPOSITORIES_ENABLED=true
export LOCAL_DURABLE_OBJECT_NAMESPACE=ticker-smoke
export LEARN_TICKER_LOCAL_DURABLE_SMOKE=1
export LEARN_TICKER_LOCAL_BROWSER_SMOKE=1
export LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000
export LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000
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

6. Verify local frontend/API plumbing.

T-119 established two valid local strategies:

- browser helpers prefer `NEXT_PUBLIC_API_BASE_URL` and call FastAPI directly, with FastAPI CORS allowing the local web origins
- the Next app also rewrites `/api/:path*` to the configured FastAPI backend, so relative chat/export links do not hit missing Next API routes during local development

Start the API with the placeholder CORS origins and start the web app with the API base configured:

```bash
npm --workspace apps/web run dev -- --hostname 127.0.0.1 --port 3000
```

Then verify the prior frontend 404 blockers:

```bash
curl -s -X POST http://127.0.0.1:3000/api/assets/VOO/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"What does this fund hold?"}'
curl -s http://127.0.0.1:3000/api/assets/VOO/export?export_format=markdown
curl -s -X POST http://127.0.0.1:3000/api/compare \
  -H 'Content-Type: application/json' \
  -d '{"left_ticker":"VOO","right_ticker":"QQQ"}'
curl -s -D - -o /dev/null http://127.0.0.1:8000/api/search?q=VOO \
  -H 'Origin: http://127.0.0.1:3000'
```

Expected result: chat, export, and compare return backend payloads instead of Next 404s, and the Origin request includes an `Access-Control-Allow-Origin` header for the configured local origin.

7. Optional local-durable smoke (T-122): run the browser smoke with durable prereqs set.

```bash
LEARN_TICKER_LOCAL_BROWSER_SMOKE=1 \
LEARN_TICKER_LOCAL_DURABLE_SMOKE=1 \
LEARN_TICKER_LOCAL_WEB_BASE=http://127.0.0.1:3000 \
LEARN_TICKER_LOCAL_API_BASE=http://127.0.0.1:8000 \
npm run test:browser-smoke
```

When durable prereqs are present, this optional run validates:

- VOO asset render through API-backed pages
- `/api/assets/VOO/chat`
- `/api/assets/VOO/export`
- `/api/assets/VOO/sources/export`
- `/assets/VOO/sources`
- `/compare?left=VOO&right=QQQ`
- `/api/compare/export`
- CORS behavior from `/api/search?q=VOO` using the local web origin
- out-of-scope/unknown search blocking behavior under API proxy

If any durable prerequisites are missing, the smoke should print blockers and report that durable smoke is skipped.

8. Verify frontend rendering with the API base configured:

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

- If an overview falls back to fixtures, check that persisted knowledge-pack, generated-output cache, and source snapshot readers are configured for the governed path.
- If generated-output cache reuse is rejected, check freshness hashes, same-asset citation bindings, source-use policy, parser status, private source snapshot artifacts, and handoff metadata.
- If Weekly News Focus has fewer items than expected, treat that as valid when evidence is thin. Do not pad the section.
- If source drawer or export output is empty, verify that sources are allowlisted, parser-valid, same-asset, and excerpt-allowed.
- If frontend rendering uses local fallback, confirm `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` points to the local backend.
- If chat or export links return frontend 404s, confirm the web dev server was started after setting `NEXT_PUBLIC_API_BASE_URL` or that the Next `/api/:path*` rewrite can reach the local FastAPI backend.
- If browser direct API calls fail, confirm `CORS_ALLOWED_ORIGINS` includes the exact local web origin, including hostname and port.

The deterministic regression for this runbook is `test_t118_local_fresh_data_ingest_to_render_smoke_path_is_deterministic` in `tests/integration/test_backend_api.py`. T-119 added static coverage for the frontend API helper, Next rewrite, and CORS settings. T-121/T-122 added optional localhost browser and durable smoke paths. T-125 keeps this runbook aligned with the v0.6 handoff docs. T-127 covers operator-only live-AI validation smoke, and T-128 proves deterministic governed golden source snapshots, knowledge-pack records, and generated-output cache records can drive API and frontend-rendering markers without approving new sources or adding live calls.
