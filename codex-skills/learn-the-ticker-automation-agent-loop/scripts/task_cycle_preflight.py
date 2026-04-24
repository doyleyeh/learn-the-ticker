#!/usr/bin/env python3
"""Summarize task-cycle readiness and print the recommended WSL command."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check TASKS.md readiness and choose a task-cycle model."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root that contains TASKS.md and scripts/run_task_cycle.sh",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=5,
        help="Requested repeat-mode cycle count. Default: 5.",
    )
    parser.add_argument(
        "--prefer-model",
        default="gpt-5.3-codex-spark",
        help="Model to use when Spark is allowed.",
    )
    parser.add_argument(
        "--fallback-model",
        default="gpt-5.4",
        help="Model to use when Spark should not be selected.",
    )
    return parser.parse_args()


def parse_percent(name: str) -> float | None:
    raw_value = os.environ.get(name)
    if raw_value is None or not raw_value.strip():
        return None

    try:
        value = float(raw_value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be numeric, got: {raw_value!r}") from exc

    if value < 0 or value > 100:
        raise SystemExit(f"{name} must be between 0 and 100, got: {value}")

    return value


def parse_tasks(tasks_path: Path) -> tuple[bool, int]:
    content = tasks_path.read_text(encoding="utf-8")
    current_present = False
    backlog_count = 0
    in_current = False
    in_backlog = False

    for line in content.splitlines():
        if line.startswith("## Current task"):
            in_current = True
            in_backlog = False
            continue
        if line.startswith("## Backlog"):
            in_backlog = True
            in_current = False
            continue
        if line.startswith("## "):
            in_current = False
            in_backlog = False
            continue
        if in_current and re.match(r"^### T-", line):
            current_present = True
        if in_backlog and re.match(r"^### T-", line):
            backlog_count += 1

    return current_present, backlog_count


def choose_model(prefer_model: str, fallback_model: str) -> tuple[str, str]:
    forced = os.environ.get("LTT_FORCE_TASK_CYCLE_MODEL", "").strip()
    if forced:
        return forced, "selected from LTT_FORCE_TASK_CYCLE_MODEL"

    remaining = parse_percent("LTT_CODEX_SPARK_REMAINING_PERCENT")
    if remaining is not None:
        if remaining < 30:
            return (
                fallback_model,
                f"Spark remaining percent is {remaining:.1f}, below the 30.0 threshold",
            )
        return (
            prefer_model,
            f"Spark remaining percent is {remaining:.1f}, meeting the 30.0 threshold",
        )

    used = parse_percent("LTT_CODEX_SPARK_USED_PERCENT")
    if used is not None:
        if used > 70:
            return (
                fallback_model,
                f"Spark used percent is {used:.1f}, above the 70.0 threshold",
            )
        return (
            prefer_model,
            f"Spark used percent is {used:.1f}, within the 70.0 threshold",
        )

    enable_without_signal = os.environ.get(
        "LTT_ENABLE_SPARK_WITHOUT_USAGE_SIGNAL", ""
    ).strip().lower() in {"1", "true", "yes", "on"}
    if enable_without_signal:
        return (
            prefer_model,
            "selected because LTT_ENABLE_SPARK_WITHOUT_USAGE_SIGNAL is enabled",
        )

    return (
        fallback_model,
        "no reliable Spark usage signal is available in the local environment",
    )


def to_wsl_path(path: Path) -> str:
    resolved = str(path.resolve())
    match = re.match(r"^([A-Za-z]):\\(.*)$", resolved)
    if not match:
        return resolved.replace("\\", "/")

    drive = match.group(1).lower()
    rest = match.group(2).replace("\\", "/")
    return f"/mnt/{drive}/{rest}"


def main() -> int:
    args = parse_args()

    if args.max_cycles < 1 or args.max_cycles > 5:
        raise SystemExit("--max-cycles must be between 1 and 5 for this skill")

    repo_root = Path(args.repo_root).resolve()
    tasks_path = repo_root / "TASKS.md"
    run_task_cycle_path = repo_root / "scripts" / "run_task_cycle.sh"

    if not tasks_path.exists():
        raise SystemExit(f"TASKS.md was not found under {repo_root}")
    if not run_task_cycle_path.exists():
        raise SystemExit(f"scripts/run_task_cycle.sh was not found under {repo_root}")

    current_present, backlog_count = parse_tasks(tasks_path)
    planned_cycles = (1 if current_present else 0) + backlog_count
    missing_cycles = max(0, args.max_cycles - planned_cycles)
    selected_model, selection_reason = choose_model(
        args.prefer_model, args.fallback_model
    )

    repo_wsl = to_wsl_path(repo_root)
    direct_bash = (
        f"cd {shlex.quote(repo_wsl)} && "
        "source scripts/activate_agent_env.sh && "
        f"bash scripts/run_task_cycle.sh --model {shlex.quote(selected_model)} "
        f"--repeat --max-cycles {args.max_cycles} --push"
    )
    wsl_command = f"wsl.exe bash -lc {shlex.quote(direct_bash)}"

    print(f"repo_root: {repo_root}")
    print(f"current_task_present: {'yes' if current_present else 'no'}")
    print(f"backlog_count: {backlog_count}")
    print(f"planned_cycles: {planned_cycles}")
    print(f"requested_cycles: {args.max_cycles}")
    print(f"additional_cycles_needed: {missing_cycles}")
    print(f"selected_model: {selected_model}")
    print(f"selection_reason: {selection_reason}")
    print("wsl_command:")
    print(wsl_command)

    return 0


if __name__ == "__main__":
    sys.exit(main())
