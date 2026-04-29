# MVP Functional Gap Review

Task: 2026-04-28 v0.6 doc alignment and fresh-data MVP review, updated during T-130.

Purpose: summarize current implementation progress, align the operational plan with the v0.6 PRD/TDS refresh, and define the next narrow tasks needed before the project is a locally functional MVP that can use fresh approved data and show it correctly in the frontend.

This is an operational planning artifact. It does not enable production deployment, production persistence, broad source coverage, recurring jobs, unrestricted provider calls, generated advice, or default live model execution.

## Current Progress

The repo is no longer planning-only. It is a deterministic, fixture-backed MVP scaffold with substantial backend, frontend, source-governance, and local-smoke behavior in place.

Completed capabilities:

- Next.js app under `apps/web` with single-asset home search, asset pages, comparison, source list, contextual glossary, asset chat, and export controls.
- FastAPI backend under `backend` with route contracts for search, overview/details, Weekly News Focus, comparison, chat, glossary, sources, exports, ingestion/pre-cache state, trust metrics, LLM runtime diagnostics, and CORS diagnostics.
- T-119 is complete: chat, export, and comparison frontend paths use the configured backend base or Next `/api` rewrite, and FastAPI CORS is wired from configured origins.
- T-120 is complete: supported ETF generated-output coverage reads `data/universes/us_equity_etfs_supported.current.json`, while ETF/ETP recognition-only blocked states read `data/universes/us_etp_recognition.current.json`.
- T-121 is complete: optional localhost browser/API smoke covers API-backed MVP flows when local web/API services are already running.
- T-122 is complete: optional local durable smoke documents and checks API proxy/CORS behavior with durable prerequisites while preserving fixture-safe default tests.
- T-123 is complete: SEC stock, ETF issuer, and Weekly News official-source fetcher boundaries are promoted behind explicit local opt-in and Golden Asset Source Handoff gates.
- T-124 is complete: Top-500 candidate/diff artifacts and reviewed launch-universe planning are present without promoting fixture candidates into runtime truth.
- Golden Asset Source Handoff enforcement exists across source policy, source snapshots, knowledge packs, citations, generated-output cache metadata, source drawer output, and exports.
- LLM runtime diagnostics, OpenRouter transport contracts, and the T-127 local live-AI validation smoke are present, with deterministic mocks as the default and live network calls blocked unless explicitly gated.
- T-128: prove governed golden evidence drives backend API and frontend rendering. This is now completed as a deterministic governed golden rendering proof: configured API reads can validate private same-asset source snapshot artifacts, normalized knowledge-pack records, and generated-output cache records before serving overview, source drawer, and export output.
- T-129 adds repo-native review-only launch-manifest packet automation for Top-500 candidate/diff/review summaries and split ETF supported/recognition manifest inspection without promoting runtime manifests.
- T-130 adds a repo-native local fresh-data MVP rehearsal command that ties source-handoff gates, governed golden API reads, source drawer/export surfaces, comparison/chat paths, frontend smoke markers, launch-manifest review packets, and opt-in readiness checks into one review-oriented local command.
- Normal CI remains deterministic and does not require live provider, news, market-data, storage, database, browser services, or LLM calls.

## Current Implementation-Doc Alignment

The implementation-facing docs now treat T-126 through T-130 as completed deterministic/operator-safe layers, not future blockers:

- source-handoff packet inspection/finalization tooling exists;
- operator-only live-AI validation smoke exists and remains disabled by default;
- governed golden evidence can drive API/frontend rendering for `AAPL`, `VOO`, and `QQQ`;
- Top-500 and ETF launch-manifest review packets exist and remain review-only;
- the local fresh-data MVP rehearsal command exists and remains deterministic by default.

The agent-loop control docs now need runnable tasks that move from review-only/golden proof toward a fully functional local fresh-data MVP without jumping to production deployment.

## MVP Fresh-Data Gaps

The project is not yet a fully functional fresh-data MVP. Remaining blockers:

1. Launch-sized manifests are not approved.
   The current Top-500 stock manifest and supported ETF manifest are deterministic fixtures. T-129 adds review-only packet automation, but the local fully functional MVP still needs reviewed Top-500 and ETF-500 source-pack readiness, full supported ETF manifest smoke, private mirror readiness, and manual approval gates before treating full coverage as fresh-data ready.

