# Desktop migration guide

The approved reboot replaces hosted Next.js with a local React/Vite/Tauri application. No installed-user migration compatibility is required for the old fixture app. User evidence created by the new desktop app must be protected from schema and application changes.

## Completed structural changes

- Frontend workspace moved from apps/web to apps/desktop; npm commands delegate there.
- React components, financial reference contracts and styling are retained in place, with a new dynamic production entry under src.
- The production API is backend/app; the fixture-only backend/main.py is not mounted.
- Shared contracts generate JSON Schema and TypeScript from Pydantic.
- SQLAlchemy records and Alembic initial migration provide durable local storage.
- Immutable evidence, saved reports, scoped conversations and term explanations persist in the desktop library. Portable full-library backup/restore has passed isolated PostgreSQL and synthetic-browser checks.
- The seven canonical root documents own requirements, decisions, plan, tasks, validation and live status as defined in [AGENTS](../AGENTS.md). This guide owns compatibility; superseded documents and original evidence are preserved under docs/archive/2026-10-04.

## Removal rules

Next routes/build configuration, hosted deployment scaffolding and the old agent-loop framework have been removed. The automatic API-key Codex PR-review workflow is also retired; normal CI remains deterministic. Its [review prompt](../.github/codex/prompts/review.md) is maintained for explicitly requested manual reviews.

Preserve useful financial components and algorithm tests until feature parity exists. `apps/desktop/components` and `lib` contain retained UX and reference contracts, only some of which are used by the new entrypoint. The flat `backend/*.py` modules, `data/universes/us_common_stocks_top500.current.json`, `config/source_allowlist.yaml` and legacy evaluation contracts remain regression dependencies. They do not define desktop coverage, active source policy or a production model fallback. The production service only reuses the flat safety module. Move useful behavior into application services and migrate its tests before deleting the remaining dependencies. Do not keep duplicate legacy trees for history.

## Database and library compatibility

The preview supports Alembic revision `0001` only. Unknown/future revisions and unrecognized non-empty databases refuse startup. Initial creation is implemented; coordinated application/schema upgrades and downgrades are not. Future migrations require a backup restored into a separate cluster and verified before activating the new app/schema pair. Preserve the pre-migration app and library. Do not silently overwrite newer research with an older snapshot.

The implemented `.lttbackup` format version `1` contains `manifest.json` and `library.json`, not a filesystem copy or SQL script. It includes current database-held records, immutable evidence/term versions, conversations, reports, jobs and normalized events. It validates checksums, schema and references, and permits at most 128 MiB compressed / 256 MiB JSON content. These limits differ from the future 10 GB disposable-document cache policy. Future attachment storage must extend the format before shipping; existing archives cannot be assumed to include it.

Restore requires an empty destination library and the fingerprint of the previewed archive. Writes commit atomically. Restored pending jobs become interrupted without replay; cloud research and start-at-login reset to off. Credentials, provider profiles, environment files and raw runtime traces are excluded. On another computer provision new local database credentials and reconnect providers. This protects existing destination work by refusing overwrite, but does not implement an application rollback manager or merge two libraries. See [restore tests](../EVALS.md#portable-backup-and-restore).

M1 model selection adds an optional model identifier to Settings records. Missing values in older libraries/archives mean the provider's current default; no SQL schema change is required. Current restoration preserves an explicit selection while disabling cloud research, then revalidates model availability on the next request. Older application versions may reject the new record field; backward app rollback is not qualified by this additive data change. Coordinated app/archive compatibility remains M10 work.

M2 admission adds optional `level` and `identity_verification` fields to evidence bundles. Older snapshots default both to null and stay immutable/readable; no old model-provided identity is retroactively verified. New proofs bind the full asset identity and their independent source fingerprint/date. Archive validation rejects mismatched identity hashes; the PostgreSQL restore scenario includes both a legacy snapshot and a new proof/reader level through restart. No SQL revision or archive version changes. These fingerprints establish internal consistency, not archive authorship. Online reuse independently rechecks identity and freshness. Older applications may reject the new fields; coordinated rollback remains M10 acceptance.

## Native packaging and platforms

The current source setup installs Python/frontend dependencies after the developer provides Python and Node. Native launch additionally requires Rust/MSVC, webview prerequisites and an explicit `LTT_PG_BIN` directory. The optional Docker Compose database is not the private desktop cluster. The public installer must remove the need for users to install or operate core Python, Node, Docker or PostgreSQL dependencies themselves.

On native Windows x64, run `.venv/Scripts/python.exe scripts/package_backend.py` to build `dist/ltt-service.exe` and copy it to `apps/desktop/src-tauri/binaries/ltt-service-x86_64-pc-windows-msvc.exe`. The script does not download PostgreSQL or provider runtimes. `npm run desktop:build` expects a reviewed PostgreSQL runtime under `apps/desktop/src-tauri/resources/postgres` as well as that sidecar. Building the sidecar is not equivalent to building or validating an installer. Native compilation, runtime redistribution, release artifact signatures and OS signing remain open.

Private-cluster checks have used PostgreSQL 17 binaries without changing their existing system service or data. Do not point another major version at an existing cluster without a qualified migration. Build and qualify packages separately in this order: native Windows, macOS, Windows with WSL, Linux. The Windows/Ubuntu unit-CI matrix does not establish desktop platform support.

## Remaining release migration work

Retained financial UI parity, structured adapters, imports, complete subscription runtime isolation/authentication, larger/attachment-aware backups, full cache/deletion controls, coordinated upgrades/rollback and self-contained distribution remain explicit tasks. Use [STATUS.md](../STATUS.md) for the current state and evidence pointers; [PLAN](../PLAN.md), [TASKS](../TASKS.md) and [EVALS](../EVALS.md) own dependencies, acceptance and checks. No public release is complete until all three providers and the packaged Windows workflow pass.
