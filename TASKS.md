## Current task

### T-080: Add deterministic ingestion worker execution contract

Goal:
Add a deterministic ingestion worker execution contract that consumes T-079 ingestion job ledger records through injected in-memory boundaries, runs fixture-only job transitions, and preserves existing API, retrieval, generation, chat, comparison, export, glossary, frontend, provider, and fixture behavior without live providers, live database execution, schedulers, or production worker wiring.

Task-scope paragraph:
This task should add only the local execution contract needed between the persisted ingestion job ledger and future source snapshot/provider work. The worker may serialize existing deterministic ingestion and pre-cache responses into ledger records, transition injected jobs through fixture-backed execution states, and return compact execution results for tests. It must not execute migrations, open database sessions, fetch SEC/issuer/market/news data, write object-storage snapshots, generate summaries, change public API route behavior, or add recurring/scheduled production behavior.

Allowed files:

- `backend/ingestion.py`
- `backend/ingestion_worker.py`
- `backend/ingestion_job_repository.py`
- `backend/repositories/ingestion_jobs.py`
- `backend/repositories/__init__.py`
- `backend/models.py`
- `tests/unit/test_ingestion_worker.py`
- `tests/unit/test_ingestion_jobs.py`
- `tests/unit/test_ingestion_job_repository.py`
- `docs/agent-journal/*.md`

Do not change:

- No frontend files under `apps/web`.
- No FastAPI route behavior, public endpoint schemas, export behavior, chat behavior, comparison behavior, glossary behavior, generated content, or retrieval behavior.
- No Alembic migration files or new persistence tables unless a focused import-only metadata change is strictly required for the worker contract; prefer no migration change.
- No live database connection, ORM session execution, source snapshot write, object-storage call, SEC/issuer/market/news provider call, LLM call, Cloud Run Job wiring, scheduler, admin auth, rate limiting, or deployment configuration.
- No source allowlist/source-use expansion, provider licensing change, production dependency addition, or environment/secret file change.

Acceptance criteria:

- Add a pure-Python deterministic ingestion worker boundary that can execute injected `IngestionJobLedgerRecords` or equivalent T-079 ledger-backed rows without opening a database connection or calling live external services.
- The worker supports manual pre-cache and approved on-demand ingestion categories and preserves the T-079 ledger categories and states for future refresh and source-revalidation work without implementing recurring jobs.
- Pending approved jobs can transition through `pending` to `running` and then to deterministic terminal results such as `succeeded`, `failed`, `unsupported`, `out_of_scope`, `unknown`, `unavailable`, or `stale` using fixture-only inputs.
- Unsupported, out-of-scope, unknown, unavailable, unapproved `pending_ingestion`, failed-validation, and source-policy-blocked jobs remain blocked from generated pages, generated chat answers, generated comparisons, generated risk summaries, and generated-output cacheability.
- Supported cached assets and approved pending-ingestion assets preserve existing capability semantics from `backend/ingestion.py`; existing request/status functions keep their current deterministic outputs unless tests expose an import-path-only adjustment.
- The worker contract preserves safety, citation, source-use, and freshness guardrails: no investment advice, no unsupported factual claims, no live external calls in normal CI, and explicit unknown/stale/unavailable/partial handling where evidence is missing.
- Execution diagnostics store only compact state-transition metadata, sanitized error categories, retryability, timestamps, job IDs, source-policy references, and checksums where available.
- Diagnostics must not store or expose secrets, raw provider payloads, raw article text, unrestricted source text, raw user text, hidden prompts, raw model reasoning, or unrestricted source excerpts.
- The worker is idempotent for already terminal ledger records and retry-safe for retryable deterministic failures; repeated execution must not invent new facts or produce different generated-output availability.
- Stale and unavailable states are explicit and preserve freshness/unknown/unavailable/partial language rather than converting missing evidence into success.
- Tests cover state transitions, manual pre-cache jobs, approved on-demand jobs, unsupported/out-of-scope blocking, unknown/unavailable/stale handling, idempotent terminal execution, retryable failure behavior, sanitized diagnostics, no-generated-output blocked states, and import-time no-live-call/no-database behavior.
- Current API, retrieval, generation, chat, comparison, export, glossary, frontend, provider, source-use policy, fixture, and quality-gate behavior remains unchanged outside the dormant worker contract.

Required commands:

```bash
python3 -m pytest tests/unit/test_ingestion_worker.py tests/unit/test_ingestion_job_repository.py tests/unit/test_ingestion_jobs.py -q
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
docker compose config
```

Iteration budget:
One agent-loop cycle. If the worker contract reveals a need for source snapshot persistence, SEC or ETF adapters, production database readers/writers, scheduler behavior, admin route wiring, generated-output caching, or broader public API changes, stop after the deterministic worker boundary and record the follow-up under Backlog instead of expanding scope.


## Completed

### T-079: Add persisted ingestion job ledger contracts

Goal:
Add the first persisted ingestion job ledger contract on top of the dormant persistence boundary so future manual pre-cache and on-demand ingestion work can track deterministic job states without routing current API, retrieval, generation, chat, comparison, export, or frontend behavior through a live database.

Completed details:

- Implementation commit `b3881fa feat(T-079): add persisted ingestion job ledger contracts` updated `backend/repositories/ingestion_jobs.py`, `backend/ingestion_job_repository.py`, `backend/repositories/__init__.py`, `alembic/versions/20260425_0003_ingestion_job_ledger_contracts.py`, `tests/unit/test_ingestion_job_repository.py`, and `docs/agent-journal/20260425T050556Z.md`.
- Merged branch `agent/T-079-20260425T050556Z` into `main` with local merge commit `398aee5 chore(T-079): merge persisted ingestion job ledger contracts`.
- `backend/repositories/ingestion_jobs.py` added a dormant pure-Python ingestion job ledger repository contract with explicit table metadata, row models, deterministic job categories, required ledger states, MVP scope classification, compact sanitized diagnostics, source-policy references, checksum references, and generated-output blocking for unsupported, out-of-scope, unknown, unavailable, and unapproved pending-ingestion jobs.
- `backend/ingestion_job_repository.py` re-exports the ingestion job ledger boundary, tables, category/state models, record models, contract error, repository, metadata helper, scope classifier, serializer, and validator for future ingestion worker integration.
- `backend/repositories/__init__.py` exposes the ingestion job ledger repository contract alongside existing dormant repository contracts.
- The Alembic revision `20260425_0003_ingestion_job_ledger_contracts.py` is import-only and limited to ingestion ledger contract tables; the journal records that it was not executed against a database.
- `tests/unit/test_ingestion_job_repository.py` covers metadata, supported categories and states, migration importability, MVP scope classification, approved pending-ingestion serialization, manual pre-cache blocked assets, unsupported/out-of-scope/unknown/unavailable generated-output blocking, sanitized diagnostics, source-reference storage boundaries, validation errors, repository import behavior, and fixture preservation.
- The journal records that the task did not add live database connections, production database readers/writers, executed migrations, worker loops, schedulers, provider calls, route wiring, frontend behavior, generated-output cache persistence, source snapshot persistence, chat persistence, or export behavior.
- `docs/agent-journal/20260425T050556Z.md` records these checks: `python3 -m pytest tests/unit/test_ingestion_job_repository.py tests/unit/test_ingestion_jobs.py -q` passed with 24 tests; `python3 -m pytest tests/unit/test_ingestion_job_repository.py -q` passed with 12 tests; `python3 -m pytest tests/unit/test_repo_contract.py tests/unit/test_persistence_settings.py -q` passed with 20 tests; `python3 -m pytest tests/unit/test_ingestion_jobs.py -q` passed with 12 tests; `python3 -m pytest tests -q` passed with 237 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `docker compose config` passed.
- Remaining risks from the journal:
  - The ledger contract is intentionally dormant and in-memory/unit-tested only; no production database reader/writer, executed migration, worker execution path, scheduler, admin auth, or route integration exists yet.
  - Scope validation uses the current deterministic fixture and Top-500 manifest boundary; future live ingestion adapters still need their own source snapshot, policy, and worker execution contracts.
  - The migration is importable and inspectable, but it was not executed against a database in this task.

Completion commits:

- `b3881fa feat(T-079): add persisted ingestion job ledger contracts`
- `398aee5 chore(T-079): merge persisted ingestion job ledger contracts`

### T-078: Route retrieval through persisted packs with fixture fallback

Goal:
Route the asset knowledge-pack build-result retrieval path through an injectable persisted-pack read boundary first, with deterministic fixture fallback preserved as the default behavior and no live database dependency in normal local or CI runs.

Completed details:

- Implementation commit `6cfd5da feat(T-078): route retrieval through persisted packs with fixture fallback` updated `backend/retrieval_repository.py`, `backend/retrieval.py`, `backend/repositories/knowledge_packs.py`, `backend/repositories/__init__.py`, `tests/unit/test_retrieval_repository.py`, and `docs/agent-journal/20260425T042223Z.md`.
- Merged branch `agent/T-078-20260425T042223Z` into `main` with local merge commit `19f5169 chore(T-078): merge route retrieval through persisted packs with fixture fallback`.
- `backend/retrieval_repository.py` added a pure-Python retrieval read boundary for injected persisted `KnowledgePackRepositoryRecords`, including `KnowledgePackRecordReader`, `RetrievalRepositoryReadResult`, `RETRIEVAL_REPOSITORY_BOUNDARY`, and `read_persisted_knowledge_pack_response`.
- `build_asset_knowledge_pack_result(ticker)` remains backward compatible and fixture-backed by default; callers may opt into the persisted-first path with an injected `persisted_reader`.
- Persisted records are deserialized through the T-077 `AssetKnowledgePackRepository` contract before use, and repository misses, unconfigured readers, reader failures, invalid reader shapes, wrong-ticker records, wrong-asset source bindings, and source-use contract violations do not replace deterministic fixture output.
- `backend/repositories/knowledge_packs.py` now preserves repository row order during deserialization and restores persisted `permitted_operations` into `SourceKnowledgePackMetadata` so persisted metadata reconstructs the fixture-backed response shape more closely.
- `backend/repositories/__init__.py` re-exports the retrieval repository boundary and read helper.
- `tests/unit/test_retrieval_repository.py` covers persisted-first retrieval for `VOO`, fixture fallback for missing/empty/failing readers, non-generated metadata-only states for `SPY`, `TQQQ`, and `ZZZZ`, rejected source-use and wrong-asset persisted records, reader ticker mismatch, lazy no-database/no-live-provider imports, invalid reader shapes, and visible deserialization contract errors.
- The journal records that the task did not add FastAPI route wiring, a live database connection, migrations, frontend behavior, generated content, source-use policy changes, provider calls, or secret-handling changes.
- `docs/agent-journal/20260425T042223Z.md` records these checks: `python3 -m pytest tests/unit/test_retrieval_repository.py tests/unit/test_knowledge_pack_repository.py tests/unit/test_retrieval_fixtures.py tests/integration/test_backend_api.py -q` passed with 59 tests; `python3 -m pytest tests -q` passed with 225 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `docker compose config` passed.
- Remaining risks from the journal:
  - The persisted read path is intentionally injectable only; no production database reader, route wiring, or live persistence execution path was added.
  - Persisted responses reconstruct metadata-only `KnowledgePackBuildResponse` records; `cache_revalidation` is still not stored by the T-077 repository contract.

Completion commits:

- `6cfd5da feat(T-078): route retrieval through persisted packs with fixture fallback`
- `19f5169 chore(T-078): merge route retrieval through persisted packs with fixture fallback`

### T-077: Add persisted knowledge-pack repository contracts

Goal:
Add the first persisted asset knowledge-pack repository contract on top of the dormant persistence boundary, without routing any current API, retrieval, generation, chat, comparison, export, or fixture behavior through a live database.

Completed details:

- Implementation commit `141b3c4 feat(T-077): add persisted knowledge-pack repository contracts` updated `backend/repositories/knowledge_packs.py`, `backend/knowledge_pack_repository.py`, `backend/repositories/__init__.py`, `alembic/versions/20260425_0002_knowledge_pack_repository_contracts.py`, `tests/unit/test_knowledge_pack_repository.py`, and `docs/agent-journal/20260425T040950Z.md`.
- Merged branch `agent/T-077-20260425T040950Z` into `main` with local merge commit `80a318b chore(T-077): merge persisted knowledge-pack repository contracts`.
- `backend/repositories/knowledge_packs.py` added a dormant pure-Python asset knowledge-pack repository contract with explicit table definitions and row models for pack envelopes, source documents, source chunks or excerpts, normalized facts, recent developments, evidence gaps, section freshness inputs, and source checksum metadata.
- Serialization/deserialization helpers preserve supported fixture-backed `KnowledgePackBuildResponse` metadata and optional retrieval fixture details without routing runtime API, retrieval, generation, chat, comparison, export, glossary, Weekly News Focus, AI Comprehensive Analysis, or frontend behavior through a live database.
- The repository contract validates source-use and same-asset boundaries: rejected or generated-output-disallowed sources are blocked, `metadata_only` and `link_only` sources do not persist raw chunk text, and facts, recent developments, and gaps must bind to same-pack sources and chunks.
- `backend/knowledge_pack_repository.py` re-exports the repository boundary, table names, record model, contract error, and metadata helpers for future retrieval integration.
- The Alembic revision is inspectable and limited to knowledge-pack repository contract tables. The journal records that it imports without Alembic or a database connection, while running it still requires Alembic/SQLAlchemy.
- The journal records that the task did not add live database connections, ORM session execution, route wiring, ingestion persistence, generated-output cache persistence, production repository execution, or changes to current API/retrieval/generation/chat/comparison/export/glossary/frontend behavior.
- `docs/agent-journal/20260425T040950Z.md` records these checks: `python3 -m pytest tests/unit/test_knowledge_pack_repository.py tests/unit/test_repo_contract.py -q` passed with 17 tests; `python3 -m pytest tests -q` passed with 216 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed; `docker compose config` passed.
- Remaining risks from the journal:
  - The repository contract is intentionally dormant and in-memory/unit-tested only; no live database connection, ORM session, route wiring, ingestion persistence, generated-output cache persistence, or production repository execution path was added.
  - The migration is deterministic and inspectable, but it was not executed against a database in this task.
  - Deserialization reconstructs the knowledge-pack contract metadata; cache revalidation runtime objects remain outside the persisted contract for now.

Completion commits:

- `141b3c4 feat(T-077): add persisted knowledge-pack repository contracts`
- `80a318b chore(T-077): merge persisted knowledge-pack repository contracts`

### T-076: Add backend persistence settings and migration scaffold

Goal:
Add the backend persistence configuration and migration scaffold needed for later persisted knowledge-pack work, without routing any current API, retrieval, generation, chat, comparison, or export behavior through a live database.

Completed details:

- Implementation commit `351895f chore(T-076): add backend persistence settings and migration scaffold` updated `requirements.txt`, `.env.example`, backend API/worker env examples, backend persistence settings modules, Alembic scaffold files, `tests/unit/test_persistence_settings.py`, and `docs/agent-journal/20260425T035646Z.md`.
- Merged branch `agent/T-076-20260425T035646Z` into `main` with local merge commit `d26cc62 chore(T-076): merge backend persistence settings and migration scaffold`.
- `backend/settings.py` added `PersistenceSettings` helpers that read server-side database configuration, expose sanitized diagnostics, redact credentials and sensitive query values, and use deterministic missing-config defaults for local tests.
- `backend/db.py` added a lazy `DatabaseEngineFactory` boundary so importing the module does not import SQLAlchemy or open a database connection; engine and session creation are explicit and fail fast when `DATABASE_URL` is missing.
- `backend/persistence.py` added dormant persistence metadata with zero tables and diagnostics for the metadata boundary.
- `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, and `alembic/versions/20260425_0001_persistence_baseline.py` added an Alembic-style migration scaffold with a no-op baseline revision that can be imported without Alembic or a database connection.
- `.env.example`, `deploy/env/api.example.env`, and `deploy/env/worker.example.env` added placeholder-only database tuning variables; no frontend `NEXT_PUBLIC_*` database variables were added.
- `requirements.txt` added bounded production dependencies for SQLAlchemy, Alembic, and psycopg. The journal records the rationale: standard future engine/session abstraction, deterministic migration tooling, and PostgreSQL driver readiness once the dormant boundary is activated; alternatives considered were a custom migration runner or driver-only connection code.
- The journal records that the task did not add repository read/write behavior, migration-generated tables, ingestion persistence, cache persistence, chat persistence, route wiring, live provider calls, or a real database connection in CI.
- `docs/agent-journal/20260425T035646Z.md` records these checks: `python3 -m pytest tests/unit/test_persistence_settings.py tests/unit/test_repo_contract.py -q` passed with 20 tests; `python3 -m pytest tests -q` passed with 208 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed, including 208 tests in both Python phases plus static evals, frontend smoke, typecheck, build, and backend checks; `docker compose config` passed.
- Remaining risks from the journal:
  - The scaffold is intentionally dormant: no repository read/write layer, migration-generated tables, ingestion persistence, cache persistence, chat persistence, or route wiring was added.
  - SQLAlchemy, Alembic, and psycopg are declared as production dependencies, but this task does not install or exercise a real database connection in CI.
  - The baseline migration is a no-op; future persistence work must add real tables and repository contracts in separate, narrowly scoped tasks.

Completion commits:

- `351895f chore(T-076): add backend persistence settings and migration scaffold`
- `d26cc62 chore(T-076): merge backend persistence settings and migration scaffold`

### T-075: Re-audit home page and navigation against frontend workflow docs

Goal:
Re-audit and tighten the home page plus global navigation against the PRD/TDS Frontend Design and Workflow v0.4 baseline so the first user path remains single-stock-or-ETF search, while comparison stays separate but connected and glossary remains contextual inside reading flows.

Completed details:

- Implementation commit `09791f6 docs(T-075): re-audit home page and navigation against frontend workflow docs` updated `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, `tests/frontend/smoke.mjs`, and added `docs/agent-journal/20260425T034732Z.md`.
- Merged branch `agent/T-075-20260425T034732Z` into `main` with local merge commit `fcde6ec chore(T-075): merge re-audit home page and navigation against frontend workflow docs`.
- `apps/web/app/layout.tsx` changed the global Compare navigation entry from the default `VOO`/`QQQ` pair to the neutral `/compare` builder and added deterministic markers for the single-search/separate-compare navigation workflow.
- `apps/web/app/page.tsx` added deterministic markers for the single-asset-search-first home baseline and clarified that glossary help is contextual inside the learning flow.
- `tests/frontend/smoke.mjs` added checks for the search-first home workflow, neutral separate comparison navigation, absence of default-pair top-level navigation, and absence of a top-level glossary workflow.
- The journal records that the task did not change search resolution behavior, comparison route behavior, glossary popover behavior, backend contracts, source-use policy, deterministic fixtures, generated content, or live-provider behavior.
- `docs/agent-journal/20260425T034732Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Coverage is deterministic static smoke coverage and build/type checks; it does not include browser screenshot or interaction testing.
  - The home and navigation audit did not change search resolution behavior, comparison route behavior, glossary popover behavior, or backend contracts.

Completion commits:

- `09791f6 docs(T-075): re-audit home page and navigation against frontend workflow docs`
- `fcde6ec chore(T-075): merge re-audit home page and navigation against frontend workflow docs`

### T-074: Add route-level frontend docs-alignment smoke coverage

Goal:
Add deterministic route-level smoke coverage that checks the existing frontend routes still expose the documented Frontend Design and Workflow v0.4 structure, without changing route behavior, React component logic, backend contracts, source-backed content, or generated copy.

Completed details:

- Implementation commit `8b9e58f docs(T-074): add route-level frontend docs-alignment smoke coverage` updated `tests/frontend/smoke.mjs` and added `docs/agent-journal/20260425T033755Z.md`.
- Merged branch `agent/T-074-20260425T033755Z` into `main` with local merge commit `299d608 chore(T-074): merge route-level frontend docs-alignment smoke coverage`.
- `tests/frontend/smoke.mjs` added grouped deterministic helpers for static marker and ordering assertions.
- Smoke coverage now checks route-level v0.4 workflow markers across home/search, supported asset pages, Weekly News Focus, AI Comprehensive Analysis, source-list/source drawer, contextual glossary, asset chat, comparison, and export controls.
- The journal records that the change stayed test-only: no application routes, React components, backend contracts, deterministic fixtures, generated content, source-use policy, dependencies, or behavior were changed.
- `docs/agent-journal/20260425T033755Z.md` records these checks: `npm test` passed after one focused assertion revision; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Coverage is deterministic static smoke coverage only; it does not replace browser screenshot, viewport, or interaction testing for hover, tap, focus, drawers, bottom sheets, chat, or export controls.
  - The smoke checks depend on existing route/component markers staying meaningful and aligned with actual rendered behavior.

Completion commits:

- `8b9e58f docs(T-074): add route-level frontend docs-alignment smoke coverage`
- `299d608 chore(T-074): merge route-level frontend docs-alignment smoke coverage`

### T-073: Align global responsive spacing and no-overlap frontend layout

Goal:
Tighten shared responsive spacing and no-overlap layout rules across the existing frontend learning surfaces so the v0.4 home, asset, comparison, source drawer, glossary, chat, and export workflows remain usable on small and desktop viewports without changing routes, backend contracts, generated content, or source-backed evidence.

Completed details:

- Implementation commit `339095f feat(T-073): align global responsive spacing and no-overlap frontend layout` updated `apps/web/styles/globals.css`, `tests/frontend/smoke.mjs`, and `docs/agent-journal/20260424T221303Z.md`.
- `apps/web/styles/globals.css` tightened shared responsive rules for text wrapping, min-width containment, and max-width constraints across buttons, chips, source metadata, glossary controls, export controls, helper rails, source drawers, and comparison surfaces.
- The CSS added desktop helper-rail viewport-height containment with internal scrolling, while restoring normal in-flow behavior below the tablet breakpoint.
- The CSS added mobile scroll margins for asset regions, chat, export, source drawer, and glossary surfaces so sticky actions are less likely to obscure anchored content.
- `tests/frontend/smoke.mjs` expanded deterministic frontend smoke coverage for responsive/no-overlap CSS selectors and preservation of v0.4 surface markers.
- `docs/agent-journal/20260424T221303Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Responsive/no-overlap behavior is covered by deterministic CSS selectors, smoke checks, typecheck, and build rather than browser screenshots or device interaction testing.
  - The changes are CSS-only and do not add JavaScript-managed modal coordination between simultaneously open mobile source, glossary, chat, and export surfaces.

Completion commits:

- `339095f feat(T-073): align global responsive spacing and no-overlap frontend layout`
- `ab9bfb3 chore(T-073): merge align global responsive spacing and no-overlap frontend layout`

### T-072: Align mobile chat and export surfaces with documented helper behavior

Goal:
Align asset chat and export controls with Frontend Design and Workflow v0.4 so chat remains a helper surface in the asset learning flow and mobile users get bottom-sheet or full-screen-style behavior for chat/export interactions without changing backend contracts or generated content.

Completed details:

- Implementation commit `ac52af7 feat(T-072): align mobile chat and export surfaces with documented helper behavior` updated `apps/web/components/AssetChatPanel.tsx`, `apps/web/components/ExportControls.tsx`, `apps/web/styles/globals.css`, `tests/frontend/smoke.mjs`, and `docs/agent-journal/20260424T220036Z.md`.
- `AssetChatPanel` now exposes deterministic markers for a bounded asset-specific helper, selected-asset knowledge-pack scope, no general finance chatbot behavior, mobile bottom-sheet or full-screen-style presentation, internal scrolling, sticky asset-context helper affordance, no raw transcript analytics, advice redirects before answer content, `/compare` redirects for comparison questions, no live external calls, and in-flow no-overlap behavior.
- The chat panel wraps prompts, the form, request states, answers, citations, source metadata, session markers, and chat transcript export controls in an `asset-chat-scroll-region`; helper copy states that answers come from the selected asset knowledge pack and that transcript text is not used for product analytics.
- Chat answers now include deterministic markers for redirect-label-before-answer ordering, single-asset-only answer scope, and `/compare` routing when a comparison redirect is returned, while preserving existing advice redirects, unsupported/insufficient-evidence states, citations, source drawers, session metadata, and transcript export behavior.
- `ExportControls` now exposes deterministic markers for Markdown/JSON citation/source/freshness/disclaimer scope, compact stacked mobile behavior, in-flow no-overlap behavior, no unrestricted raw text, no restricted provider payload export, no hidden prompts, no raw model reasoning, and no secret exposure.
- Link and chat transcript export controls now expose compact full-width mobile markers and scope markers; chat transcript exports also mark no raw transcript analytics, no hidden prompts, no raw model reasoning, and internally scrollable mobile results.
- `apps/web/styles/globals.css` added shared chat/export layout rules, mobile chat bottom-sheet-style constraints with `max-height: min(82vh, 720px)`, sticky chat helper header behavior, internal chat scrolling, compact export spacing, `max-height: min(58vh, 520px)` for export results, textarea height constraints, and overflow wrapping for export buttons.
- `tests/frontend/smoke.mjs` added checks for the new chat/export helper-role markers, mobile presentation markers, no-overlap/no-live/no-raw-transcript markers, export scope and restriction markers, chat export safety markers, and responsive CSS selectors.
- `docs/agent-journal/20260424T220036Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Mobile chat and export behavior is covered by deterministic markers, responsive CSS checks, typecheck, and build rather than browser screenshot or interaction testing.
  - The chat surface remains an in-flow bottom-sheet-style panel on mobile; it does not add a JavaScript modal, route-level full-screen view, or gesture-based close behavior.

Completion commits:

- `ac52af7 feat(T-072): align mobile chat and export surfaces with documented helper behavior`
- `dbd2d29 chore(T-072): merge align mobile chat and export surfaces with documented helper behavior`

### T-071: Align comparison builder and result layouts with PRD workflow

Goal:
Align `/compare` with the PRD/TDS comparison workflow so it behaves as a separate but connected comparison surface: an empty builder when no assets are selected, a one-side-selected builder when only one asset is present, and a scan-friendly result layout when a source-backed deterministic comparison pack is available.

Completed details:

- Implementation commit `78446ea feat(T-071): align comparison builder and result layouts with PRD workflow` updated `apps/web/app/compare/page.tsx`, `apps/web/styles/globals.css`, `tests/frontend/smoke.mjs`, and `docs/agent-journal/20260424T214336Z.md`.
- `/compare` no longer silently defaults an empty request to `VOO` vs `QQQ`; query params are normalized, empty requests render an empty builder, and one-sided requests render a selected-asset builder without fetching or generating a two-asset comparison.
- The builder state includes GET form controls, selected-asset cards, deterministic example/suggestion links, freshness labels for non-generated builder output, and explicit no-generated-output/no-live-call markers.
- Available comparison results now expose deterministic PRD markers and section-order markers for header, selected assets, beginner bottom line, stock-vs-ETF relationship context when applicable, key differences, export controls, suggested comparisons, and source metadata.
- The result layout keeps stock-vs-ETF relationship context separate from generic key differences, moves the beginner bottom line before the relationship/key-difference sections, keeps export controls after key differences, and keeps suggested comparisons before source metadata.
- `apps/web/styles/globals.css` added responsive compare-builder form and selected-card styling, including mobile collapse through the existing small-screen grid rules.
- `tests/frontend/smoke.mjs` added checks that empty and one-sided builders branch before `fetchComparisonResponse`, that `VOO`/`QQQ` are no longer defaulted for empty params, that PRD section markers exist in order, and that compare-builder CSS markers are present.
- `docs/agent-journal/20260424T214336Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Responsive behavior is covered by deterministic markers, CSS checks, typecheck, and build rather than browser screenshot or interaction testing.
  - The builder inputs are simple GET form controls and rely on the existing deterministic comparison route/fallback behavior after two tickers are submitted.

