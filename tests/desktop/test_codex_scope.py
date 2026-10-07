import asyncio
import hashlib
from types import SimpleNamespace

import pytest

from backend.app import codex_qualification as scope
from backend.app.codex_rpc import CodexRPC
from backend.app.codex_runtime import CodexRuntime
from backend.app.contracts import RuntimeCapabilities
from backend.app.runtime_base import RuntimeFailure
from backend.app.runtime_policy import apply_qualification
from tests.desktop.test_codex import FakeRPC


@pytest.mark.parametrize("change", [None, "platform", "shim", "extension", "missing", "contents"])
def test_native_identity_is_content_bound_not_version_or_path(tmp_path, monkeypatch, change):
    binary = tmp_path / "codex.exe"
    binary.write_bytes(b"synthetic executable, never executed")
    monkeypatch.setattr(scope, "EXECUTABLE_SHA256", hashlib.sha256(binary.read_bytes()).hexdigest())
    monkeypatch.setattr(scope, "sys", SimpleNamespace(platform="linux" if change == "platform" else "win32"))
    command = [str(binary)]
    if change == "shim": command = ["node.exe", str(binary)]
    if change == "extension": command = [str(tmp_path / "codex.cmd")]
    if change == "missing": binary.unlink()
    if change == "contents": binary.write_bytes(b"different binary, same version")
    monkeypatch.setattr(scope, "executable_command", lambda _: command)
    assert scope.native_identity_verified() is (change is None)


@pytest.mark.parametrize("verified,auth", [(True, "authenticated"), (False, "authenticated"), (True, "required"), (1, "authenticated")])
def test_version_authentication_and_verified_native_identity_are_all_required(verified, auth):
    result = apply_qualification(RuntimeCapabilities(provider="codex", installed=True,
        version="0.158.0-alpha.2.1", authentication=auth), native_identity_verified=verified)
    enabled = verified is True and auth == "authenticated"
    assert result.generation is enabled and result.browsing is enabled and result.approvals is enabled


def catalog():
    return SimpleNamespace(model=scope.MODEL, digest=bytes.fromhex(scope.CATALOG_SHA256), verify=lambda: None)


@pytest.mark.parametrize("browsing", [False, True])
@pytest.mark.parametrize("change", [None, "binary", "model", "catalog_model", "catalog_digest", "file", "policy", "capability", "extra", "typed", "mode"])
def test_scope_rejects_every_measured_identity_or_tool_drift(monkeypatch, browsing, change):
    # Exercise the reviewed Windows flags on both native Windows and POSIX CI.
    monkeypatch.setattr("backend.app.codex_policy.os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(scope, "native_identity_verified", lambda: change != "binary")
    selected, entry, caps = scope.MODEL, catalog(), dict(scope.CAPABILITIES)
    if change == "model": selected = "PRIVATE_OTHER_MODEL"
    if change == "catalog_model": entry.model = "PRIVATE_OTHER_MODEL"
    if change == "catalog_digest": entry.digest = b"changed"
    if change == "file":
        def changed(): raise RuntimeFailure("catalog integrity rejected")
        entry.verify = changed
    if change == "policy":
        policy = scope.policy_config
        monkeypatch.setattr(scope, "policy_config", lambda *args: {**policy(*args), "features.shell_tool": True})
    if change == "capability": caps["namespaceTools"] = False
    if change == "extra": caps["PRIVATE_EXTRA"] = False
    if change == "typed": caps["webSearch"] = 1
    if change == "mode": browsing = 1
    if change:
        with pytest.raises(RuntimeFailure) as error: scope.require_scope(entry, selected, browsing, caps)
        assert "PRIVATE" not in str(error.value)
    else:
        scope.require_scope(entry, selected, browsing, caps)


@pytest.mark.parametrize("failure", [None, "binary", "catalog", "capability"])
def test_real_production_guard_runs_before_turn_and_closes_on_drift(tmp_path, monkeypatch, failure):
    async def run():
        monkeypatch.setattr("backend.app.codex_policy.os", SimpleNamespace(name="nt"))
        monkeypatch.setattr(scope, "native_identity_verified", lambda: failure != "binary")
        class RPC(FakeRPC):
            allow_browsing = False
            verify_qualification = CodexRPC.verify_qualification
            async def restrict_model(self, selected):
                await super().restrict_model(selected)
                self.catalog = catalog()
                if failure == "catalog": self.catalog.digest = b"changed"
            async def request(self, method, params, **kwargs):
                if method == "model/list": return {"data": [{"model": scope.MODEL, "displayName": "Test", "hidden": False, "isDefault": True, "inputModalities": ["text"]}]}
                if method == "modelProvider/capabilities/read": return {**scope.CAPABILITIES, "webSearch": failure != "capability"}
                if method == "turn/start":
                    self.requests.append((method, params))
                    raise RuntimeFailure("SYNTHETIC_TURN_REACHED")
                return await super().request(method, params, **kwargs)
        rpc = RPC(); rpc.account = {"type": "chatgpt"}
        async def qualified(self): return RuntimeCapabilities(provider="codex", installed=True, qualification="live", authentication="authenticated", generation=True)
        monkeypatch.setattr(CodexRuntime, "check", qualified)
        monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *args, **kwargs: rpc)
        with pytest.raises(RuntimeFailure) as error:
            _ = [event async for event in CodexRuntime(tmp_path).stream("synthetic", "test", tmp_path, scope.MODEL, allow_browsing=False)]
        assert ("SYNTHETIC_TURN_REACHED" in str(error.value)) is (failure is None)
        assert any(method == "turn/start" for method, _ in rpc.requests) is (failure is None)
        assert rpc.closed
    asyncio.run(run())