2. ETF eligible-universe implementation is not complete.
   The product decision now names ETF-500 as the v1 supported ETF target: around 500 reviewed, currently U.S.-listed, non-leveraged, non-inverse, passive/index-based U.S. equity ETFs, with 475-525 accepted after review quality gates. Coverage should span broad/core beta, market-cap and size/style, sector, industry/theme, dividend/shareholder-yield, factor/smart-beta/equal-weight, and ESG or values-screened ETFs when source packs validate. The current supported manifest and review packet are still fixture-sized/local metadata; golden/pre-cache tickers are regression assets only, not the coverage ceiling.

3. Launch-sized governed source artifacts are absent.
   T-126 added source-handoff manifest tooling and T-128 proved governed golden evidence rendering. The next local MVP gap is expanding readiness packets for SEC stock source packs and ETF issuer source packs without approving unreviewed sources or enabling generated output for failed assets.

4. Local live-AI validation is operator-smoke covered, not launch-approved.
   T-127 adds an opt-in local smoke for grounded chat and AI Comprehensive Analysis when evidence thresholds are met. It remains disabled by default, validation-first, and separate from source approval or Golden Asset Source Handoff. Repo code relies on OpenRouter platform/API-key limits rather than a separate spend cap.

5. Local MVP rehearsal is now available, but not launch approval.
   T-130 adds `TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json` for deterministic local review. The command reports `pass`, `skipped`, and `blocked` checks, skips optional browser/durable/retrieval/live-AI modes unless explicitly enabled, and does not approve sources, promote manifests, start production services, require live calls by default, or make fixture-sized/local-only data launch-approved. It still needs explicit local-MVP thresholds for failed/unavailable assets and optional-mode blockers.

6. Batchable fresh-data ingestion planning is not yet actionable for the full local MVP.
   The repo has deterministic ingestion state contracts, but it still needs an operator-safe planner that prioritizes high-demand pre-cache assets first, then supported ETFs and Top-500 stocks by review/source-pack priority, with resumable pending/running/succeeded/failed states.

7. Production readiness remains later.
   Admin auth, rate limiting, production CORS review, private object storage, database migrations, Cloud Run service/job settings, monitoring, rollback, cost controls, launch support, and legal/compliance review remain open.

## Refined Agent Track

Current task state for the next agent-loop pass:

- T-126 completed repo-native source-handoff manifest inspection/finalization smoke tooling.
- T-127 completed the opt-in local live-AI validation smoke for grounded chat and AI Comprehensive Analysis.
- T-128 completed deterministic governed golden API/frontend rendering proof for the golden set and remains limited to deterministic golden assets.
- T-129 completed review-only launch-manifest operator automation parity for Top-500 and supported ETF review packets.
- T-129: add launch-manifest operator automation parity is now implemented as deterministic review-only operator tooling, not as launch approval or manifest promotion.
- T-130 completed the local fresh-data MVP rehearsal command as a deterministic, fixture-backed review layer with explicit optional modes.

Runnable near-term backlog:

- T-131 adds ETF eligible-universe review packet contracts.
- T-132 adds stock SEC source-pack readiness packet contracts.
- T-133 adds ETF issuer source-pack readiness packet contracts.
- T-134 adds local fresh-data MVP readiness thresholds.
- T-135 adds a batchable local ingestion priority planner.

Sequencing rationale:

- Align docs first so the agent loop does not follow commands from a different repository layout.
- Start with ETF eligible-universe review because the latest product decision makes ETF-500 the supported ETF target and golden ETFs a regression subset, not the coverage ceiling.
- Add stock and ETF source-pack readiness before changing generated-output unlock behavior.
- Add local MVP thresholds before broadening ingestion so failed/unavailable assets cannot leak generated claims.
- Add batch planning after the readiness packets exist, keeping all work deterministic and review-only until source approvals and manifest promotion are explicit.

## Non-Goals For The Next Tasks

The next agent-loop tasks must not add:

- live external calls in normal CI
- production credentials or secret inspection
- production object storage or database writes
- unreviewed manifest promotion
- generated output for unsupported or recognition-only ETF/ETP rows
- broad paid-provider or news-provider integrations
- production deployment hardening before local MVP behavior is stable

## Verification Baseline

For doc/control changes, run:

```bash
git diff --check
TMPDIR=/tmp python3 -m pytest tests/unit/test_repo_contract.py tests/unit/test_safety_guardrails.py -q
TMPDIR=/tmp python3 evals/run_static_evals.py
TMPDIR=/tmp python3 scripts/run_local_fresh_data_rehearsal.py --json
npm test
npm run typecheck
npm run build
TMPDIR=/tmp bash scripts/run_quality_gate.sh
```

Run `docker compose config` when Docker is available; otherwise record the local Docker-unavailable blocker.
