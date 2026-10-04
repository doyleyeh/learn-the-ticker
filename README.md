# Learn the Ticker

A local, citation-first financial research and learning application using your own commercial agent subscription. Your evidence, conversations and research belong in your local library.

**Status: desktop developer preview, not public v1.** The approved stack is Tauri 2, React/TypeScript/Vite, packaged FastAPI and private PostgreSQL. Native Windows comes first, followed by macOS, Windows with WSL, then Linux. The product serves beginner and intermediate users across dynamically resolved asset types; there is no fixed ticker eligibility list.

Working preview features include the local library, evidence versions and citations, cached search, conversations and bookmarks, term explanations, personal exports and portable backup/restore. The scoped verified research pipeline is complete. Admitted issuer financial history now shows exact values, original citations and retained revisions; prices, returns, comparisons, durable imports and release features are still being integrated. Codex generation is qualified only for the reviewed native Windows 0.158.0-alpha.2.1 executable and gpt-6-astra model/catalog/tool policy. Drift stops before inference. Gemini/Claude and native installers remain unqualified. Cached features and the synthetic preview remain available. Runtime qualification does not establish full research-pipeline or public release acceptance; see [implementation status](STATUS.md).

Online research must combine configured financial/news APIs with autonomous live web search and reading public source pages for current market and ticker context. Qualified Codex research retains live web search; local browser/computer control remains outside its scope. The scoped API/search/page-navigation/freshness workflow passed M2 with independent fact validation; [evidence and limits](docs/verification/2026-10-04-cited-evidence-reuse.md) remain explicit. Gemini/Claude must qualify the same online behavior in M8. Latest-information requests must verify source dates and disclose unavailable or stale information; web search alone does not establish real-time market prices.

New research requires independent identity verification. SEC resolves issuer/listing metadata; OpenFIGI provides a separate public instrument-identifier lookup without an account or API key. Exact FIGIs, tickers and full names can produce listing/class/contract choices; incomplete results require a more specific selection. Records from the two registries are never merged by name/ticker alone. Uncertain type/currency remains explicit; coverage remains source-dependent, with missing financial/news information explicit. Unresolved or changed identities cannot publish facts, and unknown source rights retain links only. Existing saved versions remain accessible. Online cache reuse checks the saved language/reader level, identity and supporting source dates; newly downloaded old information is not current evidence.

The initial SEC financial adapter independently checks one reviewed common-stock listing against its issuer, then normalizes official observations with original units, dates and filing revisions. Missing history remains explicit. Typed numeric admission, exports and actual archive/restore preserve exact decimals and conflicts separately from model claims. Research now checks applicable financial history before inference and saves admitted observations with the result. Scoped live search/page-navigation/freshness acceptance passed M2; charts and broader news coverage remain unfinished. See the [adapter evidence and limits](docs/verification/2026-10-04-sec-financial-observations.md), [numeric admission](docs/verification/2026-10-04-numeric-admission.md) and [orchestration checkpoint](docs/verification/2026-10-04-structured-orchestration.md).

SEC filing-event candidates now carry independently checked original filing/report dates from the issuer's submissions index. Each cited document still needs a separate page retrieval and literal claim-support check. The dates and index references survive exports and library restore; missing current news and market-price coverage remains explicit. The [dated research evidence](docs/verification/2026-10-04-dated-research.md) records deterministic/database verification and the separate production-path live checks, including failures. This is partial official-event coverage, not a complete news feed.

Stored facts retain their original source records and evidence version. Follow-up conversations can reuse the last five cited versions within the current asset scope, including original URLs and dates; earlier explanations are excluded from factual context. A new fact still needs independent source verification. Refresh preserves the old answer and its citations even if a page later changes or becomes unavailable. Browsing observation and factual admission are checked separately; provider navigation metadata is not treated as the complete page text seen by the model.

