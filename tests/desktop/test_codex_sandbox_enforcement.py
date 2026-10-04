import asyncio
import base64
import os
from pathlib import Path
import re
import socket

import pytest

from backend.app.contracts import RuntimeCapabilities
from backend.app.runtime_base import AIRuntime, RuntimeFailure
from scripts import verify_codex_sandbox


def test_probe_command_is_bounded_readonly_network_disabled_and_uses_argv(tmp_path):
    calls = []
    class RPC:
        async def request(self, method, params, **kwargs):
            calls.append((method, params, kwargs))
            return {"exitCode": 0, "stdout": "SYNTHETIC", "stderr": "private-diagnostic"}
    assert asyncio.run(verify_codex_sandbox.execute(RPC(), tmp_path, "synthetic '$` code")) == "SYNTHETIC"
    method, params, limits = calls[0]
    assert method == "command/exec" and params["sandboxPolicy"] == {"type": "readOnly", "networkAccess": False}
    assert params["timeoutMs"] == 15000 and limits["timeout"] == 30
    assert "outputBytesCap" not in params and "disableOutputCap" not in params
    assert params["command"][-2] == "-EncodedCommand"
    assert base64.b64decode(params["command"][-1]).decode("utf-16-le") == "synthetic '$` code"


@pytest.mark.parametrize("failure", ["control", "write_allowed", "write_error"])
def test_enforcement_failure_stops_and_cleans_up_without_raw_diagnostics(tmp_path, monkeypatch, failure):
    calls, workspaces = [], []
    class RPC:
        closed = False
        async def open(self): pass
        async def request(self, method, params):
            assert method == "windowsSandbox/readiness"
            return {"status": "ready"}
        async def close(self): self.closed = True
    rpc = RPC()
    async def discover(self):
        return RuntimeCapabilities(provider="codex", installed=True, version="synthetic", qualification="protocol_only")
    async def execute(_rpc, workspace, script):
        workspaces.append(workspace)
        calls.append(script)
        if len(calls) == 1: return "wrong" if failure == "control" else "CONTROL_OK"
        if failure == "write_allowed":
            (workspace / "canary.txt").write_text("CHANGED")
            return "WRITE_ALLOWED"
        raise RuntimeFailure("private-diagnostic")
    monkeypatch.setattr(AIRuntime, "check", discover)
    monkeypatch.setattr(verify_codex_sandbox, "execute", execute)
    result = asyncio.run(verify_codex_sandbox.probe(tmp_path, rpc_factory=lambda *args, **kwargs: rpc))
    assert result["status"] == "blocked" and not result["generation_requested"] and not result["live_qualified"]
    assert "private-diagnostic" not in str(result) and rpc.closed
    assert len(calls) == (1 if failure == "control" else 2)
    assert all(not Path(workspace).exists() for workspace in workspaces)


@pytest.mark.parametrize("marker,connect,passed", [
    ("NETWORK_BLOCKED", False, True),
    ("NETWORK_ALLOWED", True, False),
    ("NETWORK_BLOCKED", True, False),
    ("unexpected", False, False),
])
def test_network_probe_requires_denial_and_no_listener_connection(tmp_path, monkeypatch, marker, connect, passed):
    class RPC:
        async def open(self): pass
        async def request(self, method, params):
            assert method == "windowsSandbox/readiness"
            return {"status": "ready"}
        async def close(self): pass
    async def discover(self):
        return RuntimeCapabilities(provider="codex", installed=True, version="synthetic", qualification="protocol_only")
    async def execute(rpc, workspace, script):
        if "CONTROL_OK" in script: return "CONTROL_OK"
        if "WRITE_DENIED" in script: return "WRITE_DENIED"
        if connect:
            port = int(re.search(r"ConnectAsync\('127\.0\.0\.1', (\d+)\)", script).group(1))
            _, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.close(); await writer.wait_closed()
            await asyncio.sleep(0)
        return marker
    monkeypatch.setattr(AIRuntime, "check", discover)
    monkeypatch.setattr(verify_codex_sandbox, "execute", execute)
    result = asyncio.run(verify_codex_sandbox.probe(tmp_path, rpc_factory=lambda *args, **kwargs: RPC()))
    assert (result["status"] == "enforcement_probes_passed_review_required") == passed
    assert result["checks"]["controlled_loopback_connection_blocked"] == passed
    assert result["checks"]["loopback_listener_observed_connection"] == connect
    assert not result["generation_requested"] and not result["live_qualified"]


@pytest.mark.parametrize("udp", [False, True])
@pytest.mark.parametrize("connect", [False, True])
def test_extended_probe_checks_real_host_control_and_rejects_false_denial(tmp_path, monkeypatch, udp, connect):
    async def execute(rpc, workspace, script):
        if connect:
            port = int(re.search(r"(?:ConnectAsync|Connect)\('127\.0\.0\.1', (\d+)\)", script).group(1))
            if udp:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                    client.setblocking(False)
                    loop = asyncio.get_running_loop()
                    await loop.sock_sendto(client, b"probe", ("127.0.0.1", port))
                    data, _ = await asyncio.wait_for(loop.sock_recvfrom(client, 64), 2)
                    assert data == b"ack"
            else:
                _, writer = await asyncio.open_connection("127.0.0.1", port)
                writer.close(); await writer.wait_closed()
                await asyncio.sleep(0)
        return "NETWORK_BLOCKED"
    monkeypatch.setattr(verify_codex_sandbox, "execute", execute)
    result = asyncio.run(verify_codex_sandbox.additional_loopback_probe(None, tmp_path, "127.0.0.1", udp=udp))
    assert result["host_control_reachable"] and result["reported_block"]
    assert result["listener_observed_connection"] == connect and result["blocked"] != connect


@pytest.mark.skipif(os.name != "nt", reason="Windows proactor IPv6 WSASendTo regression")
def test_ipv6_udp_host_control_uses_complete_socket_address(tmp_path, monkeypatch):
    async def execute(*args): return "NETWORK_BLOCKED"
    monkeypatch.setattr(verify_codex_sandbox, "execute", execute)
    result = asyncio.run(verify_codex_sandbox.additional_loopback_probe(None, tmp_path, "::1", udp=True))
    assert result["host_control_reachable"] and result["blocked"]
