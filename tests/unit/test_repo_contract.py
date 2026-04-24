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
