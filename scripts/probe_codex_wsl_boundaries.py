"""Explicit account-free WSL2 keyring/sandbox experiments, never promotion.

All keyring values and passwords are disposable synthetic canaries. A private
D-Bus and encrypted GNOME keyring are created and destroyed for this run only.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import tempfile
from urllib.parse import unquote

from backend.app.owned_process import close_owned, launch_owned
from scripts.inspect_codex_wsl import InspectionFailure, bounded_output, reviewed_binary


def environment(root):
    return {"PATH": "/usr/bin:/bin", "HOME": str(root), "CODEX_HOME": str(root / "codex-a"),
            "XDG_CONFIG_HOME": str(root / "config"), "XDG_DATA_HOME": str(root / "data"),
            "XDG_CACHE_HOME": str(root / "cache"), "XDG_RUNTIME_DIR": str(root / "run"),
            "TMPDIR": str(root / "tmp"), "LANG": "C.UTF-8", "NO_COLOR": "1"}


async def command(args, env, cwd, data=None, timeout=15):
    process = await launch_owned(*map(str, args), env=env, cwd=cwd,
                                stdin=asyncio.subprocess.PIPE if data is not None else asyncio.subprocess.DEVNULL,
                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    tasks = []
    try:
        if data is not None:
            process.stdin.write(data)
            await process.stdin.drain()
            process.stdin.close()
        tasks = [asyncio.create_task(bounded_output(process.stdout)),
                 asyncio.create_task(bounded_output(process.stderr)), asyncio.create_task(process.wait())]
        stdout, _, code = await asyncio.wait_for(asyncio.gather(*tasks), timeout)
        return code, stdout
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await close_owned(process)


def require(condition, code):
    if not condition:
        raise InspectionFailure(code)


async def start_keyring(root, env, password):
    process = await launch_owned("/usr/bin/gnome-keyring-daemon", "--foreground", "--unlock",
                                "--components=secrets", "--control-directory=" + str(root / "run/keyring"),
                                env=env, cwd=root, stdin=asyncio.subprocess.PIPE,
                                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        process.stdin.write(password)
        await process.stdin.drain()
        process.stdin.close()
        for _ in range(40):
            code, output = await command(["/usr/bin/gdbus", "call", "--session", "--dest", "org.freedesktop.DBus",
                                         "--object-path", "/org/freedesktop/DBus", "--method",
                                         "org.freedesktop.DBus.NameHasOwner", "org.freedesktop.secrets"], env, root, timeout=2)
            if code == 0 and output.strip() == b"(true,)" and process.returncode is None:
                return process
            await asyncio.sleep(0.05)
        raise InspectionFailure("keyring_start_failed")
    except BaseException:
        await close_owned(process)
        raise


def credential_key(profile):
    return "cli|" + hashlib.sha256(str(profile.resolve()).encode()).hexdigest()[:16]


async def keyring_probe(binary, root):
    env, bus, keyring = environment(root), None, None
    password = secrets.token_urlsafe(32).encode()
    # These are not usable credentials and are never submitted to a provider.
    canaries = [secrets.token_urlsafe(32).encode() for _ in range(2)]
    keys = [credential_key(root / name) for name in ("codex-a", "codex-b")]
    async def lookup(key):
        return await command(["/usr/bin/secret-tool", "lookup", "service", "Codex Auth", "username", key], env, root)
    try:
        bus = await launch_owned("/usr/bin/dbus-daemon", "--session", "--nofork", "--print-address=1",
                                 "--address=unix:path=" + str(root / "run/bus"), env=env, cwd=root,
                                 stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
                                 stderr=asyncio.subprocess.DEVNULL)
        address = (await asyncio.wait_for(bus.stdout.readline(), 3)).decode().strip()
        require(address.startswith("unix:path=") and unquote(address.split(",", 1)[0][10:]) == str(root / "run/bus"),
                "private_bus_address_rejected")
        env["DBUS_SESSION_BUS_ADDRESS"] = address
        keyring = await start_keyring(root, env, password)
        for key, canary in zip(keys, canaries):
            code, _ = await command(["/usr/bin/secret-tool", "store", "--label=LTT disposable synthetic probe",
                                     "service", "Codex Auth", "username", key], env, root, canary)
            require(code == 0, "keyring_store_failed")
            code, value = await lookup(key)
            require(code == 0 and value.strip() == canary, "keyring_roundtrip_failed")
        files = list((root / "data/keyrings").glob("*.keyring"))
        require(bool(files) and all(p.is_file() and p.stat().st_mode & 0o077 == 0 for p in files), "keyring_permissions_failed")
        require(all(canary not in p.read_bytes() for p in files for canary in canaries), "plaintext_canary_found")
        await close_owned(keyring)
        keyring = None
        keyring = await start_keyring(root, env, password)
        for key, canary in zip(keys, canaries):
            code, value = await lookup(key)
            require(code == 0 and value.strip() == canary, "keyring_restart_failed")
        # The actual Codex logout operation must remove only this profile's
        # synthetic item. It cannot see the real user's bus/home or credentials.
        code, _ = await command([binary, "-c", 'cli_auth_credentials_store="keyring"',
                                 "-c", 'forced_login_method="chatgpt"', "logout"], env, root)
        require(code == 0, "codex_namespace_delete_failed")
        code, value = await lookup(keys[0])
        require(code != 0 and not value, "codex_namespace_not_removed")
        code, value = await lookup(keys[1])
        require(code == 0 and value.strip() == canaries[1], "other_namespace_changed")
        unavailable = {**env, "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + str(root / "run/absent")}
        code, _ = await command([binary, "-c", 'cli_auth_credentials_store="keyring"', "logout"], unavailable, root)
        require(code != 0, "unavailable_keyring_not_rejected")
        require(not list(root.rglob("auth.json")), "unexpected_file_credentials")
        return {"synthetic_roundtrip": True, "encrypted_persistence_restart": True,
                "profile_scoped_codex_logout": True, "other_profile_preserved": True,
                "unavailable_bus_rejected": True, "no_file_credentials": True}
    finally:
        try:
            await close_owned(keyring)
        finally:
            await close_owned(bus)


FILE_CHECK = """import errno,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);result={'read':p.read_text()=='synthetic-original','denied':False}
try:p.write_text('synthetic-modified')
except OSError as e:result['denied']=e.errno in (errno.EPERM,errno.EACCES,errno.EROFS)
print(json.dumps(result))
"""
NETWORK_CHECK = """import errno,json,socket,sys
family=socket.AF_INET6 if sys.argv[1]=='::1' else socket.AF_INET
kind=socket.SOCK_DGRAM if sys.argv[3]=='udp' else socket.SOCK_STREAM
s=None;blocked=False
try:
 s=socket.socket(family,kind);s.settimeout(1)
 s.connect((sys.argv[1],int(sys.argv[2])))
 if kind==socket.SOCK_DGRAM:s.send(b'probe');s.recv(32)
