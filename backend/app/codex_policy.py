"""App-owned Codex configuration; prompt instructions are not a permission boundary."""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import tomllib

from backend.app.runtime_base import RuntimeFailure


ROOT_MARKER = ".ltt-runtime-root"
SANDBOX_CONFIG = {"windows": {"sandbox": "elevated"}}
# Exact-version source confirms shell_tool controls both exec_command and write_stdin.
# unified_exec=false alone is NOT an execution restriction in this runtime.
DISABLED_FEATURES = (
    "shell_tool", "shell_snapshot", "shell_snapshot_v2", "unified_exec_zsh_fork",
    "hooks", "plugin_hooks", "plugins", "apps", "remote_plugin", "remote_control",
    "multi_agent", "multi_agent_v2", "apply_patch_freeform", "browser_use",
    "browser_use_external", "browser_use_full_cdp_access", "computer_use",
    "image_generation", "skill_search", "skill_mcp_dependency_install", "goals",
    "code_mode", "code_mode_host", "code_mode_only", "js_repl", "daemon_auto_start",
    "view_image", "sleep_tool", "tool_suggest", "tool_call_mcp_elicitation",
    "auth_elicitation", "in_app_browser", "in_app_local_automation",
    "workspace_dependencies", "worktrees", "guardian_approval", "guardianv2",
    "memories", "request_permissions_tool", "request_rule", "deferred_executor",
    "token_budget", "send_message_to_user_async", "api_key_model_discovery", "current_time_reminder",
)

TOOL_FLAGS = {"update_plan": {"enabled": False}, "experimental_request_user_input": {"enabled": False}}


def exact_settings(value, expected):
    if type(value) is not type(expected): return False
    if isinstance(expected, dict):
        return value.keys() == expected.keys() and all(exact_settings(value[k], v) for k, v in expected.items())
    return value == expected


def policy_config(allow_browsing: bool, catalog: Path | None = None) -> dict:
    return {
        **{f"features.{name}": False for name in DISABLED_FEATURES if name not in {"code_mode", "code_mode_host"}},
        # Model metadata can select code_mode_only even when its feature is off.
        # Expose only the permitted web namespace directly; keep the execution
        # service disabled. In this pinned version, setting disable_in_process_fallback
        # true also selects a process-owned execution service, so require false.
        "features.code_mode.enabled": False,
        "features.code_mode.direct_only_tool_namespaces": ["web"] if allow_browsing else [],
        "features.code_mode_host.enabled": False,
        "features.code_mode_host.disable_in_process_fallback": False,
        "features.skip_host_skill_discovery": True,
        "agents.enabled": False,
        "tools.update_plan.enabled": False,
        "tools.experimental_request_user_input.enabled": False,
        **({"model_catalog_json": str(catalog), "features.request_permissions_tool": allow_browsing} if catalog else {}),
        "web_search": "live" if allow_browsing else "disabled",
        "forced_login_method": "chatgpt", "cli_auth_credentials_store": "keyring",
        "approval_policy": "on-request", "approvals_reviewer": "user",
        "sandbox_mode": "read-only", "allow_login_shell": False,
        **({"windows.sandbox": "elevated"} if os.name == "nt" else {}),
        "project_root_markers": [ROOT_MARKER], "project_doc_max_bytes": 0,
        "skills.include_instructions": False, "skills.bundled.enabled": False,
        "mcp_servers": {}, "plugins": {}, "model_providers": {}, "model_provider": "openai",
        "notify": [], "analytics.enabled": False, "feedback.enabled": False,
        "otel.exporter": "none", "otel.trace_exporter": "none", "otel.metrics_exporter": "none",
        "otel.log_user_prompt": False, "check_for_update_on_startup": False,
    }


async def require_execution_sandbox(rpc):
    if os.name == "nt":
        response = await rpc.request("windowsSandbox/readiness", {})
        if response.get("status") != "ready":
            raise RuntimeFailure("The dedicated Windows sandbox needs setup before inference. No setup or fallback was started.")


def policy_arguments(allow_browsing: bool, catalog: Path | None = None) -> list[str]:
    args = ["--strict-config"]
    for key, value in policy_config(allow_browsing, catalog).items():
        args.extend(["-c", f"{key}={json.dumps(value, separators=(',', ':'))}"])
    return args


def system_config_directory() -> Path:
    if os.name != "nt":
        return Path("/etc/codex")
    # CSIDL_COMMON_APPDATA resolves ProgramData through Windows, not caller input.
    buffer = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 0x23, None, 0, buffer) != 0:
        raise RuntimeFailure("Cannot verify the system Codex configuration location.")
    return Path(buffer.value) / "OpenAI" / "Codex"


def require_plain_path(path: Path):
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, "is_junction", lambda: False)():
            raise RuntimeFailure("Codex profile and workspace must not use linked directories.")


