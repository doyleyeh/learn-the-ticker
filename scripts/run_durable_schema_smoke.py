from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.durable_repository_records import (
    DURABLE_REPOSITORY_RECORDS_SCHEMA_VERSION,
    DURABLE_REPOSITORY_RECORD_TABLE,
    DurableRepositoryRecordSession,
    execute_durable_repository_record_schema,
    inspect_durable_repository_record_schema,
)


SMOKE_SCHEMA_VERSION = "durable-schema-smoke-v1"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = run_durable_schema_smoke(database_path=Path(args.database_path) if args.database_path else None)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


def run_durable_schema_smoke(*, database_path: Path | None = None) -> dict[str, Any]:
    cleanup = database_path is None
    resolved_path = database_path or Path(tempfile.mkdtemp(prefix="ltt-durable-schema-smoke-")) / "durable-records.db"
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sqlite3.connect(resolved_path) as connection:
            connection.row_factory = sqlite3.Row
            applied_tables = execute_durable_repository_record_schema(connection)
            schema = inspect_durable_repository_record_schema(connection)

        writer = DurableRepositoryRecordSession(resolved_path)
        summary = writer.save_repository_record(
            "durable_schema_smoke",
            "restart-proof-record",
            {
                "schema_version": "durable-schema-smoke-record-v1",
                "no_live_external_calls": True,
                "raw_provider_payload_stored": False,
                "secret_values_stored": False,
            },
        )
        writer.commit()
        writer.close()

        reader = DurableRepositoryRecordSession(resolved_path)
        restored = reader.get_repository_record("durable_schema_smoke", "restart-proof-record")
        reader.close()

        status = "passed" if restored and restored.get("schema_version") == "durable-schema-smoke-record-v1" else "failed"
        return {
            "schema_version": SMOKE_SCHEMA_VERSION,
            "status": status,
            "repository_record_schema_version": DURABLE_REPOSITORY_RECORDS_SCHEMA_VERSION,
            "database_path": str(resolved_path),
            "table": DURABLE_REPOSITORY_RECORD_TABLE,
            "applied_tables": list(applied_tables),
            "inspected_schema": schema,
            "restart_read_succeeded": status == "passed",
            "payload_checksum": summary.payload_checksum,
            "no_live_external_calls": True,
            "secret_values_stored": False,
        }
    finally:
        if cleanup:
            try:
                resolved_path.unlink(missing_ok=True)
                resolved_path.parent.rmdir()
            except OSError:
                pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a deterministic local durable schema smoke.")
    parser.add_argument("--database-path", help="Optional SQLite path. Defaults to a throwaway /tmp database.")
    return parser


if __name__ == "__main__":  # pragma: no cover - exercised by CLI smoke.
    raise SystemExit(main())
