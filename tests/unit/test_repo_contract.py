from copy import deepcopy
import re
from pathlib import Path

from scripts.run_local_fresh_data_rehearsal import RehearsalCheck, _build_manual_fresh_data_readiness_gate, run_rehearsal


ROOT = Path(__file__).resolve().parents[2]


def read_file(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def checks_from_result(result: dict) -> list[RehearsalCheck]:
    return [
        RehearsalCheck(
            check_id=check["check_id"],
            status=check["status"],
            reason_code=check["reason_code"],
            details=deepcopy(check.get("details", {})),
        )
        for check in result["checks"]
    ]


def markdown_section(text: str, heading: str, next_headings: tuple[str, ...] = ("## ",)) -> str:
    start_marker = f"{heading}\n"
    start = text.index(start_marker) + len(start_marker)
    end = len(text)
    for marker in next_headings:
        found = text.find(f"\n{marker}", start)
        if found != -1:
            end = min(end, found)
    return text[start:end]


def task_sections() -> tuple[str, str, str, str]:
    tasks = read_file("TASKS.md")
    current = markdown_section(tasks, "## Current task")
    backlog = markdown_section(tasks, "## Backlog")
    completed = tasks.split("## Completed", 1)[1].split("## Historical Backlog Note", 1)[0]
    roadmap = tasks.split("## General MVP Roadmap", 1)[1]
    return current, backlog, completed, roadmap


def task_headings(section: str) -> dict[str, str]:
    return dict(re.findall(r"^### (T-\d+): (.+)$", section, flags=re.MULTILINE))


def roadmap_task_rows(roadmap: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for area, status, task in re.findall(
        r"^\| ([^|]+?) \| ([^|]+?) \| (T-\d+|Unpromoted) \|$",
        roadmap,
        flags=re.MULTILINE,
    ):
        if task.startswith("T-"):
            rows[task] = status
    return rows


def test_core_agent_files_exist():
    required = [
        "AGENTS.md",
        "SPEC.md",
        "TASKS.md",
        "EVALS.md",
        "docs/learn-the-ticker_proposal.md",
        "docs/learn_the_ticker_PRD.md",
        "docs/learn_the_ticker_technical_design_spec.md",
        "docs/README.md",
        "docs/mvp_functional_gap_review.md",
        "docs/SOURCE_HANDOFF.md",
        "docs/TOP500_MANIFEST_HANDOFF.md",
        "docs/ETF_MANIFEST_HANDOFF.md",
        "data/universes/us_equity_etfs.current.json",
    ]

    for filename in required:
        path = ROOT / filename
        assert path.exists(), f"{filename} is missing"
        assert path.read_text(encoding="utf-8").strip(), f"{filename} is empty"


def test_spec_contains_financial_safety_boundaries():
    spec = read_file("SPEC.md").lower()

    required_phrases = [
        "buy",
        "sell",
        "allocation",
        "tax advice",
        "unsupported price targets",
        "citations",
        "freshness",
    ]

    for phrase in required_phrases:
        assert phrase in spec, f"SPEC.md should mention safety concept: {phrase}"


def test_tasks_has_current_task_and_acceptance_criteria():
    current_task, backlog, _, _ = task_sections()
    current_lower = current_task.lower()
    backlog_lower = backlog.lower()

    if "no current task is prepared" in current_lower:
        assert "no backlog tasks are currently prepared" in backlog_lower
        assert "### t-" not in current_lower
        assert "### t-" not in backlog_lower
        return

    assert "### t-" in current_lower
    assert "acceptance criteria" in current_lower
    assert "required commands" in current_lower
    assert "iteration budget" in current_lower


def test_agents_contains_git_safety_rules():
    agents = read_file("AGENTS.md").lower()

    forbidden_commands = [
        "git reset --hard",
        "git clean -fd",
        "git push --force",
    ]

    for command in forbidden_commands:
        assert command in agents, f"AGENTS.md should explicitly restrict {command}"


def test_agents_uses_updated_prd_tds_source_order():
    agents = read_file("AGENTS.md")
    required_reading = [
        "docs/learn_the_ticker_PRD.md",
        "docs/learn_the_ticker_technical_design_spec.md",
        "docs/learn-the-ticker_proposal.md",
        "SPEC.md",
        "TASKS.md",
        "EVALS.md",
    ]

    for marker in required_reading:
        assert marker in agents, f"AGENTS.md should require reading {marker}"

    conflict_order = agents.split("If these files conflict, follow this order:", 1)[1]
    ordered_markers = [
        "Safety and advice-boundary rules",
        "docs/learn_the_ticker_PRD.md",
        "docs/learn_the_ticker_technical_design_spec.md",
        "docs/learn-the-ticker_proposal.md",
        "SPEC.md",
        "TASKS.md",
        "EVALS.md",
    ]
    positions = [conflict_order.index(marker) for marker in ordered_markers]
    assert positions == sorted(positions), "AGENTS.md should use safety, PRD, TDS, proposal, SPEC, TASKS, EVALS order"
    assert "Should I buy QQQ?" in agents
    assert "\ue000" not in agents


def test_agent_loop_uses_retry_budget_and_clean_commit_policy():
    bash_loop = read_file("scripts/agent_loop.sh")
    task_cycle = read_file("scripts/run_task_cycle.sh")
    powershell_loop = read_file("scripts/agent_loop.ps1")
    activate_env = read_file("scripts/activate_agent_env.sh")

    assert "ITERATION_BUDGET" in bash_loop
    assert "for ATTEMPT in" in bash_loop
    assert "--commit-failures" in bash_loop
    assert "Leaving changes uncommitted and unstaged for review." in bash_loop
    assert "ensure_agent_branch" in bash_loop
    assert "agent_loop blocks 'git" in bash_loop
    assert 'PATH="$ROOT/$AGENT_GIT_WRAPPER_DIR:$PATH" ltt_codex_exec' in bash_loop
    assert "ensure_repeat_backlog_capacity" in task_cycle
    assert "Repeat backlog preflight" in task_cycle
    assert "human_action_marker_present" in task_cycle

    assert "$IterationBudget" in powershell_loop
    assert "for ($Attempt = 1" in powershell_loop
    assert "CommitFailures" in powershell_loop
    assert "Leaving changes uncommitted and unstaged for review." in powershell_loop
    assert 'LTT_DEFAULT_CODEX_MODEL="${LTT_DEFAULT_CODEX_MODEL:-gpt-5.5}"' in activate_env
    assert 'LTT_DEFAULT_CODEX_REASONING_EFFORT="${LTT_DEFAULT_CODEX_REASONING_EFFORT:-high}"' in activate_env
    assert 'LTT_CODEX_MODEL="${LTT_CODEX_MODEL:-$LTT_DEFAULT_CODEX_MODEL}"' in activate_env
    assert 'LTT_CODEX_REASONING_EFFORT="${LTT_CODEX_REASONING_EFFORT:-$LTT_DEFAULT_CODEX_REASONING_EFFORT}"' in activate_env
    assert 'reasoning.effort=\\"$LTT_CODEX_REASONING_EFFORT\\"' in activate_env
    assert "ltt_set_codex_preferences" in activate_env
    assert "--model <model>" in bash_loop
    assert "--reasoning-effort <effort>" in bash_loop
    assert "--model <model>" in task_cycle
    assert "--reasoning-effort <effort>" in task_cycle
    assert "Get-CodexExecArgs" in powershell_loop
    assert '[string]$CodexModel = "gpt-5.5"' in powershell_loop
    assert '[string]$CodexReasoningEffort = "high"' in powershell_loop
    assert 'reasoning.effort=""$CodexReasoningEffort""' in powershell_loop

    for source in [bash_loop, task_cycle, powershell_loop]:
        assert "docs/learn-the-ticker_proposal.md" in source
        assert (
            "updated PRD, technical design spec, proposal, SPEC, TASKS, and EVALS" in source
            or "PRD/TDS-first authority after safety" in source
        )


def test_frontend_workspace_and_root_scripts_are_aligned():
    root_package = read_file("package.json")
    web_package_path = ROOT / "apps" / "web" / "package.json"

    assert web_package_path.exists(), "apps/web/package.json should exist"
    assert '"workspaces"' in root_package
    assert '"apps/web"' in root_package

    for script in ["dev", "build", "start", "typecheck"]:
        assert f"npm --workspace apps/web run {script}" in root_package

    for path in [
        "apps/web/app/page.tsx",
        "apps/web/app/assets/[ticker]/page.tsx",
        "apps/web/app/compare/page.tsx",
        "apps/web/components/SearchBox.tsx",
        "apps/web/lib/fixtures.ts",
        "apps/web/styles/globals.css",
    ]:
        assert (ROOT / path).exists(), f"{path} should exist after the apps/web rebase"


def test_environment_scaffolds_are_placeholder_only():
    expected_files = [
        ".env.example",
        "apps/web/.env.example",
        "deploy/env/api.example.env",
        "deploy/env/worker.example.env",
        "deploy/env/web.example.env",
        "docker-compose.yml",
        "docker/api/Dockerfile",
        "docker/web/Dockerfile",
    ]

    for filename in expected_files:
        path = ROOT / filename
        assert path.exists(), f"{filename} should exist"
        text = path.read_text(encoding="utf-8")
        assert (
            "LLM_LIVE_GENERATION_ENABLED=false" in text
            or 'LLM_LIVE_GENERATION_ENABLED: "false"' in text
            or filename in {
            "apps/web/.env.example",
            "deploy/env/web.example.env",
            "docker/api/Dockerfile",
            "docker/web/Dockerfile",
            }
        )
        for forbidden in ["sk-", "OPENAI_API_KEY=", "BEGIN PRIVATE KEY", "xoxb-", "ghp_"]:
            if forbidden.endswith("="):
                continue
            assert forbidden not in text, f"{filename} should not contain real-looking secret marker {forbidden}"

    web_env = (ROOT / "apps/web/.env.example").read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_API_BASE_URL" in web_env
    assert "OPENROUTER_API_KEY" not in web_env
    assert "FMP_API_KEY" not in web_env


def test_etf_universe_contract_files_are_local_metadata_only():
    manifest = read_file("data/universes/us_equity_etfs.current.json")
    module = read_file("backend/etf_universe.py")

    assert "us-equity-etf-universe-v1" in manifest
    assert "EQUITY_ETF_UNIVERSE_MANIFEST_URI" in manifest
    assert "no live provider" in manifest
    assert "recognized_unsupported" in manifest
    assert "eligible_not_cached" in manifest
    assert "unavailable" in manifest
    assert "ETFUniverseContractError" in module
    assert "load_etf_universe_manifest" in module

    combined = f"{manifest}\n{module}"
    for forbidden in [
        "BEGIN PRIVATE KEY",
        "OPENROUTER_API_KEY=",
        "FMP_API_KEY=",
        "ALPHA_VANTAGE_API_KEY=",
        "FINNHUB_API_KEY=",
        "TIINGO_API_KEY=",
        "EODHD_API_KEY=",
        "import requests",
        "import httpx",
        "boto3",
        "os.environ",
        "api_key",
    ]:
        assert forbidden not in combined


def test_weekly_news_event_evidence_repository_contract_is_dormant_metadata_only():
    repository = read_file("backend/repositories/weekly_news.py")
    shim = read_file("backend/weekly_news_repository.py")
    migration = read_file("alembic/versions/20260425_0008_weekly_news_event_evidence_contracts.py")

    combined = f"{repository}\n{shim}\n{migration}"

    assert "weekly-news-event-evidence-repository-contract-v1" in combined
    assert "weekly-news-live-acquisition-readiness-boundary-v1" in combined
    assert "weekly-news-official-source-mocked-acquisition-boundary-v1" in combined
    assert "weekly-news-official-source-mocked-fetch-boundary-v1" in combined
    assert "weekly-news-official-source-parser-adapter-boundary-v1" in combined
    assert "weekly_news_market_week_windows" in combined
    assert "weekly_news_event_candidates" in combined
    assert "weekly_news_selected_events" in combined
    assert "weekly_news_ai_thresholds" in combined
    assert "weekly_news_diagnostics" in combined
    assert "compute_weekly_news_window" in repository
    assert "no_live_external_calls" in repository
    assert "provider_or_llm_call_required" in repository
    assert "persisted_evidence_only" in repository
    assert "threshold_metadata_only" in repository

    for forbidden in ["import requests", "import httpx", "urllib.request", "from socket import", "os.environ", "api_key"]:
        assert forbidden not in combined
    for forbidden in [
        "BEGIN PRIVATE KEY",
        "OPENROUTER_API_KEY=",
        "FMP_API_KEY=",
        "ALPHA_VANTAGE_API_KEY=",
        "FINNHUB_API_KEY=",
        "TIINGO_API_KEY=",
        "EODHD_API_KEY=",
        "import requests",
        "import httpx",
        "boto3",
        "os.environ",
        "api_key",
    ]:
        assert forbidden not in combined


def test_llm_transport_contract_is_backend_only_mock_injected_and_dormant():
    transport = read_file("backend/llm_transport.py")
    models = read_file("backend/models.py")
    combined = f"{transport}\n{models}"

    assert "llm-transport-contract-v1" in combined
    assert "call_openrouter_transport" in transport
    assert "TransportCallable" in transport
    assert "injected_transport_missing" in transport
    assert "explicit_live_transport_opt_in_missing" in transport
    assert "server_side_key_missing" in transport
    assert "openrouter_model_chain_missing" in transport
    assert "validation_not_ready" in transport
    assert "LlmTransportResult" in models
    assert "LlmTransportStatus" in models
    assert "LlmTransportMode" in models

    for forbidden in [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "os.environ",
        "openai",
        "anthropic",
        "NEXT_PUBLIC",
        "OPENROUTER_API_KEY",
        "Authorization",
        "Bearer ",
    ]:
        assert forbidden not in transport


def test_control_docs_cover_new_mvp_operating_rules():
    combined = "\n".join(read_file(name) for name in ["AGENTS.md", "SPEC.md", "EVALS.md"])

    for marker in [
        "Top-500",
        "candidate manifest",
        "IWB",
        "Golden Asset Source Handoff",
        "pending_ingestion",
        "out-of-scope",
        "Weekly News Focus",
        "AI Comprehensive Analysis",
        "source-use",
        "LLM_LIVE_GENERATION_ENABLED",
        "OpenRouter",
        "apps/web",
        "Docker Compose",
    ]:
        assert marker in combined, f"control docs should mention {marker}"


def test_mvp_functional_gap_review_tracks_v06_progress_and_next_tasks():
    review = read_file("docs/mvp_functional_gap_review.md")
    review_lower = review.lower()

    assert "Task: 2026-04-28 v0.6 doc alignment and fresh-data MVP review" in review
    for marker in [
        "The repo is no longer planning-only",
        "Golden Asset Source Handoff enforcement",
        "T-119 is complete",
        "T-120 is complete",
        "T-121 is complete",
        "T-122 is complete",
        "T-123 is complete",
        "T-124 is complete",
        "data/universes/us_equity_etfs_supported.current.json",
        "data/universes/us_etp_recognition.current.json",
        "Launch-sized manifests are not approved",
        "ETF eligible-universe implementation is not complete",
        "Launch-sized governed source artifacts are absent",
        "Local live-AI validation is operator-smoke covered, not launch-approved",
        "T-126 completed repo-native source-handoff manifest inspection/finalization smoke tooling",
        "T-127 completed the opt-in local live-AI validation smoke",
        "T-128 completed deterministic governed golden API/frontend rendering proof",
        "T-129 completed review-only launch-manifest operator automation parity",
        "T-130 completed the local fresh-data MVP rehearsal command",
        "T-131 completed ETF eligible-universe review packet contracts",
        "T-132 completed stock SEC source-pack readiness packet contracts",
        "T-133 completed ETF issuer source-pack readiness packet contracts",
        "T-134 completed local fresh-data MVP readiness thresholds",
        "T-135 completed batchable local ingestion priority planning",
        "scripts/run_local_fresh_data_rehearsal.py --json",
        "Normal CI remains deterministic",
    ]:
        assert marker in review, f"functional review should include marker: {marker}"

    for forbidden in [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "os.environ",
        "api_key",
        "OPENROUTER_API_KEY",
        "FMP_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
        "FINNHUB_API_KEY",
        "TIINGO_API_KEY",
        "EODHD_API_KEY",
        "BEGIN PRIVATE KEY",
        "signed url",
        "public storage url",
    ]:
        assert forbidden.lower() not in review_lower


def test_v06_handoff_docs_use_repo_native_commands_and_future_boundaries():
    source = read_file("docs/SOURCE_HANDOFF.md")
    top500 = read_file("docs/TOP500_MANIFEST_HANDOFF.md")
    etf = read_file("docs/ETF_MANIFEST_HANDOFF.md")
    combined = "\n".join([source, top500, etf])

    for marker in [
        "backend/source_policy.py",
        "config/source_allowlist.yaml",
        "scripts/inspect_source_handoff_manifest.py",
        "source-handoff-manifest-v1",
        "TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py inspect",
        "TMPDIR=/tmp python3 scripts/inspect_source_handoff_manifest.py finalize",
        "scripts/generate_top500_candidate_manifest.py",
        "scripts/review_launch_manifests.py",
        "TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 generate",
        "TMPDIR=/tmp python3 scripts/review_launch_manifests.py top500 inspect",
        "TMPDIR=/tmp python3 scripts/review_launch_manifests.py etf inspect",
        "backend/etf_universe.py",
        "TMPDIR=/tmp bash scripts/run_quality_gate.sh",
        "EQUITY_ETF_UNIVERSE_MANIFEST_URI",
        "review-only",
    ]:
        assert marker in combined

    for forbidden in [
        "services/api",
        "app.cli",
        "worker.main",
        "corepack pnpm",
        ".github/workflows/top500-candidate-refresh.yml",
    ]:
        assert forbidden not in combined



def test_t114_mvp_launch_readiness_docs_cover_regression_matrix_and_go_no_go_without_runtime_wiring():
    matrix = read_file("docs/mvp_launch_readiness_regression_matrix.md")
    checklist = read_file("docs/mvp_go_no_go_checklist.md")
    combined = f"{matrix}\n{checklist}"
    combined_lower = combined.lower()

    assert "Task: T-114" in matrix
    assert "Task: T-114" in checklist

    for marker in [
        "Home remains a single supported stock or ETF search first",
        "Comparison remains a separate connected `/compare` workflow",
        "Glossary remains contextual help",
        "mobile bottom-sheet or full-screen behavior markers",
        "single-company-vs-ETF-basket structure",
        "Weekly News Focus renders only the evidence-backed set",
        "data/universes/us_common_stocks_top500.current.json",
        "candidate Top-500 refresh work is a later reviewed workflow",
        "Golden Asset Source Handoff remains the approval gate",
    ]:
        assert marker in matrix, f"matrix should preserve T-114 scope marker: {marker}"

    for marker in [
        "`AAPL`, `VOO`, and `QQQ`",
        "broader eligible ETF categories and reference tickers such as `XLE` need reviewed source-pack readiness",
        "Crypto, leveraged ETFs, inverse ETFs, fixed-income ETFs, commodity ETFs, active ETFs, multi-asset ETFs",
        "`GME` and `VXX`",
        "Unknown/no-result copy says facts are not invented",
    ]:
        assert marker in matrix, f"matrix should document launch coverage marker: {marker}"

    for marker in [
        "`/api/search`",
        "`/api/assets/{ticker}/overview`",
        "`/api/assets/{ticker}/weekly-news`",
        "`/api/compare`",
        "`/api/assets/{ticker}/chat`",
        "`/api/assets/{ticker}/sources`",
        "`/api/assets/{ticker}/glossary`",
        "Export endpoints",
        "Ingestion and pre-cache routes",
    ]:
        assert marker in matrix, f"matrix should cover route surface: {marker}"

    for marker in [
        "Unapproved or not-governed",
        "Unclear rights",
        "Parser-invalid",
        "Hidden/internal",
        "Pending review",
        "Rejected",
        "Generated-output cache",
        "Export",
    ]:
        assert marker in matrix, f"matrix should cover source-use state: {marker}"

    for marker in [
        "Production admin auth",
        "Rate limiting",
        "Deployment environment validation",
        "Private object storage",
        "Database migration execution",
        "Cloud Run API settings",
        "Cloud Run Job settings",
        "Recurring job decisions",
        "Source allowlist review",
        "Live-provider opt-in",
        "Monitoring and alerting",
        "Rollback",
        "Cost controls",
        "Launch support",
        "Legal/compliance review",
        "Current T-114 decision: **No-go for production deployment**",
    ]:
        assert marker in checklist, f"checklist should record go/no-go risk: {marker}"

    for command in [
        "npm test",
        "npm run typecheck",
        "npm run build",
        "python3 -m pytest tests/integration/test_backend_api.py -q",
        "python3 -m pytest tests/unit/test_search_classification.py tests/unit/test_ingestion_jobs.py tests/unit/test_safety_guardrails.py tests/unit/test_repo_contract.py -q",
        "python3 -m pytest tests -q",
        "python3 evals/run_static_evals.py",
        "bash scripts/run_quality_gate.sh",
        "git diff --check",
    ]:
        assert command in matrix, f"matrix should list required command: {command}"

    for forbidden in [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "os.environ",
        "api_key",
        "OPENROUTER_API_KEY",
        "FMP_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
        "FINNHUB_API_KEY",
        "TIINGO_API_KEY",
        "EODHD_API_KEY",
        "BEGIN PRIVATE KEY",
        "sk-",
        "xoxb-",
        "ghp_",
    ]:
        assert forbidden.lower() not in combined_lower


def test_tasks_general_mvp_roadmap_tracks_stable_completed_milestones():
    tasks = read_file("TASKS.md")
    current_task, backlog, completed, roadmap = task_sections()
    active_sections = f"{current_task}\n{backlog}"
    current_lower = current_task.lower()
    backlog_lower = backlog.lower()
    current_tasks = task_headings(current_task)
    backlog_tasks = task_headings(backlog)
    completed_tasks = task_headings(completed)
    roadmap_rows = roadmap_task_rows(roadmap)

    assert "## MVP Backend Roadmap" not in tasks
    if "no current task is prepared" in current_lower:
        assert "no backlog tasks are currently prepared" in backlog_lower
        assert not current_tasks
        assert not backlog_tasks
    else:
        assert len(current_tasks) == 1
        for marker in [
            "Acceptance criteria",
            "Required commands",
            "Iteration budget",
        ]:
            assert marker in current_task
    if "no backlog tasks" in backlog_lower:
        assert not backlog_tasks

    assert completed_tasks
    assert "Full production deployment, recurring jobs, and broad paid-provider integrations" in roadmap
    assert "| Full production deployment, recurring jobs, and broad paid-provider integrations | Later | Unpromoted |" in roadmap

    for task_id in current_tasks:
        assert task_id not in completed_tasks
        if task_id in roadmap_rows:
            assert roadmap_rows[task_id] == "Current"

    for task_id in backlog_tasks:
        assert task_id not in completed_tasks
        if task_id in roadmap_rows:
            assert roadmap_rows[task_id] == "Prepared"

    for task_id in completed_tasks:
        if task_id in roadmap_rows:
            assert roadmap_rows[task_id] == "Completed", f"{task_id} should be Completed in roadmap"

    for task_id, status in roadmap_rows.items():
        if status == "Current":
            assert task_id in current_tasks, f"{task_id} is Current in roadmap but not current task"
        if status == "Prepared":
            assert task_id in backlog_tasks, f"{task_id} is Prepared in roadmap but not backlog"
        if status == "Completed":
            assert task_id in completed_tasks, f"{task_id} is Completed in roadmap but not completed section"

    for marker in [
        "### T-118: Prove local fresh-data ingest-to-render smoke path",
        "### T-119: Wire local frontend API access and backend CORS",
        "### T-120: Implement v0.5 ETF manifest split contracts",
        "### T-125: Align v0.6 handoff docs and MVP backlog",
        "### T-126: Add repo-native source-handoff manifest smoke tooling",
        "### T-127: Add opt-in local live-AI validation smoke",
        "### T-128: Prove governed golden evidence drives API and frontend rendering",
        "### T-129: Add launch-manifest operator automation parity",
        "### T-130: Add local fresh-data MVP rehearsal command",
        "### T-131: Add ETF eligible-universe review packet contracts",
        "### T-132: Add stock SEC source-pack readiness packet contracts",
        "### T-133: Add ETF issuer source-pack readiness packet contracts",
        "### T-134: Add local fresh-data MVP readiness thresholds",
        "### T-135: Add batchable local ingestion priority planner",
        "The runbook explicitly states that fetching alone is retrieval, not evidence approval",
        "deterministic integration smoke coverage for the VOO golden path",
        "mocked official-source acquisition",
        "Golden Asset Source Handoff",
        "Production deployment, production durable storage, scheduled jobs",
        "Next.js rewrite",
        "build_cors_settings",
        "review-only operator automation parity",
        "Added source-snapshot validation to the persisted overview read path",
    ]:
        assert marker in completed

    for marker in [
        "T-119 closed the local frontend/API plumbing blockers",
        "T-125 completed the v0.6 handoff-doc and MVP-backlog alignment pass",
        "T-126 completed repo-native source-handoff manifest inspection/finalization smoke tooling",
        "T-127 completed the opt-in local live-AI validation smoke",
        "T-128 completed deterministic governed golden API/frontend rendering proof",
        "T-129 completed launch-manifest operator automation parity",
        "T-130 completed the deterministic local fresh-data MVP rehearsal command",
        "T-099 established deterministic provider content export-rights hardening",
        "T-100 established the backend MVP runtime gap audit and roadmap tracker",
        "T-101 established configured persisted-reader route wiring with fixture fallback",
        "T-102 established executable local ingestion ledger and mocked worker transitions",
        "T-103 established mocked SEC EDGAR stock golden-path acquisition",
        "T-104 established mocked official ETF issuer golden-path acquisition",
        "T-106 established deterministic normalized knowledge-pack writes from acquisition outputs",
        "T-107 established deterministic persisted Weekly News Focus event evidence for golden assets",
        "T-108 established deterministic generated-output cache writes and freshness invalidation",
        "T-109 established frontend API-backed search, pending states, and dynamic asset-page rendering",
        "T-110 established persisted end-to-end comparison, chat, source, glossary, Weekly News, and export verification",
        "T-111 established local durable repository execution with in-memory fallback",
        "T-115 established Golden Asset Source Handoff contract enforcement",
        "T-116 established reviewed Top-500 candidate manifest workflow contracts",
        "T-117 established handoff-gated mocked official-source acquisition execution for golden assets",
        "T-118 documented and regression-covered the deterministic local fresh-data ingest-to-render smoke path",
        "T-118 established the local fresh-data ingest-to-render runbook and deterministic smoke coverage",
        "T-119 established local frontend API access and backend CORS",
        "T-120 established the v0.5 split between supported ETF generated-output coverage",
        "T-124 established reviewed launch-universe expansion planning",
        "T-125 established v0.6 docs, handoff docs, and backlog alignment",
        "Full production deployment, recurring production jobs, broad paid-provider integrations",
    ]:
        assert marker in roadmap


def test_local_fresh_data_rehearsal_default_is_deterministic_and_review_only():
    result = run_rehearsal(env={})

    assert result["schema_version"] == "local-fresh-data-mvp-rehearsal-v1"
    assert result["status"] == "pass"
    assert result["normal_ci_requires_live_calls"] is False
    assert result["production_services_started"] is False
    assert result["manifests_promoted"] is False
    assert result["sources_approved_by_rehearsal"] is False
    threshold = result["local_mvp_threshold_summary"]
    assert threshold["schema_version"] == "local-fresh-data-mvp-threshold-summary-v1"
    assert threshold["threshold_contract"] == "review_only_no_launch_approval_v1"
    assert threshold["overall_local_approval_status"] == "ready_for_local_operator_review"
    assert threshold["local_operator_review_ready"] is True
    assert threshold["launch_or_public_deployment_approved"] is False
    assert threshold["required_blockers"] == []
    assert threshold["optional_blockers"] == []
    assert len(threshold["required_checks"]) == 10
    assert all(check["status"] == "pass" for check in threshold["required_checks"])
    assert len(threshold["optional_skipped_modes"]) == 4
    assert threshold["thresholds"] == {
        "required_blockers_allowed": 0,
        "optional_blockers_allowed": 0,
        "failed_assets_allowed": 1,
        "unavailable_assets_allowed": 1,
        "generated_surface_violations_allowed": 0,
    }
    assert threshold["review_only_boundaries"] == {
        "sources_approved": False,
        "top500_manifest_promoted": False,
        "etf_supported_manifest_promoted": False,
        "etp_recognition_manifest_promoted": False,
        "ingestion_started": False,
        "generated_output_cache_entries_written": False,
        "production_services_started": False,
        "normal_ci_requires_live_calls": False,
    }
    statuses = {check["check_id"]: check["status"] for check in result["checks"]}
    assert statuses["deterministic_default_boundary"] == "pass"
    assert statuses["source_handoff_approval_gate"] == "pass"
    assert statuses["governed_golden_api_rendering"] == "pass"
    assert statuses["local_fresh_data_mvp_slice_smoke"] == "pass"
    assert statuses["stock_vs_etf_comparison_readiness"] == "pass"
    assert statuses["launch_manifest_review_packets"] == "pass"
    assert statuses["stock_sec_source_pack_readiness"] == "pass"
    assert statuses["local_ingestion_priority_planner"] == "pass"
    assert statuses["frontend_v04_smoke_markers"] == "pass"
    assert statuses["optional_browser_services"] == "skipped"
    assert statuses["optional_local_durable_repositories"] == "skipped"
    assert statuses["optional_official_source_retrieval"] == "skipped"
    assert statuses["optional_live_ai_review"] == "skipped"
    slice_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "local_fresh_data_mvp_slice_smoke"
    )
    assert slice_details["schema_version"] == "local-fresh-data-mvp-slice-smoke-v1"
    assert slice_details["normal_ci_requires_live_calls"] is False
    assert slice_details["browser_startup_required"] is False
    assert slice_details["local_services_required"] is False
    assert slice_details["secret_values_reported"] is False
    assert slice_details["raw_payload_values_reported"] is False
    assert slice_details["raw_payload_exposed_count"] == 0
    assert slice_details["status_counts"] == {"pass": 3, "partial": 5, "blocked": 4, "unavailable": 0}
    assert slice_details["supported_renderable_tickers"] == [
        "AAPL",
        "MSFT",
        "NVDA",
        "VOO",
        "SPY",
        "VTI",
        "QQQ",
        "XLK",
    ]
    assert slice_details["blocked_regression_tickers"] == ["TQQQ", "ARKK", "BND", "GLD"]
    slice_rows = {row["ticker"]: row for row in slice_details["rows"]}
    assert slice_rows["AAPL"]["source_labels"] == ["official", "provider_derived"]
    assert slice_rows["VOO"]["source_labels"] == ["partial", "provider_derived"]
    assert slice_rows["TQQQ"]["fetch_call_count"] == 0
    assert all(row["raw_payload_exposed"] is False for row in slice_rows.values())
    launch_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "launch_manifest_review_packets"
    )
    assert launch_details["etf_eligible_universe_scope_version"] == "etf-eligible-universe-review-scope-v1"
    assert launch_details["etf_readiness_counts"]["supported"] == 13
    assert launch_details["etf_readiness_counts"]["recognition_only"] == 9
    assert launch_details["etf_readiness_counts"]["source_pack_ready"] == 0
    assert launch_details["etf_readiness_counts"]["generated_output_eligible"] == 2
    assert launch_details["etf_full_eligible_universe_count"] == 13
    assert launch_details["etf_non_golden_eligible_supported_count"] == 11
    assert "sector" in launch_details["etf_represented_categories_beyond_golden"]
    assert launch_details["etf500_review_contract_version"] == "etf500-candidate-manifest-review-contract-v1"
    assert launch_details["etf500_practical_supported_row_range"] == {"minimum": 475, "maximum": 525}
    assert [milestone["batch"] for milestone in launch_details["etf500_batch_milestones"]] == [
        "ETF-50",
        "ETF-150",
        "ETF-300",
        "ETF-500",
    ]
    assert launch_details["etf500_candidate_artifact_path_conventions"] == [
        "data/universes/us_equity_etfs_supported.candidate.YYYY-MM.etf500.json",
        "data/universes/us_etp_recognition.candidate.YYYY-MM.json",
        "data/universes/us_equity_etfs.candidate.YYYY-MM.etf500.promotion-packet.json",
    ]
    target_buckets = {bucket["bucket_id"]: bucket for bucket in launch_details["etf500_category_target_buckets"]}
    assert target_buckets["broad_core_us_equity_beta"]["target_count"] == 45
    assert target_buckets["market_cap_and_size_style"]["target_count"] == 95
    assert target_buckets["sector_etfs"]["target_count"] == 120
    assert target_buckets["industry_theme_passive_us_equity"]["target_count"] == 105
    assert target_buckets["dividend_and_shareholder_yield_index"]["target_count"] == 55
    assert target_buckets["factor_smart_beta_and_equal_weight"]["target_count"] == 60
    assert target_buckets["esg_values_screened_us_equity_index"]["target_count"] == 20
    assert launch_details["etf500_current_fixture_not_launch_coverage"] is True
    assert launch_details["etf500_category_coverage_gap_count"] == 7
    assert launch_details["etf500_disqualifier_counts"]["leveraged_etf"] >= 1
    assert launch_details["etf500_disqualifier_counts"]["option_income_or_buffer_etf"] == 0
    assert launch_details["etf500_source_pack_readiness"]["ready_count"] == 0
    assert launch_details["etf500_source_pack_readiness"]["incomplete_count"] == 13
    assert launch_details["etf500_parser_handoff_readiness"]["handoff_not_ready_count"] >= 13
    assert launch_details["etf500_checksum_status"] == {
        "supported_checksum_matches": True,
        "recognition_checksum_matches": True,
    }
    assert "do_not_pad_with_leveraged_etf" in launch_details["etf500_no_padding_stop_conditions"]
    assert "do_not_pad_with_option_income_or_buffer_etf" in launch_details["etf500_no_padding_stop_conditions"]
    assert "do_not_pad_with_cef" in launch_details["etf500_no_padding_stop_conditions"]
    assert launch_details["etf500_generated_output_blocking_rules"][
        "recognition_only_rows_unlock_generated_output"
    ] is False
    assert "generated_output_cache_entries" in launch_details["etf500_generated_output_blocking_rules"][
        "blocked_generated_surfaces"
    ]
    stock_sec_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "stock_sec_source_pack_readiness"
    )
    assert stock_sec_details["review_status"] == "review_needed"
    assert stock_sec_details["runtime_manifest_authority"] == "data/universes/us_common_stocks_top500.current.json"
    assert stock_sec_details["candidate_manifest_paths"] == [
        "data/universes/us_common_stocks_top500.candidate.2026-04.json"
    ]
    assert stock_sec_details["required_sec_components"] == [
        "sec_submissions",
        "latest_annual_filing",
        "latest_quarterly_filing_when_available",
        "xbrl_company_facts",
    ]
    assert stock_sec_details["readiness_counts"]["current_manifest_rows"] == 10
    assert stock_sec_details["readiness_counts"]["candidate_manifest_rows"] == 10
    assert stock_sec_details["readiness_counts"]["partial"] == 2
    assert stock_sec_details["readiness_counts"]["insufficient_evidence"] == 18
    assert stock_sec_details["readiness_counts"]["review_packet_unlocks_generated_output"] == 0
    top500_planning = stock_sec_details["top500_sec_source_pack_batch_planning"]
    assert top500_planning["schema_version"] == "top500-sec-source-pack-batch-plan-v1"
    assert top500_planning["boundary"] == "top500-sec-source-pack-batch-planning-review-only-v1"
    assert top500_planning["current_manifest_path"] == "data/universes/us_common_stocks_top500.current.json"
    assert top500_planning["support_resolved_from_current_manifest_only"] is True
    assert top500_planning["candidate_or_priority_data_resolves_runtime_support"] is False
    assert top500_planning["live_provider_or_exchange_data_resolves_runtime_support"] is False
    assert top500_planning["candidate_relationship_diagnostics"]["candidate_artifacts_available"] is True
    assert top500_planning["candidate_relationship_diagnostics"]["candidate_data_used_for_runtime_support"] is False
    assert top500_planning["planning_summary"] == {
        "planned_row_count": 10,
        "batch_count": 5,
        "high_demand_pre_cache_count": 1,
        "top500_review_count": 9,
        "source_backed_partial_ready_count": 1,
        "insufficient_evidence_count": 9,
        "blocked_generated_surface_count": 9,
    }
    assert top500_planning["manifest_rank_ordering"][:3] == [
        {"rank": 1, "ticker": "AAPL"},
        {"rank": 2, "ticker": "MSFT"},
        {"rank": 3, "ticker": "NVDA"},
    ]
    top500_batches = {group["batch_name"]: group for group in top500_planning["batch_groups"]}
    assert top500_batches["high-demand-pre-cache"]["tickers"] == ["AAPL"]
    assert top500_batches["TOP500-50"]["planned_row_count"] == 9
    top500_priorities = {
        group["readiness_priority"]: group["planned_row_count"]
        for group in top500_planning["readiness_priority_groups"]
    }
    assert top500_priorities == {
        "approved_partial_ready_needs_quarterly_or_full_review": 1,
        "missing_required_sec_sources": 9,
    }
    assert top500_planning["source_handoff_readiness"]["approved_component_count"] == 3
    assert top500_planning["parser_readiness"]["parser_status_counts"]["pending_review"] == 37
    assert top500_planning["freshness_as_of_checksum_placeholder_status"]["checksum_present_count"] == 0
    assert "candidate_artifacts_are_diagnostic_only" in top500_planning["stop_conditions"]
    assert "generated_pages" in top500_planning["blocked_generated_surfaces"]
    assert "generated_chat_answers" in stock_sec_details["blocked_generated_surfaces"]
    etf_readiness_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "etf_issuer_source_pack_readiness"
    )
    etf500_planning = etf_readiness_details["etf500_source_pack_batch_planning"]
    assert etf500_planning["schema_version"] == "etf500-issuer-source-pack-batch-plan-v1"
    assert etf500_planning["boundary"] == "etf500-issuer-source-pack-batch-planning-review-only-v1"
    assert etf500_planning["candidate_review_metadata_consumed"] is True
    assert etf500_planning["candidate_artifacts_available"] is False
    assert etf500_planning["fallback_to_current_fixture_review_metadata"] is True
    assert etf500_planning["fallback_not_launch_coverage"] is True
    assert etf500_planning["planning_summary"] == {
        "planned_row_count": 13,
        "batch_count": 4,
        "issuer_count": 5,
        "category_bucket_count": 7,
        "source_pack_ready_count": 0,
        "source_pack_partial_count": 2,
        "source_pack_incomplete_count": 11,
        "blocked_generated_surface_count": 9,
    }
    assert [group["batch"] for group in etf500_planning["batch_groups"]] == [
        "ETF-50",
        "ETF-150",
        "ETF-300",
        "ETF-500",
    ]
    assert etf500_planning["batch_groups"][0]["planned_row_count"] == 13
    assert etf500_planning["batch_groups"][1]["planned_row_count"] == 0
    planning_priorities = {
        group["source_pack_readiness_priority"]: group["planned_row_count"]
        for group in etf500_planning["source_pack_readiness_priority_groups"]
    }
    assert planning_priorities == {
        "missing_required_issuer_sources": 11,
        "source_backed_partial_review": 2,
    }
    category_groups = {group["bucket_id"]: group for group in etf500_planning["category_bucket_groups"]}
    assert category_groups["broad_core_us_equity_beta"]["planned_row_count"] == 7
    assert category_groups["sector_etfs"]["planned_row_count"] == 4
    assert category_groups["dividend_and_shareholder_yield_index"]["planned_row_count"] == 0
    assert etf500_planning["target_context"]["practical_supported_row_range"] == {"minimum": 475, "maximum": 525}
    assert etf500_planning["target_context"]["current_fixture_not_launch_coverage"] is True
    assert "generated_output_cache_entries" in etf500_planning["blocked_generated_surfaces"]
    planner_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "local_ingestion_priority_planner"
    )
    assert planner_details["schema_version"] == "local-ingestion-priority-plan-v1"
    assert planner_details["boundary"] == "local-ingestion-priority-planner-review-only-v1"
    assert planner_details["summary"] == {
        "planned_asset_count": 23,
        "batch_count": 6,
        "ready_to_inspect_count": 3,
        "blocked_or_not_ready_count": 20,
        "high_demand_pre_cache_count": 3,
        "supported_etf_manifest_count": 11,
        "top500_stock_manifest_count": 9,
        "blocked_diagnostic_count": 4,
    }
    assert planner_details["first_batch_tickers"] == ["AAPL", "VOO", "QQQ"]
    assert planner_details["supported_etf_runtime_authority"] == "data/universes/us_equity_etfs_supported.current.json"
    assert planner_details["recognition_manifest_used_for_priority_order"] is False
    assert planner_details["recognition_rows_unlock_generated_output"] is False
    assert planner_details["top500_runtime_authority"] == "data/universes/us_common_stocks_top500.current.json"
    assert planner_details["state_diagnostics"]["states"]["pending"] == 18
    assert planner_details["state_diagnostics"]["states"]["running"] == 1
    assert planner_details["state_diagnostics"]["states"]["succeeded"] == 3
    assert planner_details["state_diagnostics"]["states"]["failed"] == 1
    assert planner_details["state_diagnostics"]["states"]["unsupported"] == 1
    assert planner_details["state_diagnostics"]["states"]["out_of_scope"] == 1
    assert planner_details["state_diagnostics"]["states"]["unknown"] == 1
    assert planner_details["state_diagnostics"]["states"]["unavailable"] == 1
    assert planner_details["state_diagnostics"]["states"]["partial"] == 3
    assert planner_details["state_diagnostics"]["states"]["stale"] == 0
    assert planner_details["state_diagnostics"]["states"]["insufficient_evidence"] == 20
    assert "generated_output_cache_entries" in planner_details["blocked_generated_surfaces"]
    stock_vs_etf_details = next(
        check["details"] for check in result["checks"] if check["check_id"] == "stock_vs_etf_comparison_readiness"
    )
    assert stock_vs_etf_details["schema_version"] == "stock-vs-etf-comparison-readiness-v1"
    assert stock_vs_etf_details["boundary"] == "review_only_fixture_backed_no_services_no_live_calls_v1"
    assert stock_vs_etf_details["deterministic_pairs"] == {
        "stock_vs_etf": ["AAPL", "VOO"],
        "etf_vs_etf_baseline": ["VOO", "QQQ"],
        "broad_coverage_proven": False,
    }
    assert stock_vs_etf_details["backend_compare"]["state_status"] == "supported"
    assert stock_vs_etf_details["backend_compare"]["comparison_type"] == "stock_vs_etf"
    assert stock_vs_etf_details["backend_compare"]["availability_state"] == "available"
    assert stock_vs_etf_details["backend_compare"]["relationship_schema_version"] == "stock-etf-relationship-v1"
    assert stock_vs_etf_details["backend_compare"]["relationship_state"] == "direct_holding"
    assert stock_vs_etf_details["backend_compare"]["basket_structure"] == "single-company-vs-etf-basket"
    assert stock_vs_etf_details["backend_compare"]["source_reference_assets"] == ["AAPL", "VOO"]
    assert stock_vs_etf_details["backend_compare"]["old_frontend_only_holding_verified_present"] is False
    assert {"relationship_state", "evidence_boundary"} <= set(
        stock_vs_etf_details["backend_compare"]["badge_markers"]
    )
    assert stock_vs_etf_details["comparison_export"]["export_state"] == "available"
    assert stock_vs_etf_details["comparison_export"]["comparison_type"] == "stock_vs_etf"
    assert stock_vs_etf_details["comparison_export"]["binding_scope"] == "same_comparison_pack"
    assert stock_vs_etf_details["comparison_export"]["same_comparison_pack_citation_bindings_only"] is True
    assert stock_vs_etf_details["comparison_export"]["same_comparison_pack_source_bindings_only"] is True
    assert stock_vs_etf_details["comparison_export"]["relationship_context_section_present"] is True
    assert stock_vs_etf_details["comparison_export"]["educational_disclaimer_present"] is True
    assert stock_vs_etf_details["comparison_export"]["forbidden_advice_phrase_hits"] == []
    assert stock_vs_etf_details["chat_compare_redirect"] == {
        "endpoint": "POST /api/assets/VOO/chat",
        "safety_classification": "compare_route_redirect",
        "comparison_availability_state": "available",
        "route": "/compare?left=AAPL&right=VOO",
        "generated_multi_asset_chat_answer": False,
        "factual_citation_count": 0,
        "factual_source_document_count": 0,
    }
    assert stock_vs_etf_details["frontend_api_alignment"]["a_vs_b_search_routes_to_separate_compare_workflow"] is True
    assert stock_vs_etf_details["frontend_api_alignment"]["aapl_voo_opt_in_smoke_covered"] is True
    assert stock_vs_etf_details["frontend_api_alignment"]["next_api_proxy_documented"] is True
    assert {
        (case["left_ticker"], case["right_ticker"], case["availability_state"])
        for case in stock_vs_etf_details["unsupported_blocking_cases"]
    } == {
        ("VOO", "BTC", "unsupported"),
        ("VOO", "GME", "out_of_scope"),
        ("VOO", "SPY", "eligible_not_cached"),
        ("VOO", "ZZZZ", "unknown"),
        ("AAPL", "QQQ", "no_local_pack"),
    }
    assert stock_vs_etf_details["etf_vs_etf_baseline"] == {
        "left_ticker": "VOO",
        "right_ticker": "QQQ",
        "comparison_type": "etf_vs_etf",
        "availability_state": "available",
        "independent_of_stock_vs_etf_markers": True,
    }
    assert {
        "no_local_pack",
        "missing_backend_relationship_schema",
        "frontend_only_fallback",
        "unavailable_export",
        "chat_redirect_mismatch",
        "missing_source_citation_metadata",
        "missing_local_smoke_instructions",
        "unsupported_state_regression",
        "live_call_requirement",
    } == set(stock_vs_etf_details["blocker_reason_code_catalog"])
    assert stock_vs_etf_details["review_only_boundaries"]["services_started"] is False
    assert stock_vs_etf_details["review_only_boundaries"]["live_llm_calls"] is False
    assert stock_vs_etf_details["review_only_boundaries"]["comparison_coverage_broadened"] is False
    asset_summary = threshold["asset_state_summary"]
    assert asset_summary["failed_asset_count"] == 1
    assert asset_summary["unavailable_asset_count"] == 1
    assert asset_summary["partial_count"] == 4
    assert asset_summary["stale_count"] == 0
    assert asset_summary["unknown_count"] == 1
    assert asset_summary["insufficient_evidence_count"] == 29
    assert asset_summary["source_backed_partial_ready_count"] == 4
    assert asset_summary["generated_surface_violation_count"] == 0
    assert asset_summary["reason_codes_by_state"]["failed"] == ["fixture_pre_cache_failed"]
    assert asset_summary["reason_codes_by_state"]["unavailable"] == ["unavailable"]
    assert all(not row["generated_surface_exposed"] for row in asset_summary["non_generated_assets"])
    assert all(row["citation_count"] == 0 and row["source_document_count"] == 0 for row in asset_summary["non_generated_assets"])
    for surface in [
        "generated_claims",
        "generated_chat_answers",
        "generated_comparisons",
        "weekly_news_focus",
        "ai_comprehensive_analysis",
        "exports",
        "generated_risk_summaries",
        "generated_output_cache_entries",
    ]:
        assert surface in asset_summary["blocked_generated_surfaces"]
    fallback = threshold["live_generation_validation_failure_fallback"]
    assert fallback["generated_claims_allowed_after_failed_validation"] is False
    assert fallback["generated_chat_answers_allowed_after_failed_validation"] is False
    assert fallback["generated_comparisons_allowed_after_failed_validation"] is False
    assert fallback["weekly_news_focus_allowed_after_failed_validation"] is False
    assert fallback["ai_comprehensive_analysis_allowed_after_failed_validation"] is False
    assert fallback["exports_allowed_after_failed_validation"] is False
    assert fallback["generated_output_cache_entries_allowed_after_failed_validation"] is False
    assert fallback["fallback_section_states"] == [
        "partial",
        "stale",
        "unknown",
        "unavailable",
        "insufficient_evidence",
    ]
    gate = result["manual_fresh_data_readiness_gate"]
    assert gate["schema_version"] == "local-manual-fresh-data-readiness-gate-v1"
    assert gate["decision"] == "agent_work_remaining"
    assert gate["task_ready_vs_manual_test_ready_decision"] == "agent_work_remaining"
    assert gate["task_ready_for_manual_testing"] is False
    assert gate["manual_test_ready"] is False
    assert gate["agent_work_remaining"] is True
    assert gate["next_operator_action"] == "finish_deterministic_agent_work_before_manual_fresh_data_testing"
    assert gate["sanitized_operator_report"] is True
    assert gate["review_only"] is True
    assert gate["production_services_started"] is False
    assert gate["live_sources_fetched"] is False
    assert gate["live_llms_called"] is False
    assert gate["sources_approved"] is False
    assert gate["manifests_promoted"] is False
    assert gate["ingestion_started"] is False
    assert gate["generated_output_cache_entries_written"] is False
    assert gate["generated_output_unlocked_for_unsupported_or_incomplete_assets"] is False
    stop_reasons = {condition["reason_code"] for condition in gate["stop_conditions"]}
    assert {
        "etf500_review_fixture_only_not_launch_coverage",
        "etf500_source_pack_incomplete",
        "etf500_handoff_not_ready_or_unclear_rights",
        "etf500_source_pack_batch_uses_fixture_fallback",
        "etf500_issuer_source_pack_batch_incomplete",
        "top500_sec_source_pack_insufficient_evidence",
        "top500_sec_source_handoff_not_ready",
        "top500_sec_parser_not_ready",
        "top500_sec_freshness_or_checksum_not_ready",
        "local_ingestion_priority_plan_has_blocked_or_not_ready_assets",
    } <= stop_reasons
    prerequisite_ids = {item["prerequisite_id"] for item in gate["prerequisite_summaries"]}
    assert {
        "t136_etf500_candidate_review",
        "t137_etf_source_pack_batch_planning",
        "t138_top500_sec_source_pack_batch_planning",
        "local_mvp_thresholds",
        "local_ingestion_priority_planning",
        "governed_golden_rendering",
        "t144_local_fresh_data_mvp_slice_smoke",
        "stock_vs_etf_comparison_readiness",
        "frontend_workflow_smoke_markers",
    } == prerequisite_ids
    assert [mode["status"] for mode in gate["optional_mode_statuses"]] == ["skipped"] * 4
    assert gate["no_secret_diagnostics"] == {
        "secret_values_reported": False,
        "secret_values_requested": False,
        "safe_diagnostics_only": True,
        "opt_in_env_names_reported_without_values": [
            "LTT_REHEARSAL_BROWSER_SERVICES_ENABLED",
            "LTT_REHEARSAL_DURABLE_REPOSITORIES_ENABLED",
            "LTT_REHEARSAL_OFFICIAL_SOURCE_RETRIEVAL_ENABLED",
            "LTT_REHEARSAL_LIVE_AI_REVIEW_ENABLED",
            "LEARN_TICKER_LOCAL_WEB_BASE",
            "LEARN_TICKER_LOCAL_API_BASE",
        ],
    }
    assert "generated_output_cache_entries" in gate["blocked_generated_surfaces"]
    checklist_ids = {item["check_id"] for item in gate["manual_test_checklist"]}
    assert {
        "local_web_api_startup",
        "api_base_proxy_cors",
        "home_single_asset_search",
        "a_vs_b_compare_redirect",
        "source_drawer",
        "citation_chips",
        "freshness_labels",
        "exports",
        "comparison",
        "stock_etf_relationship_badges",
        "contextual_glossary",
        "asset_chat_mobile_behavior",
        "weekly_news_focus_limited_empty_states",
        "ai_comprehensive_analysis_threshold",
        "unsupported_recognition_only_blocking",
        "optional_durable_repositories",
        "optional_official_source_retrieval",
        "optional_live_ai_validation",
    } == checklist_ids


