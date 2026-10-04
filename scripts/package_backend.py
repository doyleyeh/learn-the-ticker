"""Build reviewed Windows dependencies; never download runtimes or access providers."""
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_market_dependencies(root=ROOT, *, version=importlib.metadata.version):
    for line in (root / "requirements-market-data.txt").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, expected = line.split("==")
        try:
            actual = version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        if actual != expected:
            raise SystemExit("Install the reviewed requirements-market-data.txt before packaging: " + name)
    notices = root / "docs/licenses/market"
    for item in json.loads((notices / "manifest.json").read_text()):
        path = notices / item["notice"]
        normalized = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()
        if path.parent != notices or hashlib.sha256(normalized).hexdigest() != item["sha256"]:
            raise SystemExit("Market dependency notice differs from the reviewed manifest")


def main():
    if platform.system() != "Windows" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise SystemExit("The current packaging target is native Windows x64")
    check_market_dependencies()
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
        "--name", "ltt-service", "--paths", str(ROOT),
        "--additional-hooks-dir", str(ROOT / "scripts/pyinstaller_hooks"),
        "--copy-metadata", "yfinance", "--collect-all", "psycopg",
        "--collect-all", "psycopg_binary", "--collect-all", "keyring",
        "--exclude-module", "keyring.testing", "--exclude-module", "pytest",
        "--exclude-module", "_pytest", "--exclude-module", "ruff",
        "--exclude-module", "pandas.tests", "--exclude-module", "numpy.tests",
        "--exclude-module", "lxml.isoschematron",
        "--add-data", f"{ROOT / 'backend/migrations'};backend/migrations",
        "--add-data", f"{ROOT / 'docs/licenses'};licenses",
        str(ROOT / "backend/desktop_entry.py"),
    ], cwd=ROOT, check=True)
    destination = ROOT / "apps/desktop/src-tauri/binaries"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "dist/ltt-service.exe", destination / "ltt-service-x86_64-pc-windows-msvc.exe")


if __name__ == "__main__":
    main()
