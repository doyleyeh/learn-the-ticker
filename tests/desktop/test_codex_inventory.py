import asyncio
import copy
import json

import pytest

from backend.app.codex_policy import DISABLED_FEATURES
from backend.app.runtime_base import RuntimeFailure
from scripts import codex_inventory as probe
from tests.desktop.test_codex import FakeRPC
from tests.desktop.test_codex_catalog import payload
from tests.desktop.test_codex_policy import thread_response


CAPS = {"namespaceTools": True, "imageGeneration": True, "webSearch": True}


def request_body(browsing=True):
    tools = [{"type": "namespace", "name": namespace, "tools": [
        {"type": "function", "name": name, "parameters": {"type": "object"}, "description": "synthetic schema"}]
    } for namespace, name in (("functions", "request_permissions"), ("web", "run"))] if browsing else []
    return {"model": "synthetic-model", "tools": None, "tool_choice": "auto", "input": [
        {"type": "additional_tools", "role": "developer", "tools": tools},
        {"type": "message", "content": "PRIVATE_PROMPT_SENTINEL"}]}


def test_complete_wire_set_has_only_names_hashes_and_no_prompt():
    for browsing in (False, True):
        summary = probe.summarize_request(json.dumps(request_body(browsing)).encode(), "synthetic-model", browsing)
        assert summary["tools"] == probe.EXPECTED[browsing] and summary["complete_serialized_set"]
        assert "PRIVATE" not in str(summary) and "synthetic schema" not in str(summary)
        assert all(len(value) == 64 for value in summary["declaration_sha256"].values())


@pytest.mark.parametrize("change", ["model", "top_tools", "duplicate_block", "missing_block", "role", "order", "duplicate_namespace",
    "duplicate_function", "unexpected_namespace", "unexpected_function", "hosted_tool", "empty_namespace", "missing_tool",
    "custom_tool", "unknown_field", "invalid_schema", "duplicate_json", "oversized", "reasoning", "cached_tool"])
def test_unexpected_incomplete_or_ambiguous_tool_declarations_fail(change):
    request = request_body()
    first = request["input"][0]
    specs = first["tools"]
    if change == "model": request["model"] = "other"
    if change == "top_tools": request["tools"] = []
    if change == "duplicate_block": request["input"].append(copy.deepcopy(first))
    if change == "missing_block": request["input"].pop(0)
    if change == "role": first["role"] = "user"
    if change == "order": request["input"].reverse()
    if change == "duplicate_namespace": specs.append(copy.deepcopy(specs[0]))
    if change == "duplicate_function": specs[0]["tools"].append(copy.deepcopy(specs[0]["tools"][0]))
    if change == "unexpected_namespace": specs[0]["name"] = "private-plugin"
    if change == "unexpected_function": specs[0]["tools"][0]["name"] = "exec_command"
    if change == "hosted_tool": specs.append({"type": "web_search"})
    if change == "empty_namespace": specs[0]["tools"] = []
    if change == "missing_tool": specs.pop(0)
    if change == "custom_tool": specs[0]["tools"][0]["type"] = "custom"
    if change == "unknown_field": specs[0]["tools"][0]["deferred"] = True
    if change == "invalid_schema": specs[0]["tools"][0]["parameters"] = None
    raw = json.dumps(request).encode()
    if change == "duplicate_json": raw = raw.replace(b'"model":', b'"model":"other","model":')
    if change == "oversized": raw = b"x" * (probe.LIMIT + 1)
    if change == "reasoning": raw = b"PRIVATE_REASONING_SENTINEL"
    with pytest.raises(RuntimeFailure) as error: probe.summarize_request(raw, "synthetic-model", change != "cached_tool")
    assert "PRIVATE" not in str(error.value) and "exec_command" not in str(error.value)


@pytest.mark.parametrize("change", ["number", "missing", "extra", "false"])
def test_provider_capabilities_are_typed_and_complete(change):
    actual = CAPS.copy()
    if change == "number": actual["webSearch"] = 1
    if change == "missing": actual.pop("webSearch")
    if change == "extra": actual["unknown"] = True
    if change == "false": actual["webSearch"] = False
    assert not probe.same_capabilities(actual, CAPS)


