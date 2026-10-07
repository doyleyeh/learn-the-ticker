import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app import codex_catalog
from backend.app.codex_catalog import MODEL_KEYS, RESTRICTIONS, RestrictedCatalog, restricted_metadata
from backend.app.codex_policy import policy_arguments, policy_config, validate_config, validate_features
from backend.app.codex_rpc import CodexRPC
from backend.app.runtime_base import RuntimeFailure
from tests.desktop.test_codex_policy import config_response, features_response


def metadata():
    return {**dict.fromkeys(MODEL_KEYS), "slug": "synthetic-model", "display_name": "Synthetic model",
            "tool_mode": "code_mode_only", "shell_type": "unified_exec", "apply_patch_tool_type": "freeform",
            "multi_agent_version": "v2", "node_repl_disabled": False, "supports_search_tool": True,
            "use_responses_lite": True, "web_search_tool_type": "text_and_image",
            "experimental_supported_tools": ["clock", "send_user_message_async"],
            "base_instructions": "synthetic instructions", "context_window": 32000}


def payload():
    return restricted_metadata(json.dumps({"models": [metadata()]}).encode(), "synthetic-model")


def test_narrowing_preserves_selected_identity_and_all_non_tool_metadata():
    model = json.loads(payload())["models"][0]
    assert {key: model[key] for key in RESTRICTIONS} == RESTRICTIONS
    assert {key: value for key, value in model.items() if key not in RESTRICTIONS} == {
        key: value for key, value in metadata().items() if key not in RESTRICTIONS}


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra_field", "missing_field", "duplicate_field",
                                    "too_many", "oversized", "malformed", "nan", "lite", "shell", "tool", "clock"])
def test_incompatible_or_ambiguous_metadata_never_creates_a_catalog(change):
    model = metadata()
    rows = [model]
    if change == "missing": model["slug"] = "other"
    if change == "duplicate": rows.append(model)
    if change == "extra_field": model["new_tool_permission"] = True
    if change == "missing_field": model.pop("tool_mode")
    if change == "too_many": rows = [{**model, "slug": str(i)} for i in range(201)]
    if change == "nan": model["context_window"] = float("nan")
    if change == "lite": model["use_responses_lite"] = False
    if change == "shell": model["shell_type"] = "new-shell"
    if change == "tool": model["tool_mode"] = "new-mode"
    if change == "clock": model["experimental_supported_tools"] = "clock"
    raw = json.dumps({"models": rows}).encode()
    if change == "duplicate_field": raw = raw.replace(b'"slug":', b'"slug":"other","slug":')
    if change == "oversized": raw = b" " * 2_000_001
    if change == "malformed": raw = b"private-provider-diagnostic"
    with pytest.raises(RuntimeFailure) as exc:
        restricted_metadata(raw, "synthetic-model")
    assert "private-provider" not in str(exc.value)


@pytest.mark.parametrize("change", ["content", "missing", "replacement", "directory"])
def test_catalog_integrity_and_cleanup_preserve_replacement_files(tmp_path, monkeypatch, change):
    monkeypatch.setattr(codex_catalog.tempfile, "gettempdir", lambda: str(tmp_path))
    catalog = RestrictedCatalog(payload(), "synthetic-model")
    path = catalog.path
    assert path.is_relative_to(tmp_path)
    catalog.verify()
    if change == "content": path.write_text("private mutated metadata")
    if change in ("missing", "replacement", "directory"):
        path.rename(tmp_path / "original")  # retain inode so replacement cannot reuse it
    if change == "replacement": path.write_text("user replacement")
    if change == "directory": path.mkdir()
    with pytest.raises(RuntimeFailure): catalog.verify()
    if change in ("replacement", "directory"):
        with pytest.raises(RuntimeFailure): catalog.close()
        assert path.exists()
        if change == "replacement": assert path.read_text() == "user replacement"
    else:
        catalog.close()
        catalog.close()
        assert not path.exists()