Retained-import backup infrastructure supports bounded original documents with checksums, provenance and explicit storage/backup permission. It preserves unverified state and reads older archives. The Sources screen still provides ephemeral previews; durable storage controls and provider use remain in progress. See [archive compatibility](docs/MIGRATION.md#database-and-library-compatibility).

## Development on Windows

Use Python 3.12 and Node 22.13+ (22.x) or Node 24+ for development; native builds also need Rust/MSVC and the Windows webview prerequisites. PostgreSQL 17 binaries were used in the local lifecycle tests. Other major versions have not been qualified. The future end-user installer must bundle the core dependencies and handle provider prerequisites explicitly.

On this Windows development machine, user-authorized installation supplied Rust/Cargo 1.99.0, Visual Studio 2022 Build Tools 17.14.41 (C++ workload/MSVC 14.44) and Windows SDK 10.0.26100.0. C++ and Rust compile/link/run probes passed. WebView2 was already installed. Open a new terminal after installation to pick up Cargo's PATH entry. Native builds use the committed Cargo.lock with `--locked`; toolchain installation alone does not qualify the application or installer.

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
$env:LTT_PG_BIN = 'C:/Program Files/PostgreSQL/17/bin'
npm run desktop
```

Setup creates `.venv` and installs Python/frontend dependencies; it does not install Python, Node, Rust/MSVC, PostgreSQL or provider CLIs. `.env.example` is guidance, not an automatically loaded desktop configuration. The supervisor creates its own cluster and does not use an existing PostgreSQL service. Native Windows compilation, startup and offline file previews passed the [isolated developer checks](docs/verification/2026-10-04-native-build.md). Full tray/lifecycle and clean-machine installer acceptance remain separate release work.

The developer SEC adapter requires `LTT_SEC_USER_AGENT` in the backend process environment, containing `LearnTheTicker/0.2` and a contact email you control, as requested by [SEC automated-access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data). This is a contact header sent to SEC, not authentication or a subscription email requirement. Keep the real value out of Git. Without it the adapter performs no SEC request; cached pages remain usable. After deterministic verification, `.venv/Scripts/python.exe -m scripts.qualify_sec_identity --live --query MSFT` performs one bounded public identity check without provider inference or library writes. The query is a probe, not a production eligibility list. Packaged SEC contact/onboarding is still pending; the project does not bundle a personal email, and this developer setup does not decide whether end users must configure one.

OpenFIGI checks use `.venv/Scripts/python.exe -m scripts.qualify_figi_identity --live --query FIGI:BBG000BLNNH6` after deterministic verification. Omit `--live` for a no-request result. Anonymous rate limits apply; retry explicitly later if unavailable. Identifier metadata is attributed to OpenFIGI / Bloomberg Finance L.P. under its [terms](https://www.openfigi.com/docs/terms-of-service) and [reuse FAQ](https://www.openfigi.com/about/faq); no affiliation or endorsement is implied. This registration does not cover website articles, trademarks, prices or third-party proprietary identifiers.

`npm run dev` starts only the frontend at `http://127.0.0.1:1420`; `npm start` previews the built frontend. Neither starts a database or backend. For a reproducible browser-only demonstration without subscriptions, use the [synthetic preview instructions](EVALS.md#synthetic-browser-preview). Docker Compose is optional database development support and is not connected to the desktop supervisor.

`scripts/package_backend.py` builds the Windows x64 sidecar separately. `npm run desktop:build` additionally needs that sidecar and a reviewed PostgreSQL runtime under the Tauri resources directory; it does not provision them. See [packaging and migration](docs/MIGRATION.md#native-packaging-and-platforms).

## Connect Codex

The implemented Codex setup flow is **Connections → Sign in with ChatGPT**, using an installed official Codex runtime and a dedicated provider-owned profile. Follow the provider's device-code flow; cloud research permission is separate. Dedicated native Windows runtime qualification passed on 2026-10-04 for the exact measured binary and gpt-6-astra; see [scoped acceptance](docs/verification/2026-10-04-codex-scoped-qualification.md) and [sandbox prerequisites](docs/verification/2026-10-04-codex-loopback-repair.md). A different executable, WSL runtime, model/catalog or policy requires new qualification. Gemini/Claude onboarding and tool isolation still need qualification. Public v1 requires all three subscription connections; there is no API-billing or automatic provider fallback.

Connections also offers model discovery and explicit selection; missing models fail without fallback. A provider-reported model change stops the active run before an answer is published and preserves your saved selection. Access review supports denial or cancellation within the research policy and cannot authorize shell/file/broader network grants. These controls do not enable generation before live qualification.

A pending command/file request can reach access review. Continuing after denial requires the provider to confirm that the action was declined; execution output or unresolved activity stops the run without publishing an answer. The approved restricted-catalog repair retains the selected model and removes metadata-driven execution tools. Research may request a permission review, which can only deny or cancel; cached explanations expose no intended tools. Catalogs are temporary and validated before inference. Complete live qualification remains separate.

The adapter separates Codex progress commentary from completed answers before research or term JSON validation. Failed, cancelled or malformed message sequences publish no candidate answer. This has deterministic regression coverage; selected-model live acceptance remains part of qualification.

When the native development toolchain is unavailable, run `.venv/Scripts/python.exe -m scripts.connect_codex` yourself in an interactive terminal to authorize the same dedicated Windows profile without starting inference. It opens the official device-code page; do not redirect or save the code. It never imports your developer Codex credentials. Then `.venv/Scripts/python.exe -m scripts.qualify_codex` performs a no-inference preflight. The separate `--live` option consumes subscription usage for explicit probes and requires current included-usage permission; read [the live qualification procedure](EVALS.md#codex-subscription-qualification) first. Passing probes never automatically enables production capabilities.

The separate `scripts.qualify_codex_acceptance` developer helper checks independent source-quote retrieval, live consent revocation and an owned-provider disconnect, using a disposable test library. It also defaults to preflight only; `--live --model MODEL_ID` explicitly consumes included subscription usage after the same guards. These checks do not replace source-rights review, PostgreSQL restore or installer acceptance.

`scripts.qualify_codex_tools` defaults to the same no-inference preflight. Its explicit `--live --model MODEL_ID` checks actual deny/cancel permission requests, restricted-catalog cleanup, independent source support and cached-only behavior after fresh sandbox enforcement. Model-reported tool lists are corroborating observations, not authoritative inventory or automatic qualification. Read [EVALS](EVALS.md#codex-subscription-qualification) before invoking live checks.

`.venv/Scripts/python.exe -m scripts.qualify_codex_inventory --model MODEL_ID` inspects the installed Windows binary's complete tool declaration using fresh credential-free profiles and a local test listener. The authenticated metadata process closes first; no account traffic is intercepted, no cloud inference/tool execution occurs and only names/hashes are reported. Its result needs the separate live checks and [transport-equivalence review](docs/verification/2026-10-04-codex-wire-inventory.md); it does not enable production capabilities.

For an explicit post-review check, `scripts.qualify_codex_tools --live --production --model gpt-6-astra` uses the normal production qualification guards for the four bounded turns. This consumes included subscription usage, repeats actual enforcement and retains review-required reporting; it never edits the qualification registry.

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


The Sources screen previews selected PDF/CSV/XLSX files and permitted public HTTPS pages with original page/cell references, decimal text and explicit uncertainty. Local files work offline with permission confirmation; unknown URL rights retain links only. Previews are unverified and discarded on navigation; formulas are not evaluated, and no content is added to facts, charts or your library. Native desktop file-selection acceptance and restore-aware durable imports remain unfinished. New dependency licenses are listed in [import notices](docs/THIRD_PARTY_NOTICES.md).
