# Learn the Ticker Docs

This directory is organized around one source-of-truth chain and a small set of operational planning artifacts.

## Source-Of-Truth Order

1. Safety and advice-boundary rules in `AGENTS.md`
2. `docs/learn_the_ticker_PRD.md` - product source of truth
3. `docs/learn_the_ticker_technical_design_spec.md` - engineering source of truth
4. `docs/learn-the-ticker_proposal.md` - narrative product vision
5. `SPEC.md` - operational implementation baseline
6. `TASKS.md` - runnable agent-loop task queue and completion history
7. `EVALS.md` - required checks and quality gates

## Current Operational Docs

- `docs/mvp_functional_gap_review.md`: current development progress, MVP fresh-data gaps, and the near-term Codex agent-loop track.
- `docs/local_fresh_data_ingest_to_render_runbook.md`: local golden-asset smoke procedure for API/backend/frontend rendering.
- `docs/SOURCE_HANDOFF.md`: operator guide for Golden Asset Source Handoff and governed source ingestion boundaries.
- `docs/TOP500_MANIFEST_HANDOFF.md`: operator guide for Top-500 stock candidate, review, and promotion handoff.
- `docs/ETF_MANIFEST_HANDOFF.md`: operator guide for supported ETF and ETF/ETP recognition manifest handoff.
- `docs/mvp_launch_readiness_regression_matrix.md`: deterministic launch-readiness regression matrix.
- `docs/mvp_go_no_go_checklist.md`: production readiness blockers and no-go checklist.
- `docs/agent-journal/`: append-only task journals. These are provenance records, not active planning docs.

## Redundant Files Removed

- Windows `Zone.Identifier` sidecar files are not project docs and should not be committed.
- `docs/backend_mvp_runtime_gap_audit.md` was superseded by `docs/mvp_functional_gap_review.md` so the active gap review has one canonical location.

## Current Alignment Note

The v0.6 PRD/TDS define a split ETF universe model:

- `data/universes/us_equity_etfs_supported.current.json`
- `data/universes/us_etp_recognition.current.json`

The runtime now reads the split manifests. The older combined deterministic ETF manifest at `data/universes/us_equity_etfs.current.json` remains only for repository continuity and historical tests. Current MVP gaps are launch-sized reviewed manifests, repo-native source-handoff tooling, governed golden evidence driving API/frontend output, opt-in live-AI local validation, and production readiness.
