from __future__ import annotations

import os

if os.environ.get("LTT_FORCE_COMPAT_FASTAPI") == "1":
    from backend.compat import TestClient
else:
    try:
        from fastapi.testclient import TestClient
    except ModuleNotFoundError:  # pragma: no cover - exercised only in dependency-free local gates.
        from backend.compat import TestClient


__all__ = ["TestClient"]
