#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("LTT_FORCE_COMPAT_FASTAPI", "1")

from backend.settings import build_cors_settings, build_lightweight_data_settings, build_persistence_settings


SCHEMA_VERSION = "local-deployment-env-smoke-v1"
BROWSER_ENV_FILES = ("apps/web/.env.example", "deploy/env/web.example.env")
SERVER_ENV_FILES = (".env.example", "deploy/env/api.example.env", "deploy/env/worker.example.env")
PLACEHOLDER_ENV_FILES = (*SERVER_ENV_FILES, *BROWSER_ENV_FILES)
BROWSER_SAFE_ENV_NAMES = ("NEXT_PUBLIC_API_BASE_URL",)
SERVER_ONLY_ENV_NAMES = (
    "DATABASE_URL",
    "OPENROUTER_API_KEY",
    "FMP_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "FINNHUB_API_KEY",
    "TIINGO_API_KEY",
    "EODHD_API_KEY",
)
API_REQUIRED_ENV_NAMES = (
    "PORT",
    "CORS_ALLOWED_ORIGINS",
    "DATABASE_URL",
    "DATA_POLICY_MODE",
    "LIGHTWEIGHT_LIVE_FETCH_ENABLED",
    "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED",
    "SEC_EDGAR_USER_AGENT",
    "LLM_PROVIDER",
    "LLM_LIVE_GENERATION_ENABLED",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_FREE_MODEL_ORDER",
)
WORKER_REQUIRED_ENV_NAMES = (
    "DATABASE_URL",
    "DATA_POLICY_MODE",
    "LIGHTWEIGHT_LIVE_FETCH_ENABLED",
    "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED",
    "SEC_EDGAR_USER_AGENT",
    "LLM_PROVIDER",
    "LLM_LIVE_GENERATION_ENABLED",
    "OPENROUTER_API_KEY",
)
ROOT_REQUIRED_ENV_NAMES = (
    "PORT",
    "CORS_ALLOWED_ORIGINS",
    "DATABASE_URL",
    "TOP500_UNIVERSE_MANIFEST_URI",
    "DATA_POLICY_MODE",
    "LIGHTWEIGHT_LIVE_FETCH_ENABLED",
    "LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED",
    "SEC_EDGAR_USER_AGENT",
    "LLM_PROVIDER",
    "LLM_LIVE_GENERATION_ENABLED",
    "OPENROUTER_API_KEY",
)
PROVIDER_KEY_ENV_NAMES = (
    "OPENROUTER_API_KEY",
    "FMP_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "FINNHUB_API_KEY",
    "TIINGO_API_KEY",
    "EODHD_API_KEY",
)
FORBIDDEN_OUTPUT_MARKERS = (
    "BEGIN PRIVATE KEY",
    "Bearer ",
    "Authorization:",
    "sk-",
    "xoxb-",
    "ghp_",
    "raw provider payload",
    "raw source text",
    "raw model reasoning",
)


def run_local_deployment_env_smoke(*, root: Path = ROOT, run_docker_config: bool = True) -> dict[str, Any]:
    checks = [
        _check_placeholder_env_files(root),
        _check_browser_env_secret_separation(root),
        _check_server_env_readiness(root),
        _check_settings_defaults(),
        _check_repo_local_scaffolding(root),
        _check_docker_compose_config(root, run_docker_config=run_docker_config),
    ]
    status_counts = Counter(check["status"] for check in checks)
    status = "blocked" if status_counts.get("blocked") else "pass"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reason_code": "local_deployment_env_smoke_passed" if status == "pass" else "local_deployment_env_smoke_blocked",
        "default_mode": "deterministic_repo_scaffold_inspection",
        "normal_ci_requires_live_calls": False,
        "production_services_started": False,
        "deployments_created": False,
        "live_provider_calls_attempted": False,
        "database_connections_opened": False,
        "secret_values_reported": False,
        "browser_startup_required": False,
        "local_services_required": False,
        "docker_daemon_required": False,
        "launch_or_public_deployment_approved": False,
        "production_ready": False,
        "source_approval_granted": False,
        "golden_asset_source_handoff_approved": False,
        "manifests_promoted": False,
        "generated_output_cache_promoted": False,
        "safe_diagnostics": {
            "safe_diagnostics_only": True,
            "env_var_names_reported_without_values": True,
            "secret_values_reported": False,
            "database_dsn_values_reported": False,
            "provider_payloads_reported": False,
            "raw_source_text_reported": False,
            "hidden_prompts_reported": False,
            "model_reasoning_reported": False,
            "service_account_json_reported": False,
        },
        "checks": checks,
        "status_counts": {
            "pass": int(status_counts.get("pass", 0)),
            "blocked": int(status_counts.get("blocked", 0)),
            "skipped": int(status_counts.get("skipped", 0)),
        },
    }
    marker_hits = _forbidden_output_marker_hits(payload)
    payload["safe_diagnostics"]["forbidden_marker_hits"] = marker_hits
    if marker_hits:
        payload["status"] = "blocked"
        payload["reason_code"] = "local_deployment_env_smoke_forbidden_marker_detected"
    return payload


