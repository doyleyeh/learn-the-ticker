# Foundation verification — 2026-10-04

Baseline: branch codex/project-delivery-foundation, starting commit 2fd187f. This record applies to M0; historical provider/browser/packaging results are not rerun or promoted here.

## Passed

- Canonical migration preserves all 22 P-series requirement IDs and maps D01–D21. Five historical documents retain original dates under docs/archive/2026-10-04. Local Markdown links/anchors passed; no duplicate active requirement/backlog source remains.
- The project-delivery skill passed the bundled skill-creator quick validator. Only the requested skill is unignored; the pre-existing empty read-only .codex placeholder was preserved under ignored .local storage.
- Final PowerShell milestone gate passed: Ruff, ESLint, non-writing Pydantic/TypeScript drift checks, documentation links, whitespace checks, 285 Python tests, retained static evaluations, seven frontend tests, TypeScript and Vite production build.
- Seven verification-helper scenarios passed: first-failure stop/code preservation, missing PostgreSQL diagnostics, broken links/anchors, unchanged generated-file bytes/mtime, and PowerShell fast/milestone/full wrapper failure propagation. The Git Bash fast wrapper passed; an actual Git Bash invalid-command run propagated exit 2.
- Actual isolated PostgreSQL D lane passed source service readiness/authentication/clean shutdown, duplicate library locking, atomic rollback/publication, surviving-cluster recovery, restart persistence and full-library restore. Restore retained saved/current versions, conversations, terms and events; rejected non-empty destinations and interrupted pending jobs without replay. No system cluster/service was changed.
- npm ci and package audit completed with zero reported vulnerabilities. Exact new development dependencies: Ruff 0.16.10, ESLint 10.12.0 and @typescript-eslint/parser 8.71.0. All report MIT; no application runtime dependency was added. Ruff is explicitly excluded from PyInstaller.
- Both GitHub workflow files parsed as YAML and were inspected. Normal CI delegates to the same milestone dispatcher; manual full-evals invokes the isolated database lane with read-only repository permissions.

## Repairs and limitations

Focused lint exposed a missing typing.Any import in retained backend/sources.py; the import was added without algorithm changes. Initial npm dependency saving failed opening the workspace manifest (UNKNOWN); declaring the exact dependencies explicitly, regenerating the lockfile and running npm ci succeeded. Registry metadata showed ESLint 9 end-of-support, so the foundation uses supported ESLint 10 and documents its Node requirement.

The existing Starlette/httpx test-client deprecation remains non-blocking. Git emitted platform line-ending normalization notices; whitespace checks passed. No broad formatter baseline is claimed.

The full wrapper failed closed at missing cargo, as expected; this is a real release blocker, not a passing native check. No Tauri build, packaged rebuild, clean-machine install, new UI browser acceptance or live provider inference was performed in M0. PostgreSQL smoke success does not qualify runtime redistribution or an installer. Hosted GitHub workflows were not dispatched; only their local underlying checks and definitions were verified. B/L/W and remaining native/update checks stay incomplete in EVALS.

## Handoff

M0 is recorded by the foundation checkpoint. Next: M1-T01, qualified provider capability reporting before broader provider functionality. Existing runtime discovery can report generation/approvals from version detection; tests and enforcement must distinguish installed, authenticated and qualified states.