def test_local_fresh_data_rehearsal_optional_modes_report_blockers_without_secrets():
    result = run_rehearsal(
        env={
            "LTT_REHEARSAL_DURABLE_REPOSITORIES_ENABLED": "true",
            "LTT_REHEARSAL_OFFICIAL_SOURCE_RETRIEVAL_ENABLED": "true",
            "LTT_REHEARSAL_LIVE_AI_REVIEW_ENABLED": "true",
        }
    )

    assert result["status"] == "blocked"
    checks = {check["check_id"]: check for check in result["checks"]}
    assert checks["optional_local_durable_repositories"]["status"] == "blocked"
    assert checks["optional_official_source_retrieval"]["status"] == "blocked"
    assert checks["optional_live_ai_review"]["status"] == "blocked"
    threshold = result["local_mvp_threshold_summary"]
    assert threshold["overall_local_approval_status"] == "blocked_for_local_operator_review"
    assert threshold["local_operator_review_ready"] is False
    assert threshold["required_blockers"] == []
    assert [check["check_id"] for check in threshold["optional_blockers"]] == [
        "optional_local_durable_repositories",
        "optional_official_source_retrieval",
        "optional_live_ai_review",
    ]
    assert threshold["threshold_blockers"] == [
        {
            "reason_code": "optional_mode_blocked_after_explicit_opt_in",
            "count": 3,
            "check_ids": [
                "optional_local_durable_repositories",
                "optional_official_source_retrieval",
                "optional_live_ai_review",
            ],
        }
    ]
    gate = result["manual_fresh_data_readiness_gate"]
    assert gate["decision"] == "agent_work_remaining"
    gate_optional_blockers = [
        condition
        for condition in gate["stop_conditions"]
        if condition["reason_code"] == "optional_mode_blocked_after_explicit_opt_in" and "check_id" in condition
    ]
    assert [condition["check_id"] for condition in gate_optional_blockers] == [
        "optional_local_durable_repositories",
        "optional_official_source_retrieval",
        "optional_live_ai_review",
    ]
    assert gate["no_secret_diagnostics"]["secret_values_reported"] is False
    assert gate["no_secret_diagnostics"]["secret_values_requested"] is False
    serialized = str(result)
    for forbidden in ["postgresql://", "Bearer ", "Authorization", "BEGIN PRIVATE KEY", "sk-"]:
        assert forbidden not in serialized