def _check_placeholder_env_files(root: Path) -> dict[str, Any]:
    missing = [path for path in PLACEHOLDER_ENV_FILES if not (root / path).exists()]
    empty = [
        path
        for path in PLACEHOLDER_ENV_FILES
        if (root / path).exists() and not (root / path).read_text(encoding="utf-8").strip()
    ]
    env_names_by_file = {
        path: sorted(_parse_env_file(root / path))
        for path in PLACEHOLDER_ENV_FILES
        if (root / path).exists()
    }
    provider_placeholders = {
        path: {
            name: {
                "present": name in _parse_env_file(root / path),
                "value_reported": False,
                "placeholder_or_empty": _is_empty_or_placeholder(_parse_env_file(root / path).get(name)),
            }
            for name in PROVIDER_KEY_ENV_NAMES
            if name in _parse_env_file(root / path)
        }
        for path in SERVER_ENV_FILES
        if (root / path).exists()
    }
    status = "blocked" if missing or empty else "pass"
    return {
        "check_id": "placeholder_env_files",
        "status": status,
        "reason_code": "placeholder_env_files_present" if status == "pass" else "placeholder_env_files_missing_or_empty",
        "files": [
            {
                "path": path,
                "present": path not in missing,
                "non_empty": path not in empty,
                "env_names": env_names_by_file.get(path, []),
                "env_values_reported": False,
            }
            for path in PLACEHOLDER_ENV_FILES
        ],
        "provider_secret_placeholders": provider_placeholders,
    }


def _check_browser_env_secret_separation(root: Path) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for relative in BROWSER_ENV_FILES:
        env = _parse_env_file(root / relative)
        env_names = sorted(env)
        unsafe_names = [
            name
            for name in env_names
            if name not in BROWSER_SAFE_ENV_NAMES or any(server_name == name for server_name in SERVER_ONLY_ENV_NAMES)
        ]
        missing_safe_names = [name for name in BROWSER_SAFE_ENV_NAMES if name not in env]
        if unsafe_names or missing_safe_names:
            blockers.append(
                {
                    "file": relative,
                    "unsafe_env_names": unsafe_names,
                    "missing_safe_env_names": missing_safe_names,
                }
            )
        files.append(
            {
                "path": relative,
                "env_names": env_names,
                "allowed_browser_env_names": list(BROWSER_SAFE_ENV_NAMES),
                "server_only_env_names_absent": not unsafe_names,
                "env_values_reported": False,
            }
        )
    status = "blocked" if blockers else "pass"
    return {
        "check_id": "browser_env_secret_separation",
        "status": status,
        "reason_code": "browser_env_files_are_public_only" if status == "pass" else "browser_env_file_contains_server_only_key",
        "files": files,
        "server_only_env_names_checked": list(SERVER_ONLY_ENV_NAMES),
        "blockers": blockers,
    }


def _check_server_env_readiness(root: Path) -> dict[str, Any]:
    files = {
        ".env.example": ROOT_REQUIRED_ENV_NAMES,
        "deploy/env/api.example.env": API_REQUIRED_ENV_NAMES,
        "deploy/env/worker.example.env": WORKER_REQUIRED_ENV_NAMES,
        "deploy/env/web.example.env": BROWSER_SAFE_ENV_NAMES,
    }
    summaries = []
    blockers: list[dict[str, Any]] = []
    for relative, required_names in files.items():
        env = _parse_env_file(root / relative)
        missing = [name for name in required_names if name not in env]
        if missing:
            blockers.append({"file": relative, "missing_env_names": missing})
        summaries.append(
            {
                "path": relative,
                "required_env_names": list(required_names),
                "present_env_names": sorted(name for name in required_names if name in env),
                "missing_env_names": missing,
                "configured_status_by_name": {
                    name: _configured_status(env.get(name)) for name in required_names if name in env
                },
                "env_values_reported": False,
            }
        )
    status = "blocked" if blockers else "pass"
    return {
        "check_id": "server_env_readiness_placeholders",
        "status": status,
        "reason_code": "deployment_env_placeholders_named" if status == "pass" else "deployment_env_placeholder_missing",
        "surfaces": summaries,
        "cloud_run_api_env_placeholders_present": not any(
            blocker["file"] == "deploy/env/api.example.env" for blocker in blockers
        ),
        "cloud_run_worker_env_placeholders_present": not any(
            blocker["file"] == "deploy/env/worker.example.env" for blocker in blockers
        ),
        "vercel_next_public_api_base_placeholder_present": "NEXT_PUBLIC_API_BASE_URL"
        in _parse_env_file(root / "deploy/env/web.example.env"),
        "blockers": blockers,
    }