except OSError as e:blocked=isinstance(e,TimeoutError) or e.errno in (errno.EPERM,errno.EACCES,errno.ENETUNREACH,errno.EHOSTUNREACH,errno.ECONNREFUSED)
finally:
 if s:s.close()
print(json.dumps({'blocked':blocked}))
"""


async def sandbox_command(binary, root, script, args):
    # Exact pinned standalone CLI defaults are explicit here. App Server's
    # command/exec and model-facing inventory need their own later checks.
    code, output = await command([binary, "-c", 'sandbox_mode="read-only"', "sandbox", "--",
                                  "/usr/bin/python3", "-c", script, *args], environment(root), root)
    require(code == 0, "sandbox_command_failed")
    try:
        return json.loads(output)
    except (ValueError, UnicodeError):
        raise InspectionFailure("sandbox_output_rejected") from None


async def network_probe(binary, root, address, udp):
    received = []
    server = None
    family = socket.AF_INET6 if address == "::1" else socket.AF_INET
    class Datagram(asyncio.DatagramProtocol):
        def connection_made(self, transport): self.transport = transport
        def datagram_received(self, data, peer):
            received.append(True)
            self.transport.sendto(b"ack", peer)
    def connected(reader, writer):
        received.append(True)
        writer.close()
    try:
        loop = asyncio.get_running_loop()
        if udp:
            server, _ = await loop.create_datagram_endpoint(Datagram, local_addr=(address, 0), family=family)
            port = server.get_extra_info("sockname")[1]
            with socket.socket(family, socket.SOCK_DGRAM) as client:
                client.setblocking(False)
                await loop.sock_sendto(client, b"control", (address, port))
                data, _ = await asyncio.wait_for(loop.sock_recvfrom(client, 32), 2)
                require(data == b"ack", "network_control_failed")
        else:
            server = await asyncio.start_server(connected, address, 0, family=family)
            port = server.sockets[0].getsockname()[1]
            _, writer = await asyncio.open_connection(address, port)
            writer.close()
            await writer.wait_closed()
        await asyncio.sleep(0)
        require(bool(received), "network_control_not_observed")
        received.clear()
        result = await sandbox_command(binary, root, NETWORK_CHECK, [address, str(port), "udp" if udp else "tcp"])
        await asyncio.sleep(0)
        require(result == {"blocked": True} and not received, "sandbox_network_not_blocked")
        return {"host_control_observed": True, "sandbox_connection_observed": False, "denied": True}
    finally:
        if server:
            server.close()
            if not udp: await server.wait_closed()


async def probe(binary, parent):
    reviewed_binary(binary)
    report = {"status": "boundaries_verified_review_required", "authentication_requested": False,
              "inference_requested": False, "production_qualified": False}
    # Linux Unix-domain socket paths are limited to 107 bytes, including the
    # keyring daemon's own control suffix. Keep the owned basename short.
    with tempfile.TemporaryDirectory(prefix="b-", dir=parent) as directory:
        root = Path(directory)
        for name in ("config", "data", "cache", "run", "tmp", "codex-a", "codex-b", "run/keyring"):
            (root / name).mkdir(mode=0o700)
        try:
            report["stage"] = "keyring"
            report["keyring"] = await keyring_probe(binary, root)
            report["stage"] = "file"
            canary = root / "synthetic-canary"
            canary.write_text("synthetic-original")
            result = await sandbox_command(binary, root, FILE_CHECK, [str(canary)])
            require(result == {"read": True, "denied": True} and canary.read_text() == "synthetic-original", "sandbox_write_not_blocked")
            report["file"] = result
            report["network"] = {}
            for address in ("127.0.0.1", "::1"):
                for udp in (False, True):
                    name = address + ("/udp" if udp else "/tcp")
                    report["stage"] = name
                    report["network"][name] = await network_probe(binary, root, address, udp)
            require(not list(root.rglob("auth.json")), "unexpected_file_credentials")
            report["stage"] = "complete"
        except InspectionFailure as exc:
            report["status"] = str(exc)
    reviewed_binary(binary)
    report["disposable_workspace_removed"] = not root.exists()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--workspace-parent", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(sys.platform == "linux" and "microsoft-standard-wsl2" in os.uname().release.lower(), "wsl2_required")
        require(sys.version_info >= (3, 11), "python_3_11_required")
        parent = args.workspace_parent
        require(parent.is_absolute() and parent.is_dir() and not str(parent).startswith("/mnt/")
                and not any(p.is_symlink() for p in (parent, *parent.parents)), "linux_workspace_required")
        require(len(os.fsencode(parent)) <= 75, "unix_socket_parent_too_long")
        async def bounded_probe():
            return await asyncio.wait_for(probe(args.binary, parent), 60)
        report = asyncio.run(bounded_probe())
        code = 0 if report["status"] == "boundaries_verified_review_required" else 2
    except InspectionFailure as exc:
        report, code = {"status": str(exc), "production_qualified": False}, 2
    except (Exception, KeyboardInterrupt):
        report, code = {"status": "boundary_probe_unavailable", "production_qualified": False}, 2
    print(json.dumps(report, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