@pytest.mark.parametrize("mode", ["success", "error", "oversized", "cancel"])
def test_metadata_reader_is_bounded_isolated_and_closes_owned_process(tmp_path, monkeypatch, mode):
    async def run():
        reader = asyncio.StreamReader()
        if mode != "cancel":
            reader.feed_data(b"x" * 2_000_001 if mode == "oversized" else json.dumps({"models": [metadata()]}).encode())
            reader.feed_eof()
        process = SimpleNamespace(stdout=reader, returncode=1 if mode == "error" else 0)
        async def wait(): pass
        process.wait = wait
        calls, closed = [], []
        async def launch(*args, **kwargs): calls.append((args, kwargs)); return process
        async def close(child, **kwargs): closed.append(child)
        monkeypatch.setattr(codex_catalog, "launch_owned", launch)
        monkeypatch.setattr(codex_catalog, "close_owned", close)
        monkeypatch.setattr(codex_catalog, "executable_command", lambda _: ["synthetic-codex"])
        monkeypatch.setattr("backend.app.codex_policy.system_config_directory", lambda: tmp_path / "system")
        monkeypatch.setenv("OPENAI_API_KEY", "must-not-inherit")
        monkeypatch.setenv("DATABASE_URL", "must-not-inherit")
        task = asyncio.create_task(codex_catalog.read_metadata(tmp_path / "profile", tmp_path / "workspace", "synthetic-model"))
        if mode == "cancel":
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError): await task
        elif mode == "success": assert await task == payload()
        else:
            with pytest.raises(RuntimeFailure): await task
        assert closed == [process]
        args, kwargs = calls[0]
        assert args[-2:] == ("debug", "models") and "turn/start" not in args
        assert "--strict-config" not in args  # unsupported only on diagnostic
        assert kwargs["env"]["CODEX_HOME"] == str((tmp_path / "profile").resolve())
        assert "OPENAI_API_KEY" not in kwargs["env"] and "DATABASE_URL" not in kwargs["env"]
        assert kwargs["stderr"] == asyncio.subprocess.DEVNULL
    asyncio.run(run())


def restricted_response(browsing, path):
    response = config_response(browsing)
    response["config"]["model_catalog_json"] = str(path)
    response["config"]["features"]["request_permissions_tool"] = browsing
    # Actual normalized Config omits tools; strict sessionFlags preserves them.
    response["config"] = {key: value for key, value in response["config"].items() if key != "tools"}
    response["config"]["tools"] = {"web_search": None}
    response["config"]["agents"] = {**response["config"]["agents"], "max_depth": 1}
    return response


@pytest.mark.parametrize("browsing", [False, True])
def test_request_only_exposure_requires_a_restricted_catalog_and_research_policy(tmp_path, browsing):
    path = tmp_path / "models.json"
    assert policy_config(browsing)["features.request_permissions_tool"] is False
    flags = policy_config(browsing, path)
    assert flags["features.request_permissions_tool"] is browsing
    assert flags["agents.enabled"] is False and flags["features.current_time_reminder"] is False
    args = policy_arguments(browsing, path)
    assert args[0] == "--strict-config"
    validate_config(restricted_response(browsing, path), browsing, tmp_path, path)
    response = features_response()
    for row in response["data"]:
        if row["name"] == "request_permissions_tool": row["enabled"] = browsing
    validate_features(response, request_permissions=browsing)
    if browsing:
        with pytest.raises(RuntimeFailure): validate_features(response)


@pytest.mark.parametrize("change", ["catalog", "tools_missing", "tools_extra", "tools_enabled", "tools_number", "agents", "duplicate_layer", "effective_tool"])
def test_restricted_policy_drift_stops_before_inference(tmp_path, change):
    path = tmp_path / "models.json"
    response = restricted_response(True, path)
    flags = response["layers"][0]["config"]
    if change == "catalog": response["config"]["model_catalog_json"] = "foreign"
    if change == "tools_missing": flags.pop("tools")
    if change == "tools_extra": flags["tools"]["unknown"] = {"enabled": False}
    if change == "tools_enabled": flags["tools"]["update_plan"]["enabled"] = True
    if change == "tools_number": flags["tools"]["update_plan"]["enabled"] = 0
    if change == "agents": flags["agents"]["enabled"] = True
    if change == "duplicate_layer": response["layers"].append(response["layers"][0])
    if change == "effective_tool": response["config"]["tools"] = {"update_plan": {"enabled": True}}
    with pytest.raises(RuntimeFailure): validate_config(response, True, tmp_path, path)


