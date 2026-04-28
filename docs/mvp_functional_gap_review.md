# MVP Functional Gap Review

Task: 2026-04-27 v0.5 doc alignment and fresh-data MVP review.

Purpose: summarize current development progress, remove stale planning ambiguity, and define the next narrow implementation tasks needed before the project is locally functional as an MVP that can fetch fresh approved data and show it correctly in the frontend.

This is an operational planning artifact. It does not enable live providers, production deployment, production persistence, broad source coverage, recurring jobs, or generated advice.

## Current Progress

The repo is no longer planning-only. It is a deterministic, fixture-backed MVP scaffold with substantial backend and frontend behavior in place.

Completed capabilities:

- Next.js app under `apps/web` with single-asset home search, asset pages, comparison, source list, contextual glossary, asset chat, and export controls.
- FastAPI backend under `backend` with route contracts for search, overview, details, Weekly News Focus, comparison, chat, glossary, sources, exports, ingestion/pre-cache state, trust metrics, and runtime diagnostics.
- Golden Asset Source Handoff enforcement across source policy, source snapshots, knowledge packs, citations, generated-output cache metadata, source drawer output, and exports.
- Deterministic Top-500 candidate manifest workflow contracts using official IWB first and SPY/IVV/VOO fallback fixtures, SEC/Nasdaq validation, checksums, warnings, and diff reports.
- Mocked official-source acquisition execution for golden SEC stock, ETF issuer, and Weekly News paths.
- Deterministic local fresh-data ingest-to-render smoke coverage for a golden asset through backend routes and frontend contract markers.
- T-119 local API plumbing: frontend helpers prefer the configured backend base URL, Next can rewrite `/api/:path*`, and FastAPI CORS is wired from configured origins.
- Normal CI remains deterministic and does not require live provider, news, market-data, storage, database, or LLM calls.

## Current Misalignments

The v0.5 PRD/TDS add a stricter ETF policy:

- supported ETF runtime authority: `data/universes/us_equity_etfs_supported.current.json`
- ETF/ETP recognition authority: `data/universes/us_etp_recognition.current.json`

The implementation still uses the older combined ETF manifest:

- `data/universes/us_equity_etfs.current.json`
- `backend/etf_universe.py`
- search and tests that refer to a single combined eligible ETF universe

This is the highest-priority doc-to-code alignment gap. Until it is fixed, ETF support is operationally narrower than the v0.5 docs require and agents could accidentally treat recognition metadata as support metadata.

## MVP Fresh-Data Gaps

The project is not yet a fully functional fresh-data MVP. Remaining blockers:

1. Split ETF manifests are not implemented.
   The supported ETF manifest and recognition manifest do not exist yet. Runtime ETF support still reads the legacy combined manifest.

2. Local durable fresh-data smoke is not proven.
   T-118 proves deterministic in-memory/mocked ingest-to-render behavior. It does not prove a local durable Postgres/object-storage run.

3. Automated localhost browser E2E is missing.
   T-119 manual smoke confirmed chat, exports, comparison, asset page rendering, and CORS over local servers, but there is no repeatable optional browser/HTTP smoke script yet.

4. Real official-source fetchers are not the normal local path.
   Existing acquisition execution is mocked and golden-asset scoped. Real SEC/issuer/Weekly News retrieval must stay opt-in and must fail closed unless Golden Asset Source Handoff approves evidence use.

5. Real fresh-source-to-render flow is not complete.
   A real retrieved source still needs to pass fetcher, parser diagnostics, source handoff, private snapshot rules, normalized fact writes, Weekly News evidence writes, generated-output cache validation, backend route reads, and frontend rendering.

6. Launch coverage remains fixture-sized.
   The current stock manifest is a small fixture manifest, not a reviewed 500-name launch manifest. The supported ETF launch manifest is not yet materialized under the v0.5 split.

7. Production readiness remains later.
   Admin auth, rate limiting, production CORS review, private object storage, database migrations, Cloud Run service/job settings, monitoring, rollback, cost controls, and legal/compliance review remain open.

## Refined Agent Track

Current task state:

- T-119 is completed. The next task should start from the v0.5 ETF manifest split.

Runnable near-term backlog:

- T-120: implement v0.5 ETF manifest split contracts.
- T-121: add optional localhost browser/API E2E smoke.
- T-122: prove optional local durable repository smoke with API proxy/CORS enabled.
- T-123: promote real official-source fetchers behind handoff-gated local opt-in for golden assets.
- T-124: prepare reviewed launch-universe expansion plan for the Top-500 stock manifest and supported ETF launch pack.

Sequencing rationale:

- Do the ETF manifest split first so the new PRD/TDS policy is represented in runtime support classification before more smoke tests or real fetchers are added.
- Add browser E2E before local durable and real fetcher work so API proxy/CORS/chat/export/compare regressions are caught immediately.
- Prove local durable execution before real fetchers so fresh data has a safe local persistence path.
- Add real fetchers only after handoff, browser/API plumbing, and local persistence smoke are reliable.

## Non-Goals For The Next Tasks

The next agent-loop tasks must not add:

- live external calls in normal CI
- production credentials or secret inspection
- production object storage or database writes
- unreviewed manifest promotion
- generated output for unsupported or recognition-only ETF/ETP rows
- broad paid-provider or news-provider integrations
- production deployment hardening before local MVP behavior is stable

## Verification Baseline

For doc/control changes, run:

```bash
python3 -m pytest tests/unit/test_repo_contract.py tests/unit/test_safety_guardrails.py -q
npm test
bash scripts/run_quality_gate.sh
git diff --check
```

For ETF manifest split work, also run:

```bash
python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_provider_adapters.py -q
python3 evals/run_static_evals.py
```
