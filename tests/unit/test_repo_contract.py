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


def test_backend_mvp_runtime_gap_audit_tracks_required_areas_without_runtime_wiring():
    audit = read_file("docs/backend_mvp_runtime_gap_audit.md")
    audit_lower = audit.lower()

    assert "Task: T-100" in audit
    for status in ["contract_complete", "runtime_gap", "current", "backlog", "later"]:
        assert f"`{status}`" in audit, f"audit should define status {status}"

    required_areas = [
        "Source acquisition",
        "Source snapshot storage",
        "Normalized knowledge-pack persistence",
        "Configured route read-path wiring",
        "Generated-output cache writes",
        "Weekly News Focus acquisition",
        "Ingestion job execution",
        "Frontend API rendering",
        "Launch-universe pre-cache",
        "Exports and source-use enforcement",
        "Live-generation readiness",
        "Trust metrics",
        "Production hardening",
    ]
    for area in required_areas:
        assert area in audit, f"audit should cover {area}"

    required_gap_markers = [
        "public routes still default to fixtures where configured readers are absent",
        "ingestion jobs do not fetch real official sources",
        "persistence is not the normal read/write path",
        "provider adapters are fixture-backed",
        "generated-output cache writes are not activated for public output",
        "frontend asset/search pages still have local-fixture-first behavior",
    ]
    for marker in required_gap_markers:
        assert marker in audit, f"audit should explicitly record gap: {marker}"

    for task_marker in [
        "T-101 route read-path wiring",
        "T-102 executable ingestion jobs",
        "T-103 SEC golden-path acquisition",
        "T-104 ETF issuer golden-path acquisition",
    ]:
        assert task_marker in audit, f"audit should map next task {task_marker}"

    for workflow_marker in [
        "home page single-asset stock or ETF search first",
        "comparison as a separate connected workflow",
        "glossary as contextual help",
        "mobile source, glossary, and chat surfaces",
        "stock-vs-ETF comparison relationship badges",
        "Weekly News Focus showing only the evidence-backed set",
    ]:
        assert workflow_marker in audit, f"audit should preserve v0.4 marker {workflow_marker}"

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
        assert forbidden.lower() not in audit_lower


def test_tasks_general_mvp_roadmap_marks_t110_current_and_next_backlog():
    tasks = read_file("TASKS.md")
    current_task = tasks.split("## Current task", 1)[1].split("## Completed", 1)[0]
    backlog = tasks.split("## Backlog", 1)[1].split("## General MVP Roadmap", 1)[0]
    roadmap = tasks.split("## General MVP Roadmap", 1)[1]

    assert "## MVP Backend Roadmap" not in tasks
    assert "No backlog tasks are currently prepared" not in backlog
    assert "General MVP alignment:" in current_task
    assert "T-110 verifies deterministic persisted golden-path rendering and export behavior" in current_task
    assert "Roadmap contract refinement:" in current_task
    assert "Stop after deterministic persisted end-to-end verification" in current_task

    for task_marker in [
        "### T-111: Wire local durable repository execution with in-memory fallback",
        "### T-112: Add explicit opt-in live SEC and ETF issuer golden acquisition",
        "### T-113: Add official-source Weekly News live acquisition for golden assets",
        "### T-114: Expand launch pre-cache coverage and add MVP readiness regression matrix",
    ]:
        assert task_marker in backlog, f"Backlog should include {task_marker}"

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
    assert "T-110 is the current promoted task for persisted end-to-end comparison, chat, source, glossary, and export verification" in roadmap
    assert "T-111 through T-114 are the next runnable tasks" in roadmap
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
    assert "| Persisted comparison/chat/source/glossary/export end-to-end verification | Current | T-110 |" in roadmap
    assert "| Local durable repository execution with in-memory fallback | Backlog | T-111 |" in roadmap
    assert "| Opt-in live SEC and ETF issuer golden acquisition | Backlog | T-112 |" in roadmap
    assert "| Official-source Weekly News live acquisition for golden assets | Backlog | T-113 |" in roadmap
    assert "| Launch pre-cache expansion and MVP readiness regression matrix | Backlog | T-114 |" in roadmap
    assert "| Full production deployment, recurring jobs, and broad paid-provider integrations | Later | Unpromoted |" in roadmap


def test_sec_stock_acquisition_contract_is_backend_only_fixture_backed_and_sanitized():
    adapter = read_file("backend/provider_adapters/sec_stock.py")
    worker = read_file("backend/ingestion_worker.py")
    combined = f"{adapter}\n{worker}"

    assert "sec-stock-acquisition-boundary-v1" in adapter
    assert "SecStockConfigurationReadiness" in adapter
    assert "build_sec_stock_acquisition_result" in adapter
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
    assert "EtfIssuerConfigurationReadiness" in adapter
    assert "build_etf_issuer_acquisition_result" in adapter
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
