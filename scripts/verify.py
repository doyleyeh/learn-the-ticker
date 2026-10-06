"""Shared local/CI verification. Never invokes live providers or installs dependencies."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PrerequisiteError(RuntimeError):
    pass


def executable(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise PrerequisiteError(f"Missing {name}; follow README setup and EVALS prerequisites.")
    return found


def run(command: list[str]):
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def postgres_directory() -> Path:
    configured = os.environ.get("LTT_PG_BIN")
    directory = Path(configured) if configured else Path("C:/Program Files/PostgreSQL/17/bin")
    for name in ("initdb", "pg_ctl", "postgres"):
        filename = name + (".exe" if os.name == "nt" else "")
        if not (directory / filename).is_file():
            raise PrerequisiteError("Set LTT_PG_BIN to a PostgreSQL 17 binary directory; isolated database checks cannot be skipped.")
    return directory


def verify(tier: str):
    python = sys.executable
    git = executable("git")
    npm = executable("npm.cmd" if os.name == "nt" else "npm")
    node = executable("node")
    if tier in ("database", "full"):
        postgres_directory()
    if tier in ("native", "full"):
        executable("cargo")
        if not (ROOT / "apps/desktop/src-tauri/resources/postgres/bin/postgres.exe").is_file():
            raise PrerequisiteError("Native Windows build needs reviewed PostgreSQL resources; see docs/MIGRATION.md.")
    if tier in ("packaged", "native", "full") and sys.platform != "win32":
        raise PrerequisiteError("Packaging/native verification currently requires Windows x64.")
    if tier in ("fast", "milestone", "full"):
        commands = [
            [python, "-m", "ruff", "check", "backend", "scripts", "tests", "evals"],
            [npm, "run", "lint"],
            [python, "-m", "scripts.contracts", "--check"],
            [node, "scripts/generate_types.mjs", "--check"],
            [python, "-m", "scripts.check_docs"],
            [git, "diff", "--check"],
            [git, "diff", "--cached", "--check"],
        ]
        base = os.environ.get("LTT_VERIFY_BASE")
        if base:
            # Resolve before constructing the diff argument; never interpolate shell code.
            revision = subprocess.check_output([git, "rev-parse", "--verify", "--end-of-options", base + "^{commit}"], cwd=ROOT, text=True).strip()
            commands.append([git, "diff", "--check", revision, "HEAD", "--"])
        for command in commands:
            run(command)
        if tier == "fast":
            run([npm, "run", "typecheck"])
        else:
            for command in (
                [python, "-m", "pytest", "tests", "-q"],
                [python, "evals/run_static_evals.py"],
                [npm, "test"],
                [npm, "run", "build"],  # Build already performs tsc --noEmit.
            ):
                run(command)
    if tier in ("database", "full"):
        for command in (
            [python, "scripts/smoke_local_service.py"],
            [python, "-m", "scripts.smoke_database"],
            [python, "-m", "scripts.smoke_restore"],
            [python, "-m", "scripts.smoke_library_scale"],
            [python, "-m", "scripts.smoke_library_deletion"],
        ):
            run(command)
    if tier in ("packaged", "full"):
        postgres_directory()
        run([python, "scripts/package_backend.py"])
        run([python, "scripts/smoke_local_service.py", "--packaged"])
        run([python, "-m", "scripts.smoke_import_worker", "--packaged"])
        run([python, "-m", "scripts.smoke_market_worker", "--packaged"])
        run([python, "-m", "scripts.smoke_packaged_restore"])
    if tier in ("native", "full"):
        if not (ROOT / "apps/desktop/src-tauri/binaries/ltt-service-x86_64-pc-windows-msvc.exe").is_file():
            raise PrerequisiteError("Build the Windows sidecar before native verification (verify packaged).")
        run([npm, "run", "desktop:build"])
    print(f"{tier} checks passed. Live providers, browser/native interaction and clean-machine release acceptance remain separate EVALS gates.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tier", choices=("fast", "milestone", "database", "packaged", "native", "full"))
    args = parser.parse_args(argv)
    try:
        verify(args.tier)
    except PrerequisiteError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        return getattr(exc, "returncode", 1) or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