async def send(peer, raw, *, mode="valid"):
    port = peer.server.sockets[0].getsockname()[1]
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    token = "wrong" if mode == "auth" else peer.token
    first = "POST /v1/responses HTTP/1.1" if mode != "path" else "POST /v1/responses?private=true HTTP/1.1"
    extra = ""
    if mode == "compressed": extra = "Content-Encoding: gzip\r\n"
    if mode == "chunked": extra = "Transfer-Encoding: chunked\r\n"
    if mode == "duplicate": extra = "Content-Length: 1\r\n"
    size = probe.LIMIT + 1 if mode == "size" else len(raw)
    try:
        writer.write((f"{first}\r\nAuthorization: Bearer {token}\r\nContent-Length: {size}\r\n{extra}\r\n").encode() + raw)
        await writer.drain()
        return await reader.read(1024)
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.parametrize("mode", ["valid", "auth", "path", "compressed", "chunked", "duplicate", "size", "body"])
def test_local_peer_authenticates_bounds_and_discards_without_model_output(mode):
    async def run():
        peer = probe.InventoryPeer("synthetic-model", True)
        url = await peer.open()
        assert url.startswith("http://127.0.0.1:")
        try:
            result = await send(peer, b"PRIVATE" if mode == "body" else json.dumps(request_body()).encode(), mode=mode)
            if mode == "valid":
                assert (await peer.result)["tools"] == probe.EXPECTED[True]
                assert result.startswith(b"HTTP/1.1 400") and b"PRIVATE" not in result
            else:
                with pytest.raises(RuntimeFailure): await peer.result
        finally:
            await peer.close()
        assert not peer.tasks and not peer.server.is_serving()
    asyncio.run(run())


def test_listener_shutdown_cancels_incomplete_requests():
    async def run():
        peer = probe.InventoryPeer("synthetic-model", False)
        await peer.open()
        reader, writer = await asyncio.open_connection("127.0.0.1", peer.server.sockets[0].getsockname()[1])
        writer.write(b"POST ")
        await writer.drain()
        await asyncio.sleep(0)
        await peer.close()
        assert not peer.tasks and not peer.server.is_serving()
        assert await asyncio.wait_for(reader.read(), 1) == b""
        writer.close()
        await writer.wait_closed()
    asyncio.run(run())


def config_response(expected):
    config = {}
    for key, value in expected.items():
        target = config
        parts = key.split(".")
        for part in parts[:-1]: target = target.setdefault(part, {})
        target[parts[-1]] = value
    return {"config": config, "layers": [{"name": {"type": "sessionFlags"}, "config": copy.deepcopy(config)}]}


@pytest.mark.parametrize("change", ["endpoint", "extra_auth", "unknown_null", "provider", "shell", "cloud", "board"])
def test_local_transport_comparison_cannot_hide_tool_or_auth_drift(tmp_path, change):
    expected = probe.local_policy(True, tmp_path / "catalog.json", "http://127.0.0.1:1234/v1")
    response = config_response(expected)
    actual = response["config"]["model_providers"][probe.PROVIDER]
    if change == "endpoint": actual["base_url"] = "https://example.test"
    if change == "extra_auth": actual["auth"] = {"command": "private"}
    if change == "unknown_null": actual["unknown_auth"] = None
    if change == "provider": response["config"]["model_provider"] = "openai"
    if change == "shell": response["config"]["features"]["shell_tool"] = True
    if change == "cloud": response["layers"][0]["config"]["cloud"]["skills"]["enabled"] = True
    if change == "board": response["config"]["features"]["agent_message_board"] = True
    with pytest.raises(RuntimeFailure): probe.validate_local_config(response, True, tmp_path, tmp_path / "catalog.json", expected)


@pytest.mark.parametrize("browsing,fail", [(False, None), (True, None), (True, "account"), (True, "capabilities"), (True, "cancel")])
def test_full_capture_owns_listener_catalog_profile_and_only_synthetic_token(tmp_path, monkeypatch, browsing, fail):
    async def run():
        launches, instances, senders = [], [], []
        monkeypatch.setattr("backend.app.codex_policy.system_config_directory", lambda: tmp_path / "system")
        monkeypatch.setattr(probe, "executable_command", lambda _: ["synthetic-codex"])
        monkeypatch.setenv("OPENAI_API_KEY", "PRIVATE_ACCOUNT_KEY")
        async def launch(*args, **kwargs):
            launches.append((args, kwargs))
            return object()
        monkeypatch.setattr(probe, "launch_owned", launch)
        class RPC(FakeRPC):
            def __init__(self, profile, workspace, **kwargs):
                super().__init__()
                self.profile, self.workspace = profile, workspace
                self.process = None
                self.account = {"type": "chatgpt"} if fail == "account" else None
                instances.append(self)
            async def send(self, message): pass
            async def request(self, method, params, **kwargs):
                args, environment = launches[0][0], launches[0][1]["env"]
                fields = [args[i + 1] for i, value in enumerate(args[:-1]) if value == "-c"]
                expected = {key: json.loads(value) for key, value in (field.split("=", 1) for field in fields)}
                if method == "modelProvider/capabilities/read": return {**CAPS, "webSearch": False} if fail == "capabilities" else CAPS
                if method == "config/read": return config_response(expected)
                if method == "experimentalFeature/list": return {"data": [{"name": name, "enabled": browsing if name == "request_permissions_tool" else False} for name in DISABLED_FEATURES]}
                if method == "thread/start": return {**thread_response(self.workspace), "modelProvider": probe.PROVIDER}
                if method == "turn/start":
                    if fail == "cancel": raise asyncio.CancelledError
                    from urllib.parse import urlsplit
                    port = urlsplit(expected[f"model_providers.{probe.PROVIDER}.base_url"]).port
                    async def emit():
                        reader, writer = await asyncio.open_connection("127.0.0.1", port)
                        raw = json.dumps(request_body(browsing)).encode()
                        writer.write((f"POST /v1/responses HTTP/1.1\r\nAuthorization: Bearer {environment[probe.TOKEN_ENV]}\r\nContent-Length: {len(raw)}\r\n\r\n").encode() + raw)
                        await writer.drain()
                        await reader.read()
                        writer.close()
                        await writer.wait_closed()
                    senders.append(asyncio.create_task(emit()))
                return await super().request(method, params, **kwargs)
            async def close(self): self.process = None; await super().close()
        if fail:
            with pytest.raises(asyncio.CancelledError if fail == "cancel" else RuntimeFailure):
                await probe.capture_inventory(payload(), "synthetic-model", CAPS, browsing, rpc_type=RPC)
        else:
            result = await probe.capture_inventory(payload(), "synthetic-model", CAPS, browsing, rpc_type=RPC)
            assert result["tools"] == probe.EXPECTED[browsing] and result["local_requests"] == 1
            assert result["catalog_removed"] and result["owned_process_closed"]
            assert not result["cloud_inference_requested"]
        await asyncio.gather(*senders)
        assert len(instances) == 1 and instances[0].closed and not instances[0].profile.exists()
        assert "OPENAI_API_KEY" not in launches[0][1]["env"]
        assert launches[0][1]["env"][probe.TOKEN_ENV] != "PRIVATE_ACCOUNT_KEY"
    asyncio.run(run())


@pytest.mark.parametrize("failure", [None, "version", "account", "capture", "binary"])
def test_driver_closes_authenticated_process_before_capture_and_never_promotes(tmp_path, monkeypatch, failure):
    from backend.app.contracts import RuntimeCapabilities
    from backend.app.runtime_policy import QUALIFICATIONS
    from scripts import qualify_codex_inventory as driver
    async def run():
        rpc = FakeRPC()
        rpc.account = None if failure == "account" else {"type": "chatgpt"}
        original = rpc.request
        async def request(method, params, **kwargs):
            if method == "modelProvider/capabilities/read": return CAPS
            assert method not in ("turn/start", "account/login/start")
            return await original(method, params, **kwargs)
        rpc.request = request
        catalog_path = tmp_path / "catalog.json"
        catalog_path.write_bytes(payload())
        class Catalog:
            path = catalog_path
            def verify(self): pass
        async def restrict(model): rpc.catalog = Catalog()
        rpc.restrict_model = restrict
        async def discover(self):
            return RuntimeCapabilities(provider="codex", installed=True, version="synthetic",
                                       qualification="unqualified" if failure == "version" else "protocol_only")
        calls = []
        async def capture(data, model, capabilities, browsing):
            assert rpc.closed and capabilities == CAPS and data == payload()
            calls.append(browsing)
            if failure == "capture": raise RuntimeFailure("PRIVATE_PROVIDER_DIAGNOSTIC")
            return {"tools": probe.EXPECTED[browsing], "complete_serialized_set": True}
        fingerprints = iter(["original", "changed" if failure == "binary" else "original"])
        monkeypatch.setattr(driver, "CodexRPC", lambda *args: rpc)
        monkeypatch.setattr(driver.AIRuntime, "check", discover)
        monkeypatch.setattr(driver, "capture_inventory", capture)
        monkeypatch.setattr(driver, "executable_fingerprint", lambda: next(fingerprints))
        before = dict(QUALIFICATIONS)
        report = await driver.inventory(tmp_path, "synthetic-model")
        assert report["status"] == ("blocked" if failure else "serialized_inventory_verified_review_required")
        assert not report["live_qualified"] and not report["cloud_inference_requested"]
        assert QUALIFICATIONS == before and rpc.closed and "PRIVATE" not in str(report)
        assert calls == ([] if failure in ("version", "account") else [False] if failure == "capture" else [False, True])
    asyncio.run(run())