Completion commits:

- `78446ea feat(T-071): align comparison builder and result layouts with PRD workflow`
- `c3deebd chore(T-071): merge align comparison builder and result layouts with PRD workflow`

### T-070: Align source-list page with PRD source inspection flow

Goal:
Align the dedicated supported asset source-list page with the PRD/TDS source inspection flow so `/assets/[ticker]/sources` is a clear, citation-first source review surface that complements the asset page without changing backend contracts, source-use policy, or generated content behavior.

Completed details:

- Implementation commit `6314b79 feat(T-070): align source-list page with PRD source inspection flow` updated `apps/web/app/assets/[ticker]/sources/page.tsx`, `apps/web/styles/globals.css`, and `tests/frontend/smoke.mjs` to align supported `/assets/[ticker]/sources` pages with the PRD source inspection flow.
- Supported source-list pages now include deterministic source-list markers, documented section order, backend-contract versus local-fixture fallback labels, source count, official/structured source count, freshness/source-use/allowlist overview, full-text export permission count, source drawer entry markers, back navigation, blocked-state copy, and an educational source-use note.
- The implementation preserved the existing source drawer adapter, same-asset source boundaries, local no-API-base fallback, citation/claim context, allowed excerpt handling, and mobile bottom-sheet source drawer behavior.
- `tests/frontend/smoke.mjs` added coverage for the supported source-list inspection flow marker, blocked or limited source-list marker, section-order marker, rendering/fallback labels, summary counts, source-use/freshness overview markers, back navigation, blocked-state copy, and CSS source-list summary rules.
- `docs/agent-journal/20260424T213305Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Responsive source-list behavior is covered by deterministic markers and CSS checks, not browser screenshot or interaction testing.
  - The full-text export summary depends on the existing source drawer contract or fixture fields; local fixtures without explicit permission fields report zero permitted full-text exports.

Completion commits:

- `6314b79 feat(T-070): align source-list page with PRD source inspection flow`
- `5e6f797 chore(T-070): merge align source-list page with PRD source inspection flow`

### T-069: Align supported asset-page layout with PRD learning flow

Goal:
Align the supported stock and ETF asset-page layout with the PRD/proposal learning-page flow so the page order, desktop helper rail, and mobile action surfaces match the documented user experience without changing backend contracts or source-backed content behavior.

Completed details:

- Implementation commit `0ace5fd feat(T-069): align supported asset-page layout with PRD learning flow` updated `apps/web/app/assets/[ticker]/page.tsx`, `apps/web/components/AssetHeader.tsx`, `apps/web/components/AssetModeLayout.tsx`, and `apps/web/styles/globals.css` to add deterministic PRD layout markers and make the supported asset-page learning flow explicit.
- Supported asset pages now render the documented sequence for Beginner Summary, Top 3 Risks, Key Facts, What It Does/What It Holds, Weekly News Focus, AI Comprehensive Analysis, Deep Dive, Ask, Sources, and the educational framing section.
- Source drawers were moved into a Sources section after chat; the page now includes a desktop helper rail for ask/compare/freshness/source access and mobile in-flow sticky actions for Ask, Compare, and Sources.
- Existing backend adapters, deterministic fixtures, citations, source drawers, glossary context, export controls, Weekly News Focus evidence-limited states, AI Comprehensive Analysis suppression, comparison suggestions, and chat behavior were kept intact.
- `tests/frontend/smoke.mjs` added coverage for the PRD layout marker, section-order marker, section-specific markers, helper rail source access, beginner stable/recent separation, and mobile action/layout markers.
- `docs/agent-journal/20260424T211700Z.md` records these checks: `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Responsive behavior is covered by deterministic markers and CSS smoke checks, not browser screenshot or interaction testing.
  - The helper rail uses anchor links and source titles for access context; it does not duplicate full source drawer content outside the Sources section.

Completion commits:

- `0ace5fd feat(T-069): align supported asset-page layout with PRD learning flow`
- `380ef31 chore(T-069): merge align supported asset-page layout with PRD learning flow`

### T-068: Tighten Weekly News Focus evidence-limited states

Goal:
Make Weekly News Focus contract and UI behavior explicit when the selected evidence set is smaller than the configured maximum or empty, so the product never pads timely context with weak items and AI Comprehensive Analysis stays suppressed unless enough high-signal evidence exists.

Completed details:

- Implementation commit `6a37299 feat(T-068): tighten Weekly News Focus evidence-limited states` added deterministic Weekly News Focus metadata for configured maximum item count, selected item count, suppressed candidate count, evidence state, and evidence-limited state across `backend/models.py`, `backend/weekly_news.py`, and `backend/overview.py`.
- `apps/web/lib/assetWeeklyNews.ts`, `apps/web/lib/fixtures.ts`, `apps/web/components/WeeklyNewsPanel.tsx`, and `apps/web/components/AIComprehensiveAnalysisPanel.tsx` now carry/render frontend markers for limited verified sets, empty `no_high_signal` states, selected-vs-configured counts, suppressed candidate counts, and AI Comprehensive Analysis threshold availability or suppression.
- The backend and frontend changes preserve the evidence-limited Weekly News Focus rule: show fewer items when only a smaller verified set passes selection, show explicit empty states when no high-signal evidence exists, and keep AI Comprehensive Analysis suppressed unless at least two high-signal Weekly News Focus items exist.
- `tests/unit/test_weekly_news.py`, `tests/unit/test_overview_generation.py`, `tests/integration/test_backend_api.py`, `tests/frontend/smoke.mjs`, `evals/weekly_news_eval_cases.yaml`, and `evals/run_static_evals.py` added coverage for configured-vs-selected counts, limited/empty states, AI analysis threshold metadata, and deterministic UI/eval markers.
- `docs/agent-journal/20260424T200434Z.md` records these checks: `git status --short` passed; `python3 -m pytest tests/unit/test_weekly_news.py tests/unit/test_overview_generation.py tests/unit/test_safety_guardrails.py -q` passed with 27 tests; `python3 -m pytest tests/integration/test_backend_api.py -q` passed with 33 tests; `python3 evals/run_static_evals.py` passed; `npm test` passed; `npm run typecheck` initially failed because `.next/types` had not been generated while `npm run build` was running in parallel, then passed after build completed; `npm run build` passed; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Frontend coverage remains deterministic marker/smoke based; no browser screenshot or interaction run was added.
  - Local frontend fixtures still provide a QQQ available-but-limited example, while backend deterministic pack fixtures currently evaluate QQQ as no-high-signal.
  - Suppressed candidate count is aggregate metadata and does not expose per-candidate rejection details in the public response.

Completion commits:

- `6a37299 feat(T-068): tighten Weekly News Focus evidence-limited states`
- `3b73c80 chore(T-068): merge tighten Weekly News Focus evidence-limited states`

### T-067: Add stock-vs-ETF comparison relationship badges

Goal:
Align the comparison page with Frontend Design and Workflow v0.4 for stock-vs-ETF pairs by adding deterministic relationship badges and a special single-company-vs-ETF-basket comparison structure.

Completed details:

