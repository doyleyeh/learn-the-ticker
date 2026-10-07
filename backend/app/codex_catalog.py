"""Bounded same-model metadata, privately narrowed for one owned process lifetime."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import tempfile

from backend.app.codex_policy import policy_arguments, prepare_workspace, require_plain_path
from backend.app.owned_process import close_owned, launch_owned
from backend.app.runtime_base import RuntimeFailure, executable_command, provider_environment


LIMIT = 2_000_000
# Serialized ModelInfo keys reviewed for the pinned protocol. A new field could
# enable a tool: do not silently pass unknown metadata through to the provider.
MODEL_KEYS = frozenset("""additional_speed_tiers apply_patch_tool_type availability_nux
available_access_programs base_instructions comp_hash context_window default_reasoning_level
default_reasoning_summary default_verbosity description display_name effective_context_window_percent
experimental_supported_tools include_apps_usage_instructions include_plugin_usage_instructions
include_skills_usage_instructions input_modalities max_context_window model_messages
multi_agent_reasoning_effort multi_agent_version node_repl_auto_review_required node_repl_disabled
priority service_tiers shell_type slug support_verbosity supported_in_api supported_reasoning_levels
supports_experimental_context supports_image_detail_original supports_reasoning_effort_updates
supports_search_tool tool_mode truncation_policy upgrade use_responses_lite visibility
web_search_tool_type""".split())
RESTRICTIONS = {
    "tool_mode": "direct", "shell_type": "disabled", "apply_patch_tool_type": None,
    "experimental_supported_tools": [], "supports_search_tool": False,
    "multi_agent_version": "disabled", "node_repl_disabled": True,
}
ERROR = "Codex selected-model tool metadata could not be verified. No inference was started."


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError("duplicate field")
        result[key] = value
    return result


def restricted_metadata(raw: bytes, selected: str) -> bytes:
    try:
        if not 0 < len(raw) <= LIMIT: raise ValueError()
        catalog = json.loads(raw, object_pairs_hook=unique_object)
        rows = catalog.get("models")
        if not isinstance(rows, list) or not 1 <= len(rows) <= 200: raise ValueError()
        seen, matches = set(), []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("slug"), str): raise ValueError()
            if row["slug"] in seen: raise ValueError()
            seen.add(row["slug"])
            if row["slug"] == selected: matches.append(row)
        if len(matches) != 1: raise ValueError()
        model = matches[0]
        if set(model) != MODEL_KEYS: raise ValueError()
        if (model["tool_mode"] not in (None, "direct", "code_mode", "code_mode_only")
                or model["shell_type"] not in ("disabled", "shell_command", "unified_exec")
                or model["apply_patch_tool_type"] not in (None, "freeform", "function")
                or model["multi_agent_version"] not in (None, "disabled", "v1", "v2")
                or type(model["supports_search_tool"]) is not bool
                or type(model["node_repl_disabled"]) is not bool
                or model["use_responses_lite"] is not True
                or model["web_search_tool_type"] != "text_and_image"
                or not isinstance(model["experimental_supported_tools"], list)
                or not all(isinstance(t, str) for t in model["experimental_supported_tools"])):
            raise ValueError()
        # Preserve every other metadata value, including identity, prompt and limits.
        return json.dumps({"models": [{**model, **RESTRICTIONS}]}, allow_nan=False,
                          separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, AttributeError, RecursionError) as exc:
        raise RuntimeFailure(ERROR) from exc


async def read_metadata(profile: Path, workspace: Path, selected: str) -> bytes:
    """Diagnostic only: same isolated policy, no model turn, bounded memory output."""
    prepare_workspace(profile, workspace)
    process = None
    try:
        # This exact debug subcommand rejects --strict-config. The owning RPC has
        # already verified strict startup; the actual inference server keeps it.
        args = policy_arguments(False)[1:]
        process = await launch_owned(*executable_command("codex"), *args, "debug", "models",
            cwd=workspace, env={**provider_environment(), "CODEX_HOME": str(profile.resolve())},
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)
        async with asyncio.timeout(45):
            raw = bytearray()
            while chunk := await process.stdout.read(LIMIT + 1 - len(raw)):
                raw.extend(chunk)
                if len(raw) > LIMIT: raise ValueError()
            await process.wait()
        if process.returncode != 0: raise ValueError()
        return restricted_metadata(raw, selected)
    except (OSError, ValueError, TimeoutError) as exc:
        raise RuntimeFailure(ERROR) from exc
    finally:
        await close_owned(process, grace=1)


class RestrictedCatalog:
    def __init__(self, payload: bytes, selected: str):
        self.model = selected
        self.path = None
        self.identity = None
        self.digest = hashlib.sha256(payload).digest()
        try:
            require_plain_path(Path(tempfile.gettempdir()).absolute())
            fd, name = tempfile.mkstemp(prefix="ltt-codex-catalog-", suffix=".json")
            self.path = Path(name)
            with os.fdopen(fd, "wb") as file:
                stat = os.fstat(file.fileno())
                self.identity = (stat.st_dev, stat.st_ino)
                file.write(payload)
            self.verify()
        except BaseException:
            self.close()
            raise

    def verify(self):
        try:
            require_plain_path(self.path.absolute())
            with self.path.open("rb") as file:
                stat = os.fstat(file.fileno())
                raw = file.read(LIMIT + 1)
            if (not self.path.is_file() or (stat.st_dev, stat.st_ino) != self.identity
                    or len(raw) > LIMIT or hashlib.sha256(raw).digest() != self.digest):
                raise ValueError()
        except (OSError, ValueError, AttributeError) as exc:
            raise RuntimeFailure("Codex restricted catalog changed or is unavailable. Research stopped.") from exc

    def close(self):
        if self.path is None: return
        try:
            # Never recursively delete, follow a replacement link, or remove a
            # different file that has replaced our temporary artifact.
            require_plain_path(self.path.absolute())
            stat = self.path.stat()
            if (stat.st_dev, stat.st_ino) != self.identity:
                raise RuntimeFailure("Codex restricted catalog was replaced; cleanup requires review.")
            self.path.unlink()
        except FileNotFoundError:
            pass
