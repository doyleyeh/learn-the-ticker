from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_file(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


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
    tasks = read_file("TASKS.md").lower()

    assert "current task" in tasks
    if "no current task is prepared" in tasks:
        assert "## backlog" in tasks
        backlog = tasks.split("## backlog", 1)[1]
        assert "### t-" not in backlog
        return

    assert "acceptance criteria" in tasks
    assert "required commands" in tasks
    assert "iteration budget" in tasks


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
        "Repo-native source-handoff tooling is incomplete",
        "Governed golden evidence does not yet prove full render authority",
        "Local live-AI validation is not yet exercised",
        "T-126: add repo-native source-handoff manifest inspection/finalization smoke tooling",
        "T-127: add opt-in local live-AI validation smoke",
        "T-128: prove governed golden evidence drives backend API and frontend rendering",
        "T-129: add launch-manifest operator automation parity",
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
        "scripts/generate_top500_candidate_manifest.py",
        "backend/etf_universe.py",
        "TMPDIR=/tmp bash scripts/run_quality_gate.sh",
        "T-126 should add repo-native manifest inspection/finalization smoke tooling",
        "EQUITY_ETF_UNIVERSE_MANIFEST_URI",
        "The current repo does not yet include that workflow",
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
        "`MSFT`, `NVDA`, `SPY`, `VTI`, `IVV`, `IWM`, `DIA`, `VGT`, `XLK`, `SOXX`, `SMH`, `XLF`, and `XLV`",
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


def test_tasks_general_mvp_roadmap_marks_t126_current_and_backlog_state():
    tasks = read_file("TASKS.md")
    current_task = tasks.split("## Current task", 1)[1].split("## Completed", 1)[0]
    backlog = tasks.split("## Backlog", 1)[1].split("## Completed", 1)[0]
    completed = tasks.split("## Completed", 1)[1].split("## Historical Backlog Note", 1)[0]
    roadmap = tasks.split("## General MVP Roadmap", 1)[1]

    assert "## MVP Backend Roadmap" not in tasks
    assert "### T-126: Add repo-native source-handoff manifest smoke tooling" in current_task
    assert "source-handoff manifest inspection/finalization smoke tooling" in current_task
    assert "One agent-loop cycle" in current_task
    for marker in [
        "### T-127: Add opt-in local live-AI validation smoke",
        "### T-128: Prove governed golden evidence drives API and frontend rendering",
        "### T-129: Add launch-manifest operator automation parity",
    ]:
        assert marker in backlog
    assert "Detailed acceptance criteria" in current_task
    assert "Required commands" in current_task
    assert "Iteration budget" in current_task
    assert "### T-119: Wire local frontend API access and backend CORS" in completed
    assert "Next.js rewrite" in completed
    assert "build_cors_settings" in completed
    assert "### T-125: Align v0.6 handoff docs and MVP backlog" in completed
    assert "Completed in commit `70d404e docs(T-125): align v0.6 handoff docs and MVP backlog`" in completed
    assert "### T-124: Prepare reviewed launch-universe expansion plan" in completed
    assert "### T-120: Implement v0.5 ETF manifest split contracts" in completed
    assert "### T-118: Prove local fresh-data ingest-to-render smoke path" in completed
    assert "The runbook explicitly states that fetching alone is retrieval, not evidence approval" in completed
    assert "deterministic integration smoke coverage for the VOO golden path" in completed
    assert "mocked official-source acquisition" in completed
    assert "Golden Asset Source Handoff" in completed
    assert "Production deployment, production durable storage, scheduled jobs" in completed
    assert "T-119 closed the local frontend/API plumbing blockers" in roadmap
    assert "T-125 completed the v0.6 handoff-doc and MVP-backlog alignment pass" in roadmap
    assert "The current promoted task is T-126" in roadmap

    assert "T-099 established deterministic provider content export-rights hardening" in roadmap
    assert "T-100 established the backend MVP runtime gap audit and roadmap tracker" in roadmap
    assert "T-101 established configured persisted-reader route wiring with fixture fallback" in roadmap
    assert "T-102 established executable local ingestion ledger and mocked worker transitions" in roadmap
    assert "T-103 established mocked SEC EDGAR stock golden-path acquisition" in roadmap
    assert "T-104 established mocked official ETF issuer golden-path acquisition" in roadmap
    assert "T-106 established deterministic normalized knowledge-pack writes from acquisition outputs" in roadmap
    assert "T-107 established deterministic persisted Weekly News Focus event evidence for golden assets" in roadmap
    assert "T-108 established deterministic generated-output cache writes and freshness invalidation" in roadmap
    assert "T-109 established frontend API-backed search, pending states, and dynamic asset-page rendering" in roadmap
    assert "T-110 established persisted end-to-end comparison, chat, source, glossary, Weekly News, and export verification" in roadmap
    assert "T-111 established local durable repository execution with in-memory fallback" in roadmap
    assert "T-115 established Golden Asset Source Handoff contract enforcement" in roadmap
    assert "T-116 established reviewed Top-500 candidate manifest workflow contracts" in roadmap
    assert "T-117 established handoff-gated mocked official-source acquisition execution for golden assets" in roadmap
    assert "T-118 documented and regression-covered the deterministic local fresh-data ingest-to-render smoke path" in roadmap
    assert "T-118 established the local fresh-data ingest-to-render runbook and deterministic smoke coverage" in roadmap
    assert "T-119 established local frontend API access and backend CORS" in roadmap
    assert "T-120 established the v0.5 split between supported ETF generated-output coverage" in roadmap
    assert "T-124 established reviewed launch-universe expansion planning" in roadmap
    assert "T-125 established v0.6 docs, handoff docs, and backlog alignment" in roadmap
    assert "T-127 through T-129" in roadmap
    assert "| Provider source-use/export enforcement hardening | Completed | T-099 |" in roadmap
    assert "| Backend fresh-data MVP runtime gap tracker | Completed | T-100 |" in roadmap
    assert "| Configured persisted-reader route wiring | Completed | T-101 |" in roadmap
    assert "| Executable local ingestion ledger and mocked worker path | Completed | T-102 |" in roadmap
    assert "| SEC EDGAR stock golden-path acquisition | Completed | T-103 |" in roadmap
    assert "| Official ETF issuer golden-path acquisition | Completed | T-104 |" in roadmap
    assert "| Source snapshot and parsed acquisition artifact persistence | Completed | T-105 |" in roadmap
    assert "| Normalized knowledge-pack writes from ingestion | Completed | T-106 |" in roadmap
    assert "| Weekly News Focus official-source event evidence persistence | Completed | T-107 |" in roadmap
    assert "| Generated-output cache writes and invalidation | Completed | T-108 |" in roadmap
    assert "| Frontend API-backed search, pending states, and asset rendering | Completed | T-109 |" in roadmap
    assert "| Persisted comparison/chat/source/glossary/export end-to-end verification | Completed | T-110 |" in roadmap
    assert "| Local durable repository execution with in-memory fallback | Completed | T-111 |" in roadmap
    assert "| Opt-in live SEC and ETF issuer golden acquisition | Completed | T-112 |" in roadmap
    assert "| Official-source Weekly News live acquisition for golden assets | Completed | T-113 |" in roadmap
    assert "| Launch pre-cache expansion and MVP readiness regression matrix | Completed | T-114 |" in roadmap
    assert "| Golden Asset Source Handoff contract enforcement | Completed | T-115 |" in roadmap
    assert "| Reviewed Top-500 candidate manifest workflow contracts | Completed | T-116 |" in roadmap
    assert "| Handoff-gated official-source acquisition execution for golden assets | Completed | T-117 |" in roadmap
    assert "| Local fresh-data ingest-to-render runbook and smoke coverage | Completed | T-118 |" in roadmap
    assert "| Local frontend API access and backend CORS | Completed | T-119 |" in roadmap
    assert "| Split supported ETF and recognition manifests | Completed | T-120 |" in roadmap
    assert "| Optional localhost browser/API smoke | Completed | T-121 |" in roadmap
    assert "| Optional local durable API proxy smoke | Completed | T-122 |" in roadmap
    assert "| Handoff-gated official-source fetcher boundaries | Completed | T-123 |" in roadmap
    assert "| Reviewed launch-universe expansion planning | Completed | T-124 |" in roadmap
    assert "| v0.6 docs, handoff docs, and backlog alignment | Completed | T-125 |" in roadmap
    assert "| Repo-native source-handoff manifest smoke tooling | Current | T-126 |" in roadmap
    assert "| Opt-in local live-AI validation smoke | Prepared | T-127 |" in roadmap
    assert "| Governed golden evidence API/frontend rendering proof | Prepared | T-128 |" in roadmap
    assert "| Launch-manifest operator automation parity | Prepared | T-129 |" in roadmap
    assert "| Full production deployment, recurring jobs, and broad paid-provider integrations | Later | Unpromoted |" in roadmap


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
