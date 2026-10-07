# Import preview checkpoint — 2026-10-04

M3-T01b has a verified authenticated API/browser preview implementation. It remains **BLOCKED/incomplete** because `python -m scripts.verify native` exits 1 with `BLOCKED: Missing cargo; follow README setup and EVALS prerequisites.` M3 is not complete. Browser file selection is not Tauri/native acceptance; provider consumption, durable attachment storage/restore and clean-machine distribution remain unfinished.

## Behavior and boundaries

The Sources screen accepts explicitly selected PDF/CSV/XLSX bytes after local-processing permission confirmation. Changing files resets permission; files work with online research off. Public URLs require cloud consent, HTTPS/public addresses and code-owned registered rights. Unknown rights produce link metadata without downloading content. Registered permitted HTML/text is retrieved through the existing bounded, DNS-pinned, redirect-rejecting transport. Authentication and origin checks apply to both endpoints. File bodies are bounded to 5 MiB/20 seconds and URL JSON to 4 KiB; malformed bodies and parser/network failures return fixed messages, excluding raw diagnostics.

Parsing uses the already verified owned worker, shares the two retrieval slots and limits active/queued previews to 20. Disconnect/cancellation/shutdown joins owned tasks; cloud revocation cancels online previews while local parsing remains independent. Blocking network operations retain their retrieval slot until I/O finishes. Nothing is sent to an LLM or written to the library. Generated contracts include the unverified/saved-false result; no persisted/archive schema changed.

The UI retains original URLs, publisher/rights, content fingerprint, page/cell references, numeric strings, formulas as inert text, unknown publication/as-of dates and PDF/layout limitations. It distinguishes a preview check from an actual retrieval and renders 20 content blocks per page. Imported content cannot feed facts or charts.

## Verification

- `python -m pytest tests/desktop/test_import_previews.py tests/unit/test_repo_contract.py -q`: **35 passed** (31 new API/lifecycle cases plus four contract checks). Authentication/origin, empty/oversized files, invalid/credential/private URLs, malformed/bounded JSON, cloud/rights/DNS/fetch failures, no database writes, queue/selective shutdown and disconnect cancellation covered with synthetic inputs.
- `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1`: **1,151 Python and ten frontend tests passed**, plus lint, generated schema/types, docs, static evaluations and production build. The three new frontend cases cover escaped instructions, exact numbers/locators, explicit unverified/unsaved state, undownloaded links and offline controls. Initial TypeScript verification found a missing explicit `useRef` initial value; corrected before the passing gate.
- `python -m scripts.verify database`: private PostgreSQL lifecycle, transactions/recovery and actual full-library restore/restart passed, including original conversation citation reuse. No system database or user library was touched.
- `python -m scripts.verify packaged`: rebuilt frozen Windows sidecar, private PostgreSQL lifecycle and all four synthetic parser formats passed. Existing optional PyInstaller discovery warnings (psycopg import order, unused keyring test modules/other database drivers) remain; exercised production paths succeeded.
- Extended `scripts/smoke_local_service.py` was subsequently run in both source and `--packaged` modes: actual authenticated offline CSV upload preserved `123456789.123456789`, returned no-store/unverified/unsaved output and left the library empty; both services/private databases stopped cleanly. This extends the smoke beyond the preceding packaged invocation.

## Browser observations

The browser skill initialized but could not discover an in-app browser backend. A separate Playwright CLI browser exercised Vite with `tests.desktop.preview_server --terms-demo --imports-demo`; disposable SQLite and synthetic URL/network substitutions only, production API and owned parser unchanged. No live source/provider call occurred.

Observed PDF page 1 text; CSV long decimals/Chinese characters; XLSX cell kinds and literal HYPERLINK formula; permission reset on a changed file; two-page CSV navigation; malformed-PDF and private-URL errors; cancellation feedback followed by a successful retry; unknown URL link-only state; permitted synthetic SEC URL with original link, separate retrieval time and unknown publication/as-of dates. All previews disclose that nothing was added to the library. A controlled cloud checkbox updated after its asynchronous save; CLI `check` initially reported its immediate state unchanged, but the subsequent UI confirmed online state. No second toggle was performed.

Inspected 1280×900 and 640×900 screenshots. The narrow layout stacks forms/cells without horizontal overflow (640 viewport, 625 document width including scrollbar behavior). Synthetic screenshots and inputs remain ignored under `output/playwright`; CLI snapshots are ignored. Browser console contained a missing favicon, development-tool warnings and expected 400 responses for intentionally invalid inputs; no observed product runtime exception. The native shell/file chooser/installer is unverified.

## Review and next action

Reviewed API/UI/contracts and rights/date/cancellation boundaries with the repository review guidance and React checklist. Previews do not establish source authenticity, asset identity, numeric admission or retention rights. Finish native selection after provisioning Rust/MSVC and reviewed resources. M4-T01 is independently unblocked by completed M2; M3-T02 remains pending its declared prerequisite. No provider policy, subscription, billing, SEC contact configuration or Windows sandbox rule changed.
