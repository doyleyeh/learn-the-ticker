"""Bounded, single-reader Codex JSON-RPC transport with ordered notifications."""
from __future__ import annotations

import asyncio
import json
from collections import deque
from pathlib import Path

from backend.app.codex_policy import (policy_arguments, prepare_workspace, thread_parameters,
    validate_config, validate_features, validate_thread)
from backend.app.runtime_base import RuntimeFailure, executable_command, provider_environment
from backend.app.owned_process import launch_owned, close_owned


class CodexRPC:
    def __init__(self, profile: Path, workspace: Path, *, allow_browsing: bool = False):
        self.profile, self.workspace = profile, workspace
        self.allow_browsing = allow_browsing
        self.process = None
        self.sequence = 0
        self.pending = deque()

    async def open(self):
        prepare_workspace(self.profile, self.workspace)
        environment = {**provider_environment(), "CODEX_HOME": str(self.profile.resolve())}
        try:
            self.process = await launch_owned(
                *executable_command("codex"), "app-server", "--stdio",
                *policy_arguments(self.allow_browsing), cwd=self.workspace, env=environment,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, limit=2_000_000)
            await self.request("initialize", {"clientInfo": {"name": "learn_the_ticker", "title": "Learn the Ticker", "version": "0.2.0"}})
            await self.send({"method": "initialized", "params": {}})
            await self.verify_policy()
        except BaseException:
            await self.close()
            raise

    async def verify_policy(self):
        validate_config(await self.request("config/read", {"cwd": str(self.workspace.resolve()), "includeLayers": True}), self.allow_browsing)
        validate_features(await self.request("experimentalFeature/list", {"limit": 200}))

    async def start_thread(self, model: str | None = None) -> str:
        # Recheck immediately before creating a thread, without any inference.
        prepare_workspace(self.profile, self.workspace)
        await self.verify_policy()
        response = await self.request("thread/start", thread_parameters(self.workspace, model))
        thread_id = validate_thread(response, self.workspace)
        if model is not None and response.get("model") != model:
            raise RuntimeFailure("Codex changed the selected model. No inference or fallback was permitted.")
        validate_features(await self.request("experimentalFeature/list", {"limit": 200, "threadId": thread_id}))
        return thread_id

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
                    if type(message.get("id")) is int and message["id"] == expected and "method" not in message:
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

    async def wait_disconnected(self):
        # Process.wait can wait for descendants holding stdout open. Watch the
        # actual leader status so pending access reviews are withdrawn promptly.
        while self.process and self.process.returncode is None:
            await asyncio.sleep(.05)
        raise RuntimeFailure("Codex disconnected. Research stopped; retry explicitly after reconnecting.")

    async def interrupt(self, thread_id: str, turn_id: str):
        try:
            await self.request("turn/interrupt", {"threadId": thread_id, "turnId": turn_id}, timeout=2)
        except (RuntimeFailure, OSError):
            pass  # The owned process tree is closed even if the protocol is gone.

    async def close(self):
        process, self.process = self.process, None
        self.pending.clear()
        await close_owned(process, grace=1)
