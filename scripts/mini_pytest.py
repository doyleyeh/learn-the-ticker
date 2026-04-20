from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    targets = [arg for arg in argv if not arg.startswith("-")] or ["tests"]
    failures = 0
    total = 0

    sys.path.insert(0, str(ROOT))

    for path in _test_files(targets):
        module = _load_module(path)
        for name in sorted(dir(module)):
            if not name.startswith("test_"):
                continue
            test_func = getattr(module, name)
            if not callable(test_func):
                continue
            total += 1
            try:
                test_func()
            except Exception:
                failures += 1
                print(f"FAILED {path.relative_to(ROOT)}::{name}")
                traceback.print_exc()

    if failures:
        print(f"{failures} failed, {total - failures} passed")
        return 1

    print(f"{total} passed")
    return 0


def _test_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = (ROOT / target).resolve()
        if path.is_file() and path.name.startswith("test_") and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("test_*.py")))
    return sorted(set(files))


def _load_module(path: Path) -> ModuleType:
    module_name = "mini_pytest_" + "_".join(path.relative_to(ROOT).with_suffix("").parts)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load test module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
