"""Bounded, single-reader Codex JSON-RPC transport with ordered notifications."""
from __future__ import annotations

import asyncio
import json
from collections import deque
from pathlib import Path

from backend.app.runtime_base import RuntimeFailure, executable_command, process_options, provider_environment


class CodexRPC:
    def __init__(self, profile: Path, workspace: Path, *, allow_browsing: bool = True):
        self.profile, self.workspace = profile, workspace
        self.allow_browsing = allow_browsing
        self.process = None
        self.sequence = 0
        self.pending = deque()

    async def open(self):
        self.profile.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(parents=True, exist_ok=True)
        environment = {**provider_environment(), "CODEX_HOME": str(self.profile.resolve())}
        try:
            self.process = await asyncio.create_subprocess_exec(
                *executable_command("codex"), "app-server", "--stdio",
                "-c", 'web_search="live"' if self.allow_browsing else 'web_search="disabled"', "-c", "features.shell_tool=false",
                "-c", "features.unified_exec=false", "-c", 'forced_login_method="chatgpt"',
                "-c", "mcp_servers={}", cwd=self.workspace, env=environment,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, limit=2_000_000, **process_options())
            await self.request("initialize", {"clientInfo": {"name": "learn_the_ticker", "title": "Learn the Ticker", "version": "0.2.0"}})
            await self.send({"method": "initialized", "params": {}})
        except BaseException:
            await self.close()
            raise

    async def send(self, message: dict):
        try:
            self.process.stdin.write((json.dumps(message) + "\n").encode())
            await self.process.stdin.drain()
        except (OSError, AttributeError) as exc:
            raise RuntimeFailure("Codex disconnected; reconnect before retrying.") from exc

    async def receive(self) -> dict:
        try:
            line = await self.process.stdout.readline()
            if not line:
                raise RuntimeFailure("Codex disconnected; reconnect before retrying.")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("object required")
            return value
        except (ValueError, TypeError, OSError) as exc:
            raise RuntimeFailure("Codex returned invalid or oversized protocol output.") from exc

    async def request(self, method: str, params: dict, timeout: float = 30) -> dict:
        self.sequence += 1
        expected = self.sequence
        try:
            async with asyncio.timeout(timeout):
                await self.send({"id": expected, "method": method, "params": params})
                while True:
                    message = await self.receive()
                    if message.get("id") == expected and "method" not in message:
                        if "error" in message or not isinstance(message.get("result"), dict):
                            raise RuntimeFailure("Codex rejected the request. Check runtime version, authentication and permissions.")
                        return message["result"]
                    if "id" in message or not isinstance(message.get("method"), str):
                        raise RuntimeFailure("Codex requested unsupported access or returned an unexpected response.")
                    if len(self.pending) >= 256:
                        raise RuntimeFailure("Codex exceeded the pending event limit.")
                    self.pending.append(message)
        except TimeoutError as exc:
            raise RuntimeFailure("Codex request timed out. Reconnect before retrying.") from exc

    async def event(self) -> dict:
        return self.pending.popleft() if self.pending else await self.receive()

    async def close(self):
        process, self.process = self.process, None
        if process and process.returncode is None:
            try:
                process.stdin.close()
                await asyncio.wait_for(process.wait(), 3)
            except (OSError, TimeoutError):
                if process.returncode is None:
                    process.kill()
                    await process.wait()
