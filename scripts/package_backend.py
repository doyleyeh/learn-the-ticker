"""Build on the target operating system; does not download provider or PostgreSQL binaries."""
import platform
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if platform.system() != "Windows" or platform.machine().lower() not in ("amd64", "x86_64"):
    raise SystemExit("The current packaging target is native Windows x64")
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--name", "ltt-service", "--paths", str(root), "--collect-all", "psycopg", "--collect-all", "psycopg_binary", "--collect-all", "keyring", "--exclude-module", "keyring.testing", "--exclude-module", "pytest", "--exclude-module", "_pytest", "--exclude-module", "ruff", "--add-data", f"{root / 'backend/migrations'};backend/migrations", str(root / "backend/desktop_entry.py")], cwd=root, check=True)
destination = root / "apps/desktop/src-tauri/binaries"
destination.mkdir(parents=True, exist_ok=True)
shutil.copy2(root / "dist/ltt-service.exe", destination / "ltt-service-x86_64-pc-windows-msvc.exe")