- Implementation commit `230400b feat(T-067): add stock-vs-ETF comparison relationship badges` updated `apps/web/lib/compare.ts` with deterministic stock-vs-ETF comparison data for the local `AAPL` vs `VOO` pack, including the `stock-etf-relationship-v1` model, stock ticker, ETF ticker, relationship state, evidence state, badge data, basket-structure data, same-pack citations, and source documents.
- `apps/web/app/compare/page.tsx` now renders a stock-vs-ETF relationship section for `comparison_type === "stock_vs_etf"`, including relationship badges, single-company and ETF-basket panels, verified holding membership copy, partial-overlap/unavailable detail, citation chips, and deterministic `data-*` markers.
- `apps/web/lib/compareSuggestions.ts` now includes `AAPL`/`VOO` as a local comparison pair only when the deterministic source-backed pack is available, with stock-vs-ETF-specific suggestion copy.
- `apps/web/styles/globals.css` added relationship-badge and single-company-vs-ETF-basket styling, and `tests/frontend/smoke.mjs` added marker coverage for stock-vs-ETF schema, ticker markers, relationship/evidence states, same-pack AAPL/VOO citations, unavailable overlap detail, and the allowed local suggestion pairs.
- `docs/agent-journal/20260424T195049Z.md` records these checks: `git status --short` passed; `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Stock-vs-ETF coverage is intentionally limited to the deterministic `AAPL` vs `VOO` local comparison pack.
  - Relationship badge smoke coverage checks deterministic markers and source boundaries, not browser-rendered screenshots.
  - Exact holding weight, top-10 concentration, sector exposure, and full overlap remain unavailable and are labeled as partial evidence.

Completion commits:

- `230400b feat(T-067): add stock-vs-ETF comparison relationship badges`
- `1b9aa8c chore(T-067): merge stock-vs-ETF comparison relationship badges`

### T-066: Align contextual glossary popovers and mobile sheets with v0.4

Goal:
Align contextual glossary help with Frontend Design and Workflow v0.4 so glossary terms remain inline reading aids on desktop and open as mobile bottom-sheet-style cards where appropriate.

Completed details:

- Implementation commit `ce91962 feat(T-066): align contextual glossary popovers and mobile sheets with v0.4` updated `apps/web/components/GlossaryPopover.tsx` with shared interaction behavior for hover preview, click-to-pin/toggle, keyboard focus, Escape close, and an explicit close control.
- The same component update added deterministic `data-*` markers for desktop interaction mode, mobile bottom-sheet presentation, close control, visible term context, and internal scroll readiness.
- `apps/web/styles/globals.css` added responsive mobile glossary rules so glossary cards render as fixed bottom-sheet-style panels with constrained height, sticky term/close header, and internal scrolling.
- Existing curated generic definitions, backend asset-context overlays, citation/source metadata, evidence/freshness states, generic-only fallback labels, and trust-metric readiness markers were preserved.
- `tests/frontend/smoke.mjs` added smoke coverage for glossary desktop behavior markers and mobile bottom-sheet CSS markers.
- `docs/agent-journal/20260424T193948Z.md` records these checks: `git status --short` passed; `npm test` passed; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - The mobile glossary sheet is CSS/state based and does not add drag gestures or a backdrop.
  - Smoke coverage verifies deterministic markers and CSS rules; it does not browser-test hover, focus, tap, and Escape interaction sequences.

Completion commits:

- `ce91962 feat(T-066): align contextual glossary popovers and mobile sheets with v0.4`
- `05d4090 chore(T-066): merge align contextual glossary popovers and mobile sheets with v0.4`

### T-065: Add mobile source drawer bottom-sheet behavior

Goal:
Align source inspection with Frontend Design and Workflow v0.4 so source drawers remain usable on desktop and open as mobile bottom-sheet-style panels for citation/source access.

Completed details:

- Implementation commit `b2be252 feat(T-065): add mobile source drawer bottom-sheet behavior` updated `apps/web/components/SourceDrawer.tsx` with deterministic `data-source-drawer-mobile-presentation="bottom-sheet"`, `data-source-drawer-close-control="native-details-summary"`, and `data-source-title` markers while leaving citation chip anchors unchanged.
- The same component update changed the native `<summary>` label from a generic source-drawer label to a two-line summary with `source-summary-kicker` and `source-summary-title`, so the source title remains visible when users collapse or reopen the drawer.
- `apps/web/styles/globals.css` added mobile-only source drawer rules under `@media (max-width: 620px)`, including `max-height: min(76vh, 640px)`, rounded top corners, upward sheet-style shadow, sticky summary context, internal source-body scrolling, and `overscroll-behavior: contain`.
- `tests/frontend/smoke.mjs` added smoke coverage for the bottom-sheet marker, native details-summary close marker, source title summary class, mobile media query, constrained height, internal scroll behavior, and source-title styling.
- `docs/agent-journal/20260424T193152Z.md` records these checks: `git status --short` passed with a clean initial worktree and only intended task files changed; `npm test` passed; `npm run typecheck` failed once because `.next/types` were not present while build was running, then passed after `npm run build`; `npm run build` passed; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - The mobile source drawer uses responsive CSS and native `<details>` behavior rather than a JavaScript-managed modal sheet; this preserves keyboard behavior and same-page citation anchors but does not add gesture-based drag controls.
  - The drawer remains rendered in page flow on mobile to avoid overlapping page content; it is bottom-sheet-style through constrained height, rounded top corners, shadow, sticky summary context, and internal scrolling.

Completion commits:

- `b2be252 feat(T-065): add mobile source drawer bottom-sheet behavior`
- `74f80a8 chore(T-065): merge mobile source drawer bottom-sheet behavior`

### T-064: Align home search with frontend workflow v0.4

Goal:
Align the home page and search/autocomplete experience with Frontend Design and Workflow v0.4 so the first screen has one primary action: search for a single supported stock or ETF.

Completed details:

- Implementation commit `5e5464a feat(T-064): align home search with frontend workflow v0.4` updated `apps/web/app/page.tsx` with the v0.4 headline `Understand a stock or ETF in plain English`, the required supporting copy, and secondary workflow cards that keep single-asset search primary while linking comparison separately.
- `apps/web/components/SearchBox.tsx` now uses the required placeholder `Search a ticker or name, like VOO, QQQ, or Apple`, labels example chips `VOO`, `QQQ`, `AAPL`, `NVDA`, and `SOXX` as examples only and not recommendations, shows v0.4 support-state chips, and keeps supported results routed to `/assets/[ticker]`.
- `apps/web/lib/search.ts` added deterministic clear `A vs B` / `A versus B` ticker-pattern detection that returns a `comparison_route` search result for `/compare?left=...&right=...` without turning the home page into a comparison builder.
- Recognized unsupported copy now uses `We found this ticker, but it is not supported in v1.`, the supported-scope reminder names U.S.-listed common stocks and non-leveraged U.S.-listed equity ETFs, and unknown/no-match searches show `No supported stock or ETF found for "{query}".` plus a no-invented-facts note.
- `apps/web/styles/globals.css` added styling for the updated home workflow cards, support-state legend, and example chip row; `tests/frontend/smoke.mjs` added smoke coverage for the v0.4 home copy, primary-action marker, separate comparison markers, comparison-route search result, support-state labels, unsupported copy, and no-result copy.
- `docs/agent-journal/20260424T191708Z.md` records these checks: `npm test` failed once on a smoke regex for the literal `/compare?left=` route marker, then passed; `npm run typecheck` failed once because a temporary `comparison` search asset type widened the compare contract type, then passed after keeping comparison as a search state/route only; `npm run build` passed; `python3 -m pytest tests/unit/test_safety_guardrails.py -q` passed with 11 tests; `bash scripts/run_quality_gate.sh` passed, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - The comparison-query detector is intentionally simple and deterministic; it handles clear ticker-style `A vs B` and `A versus B` patterns, while broader natural-language comparison phrasing remains out of scope for this task.
  - Search remains fixture-backed and local; partial, stale, and unavailable states are exposed as labels, but this task did not add new data fixtures for those states.

Completion commits:

- `5e5464a feat(T-064): align home search with frontend workflow v0.4`
- `40fc840 chore(T-064): merge align home search with frontend workflow v0.4`

### T-063: Surface backend trust-metric validation readiness in frontend control surfaces

Goal:
Expose deterministic frontend markers and lightweight adapter validation for the existing backend trust-metric catalog/validation contracts so citation, source drawer, glossary, comparison, export, and safety redirect surfaces remain ready for aggregate metrics without logging raw chat transcript content, adding real analytics, or weakening citation, source-use, freshness, uncertainty, and advice-boundary rules.

Completed details:

- Implementation commit `49e7caa feat(T-063): surface backend trust-metric validation readiness in frontend control surfaces` added `apps/web/lib/trustMetrics.ts` with `trust-metrics-event-v1`, validation-only mode, deterministic timestamp default `1970-01-01T00:00:00Z`, no persistence, no external analytics, no live external calls, required product events, required trust events, compact surface descriptor construction, and lightweight catalog-response validation.
- `apps/web/components/SourceDrawer.tsx`, `apps/web/components/GlossaryPopover.tsx`, `apps/web/components/ComparisonSuggestions.tsx`, `apps/web/app/compare/page.tsx`, `apps/web/components/ExportControls.tsx`, and `apps/web/components/AssetChatPanel.tsx` now expose deterministic `data-*` trust-metric readiness markers for source drawer usage, glossary usage, comparison usage, export usage, chat answer outcomes, chat safety redirects, citation coverage, freshness accuracy, and safety redirect rate.
- The frontend markers use compact metadata such as workflow area, selected section, asset ticker/support state, comparison tickers/state, export content type/format, citation count, source document count, freshness state, evidence state, safety classification, and chat outcome; they do not add analytics emission, backend persistence, browser storage, cookies, live provider calls, or raw transcript/content fields.
- Chat and safety redirect surfaces now label trust-metric readiness for `chat_answer_outcome`, `chat_safety_redirect`, and `safety_redirect_rate` while preserving advice redirects, comparison redirects, unsupported/insufficient-evidence behavior, accountless session handling, and no raw question/answer analytics.
- `tests/frontend/smoke.mjs` now checks the trust-metrics helper constants/catalog validation shape and the frontend marker coverage for source drawer, glossary, comparison, export, citation/freshness, chat answer, and safety redirect surfaces.
- `docs/agent-journal/20260424T173249Z.md` records these checks: `npm test` pass; `npm run typecheck` pass; `npm run build` pass; `python3 -m pytest tests/unit/test_trust_metrics.py tests/integration/test_backend_api.py tests/unit/test_safety_guardrails.py -q` pass with 52 tests; `python3 evals/run_static_evals.py` pass; `bash scripts/run_quality_gate.sh` pass, including 197 Python tests, static evals, frontend smoke, typecheck, build, and backend checks.
- Remaining risks from the journal:
  - Frontend trust-metric readiness remains marker-only and pure-helper validation only; it does not fetch the backend catalog or emit validation events.
  - The helper validates the required T-032 catalog shape at a lightweight frontend level, so future backend catalog expansion may need a matching descriptor update.
  - Markers intentionally expose only compact counts and state labels; they are not a substitute for backend trust-metric validation or storage if real analytics are added later.

Completion commits:

- `49e7caa feat(T-063): surface backend trust-metric validation readiness in frontend control surfaces`
- `5467c4a chore(T-063): merge surface backend trust-metric validation readiness in frontend control surfaces`

### T-062: Align accountless chat export controls with session export contracts

Goal:
Improve the chat export path so supported accountless chat exports can use the existing session export contract when a conversation ID exists, while preserving the current single-turn transcript export fallback, advice redirects, compare redirects, 7-day TTL/deleted-session states, source-use rights, and no raw transcript analytics assumptions.

Completed details:

- Implementation commit `1cb064d feat(T-062): align accountless chat export controls with session export contracts` extended `apps/web/lib/assetChat.ts` with `ChatSessionMetadata`, the `chat-session-contract-v1` session shape, broader support-state typing, `compare_route_redirect` classification, and optional `conversation_id` submission through the existing relative `/api/assets/{ticker}/chat` helper.
- `apps/web/lib/exportControls.ts` now attempts a session-backed `POST /api/assets/{ticker}/chat/export` request when an active conversation ID exists, validates available Markdown `chat_transcript` exports against same-asset or no-factual-evidence bindings, `export-validation-v1`, `export_licensing_scope`, `local_accountless_chat_session`, safe session turn records, `used_existing_chat_contract`, no-new-facts, and no-live-call diagnostics, then falls back to the existing single-turn transcript export path when the session contract is unavailable or invalid.
- `apps/web/components/AssetChatPanel.tsx` now keeps active accountless session metadata in component state for the current interaction, reuses the active conversation ID on follow-up chat calls, renders deterministic chat-session contract markers, passes exportable session metadata to `ExportControls`, and labels comparison workflow redirects separately from advice redirects.
- `apps/web/components/ExportControls.tsx` now renders deterministic chat export markers for `session_contract` versus `single_turn_fallback`, conversation ID presence, lifecycle state, export availability, expiration, validation schema, binding scope, citation/source counts, safe session records, existing chat contract use, and no-live-call diagnostics.
- `tests/frontend/smoke.mjs` now checks chat session markers, session export markers, conversation ID handling, `chat_transcript`, `session_contract`, `single_turn_fallback`, `local_accountless_chat_session`, `used_existing_chat_contract`, `no_factual_evidence`, and safe session turn record markers.
- `docs/agent-journal/20260424T171652Z.md` records these checks: `npm test` failed once on an outdated smoke marker and then passed after a focused marker update; `npm run typecheck` passed; `npm run build` passed; `python3 -m pytest tests -q` passed with 197 tests; `python3 evals/run_static_evals.py` passed; `bash scripts/run_quality_gate.sh` passed.
- Remaining risks from the journal:
  - Chat session continuity is held only in component state for the current interaction; no browser persistence was added.
  - Session-backed export validation is frontend-side contract validation over the existing backend response, so backend chat export schema expansion may require a matching frontend adapter update.
  - When a session export is unavailable or invalid, the control intentionally falls back to the existing single-turn transcript export path and labels it as `single_turn_fallback`.

Completion commits:

- `1cb064d feat(T-062): align accountless chat export controls with session export contracts`
- `c67e379 chore(T-062): merge align accountless chat export controls with session export contracts`

### T-061: Align comparison export controls with backend comparison export contracts

Goal:
Reduce comparison-page export drift by making comparison export controls prefer the existing backend comparison export contract when available, while preserving deterministic `VOO` vs `QQQ` fixture fallback, same-comparison-pack citation boundaries, blocked-state behavior, and no-live-call guardrails.

Completed details:

- Implementation commit `83e30db feat(T-061): align comparison export controls with backend comparison export contracts` extended `apps/web/lib/exportControls.ts` with `fetchSupportedComparisonExportContract`, a shared API-base export endpoint helper, same-comparison-pack Markdown export validation for `/api/compare/export?left_ticker={LEFT}&right_ticker={RIGHT}&export_format=markdown`, and comparison freshness/as-of extraction from export validation sections or source metadata.
- The adapter accepts comparison export payloads only when they are available Markdown comparison exports for the requested left/right supported tickers with educational disclaimer text, `export_licensing_scope`, rendered Markdown, `export-validation-v1`, `same_comparison_pack` binding scope, citation/source/section validation metadata, `same_comparison_pack_*` diagnostics, `used_existing_comparison_contract`, no-live-call diagnostics, no-new-facts diagnostics, allowed exportable source-use policy, and allowed source metadata.
- `apps/web/app/compare/page.tsx` now attempts backend comparison export validation only for already available source-backed local comparison packs, passes the validated contract into `ExportControls`, and preserves the existing relative Markdown export link and local fallback helper copy when validation is unavailable or invalid.
- `apps/web/components/ExportControls.tsx` now exposes comparison contract markers for link exports, including backend/local rendering, validation schema, binding scope, export state, freshness/as-of values, citation/source counts, left/right ticker, and comparison ID while keeping relative Markdown links as the baseline.
- `tests/frontend/smoke.mjs` now checks comparison export adapter markers, same-comparison-pack diagnostics, comparison export route usage, and UI contract markers.
- `docs/agent-journal/20260424T170401Z.md` records these checks: `npm test` pass; `npm run typecheck` failed once on nullable backend comparison export fields, then passed after explicit narrowing; `npm run build` pass; `python3 -m pytest tests -q` pass with 197 tests; `python3 evals/run_static_evals.py` pass; `bash scripts/run_quality_gate.sh` pass.
- Remaining risks from the journal:
  - Comparison export contract validation only runs when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise comparison export controls intentionally show `local_fallback` while preserving the relative Markdown export link.
  - The comparison page only attempts backend export validation for already available local comparison packs, so unavailable, unsupported, out-of-scope, eligible-not-cached, no-local-pack, unknown, and blocked states continue to hide export controls.

Completion commits:

- `83e30db feat(T-061): align comparison export controls with backend comparison export contracts`
- `6a5b96c chore(T-061): merge align comparison export controls with backend comparison export contracts`

### T-060: Align asset-page export controls with backend export contracts

Goal:
Reduce remaining asset-page export drift by validating backend asset-page and source-list export payload availability from existing deterministic export routes while preserving safe Markdown-only links, licensing notes, citation/freshness metadata expectations, and fallback behavior when no API base URL is configured.

Completed details:

- Implementation commit `c677892 feat(T-060): align asset-page export controls with backend export contracts` extended `apps/web/lib/exportControls.ts` with `fetchSupportedAssetExportContract`, `AssetExportContractValidation`, and same-asset Markdown export validation for `/api/assets/{ticker}/export?export_format=markdown` and `/api/assets/{ticker}/sources/export?export_format=markdown`.
- The adapter accepts only supported available Markdown exports with same-asset identity, educational disclaimer text, `export_licensing_scope`, citation/source metadata, freshness or as-of metadata, `export-validation-v1`, `same_asset` binding scope, allowed exportable source-use policy, no-live-call diagnostics, and existing-overview/no-new-facts diagnostics.
- `apps/web/app/assets/[ticker]/page.tsx` now fetches the asset-page and source-list export contracts independently for supported asset pages, records `data-asset-page-export-contract` and `data-asset-source-list-export-contract`, and preserves local fallback rendering when a backend response is unavailable, invalid, blocked, unsupported, non-Markdown, or no API base URL is configured.
- `apps/web/components/ExportControls.tsx` now renders export contract markers for link controls, including `backend_contract` or `local_fallback`, schema, binding scope, export state, freshness, as-of date, citation count, and source count, while keeping relative Markdown links as the baseline.
- `tests/frontend/smoke.mjs` now checks the asset export adapter routes, contract markers, validation diagnostics, licensing/disclaimer context, and no new live external URL usage.
- `docs/agent-journal/20260424T165234Z.md` records these checks: `npm test` pass; `npm run typecheck` pass after a focused type-narrowing fix; `npm run build` pass; `python3 -m pytest tests -q` pass with 197 tests; `python3 evals/run_static_evals.py` pass; `bash scripts/run_quality_gate.sh` pass.
- Remaining risks from the journal:
  - Backend export contract validation only runs when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise asset-page controls intentionally show `local_fallback` while keeping the relative Markdown links.
  - Asset-page and source-list export validations fall back independently if either backend response is unavailable, blocked, unsupported, non-Markdown, or contract-invalid.

Completion commits:

- `c677892 feat(T-060): align asset-page export controls with backend export contracts`
- `2bfe273 chore(T-060): merge align asset-page export controls with backend export contracts`

### T-059: Fetch supported glossary context from backend glossary contracts

Goal:
Reduce remaining supported asset-page glossary drift by consuming the existing backend glossary asset-context contract when it is available, while preserving curated generic glossary definitions, deterministic fallback rendering, same-asset citation boundaries, and current blocked/no-live-call guardrails.

Completed details:

- Implementation commit `e2a5aa7 feat(T-059): fetch supported glossary context from backend glossary contracts` added `apps/web/lib/assetGlossary.ts`, a deterministic frontend adapter for `/api/assets/{ticker}/glossary` that validates the `glossary-asset-context-v1` schema, supported same-asset identity, no-live-call diagnostics, generic-definitions-not-evidence diagnostics, same-asset evidence boundaries, and restricted-text suppression before returning usable glossary context.
- The adapter filters backend glossary terms to terms already rendered in the asset-page glossary groups, skips generic-only entries, requires same-asset allowed citation bindings for cited context, maps allowed `summary_allowed` or `full_text_allowed` source references, and keeps explicit uncertainty labels or suppression reasons when citations are absent.
- `apps/web/app/assets/[ticker]/page.tsx` now fetches backend glossary context independently after the existing overview/details/weekly-news/source-drawer fetches, passes available term context into `GlossaryPopover`, records `data-asset-glossary-rendering`, and preserves deterministic static glossary fallback when the backend response is unavailable, invalid, filtered to no usable rendered terms, or no API base URL is configured.
- `apps/web/components/GlossaryPopover.tsx` keeps curated generic definitions visible while adding optional asset-context state, evidence state, freshness state, citation IDs, uncertainty labels, source-reference metadata, suppression reasons, and generic-only labels inside glossary cards.
- `tests/frontend/smoke.mjs` now checks glossary backend-context markers, asset citation/source/uncertainty markers, the injectable asset-glossary fetch helper, and no new live external URL usage.
- `docs/agent-journal/20260424T164150Z.md` records these passing checks: `npm test`; `npm run typecheck`; `npm run build`; `python3 -m pytest tests/integration/test_backend_api.py -q`; `python3 evals/run_static_evals.py`; `bash scripts/run_quality_gate.sh`.
- Remaining risks from the journal:
  - Supported asset pages only use backend glossary context when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise they intentionally keep the deterministic static glossary path.
  - The frontend adapter overlays backend context only for terms already rendered in the asset-page glossary groups, with generic-only and unusable backend records falling back to curated definitions.

Completion commits:

- `e2a5aa7 feat(T-059): fetch supported glossary context from backend glossary contracts`
- `0a3a782 chore(T-059): merge fetch supported glossary context from backend glossary contracts`

### T-058: Align asset-page source drawer contexts with backend source metadata contracts

Goal:
Reduce remaining supported asset-page source drawer drift by preferring the existing backend source-drawer contract for related claim context, section references, and allowed excerpts when it is available, while preserving deterministic fallback rendering, same-asset citation boundaries, and current blocked/no-live-call guardrails.

Completed details:

- Implementation commit `be3527b feat(T-058): align asset-page source drawer contexts with backend source metadata contracts` updated the supported asset page to overlay backend `/api/assets/{ticker}/sources` entries onto already-rendered source drawers by `source_document_id` when the response matches the existing deterministic `asset-source-drawer-v1` contract.
- `apps/web/lib/sourceDrawer.ts` now exposes a small source-record mapping helper that lets the asset page reuse backend related claims, section references, and allowed excerpts without changing backend routes or source-use policy.
- `apps/web/app/assets/[ticker]/page.tsx` preserves independent deterministic fallback rendering when the backend source-drawer response is unavailable, invalid, missing a rendered source document ID, or no API base URL is configured.
- `tests/frontend/smoke.mjs` now checks the supported asset-page source-drawer backend overlay markers.
- `docs/agent-journal/20260424T025701Z.md` records these passing checks: `npm test`; `npm run typecheck`; `npm run build`; `python3 evals/run_static_evals.py`; `python3 -m pytest tests/integration/test_backend_api.py -q`; `bash scripts/run_quality_gate.sh`.
- Remaining risks from the journal:
  - Supported asset pages still intentionally stay on deterministic local fixture drawer rendering when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is not configured.
  - The asset page now overlays backend source-drawer entries per rendered `source_document_id`, but any supported page source not present in the backend `/sources` response still falls back to the existing local claim-context path for this cycle.

Completion commits:

- `6d29283 chore(T-058): prepare align asset-page source drawer contexts with backend source metadata contracts task`
- `be3527b feat(T-058): align asset-page source drawer contexts with backend source metadata contracts`
- `1f978dc chore(T-058): merge align asset-page source drawer contexts with backend source metadata contracts`

### T-057: Fetch supported asset detail and recent-context sections from backend contracts

Goal:
Reduce remaining frontend fixture drift on supported asset pages by consuming the existing backend detail and weekly-news contracts for Deep-Dive sections and timely-context rendering when they are available, while preserving deterministic fallback rendering, stable-vs-timely separation, and current blocked/no-live-call guardrails.

Completed details:

- Implementation commit `66adeec feat(T-057): fetch supported asset detail and recent-context sections from backend contracts` added `apps/web/lib/assetDetails.ts` to validate supported `/api/assets/{ticker}/details` payloads and merge backend stock `business_model` and `diversification_context` plus ETF `role`, `holdings`, and `cost_context` fields, refreshed citations, and updated freshness dates into the existing deterministic asset fixture shape.
- The same commit added `apps/web/lib/assetWeeklyNews.ts` to validate `weekly-news-focus-v1` and `ai-comprehensive-analysis-v1` responses from `/api/assets/{ticker}/weekly-news`, then map backend weekly-news windows, items, citations, source documents, analysis sections, suppression state, and source-document bindings into the existing Weekly News Focus and AI Comprehensive Analysis fixture shape while preserving no-live-call and stable-facts-separate behavior.
- `apps/web/app/assets/[ticker]/page.tsx` now prefers backend overview, details, and weekly-news fetches independently for supported assets, records `data-asset-overview-rendering`, `data-asset-details-rendering`, and `data-asset-weekly-news-rendering`, and preserves deterministic local fallback whenever any response is unavailable or invalid.
- `tests/frontend/smoke.mjs` now checks the asset detail and weekly-news adapter markers, including required `/details` and `/weekly-news` route strings and the page-level rendering markers.
- `docs/agent-journal/20260424T022200Z.md` records these checks: `npm test` pass; `npm run typecheck` fail on first run, then pass after one focused type fix; `npm run build` pass; `python3 evals/run_static_evals.py` pass; `python3 -m pytest tests/integration/test_backend_api.py -q` pass; `bash scripts/run_quality_gate.sh` pass.
- Remaining risks from the journal:
  - Supported asset pages only attempt backend detail and weekly-news fetches when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise they intentionally stay on the deterministic local fixture path.
  - The `/api/assets/{ticker}/details` contract is narrower than the existing deep-dive fixture sections, so this cycle overlays backend-backed stock and ETF detail fields onto the current section structure instead of replacing every section with a fully backend-native shape.
  - Weekly News Focus and AI Comprehensive Analysis now prefer the backend wrapper contract, but the deep-dive `recent_developments` fixture section remains unchanged in this cycle.

Completion commits:

- `ceb9c3a chore(T-057): prepare fetch supported asset detail and recent-context sections from backend contracts task`
- `66adeec feat(T-057): fetch supported asset detail and recent-context sections from backend contracts`
- `3ba8925 chore(T-057): merge fetch supported asset detail and recent-context sections from backend contracts`

### T-056: Fetch supported asset overview pages from backend overview contracts

Goal:
Reduce frontend fixture drift on supported asset pages by consuming the existing backend overview contract for stable beginner-overview content when it is available, while preserving deterministic fallback rendering and current blocked/no-live-call guardrails.

Completed details:

- Implementation commit `c5fab18 feat(T-056): fetch supported asset overview pages from backend overview contracts` added `apps/web/lib/assetOverview.ts` as a deterministic frontend adapter for `/api/assets/{ticker}/overview`, validating supported stock and ETF overview payloads and merging backend asset identity, freshness, beginner summary, top risks, suitability summary, claims, citations, and source documents into the existing asset fixture shape.
- `apps/web/app/assets/[ticker]/page.tsx` now attempts the backend overview fetch for supported assets, records whether overview rendering came from `backend_contract` or `local_fixture`, and preserves the existing local deterministic fallback when the response is unavailable, invalid, or the API base URL is not configured.
- `tests/frontend/smoke.mjs` now checks the overview adapter markers, including the overview fetch helper, backend-rendering marker, and required overview route strings.
- `docs/agent-journal/20260424T015016Z.md` records these passing checks: `npm test`, `npm run typecheck`, `npm run build`, `python3 -m pytest tests/integration/test_backend_api.py -q`, and `bash scripts/run_quality_gate.sh`.
- Remaining risks from the journal:
  - Supported asset pages only attempt the backend overview fetch when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise they intentionally fall back to the deterministic local fixture path.
  - This cycle only backend-aligns stable overview identity, freshness, beginner summary, top risks, suitability, citations, and source metadata; the stable fact list, citation contexts, and deep-dive sections remain on the deterministic local adapter path until later tasks expand the contract usage.

Completion commits:

- `cf9d665 chore(T-056): prepare fetch supported asset overview pages from backend overview contracts task`
- `c5fab18 feat(T-056): fetch supported asset overview pages from backend overview contracts`
- `bca802b chore(T-056): merge fetch supported asset overview pages from backend overview contracts`

### T-055: Fetch supported source-list pages from backend source-drawer contracts

Goal:
Reduce frontend fixture drift on supported source-list pages by consuming the existing backend source-drawer contract when it is available, while preserving deterministic blocked-state behavior and safe fallback rendering.

Completed details:

- Implementation commit `4faa192 feat(T-055): fetch supported source-list pages from backend source-drawer contracts` added `apps/web/lib/sourceDrawer.ts` as a deterministic frontend adapter for `/api/assets/{ticker}/sources`, validating the backend `asset-source-drawer-v1` payload and mapping `source_groups`, `citation_bindings`, `related_claims`, `section_references`, and `allowed_excerpts` into the existing `SourceDrawer` render shape.
- `apps/web/app/assets/[ticker]/sources/page.tsx` now attempts the backend source-drawer fetch for supported assets, records whether rendering came from `backend_contract` or `local_fixture`, and preserves the existing local deterministic fallback when the response is unavailable, invalid, or the API base URL is not configured.
- `apps/web/components/SourceDrawer.tsx` was updated to accept backend-mapped excerpt notes and to render a safe empty-excerpt message when supporting passages are unavailable for the current drawer state.
- `tests/frontend/smoke.mjs` now checks the new source-list rendering markers and confirms the source-drawer adapter route and contract markers are present.
- `docs/agent-journal/20260424T012006Z.md` records these passing checks: `npm test`, `npm run typecheck`, `npm run build`, `python3 -m pytest tests/integration/test_backend_api.py -q`, and `bash scripts/run_quality_gate.sh`.
- Remaining risks from the journal:
  - Supported source-list pages only attempt the backend source-drawer fetch when `NEXT_PUBLIC_API_BASE_URL` or `API_BASE_URL` is configured; otherwise they intentionally fall back to the deterministic local fixture path.
  - The frontend maps backend `related_claims` plus `allowed_excerpts` into the existing `SourceDrawer` context shape, so future backend contract expansion beyond the validated fields will need a matching adapter update.

Completion commits:

- `ab9f117 chore(T-055): prepare fetch supported source-list pages from backend source-drawer contracts task`
- `4faa192 feat(T-055): fetch supported source-list pages from backend source-drawer contracts`
- `c833638 chore(T-055): merge fetch supported source-list pages from backend source-drawer contracts`

### T-054: Align unsupported and unavailable source-list empty states with backend support-state contracts

Goal:
Align unsupported and unavailable source-list rendering and empty states with backend support-state contracts so blocked and non-blocked source routes behave deterministically and safely.

Task-scope paragraph:
Updated the source-list route and shared source-list helpers to map backend-aligned support-state classes onto source-list and source-empty UI behavior for unsupported, out-of-scope, unknown, unavailable, stale, partial, eligible-not-cached, and insufficient-evidence cases while preserving existing supported-asset metadata behavior and non-advice educational framing.

Completed details:

- Branch commit `6436893 feat(T-054): align unsupported and unavailable source-list empty states with backend support-state contracts` added/updated:
  - `apps/web/app/assets/[ticker]/sources/page.tsx` with deterministic support-state handling for source-list and source-empty behavior.
  - `apps/web/components/SourceDrawer.tsx` to export a shared support-state mapping helper.
  - `tests/frontend/smoke.mjs` with source-list presence and state-marker coverage.
- Local commit/merge evidence `18a8dc1 chore(T-054): merge align unsupported and unavailable source-list empty states with backend support-state contracts` includes the completed branch merge and a quality-gate pass note.
- `docs/agent-journal/20260423T224910Z.md` records:
  - `npm test` pass
  - `npm run typecheck` pass
  - `npm run build` pass
  - `python3 evals/run_static_evals.py` pass
  - `bash scripts/run_quality_gate.sh` pass
- Remaining risks:
  - Source-list supported-state rendering remains fixture-only.
  - Support-state derivation uses local search contracts and must be updated when those contracts change.

Completion commits:

- `6436893 feat(T-054): align unsupported and unavailable source-list empty states with backend support-state contracts`
- `18a8dc1 chore(T-054): merge align unsupported and unavailable source-list empty states with backend support-state contracts`

### T-053: Replace compare-page fixture-only routing with backend-aligned deterministic comparison adapters

Goal:
Align the compare route to backend comparison-contract inputs while preserving existing deterministic behavior and blocked-state safety.

Completed details:

- `apps/web/lib/compare.ts` and `apps/web/app/compare/page.tsx` use backend-aligned comparison contract inputs when available and keep deterministic fixture fallback behavior.
- `fetchComparisonResponse` and response shape validation were already in use in the compare flow, with fallback to local comparison fixtures when backend responses are unavailable or invalid.
- Contract-aware smoke assertions in `tests/frontend/smoke.mjs` cover compare-route behavior.
- Journal evidence at `docs/agent-journal/20260423T223353Z.md` confirms `npm test`, `npm run typecheck`, `npm run build`, and `bash scripts/run_quality_gate.sh` passed.
- Journal evidence at `docs/agent-journal/20260423T221625Z.md` confirms the same command set and documents remaining risks around backend contract fallback.
- This task was completed through branch `agent/T-053-20260423T223353Z` and merged with commit `ea385d4`.

Completion commits:

- `ea385d4` (local merge commit on branch `agent/T-053-20260423T223353Z`)


### T-052: Align home search UI with backend support-classification and blocked-state contracts

Goal:
Align the home search UX with existing backend support-classification contract states so supported, ambiguous, eligible-not-cached, recognized-unsupported, out-of-scope, and unknown search outcomes render deterministically and clearly, while preserving blocked-copy messaging, no-generated-page behavior, and educational framing.

Completed details:

- Implementation branch commit `97a3a99 feat(T-052): align home search UI with backend support-classification and blocked-state contracts` changed comparison data flow to prefer backend `/api/compare` results with deterministic fallback through local fixtures, and added runtime comparison payload validation in `apps/web/lib/compare.ts`.
- `apps/web/app/compare/page.tsx` now calls an async comparison fetch path with fallback to `getComparePageFixture` when backend fetch or payload validation fails.
- `apps/web/lib/compare.ts` now includes `fetchComparisonResponse`, `CompareRequest`, and a runtime payload guard that checks for expected backend comparison fields before rendering.
- `tests/frontend/smoke.mjs` assertions now verify that compare fixtures and routing flow are contract-aware instead of fixture-only, including `/api/compare` usage.
- Completion evidence includes a local merge commit `24cbd87 chore(T-052): merge align home search UI with backend support-classification and blocked-state contracts`.
- Journal evidence at `docs/agent-journal/20260423T221625Z.md` reports `npm test`, `npm run typecheck`, `npm run build`, and `bash scripts/run_quality_gate.sh` as passing for the branch.
- There is no separate `T-052`-specific journal content in this workspace; the existing timestamped journal file is present but labeled as `Task T-053`.

Completion commits:

- `97a3a99 feat(T-052): align home search UI with backend support-classification and blocked-state contracts`
- `dc501e3 chore(T-052): prepare align home search UI with backend support-classification and blocked-state contracts`
- `24cbd87 chore(T-052): merge align home search UI with backend support-classification and blocked-state contracts`

### T-051: Render Weekly News Focus and AI Comprehensive Analysis on supported asset pages

Goal:
Render Weekly News Focus and AI Comprehensive Analysis for supported assets using the existing deterministic contract shape on asset pages, while keeping both modules visually and semantically separate from stable canonical facts and preserving unknown/stale/partial evidence handling.

Completed:

- Updated `apps/web/app/assets/[ticker]/page.tsx`, `apps/web/components/WeeklyNewsPanel.tsx`, and `apps/web/components/AIComprehensiveAnalysisPanel.tsx` to render deterministic timely-context contract fields for supported assets only.
- Kept timely context separation from stable facts in the page flow and preserved no-advice educational framing and uncertainty labels in fallback states.
- Left backend contracts, provider wiring, and live data paths unchanged; implementation remained deterministic and fixture-backed.
- Task completed after one focused iteration following an initial typecheck pass.

Verification:

- `npm test` — pass
- `npm run typecheck` — fail then pass after focused typefix
- `npm run build` — pass
- `python3 evals/run_static_evals.py` — pass
- `bash scripts/run_quality_gate.sh` — pass

Remaining risks:

- `SourceDrawer` state mapping still treats unrecognized freshness states as `unknown`.
- AI Comprehensive Analysis renders only when `analysisAvailable` and section data exist; suppressed/empty states are textual by design.

Completion commits:

- `07f3729` chore(T-051): prepare render Weekly News Focus and AI Comprehensive Analysis on supported asset pages
- `328d08c` feat(T-051): render Weekly News Focus and AI Comprehensive Analysis on supported asset pages
- `81993ca` chore(T-051): merge render Weekly News Focus and AI Comprehensive Analysis on supported asset pages

### T-050: Align asset-page source drawer and freshness labels with backend contracts

Goal:
Align all asset-page source-drawer and freshness-label rendering with existing backend contract shapes so source metadata, freshness states, and uncertainty labels remain consistent across supported, blocked, and unavailable asset flows, while staying deterministic and education-first.

Completed:

- Updated `apps/web/app/assets/[ticker]/page.tsx`, `apps/web/components/FreshnessLabel.tsx`, and `apps/web/components/SourceDrawer.tsx` to consume deterministic contract-shaped fields for source metadata and freshness rendering.
- Fixed an initial typecheck issue by switching `SourceDrawer` to normalized contract fields (`supportingPassage`, `isOfficial`) instead of non-existent snake_case aliases.
- Kept existing blocked/unsupported/unknown/unavailable support-state behavior intact while preserving citation and uncertainty boundaries.
- No backend or live-provider changes were introduced in this frontend-contract alignment task.

Acceptance criteria:

- `SourceDrawer` and freshness chips render backend-contracted state labels (`fresh`, `stale`, `unknown`, `unavailable`, `partial`, `insufficient_evidence`) consistently for available/blocked/unavailable rows.
- `SourceDrawer` uses normalized contract fields for source metadata and freshness, preserving existing blocked-state semantics and citation access behavior.
- The updated asset-page path contains deterministic, contract-backed source/freshness behavior with no additional scope changes.
- Required checks passed, and the task was marked as pass after one revision (initial typecheck failure was corrected and re-ran).

Verification:

- `npm test`
- `npm run typecheck`
- `npm run build`
- `python3 -m pytest tests -q`
- `python3 evals/run_static_evals.py`
- `bash scripts/run_quality_gate.sh`

Remaining risks:

- `SourceDrawer` currently supports blocked-state rendering via `drawerState`, but the local fixture route continues to pass `available` for rendered source rows.
- Freshness label copy is tested through smoke-path checks without dedicated unit assertions for exact copy variants.

Completion commits:

- `8b81fae924b105182e0c515fa6f425d460eae8ea` feat(T-050): align asset-page source drawer and freshness labels with backend contracts
- `1fb6af6b8f25784f174f452c5242436d53acf8f0` chore(T-050): merge align asset-page source drawer and freshness labels with backend contracts

### T-049: Reduce frontend fixture drift by introducing shared deterministic view adapters


### T-049: Reduce frontend fixture drift by introducing shared deterministic view adapters

Goal:
Reduce frontend fixture drift by using one shared deterministic adapter path for local search, comparison, and source/freshness rendering, replacing duplicated fixture-only derivation in page components.

Completed:

- Added a shared frontend adapter module and rewired the local search/compare path to consume adapter-shaped outputs for support-state, source metadata, and freshness labels.
- Updated `apps/web/components/SearchBox.tsx`, `apps/web/components/ComparisonSourceDetails.tsx`, `apps/web/components/SourceDrawer.tsx`, and `apps/web/components/FreshnessLabel.tsx` rendering to use adapter-shaped labels/metadata instead of local ad hoc derivation.
- Updated `tests/frontend/smoke.mjs` to assert shared-adapter marker behavior and deterministic render paths.
- Added `apps/web/lib/viewAdapters.ts` as the adapter entrypoint used by `apps/web/lib/search.ts` and `apps/web/lib/compare.ts`.
- No unsupported or advisory-style outputs were added; blocked/unsupported/unknown states preserve existing deterministic guardrails.
- Remaining documented risk: compare-page availability copy in `app/compare/page.tsx` remains page-local, while support-state and source-metadata shaping is now centralized.
- A required journal entry was referenced as [docs/agent-journal/20260423T201841Z.md], but that file is not present in this workspace.

Verification:

- `python3 -m pytest tests -q`
- `npm test`
- `npm run typecheck`
- `npm run build`
- `python3 evals/run_static_evals.py`
- `bash scripts/run_quality_gate.sh`

Completion commits:

- `4a1091360017e16a421fa71f7a5e6affb88dcd16 feat(T-049): reduce frontend fixture drift by introducing shared deterministic view adapters`
- `9c602cc4fae2f4e1bf759e0cd95dea021e726d51 chore(T-049): merge reduce frontend fixture drift by introducing shared deterministic view adapters task`

### T-048: Replace compare-page fixture logic with backend-aligned deterministic comparison contracts

Goal:
Align the deterministic compare page with the existing backend comparison contract so supported and unavailable comparison states render from backend-aligned response shapes instead of compare-page-only fixture logic, without introducing live calls, new comparison packs, or advice-like copy.

Completed:

- Refactored the compare-page data path around backend-aligned deterministic comparison shaping in `apps/web/lib/compare.ts`, then updated `apps/web/app/compare/page.tsx` and `apps/web/components/ComparisonSourceDetails.tsx` to consume that local contract instead of compare-page-only fixture fields.
- Updated compare UI gating so unsupported or unavailable comparison states do not imply supported generated output, while `apps/web/components/ComparisonSuggestions.tsx` and `apps/web/lib/compareSuggestions.ts` stay aligned with the current deterministic comparison availability flow.
- Extended `tests/frontend/smoke.mjs` for compare-route rendering markers and state gating, and recorded the run in `docs/agent-journal/20260423T194410Z.md`.
- The T-048 agent journal records that these commands passed:
  - `python3 -m pytest tests/unit/test_comparison_generation.py tests/integration/test_backend_api.py -q`
  - `npm test`
  - `npm run typecheck`
  - `npm run build`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
- Merged local branch: `agent/T-048-20260423T194410Z`.
- Remaining documented risk: the compare page now mirrors the backend comparison contract shape and availability taxonomy locally, but it is still deterministic fixture-backed only and does not fetch `/api/compare`.
- Remaining documented risk: available comparison evidence details remain implemented only for the current local `VOO`/`QQQ` pack and its reverse order; future local packs will need matching contract data to preserve parity.

Completion commits:

- `402fddd feat(T-048): replace compare-page fixture logic with backend-aligned deterministic comparison contracts`
- `c6e5740 chore(T-048): merge replace compare-page fixture logic with backend-aligned deterministic comparison contracts`

### T-047: Align home search UI with backend support-classification states

Goal:
Align the deterministic home search UI with the existing backend search support-classification contract so beginners see clear, state-correct results for supported, ambiguous, eligible-not-cached, recognized-unsupported, out-of-scope, and unknown searches without introducing live calls, new asset coverage, or advice-like copy.

Completed:

- Added `apps/web/lib/search.ts` as a compare-independent local search contract module with backend-aligned support-classification types, blocked-explanation metadata, deterministic candidate sets, and resolution helpers for `cached_supported`, `eligible_not_cached`, `recognized_unsupported`, `out_of_scope`, and `unknown` search states.
- Updated `apps/web/components/SearchBox.tsx` to render state-specific result panels for supported, ambiguous, ingestion-needed, unsupported, out-of-scope, and unknown searches, including generated-page gating via `can_open_generated_page`, disambiguation requirements for multi-result searches, and explicit no-invented-facts handling for unknown queries.
- Updated `apps/web/app/page.tsx` home-page copy and example cards so the visible search examples match the backend-aligned state taxonomy, including ambiguous, ingestion-needed, unsupported, out-of-scope, and unknown examples.
- Extended `tests/frontend/smoke.mjs` to assert the new home-search state markers, result gating markers, blocked-state messaging, ingestion-needed messaging, and unknown-search no-invented-facts copy.
- Added `docs/agent-journal/20260423T191509Z.md` documenting the changed files, commands run, pass/fail status, and remaining risks.
- The agent journal records that these commands passed:
  - `npm run typecheck`
  - `npm test`
  - `npm run build`
  - `python3 -m pytest tests -q`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
- Merged local branch: `agent/T-047-20260423T191509Z`.
- Remaining documented risk: the home search contract is still duplicated in frontend-local deterministic fixtures, so future backend search-candidate or copy changes will need a matching frontend update to keep parity.
- Remaining documented risk: search disambiguation now reflects backend support states and routing gates, but it remains fixture-backed only and does not add live API fetching or broader entity-resolution coverage beyond the local contract examples.

Completion commits:

- `0b2a651 feat(T-047): align home search UI with backend support-classification states`
- `de95739 chore(T-047): merge align home search UI with backend support-classification states`

### T-046: Render Weekly News Focus and AI analysis on asset pages

Goal:
Render the existing deterministic Weekly News Focus and AI Comprehensive Analysis contract on supported frontend asset pages so the UI matches the PRD/TDS separation between stable facts and timely context without introducing live calls, new assets, or advice-like copy.

Completed:

- Added dedicated frontend timely-context components in `apps/web/components/WeeklyNewsPanel.tsx` and `apps/web/components/AIComprehensiveAnalysisPanel.tsx`, with explicit Weekly News Focus state markers, source quality and source-use metadata, and AI Comprehensive Analysis section ordering for `What Changed This Week`, `Market Context`, `Business/Fund Context`, and `Risk Context`.
- Updated `apps/web/app/assets/[ticker]/page.tsx` to render those modules separately from stable facts and to wire the deterministic timely-context fixture helpers already referenced by the asset-page scaffold.
- Expanded `apps/web/lib/fixtures.ts` with deterministic Weekly News Focus and AI Comprehensive Analysis fixture data and state handling used by supported asset pages, while keeping the implementation fixture-backed and local only.
- Extended `tests/frontend/smoke.mjs` to assert the new timely-context rendering markers, including Weekly News Focus visibility, AI analysis state handling, and the required separation from stable facts.
- Added `docs/agent-journal/20260423T183709Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- The agent journal records that these commands passed:
  - `npm test`
  - `npm run typecheck`
  - `npm run build`
  - `python3 -m pytest tests/unit/test_repo_contract.py -q`
  - `bash scripts/run_quality_gate.sh`