def test_manual_fresh_data_readiness_gate_can_report_manual_test_ready_when_blockers_clear():
    result = run_rehearsal(env={})
    checks = checks_from_result(result)
    check_by_id = {check.check_id: check for check in checks}
    threshold = deepcopy(result["local_mvp_threshold_summary"])

    launch = check_by_id["launch_manifest_review_packets"].details
    launch["etf500_current_fixture_not_launch_coverage"] = False
    launch["etf500_category_coverage_gap_count"] = 0
    launch["etf500_source_pack_readiness"]["ready_count"] = 500
    launch["etf500_source_pack_readiness"]["incomplete_count"] = 0
    launch["etf500_parser_handoff_readiness"]["handoff_ready_count"] = 500
    launch["etf500_parser_handoff_readiness"]["handoff_not_ready_count"] = 0
    launch["etf500_parser_handoff_readiness"]["unclear_rights_count"] = 0
    launch["etf500_parser_handoff_readiness"]["parser_invalid_count"] = 0
    launch["etf_readiness_counts"]["source_pack_ready"] = 500
    launch["etf_readiness_counts"]["pending_review"] = 0
    launch["etf_readiness_counts"]["unavailable"] = 0

    etf_plan = check_by_id["etf_issuer_source_pack_readiness"].details["etf500_source_pack_batch_planning"]
    etf_plan["candidate_artifacts_available"] = True
    etf_plan["fallback_not_launch_coverage"] = False
    etf_plan["planning_summary"]["source_pack_ready_count"] = 500
    etf_plan["planning_summary"]["source_pack_incomplete_count"] = 0

    stock = check_by_id["stock_sec_source_pack_readiness"].details
    stock["readiness_counts"]["insufficient_evidence"] = 0
    stock["readiness_counts"]["pass"] = 500
    stock_plan = stock["top500_sec_source_pack_batch_planning"]
    stock_plan["planning_summary"]["insufficient_evidence_count"] = 0
    stock_plan["source_handoff_readiness"]["pending_or_missing_component_count"] = 0
    stock_plan["source_handoff_readiness"]["pending_review_component_count"] = 0
    stock_plan["source_handoff_readiness"]["rejected_or_unclear_rights_component_count"] = 0
    stock_plan["source_handoff_readiness"]["wrong_asset_component_count"] = 0
    stock_plan["parser_readiness"]["parser_not_ready_component_count"] = 0
    stock_plan["freshness_as_of_checksum_placeholder_status"]["freshness_as_of_checksum_review_required"] = False
    stock_plan["freshness_as_of_checksum_placeholder_status"]["checksum_required_count"] = 3
    stock_plan["freshness_as_of_checksum_placeholder_status"]["checksum_present_count"] = 3

    ingestion = check_by_id["local_ingestion_priority_planner"].details
    ingestion["summary"]["blocked_or_not_ready_count"] = 0

    gate = _build_manual_fresh_data_readiness_gate(checks, threshold)

    assert gate["decision"] == "manual_test_ready"
    assert gate["task_ready_vs_manual_test_ready_decision"] == "manual_test_ready"
    assert gate["task_ready_for_manual_testing"] is True
    assert gate["manual_test_ready"] is True
    assert gate["agent_work_remaining"] is False
    assert gate["next_operator_action"] == "run_manual_local_fresh_data_testing_with_explicit_opt_ins"
    assert gate["stop_conditions"] == []
    assert gate["generated_output_unlocked_for_unsupported_or_incomplete_assets"] is False
    assert "generated_output_cache_entries" in gate["blocked_generated_surfaces"]


