"""Explicit native Windows enforcement probe; no sign-in, inference or OS setup.

Exercises the provider's standalone sandbox command endpoint with synthetic
canaries and a disposable loopback listener. This does not expose command tools
to models or qualify subscription billing, model-facing tools or the installer.
"""
import argparse
import asyncio
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import tempfile

from backend.app.codex_policy import require_execution_sandbox
from backend.app.codex_rpc import CodexRPC
from backend.app.codex_runtime import CodexRuntime
from backend.app.runtime_base import AIRuntime, RuntimeFailure
from scripts.qualify_codex import resolve_profile


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


async def execute(rpc, workspace, script):
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    shell = Path(os.environ.get("SYSTEMROOT", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = await rpc.request("command/exec", {
        "command": [str(shell), "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        "cwd": str(workspace.resolve()), "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
        # Pinned Windows command/exec rejects custom output caps. Retain its
        # default cap and the RPC transport's independent message bound.
        "timeoutMs": 15000,
    }, timeout=30)
    if type(result.get("exitCode")) is not int or result["exitCode"] != 0 or not isinstance(result.get("stdout"), str):
        raise RuntimeFailure("Sandbox probe did not complete its controlled operation")
    return result["stdout"].strip()


async def additional_loopback_probe(rpc, workspace, address, *, udp=False):
    """Control the same live listener from the host, then from the sandbox."""
    accepted, connections = asyncio.Event(), []
    family = socket.AF_INET6 if address == "::1" else socket.AF_INET
    shell_family = "InterNetworkV6" if family == socket.AF_INET6 else "InterNetwork"
    server = None
    class Datagram(asyncio.DatagramProtocol):
        def connection_made(self, transport): self.transport = transport
        def datagram_received(self, data, peer):
            connections.append(True)
            accepted.set()
            self.transport.sendto(b"ack", peer)
    def connected(reader, writer):
        connections.append(True)
        accepted.set()
        writer.close()
    try:
        loop = asyncio.get_running_loop()
        if udp:
            server, _ = await loop.create_datagram_endpoint(Datagram, local_addr=(address, 0), family=family)
            port = server.get_extra_info("sockname")[1]
            with socket.socket(family, socket.SOCK_DGRAM) as client:
                client.setblocking(False)
                peer = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
                await loop.sock_sendto(client, b"probe", peer)
                data, _ = await asyncio.wait_for(loop.sock_recvfrom(client, 64), timeout=2)
                if data != b"ack": raise RuntimeFailure("Datagram control failed")
        else:
            server = await asyncio.start_server(connected, address, 0, family=family)
            port = server.sockets[0].getsockname()[1]
            _, writer = await asyncio.open_connection(address, port)
            writer.close(); await writer.wait_closed()
        await asyncio.wait_for(accepted.wait(), timeout=2)
        connections.clear()
        start = f"$ErrorActionPreference='Stop'; $probeClient = [Net.Sockets.{'UdpClient' if udp else 'TcpClient'}]::new([Net.Sockets.AddressFamily]::{shell_family}); try {{ "
        if udp:
            operation = f"$probeClient.Client.ReceiveTimeout=2000; $probeClient.Connect('{address}', {port}); [void]$probeClient.Send([byte[]](83),1); $probePeer=[Net.IPEndPoint]::new([Net.IPAddress]::{'IPv6Any' if family == socket.AF_INET6 else 'Any'},0); [void]$probeClient.Receive([ref]$probePeer); [Console]::Write('NETWORK_ALLOWED')"
            caught = " } catch [Net.Sockets.SocketException] { if ($_.Exception.NativeErrorCode -in @(10013,10060)) { [Console]::Write('NETWORK_BLOCKED') } else { [Console]::Write('NETWORK_ERROR') } }"
        else:
            operation = f"$probeConnect=$probeClient.ConnectAsync('{address}', {port}); if ($probeConnect.Wait(2000) -and $probeClient.Connected) {{ [Console]::Write('NETWORK_ALLOWED') }} else {{ [Console]::Write('NETWORK_BLOCKED') }}"
            caught = " } catch [System.AggregateException] { [Console]::Write('NETWORK_BLOCKED') }"
        marker = await execute(rpc, workspace, start + operation + caught + " finally { $probeClient.Dispose() }")
        await asyncio.sleep(0)  # Drain delivered local socket callbacks before deciding.
        return {"host_control_reachable": True, "reported_block": marker == "NETWORK_BLOCKED",
                "listener_observed_connection": bool(connections),
                "blocked": marker == "NETWORK_BLOCKED" and not connections}
    finally:
        if server:
            server.close()
            if not udp: await server.wait_closed()


async def probe(profile, *, rpc_factory=CodexRPC, extended=False):
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": "blocked",
              "generation_requested": False, "live_qualified": False, "version": None,
              "checks": {}, "stage": "version"}
    version = await AIRuntime.check(CodexRuntime(profile))
    report["version"] = version.version
    if not version.installed or version.qualification == "unqualified": return report
    with tempfile.TemporaryDirectory(prefix="ltt-sandbox-enforcement-") as directory:
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir()
        canaries = {"inside": workspace / "canary.txt", "outside": root / "canary.txt"}
        original = "Synthetic sandbox canary."
        for path in canaries.values(): path.write_text(original, encoding="utf-8")
        rpc = rpc_factory(profile, workspace, allow_browsing=False)
        server = None
        try:
            report["stage"] = "readiness"
            await rpc.open()
            await require_execution_sandbox(rpc)
            report["stage"] = "control"
            paths = ",".join(ps_literal(path) for path in canaries.values())
            control = "$ErrorActionPreference='Stop'; " + f"foreach ($probePath in @({paths})) {{ if ([IO.File]::ReadAllText($probePath) -ne {ps_literal(original)}) {{ exit 3 }} }}; [Console]::Write('CONTROL_OK')"
            report["checks"]["sandbox_command_and_canary_reads"] = await execute(rpc, workspace, control) == "CONTROL_OK"
            if not report["checks"]["sandbox_command_and_canary_reads"]: raise RuntimeFailure("Control failed")
            for name, path in canaries.items():
                report["stage"] = name + "_write"
                script = "$ErrorActionPreference='Stop'; try { " + f"[IO.File]::WriteAllText({ps_literal(path)}, 'CHANGED'); [Console]::Write('WRITE_ALLOWED')" + " } catch [UnauthorizedAccessException] { [Console]::Write('WRITE_DENIED') }"
                denied = await execute(rpc, workspace, script) == "WRITE_DENIED"
                report["checks"][name + "_write_denied"] = denied and path.read_text(encoding="utf-8") == original
                if not report["checks"][name + "_write_denied"]: raise RuntimeFailure("Write enforcement failed")
            report["stage"] = "network"
            connections, accepted = [], asyncio.Event()
            def connected(reader, writer):
                connections.append(True)
                accepted.set()
                writer.close()
            server = await asyncio.start_server(connected, "127.0.0.1", 0)
            port = server.sockets[0].getsockname()[1]
            _, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.close(); await writer.wait_closed()
            await asyncio.wait_for(accepted.wait(), timeout=2)
            connections.clear()
            script = "$ErrorActionPreference='Stop'; $probeClient = [Net.Sockets.TcpClient]::new(); try { " + f"$probeConnect = $probeClient.ConnectAsync('127.0.0.1', {port}); if ($probeConnect.Wait(2000) -and $probeClient.Connected) {{ [Console]::Write('NETWORK_ALLOWED') }} else {{ [Console]::Write('NETWORK_BLOCKED') }}" + " } catch [System.AggregateException] { [Console]::Write('NETWORK_BLOCKED') } finally { $probeClient.Dispose() }"
            blocked = await execute(rpc, workspace, script) == "NETWORK_BLOCKED"
            report["checks"]["network_probe_reported_block"] = blocked
            report["checks"]["loopback_listener_observed_connection"] = bool(connections)
            report["checks"]["controlled_loopback_connection_blocked"] = blocked and not connections
            if not report["checks"]["controlled_loopback_connection_blocked"]: raise RuntimeFailure("Network enforcement failed")
            if extended:
                for name, address, udp in (("tcp_ipv6", "::1", False), ("udp_ipv4", "127.0.0.1", True), ("udp_ipv6", "::1", True)):
                    report["stage"] = name
                    result = await additional_loopback_probe(rpc, workspace, address, udp=udp)
                    report["checks"].update({name + "_" + key: value for key, value in result.items()})
                    if not result["blocked"]: raise RuntimeFailure("Extended network enforcement failed")
            report.update(status="enforcement_probes_passed_review_required", stage="review")
        except (RuntimeFailure, OSError, ValueError, TypeError, TimeoutError):
            report["status"] = "blocked"
        finally:
            if server:
                server.close(); await server.wait_closed()
            await rpc.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help="Dedicated app-owned profile; never the developer profile")
    parser.add_argument("--extended", action="store_true", help="Also require IPv6 TCP and IPv4/IPv6 UDP host controls and sandbox denials")
    args = parser.parse_args()
    if os.name != "nt":
        print(json.dumps({"status": "windows_required", "generation_requested": False}))
        return 2
    try:
        report = asyncio.run(probe(resolve_profile(args.profile), extended=args.extended))
        print(json.dumps(report, indent=2))
        return 0 if report["status"] == "enforcement_probes_passed_review_required" else 2
    except (RuntimeFailure, OSError, ValueError, TypeError, KeyboardInterrupt):
        print(json.dumps({"status": "blocked_or_cancelled", "generation_requested": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