def prepare_workspace(profile: Path, workspace: Path):
    """Refuse custom startup configuration without overwriting any user files."""
    try:
        for directory in (profile, workspace):
            require_plain_path(directory.absolute())
        sandbox_config = profile / "config.toml"
        require_plain_path(sandbox_config.absolute())
        if sandbox_config.exists():
            try:
                if (os.name != "nt" or not sandbox_config.is_file() or sandbox_config.stat().st_size > 4096
                        or tomllib.loads(sandbox_config.read_text(encoding="utf-8")) != SANDBOX_CONFIG):
                    raise ValueError()
            except (ValueError, UnicodeError):
                raise RuntimeFailure("Custom Codex configuration is unsupported in the isolated connection. No files were changed.") from None
        system = system_config_directory()
        candidates = [profile / "hooks.json", profile / "auth.json",
                      workspace / "config.toml", workspace / ".codex" / "config.toml",
                      workspace / ".codex" / "hooks.json"]
        candidates += [system / name for name in ("config.toml", "requirements.toml", "managed_config.toml", "hooks.json")]
        for path in candidates:
            require_plain_path(path.absolute())
            if path.exists():
                raise RuntimeFailure("Custom Codex configuration or file credentials are unsupported in the isolated connection. No files were changed.")
        profile.mkdir(parents=True, exist_ok=True)
        workspace.mkdir(parents=True, exist_ok=True)
        marker = workspace / ROOT_MARKER
        require_plain_path(marker.absolute())
        if marker.exists() and (not marker.is_file() or marker.stat().st_size):
            raise RuntimeFailure("The Codex workspace boundary is invalid.")
        marker.touch(exist_ok=True)
    except OSError as exc:
        raise RuntimeFailure("The isolated Codex workspace could not be verified.") from exc


def validate_config(response: dict, allow_browsing: bool, profile: Path | None = None, catalog: Path | None = None):
    config, layers = response.get("config"), response.get("layers")
    if not isinstance(config, dict) or not isinstance(layers, list) or not layers:
        raise RuntimeFailure("Codex did not report its effective configuration.")
    for key, expected in policy_config(allow_browsing, catalog).items():
        if key.startswith("tools."):
            continue  # These fields are verified in the strict sessionFlags layer below.
        value = config
        for part in key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if type(value) is not type(expected) or value != expected:
            raise RuntimeFailure("Codex effective configuration does not enforce the application policy.")
    # Session flags are ours. Do not inherit even apparently harmless instructions,
    # endpoints or profiles from other layers; future versions may interpret them.
    for layer in layers:
        if not isinstance(layer, dict) or not isinstance(layer.get("name"), dict):
            raise RuntimeFailure("Codex returned an invalid configuration layer.")
        # Provider setup persists exactly this setting. It cannot contribute tools,
        # credentials, instructions, or settings from another profile.
        sandbox_layer = False
        if os.name == "nt" and profile and layer["name"].get("type") == "user" and layer.get("config") == SANDBOX_CONFIG:
            try:
                file = layer["name"].get("file")
                sandbox_layer = isinstance(file, str) and Path(file).resolve() == (profile / "config.toml").resolve()
            except (OSError, ValueError):
                pass
        if layer["name"].get("type") != "sessionFlags" and layer.get("config") != {} and not sandbox_layer:
            raise RuntimeFailure("Codex inherited configuration outside the isolated connection.")
    flags = [layer for layer in layers if layer["name"].get("type") == "sessionFlags"]
    if (len(flags) != 1 or not isinstance(flags[0].get("config"), dict)
            or not exact_settings(flags[0]["config"].get("tools"), TOOL_FLAGS)
            or not exact_settings(flags[0]["config"].get("agents"), {"enabled": False})):
        raise RuntimeFailure("Codex strict session tool settings could not be verified.")
    # Pinned normalized Config contains only legacy tools.web_search=null; the
    # plan/input switches are absent. If returned they must agree. Agents includes
    # provider defaults; its effective enabled flag is
    # checked above and the strict session layer forbids extra agent settings.
    if not (exact_settings(config.get("tools"), {"web_search": None})
            or exact_settings(config.get("tools"), TOOL_FLAGS)):
        raise RuntimeFailure("Codex effective tool settings do not enforce the application policy.")


def validate_features(response: dict, *, request_permissions: bool = False):
    rows = response.get("data")
    if not isinstance(rows, list) or response.get("nextCursor") is not None or len(rows) > 256:
        raise RuntimeFailure("Codex feature policy could not be verified completely.")
    features = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or type(row.get("enabled")) is not bool or row["name"] in features:
            raise RuntimeFailure("Codex returned an invalid feature policy.")
        features[row["name"]] = row["enabled"]
    if any(features.get(name) is not (request_permissions if name == "request_permissions_tool" else False) for name in DISABLED_FEATURES):
        raise RuntimeFailure("Codex reports a prohibited or unrecognized tool capability.")


def thread_parameters(workspace: Path, model: str | None = None) -> dict:
    params = {"cwd": str(workspace.resolve()), "approvalPolicy": "on-request",
              "approvalsReviewer": "user", "sandbox": "read-only", "ephemeral": True,
              "allowProviderModelFallback": False}
    if model:
        params["model"] = model
    return params


def validate_thread(response: dict, workspace: Path) -> str:
    thread = response.get("thread")
    sandbox = response.get("sandbox")
    roots = response.get("runtimeWorkspaceRoots")
    try:
        workspace_matches = (isinstance(response.get("cwd"), str)
            and Path(response["cwd"]).resolve() == workspace.resolve()
            and isinstance(roots, list) and len(roots) == 1 and isinstance(roots[0], str)
            and Path(roots[0]).resolve() == workspace.resolve())
    except (OSError, ValueError):
        workspace_matches = False
    if (not isinstance(thread, dict) or not isinstance(thread.get("id"), str) or not 1 <= len(thread["id"]) <= 200
            or not isinstance(sandbox, dict) or sandbox.get("type") != "readOnly" or sandbox.get("networkAccess") is not False
            or response.get("approvalPolicy") != "on-request" or response.get("approvalsReviewer") != "user"
            or response.get("modelProvider") != "openai" or response.get("instructionSources") != []
            or not workspace_matches):
        raise RuntimeFailure("Codex thread permissions or instruction isolation could not be verified.")
    return thread["id"]
