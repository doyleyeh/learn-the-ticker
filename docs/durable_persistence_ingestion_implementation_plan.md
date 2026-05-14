# Durable Persistence, Ingestion, And Trust-State Implementation Plan

Date: 2026-05-13

Purpose: turn the current contract-first, deterministic, fixture-backed persistence and ingestion scaffold into an authoritative durable MVP path while making frontend fallback states visible enough that users can distinguish fresh backend evidence, stale cache, partial evidence, fixture fallback, timeout, and valid empty evidence.

This plan does not approve public launch, enable recurring production jobs, add broad paid providers, weaken Golden Asset Source Handoff, expose admin routes, or make live provider/LLM calls part of normal CI.

## Current Gap

The current implementation already has many boundaries:

- persistence settings, repository contracts, generated-output cache contracts, source snapshot metadata, and local durable smoke paths;
- deterministic ingestion ledger and worker execution contracts;
- backend routes that can read from configured repositories while preserving fixture fallback;
- frontend asset pages that can use backend overview/details/timely/source/glossary contracts.

The missing product behavior is that these are not yet the normal authoritative path. `backend/persistence.py` still describes persistence as a dormant metadata boundary, and `backend/ingestion.py` still describes launch pre-cache as a deterministic contract that creates no workers, queues, provider calls, source facts, citations, or generated outputs.

The related frontend trust gap is that `apps/web/app/assets/[ticker]/page.tsx` can swallow details, Economic Indicators, Market News Focus, Weekly News Focus, source drawer, and glossary fetch failures. Those failures currently become local/default content with mostly internal data attributes. A timeout, missing API base URL, backend 500, invalid contract, and valid empty Weekly News state can look too similar.

## Implementation Principles

- Keep normal CI deterministic and fixture-backed unless a task explicitly opts into local operator-only checks.
- Preserve manifest-owned support classification for top-500 stocks and supported ETF generated-output coverage.
- Treat every fetch as retrieval only. Evidence promotion still requires Golden Asset Source Handoff or the explicitly labeled lightweight personal-MVP rules.
- Store raw source text only when source-use policy and storage rights permit it.
- Prefer Postgres `ingestion_jobs` as the first production queue. Add Redis or a dedicated queue only after manual jobs prove inadequate.
- Prefer visible partial, stale, unknown, unavailable, backend-timeout, backend-error, fixture-fallback, and valid-empty states over complete-looking pages with hidden fallbacks.
- Route production-like reads through durable packs and generated-output cache only after validation, citation, source-use, freshness, and safety gates pass.
- Keep admin/import/worker endpoints disabled or private until auth and rate limits are implemented.

## Phase 1: Make Frontend Section State Honest

Goal: stop backend section failures from masquerading as normal evidence-limited content.

Concrete changes:

- Replace `Promise.all(...catch(() => null))` section loading on asset pages with typed section load results.
- Distinguish at least:
  - `backend_live_loaded`
  - `backend_not_configured`
  - `backend_timeout`
  - `backend_error`
  - `backend_invalid_contract`
  - `stale_cached_data`
  - `local_fixture_fallback`
  - `valid_empty_evidence`
  - `partial_backend_page`
- Add user-facing `PartialDataNotice` or section-level status copy for timed-out, errored, stale, and fixture-fallback sections.
- Keep valid empty Weekly News Focus copy distinct from backend failure copy.
- Keep existing internal data attributes, but make the visible state the source of truth for trust.
- Make section fetch timeout configurable and long enough that a slow but valid local backend is not treated the same as missing data.

Acceptance gates:

- A backend timeout in Weekly News Focus renders a visible backend-timeout or retryable section state, not "No major Weekly News Focus items found."
- A valid empty Weekly News response still renders the normal evidence-limited empty state.
- Details failure can produce a partial-page notice instead of silently continuing as a complete local fixture page.
- Frontend smoke covers no API base, timeout, backend error, invalid contract, local fixture fallback, and valid empty evidence.

## Phase 2: Execute Durable Storage Migrations And Repository Smoke

Goal: move from repository contracts to a verified durable schema and storage execution path.

Concrete changes:

