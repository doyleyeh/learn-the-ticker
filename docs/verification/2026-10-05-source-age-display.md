# Source-age display and M4 review — 2026-10-05

M4-T01g5 addresses a finding in the final M4 parity review: `App.tsx` derived a freshness label from the bundle creation time and always showed a newer bundle as partially available. That did not reflect its recorded availability or original evidence dates. The new saved-status display and transient source-age endpoint implement DEC-047 without changing original records or online cache eligibility.

## Scope and checks

The authenticated endpoint returns only the exact bundle ID, assessment time and source IDs/age states/reasons. It uses current registered source rules, including the separate rules for admitted private numerics. Old publication, as-of, claim or retrieval dates cannot be refreshed by a newer wrapper. Notes do not participate; a claim date cannot establish the date of an otherwise undated source. Future dates, unverified/foreign references, unknown rules and changed usage policies remain unknown. Within-age-limit is explicitly distinct from current coverage or a live quote.

The page requests one local assessment per mounted version, aborts abandoned requests and rejects another version's result. Assessment failure preserves the original page, numerical values and citation navigation. Saved availability is reported as recorded, without upgrading missing/partial states. No live source/provider call, library mutation, financial calculation, dependency or migration is involved.

Focused checks passed **35 cases** across `test_freshness.py`, `test_cache_resolution.py` and `test_repo_contract.py`; frontend tests passed **74 cases**. The final Q outcome is recorded below after completion. Actual D passed the private-service/transaction/restore lifecycle; the extended restore smoke separately verifies identical source-age assessments after transfer/restart and unchanged original private records. Browser B passed the existing integrated review/progress/numerical-learning flow plus the new age display and failed-read scenario, with no new research requests from the assessment. Normal/640-pixel screenshots were visually inspected: readable wrapped text, no page overflow and preserved navigation.

Ignored B captures: `output/playwright/automated/research-admitted-versions-89be9-at-normal-and-narrow-widths/freshness-wide.png`, `freshness-narrow.png` and the existing citation/financial captures. Services shut down after the harness. This remains a synthetic browser check; native artifacts from g4 predate this source/UI change and no new installed-build claim is made.

## Repairs

1. The new API test initially used the wrong database method name (`list_research_jobs`); changed it to the existing `research_jobs`, retaining the no-job assertion. The targeted suite passed.
2. F and the first B build both caught the same optional-list TypeScript error. The response always supplies its source list, so made that wire field required and regenerated both contracts. The real browser workflow then passed.
3. Q found the independent contract inventory test missing the new response model. Added it to that test's expected inventory without relaxing equality; the focused contract test passed. Final Q was rerun.
4. Review made date assessment more conservative: claim dates may downgrade a source but cannot certify an undated source. Added that regression and reran the affected checks and actual restore scenario.

These were distinct diagnosed issues, with successful repair checks; no failure was skipped or weakened and no repeated-failure blocker is claimed. Existing Starlette/httpx deprecation and Playwright color-environment warnings remain.

## Remaining M4 review

Final Q (`powershell -ExecutionPolicy Bypass -File .codex/skills/project-delivery/scripts/verify-milestone.ps1`) passed **1,696 Python/74 frontend tests**, Ruff/ESLint, non-writing schema/types, documentation/whitespace/static checks and production TypeScript/Vite build. Final documentation F also passed before the reviewed local checkpoint. The browser listeners on 1420/18764 were absent after testing. M4-T01g5 is complete; M4 overall remains incomplete.

This slice alone does not complete M4. Final review still needs stock/fund/unknown-type browser parity and routing of the production `news` section into the ticker context area. The generic research path still instructs online search unconditionally; DEC-035's sufficient-context behavior needs explicit verification/repair. Analyst insights is currently an unavailable-only panel, with no production analyst dataset or attributed-opinion contract. A missing-data label does not qualify that integration. These findings remain actionable work in TASKS/STATUS; no milestone-order exception or source-policy expansion is inferred.
