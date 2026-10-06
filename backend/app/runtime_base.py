"""Shared provider process boundaries; no API-key fallback."""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator

from backend.app.contracts import RuntimeCapabilities, RuntimeEvent, RuntimeModelCatalog
from backend.app.runtime_policy import apply_qualification
from backend.app.owned_process import launch_owned, close_owned


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
        shim_directory = Path(binary).parent
        modules = shim_directory.parent if shim_directory.name == ".bin" and shim_directory.parent.name == "node_modules" else shim_directory / "node_modules"
        entry = modules / (package or "missing")
        if provider == "gemini":
            root = modules / "@google/gemini-cli"
            try:
                manifest = root / "package.json"
                if manifest.stat().st_size > 64 * 1024:
                    raise ValueError("Package metadata exceeds bounds")
                data = json.loads(manifest.read_text(encoding="utf-8"))
                declared = data.get("bin", {}).get("gemini")
                if data.get("name") != "@google/gemini-cli" or declared not in ("dist/index.js", "bundle/gemini.js"):
                    raise ValueError("Unreviewed Gemini package entry")
                entry = root / declared
                if not entry.resolve().is_relative_to(root.resolve()):
                    raise ValueError("Gemini entry leaves its package")
            except (OSError, ValueError, AttributeError, TypeError, RecursionError) as exc:
                raise RuntimeFailure("Gemini package entry could not be verified; reinstall the official runtime.") from exc
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
            process = await launch_owned(*command, "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, env=provider_environment(), limit=8192)
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
            await close_owned(process)

    async def require_generation(self, *, allow_browsing: bool):
        result = await self.check()
        if not result.installed or result.qualification != "live" or result.authentication != "authenticated" or not result.generation:
            raise RuntimeFailure(result.reason or "This subscription connection is not qualified for generation.")
        if allow_browsing and not result.browsing:
            raise RuntimeFailure("This connection is qualified for cached/imported evidence only. Browsing is unavailable.")

    @abstractmethod
    async def stream(self, prompt: str, run_id: str, workspace: Path, model: str | None = None, *, allow_browsing: bool = True) -> AsyncIterator[RuntimeEvent]:
        yield
