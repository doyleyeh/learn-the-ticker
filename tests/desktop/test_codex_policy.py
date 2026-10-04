import asyncio
import os
from types import SimpleNamespace

import pytest

from backend.app.codex_policy import (
    DISABLED_FEATURES, ROOT_MARKER, policy_config, prepare_workspace,
    validate_config, validate_features, validate_thread,
)
from backend.app.codex_rpc import CodexRPC
from backend.app.runtime_base import RuntimeFailure


def config_response(browsing=False):
    result = {}
    for key, value in policy_config(browsing).items():
        target = result
        parts = key.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
    return {"config": result, "layers": [{"name": {"type": "sessionFlags"}, "config": result},
                                           {"name": {"type": "user"}, "config": {}}]}


def features_response():
    return {"data": [{"name": name, "enabled": False} for name in DISABLED_FEATURES], "nextCursor": None}


def thread_response(workspace):
    return {"thread": {"id": "synthetic-thread"}, "model": "synthetic-model", "sandbox": {"type": "readOnly", "networkAccess": False},
            "approvalPolicy": "on-request", "approvalsReviewer": "user", "modelProvider": "openai",
            "instructionSources": [], "cwd": str(workspace.resolve()), "runtimeWorkspaceRoots": [str(workspace.resolve())]}


@pytest.mark.parametrize("key,value", [
    ("features.shell_tool", True), ("features.hooks", True), ("features.apps", True),
    ("features.browser_use", True), ("features.code_mode", True),
    ("features.code_mode.enabled", True),
    ("features.code_mode.direct_only_tool_namespaces", ["functions"]),
    ("features.code_mode_host.enabled", True),
    ("features.code_mode_host.disable_in_process_fallback", True),
    ("cli_auth_credentials_store", "auto"), ("forced_login_method", "api"),
    ("sandbox_mode", "danger-full-access"), ("approvals_reviewer", "auto_review"),
    ("analytics.enabled", True), ("otel.exporter", "statsig"), ("project_doc_max_bytes", False),
    ("web_search", "live"), ("model_providers", {"openai": {"base_url": "https://untrusted.example"}}),
    ("mcp_servers", {"untrusted": {"command": "private-command"}}),
])
def test_effective_policy_drift_is_rejected_without_sensitive_values(key, value):
    response = config_response()
    target = response["config"]
    parts = key.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value
    with pytest.raises(RuntimeFailure) as exc:
        validate_config(response, False)
    assert "private-command" not in str(exc.value) and "untrusted.example" not in str(exc.value)


@pytest.mark.skipif(os.name != "nt", reason="native Windows sandbox policy")
@pytest.mark.parametrize("mode", [None, "unelevated", "mxc"])
def test_windows_mode_cannot_fall_back(mode):
    response = config_response()
    response["config"]["windows"]["sandbox"] = mode
    with pytest.raises(RuntimeFailure): validate_config(response, False)


@pytest.mark.skipif(os.name != "nt", reason="provider Windows setup configuration")
@pytest.mark.parametrize("variant", ["exact", "extra", "wrong_mode", "malformed", "oversized"])
def test_provider_setup_config_allows_only_exact_elevated_setting(tmp_path, monkeypatch, variant):
    monkeypatch.setattr("backend.app.codex_policy.system_config_directory", lambda: tmp_path / "system")
    profile = tmp_path / "profile"; profile.mkdir()
    payload = '[windows]\nsandbox="elevated"\n'
    if variant == "extra": payload += '[hooks]\ncommand="never-run"\n'
    if variant == "wrong_mode": payload = payload.replace("elevated", "unelevated")
    if variant == "malformed": payload += '['
    if variant == "oversized": payload += '#' + 'x' * 4096
    config = profile / "config.toml"; config.write_text(payload, encoding="utf-8")
    if variant == "exact": prepare_workspace(profile, tmp_path / "workspace")
    else:
        with pytest.raises(RuntimeFailure): prepare_workspace(profile, tmp_path / "workspace")
    assert config.read_text(encoding="utf-8") == payload


@pytest.mark.skipif(os.name != "nt", reason="provider Windows setup configuration")
@pytest.mark.parametrize("variant", ["exact", "foreign_path", "system", "extra"])
def test_setup_config_layer_is_bound_to_profile_and_minimal_setting(tmp_path, variant):
    response = config_response()
    layer = {"name": {"type": "user", "file": str(tmp_path / "config.toml")}, "config": {"windows": {"sandbox": "elevated"}}}
    if variant == "foreign_path": layer["name"]["file"] = str(tmp_path / "other" / "config.toml")
    if variant == "system": layer["name"]["type"] = "system"
    if variant == "extra": layer["config"]["notify"] = ["never-run"]
    response["layers"].append(layer)
    if variant == "exact": validate_config(response, False, tmp_path)
    else:
        with pytest.raises(RuntimeFailure): validate_config(response, False, tmp_path)


@pytest.mark.parametrize("layer", ["project", "user", "system", "unknown"])
def test_custom_layers_are_rejected_even_if_effective_flags_look_safe(layer):
    response = config_response()
    response["layers"].append({"name": {"type": layer}, "config": {"developer_instructions": "untrusted instructions"}})
    with pytest.raises(RuntimeFailure, match="inherited configuration"):
        validate_config(response, False)


