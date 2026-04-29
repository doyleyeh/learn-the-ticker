from pathlib import Path

from scripts.run_local_fresh_data_rehearsal import run_rehearsal


ROOT = Path(__file__).resolve().parents[2]


def read_file(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


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
        "T-131 adds ETF eligible-universe review packet contracts",
        "T-132 adds stock SEC source-pack readiness packet contracts",
        "T-133 adds ETF issuer source-pack readiness packet contracts",
        "T-134 adds local fresh-data MVP readiness thresholds",
        "T-135 adds a batchable local ingestion priority planner",
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

    assert "## MVP Backend Roadmap" not in tasks
    if "no current task is prepared" in current_lower:
        assert "no backlog tasks are currently prepared" in backlog_lower
        assert "### T-" not in active_sections
        assert "No current local fully functional fresh-data MVP task is prepared" in roadmap
    else:
        for marker in [
            "### T-",
            "Acceptance criteria",
            "Required commands",
            "Iteration budget",
        ]:
            assert marker in current_task

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
        "T-131 through T-135 completed the ETF eligible-universe, stock SEC source-pack readiness, ETF issuer source-pack readiness, local MVP readiness-threshold packets, and batchable local ingestion priority planner",
        "The ETF-500 scope update is documented across the product and handoff docs; T-136 is currently promoted to turn that scope into deterministic candidate manifest review contracts.",
        "T-134 and T-135 are completed. T-136 is currently promoted as the next local fresh-data MVP task before production-hardening tasks.",
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

    completed_rows = [
        "| Provider source-use/export enforcement hardening | Completed | T-099 |",
        "| Backend fresh-data MVP runtime gap tracker | Completed | T-100 |",
        "| Configured persisted-reader route wiring | Completed | T-101 |",
        "| Executable local ingestion ledger and mocked worker path | Completed | T-102 |",
        "| SEC EDGAR stock golden-path acquisition | Completed | T-103 |",
        "| Official ETF issuer golden-path acquisition | Completed | T-104 |",
        "| Source snapshot and parsed acquisition artifact persistence | Completed | T-105 |",
        "| Normalized knowledge-pack writes from ingestion | Completed | T-106 |",
        "| Weekly News Focus official-source event evidence persistence | Completed | T-107 |",
        "| Generated-output cache writes and invalidation | Completed | T-108 |",
        "| Frontend API-backed search, pending states, and asset rendering | Completed | T-109 |",
        "| Persisted comparison/chat/source/glossary/export end-to-end verification | Completed | T-110 |",
        "| Local durable repository execution with in-memory fallback | Completed | T-111 |",
        "| Opt-in live SEC and ETF issuer golden acquisition | Completed | T-112 |",
        "| Official-source Weekly News live acquisition for golden assets | Completed | T-113 |",
        "| Launch pre-cache expansion and MVP readiness regression matrix | Completed | T-114 |",
        "| Golden Asset Source Handoff contract enforcement | Completed | T-115 |",
        "| Reviewed Top-500 candidate manifest workflow contracts | Completed | T-116 |",
        "| Handoff-gated official-source acquisition execution for golden assets | Completed | T-117 |",
        "| Local fresh-data ingest-to-render runbook and smoke coverage | Completed | T-118 |",
        "| Local frontend API access and backend CORS | Completed | T-119 |",
        "| Split supported ETF and recognition manifests | Completed | T-120 |",
        "| Optional localhost browser/API smoke | Completed | T-121 |",
        "| Optional local durable API proxy smoke | Completed | T-122 |",
        "| Handoff-gated official-source fetcher boundaries | Completed | T-123 |",
        "| Reviewed launch-universe expansion planning | Completed | T-124 |",
        "| v0.6 docs, handoff docs, and backlog alignment | Completed | T-125 |",
        "| Repo-native source-handoff manifest smoke tooling | Completed | T-126 |",
        "| Opt-in local live-AI validation smoke | Completed | T-127 |",
        "| Governed golden evidence API/frontend rendering proof | Completed | T-128 |",
        "| Launch-manifest operator automation parity | Completed | T-129 |",
        "| Local fresh-data MVP rehearsal command | Completed | T-130 |",
        "| ETF eligible-universe review packet contracts | Completed | T-131 |",
        "| Stock SEC source-pack readiness packets | Completed | T-132 |",
        "| ETF issuer source-pack readiness packets | Completed | T-133 |",
        "| Local fresh-data MVP readiness thresholds | Completed | T-134 |",
        "| Batchable local ingestion priority planner | Completed | T-135 |",
        "| ETF-500 candidate manifest review contracts | Current | T-136 |",
        "| Full production deployment, recurring jobs, and broad paid-provider integrations | Later | Unpromoted |",
    ]
    for row in completed_rows:
        assert row in roadmap

    for stale_status in [
        "| Launch-manifest operator automation parity | Current | T-129 |",
        "| Local fresh-data MVP rehearsal command | Prepared | T-130 |",
        "| ETF issuer source-pack readiness packets | Current | T-133 |",
        "| Local fresh-data MVP readiness thresholds | Prepared | T-134 |",
        "| Local fresh-data MVP readiness thresholds | Current | T-134 |",
        "| Batchable local ingestion priority planner | Prepared | T-135 |",
        "| Batchable local ingestion priority planner | Current | T-135 |",
        "The current promoted task is T-129",
        "No current local fully functional fresh-data MVP task is prepared",
    ]:
        assert stale_status not in roadmap


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
    assert len(threshold["required_checks"]) == 8
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
    assert statuses["launch_manifest_review_packets"] == "pass"
    assert statuses["stock_sec_source_pack_readiness"] == "pass"
    assert statuses["local_ingestion_priority_planner"] == "pass"
    assert statuses["frontend_v04_smoke_markers"] == "pass"
    assert statuses["optional_browser_services"] == "skipped"
    assert statuses["optional_local_durable_repositories"] == "skipped"
    assert statuses["optional_official_source_retrieval"] == "skipped"
    assert statuses["optional_live_ai_review"] == "skipped"
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
    assert "generated_chat_answers" in stock_sec_details["blocked_generated_surfaces"]
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
    serialized = str(result)
    for forbidden in ["postgresql://", "Bearer ", "Authorization", "BEGIN PRIVATE KEY", "sk-"]:
        assert forbidden not in serialized


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