def test_t118_local_fresh_data_runbook_covers_deterministic_smoke_without_live_requirements():
    runbook = read_file("docs/local_fresh_data_ingest_to_render_runbook.md")
    runbook_lower = runbook.lower()

    for marker in [
        "Task: T-118",
        "Fetching alone is retrieval, not evidence approval",
        "`in_memory`: deterministic smoke mode",
        "`local_durable`: optional operator-only local repository mode",
        "`operator_live_experiment`: optional local experiment mode",
        "placeholder-only environment",
        "manual pre-cache job",
        "mocked official-source acquisition",
        "parser diagnostics marked `parsed`",
        "Golden Asset Source Handoff marked `approved`",
        "private source snapshot metadata only",
        "normalized knowledge-pack records from deterministic fixtures",
        "Weekly News Focus evidence records from deterministic official-source candidates",
        "generated-output cache records that already passed citation, source-use, freshness, and safety validation",
        "/api/assets/VOO/overview",
        "/api/assets/VOO/weekly-news",
        "/api/assets/VOO/sources",
        "/api/assets/VOO/glossary?term=expense%20ratio",
        "/api/assets/VOO/export?export_format=json",
        "home remains single stock/ETF search first",
        "comparison remains a separate connected `/compare` workflow",
        "glossary appears as contextual help",
        "stock-vs-ETF comparison keeps relationship badges",
        "Weekly News Focus renders only the evidence-backed set",
        "test_t118_local_fresh_data_ingest_to_render_smoke_path_is_deterministic",
        "Task: T-127",
        "scripts/run_live_ai_validation_smoke.py --json",
        "both smoke cases report `skipped`",
        "both smoke cases report `blocked`",
        "T-128 proves deterministic governed golden source snapshots",
        "does not approve sources",
        "does not relax Golden Asset Source Handoff",
        "stock_vs_etf_comparison_readiness",
        "backend comparison pack, API-aligned frontend markers, comparison export, asset-chat compare redirect",
        "does not mean broad stock-vs-ETF coverage",
        "unsupported, out-of-scope, eligible-not-cached, unknown, or missing-pack pairs",
        "Task: T-144",
        "scripts/run_local_fresh_data_slice_smoke.py --json",
        "local fresh-data MVP slice smoke",
        "`pass`, `partial`, `blocked`, and `unavailable`",
        "`AAPL`, `MSFT`, `NVDA`, `VOO`, `SPY`, `VTI`, `QQQ`, and `XLK`",
        "`TQQQ`, `ARKK`, `BND`, and `GLD`",
        "DATA_POLICY_MODE=lightweight LIGHTWEIGHT_LIVE_FETCH_ENABLED=true LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true SEC_EDGAR_USER_AGENT=\"learn-the-ticker-local/0.1 contact@example.com\" TMPDIR=/tmp python3 scripts/run_lightweight_data_fetch_smoke.py --live --ticker AAPL --ticker MSFT --ticker NVDA --ticker VOO --ticker SPY --ticker VTI --ticker QQQ --ticker XLK --json",
    ]:
        assert marker in runbook, f"T-118 runbook should include marker: {marker}"

    for forbidden in [
        "OPENROUTER",
        "FMP_API",
        "ALPHA_VANTAGE",
        "FINNHUB",
        "TIINGO",
        "EODHD",
        "api_key",
        "BEGIN PRIVATE KEY",
        "signed url",
        "public storage url",
        "sk-",
        "xoxb-",
        "ghp_",
        "raw model reasoning is shown",
        "raw transcript",
    ]:
        assert forbidden.lower() not in runbook_lower