@pytest.mark.parametrize("mode", ["enabled", "missing", "duplicate", "truncated", "malformed"])
def test_missing_or_ambiguous_feature_evidence_fails_closed(mode):
    response = features_response()
    if mode == "enabled": response["data"][0]["enabled"] = True
    if mode == "missing": response["data"].pop(0)
    if mode == "duplicate": response["data"].append(response["data"][0])
    if mode == "truncated": response["nextCursor"] = "another-page"
    if mode == "malformed": response["data"][0]["enabled"] = "false"
    with pytest.raises(RuntimeFailure): validate_features(response)


@pytest.mark.parametrize("key,value", [
    ("sandbox", {"type": "readOnly", "networkAccess": True}),
    ("sandbox", {"type": "workspaceWrite", "networkAccess": False}),
    ("approvalsReviewer", "auto_review"), ("modelProvider", "other"),
    ("instructionSources", ["private-instruction.md"]), ("cwd", "/other-workspace"),
    ("runtimeWorkspaceRoots", []), ("runtimeWorkspaceRoots", ["/other-workspace"]),
    ("cwd", "private\x00path"), ("runtimeWorkspaceRoots", ["private\x00path"]),
])
def test_thread_permissions_must_match_before_turn_start(tmp_path, key, value):
    response = thread_response(tmp_path)
    response[key] = value
    with pytest.raises(RuntimeFailure): validate_thread(response, tmp_path)


@pytest.mark.parametrize("location", ["profile", "workspace", "system"])
def test_custom_configuration_is_preserved_and_blocks_process_launch(tmp_path, monkeypatch, location):
    profile, workspace, system = (tmp_path / name for name in ("profile", "workspace", "system"))
    monkeypatch.setattr("backend.app.codex_policy.system_config_directory", lambda: system)
    target = {"profile": profile, "workspace": workspace, "system": system}[location]
    target.mkdir()
    config = target / "config.toml"
    payload = '[hooks]\ncommand="do not execute"\n'
    config.write_text(payload)
    async def forbidden(*args, **kwargs): pytest.fail("spawned with inherited config")
    monkeypatch.setattr("backend.app.codex_rpc.launch_owned", forbidden)
    with pytest.raises(RuntimeFailure, match="Custom Codex"):
        asyncio.run(CodexRPC(profile, workspace).open())
    assert config.read_text() == payload


def test_workspace_boundary_does_not_overwrite_existing_data(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.codex_policy.system_config_directory", lambda: tmp_path / "system")
    profile, workspace = tmp_path / "profile", tmp_path / "workspace"
    prepare_workspace(profile, workspace)
    marker = workspace / ROOT_MARKER
    assert marker.read_bytes() == b""
    marker.write_text("user data")
    with pytest.raises(RuntimeFailure): prepare_workspace(profile, workspace)
    assert marker.read_text() == "user data"


def test_file_auth_is_not_imported_or_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.codex_policy.system_config_directory", lambda: tmp_path / "system")
    profile = tmp_path / "profile"
    profile.mkdir()
    auth = profile / "auth.json"
    auth.write_text("synthetic credential")
    with pytest.raises(RuntimeFailure): prepare_workspace(profile, tmp_path / "workspace")
    assert auth.read_text() == "synthetic credential"


def test_rpc_rechecks_thread_policy_and_never_starts_inference(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.codex_policy.system_config_directory", lambda: tmp_path / "system")
    async def run():
        rpc = CodexRPC(tmp_path / "profile", tmp_path / "workspace")
        calls = []
        async def request(method, params):
            calls.append((method, params))
            if method == "config/read": return config_response()
            if method == "experimentalFeature/list": return features_response()
            if method == "thread/start": return thread_response(rpc.workspace)
            pytest.fail("unexpected method")
        rpc.request = request
        assert await rpc.start_thread("synthetic-model") == "synthetic-thread"
        assert [m for m, _ in calls] == ["config/read", "experimentalFeature/list", "thread/start", "experimentalFeature/list"]
        assert calls[2][1]["sandbox"] == "read-only" and calls[2][1]["model"] == "synthetic-model"
        assert calls[3][1]["threadId"] == "synthetic-thread"
        assert all(m != "turn/start" for m, _ in calls)
    asyncio.run(run())


def test_startup_mismatch_closes_owned_process(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.codex_policy.system_config_directory", lambda: tmp_path / "system")
    async def run():
        process = SimpleNamespace(returncode=None, stdin=SimpleNamespace(close=lambda: None), closed=False)
        async def wait(): process.returncode = 0; process.closed = True
        process.wait = wait
        async def spawn(*args, **kwargs): return process
        async def request(*args, **kwargs): return {}
        async def send(*args, **kwargs): pass
        monkeypatch.setattr("backend.app.codex_rpc.executable_command", lambda _: ["synthetic-codex"])
        monkeypatch.setattr("backend.app.codex_rpc.launch_owned", spawn)
        rpc = CodexRPC(tmp_path / "profile", tmp_path / "workspace")
        rpc.request, rpc.send = request, send
        with pytest.raises(RuntimeFailure, match="effective configuration"): await rpc.open()
        assert rpc.process is None and process.closed
    asyncio.run(run())
