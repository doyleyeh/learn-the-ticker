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


def test_agent_loop_uses_retry_budget_and_clean_commit_policy():
    bash_loop = read_file("scripts/agent_loop.sh")
    powershell_loop = read_file("scripts/agent_loop.ps1")

    assert "ITERATION_BUDGET" in bash_loop
    assert "for ATTEMPT in" in bash_loop
    assert "--commit-failures" in bash_loop
    assert "Leaving changes uncommitted and unstaged for review." in bash_loop
    assert "ensure_agent_branch" in bash_loop
    assert "agent_loop blocks 'git" in bash_loop
    assert 'PATH="$ROOT/$AGENT_GIT_WRAPPER_DIR:$PATH" codex' in bash_loop

    assert "$IterationBudget" in powershell_loop
    assert "for ($Attempt = 1" in powershell_loop
    assert "CommitFailures" in powershell_loop
    assert "Leaving changes uncommitted and unstaged for review." in powershell_loop
