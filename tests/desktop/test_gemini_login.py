import hashlib
import json
import shutil
import subprocess

import pytest

from scripts import connect_gemini as login


def test_login_guard_without_a_runtime_account_or_network():
    result = subprocess.run(
        [shutil.which("node") or "node", str(login.ROOT / "tests/desktop/gemini_login_scenarios.mjs")],
        capture_output=True, timeout=15, env=login.provider_environment(),
    )
    assert result.returncode == 0, "Synthetic Gemini credential isolation scenario failed"
    assert result.stdout == b"guard_scenarios_passed\n"
    assert result.stderr == b""


def test_login_environment_discards_inherited_auth_billing_and_node_hooks(monkeypatch, tmp_path):
    for name in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT",
                 "NODE_OPTIONS", "GEMINI_FORCE_FILE_STORAGE", "GEMINI_CLI_HOME", "OAUTH_CALLBACK_HOST"]:
        monkeypatch.setenv(name, "synthetic-hostile")
    env = login.login_environment(tmp_path)
    assert "synthetic-hostile" not in env.values()
    assert env["GEMINI_CLI_HOME"] == str(tmp_path)
    assert env["GEMINI_FORCE_ENCRYPTED_FILE_STORAGE"] == "true"
    assert env["OAUTH_CALLBACK_HOST"] == "127.0.0.1"
    assert env["GEMINI_TELEMETRY_ENABLED"] == "false"


def test_reviewed_package_rejects_version_and_code_drift(monkeypatch, tmp_path):
    metadata = tmp_path / "package.json"
    metadata.write_text(json.dumps({"name": "@google/gemini-cli", "version": "0.62.0"}))
    (tmp_path / "bundle").mkdir()
    code = tmp_path / "bundle/chunk-MLY4WQFO.js"
    code.write_bytes(b"synthetic")
    monkeypatch.setattr(login, "HASHES", {code.name: hashlib.sha256(b"synthetic").hexdigest()})
    assert login.reviewed_entry(tmp_path) == code
    code.write_bytes(b"changed")
    with pytest.raises(ValueError, match="implementation"):
        login.reviewed_entry(tmp_path)
    metadata.write_text(json.dumps({"name": "@google/gemini-cli", "version": "0.63.0"}))
    with pytest.raises(ValueError, match="package"):
        login.reviewed_entry(tmp_path)


def test_no_implicit_login():
    with pytest.raises(SystemExit) as exc:
        login.main([])
    assert exc.value.code == 2


@pytest.mark.parametrize("filename", ["oauth_creds.json", "gemini-credentials.json"])
def test_file_credentials_stop_before_importing_provider(tmp_path, filename):
    (tmp_path / ".gemini").mkdir()
    credential = tmp_path / ".gemini" / filename
    credential.write_text("synthetic-not-to-be-read")
    marker = tmp_path / "unexpected-import"
    entry = tmp_path / "fake-provider.mjs"
    entry.write_text(
        "import {writeFileSync} from 'node:fs'; writeFileSync("
        + json.dumps(str(marker)) + ", 'imported');",
        encoding="utf-8",
    )
    result = subprocess.run(
        [shutil.which("node") or "node", str(login.ROOT / "scripts/gemini_login.mjs"), "--login", str(entry)],
        capture_output=True, timeout=15, env=login.login_environment(tmp_path),
    )
    assert result.returncode == 2
    assert result.stdout == b"sign_in_failed\n"
    assert result.stderr == b""
    assert credential.read_text() == "synthetic-not-to-be-read"
    assert not marker.exists()