- Add/verify migrations for authoritative MVP tables and repository records:
  - `assets`
  - `source_documents`
  - `facts`
  - `holdings`
  - `exposures`
  - `financial_metrics`
  - `recent_events`
  - `summaries`
  - `claims`
  - `claim_citations`
  - `ingestion_jobs`
  - generated-output cache records
  - analysis-pack import history
  - rollback/import ledger
- Add a deterministic migration smoke that can run against a temporary local database or the existing local durable test boundary without secrets.
- Add the local `durable_repository_records` adapter as the first restart-proof repository-record smoke path for validated source snapshot, knowledge-pack, Weekly News, generated-output cache, and ingestion ledger records.
- Add object-artifact storage abstractions for private `raw/`, `parsed/`, `generated/`, and `diagnostics/` key families.
- Enforce object namespace validation: no public URLs, signed URLs, browser-readable paths, or credential-bearing links in source drawer, exports, generated-output cache, logs, or diagnostics.

Acceptance gates:

- Migrations can be applied and rolled back in a local throwaway environment.
- Repository reads/writes survive process restart in local durable mode.
- CI remains deterministic when no durable settings are configured.
- Placeholder env files contain no secrets and no browser-exposed database/storage settings.

## Phase 3: Enforce Source Snapshot And Handoff Promotion Gates

Goal: make source handoff records the promotion gate between retrieval and evidence use.

Concrete changes:

- Persist source snapshot metadata for every retrieved document or provider record before evidence use.
- For each source, persist handoff fields:
  - domain/source identity
  - source type
  - official-source status
  - storage rights
  - export rights
  - source-use policy
  - parser status
  - freshness/as-of metadata
  - review status
  - approval rationale or rejection reason
- Default missing, unclear, parser-invalid, hidden/internal, unreviewed, or rights-disallowed records to closed states.
- Block unapproved sources from generated-output cache writes, citation support, exports, source drawer supporting excerpts, and strict/audit-quality knowledge packs.
- Implemented in the durable trust-state slice: strict generated evidence, generated-output cache, citation validation, allowed excerpt export, markdown/JSON section export, source snapshots, and knowledge-pack records share the same handoff validator, while local lightweight metadata remains cache-ineligible display evidence.
- Preserve lightweight personal-MVP fallback labels where allowed by `docs/LIGHTWEIGHT_DATA_POLICY.md`.

Acceptance gates:

- A pending-review source can be retrieved but cannot become strict generated evidence, cache, export, or citation support.
- Metadata-only and link-only sources cannot store raw body text or unrestricted article excerpts.
- Source drawer and exports expose only approved metadata and allowed excerpts.
- Same-asset and same-comparison-pack citation checks still pass.

## Phase 4: Turn Pre-Cache Into A Manual Postgres-Ledger Worker Pipeline

Goal: make pre-cache and on-demand ingestion real manual jobs without introducing an always-on production queue.

Concrete changes:

- Use `ingestion_jobs` as the first queue/ledger with statuses such as `queued`, `running`, `succeeded`, `failed`, `cancelled`, `unsupported`, `out_of_scope`, `unknown`, `unavailable`, `partial`, and `stale`.
- Add safe job claiming with retry/lease metadata so manual Cloud Run Jobs can execute idempotently.
- Execute worker steps in order:
  - classify asset from manifests/recognition data;
  - fetch official sources first;
  - run provider/news fallback only when configured and source-use-safe;
  - persist snapshot metadata and allowed private artifacts;
  - run source handoff;
  - parse and normalize facts;
  - build knowledge packs;
  - select Weekly News Focus items;
  - generate or invalidate summaries only after evidence gates;
  - write generated-output cache records;
  - append import/rollback history.
- Keep unsupported and out-of-scope assets blocked from generated pages, chat, comparison, Weekly News Focus, AI Comprehensive Analysis, exports, and cache entries.

Acceptance gates:

- A launch pre-cache request creates durable jobs rather than only deterministic status fixtures when durable mode is explicitly enabled.
- The worker can resume safely after a failed or interrupted job.
- Job diagnostics are sanitized and never include secrets, raw provider payloads, unrestricted source text, hidden prompts, raw model reasoning, or transcripts.
- Normal CI uses mocked repositories and provider fixtures only.

