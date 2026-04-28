# MVP Functional Gap Review

Task: 2026-04-28 v0.6 doc alignment and fresh-data MVP review, updated after T-125 completion.

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
- LLM runtime diagnostics and OpenRouter transport contracts are present, with deterministic mocks as the default and live network calls blocked unless explicitly gated.
- Normal CI remains deterministic and does not require live provider, news, market-data, storage, database, browser services, or LLM calls.

## Current Misalignments

The v0.6 docs intentionally move execution details out of the proposal and into specialized handoff docs. Those new handoff docs need repo-native command alignment.

Doc/runtime mismatches addressed by T-125:

- `docs/SOURCE_HANDOFF.md`, `docs/TOP500_MANIFEST_HANDOFF.md`, and `docs/ETF_MANIFEST_HANDOFF.md` now use repo-native command examples or explicitly label missing tooling as future T-126 work.
- `docs/README.md`, `SPEC.md`, the runbook, readiness matrix, and go/no-go checklist now describe the ETF split and T-121 through T-124 as completed deterministic/operator-scoped work.
- `TASKS.md` and repo-contract tests now mark T-125 complete and promote T-126 as the current active agent-loop task.

## MVP Fresh-Data Gaps

The project is not yet a fully functional fresh-data MVP. Remaining blockers:

1. Launch-sized manifests are not approved.
   The current Top-500 stock manifest and supported ETF manifest are deterministic fixtures. Public v1 still needs the full approved Top-500 stock manifest, a launch-sized supported ETF manifest, private production mirrors, and review packets.

2. Repo-native source-handoff tooling is incomplete.
   Source policy and handoff validation exist, but the operator-facing finalized governed-source manifest inspection/finalization workflow is not implemented as repo-native CLI/script tooling.

3. Governed golden evidence does not yet prove full render authority.
   The repo needs an end-to-end proof that approved governed sources for golden assets can flow through source persistence, normalized facts, generated-output cache validation, backend route reads, and frontend rendering.

4. Local live-AI validation is not yet exercised.
   v0.6 expects operator-only local review of grounded chat and AI Comprehensive Analysis when evidence thresholds are met. That smoke must remain opt-in and must not become a normal CI requirement.

5. Third-party/news governance needs updated regression coverage.
   The v0.6 source policy allows approved reputable third-party/news metadata and beginner summaries, while full article text remains rights-gated. Weekly News Focus and export tests need to preserve those distinctions.

6. Production readiness remains later.
   Admin auth, rate limiting, production CORS review, private object storage, database migrations, Cloud Run service/job settings, monitoring, rollback, cost controls, launch support, and legal/compliance review remain open.

## Refined Agent Track

Current task state:

- T-125 completed v0.6 docs, handoff guides, MVP gap review, and repo-contract test alignment.
- T-126: add repo-native source-handoff manifest inspection/finalization smoke tooling or accurately scoped equivalents. This is the current promoted task.

Runnable near-term backlog:

- T-127: add opt-in local live-AI validation smoke for grounded chat and AI Comprehensive Analysis, with CI-safe mocks.
- T-128: prove governed golden evidence drives backend API and frontend rendering for the golden set.
- T-129: add launch-manifest operator automation parity for Top-500 and supported ETF review packets without promoting runtime manifests.
- T-130: add a local fresh-data MVP rehearsal command or command sequence that ties the governed golden path into one operator-facing pre-production check.

Sequencing rationale:

- Align docs first so the agent loop does not follow commands from a different repository layout.
- Add repo-native source-handoff tooling before proving governed evidence can drive rendered output.
- Add live-AI local validation as an opt-in operator smoke with CI-safe mocks before broader governed-evidence render proof expands the blast radius.
- Keep launch-manifest automation review-only until promotion gates and private mirrors are ready.
- Add the local fresh-data rehearsal only after the source, evidence, AI, and manifest gates exist, so it verifies the integrated local MVP path instead of masking missing pieces.

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
npm test
npm run typecheck
npm run build
TMPDIR=/tmp bash scripts/run_quality_gate.sh
```

Run `docker compose config` when Docker is available; otherwise record the local Docker-unavailable blocker.