- Remaining documented risk: Weekly News Focus and AI Comprehensive Analysis remain deterministic fixture-backed frontend rendering only; no live provider or backend-fetch integration was added.
- Remaining documented risk: the available-analysis path is exercised by local `QQQ` fixture context, while `VOO` and `AAPL` intentionally remain in empty or suppressed analysis states.
- Remaining documented risk: weekly-context source drawers reuse asset citation contexts when available and otherwise fall back to timely-context claim labels instead of richer per-citation weekly context records.

Completion commits:

- `d42cc82 feat(T-046): render Weekly News Focus and AI analysis on asset pages`
- `4dd683c chore(T-046): merge render Weekly News Focus and AI analysis on asset pages`

### T-045: Add grounded chat comparison-redirect contract

Goal:
Add a deterministic grounded chat comparison-redirect contract so single-asset chat can detect second-ticker comparison questions and return a compare-workflow suggestion backed by existing local comparison availability states instead of generating a multi-asset answer inside the single-asset endpoint, without adding frontend UI, live calls, new facts, new comparison pairs, or weakening citation, source-use, freshness, unknown/stale/unavailable/partial, and safety rules.

Completed:

- Added additive grounded-chat redirect models in `backend/models.py`, including `ChatCompareRouteDiagnostics` and `ChatCompareRouteSuggestion`, plus `compare_route_suggestion` support on `ChatResponse`, `ChatTurnRecord`, and `ChatSessionTurnSummary`.
- Updated `backend/chat.py` so second-ticker questions in single-asset chat detect the ordered comparison pair from the submitted question, call the existing deterministic comparison pipeline, reuse `comparison.evidence_availability.availability_state`, and return `compare_route_redirect` workflow guidance with ordered `/compare?left=...&right=...` metadata instead of a multi-asset factual answer.
- Preserved grounding and safety boundaries by returning empty chat citations and source documents for redirect-only turns, keeping advice redirects higher priority than comparison convenience, and reusing existing local availability states for `available`, `no_local_pack`, `eligible_not_cached`, `unsupported`, `out_of_scope`, and `unknown` comparison cases covered by local fixtures.
- Updated `backend/chat_sessions.py` and `backend/export.py` so compare redirects persist through session turn records, session status, and transcript export, including `comparison_redirect` and `comparison_redirects` export sections plus `no_factual_evidence` validation without fabricated comparison evidence.
- Extended `evals/run_static_evals.py`, `tests/unit/test_chat_generation.py`, `tests/unit/test_chat_sessions.py`, `tests/unit/test_exports.py`, `tests/unit/test_safety_guardrails.py`, and `tests/integration/test_backend_api.py` for redirect schema coverage, second-ticker detection, ordered route metadata, supported and unavailable comparison states, advice-precedence behavior, session/export propagation, and no mixed-asset citation or source-document leakage.
- Added `docs/agent-journal/20260423T163224Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- The agent journal records that these commands passed:
  - `python3 -m pytest tests/unit/test_chat_generation.py tests/unit/test_chat_sessions.py tests/unit/test_exports.py tests/unit/test_safety_guardrails.py -q`
  - `python3 -m pytest tests/integration/test_backend_api.py -q`
  - `python3 -m pytest tests -q`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
- Merged local branch: `agent/T-045-20260423T163224Z`.
- Remaining documented risk: second-ticker detection is intentionally narrow and ticker-token-based; it handles the deterministic comparison question patterns covered by local fixtures without expanding into broader name/entity resolution.
- Remaining documented risk: comparison redirects reuse current local comparison availability only and do not expose comparison facts, so future fixture changes need to preserve the same availability-state meanings and route-order expectations.

Completion commits:

- `09b0c7d feat(T-045): add grounded chat comparison-redirect contract`
- `5551f0e chore(T-045): merge grounded chat comparison-redirect contract`

### T-044: Add export source-use and freshness validation contract

Goal:
Add a deterministic export source-use and freshness validation contract so backend and UI clients can tell whether each available export payload's freshness labels, as-of dates, allowed excerpts, and source-use permissions are supported by the existing same-asset or same-comparison-pack evidence already present in the export, without adding frontend UI, live calls, new facts, new assets, or weakening citation, source-use, unknown/stale/unavailable/partial, and safety rules.

Completed:

- Added export validation contract models in `backend/models.py`, including `ExportValidationOutcome`, `ExportValidationBindingScope`, `ExportValidationCitationBinding`, `ExportValidationSourceBinding`, `ExportValidationDiagnostics`, `ExportValidation`, and additive `export_validation` support on `ExportResponse`.
- Extended `backend/export.py` so asset-page, source-list, comparison, and chat transcript exports serialize deterministic `export-validation-v1` metadata with section validations, same-asset and same-comparison-pack binding checks, no-factual-evidence handling for advice redirects, limitation messaging, and diagnostics derived from existing overview/comparison/chat contracts only.
- Preserved existing export payload behavior while validating current evidence boundaries, including the stale-with-limitations `VOO` `cost_trading_context` export path instead of promoting it to a cleaner freshness state.
- Added `evals/export_eval_cases.yaml` and extended `evals/run_static_evals.py` for supported `AAPL`, `VOO`, and `QQQ` export cases, `VOO` freshness-limitation preservation, comparison-pack-only bindings for `VOO`/`QQQ` in both directions, advice-redirect chat exports with `no_factual_evidence`, blocked-state handling, and no live-call or secret-exposure regressions.
- Extended `tests/unit/test_exports.py` and `tests/integration/test_backend_api.py` for asset-page, source-list, comparison, grounded-chat, advice-redirect chat, and blocked export serialization, binding-scope coverage, and deterministic diagnostics.
- Added `docs/agent-journal/20260423T155943Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- The agent journal records that these commands passed:
  - `python3 -m pytest tests/unit/test_exports.py tests/unit/test_safety_guardrails.py -q`
  - `python3 -m pytest tests/integration/test_backend_api.py -q`
  - `python3 -m pytest tests -q`
  - `npm test`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
- Merged local branch: `agent/T-044-20260423T155943Z`.
- Remaining documented risk: the export validation contract is deterministic and fixture-backed only; it validates existing export citations, freshness labels, source-use rights, and blocked states without adding live evidence, new facts, or new export routes.
- Remaining documented risk: asset-page freshness preservation relies on the current overview freshness-validation contract for matched overview sections and export-local metadata for export-only sections, so future fixture changes need to preserve the same same-asset binding assumptions.
- Remaining documented risk: comparison export validation stays limited to the current local comparison packs and prevents non-pack bindings by diagnostics and tests; future comparison fixtures will need to preserve the same comparison-pack-only guarantees.

Completion commits:

- `4866c0a feat(T-044): add export source-use and freshness validation contract`
- `ec7f295 chore(T-044): merge export source-use and freshness validation contract`

### T-043: Add section-level freshness validation contract

Goal:
Add a deterministic section-level freshness validation contract so backend and UI clients can tell whether each generated overview section's displayed freshness label is supported by the selected asset's existing same-asset evidence, dates, and knowledge-pack freshness inputs, without adding frontend UI, live calls, new facts, new assets, or weakening citation, source-use, unknown/stale/unavailable/partial, and safety rules.

Completed:

- Added additive overview freshness-validation models in `backend/models.py`, including `OverviewSectionFreshnessValidationOutcome`, `OverviewSectionFreshnessCitationBinding`, `OverviewSectionFreshnessSourceBinding`, `OverviewSectionFreshnessDiagnostics`, and `OverviewSectionFreshnessValidation`, plus `section_freshness_validation` on `OverviewResponse`.
- Extended `backend/overview.py` so generated supported overviews now build deterministic section freshness validation records for overview sections, `weekly_news_focus`, and `ai_comprehensive_analysis` by reusing existing same-asset citations, source documents, and knowledge-pack section freshness inputs.
- Kept validation evidence-bound by recording displayed vs validated freshness/as-of metadata, same-asset citation/source bindings, matched knowledge-pack section IDs, missing-binding diagnostics, and mismatch reasons when a displayed label is not supported by the existing local evidence.
- Preserved non-generated routing by returning no section freshness validation records for unsupported or unknown assets, and preserved existing stale/limited states such as `VOO` `cost_trading_context` instead of promoting them to `fresh`.
- Extended `evals/run_static_evals.py` for required freshness-validation models/helpers, route behavior, same-asset binding, stale/unknown/unavailable handling, no live-call imports, and advice-boundary checks.
- Extended `tests/unit/test_overview_generation.py` and `tests/integration/test_backend_api.py` for supported stock and ETF serialization, same-asset binding coverage, recent-context separation, stale `VOO` cost/trading validation, mismatch detection, and blocked-state behavior.
- Added `docs/agent-journal/20260423T152949Z.md` documenting the changed files, commands run, pass/fail status, and remaining risks.
- The agent journal records that these commands passed:
  - `python3 -m pytest tests/unit/test_cache_contracts.py tests/unit/test_overview_generation.py tests/unit/test_safety_guardrails.py -q`
  - `python3 -m pytest tests/integration/test_backend_api.py -q`
  - `python3 -m pytest tests -q`
  - `python3 evals/run_static_evals.py`
  - `bash scripts/run_quality_gate.sh`
- Merged local branch: `agent/T-043-20260423T152949Z`.
- Remaining documented risk: the section freshness validation contract is deterministic and fixture-backed only; it validates existing overview freshness labels and bindings but does not add live freshness sources, new facts, or new assets.
- Remaining documented risk: Weekly News Focus and AI Comprehensive Analysis validation currently reflects the existing local no-high-signal and insufficient-evidence fixture states; future timely-context fixtures must preserve the same same-asset binding and mismatch checks.

Completion commits:

- `a55fe1f feat(T-043): add section-level freshness validation contract`
- `bdcc9c8 chore(T-043): merge section-level freshness validation contract`

### T-042: Add unsupported asset search explanation contract

Goal:
Add a deterministic unsupported-asset search explanation contract so search clients can show a clear structured explanation for recognized unsupported and out-of-scope search matches, including why the asset is blocked, which capabilities stay disabled, and what the supported MVP scope is, without adding frontend UI, live calls, new asset coverage, or weakening classification, citation, source-use, freshness, unknown/unavailable/partial, and safety rules.

Completed:

- Added additive blocked-search explanation contract models in `backend/models.py`, including `SearchBlockedCapabilityFlags`, `SearchBlockedExplanationDiagnostics`, and `SearchBlockedExplanation`, plus `blocked_explanation` fields on `SearchResult` and `SearchState`.
- Updated `backend/search.py` so single-result recognized unsupported and out-of-scope matches attach deterministic `search-blocked-explanation-v1` metadata with explanation category, scope rationale, supported-v1 scope reminder, blocked capability flags, and no-ingestion diagnostics while preserving existing supported, ambiguous, eligible-not-cached, and unknown behavior.
- Kept blocked explanations scope-bound and non-analytical by deriving them from existing deterministic unsupported-category metadata and Top-500 manifest-backed out-of-scope stock handling rather than adding citations, source text, freshness claims, or new asset facts.
- Added `evals/search_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required models/helpers, blocked explanation coverage for unsupported and out-of-scope results, preservation of unknown and eligible-not-cached behavior, no live-call imports, and no forbidden advice language.
- Extended `tests/unit/test_search_classification.py`, `tests/unit/test_safety_guardrails.py`, and `tests/integration/test_backend_api.py` for blocked explanation serialization, API coverage, supported/ambiguous/eligible-not-cached preservation, and safety checks.
- Added `docs/agent-journal/20260423T150352Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-042 agent journal records that focused search/safety pytest passed with 19 tests, backend API pytest passed with 30 tests, full Python pytest passed with 190 tests, `npm test` passed with frontend smoke checks, static evals passed, and the full quality gate passed.
- Merged local branch: `agent/T-042-20260423T150352Z`.
- Remaining documented risk: the blocked search explanation is deterministic product-state metadata only; it does not add citations, freshness, source text, live calls, or any new asset coverage.
- Remaining documented risk: the contract currently covers recognized unsupported assets and manifest-backed out-of-scope stocks in local fixtures; future broader search datasets will need to preserve the same blocked-capability and no-advice guarantees.

Completion commits:

- `bcef2b4 feat(T-042): add unsupported asset search explanation contract`
- `bc75dce chore(T-042): merge unsupported asset search explanation contract`

### T-041: Add glossary asset-context evidence contract

Goal:
Add a deterministic backend glossary asset-context evidence contract so UI clients can request beginner glossary terms for a selected asset and see which optional asset-specific glossary context is source-backed, generic-only, unavailable, stale, partial, or suppressed without adding frontend UI, live calls, new facts, generated unsupported content, or weakening citation, source-use, freshness, unknown/unavailable/partial, and safety rules.

Completed:

- Added `backend/glossary.py` with a deterministic `glossary-asset-context-v1` response builder, a backend-owned curated term catalog, and asset-aware term coverage for stock terms such as `market cap`, `revenue`, `operating margin`, `EPS`, `free cash flow`, `debt`, `P/E ratio`, and `forward P/E`, plus ETF terms such as `expense ratio`, `AUM`, `benchmark`, `holdings`, `tracking error`, and `tracking difference`.
- Added glossary response and asset-context contract models in `backend/models.py` so term identity, generic definition fields, asset-context availability state, evidence metadata, and diagnostics serialize through a stable backend schema.
- Wired `GET /api/assets/{ticker}/glossary` in `backend/main.py` with optional `term` filtering.
- Implemented deterministic generic-only and source-backed glossary behavior in `backend/glossary.py`, including same-asset citation/source binding, preserved unavailable or insufficient-evidence states, and non-generated states for `eligible_not_cached`, `unsupported`, `out_of_scope`, and `unknown` assets.
- Added `evals/glossary_context_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required glossary models/helpers, curated term coverage, same-asset citation/source binding, generic-only behavior, non-generated blocked states, no restricted text exposure, no live-call imports, and no forbidden advice language.
- Added `tests/unit/test_glossary_context.py` and updated retrieval, citation, safety, and backend API coverage in `tests/unit/test_retrieval_fixtures.py`, `tests/unit/test_citation_validation.py`, `tests/unit/test_safety_guardrails.py`, and `tests/integration/test_backend_api.py` for supported `AAPL`, `VOO`, and `QQQ` glossary serialization, optional term filtering, generic-only terms, and blocked states for `SPY`, `TQQQ`, `GME`, and `ZZZZ`.
- Added `docs/agent-journal/20260423T143641Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-041 agent journal records that focused glossary/retrieval/citation/safety pytest passed with 36 tests, backend API pytest passed with 30 tests, full Python pytest passed with 189 tests, static evals passed, `npm test` and `npm run typecheck` passed, and the full quality gate passed.
- Merged local branch: `agent/T-041-20260423T143641Z`.
- Remaining documented risk: glossary asset-context is deterministic and fixture-backed only; it does not add live ingestion, scraping, persistence, frontend rendering, or new asset facts.
- Remaining documented risk: asset-specific glossary context exposes evidence metadata and bindings, not new explanatory prose or raw source passages.
- Remaining documented risk: future persisted glossary context will need to preserve the same same-asset citation/source binding and source-use policy checks.

Completion commits:

- `b61747e feat(T-041): add glossary asset-context evidence contract`
- `046b05f chore(T-041): merge glossary asset-context evidence contract`

### T-040: Add comparison evidence availability contract

Goal:
Add a deterministic backend comparison evidence availability contract so comparison UI clients can tell which comparison dimensions are source-backed, partial, stale, unavailable, or suppressed for each side of a comparison without adding frontend UI, making live calls, generating unsupported comparisons, or weakening citation, source-use, freshness, unknown/unavailable/partial, and safety rules.

Completed:

- Added comparison evidence availability contract models in `backend/models.py`, including availability states, side roles, diagnostics, source references, evidence items, dimensions, citation bindings, claim bindings, and the top-level `ComparisonEvidenceAvailability`.
- Extended `CompareResponse` with additive `evidence_availability` metadata while preserving the existing `left_asset`, `right_asset`, `state`, `comparison_type`, `key_differences`, `bottom_line_for_beginners`, `citations`, and `source_documents` response shape.
- Added deterministic availability helpers in `backend/comparison.py`, including required comparison dimensions for `Benchmark`, `Expense ratio`, `Holdings count`, `Breadth`, and `Educational role`.
- Supported existing local `VOO` vs `QQQ` and `QQQ` vs `VOO` comparison packs with `available` metadata, per-side evidence roles, dimension-to-citation/source mappings, claim bindings, source references, freshness/source-use metadata, and no-live-call/no-new-generated-output diagnostics.
- Added explicit non-generated evidence availability states for unsupported, out-of-scope, unknown, eligible-not-cached, no-local-pack, unavailable-style comparisons, with no generated key differences, beginner bottom line, citations, source documents, claim support, or live calls.
- Preserved same-comparison-pack citation/source binding by requiring availability citation bindings to reference citations and source documents already present in the selected `CompareResponse`.
- Preserved source-use policy by resolving source permissions and only marking allowed, citation-supporting, generated-output-supporting sources as supporting generated comparison claims; restricted text is not newly exposed.
- Added `evals/comparison_evidence_eval_cases.yaml` and extended `evals/run_static_evals.py` for required models/helpers, supported and non-generated states, required dimensions, citation/source binding, source-use/freshness handling, no restricted markers, no live-call imports, and no forbidden advice language.
- Extended `tests/unit/test_comparison_generation.py` and `tests/integration/test_backend_api.py` for supported availability serialization, reverse ticker order, per-side roles, dimension and claim bindings, non-generated states for `BTC`, `TQQQ`, `GME`, `SPY`, `ZZZZ`, and `AAPL`/`VOO`, and API serialization.
- Added `docs/agent-journal/20260423T140420Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-040 agent journal records that focused comparison/citation/safety pytest passed with 26 tests, backend API pytest passed with 29 tests, full Python pytest passed with 178 tests, static evals passed, and the full quality gate passed.
- Merged local branch: `agent/T-040-20260423T140420Z`.
- Remaining documented risk: the comparison evidence availability contract is deterministic and fixture-backed only; it does not add live ingestion, scraping, provider calls, persistence, frontend rendering, or new comparison pairs.
- Remaining documented risk: stale, partial, unavailable, and insufficient-evidence states are modeled in the contract for deterministic response shaping, but current local comparison fixtures only exercise available and non-generated unavailable-style routes.
- Remaining documented risk: future persisted comparison packs will need to preserve the same same-pack citation/source binding rules and source-use policy fields.

Completion commits:

- `7b305ea feat(T-040): add comparison evidence availability contract`
- `58c5f63 chore(T-040): merge comparison evidence availability contract`

### T-039: Add asset source drawer response contract

Goal:
Add a deterministic backend asset source drawer response contract so UI clients can open a source drawer for an asset or citation and receive source metadata, related claim context, freshness, source-use rights, and allowed excerpts without exposing restricted raw text, adding frontend UI, making live calls, or weakening citation, source-use, freshness, unknown/unavailable/partial, and safety rules.

Completed:

- Added source drawer contract models in `backend/models.py`, including `SourceDrawerState`, `SourceDrawerExcerpt`, `SourceDrawerRelatedClaim`, `SourceDrawerSectionReference`, `SourceDrawerCitationBinding`, `SourceDrawerSourceGroup`, and `SourceDrawerDiagnostics`.
- Extended `SourcesResponse` with additive source drawer fields while preserving the legacy `asset`, `state`, and `sources` response shape.
- Added `backend/sources.py` with `build_asset_source_drawer_response`, deterministic `asset-source-drawer-v1` shaping, and explicit non-generated responses for unavailable asset states.
- Built source drawer related-claim and section-reference context from existing overview claims, snapshot metrics, top risks, PRD overview sections, Weekly News Focus items, and AI Comprehensive Analysis sections when present.
- Built citation bindings from existing overview citations and asset knowledge-pack facts, chunks, and recent-development evidence, with same-asset source document checks and evidence-layer labels for canonical facts, source chunks, and timely context.
- Built source groups from existing overview and knowledge-pack source documents with source type, title, publisher, URL, published/as-of/retrieved dates, freshness, official-source flag, source quality, allowlist status, source-use policy, permitted operations, citation IDs, related claim IDs, section IDs, allowed excerpts, and excerpt-suppression reasons.
- Added deterministic filtering for `citation_id` and `source_document_id`, including diagnostics for applied filters and omitted citation/source IDs.
- Gated source drawer excerpts through the existing source-use policy resolver so `full_text_allowed` and `summary_allowed` sources can expose short allowed fixture passages while restricted policies suppress source text with explicit suppression reasons.
- Wired `GET /api/assets/{ticker}/sources` in `backend/main.py` to return the new source drawer contract and accept optional `citation_id` and `source_document_id` query filters.
- Added `evals/source_drawer_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required models/helpers/routes, supported cached assets, non-generated cases, same-asset source/citation binding, source-use/freshness handling, no restricted markers, no live-call imports, and no forbidden advice language.
- Added `tests/unit/test_source_drawer.py` plus API coverage in `tests/integration/test_backend_api.py` for supported `AAPL`, `VOO`, and `QQQ` source drawer serialization, citation/source filtering, related-claim mapping, source-use excerpt behavior, and non-generated `SPY`, `TQQQ`, `GME`, and `ZZZZ` states.
- Added `docs/agent-journal/20260423T133237Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-039 agent journal records that focused source-drawer pytest passed with 4 tests, focused source-drawer/citation/safety pytest passed with 21 tests, backend API pytest passed with 29 tests, full Python pytest passed with 178 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-039-20260423T133237Z`.
- Remaining documented risk: the source drawer contract is deterministic and fixture-backed only; it does not add live ingestion, persistence, scraping, source allowlist changes, or frontend rendering.
- Remaining documented risk: the contract groups and filters source drawer metadata from existing asset overviews and knowledge packs only, so future persisted claim/source tables may need an adapter to preserve the same response shape.
- Remaining documented risk: non-generated states return explicit empty drawer payloads, but richer deleted/stale/partial production states will still depend on future storage and ingestion lifecycle work.

Completion commits:

- `f84ddcc feat(T-039): add asset source drawer response contract`
- `94943ba chore(T-039): merge asset source drawer response contract`

### T-038: Add accountless chat session lifecycle contract

Goal:
Add a deterministic accountless chat session lifecycle contract so grounded chat can issue anonymous conversation IDs, record safe turn metadata, expose TTL/delete/session status, and support transcript export without adding user accounts, persistent storage, raw transcript analytics, live LLM/provider calls, or weakening citation, source-use, freshness, unknown/unavailable/partial, and safety rules.

Completed:

- Added `backend/chat_sessions.py` with a deterministic in-memory `ChatSessionStore`, injectable clock and ID generator, `CHAT_SESSION_TTL_DAYS = 7`, `CHAT_SESSION_TTL_SECONDS = 604800`, opaque deterministic UUID-style conversation IDs, active/expired/deleted/ticker-mismatch/unavailable lifecycle handling, idempotent deletion, and safe export payload helpers.
- Added chat session lifecycle models in `backend/models.py`, including `ChatSessionLifecycleState`, `ChatSessionDeletionStatus`, `ChatTurnRecord`, `ChatSessionTurnSummary`, `ChatSessionPublicMetadata`, `ChatSessionStatusResponse`, and `ChatSessionDeleteResponse`.
- Extended chat request/response contracts so `ChatRequest` accepts optional `conversation_id` and `ChatResponse` can return additive safe session metadata without changing the existing deterministic grounded chat answer fields.
- Wired `POST /api/assets/{ticker}/chat` through `answer_chat_with_session` so supported cached assets can create sessions when `conversation_id` is omitted, append turns for active same-ticker sessions, and return no generated chat answer for expired, deleted, unavailable, or ticker-mismatched sessions.
- Added deterministic chat session routes in `backend/main.py`: `GET /api/chat-sessions/{conversation_id}`, `POST /api/chat-sessions/{conversation_id}/delete`, and `GET /api/chat-sessions/{conversation_id}/export`.
- Extended chat transcript export in `backend/export.py` so stored session transcript exports include safe session metadata, display-ready turn answers, citations, source metadata, freshness/source-use information, uncertainty labels, and the educational disclaimer while deleted or unavailable sessions return minimal unavailable export states.
- Preserved the existing single-turn chat export path, including the documented fallback where client-submitted question export can still work when no stored session is found.
- Added `evals/chat_session_eval_cases.yaml` and extended `evals/run_static_evals.py` for TTL constants, lifecycle states, required models/helpers/routes, no account/auth/cookie/analytics/live-call imports, no restricted storage markers, source-use/freshness metadata, and advice-boundary safety.
- Added `tests/unit/test_chat_sessions.py` plus focused updates to chat generation, safety guardrail, and backend API tests for session creation, continuation, expiry, deletion, ticker mismatch, unsupported-session blocking, advice redirects, source-policy preservation, transcript export, and API serialization.
- Added `docs/agent-journal/20260423T130125Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-038 agent journal records that focused chat-session/chat-generation/safety pytest passed with 26 tests, backend API pytest passed with 29 tests, full Python pytest passed with 174 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-038-20260423T130125Z`.
- Remaining documented risk: session storage is an in-memory deterministic contract only; it does not add database persistence, distributed cleanup, cross-process sharing, or production rate limiting.
- Remaining documented risk: accountless conversation IDs and timestamps are deterministic for local contract behavior; production entropy and real clock wiring can be swapped through the existing injection points.
- Remaining documented risk: stored session transcript export intentionally omits submitted question text from stored session turns; the existing single-turn export shape still supports client-submitted question export when no stored session is found.

Completion commits:

- `5395cb8 feat(T-038): add accountless chat session lifecycle contract`
- `79ef9ea chore(T-038): merge accountless chat session lifecycle contract`

### T-037: Add LLM provider orchestration and live-generation gating contract

Goal:
Add a deterministic LLM provider orchestration and live-generation gating contract so generated-output attempts, validation, model fallback metadata, cache eligibility, and public reasoning summaries are modeled without making live LLM calls, exposing secrets, changing generated asset/chat/comparison output, or weakening citation, source-use, freshness, and safety rules.

Completed:

