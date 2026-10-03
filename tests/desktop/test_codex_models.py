import asyncio
from collections import deque
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.codex_models import read_models, select_model
from backend.app.codex_runtime import CodexRuntime
from backend.app.codex_rpc import CodexRPC
from backend.app.contracts import ResearchRequest, RuntimeCapabilities, RuntimeModel, RuntimeModelCatalog, Settings
from backend.app.db import Database
from backend.app.runtime_base import AIRuntime, RuntimeFailure
from tests.desktop.test_codex import FakeRPC
from tests.desktop.test_codex_policy import config_response, features_response, thread_response


def row(model="synthetic-default", **kwargs):
    return {"model": model, "displayName": "Synthetic model", "hidden": False, "isDefault": True, "inputModalities": ["text"], **kwargs}


class CatalogRPC:
    def __init__(self, pages): self.pages, self.requests = deque(pages), []
    async def request(self, method, params):
        self.requests.append((method, params))
        return self.pages.popleft()


def test_model_catalog_pagination_uses_actual_model_ids_and_filters_hidden_nontext():
    rpc = CatalogRPC([
        {"data": [row(id="picker-id")], "nextCursor": "page2"},
        {"data": [row("hidden", hidden=True, isDefault=False), row("audio", inputModalities=["audio"], isDefault=False), row("alternate", isDefault=False)], "nextCursor": None},
    ])
    models = asyncio.run(read_models(rpc))
    assert [model.id for model in models] == ["synthetic-default", "alternate"]
    assert select_model(models, None) == "synthetic-default" and select_model(models, "alternate") == "alternate"
    assert rpc.requests[1][1]["cursor"] == "page2" and not rpc.requests[0][1]["includeHidden"]
    with pytest.raises(RuntimeFailure, match="no fallback"): select_model(models, "removed")


@pytest.mark.parametrize("change", [
    {"model": "https://bad.example?token=private"}, {"hidden": "false"},
    {"isDefault": 1}, {"displayName": "private\ntext"}, {"inputModalities": "text"}, {"model": ""},
])
def test_malformed_catalog_is_sanitized_and_never_partially_accepted(change):
    rpc = CatalogRPC([{"data": [row(), row("second") | change]}])
    with pytest.raises(RuntimeFailure) as exc: asyncio.run(read_models(rpc))
    assert "private" not in str(exc.value)


@pytest.mark.parametrize("pages", [
    [{"data": [row(), row()]}],
    [{"data": [row(), row("second")]}],
    [{"data": [], "nextCursor": "same"}, {"data": [], "nextCursor": "same"}],
    [{"data": [], "nextCursor": str(n)} for n in range(4)],
    [{"data": [row(str(n), isDefault=False) for n in range(51)]}],
    [{"data": [], "nextCursor": 3}],
])
def test_ambiguous_or_incomplete_catalog_fails_closed(pages):
    with pytest.raises(RuntimeFailure): asyncio.run(read_models(CatalogRPC(pages)))


def test_default_selection_requires_one_catalog_default():
    with pytest.raises(RuntimeFailure, match="unambiguous"): select_model([], None)
    with pytest.raises(RuntimeFailure, match="unambiguous"): select_model([RuntimeModel(id="one", name="One")], None)


@pytest.mark.parametrize("account,status", [(None, "authentication_required"), ({"type": "apiKey"}, "unavailable"), ({"type": "chatgptAuthTokens"}, "unavailable"), ({"type": "chatgpt"}, "available")])
def test_catalog_discovery_checks_subscription_and_never_infers(tmp_path, monkeypatch, account, status):
    rpc = FakeRPC(); rpc.account = account
    monkeypatch.setattr("backend.app.codex_runtime.CodexRPC", lambda *args, **kwargs: rpc)
    async def version(self): return RuntimeCapabilities(provider="codex", installed=True, qualification="protocol_only")
    monkeypatch.setattr(AIRuntime, "check", version)
    result = asyncio.run(CodexRuntime(tmp_path).models())
    assert result.status == status and rpc.closed
    methods = [method for method, _ in rpc.requests]
    assert "thread/start" not in methods and "turn/start" not in methods
    assert ("model/list" in methods) == (status == "available")


def test_server_model_substitution_is_rejected_before_inference(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.app.codex_policy.system_config_directory", lambda: tmp_path / "system")
    async def run():
        rpc = CodexRPC(tmp_path / "profile", tmp_path / "workspace")
        async def request(method, params):
            if method == "config/read": return config_response()
            if method == "experimentalFeature/list": return features_response()
            if method == "thread/start":
                assert params["allowProviderModelFallback"] is False
                return thread_response(rpc.workspace) | {"model": "substituted"}
            pytest.fail("inference started")
        rpc.request = request
        with pytest.raises(RuntimeFailure, match="changed the selected model"): await rpc.start_thread("requested")
    asyncio.run(run())


class ModelAdapter:
    async def models(self):
        return RuntimeModelCatalog(provider="codex", status="available", models=[RuntimeModel(id="selected", name="Synthetic")])


def test_authenticated_api_selects_only_current_catalog_and_retains_previous_on_failure(tmp_path):
    db = Database("sqlite://", testing=True)
    app = create_app(db, "x" * 40, tmp_path, adapters={"codex": ModelAdapter()})
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer " + "x" * 40}
        assert client.get("/api/connections/codex/models").status_code == 401
        response = client.get("/api/connections/codex/models", headers=headers)
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        assert client.get("/api/connections/unknown/models", headers=headers).status_code == 404
        assert client.put("/api/settings", headers=headers, json={"model": "selected"}).status_code == 200
        assert client.put("/api/settings", headers=headers, json={"model": "removed"}).status_code == 409
        assert client.put("/api/settings", headers=headers, json={"provider": "gemini", "model": "selected"}).status_code == 409
        assert client.get("/api/settings", headers=headers).json()["model"] == "selected"
        assert client.put("/api/settings", headers=headers, json={"provider": "gemini", "model": None}).status_code == 200


def test_selected_request_snapshots_settings_and_rejects_foreign_model_provider(tmp_path):
    db = Database("sqlite://", testing=True)
    service = create_app(db, "x" * 40, tmp_path, adapters={"codex": ModelAdapter()}).state.service
    assert Settings.model_validate({}).model is None
    db.put("settings", "settings", {"model": "selected"})
    assert service.selected_request(ResearchRequest(query="example")).model == "selected"
    for request in [ResearchRequest(query="example", provider="gemini"), ResearchRequest(query="example", model="foreign")]:
        with pytest.raises(ValueError, match="Connections"): service.selected_request(request)


def test_model_change_rechecks_active_work_after_catalog_wait(tmp_path):
    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        class DelayedModels(ModelAdapter):
            async def models(self):
                started.set()
                await release.wait()
                return await super().models()
        db = Database("sqlite://", testing=True)
        app = create_app(db, "x" * 40, tmp_path, adapters={"codex": DelayedModels()})
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", headers={"Authorization": "Bearer " + "x" * 40}) as client:
            change = asyncio.create_task(client.put("/api/settings", json={"cloud_enabled": True, "model": "selected"}))
            await started.wait()
            app.state.service.tasks["active"] = SimpleNamespace(done=lambda: False)
            release.set()
            assert (await change).status_code == 409
            assert db.get("settings") is None
            app.state.service.tasks.clear()
    asyncio.run(run())
