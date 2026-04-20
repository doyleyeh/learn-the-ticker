from __future__ import annotations

try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - exercised only in dependency-free local gates.
    from backend.compat import TestClient


__all__ = ["TestClient"]