def test_sec_stock_acquisition_contract_is_backend_only_fixture_backed_and_sanitized():
    adapter = read_file("backend/provider_adapters/sec_stock.py")
    worker = read_file("backend/ingestion_worker.py")
    combined = f"{adapter}\n{worker}"

    assert "sec-stock-acquisition-boundary-v1" in adapter
    assert "sec-stock-mocked-http-fetch-boundary-v1" in adapter
    assert "sec-stock-parser-adapter-boundary-v1" in adapter
    assert "sec-stock-handoff-gated-execution-boundary-v1" in adapter
    assert "SecStockConfigurationReadiness" in adapter
    assert "build_sec_stock_acquisition_result" in adapter
    assert "execute_sec_stock_handoff_gated_official_source_acquisition" in adapter
    assert "user_agent_configured" in adapter
    assert "rate_limit_ready" in adapter
    assert "live_call_disabled" in adapter
    assert "wrote_source_snapshot: bool = False" in adapter
    assert "wrote_knowledge_pack: bool = False" in adapter
    assert "wrote_generated_output_cache: bool = False" in adapter
    assert "created_generated_asset_page: bool = False" in adapter
    assert "created_generated_chat_answer: bool = False" in adapter
    assert "created_generated_comparison: bool = False" in adapter
    assert "created_generated_risk_summary: bool = False" in adapter

    for forbidden in [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "os.environ",
        "NEXT_PUBLIC",
        "OPENROUTER_API_KEY",
        "Authorization",
        "Bearer ",
    ]:
        assert forbidden not in combined


