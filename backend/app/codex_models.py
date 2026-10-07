"""Bounded subscription model catalogs. A catalog does not establish entitlement."""
import asyncio

from pydantic import ValidationError

from backend.app.contracts import RuntimeModel
from backend.app.runtime_base import RuntimeFailure


async def read_models(rpc) -> list[RuntimeModel]:
    models, seen, cursors = [], set(), set()
    cursor = None
    try:
        async with asyncio.timeout(30):
            for _ in range(4):
                page = await rpc.request("model/list", {"limit": 50, "includeHidden": False, "cursor": cursor})
                rows = page.get("data")
                if not isinstance(rows, list) or len(rows) > 50:
                    raise ValueError("invalid page")
                for row in rows:
                    if not isinstance(row, dict) or type(row.get("hidden")) is not bool or type(row.get("isDefault")) is not bool:
                        raise ValueError("invalid entry")
                    modalities = row.get("inputModalities")
                    if not isinstance(modalities, list) or not all(isinstance(value, str) for value in modalities):
                        raise ValueError("invalid modalities")
                    model = RuntimeModel(id=row.get("model"), name=row.get("displayName"), is_default=row["isDefault"])
                    if model.id in seen or any(ord(char) < 32 for char in model.name):
                        raise ValueError("ambiguous model")
                    seen.add(model.id)
                    if not row["hidden"] and "text" in modalities:
                        models.append(model)
                cursor = page.get("nextCursor")
                if cursor is None:
                    if sum(model.is_default for model in models) > 1:
                        raise ValueError("ambiguous default")
                    return models
                if not isinstance(cursor, str) or not 1 <= len(cursor) <= 1024 or cursor in cursors:
                    raise ValueError("invalid cursor")
                cursors.add(cursor)
        raise ValueError("page limit")
    except (ValueError, TypeError, ValidationError, TimeoutError) as exc:
        raise RuntimeFailure("Codex model catalog is invalid or incomplete. Refresh the connection; no model was selected.") from exc


def select_model(models: list[RuntimeModel], requested: str | None) -> str:
    if requested is not None:
        if any(model.id == requested for model in models):
            return requested
        raise RuntimeFailure("The selected model is no longer in the provider catalog. Choose a model in Connections; no fallback was attempted.")
    defaults = [model.id for model in models if model.is_default]
    if len(defaults) != 1:
        raise RuntimeFailure("The provider has no unambiguous default model. Choose a model in Connections.")
    return defaults[0]