def _check_settings_defaults() -> dict[str, Any]:
    persistence = build_persistence_settings(env={})
    lightweight = build_lightweight_data_settings(env={})
    cors = build_cors_settings(env={})
    blockers = []
    if persistence.database_url_configured:
        blockers.append("default_database_url_should_be_missing")
    if lightweight.data_policy_mode != "lightweight":
        blockers.append("data_policy_mode_default_not_lightweight")
    if lightweight.live_fetch_enabled:
        blockers.append("lightweight_live_fetch_should_default_off")
    if not lightweight.provider_fallback_enabled:
        blockers.append("provider_fallback_should_default_on")
    if not lightweight.sec_user_agent_configured:
        blockers.append("sec_user_agent_placeholder_missing")
    if not cors.enabled:
        blockers.append("cors_local_origins_missing")
    status = "blocked" if blockers else "pass"
    return {
        "check_id": "backend_settings_defaults",
        "status": status,
        "reason_code": "backend_settings_defaults_safe" if status == "pass" else "backend_settings_default_regression",
        "data_policy_mode": lightweight.data_policy_mode,
        "lightweight_live_fetch_enabled": lightweight.live_fetch_enabled,
        "lightweight_provider_fallback_enabled": lightweight.provider_fallback_enabled,
        "sec_edgar_user_agent_placeholder_present": lightweight.sec_user_agent_configured,
        "sec_edgar_user_agent_value_reported": False,
        "database_url_configured_by_default": persistence.database_url_configured,
        "database_url_value_reported": False,
        "cors_allowed_origins_configured": cors.enabled,
        "cors_origin_values_reported": False,
        "blockers": blockers,
    }


def _check_repo_local_scaffolding(root: Path) -> dict[str, Any]:
    root_package = (root / "package.json").read_text(encoding="utf-8")
    next_config = (root / "apps/web/next.config.mjs").read_text(encoding="utf-8")
    api_dockerfile = (root / "docker/api/Dockerfile").read_text(encoding="utf-8")
    web_dockerfile = (root / "docker/web/Dockerfile").read_text(encoding="utf-8")
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    blockers: list[str] = []
    if '"apps/web"' not in root_package:
        blockers.append("apps_web_workspace_missing")
    for script in ("dev", "build", "start", "typecheck"):
        if f"npm --workspace apps/web run {script}" not in root_package:
            blockers.append(f"root_script_{script}_does_not_delegate_to_apps_web")
    if "destination: `${apiBaseUrl}/api/:path*`" not in next_config:
        blockers.append("next_api_rewrite_missing")
    if "process.env.NEXT_PUBLIC_API_BASE_URL" not in next_config or "process.env.API_BASE_URL" not in next_config:
        blockers.append("next_api_base_env_fallback_missing")
    if "ENV PORT=8000" not in api_dockerfile or "--port ${PORT:-8000}" not in api_dockerfile:
        blockers.append("api_dockerfile_port_contract_missing")
    if 'COPY apps/web ./apps/web' not in web_dockerfile or '["npm", "--workspace", "apps/web"' not in web_dockerfile:
        blockers.append("web_dockerfile_next_workspace_build_missing")
    for service in ("web:", "api:", "ingestion-worker:", "postgres:", "redis:", "minio:"):
        if service not in compose:
            blockers.append(f"docker_compose_service_{service.rstrip(':')}_missing")
    if 'LLM_PROVIDER: mock' not in compose or 'LLM_LIVE_GENERATION_ENABLED: "false"' not in compose:
        blockers.append("docker_compose_mock_llm_defaults_missing")
    status = "blocked" if blockers else "pass"
    return {
        "check_id": "repo_local_deployment_scaffolding",
        "status": status,
        "reason_code": "repo_local_deployment_scaffolding_ready" if status == "pass" else "repo_local_deployment_scaffolding_blocked",
        "apps_web_is_vercel_project_root": (root / "apps/web/package.json").exists(),
        "root_npm_scripts_delegate_to_apps_web": not any("root_script_" in blocker for blocker in blockers),
        "next_api_rewrite_or_api_base_behavior_present": "next_api_rewrite_missing" not in blockers,
        "api_dockerfile_respects_port_contract": "api_dockerfile_port_contract_missing" not in blockers,
        "web_dockerfile_builds_next_workspace": "web_dockerfile_next_workspace_build_missing" not in blockers,
        "docker_compose_local_only_services_present": not any(blocker.startswith("docker_compose_service_") for blocker in blockers),
        "docker_compose_mock_llm_defaults_present": "docker_compose_mock_llm_defaults_missing" not in blockers,
        "services_started": False,
        "blockers": blockers,
    }


