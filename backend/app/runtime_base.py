"""Shared provider process boundaries; no API-key fallback."""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator

from backend.app.contracts import RuntimeCapabilities, RuntimeEvent


def process_options() -> dict:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


class RuntimeFailure(Exception):
    pass


def provider_environment() -> dict[str, str]:
    # Pass only process prerequisites; never leak the app's DB/session credentials or API keys.
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL"}
    return {k: v for k, v in os.environ.items() if k.upper() in allowed}


def executable_command(provider: str) -> list[str]:
    binary = shutil.which(provider)
    if not binary:
        raise RuntimeFailure("Provider runtime is not installed. Complete provider setup first.")
    if Path(binary).suffix.lower() in (".cmd", ".bat", ".ps1"):
        # npm's Windows shim is a shell script; resolve the known package entry point instead.
        package = {"codex": "@openai/codex/bin/codex.js", "gemini": "@google/gemini-cli/dist/index.js", "claude": "@anthropic-ai/claude-code/cli.js"}.get(provider)
        entry = Path(binary).parent / "node_modules" / (package or "missing")
        node = shutil.which("node")
        if not node or not entry.is_file():
            raise RuntimeFailure("A compatible native executable or Node runtime is required.")
        return [node, str(entry)]
    return [binary]


class AIRuntime(ABC):
    provider: str

    async def check(self) -> RuntimeCapabilities:
        try:
            command = executable_command(self.provider)
            process = await asyncio.create_subprocess_exec(*command, "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, env=provider_environment(), **process_options())
            try:
                output, _ = await asyncio.wait_for(process.communicate(), 10)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise RuntimeFailure("Provider version check timed out")
            version = re.search(r"\d+\.\d+\.\d+", output.decode(errors="replace"))
            # Installed is not authenticated. The first successful subscription turn establishes readiness.
            available = process.returncode == 0 and bool(version)
            reason = "Gemini execution is disabled until isolated tool permissions are qualified." if self.provider == "gemini" else "Subscription authentication and compatibility require a live connection check."
            return RuntimeCapabilities(provider=self.provider, installed=process.returncode == 0, version=version.group() if version else None, generation=available and self.provider != "gemini", browsing=available and self.provider == "codex", approvals=available and self.provider == "codex", reason=reason)
        except (OSError, RuntimeFailure):
            return RuntimeCapabilities(provider=self.provider, reason="Install and authenticate the provider runtime using its official setup.")

    @abstractmethod
    async def stream(self, prompt: str, run_id: str, workspace: Path, model: str | None = None, *, allow_browsing: bool = True) -> AsyncIterator[RuntimeEvent]:
        yield
