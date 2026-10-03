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

from backend.app.contracts import RuntimeCapabilities, RuntimeEvent, RuntimeModelCatalog
from backend.app.runtime_policy import apply_qualification


def process_options() -> dict:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


class RuntimeFailure(Exception):
    pass


def runtime_version(provider: str, raw: bytes) -> str | None:
    """Accept a bounded, recognized version line; preserve prerelease/build identity."""
    version = r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z][0-9A-Za-z.-]*)?(?:\+[0-9A-Za-z][0-9A-Za-z.-]*)?"
    patterns = {
        "codex": rf"(?:codex-cli\s+)?(?P<version>{version})",
        "gemini": rf"(?:gemini(?:-cli)?\s+)?(?P<version>{version})",
        "claude": rf"(?P<version>{version})(?: \(Claude Code\))?",
    }
    try:
        match = re.fullmatch(patterns[provider], raw.decode("utf-8").strip())
    except (KeyError, UnicodeError):
        return None
    return match.group("version") if match else None


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

    async def models(self) -> RuntimeModelCatalog:
        return RuntimeModelCatalog(provider=self.provider)

    async def check(self) -> RuntimeCapabilities:
        process = None
        result = RuntimeCapabilities(provider=self.provider)
        try:
            command = executable_command(self.provider)
            process = await asyncio.create_subprocess_exec(*command, "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, env=provider_environment(), limit=8192, **process_options())
            result.installed = True
            async with asyncio.timeout(10):
                output = await process.stdout.read(4097)
                if len(output) > 4096:
                    raise RuntimeFailure("Provider version output exceeds the allowed size")
                # read() may return before EOF; collect the remainder with the same bound.
                while chunk := await process.stdout.read(4097 - len(output)):
                    output += chunk
                    if len(output) > 4096:
                        raise RuntimeFailure("Provider version output exceeds the allowed size")
                await process.wait()
            result.version = runtime_version(self.provider, output) if process.returncode == 0 else None
            return apply_qualification(result)
        except asyncio.TimeoutError:
            result.reason = "Provider version check timed out. No capability was enabled."
            return result
        except (OSError, RuntimeFailure):
            result.reason = "Provider version could not be verified. Check the runtime installation; no capability was enabled."
            return result
        finally:
            if process and process.returncode is None:
                process.kill()
                await process.wait()

    async def require_generation(self, *, allow_browsing: bool):
        result = await self.check()
        if not result.installed or result.qualification != "live" or result.authentication != "authenticated" or not result.generation:
            raise RuntimeFailure(result.reason or "This subscription connection is not qualified for generation.")
        if allow_browsing and not result.browsing:
            raise RuntimeFailure("This connection is qualified for cached/imported evidence only. Browsing is unavailable.")

    @abstractmethod
    async def stream(self, prompt: str, run_id: str, workspace: Path, model: str | None = None, *, allow_browsing: bool = True) -> AsyncIterator[RuntimeEvent]:
        yield