## Phase 5: Make Durable Packs And Generated-Output Cache Authoritative For Routes

Goal: make runtime reads prefer valid durable data while keeping explicit deterministic fallback for tests and local no-backend mode.

Concrete changes:

- Backend route responses should include section-level origin and state metadata:
  - `data_origin`
  - `section_status`
  - `fallback_reason`
  - `freshness_state`
  - `source_handoff_state`
  - `cache_state`
  - `evidence_state`
- Routes should read in this priority order:
  1. valid generated-output cache tied to current evidence hash;
  2. valid durable knowledge pack/facts/events;
  3. lightweight local fetch output where enabled and labeled;
  4. deterministic fixture fallback only when configured for tests/local development.
- Invalidate generated outputs when facts, source checksums, Weekly News event IDs, prompt version, schema version, model, or citation validation state changes.
- Return explicit partial/unavailable states when durable reads are missing or invalid.

Acceptance gates:

- A route can prove whether data came from durable evidence, stale cache, lightweight fallback, or deterministic fixtures.
- Generated-output cache entries cannot be served after source-use, citation, freshness, schema, or safety validation fails.
- Chat, comparison, source drawer, exports, and glossary read the same durable pack state as the asset page.
- Frontend trust-state rendering consumes backend state metadata instead of guessing from `null`.

## Phase 6: Production Controls Before Exposure

Goal: make the durable pipeline safe enough for a controlled deployment.

Concrete changes:

- Add admin auth and rate limits before exposing ingestion, import, pre-cache, or rollback endpoints.
- Keep `ADMIN_ROUTES_ENABLED=false` as the safe deployment default until those controls pass.
- Add Cloud Run Job runbooks for manual jobs, retries, rollback, and incident response.
- Add monitoring for source retrieval failures, source handoff rejection rates, generated-output validation failures, stale pages, backend section timeouts, and cache invalidation.
- Add budget/rate-limit controls outside code for OpenRouter and provider keys.

Acceptance gates:

- Admin and worker endpoints fail closed without credentials.
- Rate limits run before provider, retrieval, ingestion, or LLM work.
- Rollback procedures cover migrations, source snapshots, generated-output cache, imports, API, worker, and frontend revisions.
- Legal/compliance review remains a pre-public-launch gate.

## Recommended Task Sequence

1. Surface asset-page backend section state and fallback notices.
2. Add durable schema execution smoke and restart-proof repository checks.
3. Enforce source snapshot/handoff promotion gates for durable evidence writes.
4. Convert launch pre-cache to durable job creation plus manual worker execution.
5. Route asset, chat, comparison, source drawer, export, and glossary reads through durable state metadata.
6. Add admin auth, rate limits, deployment runbooks, monitoring, and rollback controls.

The first five tasks are prepared in `TASKS.md` so the agent loop can make progress without jumping straight to broad production deployment.

## Required Verification By Task Type

Frontend trust-state tasks:

```bash
npm test
npm run typecheck
npm run build
bash scripts/run_quality_gate.sh
```

Backend persistence, ingestion, source-use, cache, and route tasks:

```bash
TMPDIR=/tmp python3 -m pytest tests -q
TMPDIR=/tmp python3 evals/run_static_evals.py
TMPDIR=/tmp bash scripts/run_quality_gate.sh
```

Deployment/control-doc tasks:

```bash
git diff --check
TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py tests/unit/test_safety_guardrails.py -q
TMPDIR=/tmp python3 evals/run_static_evals.py
TMPDIR=/tmp bash scripts/run_quality_gate.sh
```

Optional operator-only checks should stay explicitly gated and report `skipped` when not enabled.

## Non-Goals

- No live provider, market-data, news, database, object-storage, queue, browser, or LLM dependency in normal CI.
- No source approval by fetching alone.
- No generated output for unsupported, out-of-scope, recognition-only, pending-review, or source-policy-blocked assets.
- No public admin/worker/import endpoints before auth and rate limits.
- No recurring scheduler until manual jobs are reliable.
- No broad paid-provider expansion before licensing, caching, attribution, display, and export rights are reviewed.
