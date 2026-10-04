# Retained document learning — 2026-10-04

M3-T03b adds explicitly consented explanations over one retained document. [DEC-031](../../DECISIONS.md#dec-031-explain-retained-documents-as-separate-interpretations) records the separate interpretation model. M3 acceptance passed, including the final frozen backend/native artifact checks below. M4-M11 remain incomplete; public Windows v1 is not ready.

## Behavior and review

Saving a document never authorizes cloud transmission. Sources first performs a read-only cache lookup. New generation needs the document's exact ID/hash, current rights, a successful original-byte reparse, cloud consent and a separate sharing confirmation. It uses the selected runtime/model with browsing disabled and shares the existing queue, single inference semaphore and cancellation lifecycle. Context is bounded to 300,000 serialized characters, provider output to 12,000 and operation time to 180 seconds. No truncated document is silently represented as complete.

References contain original page/cell locators and literal quotations. Generated numeral tokens must occur in those quotations; invented references/URLs and known advice patterns fail. Interpretations remain visibly unverified and never enter asset/bundle records, calculations or factual follow-up context. These checks do not establish semantic entailment, comprehensive advice detection or source truth. Native stored content remains escaped, formulas inert and original dates separate from generated dates.

An explanation and its job publish atomically to an immutable `import_explanation` record. Language/reader level are independent cache scopes; a provider switch can reuse a prior explanation without a new call. Pending lookup returns the existing job without replay. Completed-job reads must match the immutable interpretation and revalidate original bytes/rights. Restore preserves original references and interrupts active jobs without inference. No dependency, source-rights policy, SQL revision, paid service or tool capability changed.

## Deterministic and database evidence

- Intermediate Q passed 1,256 Python/28 frontend tests; review added completed-job/source checks and the guarded live helper. The next Q passed 1,259/28. Final reviewed Q results are recorded at checkpoint completion below.
- Thirty-one new learning scenarios plus two live-helper boundary tests cover exact permission types, original fingerprints/quotes, changed numbers, known advice, invented URLs/citations, bounded context/queue, selected provider, unexpected tools/reviews, cancellation and consent revocation before/after inference, pending lookup without replay, immutable publication, failed-write rollback, corrupted completed jobs and strict archive references. Two frontend checks cover separate sharing permission, offline/no-browsing disclosures and escaped original references.
- Actual D passed with staged PostgreSQL 17.5 and private disposable clusters. Added a production-service explanation using an explicitly synthetic no-browsing runtime, then verified atomic rollback/restore/restart of the document, explanation and completed job alongside five documents/four formats and earlier financial citations. A final D extension reopened the restored explanation offline through the owned parser after database restart, with no provider adapter or inference task; it passed.
- Frozen-service rebuild passed authenticated preview, explicit retention, original-byte reopening, exact attachment archive export, shutdown and four parser formats. The final artifact rebuild after the last read-consistency guard is recorded below. Existing optional PyInstaller collection notices and the Starlette/httpx deprecation remain known warnings, not skipped checks.

## Browser and native interaction

The in-app browser backend remained unavailable. Playwright CLI used Chrome with the synthetic preview; production UI, API and owned parser handled data, while an explicit fixture supplied provider output. No live inference occurred in these UI tests.

Passed separate unchecked sharing permission, disabled generation while offline, no-browsing/unverified disclosures, cancellation, explicit retry, saved English and Traditional Chinese interpretations, exact original locators/quotations and unchanged generated timestamps on offline reopen. Changing reader level exposed an independent missing cache with generation disabled; returning restored the earlier saved interpretation. Normal/640-pixel screenshots were visually inspected, and the document width equalled the 640-pixel viewport. Browser console had only the existing development React DevTools shim warning after reload, with no operation/script error. Ignored evidence: `output/playwright/import-learning-640.png`, `import-learning-zh-wide.png`, `import-learning-zh-offline-640.png`.

The compiled native host used the existing isolated `org.learntheticker.verification.imports20261004` profile, packaged sidecar/private PostgreSQL and a separate test WebView2 directory. Selected a synthetic CSV through its actual FileChooser event, confirmed local processing and separate storage permission, then used Tab/Enter to retain it. Reopening preserved Chinese text, `9007199254740993`, `123456789.123456789`, literal formulas/script text, original checked time and explicit unverified status. The explanation panel correctly stayed offline with unchecked/disabled transmission permission and an empty cache. Native console had zero errors/warnings. The test did not connect a subscription or touch the user's normal application library.

Temporary debugging listened only at `127.0.0.1:18864`; the sidecar used loopback port 7745. After detaching the CLI, the exact native PID 12060 was stopped only after executable/start-time identity verification. Sidecar/DB shutdown removed the private postmaster PID file and both listeners. Synthetic preview/Vite listeners also stopped. Test profiles/screenshots were preserved under ignored locations. This is developer native interaction, not clean-machine installation, tray Quit or release lifecycle qualification.

One temporary-build invocation placed Tauri's `--no-bundle` after the root script's Cargo separator and failed argument parsing. Corrected the invocation to `npm.cmd --workspace apps/desktop run tauri -- build --no-bundle --config <isolated-config> -- --locked`; compilation and native interaction then passed. No application repair or check relaxation was needed. Final review additionally hardened completed-job result consistency before the final build; its targeted tampering test passes.

## Scoped live Codex check

After Q/D, `python -m scripts.qualify_import_learning --live --model gpt-6-astra` passed. The run began at `2026-10-04T10:05:18.765912+00:00` with native Windows Codex **0.158.0-alpha.2.1**, **gpt-6-astra**, the already-authorized dedicated subscription profile, current included-usage checks and fresh extended sandbox enforcement. It used the normal production runtime, no prequalification bypass, only a small synthetic revenue-definition CSV and a disposable library. It made two explicit language requests and no public-source retrieval.

Both English and zh-TW requests returned three validated original literal references and remained unverified interpretations. Requested language scripts were observed; this automated check is not comprehensive translation-quality certification. Offline cache reuse passed, asset/bundle stores stayed empty, and raw message events were not retained. The helper reports `live_qualified:false` deliberately: it never promotes runtime capabilities. No sign-in, permission grant, billing fallback, persistent user-library write or source contact details were involved.

## Requirement review

| Requirement / M3 condition | Evidence and limit |
| --- | --- |
| P-015 formats and untrusted imports | M3-T01 parser/URL rights/private-address/worker evidence plus prior actual native CSV/XLSX/PDF selection; this native retention check uses CSV |
| P-012 rights and provenance | Current URL policy and original-byte reparse before reading/transmission; storage/sharing permissions separate; no factual identity promotion |
| P-013 interpretation isolation | Separate record kind, unchanged asset/bundle stores, no chart/calculation admission, exact-reference/number rejection scenarios |
| P-014 original references/dates | Original document ID/hash/page/cell/source metadata retained; generated date cannot refresh source dates; offline browser/native and actual restore evidence |
| P-001 language/level | English/Traditional Chinese requests, independent level caches, readable normal/640-pixel UI; no claim of comprehensive translation quality |
| P-002 safety / P-040 selected connection | Fixed educational task, known advice rejection, no tools/browsing, explicit sharing/cloud consent, selected-model and quota guards, scoped live Codex acceptance |
| P-041 bounded authenticated isolation | Existing loopback/origin/auth rules and owned parser/provider processes retained; cancellation/queue/context limits; no new frontend filesystem capability |
| P-043 attachments and explanations | Actual PostgreSQL rollback/restore/restart and offline reparse; archive checks preserve original references and reject mismatched completed jobs; older binaries unqualified |
| Other subscriptions / Windows release | Gemini/Claude remain M8; large-library/cache, tray, update/rollback, signing and clean-machine acceptance remain M9-M11 |

## Final checkpoint

Final Q passed **1,260 Python/28 frontend tests**, lint, contract/schema drift, documentation/static checks, TypeScript and production build. Actual D passed the final offline-reopen extension. Final packaged verification passed the authenticated frozen service, retention/archive and four-format parser checks. Final N compiled the normal release application and NSIS installer after the completed-job consistency repair. F passed after the evidence and task/status updates.

Final developer artifacts (2026-10-04; unsigned, not clean-machine qualified):

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| `learn-the-ticker.exe` | 11,096,576 | `bc141a96d99934896e488dce41520fba17063c2205557fdfb66d8875aa259ecf` |
| `Learn the Ticker_0.2.0_x64-setup.exe` | 50,690,381 | `5a51b14f110abac6eb23be869e70016276bf7d25dd8642985d6f789b04700435` |

The requirement review above, earlier parser/retention evidence and these checks close M3. No test failure remains unresolved. This does not qualify Gemini/Claude, the complete native lifecycle, updates/rollback, distribution rights for staged runtime resources, signatures or clean-machine release acceptance. Next required milestone is M4.
