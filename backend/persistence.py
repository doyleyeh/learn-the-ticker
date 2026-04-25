from __future__ import annotations


PERSISTENCE_METADATA_BOUNDARY = "persistence-metadata-boundary-v1"
PERSISTENCE_METADATA_NOTE = (
    "Dormant metadata boundary only. Current asset, retrieval, generation, chat, "
    "comparison, export, cache, and ingestion behavior remains fixture-backed."
)
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


try:
    from sqlalchemy import MetaData
except ModuleNotFoundError:  # pragma: no cover - exercised when dependencies are not installed.

    class _DormantMetadata:
        def __init__(self) -> None:
            self.naming_convention = NAMING_CONVENTION
            self.tables: dict[str, object] = {}

    target_metadata = _DormantMetadata()
else:
    target_metadata = MetaData(naming_convention=NAMING_CONVENTION)


def persistence_metadata_diagnostics() -> dict[str, object]:
    return {
        "boundary": PERSISTENCE_METADATA_BOUNDARY,
        "note": PERSISTENCE_METADATA_NOTE,
        "table_count": len(target_metadata.tables),
        "dormant": True,
    }