def test_etf_issuer_acquisition_contract_is_backend_only_fixture_backed_and_sanitized():
    adapter = read_file("backend/provider_adapters/etf_issuer.py")
    worker = read_file("backend/ingestion_worker.py")
    combined = f"{adapter}\n{worker}"

    assert "etf-issuer-acquisition-boundary-v1" in adapter
    assert "etf-issuer-mocked-http-fetch-boundary-v1" in adapter
    assert "etf-issuer-parser-adapter-boundary-v1" in adapter
    assert "etf-issuer-handoff-gated-execution-boundary-v1" in adapter
    assert "EtfIssuerConfigurationReadiness" in adapter
    assert "build_etf_issuer_acquisition_result" in adapter
    assert "execute_etf_issuer_handoff_gated_official_source_acquisition" in adapter
    assert "issuer_source_configured" in adapter
    assert "rate_limit_ready" in adapter
    assert "live_call_disabled" in adapter
    assert "wrote_source_snapshot: bool = False" in adapter
    assert "wrote_knowledge_pack: bool = False" in adapter
    assert "wrote_generated_output_cache: bool = False" in adapter
    assert "created_generated_asset_page: bool = False" in adapter
    assert "created_generated_chat_answer: bool = False" in adapter
    assert "created_generated_comparison: bool = False" in adapter
    assert "created_generated_risk_summary: bool = False" in adapter

    for forbidden in [
        "import requests",
        "import httpx",
        "urllib.request",
        "from socket import",
        "os.environ",
        "NEXT_PUBLIC",
        "OPENROUTER_API_KEY",
        "Authorization",
        "Bearer ",
    ]:
        assert forbidden not in combined
