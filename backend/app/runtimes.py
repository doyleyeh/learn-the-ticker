"""Provider transports. No shell commands, browser automation or API-key fallback."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from backend.app.contracts import RuntimeCapabilities, RuntimeEvent


from backend.app.runtime_base import AIRuntime, RuntimeFailure, executable_command, provider_environment, process_options
from backend.app.codex_runtime import CodexRuntime


def normalize_cli_event(provider: str, raw: dict, run_id: str) -> RuntimeEvent | None:
    kind = raw.get("type")
    if provider == "gemini" and kind == "message" and raw.get("role") == "assistant":
        return RuntimeEvent(run_id=run_id, kind="message.delta", text=str(raw.get("content", "")))
    if provider == "claude" and kind == "assistant":
        text = "".join(b.get("text", "") for b in raw.get("message", {}).get("content", []) if b.get("type") == "text")
        return RuntimeEvent(run_id=run_id, kind="message.delta", text=text)
    if kind in ("tool_use", "tool_result"):
        return RuntimeEvent(run_id=run_id, kind="tool.started", text="Provider tool activity")
    if kind == "error" or (kind == "result" and (raw.get("is_error") or raw.get("status") == "error")):
        return RuntimeEvent(run_id=run_id, kind="run.failed", text="Provider failed. Check authentication, quota and version; no fallback was attempted.")
    # Never expose thinking/reasoning, tool arguments, environment or raw diagnostics.
    return None


class CLIRuntime(AIRuntime):
    def __init__(self, provider: str):
        self.provider = provider

    async def stream(self, prompt, run_id, workspace, model=None, *, allow_browsing=True):
        await self.require_generation(allow_browsing=allow_browsing)
        command = executable_command(self.provider)
        if self.provider == "claude":
            # Restricted/safe mode prevents user hooks, plugins and project customizations
            # from expanding this cached-evidence connection's permissions.
            args = ["--restricted", "--safe-mode", "-p", "--output-format", "stream-json", "--verbose", "--tools", "", "--disallowedTools", "mcp__*", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "", "--no-session-persistence"]
            status = await asyncio.create_subprocess_exec(*command, "auth", "status", "--json", cwd=workspace, env=provider_environment(), **process_options(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            try:
                output, _ = await asyncio.wait_for(status.communicate(), 10)
                auth = json.loads(output)
                if status.returncode or auth.get("authMethod") != "claude.ai" or not auth.get("loggedIn"):
                    raise RuntimeFailure("Connect Claude Code with subscription authentication; API-key billing is not enabled.")
            except (ValueError, asyncio.TimeoutError) as exc:
                raise RuntimeFailure("Claude subscription authentication could not be verified.") from exc
            finally:
                if status.returncode is None:
                    status.kill()
                    await status.wait()
        else:
            # Gemini safe tool isolation still needs version-specific qualification. Fail closed
            # rather than launch a CLI that can inherit unrestricted hooks or MCP servers.
            raise RuntimeFailure("Gemini transport is awaiting isolated-tool policy qualification; use cached material until connected safely.")
        if model:
            args += ["--model", model]
        process = await asyncio.create_subprocess_exec(*command, *args, cwd=workspace, env=provider_environment(), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=2_000_000, **process_options())
        try:
            process.stdin.write(prompt.encode())
            await process.stdin.drain()
            process.stdin.close()
            async with asyncio.timeout(180):
                async for line in process.stdout:
                    try:
                        event = normalize_cli_event(self.provider, json.loads(line), run_id)
                    except (ValueError, TypeError, AttributeError) as exc:
                        raise RuntimeFailure("Provider returned malformed output") from exc
                    if event:
                        yield event
                        if event.kind == "run.failed":
                            return
                await process.wait()
                if process.returncode:
                    raise RuntimeFailure("Provider exited unsuccessfully. Reconnect or check quota.")
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()


def runtimes(profile: Path | None = None) -> dict[str, AIRuntime]:
    return {"codex": CodexRuntime(profile), "gemini": CLIRuntime("gemini"), "claude": CLIRuntime("claude")}
