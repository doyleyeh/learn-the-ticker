# Date-proven weekly selection

Date: 2026-10-06 (Asia/Taipei). Scope: M7-T01; M7 report storage, UI and exports remain M7-T02.

`backend/app/weekly.py` migrates the useful weekly-window, deduplication and sparse-context rules into production without importing the fixture backend. It accepts independently identified immutable evidence and revalidates SEC filing publication proofs. Reporting periods remain separate from filing/publication dates. Model dates, notes, restricted sources and wrong assets cannot qualify. Current coverage is explicitly limited to saved independently verified filings, with no new provider or news-feed qualification.

Selection uses the last completed Eastern Monday–Sunday and the current week through yesterday, at most eight distinct filing events, and stable accession/content deduplication before thresholds. Fewer than three weekly events selects available Earlier context from the preceding 30 days, outside weekly counts. Analysis eligibility requires two weekly events. Neither sparse context nor a recently saved page makes older evidence current.

- Targeted `python -m pytest tests/desktop/test_weekly_selection.py tests/unit/test_weekly_news.py -q`: **25 passed**, including both DST transitions, Monday/year boundaries, inclusive/exclusive dates, zero/one/two/three/four thresholds, duplicate accession/body, deterministic order, malformed date/identity/rights and input preservation.
- F `python -m scripts.verify fast`: passed lint, unchanged contract equality, documentation, whitespace and TypeScript (`.local/m7-weekly-f.log`).
- Q `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1`: **1,971 Python/91 frontend passed**, lint, generated contracts, documentation, static evaluations, TypeScript and build (`.local/m7-weekly-q.log`). Complete diff/whitespace reviewed; no required gate weakened.

No live requests, database/schema changes, new dependency, paid activation, source-policy expansion, model inference or installer changes occurred. Report publication and final M7 acceptance remain unverified at this checkpoint.