def _check_docker_compose_config(root: Path, *, run_docker_config: bool) -> dict[str, Any]:
    if not run_docker_config:
        return {
            "check_id": "docker_compose_config",
            "status": "skipped",
            "reason_code": "docker_compose_config_skipped_by_caller",
            "command": "docker compose config",
            "services_started": False,
            "volumes_created": False,
            "images_pulled": False,
        }
    docker_path = shutil.which("docker")
    if docker_path is None:
        return {
            "check_id": "docker_compose_config",
            "status": "skipped",
            "reason_code": "skipped_unavailable",
            "docker_cli_available": False,
            "docker_compose_config_status": "skipped_unavailable",
            "command": "docker compose config",
            "services_started": False,
            "volumes_created": False,
            "images_pulled": False,
            "output_reported": False,
        }
    try:
        result = subprocess.run(
            [docker_path, "compose", "config"],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {
            "check_id": "docker_compose_config",
            "status": "skipped",
            "reason_code": "skipped_unavailable",
            "docker_cli_available": True,
            "docker_compose_config_status": "skipped_unavailable",
            "command": "docker compose config",
            "services_started": False,
            "volumes_created": False,
            "images_pulled": False,
            "output_reported": False,
        }
    stderr = (result.stderr or "").lower()
    if result.returncode != 0 and (
        "not a docker command" in stderr
        or "unknown command" in stderr
        or "compose is not" in stderr
        or "no such file" in stderr
    ):
        return {
            "check_id": "docker_compose_config",
            "status": "skipped",
            "reason_code": "skipped_unavailable",
            "docker_cli_available": True,
            "docker_compose_config_status": "skipped_unavailable",
            "command": "docker compose config",
            "services_started": False,
            "volumes_created": False,
            "images_pulled": False,
            "output_reported": False,
        }
    status = "pass" if result.returncode == 0 else "blocked"
    return {
        "check_id": "docker_compose_config",
        "status": status,
        "reason_code": "docker_compose_config_passed" if status == "pass" else "docker_compose_config_failed",
        "docker_cli_available": True,
        "docker_compose_config_status": "pass" if status == "pass" else "failed",
        "returncode": result.returncode,
        "command": "docker compose config",
        "services_started": False,
        "volumes_created": False,
        "images_pulled": False,
        "output_reported": False,
    }


def _parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        name = name.strip()
        if name:
            env[name] = value.strip()
    return env


def _configured_status(value: str | None) -> str:
    if value is None:
        return "missing"
    if _is_empty_or_placeholder(value):
        return "placeholder_or_empty"
    return "configured_placeholder"


def _is_empty_or_placeholder(value: str | None) -> bool:
    if value is None:
        return False
    stripped = value.strip()
    return stripped == "" or "example" in stripped.lower() or "placeholder" in stripped.lower()


def _forbidden_output_marker_hits(payload: dict[str, Any]) -> list[str]:
    serialized = json.dumps(payload, sort_keys=True)
    return [marker for marker in FORBIDDEN_OUTPUT_MARKERS if marker.lower() in serialized.lower()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic local deployment/env smoke.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument(
        "--skip-docker-compose-config",
        action="store_true",
        help="Skip optional docker compose config validation.",
    )
    args = parser.parse_args()
    result = run_local_deployment_env_smoke(run_docker_config=not args.skip_docker_compose_config)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{SCHEMA_VERSION}: {result['status']} ({result['reason_code']})")
    return 0 if result["status"] in {"pass"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