@pytest.mark.parametrize("outcome", ["success", "startup_failure", "cancel", "model_drift"])
def test_rpc_catalog_restart_owns_cleanup_and_preserves_model(tmp_path, monkeypatch, outcome):
    async def run():
        rpc = CodexRPC(tmp_path / "profile", tmp_path / "workspace", allow_browsing=True)
        rpc.process = "bootstrap"
        closed, paths = [], []
        async def close(process, **kwargs): closed.append(process)
        async def verify(): pass
        async def read(*args): return payload()
        async def open_rpc():
            rpc.process = "restricted"
            paths.append(rpc.catalog.path)
            rpc.catalog.verify()
            if outcome == "startup_failure": raise RuntimeFailure("synthetic startup failure")
            if outcome == "cancel": raise asyncio.CancelledError
        async def models(*args):
            from backend.app.contracts import RuntimeModel
            return [RuntimeModel(id="other" if outcome == "model_drift" else "synthetic-model", name="Synthetic")]
        rpc.verify_policy, rpc.open = verify, open_rpc
        monkeypatch.setattr("backend.app.codex_rpc.read_metadata", read)
        monkeypatch.setattr("backend.app.codex_rpc.read_models", models)
        monkeypatch.setattr("backend.app.codex_rpc.close_owned", close)
        if outcome == "success":
            await rpc.restrict_model("synthetic-model")
            await rpc.verify_generation("synthetic-model")
            with pytest.raises(RuntimeFailure): await rpc.verify_generation("other")
            with pytest.raises(RuntimeFailure): await rpc.restrict_model("other")
            assert paths[0].is_file() and closed == ["bootstrap"]
        else:
            with pytest.raises(asyncio.CancelledError if outcome == "cancel" else RuntimeFailure):
                await rpc.restrict_model("synthetic-model")
        await rpc.close()
        assert not paths[0].exists() and rpc.catalog is None and rpc.process is None
        assert closed[:2] == ["bootstrap", "restricted"]
        with pytest.raises(RuntimeFailure): await rpc.verify_generation("synthetic-model")
    asyncio.run(run())


def test_replaced_catalog_link_is_neither_read_nor_deleted(tmp_path, monkeypatch):
    catalog = RestrictedCatalog(payload(), "synthetic-model")
    path = catalog.path
    original = Path.is_symlink
    try:
        monkeypatch.setattr(Path, "is_symlink", lambda value: value == path or original(value))
        with pytest.raises(RuntimeFailure): catalog.verify()
        with pytest.raises(RuntimeFailure): catalog.close()
        assert path.exists()
    finally:
        monkeypatch.setattr(Path, "is_symlink", original)
        catalog.close()


@pytest.mark.parametrize("failure", ["catalog", "account", "policy"])
def test_generation_requires_restriction_account_and_final_policy_before_turn(tmp_path, monkeypatch, failure):
    from backend.app.codex_runtime import CodexRuntime
    from tests.desktop.test_codex import FakeRPC

    async def run():
        rpc = FakeRPC()
        rpc.account = {"type": "chatgpt"}
        order = []
        async def restrict(selected):
            order.append("restrict")
            if failure == "catalog": raise RuntimeFailure("synthetic metadata failure")
            if failure == "account": rpc.account = {"type": "apiKey"}
        async def policy(selected):
            order.append("verify")
            if failure == "policy": raise RuntimeFailure("synthetic policy drift")
        async def require(*args, **kwargs): pass
        rpc.restrict_model, rpc.verify_generation = restrict, policy
        monkeypatch.setattr(CodexRuntime, "require_generation", require)
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *args, **kwargs: rpc)
        with pytest.raises(RuntimeFailure):
            _ = [e async for e in CodexRuntime(tmp_path).stream("synthetic", "run", tmp_path, "synthetic-model")]
        assert rpc.closed and not any(method == "turn/start" for method, _ in rpc.requests)
        assert order == (["restrict", "verify"] if failure == "policy" else ["restrict"])
    asyncio.run(run())
