"""Private, short-lived disk index for bounded-memory portable-library validation.

The application library remains PostgreSQL. This SQLite file is an owned scratch
index of typed application rows, never a user-supplied database or SQL program.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.backup import BackupError, StoredEvent, StoredJob, StoredRecord, utc, validate_indexed_library
from backend.app.db import Database, Event, Job, Record


TABLES = {"records": StoredRecord, "jobs": StoredJob, "events": StoredEvent}


class RowIndex:
    def __init__(self, connection, table, cursors):
        if table not in TABLES:
            raise ValueError("Unknown scratch table")
        self.connection, self.table, self.model = connection, table, TABLES[table]
        self.cursors = cursors

    def add(self, row):
        if not isinstance(row, self.model):
            raise TypeError("Wrong scratch row type")
        try:
            self.connection.execute(f"INSERT INTO {self.table} (id, data) VALUES (?, ?)", (row.id, row.model_dump_json()))
        except sqlite3.IntegrityError as exc:
            raise BackupError("Duplicate library record, job or event") from exc

    def __setitem__(self, key, row):
        if not isinstance(row, self.model) or key != row.id:
            raise ValueError("Scratch row identity cannot change")
        result = self.connection.execute(f"UPDATE {self.table} SET data = ? WHERE id = ?", (row.model_dump_json(), key))
        if result.rowcount != 1:
            raise KeyError(key)

    def __contains__(self, key):
        return self.connection.execute(f"SELECT 1 FROM {self.table} WHERE id = ?", (key,)).fetchone() is not None

    def __getitem__(self, key):
        row = self.connection.execute(f"SELECT data FROM {self.table} WHERE id = ?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return self.model.model_validate_json(row[0])

    def get(self, key):
        return self[key] if key in self else None

    def __len__(self):
        return self.connection.execute(f"SELECT COUNT(*) FROM {self.table}").fetchone()[0]

    def values(self):
        cursor = self.connection.execute(f"SELECT data FROM {self.table} ORDER BY id")
        self.cursors.add(cursor)
        try:
            for row in cursor:
                yield self.model.model_validate_json(row[0])
        finally:
            if cursor in self.cursors:
                self.cursors.remove(cursor)
                cursor.close()


class LibraryIndex:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)
        self.cursors = set()
        try:
            self.connection.execute("PRAGMA cache_size = -2048")
            self.connection.execute("PRAGMA temp_store = FILE")
            for name in TABLES:
                key_type = "INTEGER" if name == "events" else "TEXT"
                self.connection.execute(f"CREATE TABLE {name} (id {key_type} PRIMARY KEY NOT NULL, data TEXT NOT NULL)")
            self.records = RowIndex(self.connection, "records", self.cursors)
            self.jobs = RowIndex(self.connection, "jobs", self.cursors)
            self.events = RowIndex(self.connection, "events", self.cursors)
        except BaseException:
            self.connection.close()
            raise

    def validate(self):
        validate_indexed_library(self.records, self.jobs, self.events.values())
        self.connection.commit()

    def close(self):
        # Tracebacks can retain paused iterators past the context-manager exit.
        # Close their cursors before the connection, rather than during later GC.
        for cursor in self.cursors:
            cursor.close()
        self.cursors.clear()
        self.connection.close()


@contextmanager
def temporary_index():
    with TemporaryDirectory(prefix="ltt-library-index-") as directory:
        index = LibraryIndex(Path(directory) / "library.sqlite")
        try:
            yield index
        finally:
            index.close()


@contextmanager
def indexed_snapshot(db: Database):
    """Stage one repeatable snapshot using a one-row server cursor per table."""
    with temporary_index() as index:
        with db.engine.connect() as connection:
            if connection.dialect.name == "postgresql":
                connection = connection.execution_options(isolation_level="REPEATABLE READ")
            with Session(connection) as session, session.begin():
                for row in session.scalars(select(Record).order_by(Record.id).execution_options(yield_per=1)):
                    index.records.add(StoredRecord(id=row.id, kind=row.kind, parent_id=row.parent_id,
                                                  payload=row.payload, updated_at=utc(row.updated_at)))
                for row in session.scalars(select(Job).order_by(Job.id).execution_options(yield_per=1)):
                    index.jobs.add(StoredJob(id=row.id, status=row.status, request=row.request, result=row.result,
                                            error=row.error, created_at=utc(row.created_at)))
                for row in session.scalars(select(Event).order_by(Event.id).execution_options(yield_per=1)):
                    index.events.add(StoredEvent(id=row.id, job_id=row.job_id, payload=row.payload))
        index.validate()
        yield index