- Added `backend/llm.py` with pure deterministic orchestration helpers for mock default behavior, sanitized OpenRouter gate metadata, generation-attempt metadata, validation-before-cache decisions, fallback decisions, and runtime diagnostics without live provider calls.
- Added LLM runtime, provider, model-chain, live-gate, generation request/attempt, validation, fallback, public metadata, and cache-eligibility contract models in `backend/models.py`.
- Extended `backend/cache.py` with cache eligibility metadata for validated generated-output contracts.
- Added a diagnostics-only `GET /api/llm/runtime` route in `backend/main.py` that exposes sanitized runtime metadata only.
- Added `evals/llm_provider_eval_cases.yaml` and extended `evals/provider_eval_cases.yaml` and `evals/run_static_evals.py` for model-chain order, live-gate behavior, sanitized public metadata, no secret exposure, no live-call imports, validation-before-cache behavior, no raw prompt/reasoning/source-text exposure, and no advice-like generated language.
- Added `tests/unit/test_llm_provider.py` for mock default behavior, OpenRouter disabled/enabled gate metadata from sanitized config, fallback decision metadata, validation rejection cases, cache eligibility, no secret/raw prompt/raw reasoning/source-text exposure, and no live-call imports.
- Extended safety and backend API tests for provider diagnostics serialization and safety guardrails.
- Added `docs/agent-journal/20260423T123524Z.md` documenting changed files, commands run, pass/fail status, an initial focused-test failure, final passing results, and remaining risks.
- T-037 agent journal records that the first focused pytest run failed with two test-scan issues around the literal OpenRouter model name and a validator marker phrase; the focused checks/marker were revised without changing runtime behavior.
- T-037 agent journal records that focused LLM/cache/citation/safety pytest passed with 40 tests, backend API pytest passed with 28 tests, full Python pytest passed with 163 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-037-20260423T123524Z`.
- Remaining documented risk: this is a deterministic contract and metadata layer only; it does not implement live OpenRouter calls or replace existing generated asset, chat, comparison, export, Weekly News Focus, or AI Comprehensive Analysis output.
- Remaining documented risk: live-provider enablement still requires separate server-side configuration wiring, provider-call implementation, licensing/cost review, and validation around any future network path.
- Remaining documented risk: cache eligibility is modeled and test-covered, but no persistent cache store or generated-summary persistence was added in this task.

Completion commits:

- `d9c6fd9 feat(T-037): add LLM provider orchestration and live-generation gating contract`
- `2f63449 chore(T-037): merge LLM provider orchestration and live-generation gating contract`

### T-036: Add Weekly News Focus and AI Comprehensive Analysis contracts

Goal:
Add deterministic Weekly News Focus and AI Comprehensive Analysis contracts so timely context is modeled, validated, cited, and kept separate from stable canonical facts, without adding live news/provider/market/LLM calls, new generated asset pages, or prediction/recommendation language.

Completed:

- Added `backend/weekly_news.py` with deterministic Weekly News Focus window calculation, candidate selection, source-priority scoring, exclusion rationale, deduplication metadata, empty/no-high-signal states, and AI Comprehensive Analysis construction/validation.
- Added Weekly News Focus and AI Comprehensive Analysis contract models in `backend/models.py`, including market-week periods, event types, contract states, source metadata, selected items, selection rationale, empty states, analysis sections, and the combined weekly-news response.
- Wired deterministic Weekly News Focus and AI Comprehensive Analysis into overview generation and the asset knowledge-pack section metadata while preserving stable canonical facts as separate overview sections.
- Added `GET /api/assets/{ticker}/weekly-news` in `backend/main.py` to return the selected asset's Weekly News Focus and AI Comprehensive Analysis contract data from the existing deterministic overview path.
- Updated exports so asset-page exports include separate Weekly News Focus and AI Comprehensive Analysis sections with citation IDs, source document IDs, freshness/as-of metadata, suppression messaging, and no hidden prompts or restricted raw text.
- Added `evals/weekly_news_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify market-week window logic, contract models, fixture empty states, AI analysis suppression, stable/recent separation, no live-call imports, and no advice-like analysis language.
- Added `tests/unit/test_weekly_news.py` for explicit Eastern as-of window behavior, fixture empty states without padding, official-source priority, disallowed/duplicate/promotional/irrelevant/wrong-asset exclusion, AI analysis threshold, required section order, and no live network imports.
- Extended retrieval, overview, export, and backend API tests for weekly-news section metadata, overview serialization, export serialization, and API response coverage.
- Added `docs/agent-journal/20260423T120556Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-036 agent journal records that focused weekly-news pytest passed with 5 tests, focused retrieval/overview/export/API pytest passed with 52 tests, the required focused task pytest passed with 53 tests, backend API pytest passed with 27 tests, full Python pytest passed with 152 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-036-20260423T120556Z`.
- Remaining documented risk: this is a deterministic contract and fixture-selection layer only; it does not add live news, SEC, issuer-site, market-data, or LLM calls.
- Remaining documented risk: existing cached local packs still produce empty/no-high-signal Weekly News Focus states, so the available AI Comprehensive Analysis path is covered by contract tests with deterministic candidates rather than by a persisted asset fixture.
- Remaining documented risk: Weekly News Focus candidate examples remain local and synthetic; future live or scraped sources still require allowlist, source-use, licensing, caching, and export review before use.

Completion commits:

- `9be562d feat(T-036): add Weekly News Focus and AI Comprehensive Analysis contracts`
- `dbf9865 chore(T-036): merge Weekly News Focus and AI Comprehensive Analysis contracts`

### T-035: Add source allowlist and rights-tiered raw text policy contract

Goal:
Add a deterministic source allowlist and rights-tiered raw text policy contract so source ingestion, retrieval metadata, citation resolution, exports, provider fixtures, and future Weekly News Focus work can validate source-use rights before storage, summarization, rendering, caching, or export, without adding live provider/news/market/LLM calls or changing generated learning output.

Completed:

