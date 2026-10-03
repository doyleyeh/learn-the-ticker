# Learn the Ticker

A local, citation-first financial research and learning application using your own commercial agent subscription. Your evidence, conversations and research belong in your local library.

**Status: desktop developer preview, not public v1.** The approved stack is Tauri 2, React/TypeScript/Vite, packaged FastAPI and private PostgreSQL. Native Windows comes first, followed by macOS, Windows with WSL, then Linux. The product serves beginner and intermediate users across dynamically resolved asset types; there is no fixed ticker eligibility list.

Working preview features include the local library, evidence versions and citations, cached search, conversations and bookmarks, term explanations, personal exports and portable backup/restore. Structured financial retrieval, imports, charts, comparisons and several release features are still being integrated. Codex and Claude transports are experimental; Gemini execution is disabled pending safe tool qualification. No live subscription integration or native installer has passed release acceptance. See [implementation status](STATUS.md) for the complete record.

## Development on Windows

Use Python 3.12 and Node 22.13+ (22.x) or Node 24+ for development; native builds also need Rust/MSVC and the Windows webview prerequisites. PostgreSQL 17 binaries were used in the local lifecycle tests. Other major versions have not been qualified. The future end-user installer must bundle the core dependencies and handle provider prerequisites explicitly.

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
$env:LTT_PG_BIN = 'C:/Program Files/PostgreSQL/17/bin'
npm run desktop
```

Setup creates `.venv` and installs Python/frontend dependencies; it does not install Python, Node, Rust/MSVC, PostgreSQL or provider CLIs. `.env.example` is guidance, not an automatically loaded desktop configuration. The supervisor creates its own cluster and does not use an existing PostgreSQL service. The native launcher source still needs Rust/MSVC build and window/tray validation; these commands are not a claim of a verified installer.

`npm run dev` starts only the frontend at `http://127.0.0.1:1420`; `npm start` previews the built frontend. Neither starts a database or backend. For a reproducible browser-only demonstration without subscriptions, use the [synthetic preview instructions](EVALS.md#synthetic-browser-preview). Docker Compose is optional database development support and is not connected to the desktop supervisor.

`scripts/package_backend.py` builds the Windows x64 sidecar separately. `npm run desktop:build` additionally needs that sidecar and a reviewed PostgreSQL runtime under the Tauri resources directory; it does not provision them. See [packaging and migration](docs/MIGRATION.md#native-packaging-and-platforms).

## Connect Codex

The implemented Codex setup flow is **Connections → Sign in with ChatGPT**, using an installed official Codex runtime and a dedicated provider-owned profile. Follow the provider's device-code flow; cloud research permission is separate. A fresh-profile protocol handshake and synthetic sign-in tests passed, but actual account authorization and inference remain unverified. Gemini and Claude onboarding, supported-version ranges and full tool isolation still need qualification. Public v1 requires all three subscription connections; there is no API-billing or automatic provider fallback.

## Learn terms

On an asset page, choose a core term, type one or select a short phrase in the evidence to request an explanation. Saved explanations and curated English definitions remain usable offline. Generated interpretations carry their evidence version, language, date and citations when supplied; they never become factual evidence. Hover only reuses saved material.

## Checks

Run the quality gate after a change. The other checks are explicit, separate operations; PostgreSQL checks create isolated disposable libraries.

- `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1`
- `.venv/Scripts/python.exe scripts/smoke_local_service.py` for an explicit, isolated PostgreSQL lifecycle check.
- `.venv/Scripts/python.exe -m scripts.smoke_database` for private PostgreSQL transaction rollback, recovery and durable restart checks.
- `.venv/Scripts/python.exe -m scripts.smoke_restore` for a full-library round trip between isolated PostgreSQL clusters.
- `.venv/Scripts/python.exe -m scripts.smoke_codex_protocol` for an explicit installed-runtime handshake with no login or inference.
- `.venv/Scripts/python.exe -m scripts.contracts`, then `node scripts/generate_types.mjs` after contract changes.

Normal CI runs deterministic tests and contract drift checks on Windows and Ubuntu. It makes no live research or subscription calls. Live compatibility checks and native installer checks are separate and must pass before release. Ubuntu CI does not certify a Linux desktop release.

## Back up and move a library

Connections offers a full-library download, archive validation and restore into an empty library. Current archives preserve database-held evidence versions, reports, conversations, term explanations, jobs and settings. They exclude credentials and provider sign-ins. Restore resets cloud research and start-at-login to off; reconnect the provider on the destination computer. Existing work is never overwritten. Current archive limits and the unfinished application/schema rollback work are described in [the migration guide](docs/MIGRATION.md#database-and-library-compatibility).

## Documentation

Start with [STATUS](STATUS.md) for current work and evidence, then [AGENTS](AGENTS.md) for document ownership and durable rules.

| Document | Responsibility |
| --- | --- |
| [SPEC](SPEC.md) | Required product behavior and public-v1 definition of done |
| [DECISIONS](DECISIONS.md) | Accepted architecture, defaults and significant decisions |
| [PLAN](PLAN.md) | Milestone dependencies, scope and acceptance |
| [TASKS](TASKS.md) | Actionable task states and required checks |
| [EVALS](EVALS.md) | Fast, milestone and full verification commands/scenarios |
| [STATUS](STATUS.md) | Current milestone/task, results, blockers and next action |
| [Technical design](TECHNICAL_DESIGN_SPEC.md) | Mechanisms and implementation limitations |
| [Migration](docs/MIGRATION.md) | Compatibility and packaging transition |
| [Audit](docs/project-audit.md) | One-time document/implementation audit and requirement mapping |
| [Contributing](CONTRIBUTING.md) / [delivery skill](.codex/skills/project-delivery/SKILL.md) | Development procedure |

Use the shared fast check with `python -m scripts.verify fast`; the existing PowerShell/Bash quality gate runs the milestone tier. `python -m scripts.verify full` additionally requires PostgreSQL, native packaging resources and Rust/MSVC; it does not replace live-provider or clean-machine acceptance. The delivery skill provides equivalent portable wrappers. CI uses these same underlying checks; the manual full-evals workflow adds isolated PostgreSQL verification. See EVALS for prerequisites and currently missing release evidence.

Requirements describe the destination; STATUS records verified progress. Historical documents retain original dates under docs/archive/2026-10-04.

This is educational software, not investment advice or a trading application. Distribution is Apache-2.0; data and runtime dependencies retain their own terms.
