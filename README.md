# Learn the Ticker

A local, citation-first financial research and learning application using your own commercial agent subscription. Your evidence, conversations and research belong in your local library.

**Status: desktop developer preview, not public v1.** The approved stack is Tauri 2, React/TypeScript/Vite, packaged FastAPI and private PostgreSQL. Native Windows comes first, followed by macOS, Windows with WSL, then Linux. The product serves beginner and intermediate users across dynamically resolved asset types; there is no fixed ticker eligibility list.

Working preview features include the local library, evidence versions and citations, cached search, conversations and bookmarks, term explanations, personal exports and portable backup/restore. Structured financial retrieval, imports, charts, comparisons and several release features are still being integrated. Codex and Claude transports are experimental; production inference is disabled until exact runtime versions pass live/tool qualification. Gemini execution also awaits its safe transport. Cached features and the synthetic preview remain available. No live subscription integration or native installer has passed release acceptance. See [implementation status](STATUS.md) for the complete record.

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

The implemented Codex setup flow is **Connections → Sign in with ChatGPT**, using an installed official Codex runtime and a dedicated provider-owned profile. Follow the provider's device-code flow; cloud research permission is separate. Dedicated Windows sign-in, initial live probes and subsequent local sandbox repair checks passed on 2026-10-04, but complete subscription qualification remains outstanding; production generation stays disabled. See [the initial acceptance evidence](docs/verification/2026-10-04-authenticated-codex.md) and [the sandbox repair](docs/verification/2026-10-04-codex-loopback-repair.md). Gemini and Claude onboarding, supported-version ranges and full tool isolation still need qualification. Public v1 requires all three subscription connections; there is no API-billing or automatic provider fallback.

Connections also offers model discovery and explicit selection; missing models fail without fallback. A provider-reported model change stops the active run before an answer is published and preserves your saved selection. Access review supports denial or cancellation within the research policy and cannot authorize shell/file/broader network grants. These controls do not enable generation before live qualification.

A pending command/file request can reach access review. Continuing after denial requires the provider to confirm that the action was declined; execution output or unresolved activity stops the run without publishing an answer. The approved restricted-catalog repair retains the selected model and removes metadata-driven execution tools. Research may request a permission review, which can only deny or cancel; cached explanations expose no intended tools. Catalogs are temporary and validated before inference. Complete live qualification remains separate.

The adapter separates Codex progress commentary from completed answers before research or term JSON validation. Failed, cancelled or malformed message sequences publish no candidate answer. This has deterministic regression coverage; selected-model live acceptance remains part of qualification.

When the native development toolchain is unavailable, run `.venv/Scripts/python.exe -m scripts.connect_codex` yourself in an interactive terminal to authorize the same dedicated Windows profile without starting inference. It opens the official device-code page; do not redirect or save the code. It never imports your developer Codex credentials. Then `.venv/Scripts/python.exe -m scripts.qualify_codex` performs a no-inference preflight. The separate `--live` option consumes subscription usage for explicit probes and requires current included-usage permission; read [the live qualification procedure](EVALS.md#codex-subscription-qualification) first. Passing probes never automatically enables production capabilities.

The separate `scripts.qualify_codex_acceptance` developer helper checks independent source-quote retrieval, live consent revocation and an owned-provider disconnect, using a disposable test library. It also defaults to preflight only; `--live --model MODEL_ID` explicitly consumes included subscription usage after the same guards. These checks do not replace source-rights review, PostgreSQL restore or installer acceptance.

`scripts.qualify_codex_tools` defaults to the same no-inference preflight. Its explicit `--live --model MODEL_ID` checks actual deny/cancel permission requests, restricted-catalog cleanup, independent source support and cached-only behavior after fresh sandbox enforcement. Model-reported tool lists are corroborating observations, not authoritative inventory or automatic qualification. Read [EVALS](EVALS.md#codex-subscription-qualification) before invoking live checks.

`.venv/Scripts/python.exe -m scripts.qualify_codex_inventory --model MODEL_ID` inspects the installed Windows binary's complete tool declaration using fresh credential-free profiles and a local test listener. The authenticated metadata process closes first; no account traffic is intercepted, no cloud inference/tool execution occurs and only names/hashes are reported. Its result needs the separate live checks and [transport-equivalence review](docs/verification/2026-10-04-codex-wire-inventory.md); it does not enable production capabilities.

The helper distinguishes a missing/unstartable runtime, an unverifiable version and a version not reviewed for this project. A Codex desktop agent may have its bundled runtime on PATH while an ordinary PowerShell terminal does not. Check `Get-Command codex` in the terminal used for sign-in; merely having a working development chat does not establish that terminal's runtime availability. Keep the app's dedicated profile and OS credential storage separate from the development profile.

Inspect the native sandbox with `.venv/Scripts/python.exe -m scripts.setup_codex_sandbox`. Inspection requests no setup or inference. After approving the provider's administrator-level sandbox accounts, filesystem permissions and firewall changes, run the same command with `--apply` in an interactive terminal. It configures the dedicated app profile and requests elevated mode without project write roots; the provider-managed Windows accounts are shared across native profiles. It never falls back to a weaker mode. The provider's minimal `[windows] sandbox = "elevated"` configuration is accepted; additional configuration still blocks the connection. Setup success only permits further qualification: actual enforcement must be tested before enabling production generation. A Windows sandbox ready check is now mandatory before every turn, including qualification probes.

The approved setup completed on 2026-10-04, but initially allowed sandboxed localhost connections. The [original failure](docs/verification/2026-10-04-codex-sandbox-enforcement.md) was repaired with a scoped Windows Filtering Platform supplement; [actual IPv4/IPv6 TCP/UDP and write checks now pass](docs/verification/2026-10-04-codex-loopback-repair.md). Run `.venv/Scripts/python.exe -m scripts.verify_codex_sandbox --extended` as your normal Windows user to verify synthetic file/socket enforcement without generation. Every explicit `qualify_codex --live` run also requires these checks before inference.

For the pinned runtime, `.venv/Scripts/python.exe -m scripts.repair_codex_sandbox` inspects the supplement from an elevated Windows terminal. Explicit `--apply` installs it and `--remove` removes only its verified objects; both require an elevated interactive terminal. Installation requires the exact reviewed Codex binary on that terminal's PATH. It creates two persistent loopback-block filters and one dedicated sublayer, with transactional readback and no change to existing provider/firewall rules. Codex shares its **offline sandbox account across native profiles**, so that account's other sessions also lose loopback access, including any configured local-binding exception. Your normal Windows account, online sandbox account and WSL are outside the filter scope. Drift or account replacement requires review; no broad cleanup is attempted. This is a developer qualification repair, not packaged/reboot/clean-machine acceptance or production capability enablement.

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