- Added `config/source_allowlist.yaml` with a versioned local source-use policy registry for fixture and mock-provider sources, including required policy tiers, source type, source quality, allowlist status, operation permissions, allowed excerpt behavior, rationale, and review metadata.
- Added `backend/source_policy.py` with deterministic allowlist loading, validation, fixture/domain resolution, and explicit allowed/rejected/pending-review/not-allowlisted decisions without network calls.
- Added source-policy and allowlist models in `backend/models.py`, including `SourceUsePolicy`, `SourceAllowlistStatus`, `SourceQuality`, `SourceOperationPermissions`, `SourceAllowedExcerptBehavior`, allowlist record/config models, and source-policy decision models.
- Threaded source-use policy and allowlist status through deterministic retrieval, provider, citation, overview, comparison, chat, export, and cache metadata surfaces where source metadata is exposed.
- Updated `data/retrieval_fixtures.json` so existing SEC, ETF issuer, local fixture, provider, and recent-context sources carry explicit policy metadata while preserving current generated learning output.
- Updated citation validation so disallowed source-policy states cannot support generated claims.
- Updated export behavior so source-list and generated-output exports respect metadata, excerpt, and full-text operation permissions and do not expose restricted raw payloads.
- Added `evals/source_policy_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify allowlist path/schema, required tiers, official and fixture records, rejected/unrecognized source blocking, rights-tier operation flags, provider licensing consistency, no live-call imports, and no advice-like policy language.
- Extended provider eval cases for source-use and licensing consistency.
- Added `tests/unit/test_source_policy.py` for policy loading, validation, resolution, operation permissions, rejected/unrecognized sources, and no-network behavior.
- Extended retrieval, citation, export, provider, and backend API tests for source-policy metadata, disallowed evidence rejection, allowed-excerpt behavior, provider fixture policy consistency, and API serialization.
- Added `docs/agent-journal/20260423T064752Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-035 agent journal records that the first focused test run failed because PyYAML parsed unquoted allowlist dates into date/datetime values while the Pydantic contract expected strings; a focused `backend/models.py` revision normalized those YAML scalar types before validation.
- T-035 agent journal records that focused source-policy/retrieval/citation/export/provider pytest passed with 34 tests, backend API pytest passed with 27 tests, full Python pytest passed with 147 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-035-20260423T064752Z`.
- Remaining documented risk: this is a deterministic policy contract and fixture metadata layer only; it does not implement live ingestion, Weekly News Focus fetching, or provider licensing review.
- Remaining documented risk: restricted provider and recent-context handling are validated against local fixtures and mocks only.
- Remaining documented risk: future allowlist updates still need coordinated config, validation tests, and development-log rationale to preserve source-use governance.

Completion commits:

- `d73b51a feat(T-035): add source allowlist and rights-tiered raw text policy contract`
- `a65feae chore(T-035): merge source allowlist and rights-tiered raw text policy contract`

### T-034: Add Top-500 stock universe manifest contract

Goal:
Add a deterministic Top-500 U.S.-listed common stock universe manifest contract so stock support scope is driven by a versioned local manifest instead of live provider queries, without adding live market/reference calls, changing generated asset pages, or treating the manifest as an endorsement, recommendation, portfolio, or ranking surface.

Completed:

- Added `data/universes/us_common_stocks_top500.current.json` with schema version `top500-us-common-stock-universe-v1`, runtime path metadata, production mirror env-var metadata, monthly refresh cadence, snapshot/provenance/checksum fields, non-advice policy language, and deterministic launch stock entries for `AAPL`, `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `BRK.B`, `JPM`, and `UNH`.
- Added Top-500 manifest models in `backend/models.py`, including entry and manifest fields for ticker, name, stock/security type, CIK, exchange, rank, rank basis, source provenance, snapshot date, checksum input/checksum, approval timestamp, launch group, and aliases.
- Added deterministic manifest loading and validation helpers in `backend/data.py`, including runtime path validation, `TOP500_UNIVERSE_MANIFEST_URI` metadata validation, stock-only/security-type checks, rank and ticker uniqueness checks, checksum-field checks, snapshot-date consistency, no-advice-language checks, and lookup helpers.
- Rebuilt eligible-not-cached stock metadata from the manifest so cached `AAPL` remains generated from its local pack while `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `BRK.B`, `JPM`, and `UNH` become manifest-backed eligible-not-cached stocks.
- Added `OUT_OF_SCOPE_COMMON_STOCKS` handling for a recognized common stock outside the manifest, including `GME`, so search, ingestion, pre-cache, and provider fixtures return out-of-scope non-generated states rather than treating it as eligible-not-cached.
- Updated `backend/search.py`, `backend/ingestion.py`, and `backend/providers.py` so manifest-backed eligible-not-cached stocks expose ingestion/pre-cache/provider fixture states without generated pages, chat answers, comparisons, citations, source documents, or risk summaries.
- Extended `evals/search_eval_cases.yaml`, `evals/ingestion_eval_cases.yaml`, `evals/provider_eval_cases.yaml`, and `evals/run_static_evals.py` to verify the manifest path/schema/fields, required stock membership, cached versus eligible-not-cached boundaries, out-of-scope stock behavior, no generated output for non-cached stocks, no live provider imports, and no advice-like manifest language.
- Extended `tests/unit/test_search_classification.py`, `tests/unit/test_ingestion_jobs.py`, `tests/unit/test_provider_adapters.py`, and `tests/integration/test_backend_api.py` for manifest-backed classification, ingestion/pre-cache routing, provider mock states, API serialization, and out-of-scope common-stock behavior.
- Added `docs/agent-journal/20260423T061610Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-034 agent journal records that focused search/ingestion/provider pytest passed with 28 tests, backend API pytest passed with 27 tests, full Python pytest passed with 143 tests, static evals passed, and the full quality gate passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-034-20260423T061610Z`.
- Remaining documented risk: the manifest is a deterministic contract fixture for the current launch stock set, not a live refreshed 500-entry universe.
- Remaining documented risk: manifest rank is operational coverage metadata only; future refreshes must preserve the non-advice framing and checksum/provenance fields.
- Remaining documented risk: no generated pages, source evidence, citations, chat answers, comparisons, or risk summaries were added for manifest-backed eligible-not-cached stocks.

Completion commits:

- `cb1bda5 feat(T-034): add Top-500 stock universe manifest contract`
- `73c0153 chore(T-034): merge Top-500 stock universe manifest contract`

### T-033: Rebase agent instructions and local environment to updated PRD/TDS

Goal:
Rebaseline the project control plane, local agent-loop environment, and frontend workspace layout around the updated proposal, PRD, and technical design spec without rolling back the user's documentation changes, changing product behavior, adding live provider calls, or exposing secrets.

Completed:

- Updated `AGENTS.md`, `SPEC.md`, `EVALS.md`, `TASKS.md`, and `.github/codex/prompts/review.md` around the updated PRD/TDS/proposal authority order, Top-500-first MVP scope, Weekly News Focus and AI Comprehensive Analysis separation, source-use rights, OpenRouter/live-provider gating, secret handling, and `apps/web` frontend root.
- Moved the Next.js frontend into `apps/web` with 100% file renames for the `app`, `components`, `lib`, styles, Next config, and TypeScript config files.
- Added root npm workspace delegation so `npm run dev`, `npm run build`, `npm run start`, and `npm run typecheck` delegate to `apps/web`, while `npm test` continues to run frontend smoke checks from the repo root.
- Added `apps/web/package.json` with local Next.js dev/build/start/typecheck scripts and updated `package-lock.json` for the workspace layout.
- Updated frontend smoke and safety tests so path-sensitive checks read frontend files from `apps/web`.
- Updated Bash and PowerShell agent-loop and quality-gate scripts so prompts read the proposal, PRD, TDS, SPEC, TASKS, and EVALS with PRD/TDS-first authority after safety.
- Added placeholder-only local environment examples in `.env.example`, `apps/web/.env.example`, and `deploy/env/*.example.env` without real secret values or browser-exposed provider keys.
- Added local-only Docker Compose scaffolding for web, API, ingestion-worker placeholder, Postgres/pgvector, Redis, and MinIO-compatible object storage, plus web/API Dockerfiles.
- Normalized the updated PRD, technical design spec, and proposal docs to LF line endings so `git diff --check` passes.
- Verified the staged diff detected frontend moves as `R100` renames and found no P0/P1 review blockers before commit.
- Ran `python3 -m pytest tests/unit/test_repo_contract.py -q`: 9 tests passed.
- Ran `npm test`: frontend smoke checks passed.
- Ran `python3 -m pytest tests -q`: 140 tests passed.
- Ran `python3 evals/run_static_evals.py`: passed.
- Ran `npm run typecheck`: passed.
- Ran `npm run build`: passed.
- Ran `bash scripts/run_quality_gate.sh`: passed, including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Ran `docker compose config`: passed.
- Pushed `main` to `origin/main` with commit `2a3175f`.
- Remaining documented risk: Docker Compose was syntax-validated only; it was not used to build images or run the local stack end to end.
- Remaining documented risk: the workspace move did not add new frontend behavior; future UI tasks still need browser/mobile verification when they change rendered flows.
- Remaining documented risk: placeholder provider environment variables remain configuration readiness only; live provider behavior still requires separate licensing, caching, display, export, and validation work.

Completion commits:

- `2a3175f chore(T-033): rebase control plane for updated PRD/TDS`

### T-032: Add trust metrics event contract for MVP workflows

Goal:
Add a deterministic backend trust-metrics event contract so MVP workflows can validate and inspect privacy-preserving product/trust event payloads without adding real analytics, persistence, user tracking, live calls, or changes to generated learning output.

Completed:

- Added trust-metrics contract models in `backend/models.py`, including workflow areas, event types, metric kind, validation status, asset support states, output kinds, safety status, generated-output metadata, event, validated event, catalog, validation request/response, and summary response models.
- Added `backend/trust_metrics.py` with schema version `trust-metrics-event-v1`, deterministic default timestamp `1970-01-01T00:00:00Z`, a validation-only product/trust event catalog, and pure helpers for event validation, batch validation, and in-memory summarization.
- Product event catalog coverage includes search success, unsupported asset outcomes, asset-page views, comparison usage, source drawer usage, glossary usage, export usage, chat follow-up, chat answer outcomes, chat safety redirects, and latency-to-first-meaningful-result metadata.
- Trust event catalog coverage includes citation coverage, unsupported-claim drops, weak citation counts, generated-output validation failures, safety redirect rate, freshness accuracy, source retrieval failure, hallucination/unsupported-fact incidents, and stale data incidents.
- Validation normalizes asset tickers and infers support states for cached supported assets, eligible-not-cached assets, recognized unsupported assets, and unknown assets without implying generated output exists for non-generated states.
- Validation rejects privacy-sensitive or licensing-sensitive field names such as `raw_query`, `question`, `answer`, `source_passage`, `source_url`, `email`, `ip_address`, `user_agent`, `account_id`, `portfolio`, `allocation`, cookies, and external analytics identifiers.
- Validation rejects inconsistent metric payloads including generated-output availability for eligible-not-cached, unsupported, unknown, or unavailable assets; citation coverage outside `0..1`; negative counts or latency; source/citation IDs when no generated output exists; and freshness/retrieval/stale-data metrics without explicit freshness state.
- Generated-output metadata can carry compact validation metadata such as output kind, prompt version, model name, schema-valid flag, citation coverage rate, citation IDs, source document IDs, freshness hash/state, safety status, unsupported-claim count, weak-citation count, stale-source count, and latency, while raw generated text, retrieved text, source passages, URLs, prompts, and personal identifiers remain forbidden.
- Deterministic summarization aggregates accepted events only into event-type counts, workflow-area counts, product/trust metric counts, rates, and latency min/max/average without persistence, clock dependence, analytics services, or network calls.
- Added validation-only API routes in `backend/main.py`: `GET /api/trust-metrics/catalog` and `POST /api/trust-metrics/validate`; responses explicitly report validation-only behavior and do not store, forward, or enrich events from live services.
- Added `evals/trust_metrics_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required models, helpers, product/trust event coverage, forbidden fields, required routes, deterministic validation/summarization, and absence of persistence, analytics SDK, credential, environment, and live-network imports.
- Added `tests/unit/test_trust_metrics.py` for catalog coverage, anonymous metadata normalization, eligible-not-cached/unsupported/unknown state distinction, generated-output metadata acceptance, privacy/state rejection cases, and deterministic summarization.
- Extended `tests/integration/test_backend_api.py` for catalog/validation API serialization, accepted and rejected payloads, no-storage response flags, invalid generated-output states, and no mutation of existing overview/chat/comparison/export responses.
- Extended `tests/unit/test_safety_guardrails.py` so trust-metrics contract and API copy are scanned for forbidden advice-like language.
- Added `docs/agent-journal/20260422T203211Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-032 agent journal records that `git status --short`, focused trust metrics/API/safety pytest, full pytest, safety guardrail pytest, static evals, and the full quality gate passed.
- T-032 agent journal records focused trust metrics/API/safety pytest as 42 tests passed, full Python pytest as 136 tests passed, safety guardrail pytest as 7 tests passed, static evals as passed, and the full quality gate as passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-032-20260422T203211Z`.
- Remaining documented risk: this is a deterministic validation and summarization contract only; it does not emit analytics from frontend components, persist events, forward payloads, add an analytics SDK, or create a real metrics store.
- Remaining documented risk: accepted event payloads intentionally carry compact anonymous metadata only; future instrumentation must continue to reject raw questions, generated answers, source passages, source URLs, personal identifiers, cookies, portfolio/allocation details, and external analytics IDs.
- Remaining documented risk: aggregation is in-memory and count/rate based for contract validation; production observability would need separate privacy and licensing review before any storage or vendor integration is added.

Completion commits:

- `4e84de1 feat(T-032): add trust metrics event contract for MVP workflows`
- `3138655 chore(T-032): merge trust metrics event contract for MVP workflows`

### T-031: Add common comparison suggestions for supported assets

Goal:
Add deterministic common comparison suggestions for fixture-backed supported assets so beginners can discover available local comparisons and understand when comparison evidence is unavailable, without generating unsupported comparisons, adding new asset facts, or making live calls.

Completed:

- Added `lib/compareSuggestions.ts` with a deterministic comparison-suggestion model, `local_comparison_available`, `no_local_comparison_pack`, and `unavailable_with_fixture_examples` states, relative `/compare?left={left}&right={right}` URL construction, and local availability checks against the existing compare-page fixture.
- Kept the only actionable local comparison pair as `VOO`/`QQQ`: `VOO` suggests `QQQ`, `QQQ` suggests `VOO`, and `AAPL` receives an explicit no-local-comparison-pack state with no generated peer list or factual differences.
- Added `components/ComparisonSuggestions.tsx` with stable markers for suggestion scope, selected ticker, state, requested comparison tickers, target ticker, left/right tickers, compare URL, and no-local-pack state, plus accessible link labels that preserve educational non-advice framing.
- Wired comparison suggestions into `app/assets/[ticker]/page.tsx` for fixture-backed asset pages and into `app/compare/page.tsx` for supported and unavailable comparison states without changing the generated comparison output.
- Added responsive comparison-suggestion styling in `styles/globals.css`.
- Extended `tests/frontend/smoke.mjs` for the new comparison-suggestion component/helper markers, `VOO`/`QQQ` fixture pair coverage, unavailable-state copy, no-local-pack copy, and absence of live external comparison behavior from the suggestion UI.
- Extended `tests/unit/test_safety_guardrails.py` so comparison suggestion copy is scanned for forbidden advice-like language.
- Added `docs/agent-journal/20260422T200644Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-031 agent journal records that the initial `npm test` failed because a new smoke-test regex marker did not escape literal parentheses, then passed after one focused smoke-test assertion revision.
- T-031 agent journal records that `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, static evals, and the full quality gate passed.
- T-031 agent journal records safety guardrail pytest as 6 tests passed and the full quality gate as passed including 123 Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-031-20260422T200644Z`.
- Remaining documented risk: comparison suggestions remain deterministic frontend discovery only; no new comparison evidence, backend contract, retrieval pack, source fixture, generated output, export behavior, analytics, or live-call path was added.
- Remaining documented risk: `AAPL` and unavailable requested comparison states intentionally show no-local-pack or fixture-example messaging rather than generated peer lists or factual differences.
- Remaining documented risk: the only actionable local comparison suggestion remains the existing `VOO`/`QQQ` fixture-backed pair in either direction.

Completion commits:

- `5f7d041 feat(T-031): add common comparison suggestions for supported assets`
- `a2cb228 chore(T-031): merge common comparison suggestions for supported assets`

### T-030: Add frontend export controls for saved learning outputs

Goal:
Add deterministic frontend export controls so users can save fixture-backed asset-page output, asset source lists, comparison output, and chat transcripts through the existing export API contracts, while preserving citations, freshness labels, source metadata, educational disclaimers, licensing scope, unsupported/unavailable states, and no-live-call behavior.

Completed:

- Added reusable frontend export URL/request helpers in `lib/exportControls.ts` for asset-page, asset source-list, comparison, and chat transcript exports using relative local API paths.
- Added `components/ExportControls.tsx` with accessible link controls for GET exports and a deterministic POST/copy flow for chat transcript Markdown exports.
- Wired fixture-backed asset pages in `app/assets/[ticker]/page.tsx` so `AAPL`, `VOO`, and `QQQ` show asset-page and source-list export controls with citation, freshness, disclaimer, and licensing context.
- Wired supported `VOO`/`QQQ` and `QQQ`/`VOO` comparison pages in `app/compare/page.tsx` to show comparison export controls, while unavailable comparison states keep export controls hidden and preserve non-generated guardrail copy.
- Added chat transcript export controls in `components/AssetChatPanel.tsx` after a deterministic chat answer is returned, preserving educational redirect, unsupported/unknown, and insufficient-evidence states through the backend export contract.
- Added responsive export-control styling in `styles/globals.css`.
- Extended `tests/frontend/smoke.mjs` for export markers, relative API paths, no live external URLs, unavailable export states, package dependency shape, and backend export-route presence.
- Extended `tests/unit/test_safety_guardrails.py` for advice-safe export helper and component copy.
- Added `docs/agent-journal/20260422T193929Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-030 agent journal records that `git status --short`, `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, focused export/API pytest, static evals, and the full quality gate passed.
- T-030 agent journal records safety guardrail pytest as 5 tests passed, focused export/API pytest as 29 tests passed, static evals as passed, and the full quality gate as passed including 122 Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-030-20260422T193929Z`.
- Remaining documented risk: export controls open or prepare existing JSON/Markdown-style backend export payloads; this task does not add PDF generation, file storage, browser file naming, authentication, analytics, or persistence.
- Remaining documented risk: chat transcript export still depends on the local backend route being available at runtime; normal CI remains deterministic and uses no provider credentials or live external calls.
- Remaining documented risk: licensing copy is frontend trust-context UI only; final provider-specific redistribution rules still need review before paid or restricted provider content is exposed.

Completion commits:

- `982b1a2 feat(T-030): add frontend export controls for saved learning outputs`
- `fbc5484 chore(T-030): merge frontend export controls for saved learning outputs`

### T-029: Add deterministic asset knowledge-pack builder

Goal:
Add a deterministic asset knowledge-pack builder contract that makes the bounded evidence set for each local cached asset inspectable, freshness-hashable, and explicitly unavailable for eligible-not-cached, unsupported, and unknown assets without adding new source facts, generated output, live calls, or frontend UI.

Completed:

- Added knowledge-pack build contract models in `backend/models.py`: `KnowledgePackBuildState`, `KnowledgePackCounts`, `KnowledgePackSourceMetadata`, `KnowledgePackFactMetadata`, `KnowledgePackChunkMetadata`, `KnowledgePackRecentDevelopmentMetadata`, `KnowledgePackEvidenceGapMetadata`, and `KnowledgePackBuildResponse`.
- Added `build_asset_knowledge_pack_result` in `backend/retrieval.py` with schema version `asset-knowledge-pack-build-v1` and stable pack IDs such as `asset-knowledge-pack-aapl-local-fixture-v1`, `asset-knowledge-pack-voo-local-fixture-v1`, and `asset-knowledge-pack-qqq-local-fixture-v1`.
- Supported cached local assets `AAPL`, `VOO`, and `QQQ` now return available knowledge-pack metadata from existing local retrieval fixtures, including generated routes, generated-output availability, page/chat/comparison capability flags, page and section freshness labels, source-document IDs, derived citation IDs, counts, source checksums, cache keys, cache revalidation state, and deterministic knowledge-pack freshness hashes.
- Supported cached responses expose same-asset source, fact, chunk, recent-development, and evidence-gap metadata while intentionally omitting raw chunk text, supporting passages, and full source-document exports.
- Eligible-not-cached assets such as `SPY` return explicit non-generated `eligible_not_cached` knowledge-pack states with no sources, citations, normalized facts, chunks, recent developments, source checksums, freshness hash, generated route, page/chat/comparison capability, or reusable generated-output cache hit; only the ingestion-request capability is true for eligible-not-cached states.
- Unsupported assets such as `TQQQ` and unknown assets such as `ZZZZ` return explicit non-generated `unsupported` or `unknown` knowledge-pack states with no generated output, no source evidence, no citations, no freshness hash, and non-reusable cache revalidation results.
- Added the read-only API route `GET /api/assets/{ticker}/knowledge-pack` in `backend/main.py`, serializing the same deterministic response for supported cached, eligible-not-cached, unsupported, and unknown tickers.
- Preserved existing generated overview, chat, and comparison behavior by keeping existing `build_asset_knowledge_pack` and `build_comparison_knowledge_pack` callers compatible.
- Added `evals/knowledge_pack_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required models/helpers, stable pack IDs, supported cached coverage, eligible-not-cached and unsupported/unknown non-generation, source/citation absence for nonexistent packs, same-asset binding, freshness-hash determinism, no raw full-document export, API serialization, and forbidden live-call or credential imports scoped to retrieval.
- Added focused coverage in `tests/unit/test_retrieval_fixtures.py`, `tests/unit/test_cache_contracts.py`, `tests/unit/test_overview_generation.py`, `tests/unit/test_chat_generation.py`, `tests/unit/test_comparison_generation.py`, and `tests/integration/test_backend_api.py` for deterministic repeated builds, metadata-only supported responses, no generated output for non-cached states, freshness-hash integration, route serialization, and preservation of generated overview/chat/comparison outputs.
- Added `docs/agent-journal/20260422T191056Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-029 agent journal records that `git status --short`, focused retrieval/cache pytest, focused overview/chat/comparison pytest, backend API pytest, full pytest, static evals, and the full quality gate passed.
- T-029 agent journal records focused retrieval/cache pytest as 24 tests passed, focused overview/chat/comparison pytest as 27 tests passed, backend API integration pytest as 23 tests passed, full Python pytest as 121 tests passed, static evals as passed after one eval-only revision, and the full quality gate as passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-029-20260422T191056Z`.
- Remaining documented risk: the knowledge-pack builder is a deterministic read-only contract over existing local fixtures; it does not add ingestion workers, persistence, provider calls, source facts, LLM calls, frontend UI, or generated output for non-cached assets.
- Remaining documented risk: eligible-not-cached assets remain explicit non-generated states with no source evidence, citations, facts, chunks, recent developments, freshness hash, generated route, or reusable generated-output cache hit.
- Remaining documented risk: supported cached assets expose metadata and freshness hashes for existing `AAPL`, `VOO`, and `QQQ` fixture packs, but intentionally omit raw chunk text and full source-document passages.

Completion commits:

- `bfeba12 feat(T-029): add deterministic asset knowledge-pack builder`
- `5ac1597 chore(T-029): merge deterministic asset knowledge-pack builder`

### T-028: Add pre-cache launch-universe job contracts

Goal:
Add deterministic pre-cache launch-universe job contracts so the MVP operational pre-cache set can be requested and inspected as fixture-backed job state without starting real workers, making provider calls, generating new asset output, or changing search/support classification.

Completed:

- Added pre-cache response models in `backend/models.py`: `PreCacheJobResponse`, `PreCacheBatchSummary`, and `PreCacheBatchResponse`, using existing ingestion job types, job states, worker states, capabilities, retryability, generated-output flags, citation/source ID lists, and status URLs.
- Added deterministic pre-cache contract helpers in `backend/ingestion.py`, including stable launch batch ID `pre-cache-launch-universe-v1`, stable launch status URL `/api/admin/pre-cache/launch-universe`, stable per-asset job IDs such as `pre-cache-launch-voo`, and fixture-backed request/status helpers for launch-universe assets.
- The launch-universe pre-cache contract covers cached local generated assets `AAPL`, `VOO`, and `QQQ` plus the eligible-not-cached launch assets from `ELIGIBLE_NOT_CACHED_ASSETS`.
- Cached local assets are marked succeeded/already available with existing generated routes and page/chat/comparison capability flags preserved.
- Eligible-not-cached assets remain non-generated: the contract gives pending/queued states for most launch assets, a deterministic running fixture for `MSFT`, and a deterministic failed retryable fixture for `AMZN`, with no generated route, citations, source documents, generated page, chat answer, comparison, or reusable generated-output cache hit.
- Unsupported and unknown pre-cache requests return explicit unsupported or unknown non-generated states, and missing pre-cache job IDs return an unavailable non-generated state.
- Added API routes in `backend/main.py` for `POST /api/admin/pre-cache/launch-universe`, `GET /api/admin/pre-cache/launch-universe`, `GET /api/admin/pre-cache/jobs/{job_id}`, and `POST /api/admin/pre-cache/{ticker}` while preserving existing `/api/admin/ingest/{ticker}` and `/api/jobs/{job_id}` behavior.
- Added `evals/pre_cache_eval_cases.yaml` and extended `evals/run_static_evals.py` to verify required models, status states, launch-universe coverage, stable IDs, capability flags, no generated output for non-cached states, absence of citations/source documents from nonexistent packs, and forbidden live-call or credential imports.
- Added focused coverage in `tests/unit/test_ingestion_jobs.py`, `tests/unit/test_cache_contracts.py`, and `tests/integration/test_backend_api.py` for deterministic batch/status responses, cached versus eligible-not-cached capabilities, running/failed/unsupported/unknown/unavailable states, cache non-reuse for non-generated states, and API serialization.
- Added `docs/agent-journal/20260422T184635Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-028 agent journal records that `git status --short`, focused ingestion/cache pytest, backend API pytest, full pytest, static evals, and the full quality gate passed.
- T-028 agent journal records focused ingestion/cache pytest as 24 tests passed, backend API integration pytest as 22 tests passed, full Python pytest as 113 tests passed, static evals as passed, and the full quality gate as passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-028-20260422T184635Z`.
- Remaining documented risk: the pre-cache work is contract-only; it does not add real workers, queues, Redis/PostgreSQL persistence, provider calls, source facts, retrieval packs, generated pages, generated chat answers, generated comparisons, frontend UI, analytics, auth, or deployment config.
- Remaining documented risk: eligible-not-cached launch assets remain non-generated even though their pre-cache jobs expose deterministic pending/running/failed states and status URLs.
- Remaining documented risk: cached local assets `AAPL`, `VOO`, and `QQQ` are marked pre-cache succeeded only because existing fixture-backed generated routes and capabilities already exist.

Completion commits:

- `a61de16 feat(T-028): add pre-cache launch-universe job contracts`
- `f23e33f chore(T-028): merge pre-cache launch-universe job contracts`

### T-027: Expand golden asset eval coverage for MVP launch universe

Goal:
Expand deterministic golden eval coverage so the MVP launch-universe control set catches regressions in search/support classification, on-demand ingestion eligibility, provider mock states, unavailable comparisons, citations/freshness expectations, and advice-boundary safety without making live external calls or generating unsupported asset content.

Completed:

- Expanded `evals/golden_assets.yaml` to schema `golden-assets-v2` with technical-design golden assets, cached supported assets, eligible-not-cached launch assets, unsupported samples, unknown samples, common comparison pairs, local generated comparison pairs, and expected capability flags.
- Preserved `AAPL`, `VOO`, and `QQQ` as the only cached supported local generated fixtures with generated routes, page/chat/comparison capabilities, citations, source documents, freshness expectations, stable/recent separation, and exactly three top risks.
- Added deterministic eligible-not-cached launch-universe metadata in `backend/data.py` for non-cached launch assets including broad ETFs, sector/theme ETFs, and large stocks such as `SPY`, `VTI`, `IVV`, `IWM`, `DIA`, `VGT`, `XLK`, `SOXX`, `SMH`, `XLF`, `XLV`, `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `BRK.B`, `JPM`, and `UNH`.
- Extended deterministic ingestion behavior in `backend/ingestion.py` so eligible-not-cached launch assets return stable on-demand job IDs and status URLs with no generated route, page capability, chat capability, comparison capability, citations, or invented facts.
- Extended mocked provider behavior in `backend/providers.py` so market/reference asset-resolution responses cover eligible-not-cached launch assets with same-asset identity and generated-output flags still false.
- Extended search, ingestion, provider, backend API, and static eval coverage through `tests/unit/test_search_classification.py`, `tests/unit/test_ingestion_jobs.py`, `tests/unit/test_provider_adapters.py`, `tests/integration/test_backend_api.py`, `evals/search_eval_cases.yaml`, `evals/ingestion_eval_cases.yaml`, `evals/provider_eval_cases.yaml`, and `evals/run_static_evals.py`.
- Golden comparison coverage now preserves the existing generated local `VOO`/`QQQ` comparison where a local pack exists and verifies common pairs involving eligible-not-cached or missing packs stay unavailable without generated factual differences, beginner bottom lines, citations, source documents, or invented facts.
- Static evals verify launch-universe membership, cached-supported versus eligible-not-cached capability boundaries, citation/source/freshness expectations for cached fixtures, unavailable states for missing comparison packs, advice-boundary safety, and no live-call or credential imports.
- Added `docs/agent-journal/20260422T181551Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-027 agent journal records that `git status --short`, focused search/ingestion/provider pytest, backend API pytest, full pytest, static evals, and the full quality gate passed.
- T-027 agent journal records focused search/ingestion/provider pytest as 20 tests passed, backend API pytest as 20 tests passed, full pytest as 105 tests passed, static evals as passed, and the quality gate as passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Merged local branch: `agent/T-027-20260422T181551Z`.
- Remaining documented risk: launch-universe additions are deterministic resolution and eval metadata only; they do not add real source facts, retrieval knowledge packs, generated pages, chat answers, comparison packs, exports, provider network calls, or ingestion workers.
- Remaining documented risk: eligible-not-cached generated API paths remain blocked by the existing local fixture behavior, but forced overview/chat calls still surface unavailable or unsupported-redirect style responses because no retrieval packs exist yet.
- Remaining documented risk: provider responses for newly added launch assets are mocked asset-resolution contracts only; future real provider ingestion must preserve same-asset binding, licensing constraints, freshness metadata, and no-live-call CI behavior.

Completion commits:

- `c803eee test(T-027): expand golden asset eval coverage for MVP launch universe`
- `d6be27a chore(T-027): merge expand golden asset eval coverage for MVP launch universe`

### T-026: Add caching and freshness-hash contracts

Goal:
Add deterministic backend cache-key, source-checksum, and freshness-hash contracts so future cached asset pages, comparisons, chat answers, exports, pre-cache jobs, and refresh jobs can decide whether cached outputs are reusable without making live external calls or weakening citation, freshness, licensing, or safety guarantees.

Completed:

- Added cache contract enums and models in `backend/models.py`, including `CacheEntryKind`, `CacheScope`, `CacheEntryState`, `CacheInvalidationReason`, `CacheKeyMetadata`, `SourceChecksumInput`, `SourceChecksumRecord`, `FreshnessFactInput`, `FreshnessRecentEventInput`, `FreshnessEvidenceGapInput`, `SectionFreshnessInput`, `KnowledgePackFreshnessInput`, `GeneratedOutputFreshnessInput`, `CacheEntryMetadata`, and `CacheRevalidationResult`.
- Added `backend/cache.py` with pure deterministic helpers for cache-key construction, source-document checksum computation, knowledge-pack freshness hashes, generated-output freshness hashes, cache revalidation decisions, local text fingerprinting, retrieval/provider source checksum adapters, knowledge/comparison pack freshness inputs, generated-output freshness inputs, and generated-output cache metadata.
- Cache keys include schema version, cache scope, entry kind, asset or comparison identity, mode/output type, source freshness state, prompt version, model name, and input freshness hash where provided.
- Comparison cache keys preserve left/right direction with identities such as `comparison-voo-to-qqq` and `comparison-qqq-to-voo`.
- Source checksums normalize unordered fact bindings, recent-event bindings, citation IDs, and local chunk text fingerprints so equivalent reordering does not change checksums.
- Source checksum records preserve source document ID, asset ticker, checksum, freshness state, cache permission, source type/rank, citation IDs, fact bindings, and recent-event bindings without storing raw local chunk text.
- Knowledge-pack and generated-output freshness hashes sort source checksum, fact, recent-event, evidence-gap, and section-freshness inputs so unordered equivalent inputs hash consistently.
- Generated-output freshness hashes change when prompt version, model name, schema version, source freshness state, source checksum, canonical fact input, or recent-development input changes.
- Cache revalidation can return `hit`, `miss`, `stale`, `hash_mismatch`, `expired`, `permission_limited`, `unsupported`, `unknown`, `unavailable`, and `eligible_not_cached` states without inventing facts.
- Unsupported, unknown, eligible-not-cached, unavailable, stale, and permission-limited inputs are explicitly blocked from reusable generated-output cache hits.
- Provider/source licensing metadata is respected at the contract level: `cache_allowed=False` produces a permission-limited non-reusable cache decision.
- Cache entry metadata preserves source document IDs, citation IDs, source freshness states, section freshness labels, unknown/stale/unavailable evidence-gap states, prompt/model metadata, cache permission, and export permission.
- Added focused cache contract tests in `tests/unit/test_cache_contracts.py` covering deterministic cache keys, direction-preserving comparison keys, source checksum determinism, raw text exclusion, provider cache permissions, order-insensitive knowledge hashes, generated-output hash invalidation, revalidation states, no-live-call/no-store imports, and preserved metadata.
- Added `evals/cache_eval_cases.yaml` and extended `evals/run_static_evals.py` for required cache models, required helpers, revalidation states, invalidation reasons, checksum inputs, freshness-hash inputs, cache-key cases, permission-limited blocking, unsupported blocking, hash-mismatch blocking, and forbidden imports.
- Added `docs/agent-journal/20260422T174755Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-026 agent journal records that `git status --short`, cache contract pytest, backend API pytest, full pytest, static evals, and the full quality gate passed.
- T-026 agent journal records cache contract pytest as 12 passed, backend API pytest as 20 passed, full pytest as 103 passed, static evals as passed, and the quality gate as passed including Python tests, static evals, frontend smoke checks, TypeScript typecheck, production build, and backend checks.
- Remaining documented risk: the cache work is contract-only; no Redis, PostgreSQL, persistence layer, queue, provider fetch path, LLM path, API route, frontend UI, or generated-output behavior was wired to these helpers.
- Remaining documented risk: freshness hashes are deterministic over local fixture/provider-contract inputs, but future ingestion/provider implementations must map real source metadata, normalized facts, recent events, evidence gaps, and licensing permissions into these models consistently.
- Remaining documented risk: provider licensing is enforced only at the cache-contract decision level; real paid or restricted provider terms still need review before storing, exporting, or redistributing any provider content.

Completion commits:

- `a44dada feat(T-026): add caching and freshness-hash contracts`
- `9b1896a chore(T-026): merge caching and freshness-hash contracts`

### T-025: Add provider adapter interfaces with mocked tests

Goal:
Add typed provider adapter interfaces and deterministic mocked adapter responses for the future SEC, ETF issuer, market/reference, and recent-development provider layer so ingestion work has explicit contracts for source-backed data, attribution, freshness, licensing, and failure states without making live external calls.

Completed:

- Added provider contract enums and models in `backend/models.py`, including `ProviderKind`, `ProviderDataCategory`, `ProviderResponseState`, `ProviderSourceUsage`, `ProviderRequestMetadata`, `ProviderCapability`, `ProviderLicensing`, `ProviderSourceAttribution`, `ProviderFact`, `ProviderRecentDevelopmentCandidate`, `ProviderResponseFreshness`, `ProviderError`, `ProviderGeneratedOutputFlags`, and `ProviderResponse`.
- Added `backend/providers.py` with a `ProviderAdapter` protocol, deterministic `MockProviderAdapter`, `NO_LIVE_EXTERNAL_CALLS`, `DEFAULT_PROVIDER_RETRIEVED_AT`, factory functions for SEC-like, ETF issuer, market/reference, and recent-development mock adapters, plus `get_mock_provider_adapters` and `fetch_mock_provider_response`.
- Added a deterministic SEC-like stock provider response for `AAPL` with official SEC source attribution, source rank `1`, canonical usage, `primary_business`, and `net_sales_trend_available` facts.
- Added deterministic ETF issuer provider responses for `VOO` and `QQQ` with official issuer fact-sheet and holdings-file attribution, source rank `1`, benchmark, expense-ratio, and holdings-count facts.
- Added deterministic structured market/reference responses for `AAPL`, `VOO`, and `QQQ` as supported local assets, and `SPY` and `MSFT` as eligible-not-cached assets.
- Market/reference responses use structured-reference source usage, source rank `4`, non-official attribution, and restricted licensing metadata with export and redistribution disallowed for restricted provider payloads.
- Added deterministic recent-development responses where `AAPL` has a high-signal recent-context filing-review candidate, while `VOO` and `QQQ` return an explicit `no_high_signal` state.
- Recent-development source attribution and candidates are marked as recent context only and cannot overwrite canonical facts.
- Added explicit provider failure states for recognized unsupported assets such as `BTC`, `TQQQ`, and `SQQQ`, unknown assets such as `ZZZZ`, and unavailable recent-development fixtures without invented facts.
- Provider responses include source document IDs, source types, publishers, URLs where available, published/as-of dates, retrieved timestamps, freshness states, official-source flags, provider names/kinds, data categories, source usage/rank, licensing metadata, provider errors, and generated-output flags.
- Generated-output flags remain false for asset pages, chat answers, comparisons, overview sections, export payloads, and frontend routes.
- Provider facts and recent-development candidates bind to the requested asset only, bind citations to source document IDs where applicable, and do not use glossary entries as support for asset-specific claims.
- Added focused provider adapter tests in `tests/unit/test_provider_adapters.py` covering adapter capabilities, supported responses, eligible-not-cached states, unsupported/unknown/unavailable states, same-asset binding, source hierarchy, freshness fields, licensing constraints, recent-context separation, no-high-signal recent-development handling, generated-output flags, and absence of live-call or credential imports.
- Added provider static eval cases in `evals/provider_eval_cases.yaml` and extended `evals/run_static_evals.py` for required provider kinds, supported stock/ETF/market/recent cases, eligible-not-cached cases, failure states, no-high-signal recent-development cases, licensing constraints, source hierarchy, generated-output flags, and forbidden live-call imports.
- Added `docs/agent-journal/20260422T172010Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-025 agent journal records that `git status --short`, provider adapter pytest, backend API pytest, full pytest, static evals, and the full quality gate passed.
- T-025 agent journal records provider adapter pytest as 8 passed, backend API pytest as 20 passed, full pytest as 91 passed, static evals as passed, and the quality gate as passed including provider contract tests, static evals, full Python suite, frontend smoke/type/build checks, and backend checks.
- Remaining documented risk: provider adapters are deterministic mock contracts only; they do not fetch SEC, ETF issuer, market/reference, or news data.
- Remaining documented risk: provider contracts are intentionally not wired into search, ingestion jobs, overview generation, comparison, chat, export, persistence, caching, queues, or frontend UI.
- Remaining documented risk: licensing metadata documents export/display constraints at the contract level, but real provider terms still require review before paid or restricted data is exposed, cached, or exported.

Completion commits:

- `e14a798 test(T-025): add provider adapter interfaces with mocked tests`
- `0d0cbb6 chore(T-025): merge provider adapter interfaces with mocked tests`

### T-024: Add export/download contracts for pages, comparisons, sources, and chat

Goal:
Add deterministic accountless export/download API contracts for fixture-backed asset pages, comparison output, source lists, and chat transcripts so users can save learning outputs with citations, source metadata, freshness context, and the educational disclaimer, without adding live calls or unsupported asset facts.

Completed:

- Added typed export contract models in `backend/models.py`, including `ExportFormat`, `ExportContentType`, `ExportState`, `ExportExcerpt`, `ExportSourceMetadata`, `ExportCitation`, `ExportedItem`, `ExportedSection`, `ExportNote`, `ComparisonExportRequest`, `ChatTranscriptExportRequest`, `ExportResponse`, and the reusable `EDUCATIONAL_DISCLAIMER`.
- Added `backend/export.py` with deterministic `export_asset_page`, `export_asset_source_list`, `export_comparison`, and `export_chat_transcript` functions that shape existing local overview, source, comparison, and chat outputs into JSON/Markdown-style export payloads.
- Added the export licensing note `export_licensing_scope`, including citation IDs, source attribution, freshness metadata, short allowed fixture passages, and an explicit restriction against exporting full paid-news articles, full filings, full issuer documents, or restricted provider payloads unless rights are confirmed.
- Wired export API routes in `backend/main.py`: `GET /api/assets/{ticker}/export`, `GET /api/assets/{ticker}/sources/export`, `POST /api/compare/export`, `GET /api/compare/export`, and `POST /api/assets/{ticker}/chat/export`.
- Asset-page exports preserve asset identity, page freshness, beginner summary, exactly three top risks first, recent developments separated from stable facts, educational suitability, PRD sections, citation IDs, source metadata, rendered Markdown, disclaimer, and licensing note for supported local assets.
- Source-list exports preserve source document ID, title, source type, publisher, URL, published/as-of date, retrieved timestamp, freshness state, official-source flag, metadata, and short allowed excerpt notes without exporting full source documents.
- Comparison exports preserve left/right asset identity, key differences, beginner bottom line, comparison type metadata, citation IDs, comparison source metadata, rendered Markdown, disclaimer, and licensing note for `VOO` vs `QQQ` in both directions.
- Chat transcript exports preserve ticker, question, direct answer, why-it-matters text, uncertainty notes, safety classification, citations, source metadata, disclaimer, and licensing note.
- Advice-like chat transcript exports preserve the educational redirect and avoid generated factual citations or source documents for the redirected answer.
- Unsupported, unknown, unavailable-comparison, unsupported-comparison, and eligible-not-cached export requests return `unsupported` or `unavailable` states with no generated factual sections, citations, source documents, pages, chat answers, comparisons, or invented facts.
- Added focused export tests in `tests/unit/test_exports.py`, API route coverage in `tests/integration/test_backend_api.py`, and export static eval coverage in `evals/export_eval_cases.yaml` plus `evals/run_static_evals.py`.
- Extended safety guardrail coverage so `backend/export.py` is scanned for forbidden advice-like output.
- Added `docs/agent-journal/20260422T081035Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-024 agent journal records that `git status --short`, focused export/API pytest, safety guardrail pytest, full pytest, frontend smoke via `npm test`, static evals, and the full quality gate passed.
- T-024 agent journal records focused export/API pytest as 26 passed, safety guardrail pytest as 4 passed, full pytest as 83 passed, frontend smoke as passed, static evals as passed, and the quality gate as passed including Python tests, static evals, frontend smoke, TypeScript typecheck, production build, and backend checks.
- Remaining documented risk: exports are JSON/Markdown-style contract payloads only; no PDF rendering, file storage, browser download controls, clipboard behavior, persistence, analytics, caching, provider adapters, or live ingestion were added.
- Remaining documented risk: exported content is limited to existing deterministic local overview, comparison, source, and chat outputs; it does not add new evidence or fill existing unknown, stale, unavailable, mixed, or insufficient-evidence gaps.
- Remaining documented risk: source excerpts are short local fixture supporting passages with licensing notes; final provider-specific redistribution rules still need legal/licensing review before using paid or restricted provider content.

Completion commits:

- `2e6ccf7 feat(T-024): add export/download contracts for pages, comparisons, sources, and chat`
- `df9a0f9 chore(T-024): merge export/download contracts for pages, comparisons, sources, and chat`

### T-023: Add hybrid glossary baseline terms and UI hooks

Goal:
Add a broader curated glossary baseline and deterministic frontend hooks so Beginner Mode can expose beginner-friendly finance terms for local fixture-backed stock and ETF pages without adding unsupported asset-specific claims or live calls.

Completed:

- Expanded `lib/glossary.ts` into a curated static glossary baseline covering the required PRD core terms, including ETF cost/size/structure/exposure/tracking/pricing/trading terms, stock company-size/fundamental/profitability/cash-generation/balance-sheet/valuation terms, and risk terms.
- Added `category` metadata to glossary entries and preserved short beginner-readable definitions, why-it-matters text, and common beginner mistakes for each curated term.
- Added stock and ETF glossary term groups in `lib/glossary.ts`, including `stock-business-metrics`, `stock-valuation-risk`, `etf-fund-basics`, `etf-exposure-risk`, and `etf-trading-tracking`.
- Added `getGlossaryTerm` lookup behavior so `GlossaryPopover` can accept a string term and handle unavailable terms without inventing definitions.
- Updated `components/GlossaryPopover.tsx` with stable glossary markers for term, category, definition, why-it-matters, beginner-mistake, and availability state.
- Preserved keyboard and screen-reader behavior in `GlossaryPopover` with `aria-expanded`, `aria-controls`, dialog labeling, and Escape handling for the open popover.
- Updated `app/assets/[ticker]/page.tsx` so fixture-backed Beginner Mode pages render a deterministic `Glossary for this page` learning area with stock/ETF term groups, asset ticker/type markers, and a no-generated-context marker.
- Kept inline glossary access near the beginner overview and made ETF pages show `expense ratio` and `index tracking`, while stock pages show `market risk` and `P/E ratio`.
- Added glossary learning-area CSS in `styles/globals.css`.
- Extended `tests/frontend/smoke.mjs` to require glossary catalog coverage, glossary UI markers, glossary term groups, generic-education/no-generated-context markers, no asset-specific glossary claims in `lib/glossary.ts`, preservation of fixture-backed citations/freshness/source checks, and absence of live external glossary calls.
- T-023 agent journal records that `git status --short`, `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, static evals, and the full quality gate passed.
- T-023 agent journal records the full quality gate as passed with Python tests 73 passed, frontend smoke checks passed, production build passed and prerendered `/assets/VOO`, `/assets/QQQ`, and `/assets/AAPL`, and backend checks 73 passed.
- Remaining documented risk: glossary content is static frontend data only; it does not add backend glossary APIs, generated asset-specific glossary context, glossary detail pages, exports, analytics, or persistence.
- Remaining documented risk: AAPL, VOO, and QQQ glossary hooks are grouped by asset type and local page vocabulary, but they do not fill existing explicit evidence gaps such as unavailable ETF exposure/trading metrics or stock valuation metrics.
- Remaining documented risk: glossary entries are generic educational explanations and are intentionally not citation sources for asset-specific claims.

Completion commits:

- `c22f022 feat(T-023): add hybrid glossary baseline terms and UI hooks`
- `3e53e25 chore(T-023): merge hybrid glossary baseline terms and UI hooks`

### T-022: Add Beginner Mode and Deep-Dive Mode page structure

Goal:
Add a clear Beginner Mode first and Deep-Dive Mode baseline structure to the fixture-backed asset pages so beginners can start with the plain-English learning view and still reach the richer cited PRD sections without live calls.

Completed:

- Added `components/AssetModeLayout.tsx` with accessible Beginner Mode and Deep-Dive Mode regions, stable frontend markers, and a sidebar area for source and learning tools.
- Updated `app/assets/[ticker]/page.tsx` so `AAPL`, `VOO`, and `QQQ` render Beginner Mode first and Deep-Dive Mode second through the new layout component.
- Built the Beginner Mode flow from existing local fixture data: plain-English beginner overview, primary citation chip, page and section freshness labels, glossary access, exactly three top risks first, stable fact details, visually separate recent developments, educational suitability copy, and the existing asset chat panel.
- Preserved educational framing in Beginner Mode without adding buy/sell/hold, allocation, tax, brokerage, or price-target language.
- Preserved Deep-Dive Mode rendering by routing `AAPL` through `AssetStockSections` and `VOO`/`QQQ` through `AssetEtfSections`.
- Preserved the existing stock PRD section IDs for `AAPL`: `business_overview`, `products_services`, `strengths`, `financial_quality`, `valuation_context`, `top_risks`, `recent_developments`, and `educational_suitability`.
- Preserved the existing ETF PRD section IDs for `VOO` and `QQQ`: `fund_objective_role`, `holdings_exposure`, `construction_methodology`, `cost_trading_context`, `etf_specific_risks`, `similar_assets_alternatives`, `recent_developments`, and `educational_suitability`.
- Updated source-tool rendering on the asset page so pages with PRD sections render `SourceDrawer` entries for section source documents with related claim contexts; the primary-source fallback remains for pages without PRD sections.
- Added CSS for the two-mode layout, mode stack, mode regions, and mode headings in `styles/globals.css`.
- Extended frontend smoke checks to require mode layout markers, Beginner Mode ordering, top-risk ordering, stable/recent separation, chat placement, PRD section preservation, source/citation/freshness availability, risk count preservation, and no live external calls from the mode layout.
- Extended safety guardrail coverage so `components/AssetModeLayout.tsx` is scanned for forbidden advice-like frontend copy.
- Added `docs/agent-journal/20260422T070202Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-022 agent journal records that `git status --short`, `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, static evals, and the full quality gate passed.
- T-022 agent journal records the full quality gate as passed with Python tests 73 passed, frontend smoke checks passed, production build passed and prerendered `/assets/VOO`, `/assets/QQQ`, and `/assets/AAPL`, and backend checks 73 passed.
- Remaining documented risk: the mode structure is frontend-only and fixture-backed; it does not add backend overview calls, ingestion, providers, caching, export, glossary expansion, comparison changes, or chat behavior changes.
- Remaining documented risk: Beginner Mode reuses existing local fixture fields and citations; it does not add new evidence or fill existing unknown, stale, unavailable, insufficient-evidence, or no-high-signal gaps.
- Remaining documented risk: Deep-Dive Mode preserves the existing stock and ETF PRD section components, so source drawer links still use the existing source-document drawer anchor pattern rather than per-citation deep links.

Completion commits:

- `fd7d0f5 feat(T-022): add Beginner Mode and Deep-Dive Mode page structure`
- `65c538f chore(T-022): merge Beginner Mode and Deep-Dive Mode page structure`

### T-021: Render ETF PRD sections on asset pages

Goal:
Render the richer ETF PRD overview sections for the local `VOO` and `QQQ` asset pages so beginners can inspect fund objective/role, holdings/exposure, construction/methodology, cost/trading limitations, ETF-specific risks, similar-assets gaps, recent developments, educational suitability, citations, and freshness states in the frontend without live calls.

Completed:

- Added `components/AssetEtfSections.tsx` to render ETF-only PRD sections from deterministic local fixtures with section, item, metric, evidence-state, freshness-state, stable/recent-separation, and top-risk-count markers.
- Updated `app/assets/[ticker]/page.tsx` so `VOO` and `QQQ` use the ETF PRD section path while `AAPL` continues to use the stock PRD section path.
- Updated the asset-page sidebar source handling so PRD-section pages render source drawers for the section source documents instead of a single primary-source fallback.
- Extended `lib/fixtures.ts` with ETF section fixture data for `VOO` and `QQQ`, including ETF section items, metrics, citation IDs, source-document bindings, citation contexts, and explicit evidence-gap states.
- Rendered the VOO and QQQ ETF PRD sections for `fund_objective_role`, `holdings_exposure`, `construction_methodology`, `cost_trading_context`, `etf_specific_risks`, `similar_assets_alternatives`, `recent_developments`, and `educational_suitability`.
- Rendered VOO source-backed S&P 500 benchmark and broad U.S. large-company ETF role details from the local fixture.
- Rendered QQQ source-backed Nasdaq-100 benchmark and narrower growth-oriented ETF role details from the local fixture.
- Preserved ETF holdings, methodology, trading-data, similar-assets, and recent-development evidence gaps instead of inventing unsupported facts.
- Preserved exactly three ETF-specific risk items first, with citation chips and no extra risk claims inserted ahead of them.
- Added CSS for ETF PRD section spacing, ETF section item cards, compact evidence-state pills, evidence-gap notes, and ETF item headings.
- Extended frontend smoke checks to require ETF PRD component markers, VOO and QQQ ETF section IDs, ETF citation/source markers, explicit gap markers, source drawer metadata hooks, freshness and stable/recent markers, exactly three ETF top risks, AAPL stock-section preservation, no cross-asset source binding, no asset-page backend overview calls, and no live external calls.
- Extended safety guardrail coverage so `components/AssetEtfSections.tsx` is scanned for forbidden advice-like frontend copy.
- Added `docs/agent-journal/20260422T063309Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-021 agent journal records that `git status --short`, `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, static evals, and the full quality gate passed.
- T-021 agent journal records the final quality gate as passed with Python tests 73 passed, static evals passed, frontend smoke passed, typecheck passed, production build passed, and backend checks 73 passed.
- Remaining documented risk: ETF PRD sections are deterministic local frontend fixtures only; no backend overview calls, provider adapters, ingestion, caching, chat, comparison, glossary, or export behavior were added.
- Remaining documented risk: VOO and QQQ still show explicit evidence gaps for top-10 weights, top-10 concentration, sector exposure, country exposure, largest-position data, full methodology details, bid-ask spread, average volume, premium/discount, holdings overlap, similar ETFs, simpler alternatives, and diversification-addition claims.
- Remaining documented risk: source drawers expose local fixture source metadata and related claim context, but citation links still target the existing source-document drawer anchors rather than deep-linking to an individual citation row.

Completion commits:

- `5adaf8d feat(T-021): render ETF PRD sections on asset pages`
- `bf3aea9 chore(T-021): merge render ETF PRD sections on asset pages`

### T-020: Render stock PRD sections on asset pages

Goal:
Render the richer stock PRD overview sections for the local `AAPL` asset page so beginners can inspect stock business, products/services, strengths, financial quality, valuation-context limitations, top risks, recent developments, educational suitability, citations, and freshness states in the frontend without live calls.

Completed:

- Added `components/AssetStockSections.tsx` to render stock-only PRD sections from deterministic local fixtures with section, item, metric, evidence-state, freshness-state, stable/recent-separation, and top-risk-count markers.
- Updated `app/assets/[ticker]/page.tsx` so `AAPL` uses the stock PRD section path while `VOO` and `QQQ` intentionally stay on the existing ETF rendering path until T-021.
- Updated the asset-page sidebar so stock PRD pages render source drawers for the stock section source documents instead of a single primary-source fallback.
- Extended `components/SourceDrawer.tsx` to accept citation contexts, render related claim context lists, and deduplicate supporting passages while preserving title, source type, publisher, URL, published/as-of date, retrieved timestamp, freshness state, and official-source metadata.
- Extended `lib/fixtures.ts` with stock-section fixture types, AAPL `stockSections`, `citationContexts`, additional AAPL source-document bindings, and citation IDs for primary business, products/services detail, business-quality strength, SEC XBRL net sales trend, valuation-data limitation, risk context, and no-high-signal recent-development review.
- Rendered the AAPL stock PRD sections for `business_overview`, `products_services`, `strengths`, `financial_quality`, `valuation_context`, `top_risks`, `recent_developments`, and `educational_suitability`.
- Preserved explicit evidence gaps in the AAPL UI for business segments, revenue drivers, geographic exposure, competitor detail, earnings, margins, cash flow, debt, cash, ROE, ROIC, valuation metrics, and no high-signal recent developments instead of inventing unsupported facts.
- Preserved exactly three AAPL top risks first, with citation chips and no extra risk claims inserted ahead of them.
- Added CSS for stock PRD section spacing, stock section item cards, compact evidence-state pills, evidence-gap notes, and source context lists.
- Extended frontend smoke checks to require the new stock PRD component, AAPL section IDs, AAPL section citation/source markers, explicit gap markers, source drawer metadata hooks, stable/recent markers, exactly three top risks, no `stockSections` on `VOO` or `QQQ`, no asset-page backend overview calls, and no live external calls.
- Extended safety guardrail coverage so `components/AssetStockSections.tsx` is scanned for forbidden advice-like frontend copy.
- Added `docs/agent-journal/20260422T060036Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-020 agent journal records that `git status --short`, `npm test`, `npm run typecheck`, `npm run build`, safety guardrail pytest, static evals, and the full quality gate passed.
- T-020 agent journal records the final quality gate as passed with Python tests 73 passed, static evals passed, frontend smoke passed, typecheck passed, production build passed, and backend checks 73 passed.
- Remaining documented risk: AAPL stock PRD sections are deterministic local frontend fixtures only; no backend overview API calls, provider adapters, ingestion, caching, export, chat, comparison, glossary, or ETF-section behavior were added.
- Remaining documented risk: VOO and QQQ intentionally remain on the existing ETF page rendering path; ETF PRD section rendering is left for T-021.
- Remaining documented risk: AAPL still shows explicit evidence gaps for business segments, revenue drivers, geographic exposure, competitor detail, earnings, margins, cash flow, debt, cash, ROE, ROIC, and valuation metrics.
- Remaining documented risk: source drawers expose local fixture source metadata and claim context, but do not deep-link per citation beyond the existing source-document drawer anchor pattern.

Completion commits:

- `56e1a07 feat(T-020): render stock PRD sections on asset pages`
- `48d9db2 chore(T-020): merge render stock PRD sections on asset pages`

### T-019: Add richer stock and ETF fixture data for MVP content sections

Goal:
Add richer deterministic local retrieval fixture evidence so the PRD asset overview sections introduced in T-018 can carry more source-backed stock and ETF content without live calls, frontend rendering changes, or schema changes.

Completed:

- Expanded `data/retrieval_fixtures.json` for `AAPL` with additional same-asset source documents, chunks, and normalized facts for products/services detail, a business-quality strength, an FY2023-FY2024 net sales trend, and a cited valuation-data limitation.
- Added an `AAPL` SEC XBRL fixture source and a local valuation-data limitation source with source type, publisher, URL, published/as-of date, retrieved timestamp, freshness state, and official-source metadata.
- Expanded `data/retrieval_fixtures.json` for `VOO` and `QQQ` with holdings-file sources, holdings/exposure detail chunks, construction/methodology chunks, and local trading-data limitation sources.
- Added normalized ETF facts for holdings exposure detail, construction methodology, and trading-data limitations for both `VOO` and `QQQ`, with same-asset source document and chunk bindings.
- Updated `backend/overview.py` so AAPL stock sections consume the richer fixture facts: products/services uses supported product and services detail, strengths becomes supported when the business-quality point exists, financial quality becomes mixed with a net sales trend and residual metric gaps, and valuation context becomes mixed with a cited valuation limitation plus remaining valuation metric gaps.
- Updated `backend/overview.py` so VOO and QQQ ETF sections consume richer fixture facts for holdings exposure detail, construction methodology, and cited trading-data limitations while preserving residual gaps for full holdings weights, concentration, sector/country exposure, trading metrics, overlap, and alternatives.
- Preserved stable/recent separation, exactly three top risks first, educational framing, and blocking for unsupported, unknown, ambiguous, and eligible-not-cached assets.
- Extended `tests/unit/test_retrieval_fixtures.py` to require the richer stock and ETF fact fields for `AAPL`, `VOO`, and `QQQ`.
- Extended `tests/unit/test_overview_generation.py` and `tests/integration/test_backend_api.py` to verify richer stock and ETF section item IDs, citation/source presence, and updated evidence states.
- Extended `evals/run_static_evals.py` to cover richer fixture field coverage and richer generated overview section expectations.
- Added `docs/agent-journal/20260422T053337Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-019 agent journal records an initial focused test failure from an outdated T-018 assertion expecting AAPL strengths to remain unknown, followed by a focused revision and passing reruns.
- T-019 agent journal records focused retrieval/overview/safety/API pytest as 36 passed, full pytest as 73 passed, static evals as passed, and the quality gate as passed including Python tests, static evals, frontend smoke checks, typecheck, production build, and backend checks.
- Remaining documented risk: richer content remains deterministic local fixture evidence only; no provider adapters, live ingestion, embeddings, LLM calls, cache refresh, export behavior, or frontend rendering were added.
- Remaining documented risk: AAPL still has explicit gaps for segment, revenue-driver, geographic, competitor, margin, cash-flow, debt, cash, ROE/ROIC, and valuation metrics.
- Remaining documented risk: VOO and QQQ still have explicit gaps for full top-10 weights, concentration, sector/country exposure, largest position, full methodology details, bid-ask spread, average volume, premium/discount, overlap, and alternatives.
- Remaining documented risk: unsupported, unknown, ambiguous, and eligible-not-cached assets remain blocked from generated overview content, citations, source documents, chat answers, and comparison output.

Completion commits:

- `ef06a5e feat(T-019): add richer stock and ETF fixture data for MVP content sections`
- `693350f chore(T-019): merge richer stock and ETF fixture data for MVP content sections`

### T-018: Expand asset overview schema for PRD content sections

Goal:
Expand the backend asset overview response schema so supported stock and ETF pages can expose the PRD-required content sections with citations, freshness, and explicit unknown/stale/unavailable states before richer fixtures and frontend rendering are added.

Completed:

- Added overview section contract models in `backend/models.py`, including `EvidenceState`, `OverviewSectionType`, `OverviewMetric`, `OverviewSectionItem`, and `OverviewSection`.
- Extended `OverviewResponse` with a `sections` field while preserving the existing `beginner_summary`, `top_risks`, `recent_developments`, `suitability_summary`, `claims`, `citations`, and `source_documents` fields.
- Updated deterministic overview generation in `backend/overview.py` so fixture-backed stock overview responses expose `business_overview`, `products_services`, `strengths`, `financial_quality`, `valuation_context`, `top_risks`, `recent_developments`, and `educational_suitability` sections.
- Updated deterministic overview generation so fixture-backed ETF overview responses expose `fund_objective_role`, `holdings_exposure`, `construction_methodology`, `cost_trading_context`, `etf_specific_risks`, `similar_assets_alternatives`, `recent_developments`, and `educational_suitability` sections.
- Added section-level citation IDs, source document IDs, freshness state, evidence state, as-of dates, retrieved timestamps, limitations, items, and metrics where supported by the existing local retrieval packs.
- Represented missing fixture evidence as explicit `unknown`, `unavailable`, `stale`, `mixed`, `insufficient_evidence`, or `no_major_recent_development` states instead of inventing unsupported strengths, financial-quality metrics, valuation metrics, holdings details, trading metrics, alternatives, or recent events.
- Kept recent-development section data separate from stable asset basics, including source/as-of or retrieved-date context where the existing models provide it.
- Preserved exactly three top risks first for supported generated overviews.
- Kept unsupported and unknown assets such as `BTC` and `ZZZZ` blocked from generated PRD sections, generated factual claims, citations, source documents, and generated routes.
- Extended backend API tests so `/api/assets/VOO/overview` and `/api/assets/AAPL/overview` serialize the new section schema while unsupported and unknown overview responses keep empty `sections`.
- Extended overview unit tests and static evals for stock section presence, ETF section presence, same-asset citation/source binding for section items and metrics, explicit evidence-gap handling, stable/recent separation, top-risk count, safety copy, and absence of live external calls.
- Added `docs/agent-journal/20260422T050742Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-018 agent journal records that `git status --short`, focused backend/API/safety pytest, full pytest, static evals, and the full quality gate passed.
- T-018 agent journal records focused backend/API/safety pytest as 29 passed, the full pytest suite as 73 passed, static evals as passed, and the quality gate as passed including Python tests, static evals, frontend smoke checks, typecheck, production build, and backend checks.
- Remaining documented risk: the new overview sections are deterministic and fixture-backed only; they do not add richer source data, provider adapters, live ingestion, embeddings, LLM calls, or frontend rendering.
- Remaining documented risk: several PRD sections intentionally return `unknown`, `unavailable`, `stale`, `mixed`, or `insufficient_evidence` states because current local packs do not contain enough evidence for detailed strengths, financial quality, holdings exposure, trading metrics, or alternatives.
- Remaining documented risk: unsupported, unknown, and eligible-not-cached assets remain blocked from generated PRD sections, citations, source documents, chat answers, comparisons, and generated routes.

Completion commits:

- `a7564f4 feat(T-018): expand asset overview schema for PRD content sections`
- `d8c52a9 chore(T-018): merge expand asset overview schema for PRD content sections`

### T-017: Add on-demand ingestion job-state contract

Goal:
Define a deterministic backend/API contract for on-demand ingestion job states so eligible-but-not-cached assets from search can expose a future ingestion path without making live provider calls or generating unsupported pages.

Completed:

- Added typed ingestion job models in `backend/models.py`, including job type, job state, worker status, retryability, capabilities, error metadata, status URL, timestamps, generated route, and page/chat/comparison capability flags.
- Added deterministic fixture-backed ingestion service functions in `backend/ingestion.py` for requesting ingestion by ticker and reading job status by stable job ID.
- Wired `POST /api/admin/ingest/{ticker}` and `GET /api/jobs/{job_id}` in `backend/main.py`.
- Eligible-not-cached fixtures such as `SPY` and `MSFT` return deterministic on-demand job states with stable IDs such as `ingest-on-demand-spy` and `ingest-on-demand-msft`.
- Re-requesting an eligible-not-cached ticker is deterministic and does not depend on random IDs, wall-clock timing, live queues, provider credentials, market-data calls, news calls, or LLM calls.
- Cached supported fixtures such as `AAPL`, `VOO`, and `QQQ` return no-ingestion-needed behavior while preserving generated route and generated page/chat/comparison capability flags.
- Recognized unsupported assets such as `BTC`, `TQQQ`, and `SQQQ` return unsupported non-job states with no generated-page, chat, or comparison capabilities.
- Unknown tickers return unknown non-job states with no invented asset facts, job ID, citations, or generated route.
- Added fixture status coverage for pending, running, succeeded, refresh-needed, failed, and unavailable job states, including a deterministic failed job error code `fixture_ingestion_failed`.
- Extended search classification output so eligible-not-cached results expose `can_request_ingestion` and an ingestion request route, while cached, unsupported, ambiguous, and unknown states remain structurally blocked.
- Added focused unit and integration coverage in `tests/unit/test_ingestion_jobs.py`, `tests/unit/test_search_classification.py`, and `tests/integration/test_backend_api.py`.
- Added ingestion eval cases in `evals/ingestion_eval_cases.yaml` and extended `evals/run_static_evals.py` plus `evals/search_eval_cases.yaml` for ingestion request/status states, capability flags, deterministic reruns, and no live external calls.
- Added `docs/agent-journal/20260422T044335Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-017 agent journal records that `git status --short`, focused ingestion/search/API pytest, full pytest, `npm test`, static evals, and the full quality gate passed.
- Remaining documented risk: the ingestion contract is deterministic and fixture-backed only; it does not start real queues, fetch sources, parse documents, generate embeddings, call providers, or call LLMs.
- Remaining documented risk: eligible-not-cached assets such as `SPY` and `MSFT` expose request/status job states but still do not receive generated asset pages, chat answers, comparisons, citations, source documents, or new facts.
- Remaining documented risk: admin ingestion routes are unauthenticated in this local skeleton; the technical design still requires authentication and rate limiting before production use.

Completion commits:

- `188ce86 feat(T-017): add on-demand ingestion job-state contract`
- `226744d chore(T-017): merge on-demand ingestion job-state contract`

### T-016: Define search support-classification contract

Goal:
Define a deterministic search support-classification contract that lets backend clients distinguish cached supported assets, recognized-but-unsupported assets, unknown assets, ambiguous matches, and eligible assets that would require on-demand ingestion later.

Completed:

- Added structured search support-classification models in `backend/models.py`, including response/result status enums, support classifications, disambiguation and ingestion flags, generated routes, and generated page/chat/comparison capability flags.
- Added deterministic fixture-backed search logic in `backend/search.py` and wired `/api/search` in `backend/main.py` to use it.
- Search now ranks cached supported local assets from `ASSETS`, recognized unsupported assets from `UNSUPPORTED_ASSETS` plus search metadata, and eligible-not-cached assets from `ELIGIBLE_NOT_CACHED_ASSETS`.
- Cached supported fixtures such as `AAPL`, `VOO`, and `QQQ` resolve by ticker or name and are marked safe to open only when a local generated asset page is available.
- Ambiguous searches such as `S&P 500 ETF` return multiple candidates and require disambiguation instead of silently choosing a ticker.
- Recognized unsupported examples such as crypto, leveraged ETFs, and inverse ETFs are blocked from generated pages, generated chat, and generated comparisons.
- Unknown searches return an unknown state without invented facts, citations, or generated routes.
- Eligible-but-not-cached examples such as `SPY` and `MSFT` expose the future ingestion-needed contract while remaining blocked from generated page, chat, and comparison output.
- Added focused unit and integration coverage in `tests/unit/test_search_classification.py` and `tests/integration/test_backend_api.py`.
- Added search eval cases in `evals/search_eval_cases.yaml` and static eval checks in `evals/run_static_evals.py` for supported, ambiguous, unsupported, unknown, ingestion-needed, capability flags, and no live external calls.
- Added `docs/agent-journal/20260422T041752Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-016 agent journal records that `git status --short`, focused search/API pytest, full pytest, `npm test`, static evals, and the full quality gate passed.
- Remaining documented risk: search classification is deterministic and fixture-backed only; it does not perform live provider lookup or start ingestion jobs.
- Remaining documented risk: eligible-but-not-cached examples expose the future ingestion-needed contract but intentionally do not generate pages, chat, or comparisons in this task.
- Remaining documented risk: the frontend still uses its existing local search path; this task only defined and tested the backend `/api/search` contract.

Completion commits:

- `b2c71d9 feat(T-016): define search support-classification contract`
- `d49a938 chore(T-016): merge define search support-classification contract`

### T-015: Align MVP control docs with PRD v0.2

Goal:
Update SPEC.md, EVALS.md, TASKS.md, and the technical design spec where needed so the agent loop follows the updated PRD v0.2 MVP direction.

Completed:

- Updated `SPEC.md` so MVP direction covers all eligible U.S.-listed common stocks and plain-vanilla ETFs, recognized-but-unsupported blocking, Massive / ETF Global provider planning, provider licensing review, glossary support, export/download metadata, freshness hashes, and expanded trust metrics.
- Expanded `EVALS.md` with task-specific guidance for search/support classification, glossary/beginner education, export/download, and broader no-live-provider-call expectations across task categories.
- Updated `TASKS.md` backlog from T-016 through T-027 to align with PRD v0.2 MVP sequencing, including search classification, on-demand ingestion job states, PRD asset sections, glossary, export, provider adapters, caching/freshness hashes, and golden asset coverage.
- Updated `docs/learn_the_ticker_technical_design_spec.md` for durable v0.2 architecture details: accountless export behavior, Phase 4 MVP reliability/accountless learning features, caching and freshness-hash work, glossary support, export acceptance, trust metrics, and unsupported asset exclusions.
- Added `docs/agent-journal/20260422T035714Z.md` documenting changed files, commands run, pass/fail status, and remaining risks.
- T-015 agent journal records that `git status --short` and `bash scripts/run_quality_gate.sh` passed on attempt 1.
- Remaining documented risk: this was a documentation/control-plane task only; no product behavior was implemented.
- Remaining documented risk: future provider, export, and on-demand ingestion tasks still need mocked tests and licensing review before exposing restricted data or live external calls.

Completion commits:

- `1828e06 docs(T-015): align MVP control docs with PRD v0.2`
- `7231055 chore(T-015): merge align MVP control docs with PRD v0.2`

### T-014: Add beginner chat starter prompts

Goal:
Make the asset-page grounded chat easier for beginners to start by showing asset-aware starter prompts that cover identity, holdings or business model, risks, recent developments, and advice-boundary education.

Completed:

- Updated `components/AssetChatPanel.tsx` with typed deterministic starter prompt intents for identity, stock business model, ETF holdings/exposure, top risk, recent developments, and advice-boundary education.
- Added asset-aware prompt selection so the local stock fixture `AAPL` receives business-model language, while ETF fixtures such as `VOO` and `QQQ` receive holdings and fund-exposure language.
- Preserved the existing local chat submission flow: clicking a starter prompt submits that exact question through the current `postAssetChat` path and leaves loading, error, answer, citation, source metadata, educational redirect, unsupported, and insufficient-evidence rendering in place.
- Added stable frontend markers for smoke checks with `data-chat-starter-group="beginner-prompts"` and per-intent `data-chat-starter-intent` values.
- Added responsive starter prompt styling in `styles/globals.css` so longer beginner questions wrap cleanly and become full-width on narrow viewports.
- Extended frontend smoke checks for starter prompt markers, stock-specific prompt text, ETF-specific prompt text, advice-boundary prompt text, and no live external chat calls.
- Extended safety guardrail tests with explicit forbidden advice-like examples and starter-prompt copy checks.
- T-014 agent journal records that `npm test`, `npm run typecheck`, `npm run build`, `python3 -m pytest tests/unit/test_safety_guardrails.py -q`, `python3 evals/run_static_evals.py`, and `bash scripts/run_quality_gate.sh` passed.
- Remaining documented risk: starter prompts remain deterministic and fixture-aware for the current local supported assets `AAPL`, `VOO`, and `QQQ`.
- Remaining documented risk: frontend coverage is static smoke coverage plus typecheck/build; it does not browser-click every starter prompt.

Completion commits:

- `99adaf3 feat(T-014): add beginner chat starter prompts`
- `e12735a chore(T-014): merge beginner chat starter prompts`

### T-013: Add fixture-backed asset name search states

Goal:
Let the home-page search workflow resolve supported fixture-backed assets by ticker or asset name, while preserving clear unsupported, unknown, and multi-match states without live calls or invented facts.

Completed:

- Updated `components/SearchBox.tsx` with deterministic local fixture search resolution over supported asset tickers, names, asset type, exchange, issuer, beginner summaries, claims, facts, and source-document fields.
- Added case-insensitive, trimmed query handling with scoring so exact ticker and name matches rank ahead of broader text matches.
- Added a multi-match state that lists each matching local fixture as an asset-page link instead of silently choosing one.
- Added supported-result rendering with canonical ticker, asset name, asset type, exchange, and issuer when available, and kept the Open action pointed at `/assets/{ticker}` only for a single supported result.
- Preserved unsupported and unknown states with no asset-page link, including explicit no-invented-facts copy for unknown ticker or name searches.
- Updated search helper text and placeholders to include supported name-search examples such as Apple, Vanguard S&P 500 ETF, Invesco QQQ Trust, and Nasdaq-100.
- Added search result panel styling in `styles/globals.css`.
- Extended frontend smoke checks with markers for local search resolution, supported result, multi-match result, unsupported result, unknown result, result links, supported fixture name examples, and no live external search calls or `/api/search` call from the fixture-backed home search.
- T-013 agent journal records that `npm test`, `npm run typecheck`, `npm run build`, backend API pytest, safety pytest, static evals, and the main quality gate passed.
- Remaining documented risk: home search remains deterministic and fixture-backed for the current local `AAPL`, `VOO`, and `QQQ` fixtures only.
- Remaining documented risk: frontend coverage is static smoke coverage plus typecheck/build; it does not browser-type every search query.

Completion commits:

- `8e963c8 feat(T-013): add fixture-backed asset name search states`
- `e1b59db chore(T-013): merge fixture-backed asset name search states`

### T-012: Render comparison source metadata on compare page

Goal:
Render comparison source-document metadata on the compare page so beginners can inspect the sources, freshness, and supporting passages behind generated comparison citations.

Completed:

- Reworked `app/compare/page.tsx` to use a comparison-specific fixture shape from `lib/compare.ts` instead of the older `compareFixture` and left-asset primary-source fallback.
- Added `lib/compare.ts` with deterministic `VOO` vs `QQQ` and `QQQ` vs `VOO` compare-page fixtures, comparison citation IDs for benchmark, expense ratio, holdings count, and educational role, same-pack comparison source documents, and unsupported/unknown unavailable states with no citations or source documents.
- Added `getComparisonCitationMetadata` so compare-page citation chips resolve to the matching comparison source document and related claim context.
- Added `components/ComparisonSourceDetails.tsx` to render comparison source document ID, title, source type, publisher, URL, published or as-of date, retrieved timestamp, freshness state, official-source badge, related comparison claims, and supporting passage.
- Updated `CitationChip` to expose `data-source-document-id` and `data-freshness-state` markers used by comparison source metadata smoke checks.
- Updated compare-page unavailable states so unsupported, unknown, or unavailable comparison pairs show an unavailable comparison source-pack label and explicitly avoid factual citation chips or source drawers.
- Added source-context list styling in `styles/globals.css`.
- Extended frontend smoke checks to cover comparison source metadata markers, chip-to-source linkage markers, official-source display, freshness display, supporting passages, absence of live compare calls, absence of `/api/compare` calls from the fixture-backed compare page, and absence of `AAPL` sources in comparison metadata.
- Extended safety guardrail frontend-copy coverage to include `components/ComparisonSourceDetails.tsx` and `lib/compare.ts`.
- T-012 agent journal records that `npm test`, `npm run typecheck`, `npm run build`, focused comparison/API pytest, safety pytest, static evals, and the main quality gate passed. The initial `npm test` and `npm run typecheck` required one focused revision to make smoke citation markers literal and narrow the comparison bottom-line value.
- Remaining documented risk: comparison source rendering remains deterministic and fixture-backed for the existing local `VOO` vs `QQQ` / `QQQ` vs `VOO` comparison pack only.
- Remaining documented risk: frontend coverage is static smoke coverage plus build/typecheck; it does not browser-click citation chips to verify scrolling or focus behavior.

Completion commits:

- `b5f1d1d feat(T-012): render comparison source metadata on compare page`
- `ecacb1b chore(T-012): merge render comparison source metadata on compare page`

### T-011: Add comparison source metadata contract

Goal:
Expose source-document metadata for comparison citations so UI clients can render source drawer details for generated comparison answers without making unsupported assumptions from citation IDs alone.

Completed:

- Added `source_documents` to `CompareResponse`.
- Updated deterministic comparison generation so citation bindings carry both citation metadata and full `SourceDocument` metadata built from same-pack comparison source fixtures.
- Supported `VOO` vs `QQQ` comparison responses now include deduplicated source-document metadata for cited comparison facts and supporting chunks.
- Reverse-order `QQQ` vs `VOO` comparison responses include source-document metadata bound to the reversed local comparison pack and selected assets.
- Unavailable, unsupported, and unknown comparison responses return empty key differences, no beginner bottom line, no factual citations, and no source documents.
- Comparison validation now checks source metadata after citation validation and rejects missing citation metadata, wrong-asset source documents, stale sources, unsupported source types, and empty supporting passages.
- Backend route tests cover serialized `/api/compare` source metadata, including source document ID, title, publisher, source type, URL, published or as-of date, retrieved timestamp, freshness state, official-source flag, and supporting passage.
- Unit tests cover schema-valid source-backed comparison metadata, reverse-order metadata, unavailable responses with no metadata, and validation failures for missing, wrong-asset, stale, unsupported, and insufficient source metadata.
- Static evals cover comparison source metadata same-pack binding, reverse-order source binding, required source metadata fields, unavailable responses with no source metadata, and no live external calls.
- T-011 agent journal records that focused comparison/API tests, static evals, backend compile check, and the main quality gate passed.
- Remaining documented risk: comparison source metadata is deterministic and fixture-backed for the existing local `VOO` vs `QQQ` comparison pack only.
- Remaining documented risk: UI rendering of comparison `source_documents` was intentionally not included in this backend/API contract task.

Completion commits:

- `f9313b1 feat(T-011): add comparison source metadata contract`
- `e9b9c7f chore(T-011): merge comparison source metadata contract`

### T-010: Add asset page chat panel for fixture-backed assets

Goal:
Add a beginner-facing asset page chat panel that calls the grounded chat API for fixture-backed supported assets and renders citations, source metadata, advice redirects, unsupported states, and insufficient-evidence states.

Completed:

- Added `AssetChatPanel` to asset pages for fixture-backed assets and wired `app/assets/[ticker]/page.tsx` to render it.
- Added a client-side chat workflow with starter prompts, text input, submit control, empty state, loading state, error state, answer state, and explicit advice redirect, unsupported or unknown, and insufficient-evidence labels.
- Added `lib/assetChat.ts` with typed chat response shapes and an injectable `postAssetChat` helper that calls the local relative `/api/assets/{ticker}/chat` endpoint.
- Rendered supported chat answers with direct answer, `why_it_matters`, uncertainty notes, citation chips, and chat source metadata details including title, source type, publisher, published or as-of date, retrieved timestamp, freshness state, official-source badge, source URL, chunk/source IDs, and supporting passage.
- Rendered no-citation copy for educational redirects, unsupported states, and insufficient-evidence states without inventing factual claims.
- Frontend smoke checks now cover the chat panel, local endpoint helper, chat state markers, source metadata hooks, educational redirect copy, unsupported or unknown copy, insufficient-evidence copy, and no live external chat URLs.
- Safety guardrail tests include the new asset chat panel in frontend copy checks.
- T-010 agent journal records that `npm test`, `npm run typecheck`, `npm run build`, static evals, and the main quality gate passed. The initial `npm test` failed because the new smoke check rejected existing fixture source URLs; the check was narrowed to the new chat helper/component and passed on rerun.
- Remaining documented risk: the frontend chat helper uses the local relative `/api/assets/{ticker}/chat` path, so deployment still needs the frontend and backend served or proxied so that path resolves at runtime.
- Remaining documented risk: frontend coverage is static smoke coverage, not browser automation of typed questions and rendered network responses.

Completion commits:

- `6f51ae2 feat(T-010): add asset page chat panel for fixture-backed assets`
- `167f1b9 chore(T-010): merge asset page chat panel for fixture-backed assets`

### T-009: Add chat source metadata contract

Goal:
Expose source-document metadata for grounded chat citations so UI clients can render source drawer details for chat answers without making unsupported assumptions from citation IDs alone.

Completed:

- Added chat source metadata fields to the backend response models.
- Grounded chat responses now include source-document metadata derived from the selected asset knowledge pack.
- Chat source metadata includes citation ID, source document ID, title, source type, URL, as-of date, retrieved timestamp, freshness state, stale flag, and supporting passage where available.
- Supported grounded chat responses for `AAPL`, `VOO`, and `QQQ` include source metadata for grounded citations.
- Advice-like redirects, unsupported assets, unknown assets, and insufficient-evidence responses continue to return no generated factual citations or source metadata.
- Chat validation now checks response source metadata against selected-pack citation evidence.
- Backend route tests cover the serialized `source_documents` shape.
- Static evals cover chat source metadata same-asset binding and no live external calls.
- T-009 agent journal records that the focused pytest slice, static evals, and main quality gate passed.
- Remaining documented risk: chat source metadata remains deterministic and fixture-backed for the current supported assets.
- Remaining documented risk: UI rendering for the new chat `source_documents` field was not changed in this backend-only task.

Completion commits:

- `8306738 feat(T-009): add chat source metadata contract`

### T-008: Add grounded asset chat pipeline

Goal:
Generate asset-specific chat responses from selected asset knowledge packs, citation mappings, and safety classification.

Completed:

- Added deterministic grounded chat generation in `backend/chat.py`.
- Backend `/api/assets/{ticker}/chat` now uses the grounded chat pipeline for fixture-backed supported assets.
- Supported educational chat works for `AAPL`, `VOO`, and `QQQ`.
- Chat intent handling covers asset identity, stock business basics, ETF holdings or benchmark basics, ETF cost or breadth questions, top risks, recent developments, and beginner educational suitability framing.
- Generated supported chat responses include canonical asset identity, a direct answer, `why_it_matters`, citations when evidence exists, source-backed uncertainty or limits notes, and an educational safety classification.
- Chat citation binding is restricted to source documents and chunks from the selected asset knowledge pack.
- Advice-like questions continue to redirect into educational framing without generated factual claims or citations.
- Unsupported and unknown assets continue to return clear unsupported-scope or unknown states without generated factual claims.
- Static evals and tests cover schema validity, supported chat intents, same-asset citation binding, advice redirects, unsupported states, insufficient-evidence behavior, safety phrasing, and no live external calls.
- T-008 agent journal records that focused chat tests, the required safety/API test slice, static evals, and the main quality gate passed.
- Remaining documented risk: chat generation is deterministic and fixture-backed for `AAPL`, `VOO`, and `QQQ`; unsupported, unknown, or non-fixture-backed assets intentionally return redirect or insufficient-evidence states.
- Remaining documented risk: intent handling is narrow by design and covers only the beginner intents required for this task.
- Remaining documented risk: `ChatResponse` still exposes chat citations as source document and chunk IDs rather than full source-document metadata; richer source drawer behavior would need a later schema/UI extension.

Completion commits:

- `37e6f59 feat(T-008): add grounded asset chat pipeline`
- `dbbab3c chore(T-008): merge grounded asset chat pipeline`

### T-007: Add comparison generation pipeline

Goal:
Generate beginner comparison responses from structured local facts, comparison knowledge packs, source metadata, and citation mappings.

Completed:

- Added deterministic comparison generation in `backend/comparison.py`.
- Backend `/api/compare` now uses `generate_comparison` for fixture-backed comparison responses.
- Supported `VOO` vs `QQQ` comparison generation works in either ticker order.
- Generated ETF comparison responses include canonical left/right assets, supported state, `etf_vs_etf` type, key differences for benchmark, expense ratio, holdings count, breadth, educational role, a beginner bottom line, and citations.
- Comparison citation binding maps generated citation IDs to same-pack source documents, normalized facts, and source chunks from the local comparison knowledge pack.
- Comparison validation covers generated responses and planned claims, including missing citations, wrong-asset citations, stale sources, unsupported source types, and insufficient evidence.
- Unsupported, unknown, or unavailable comparison requests return `unavailable` comparison state without key differences, bottom-line content, or citations.
- Static evals now include the generated comparison contract, reverse ticker order, unavailable states, same-pack citation binding, safety phrase checks, and no network-client imports.
- Focused unit and integration tests were added for comparison generation and `/api/compare`.
- T-007 agent journal records that focused comparison/API tests, static evals, backend compile check, and the main quality gate passed.
- Remaining documented risk: comparison generation is deterministic and fixture-backed for `VOO` vs `QQQ` only; other supported ticker pairs intentionally return an unavailable comparison state until a local comparison pack exists.
- Remaining documented risk: `CompareResponse` exposes citation metadata but not full comparison source documents, so source drawer-style rendering would need a later schema/UI extension if required.

Completion commits:

- `46b05f2 feat(T-007): add comparison generation pipeline`
- `285948d chore(T-007): merge comparison generation pipeline`

### T-006: Add asset overview generation pipeline

Goal:
Generate beginner asset overview responses from structured local facts, source metadata, and citation mappings.

Completed:

- Deterministic overview generation exists in `backend/overview.py`.
- Supported overview generation works for fixture-backed `AAPL`, `VOO`, and `QQQ`.
- Generated overviews include canonical identity, state, freshness metadata, snapshot fields, beginner summary, exactly three top risks, separated recent developments, suitability summary, claims, citations, and source documents.
- Citation IDs generated for claims, summary facts, risks, and recent developments resolve to same-asset sources.
- Unsupported and unknown assets return explicit states without generated factual claims, invented summaries, or citations.
- Backend asset overview, source, and recent routes use generated overview output for fixture-backed assets.
- Tests and static evals cover schema validity, citation coverage, top-risk count, freshness fields, stable/recent separation, unsupported states, safety language, and no live external calls.
- Existing retrieval fixture tests, citation validation, safety evals, backend route tests, frontend smoke checks, static evals, and quality gate behavior pass.

Completion commits:

- `0f4fd70 feat(T-006): add asset overview generation pipeline`
- `910761c Merge pull request #6 from doyleyeh/agent/T-006-20260420T214313Z`

### T-005: Add source-backed retrieval fixtures

Goal:
Create local fixture data and retrieval contracts for supported stocks and ETFs without live external calls in CI.

Completed:

- Local retrieval fixture data exists in `data/retrieval_fixtures.json` for `AAPL`, `VOO`, and `QQQ`.
- Retrieval models and services exist in `backend/retrieval.py`.
- Asset knowledge packs include canonical identity, source document metadata, stable chunk IDs, normalized facts, freshness fields, recent-development layer data, and explicit evidence gaps.
- Single-asset retrieval is filtered to the requested asset and does not return wrong-asset evidence.
- Comparison retrieval builds a bounded `VOO` vs `QQQ` comparison pack.
- Tests and static evals check fixture shape, source linkage, asset filtering, freshness metadata, explicit evidence states, and no network-client imports.
- Existing citation validation, safety evals, backend route tests, frontend smoke checks, static evals, and quality gate behavior pass.

Completion commits:

- `ef731a3 agent(T-005): implement current task`
- `92c54c9 Merge pull request #5 from doyleyeh/agent/T-005-20260420T205818Z`

### T-004: Add safety guardrail tests

Goal:
Add deterministic safety guardrail tests and eval coverage that detect buy/sell/hold recommendation leakage, personalized allocation advice, unsupported price targets, tax advice, brokerage/trading behavior, and certainty around future returns.

Completed:

- Safety eval cases cover direct buy/sell/hold questions, allocation or position sizing, unsupported price targets, tax advice, brokerage/trading execution, future-return certainty, unsupported assets, and safe educational prompts.
- Static safety evals check backend chat outputs and forbidden output phrases, not only fixture structure.
- Backend chat tests verify advice-like questions redirect into educational framing and return no citations unless grounded in supported asset facts.
- Safety tests assert forbidden phrases do not appear in backend responses, frontend copy, fixture summaries, or comparison output.
- Safe educational prompts continue to produce grounded educational responses.
- Unsupported asset prompts redirect into clear unsupported-scope language.
- Existing citation validation, backend route, frontend smoke, static eval, and quality gate behavior pass.

Completion commits:

- `3be6ff1 agent(T-004): implement current task`
- `08f68d0 Merge pull request #4 from doyleyeh/agent/T-004-20260420T182024Z`

### T-003: Add citation validation module

Goal:
Add a citation validation module that verifies generated or fixture-backed claims only cite source documents, chunks, or normalized facts that belong to the same asset or comparison pack and support the claim type.

Completed:

- Citation validation module exists in `backend/citations.py`.
- Validator accepts structured claims, citation IDs, source evidence, and asset or comparison-pack context.
- Validator rejects missing citations, nonexistent citations, wrong-asset citations, non-recent sources for recent claims, stale unlabeled sources, unsupported source types, and insufficient evidence.
- Citation eval cases are exercised by deterministic static evals and unit tests.
- Tests cover single-asset claims, comparison claims, recent-development claims, stale/unknown states, and wrong-asset citations.
- Existing backend, frontend, static eval, and quality gate behavior pass.

Completion commits:

- `98be660 agent(T-003): implement current task`
- `78a6508 fix: skip codex review without api key`
- `72535b7 Merge pull request #3 from doyleyeh/agent/T-003-20260420T054020Z`

### T-002: Create frontend Next.js skeleton

Goal:
Create the initial frontend structure for search, asset pages, comparison, citation chips, source drawer, freshness labels, stale/unknown states, and glossary popovers.

Completed:

- Next.js frontend app exists at the repo root using TypeScript.
- Routes exist for `/`, `/assets/[ticker]`, and `/compare`.
- Home page provides a ticker search workflow with supported, unsupported, unknown, and example states.
- Asset page renders deterministic fixture-backed stable facts, recent developments, exactly three top risks, citation chips, freshness labels, source drawer, glossary popovers, and stale/unknown treatment.
- Compare page renders a deterministic `VOO` vs `QQQ` comparison.
- Frontend copy stays educational and avoids buy/sell/hold, allocation, price target, tax, and brokerage behavior.
- Frontend smoke checks and Next build run in the quality gate.
- `package-lock.json` is committed so CI can run `npm ci`.
- Normal tests and CI make no live external calls.

Completion commits:

- `1164a3d agent(T-002): implement current task`
- `098f7ac fix: make frontend checks reproducible`
- `ec66cb2 Merge T-002 frontend skeleton`

### T-001: Create backend FastAPI skeleton

Goal:
Create the initial backend service structure for search, asset overview, sources, recent developments, compare, and asset-grounded chat endpoints.

Completed:

- Backend FastAPI app exists under `backend/`.
- Health, search, asset overview, details, sources, recent, compare, and chat endpoints exist.
- Endpoint responses use explicit typed models.
- Stub responses are deterministic and educational.
- Unsupported and unknown asset states are covered.
- Advice-like chat inputs are redirected into educational framing.
- Normal tests and CI make no live external calls.
- Backend route, schema, unsupported-state, and advice-boundary tests pass.

Completion commits:

- `61b2bd0 chore: fix codex exec approval flag`
- `7bfe0f6 agent(T-001): implement current task`
- `a27ea80 Merge pull request #2 from doyleyeh/agent/T-001-20260420T024831Z`

### T-000: Create agentic development scaffold

Goal:
Set up the files, tests, eval folders, scripts, and CI workflow needed for Codex-assisted development.

Completed:

- Core agent instruction files exist.
- Quality gate script exists.
- Agent loop script exists.
- Basic repo contract tests pass.
- Basic static evals pass.
- CI workflow runs the quality gate.
- Git commits are created by the harness, not directly by Codex.

Completion commits:

- `4be1fa3 chore: add agentic development scaffold`
- `c7e2004 chore: add agent loop retries`

## Backlog

### T-081: Add source snapshot artifact metadata contracts

Goal:
Add dormant source snapshot artifact metadata contracts for raw, parsed, generated, and diagnostics artifacts so future ingestion can reference private object storage safely while preserving rights-tiered source-use policy and no-public-snapshot behavior.

Acceptance criteria:

- Add repository/table metadata and pure model helpers for source snapshot artifact records, private object URIs, checksums, source-use policy, allowed operations, retrieval timestamps, and artifact categories.
- Enforce rights-tier behavior for `full_text_allowed`, `summary_allowed`, `metadata_only`, `link_only`, and `rejected` sources before any raw or parsed text field can be represented.
- Keep snapshots private and metadata-only by default; do not expose public URLs, browser-facing storage paths, unrestricted provider payloads, raw article text, or rejected-source content.
- Integrate with existing source allowlist/source-policy helpers and persisted knowledge-pack metadata only through dormant contracts or tests.
- Add tests for rights-tier storage rules, same-asset/source binding, checksum metadata, redacted diagnostics, and no live storage/network imports.

Required checks:

```bash
python3 -m pytest tests/unit/test_source_policy.py tests/unit/test_repo_contract.py -q
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

### T-082: Add SEC stock source adapter fixture contract

Goal:
Add a fixture-backed SEC stock source adapter and parser contract for identity, filings, company facts, source attribution, freshness, and evidence gaps without live SEC calls, generated-output changes, or broader stock coverage.

Acceptance criteria:

- Add adapter interfaces and deterministic fixture responses for SEC submissions, selected filing metadata, and XBRL company facts needed by existing stock knowledge-pack sections.
- Parse and normalize compact stock identity, business/filing references, financial fact metadata, source attribution, freshness labels, and evidence gaps into existing backend contract shapes or new dormant adapter records.
- Enforce same-asset CIK/ticker binding and source-use policy before any source can support generated claims.
- Keep top-500 manifest behavior unchanged and do not generate pages, chat answers, comparisons, or risk summaries for eligible-not-cached, unsupported, out-of-scope, unknown, or unavailable stocks.
- Add tests for fixture parsing, stale/unavailable/partial handling, same-asset source binding, source policy enforcement, no live network imports, and no secret exposure.

Required checks:

```bash
python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_retrieval_fixtures.py -q
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

### T-083: Add ETF issuer and holdings source adapter fixture contracts

Goal:
Add fixture-backed ETF issuer, fact-sheet, holdings, prospectus, and exposure-file adapter contracts for supported non-leveraged U.S.-listed equity ETFs without live issuer/provider calls, generated-output changes, or unsupported ETF expansion.

Acceptance criteria:

- Add adapter interfaces and deterministic fixture responses for issuer profile/fact-sheet metadata, prospectus references, holdings or exposure rows, benchmark/expense data, source attribution, freshness, and evidence gaps.
- Preserve ETF scope boundaries: non-leveraged U.S.-listed equity index, sector, and thematic ETFs only; leveraged, inverse, ETN, fixed-income, commodity, active, and multi-asset ETFs remain blocked from generated output.
- Enforce source-use policy, allowed excerpt behavior, same-ETF binding, freshness labels, and partial/unavailable states before facts can support generated claims.
- Do not add live network calls, browser provider calls, new generated pages, generated chat answers, generated comparisons, or unrestricted source exports.
- Add tests for fixture parsing, holdings/source binding, blocked ETF classes, source-policy enforcement, freshness/evidence gaps, no live imports, and no secret exposure.

Required checks:

```bash
python3 -m pytest tests/unit/test_provider_adapters.py tests/unit/test_retrieval_fixtures.py -q
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

### T-084: Add persisted generated-output cache and freshness-hash contracts

Goal:
Add dormant persisted generated-output cache contracts for overview, comparison, chat-safe answer artifacts, exports, source checksums, knowledge-pack hashes, generated-output freshness hashes, and invalidation diagnostics without routing current responses through the cache.

Acceptance criteria:

- Add pure repository/table metadata and model helpers for generated-output cache entries, section-level freshness hashes, source checksum inputs, knowledge-pack hashes, validation status, citation coverage, safety status, and invalidation reasons.
- Keep cache records tied to same-asset or same-comparison-pack evidence and existing source-use policy.
- Preserve current deterministic fixture fallback and current API/frontend behavior; no route should read from or write to a live cache in this task.
- Block cacheability for unsupported, out-of-scope, rejected-source, failed-validation, advice-like, uncited, stale-without-label, or source-policy-disallowed generated output.
- Add tests for hash stability, invalidation metadata, citation/source binding, safety/source-policy gating, no raw model reasoning, no hidden prompts, no secrets, and no live database dependency.

Required checks:

```bash
python3 -m pytest tests/unit/test_cache_contracts.py tests/unit/test_source_policy.py tests/unit/test_safety_guardrails.py -q
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

## MVP Backend Roadmap

This section is intentionally non-operational for the agent loop. Keep runnable repeat-mode tasks above this roadmap as third-level task headings, and keep this longer MVP roadmap as bullets until each item is promoted into a narrow task contract. Early backend tasks may add production dependencies such as SQLAlchemy, Alembic, or psycopg only with dependency rationale, focused tests, and no live external calls in normal CI.

Operational defaults for backend roadmap tasks:

- T-076 established the persistence boundary and migration tooling before provider or worker work starts. It is completed and must not be reintroduced as runnable backlog.
- T-077 established persisted knowledge-pack repository contracts. It is completed and must not be reintroduced as runnable backlog.
- T-078 routed retrieval through persisted packs with deterministic fixture fallback. It is completed and must not be reintroduced as runnable backlog.
- T-079 established the dormant persisted ingestion job ledger contract. It is completed and must not be reintroduced as runnable backlog.
- T-080 is the current promoted task and should add only the deterministic ingestion worker execution contract on top of injected ledger records.
- T-081 through T-084 are prepared backlog tasks promoted from the roadmap in a safe order.
- Later promoted tasks must keep live providers, secrets, deployment credentials, and recurring jobs out of normal CI until the explicit production-hardening stage.
- Each promoted backend task should run the relevant EVALS.md backend checks: `python3 -m pytest tests -q`, `python3 evals/run_static_evals.py`, and `bash scripts/run_quality_gate.sh`.

Roadmap integration tracker:

| Roadmap area | Status | Task mapping |
| --- | --- | --- |
| Persistence settings and migration scaffold | Completed | T-076 |
| Persisted knowledge-pack repository contracts | Completed | T-077 |
| Persisted-pack-first retrieval with fixture fallback | Completed | T-078 |
| Ingestion job ledger | Completed | T-079 |
| Deterministic ingestion worker execution path | Promoted | T-080 |
| Source snapshot storage metadata | Backlog | T-081 |
| SEC stock source adapter/parser | Backlog | T-082 |
| ETF issuer, holdings, prospectus, and exposure adapters | Backlog | T-083 |
| Generated-output cache and freshness hashes | Backlog | T-084 |
| Route overview, comparison, and chat generation through persisted packs | Roadmap only | Not yet promoted |
| Persist accountless chat sessions and transcript exports | Roadmap only | Not yet promoted |
| Trust-metric event sink | Roadmap only | Not yet promoted |
| Broaden launch-universe search and support classification | Roadmap only | Not yet promoted |
| Weekly News Focus acquisition from persisted evidence | Roadmap only | Not yet promoted |
| Gated OpenRouter live generation | Roadmap only | Not yet promoted |
| Provider source-use/export enforcement hardening | Roadmap only | Not yet promoted |
| Production hardening and deployment documentation | Roadmap only | Not yet promoted |

Remaining unpromoted backend MVP sequence:

- Route overview, comparison, and chat generation through persisted knowledge packs while preserving fixture fallback and current safety/citation behavior.
- Persist accountless chat sessions, seven-day TTL metadata, deletion state, and transcript export payloads without raw transcript analytics or training storage.
- Add a trust-metric event sink for compact metadata events covering citation coverage, unsupported claims, freshness accuracy, glossary use, comparison use, source drawer use, safety redirects, export use, and latency.
- Broaden launch-universe search and support classification from the versioned manifest and eligible ETF metadata, with blocked generated output for unsupported and out-of-scope assets.
- Add Weekly News Focus acquisition, windowing, dedupe, source ranking, empty/limited states, and AI Comprehensive Analysis thresholds from persisted recent-event evidence.
- Add gated OpenRouter live generation behind `LLM_LIVE_GENERATION_ENABLED=true`, with schema, citation, source-policy, safety validation, repair retry, paid fallback metadata, and no raw reasoning exposure.
- Enforce source-use and export rules for provider content, including metadata-only, link-only, summary-allowed, full-text-allowed, and rejected tiers.
- Harden production surfaces with admin auth, rate limits, CORS, Secret Manager, Cloud Run Jobs, private GCS object URIs, Vercel API wiring, and deployment documentation.
