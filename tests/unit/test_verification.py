"""Behavioral checks for fail-closed verification and read-only generators."""
import subprocess
import sys
import os
from pathlib import Path

import pytest

from scripts import verify
from scripts.check_docs import check_file

ROOT = Path(__file__).resolve().parents[2]


def test_failed_command_stops_later_checks_and_preserves_exit_code(monkeypatch):
    calls = []
    monkeypatch.setattr(verify, "executable", lambda name: name)
    def fail(command):
        calls.append(command)
        raise subprocess.CalledProcessError(7, command)
    monkeypatch.setattr(verify, "run", fail)
    assert verify.main(["milestone"]) == 7
    assert len(calls) == 1


def test_missing_postgres_blocks_before_any_commands(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LTT_PG_BIN", str(tmp_path))
    monkeypatch.setattr(verify, "executable", lambda name: name)
    monkeypatch.setattr(verify, "run", lambda _: pytest.fail("Prerequisite failure must stop commands"))
    assert verify.main(["database"]) == 2
    assert "LTT_PG_BIN" in capsys.readouterr().err


def test_markdown_links_detect_missing_paths_and_anchors(tmp_path):
    page = tmp_path / "page.md"
    target = tmp_path / "target.md"
    target.write_text("# Repeated\n# Repeated\n", encoding="utf-8")
    page.write_text("[good](target.md#repeated-1) [bad](target.md#absent) [missing](missing.md) [remote](https://example.invalid)\n", encoding="utf-8")
    errors = check_file(page, tmp_path)
    assert len(errors) == 2
    assert any("missing heading" in error for error in errors)
    assert any("missing target" in error for error in errors)


def test_contract_check_does_not_rewrite_outputs():
    paths = [ROOT / "contracts/desktop.schema.json", ROOT / "apps/desktop/src/contracts.ts"]
    before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
    subprocess.run([sys.executable, "-m", "scripts.contracts", "--check"], cwd=ROOT, check=True)
    subprocess.run([verify.executable("node"), "scripts/generate_types.mjs", "--check"], cwd=ROOT, check=True)
    assert [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths] == before


@pytest.mark.parametrize("tier", ["fast", "milestone", "full"])
def test_portable_wrapper_propagates_invalid_command_failure(tier):
    directory = ROOT / ".codex/skills/project-delivery/scripts"
    if os.name == "nt":
        command = [verify.executable("powershell"), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(directory / f"verify-{tier}.ps1")]
    else:
        command = [verify.executable("bash"), str(directory / f"verify-{tier}.sh")]
    result = subprocess.run([*command, "--invalid-test-option"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr
