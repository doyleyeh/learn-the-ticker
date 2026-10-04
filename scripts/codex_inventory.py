"""Installed-binary tool serialization against a credential-free local test peer.

Not an inference provider, proxy, production adapter or qualification promotion.
Never give this peer a real provider profile or authentication credential.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import tempfile

from backend.app.codex_catalog import RestrictedCatalog, unique_object
from backend.app.codex_models import read_models, select_model
from backend.app.codex_policy import (policy_config, prepare_workspace, thread_parameters,
                                     validate_config, validate_features, validate_thread)
from backend.app.codex_rpc import CodexRPC
from backend.app.owned_process import launch_owned
from backend.app.runtime_base import RuntimeFailure, executable_command, provider_environment


LIMIT = 1_000_000
PROVIDER = "ltt_inventory"
TOKEN_ENV = "LTT_INVENTORY_TOKEN"
FAILURE = "The local Codex inventory check failed. No cloud inference or permission grant was requested."
EXPECTED = {False: [], True: ["functions.request_permissions", "web.run"]}
PROVIDER_OPTIONALS = {"model_catalog_url", "env_key_instructions", "experimental_bearer_token", "auth", "gateway_oauth", "aws",
                      "query_params", "http_headers", "env_http_headers", "stream_idle_timeout_ms", "websocket_connect_timeout_ms"}


def same_capabilities(actual, expected):
    keys = {"namespaceTools", "imageGeneration", "webSearch"}
    return (isinstance(actual, dict) and isinstance(expected, dict) and set(actual) == set(expected) == keys
            and all(type(actual[k]) is bool and type(expected[k]) is bool and actual[k] == expected[k] for k in keys))


def summarize_request(raw: bytes, model: str, browsing: bool) -> dict:
    """Discard every non-tool value; unknown tool structure/names fail closed."""
    try:
        if not 0 < len(raw) <= LIMIT: raise ValueError()
        request = json.loads(raw, object_pairs_hook=unique_object)
        if (not isinstance(request, dict) or request.get("model") != model
                or request.get("tools") is not None or request.get("tool_choice") != "auto"):
            raise ValueError()
        items = request.get("input")
        if not isinstance(items, list) or not 1 <= len(items) <= 100 or not all(isinstance(i, dict) for i in items): raise ValueError()
        declarations = [i for i in items if i.get("type") == "additional_tools"]
        if len(declarations) != 1 or declarations[0] is not items[0] or declarations[0].get("role") != "developer": raise ValueError()
        specs = declarations[0].get("tools")
        if not isinstance(specs, list) or len(specs) > 32: raise ValueError()
        names, namespaces, schemas = [], set(), {}
        for spec in specs:
            if (not isinstance(spec, dict) or spec.get("type") != "namespace"
                    or set(spec) - {"type", "name", "description", "tools"}
                    or spec.get("name") not in ("functions", "web") or spec["name"] in namespaces):
                raise ValueError()
            namespaces.add(spec["name"])
            children = spec.get("tools")
            if not isinstance(children, list) or not 1 <= len(children) <= 32: raise ValueError()
            for child in children:
                if (not isinstance(child, dict) or child.get("type") != "function"
                        or set(child) - {"type", "name", "description", "parameters", "strict"}
                        or not isinstance(child.get("name"), str) or not isinstance(child.get("parameters"), dict)):
                    raise ValueError()
                name = spec["name"] + "." + child["name"]
                if name not in EXPECTED[browsing] or name in names: raise ValueError()
                names.append(name)
                # Hash the complete tool declaration, not just its parameter schema.
                schemas[name] = hashlib.sha256(json.dumps(child, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()
        if sorted(names) != EXPECTED[browsing]: raise ValueError()
        return {"tools": sorted(names), "declaration_sha256": schemas, "complete_serialized_set": True}
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        raise RuntimeFailure(FAILURE) from exc


class InventoryPeer:
    """One authenticated loopback request; never returns model/tool output."""
    def __init__(self, model, browsing):
        self.model, self.browsing = model, browsing
        self.token = secrets.token_urlsafe(48)
        self.server = None
        self.tasks = set()
        self.writers = set()
        self.closing = False
        self.result = asyncio.get_running_loop().create_future()
        self.requests = 0

    async def open(self):
        self.server = await asyncio.start_server(self.accept, "127.0.0.1", 0, limit=16_384)
        return f"http://127.0.0.1:{self.server.sockets[0].getsockname()[1]}/v1"

    def accept(self, reader, writer):
        if self.closing or len(self.tasks) >= 4:
            writer.close()
            return
        self.writers.add(writer)
        task = asyncio.create_task(self.handle(reader, writer))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def handle(self, reader, writer):
        try:
            async with asyncio.timeout(10):
                head = await reader.readuntil(b"\r\n\r\n")
                first, *lines = head.decode("ascii").split("\r\n")
                headers = {}
                for line in lines:
                    if not line: continue
                    key, value = line.split(":", 1)
                    key = key.lower()
                    if key in headers: raise ValueError()
                    headers[key] = value.strip()
                if (first != "POST /v1/responses HTTP/1.1"
                        or not hmac.compare_digest(headers.get("authorization", ""), "Bearer " + self.token)
                        or "transfer-encoding" in headers or "content-encoding" in headers
                        or self.requests != 0):
                    raise ValueError()
                size = int(headers.get("content-length", "0"))
                if not 0 < size <= LIMIT: raise ValueError()
                self.requests += 1
                summary = summarize_request(await reader.readexactly(size), self.model, self.browsing)
                if not self.result.done(): self.result.set_result(summary)
                # Stop transport here: no completion, tool call, retrieval or paid API.
                writer.write(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                await writer.drain()
        except (ValueError, OSError, TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, RuntimeFailure):
            if not self.result.done(): self.result.set_exception(RuntimeFailure(FAILURE))
        finally:
            writer.close()
            try: await writer.wait_closed()
            except OSError: pass
            self.writers.discard(writer)

    async def close(self):
        self.closing = True
        if self.server:
            self.server.close()
        # Close accepted transports before wait_closed(), which on Python 3.12
        # also waits for active connections. Include tasks not yet started.
        writers = list(self.writers)
        for writer in writers: writer.close()
        tasks = list(self.tasks)
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.tasks.difference_update(tasks)
        await asyncio.gather(*(writer.wait_closed() for writer in writers), return_exceptions=True)
        self.writers.difference_update(writers)
        if self.server: await self.server.wait_closed()
        if not self.result.done(): self.result.cancel()
        elif not self.result.cancelled(): self.result.exception()  # retrieve any unattended failure


def local_policy(browsing, catalog, base_url):
    provider = {"name": "OpenAI", "base_url": base_url, "env_key": TOKEN_ENV, "wire_api": "responses",
                "requires_openai_auth": False, "supports_websockets": False, "supports_standalone_web_search": True,
                "request_max_retries": 0, "stream_max_retries": 0}
    config = policy_config(browsing, catalog)
    config.pop("model_providers")
    config.update(model_provider=PROVIDER, **{f"model_providers.{PROVIDER}.{k}": v for k, v in provider.items()})
    return config


def validate_local_config(response, browsing, profile, catalog, expected):
    """Validate test transport separately; keep production validation unchanged."""
    config = response.get("config")
    if not isinstance(config, dict): raise RuntimeFailure(FAILURE)
    providers = config.get("model_providers")
    if not isinstance(providers, dict) or set(providers) != {PROVIDER} or config.get("model_provider") != PROVIDER:
        raise RuntimeFailure(FAILURE)
    actual = providers[PROVIDER]
    if not isinstance(actual, dict): raise RuntimeFailure(FAILURE)
    prefix = f"model_providers.{PROVIDER}."
    requested = {key.removeprefix(prefix): value for key, value in expected.items() if key.startswith(prefix)}
    # Typed provider serialization supplies absent optional fields as null. Reject
    # any non-null extra (headers, endpoints, command auth, query params, AWS...).
    for key, value in actual.items():
        if key not in requested and (key not in PROVIDER_OPTIONALS or value is not None): raise RuntimeFailure(FAILURE)
    for key, value in requested.items():
        if type(actual.get(key)) is not type(value) or actual.get(key) != value: raise RuntimeFailure(FAILURE)
    # The only differences allowed from app policy are the inspected test
    # transport fields above. All tool/sandbox/config-layer checks are unchanged.
    validate_config({**response, "config": {**config, "model_provider": "openai", "model_providers": {}}},
                    browsing, profile, catalog)


async def capture_inventory(payload, selected, capabilities, browsing, *, rpc_type=CodexRPC):
    peer = InventoryPeer(selected, browsing)
    rpc, catalog, path = None, None, None
    try:
        with tempfile.TemporaryDirectory(prefix="ltt-codex-inventory-") as directory:
            root = Path(directory)
            catalog = RestrictedCatalog(payload, selected)
            path = catalog.path
            base_url = await peer.open()
            rpc = rpc_type(root / "profile", root / "workspace", allow_browsing=browsing)
            prepare_workspace(rpc.profile, rpc.workspace)
            config = local_policy(browsing, path, base_url)
            args = ["--strict-config"]
            for key, value in config.items(): args.extend(["-c", key + "=" + json.dumps(value, separators=(",", ":"))])
            try:
                rpc.process = await launch_owned(*executable_command("codex"), "app-server", "--stdio", *args,
                    cwd=rpc.workspace, env={**provider_environment(), "CODEX_HOME": str(rpc.profile), TOKEN_ENV: peer.token},
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=2_000_000)
                await rpc.request("initialize", {"clientInfo": {"name": "ltt_inventory_probe", "version": "0.1.0"}})
                await rpc.send({"method": "initialized", "params": {}})
                if (await rpc.request("account/read", {"refreshToken": False})).get("account") is not None:
                    raise RuntimeFailure(FAILURE)
                if not same_capabilities(await rpc.request("modelProvider/capabilities/read", {}), capabilities): raise RuntimeFailure(FAILURE)
                validate_local_config(await rpc.request("config/read", {"cwd": str(rpc.workspace), "includeLayers": True}),
                                      browsing, rpc.profile, path, config)
                validate_features(await rpc.request("experimentalFeature/list", {"limit": 200}), request_permissions=browsing)
                if select_model(await read_models(rpc), selected) != selected: raise RuntimeFailure(FAILURE)
                thread = await rpc.request("thread/start", thread_parameters(rpc.workspace, selected))
                if thread.get("modelProvider") != PROVIDER or thread.get("model") != selected: raise RuntimeFailure(FAILURE)
                thread_id = validate_thread({**thread, "modelProvider": "openai"}, rpc.workspace)
                validate_features(await rpc.request("experimentalFeature/list", {"limit": 200, "threadId": thread_id}), request_permissions=browsing)
                catalog.verify()
                await rpc.request("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": "Synthetic inventory serialization. Do not call tools."}]})
                summary = await asyncio.wait_for(asyncio.shield(peer.result), 30)
            finally:
                await peer.close()
                await rpc.close()
                catalog.close()
        return {**summary, "credential_free_profile": True, "provider_capabilities_match": True,
                "tool_policy_matches": True, "local_requests": peer.requests,
                "owned_process_closed": rpc.process is None, "catalog_removed": not path.exists(),
                "test_transport_only": True, "cloud_inference_requested": False}
    except (OSError, ValueError, TypeError, TimeoutError) as exc:
        raise RuntimeFailure(FAILURE) from exc
    finally:
        await peer.close()
        if rpc: await rpc.close()
        if catalog: catalog.close()
