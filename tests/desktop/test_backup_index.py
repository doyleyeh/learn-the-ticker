import copy
import sqlite3
from datetime import datetime, timezone
from functools import partial
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import update

from backend.app import backup_index
from backend.app.backup import BackupError, make_backup, preview_backup, read_backup, restore_backup
from backend.app.db import Database, Record
from tests.desktop.test_backup import seed


def test_equal_timestamp_list_order_survives_archive_restore():
    from tests.desktop.term_deletion_fixture import seed_terms
    db, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    version = seed(db)
    terms, _ = seed_terms(db, version)
    with db.session.begin() as session:
        session.execute(update(Record).where(Record.kind == "term").values(updated_at=datetime(2026, 10, 1, tzinfo=timezone.utc)))
    assert [row["id"] for row in db.list("term")] == sorted(row.id for row in terms)
    archive = make_backup(db)
    restore_backup(target, archive, preview_backup(target, archive).fingerprint)
    assert target.list("term") == db.list("term")
    db.engine.dispose()
    target.engine.dispose()


def test_disk_snapshot_matches_all_portable_rows_and_removes_owned_scratch(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_index, "TemporaryDirectory", partial(TemporaryDirectory, dir=tmp_path))
    db = Database("sqlite://", testing=True)
    seed(db)
    _, expected = read_backup(make_backup(db))
    with backup_index.indexed_snapshot(db) as index:
        for name in ("records", "jobs", "events"):
            actual = [row.model_dump(mode="json") for row in getattr(index, name).values()]
            assert actual == [row.model_dump(mode="json") for row in getattr(expected, name)]
        assert len(list(tmp_path.iterdir())) == 1
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(sqlite3.ProgrammingError):
        len(index.records)
    db.engine.dispose()


@pytest.mark.parametrize("table", ["records", "jobs", "events"])
def test_disk_index_rejects_duplicate_ids_without_replacing_first_row(table):
    db = Database("sqlite://", testing=True)
    seed(db)
    _, data = read_backup(make_backup(db))
    first = getattr(data, table)[0]
    with backup_index.temporary_index() as index:
        rows = getattr(index, table)
        rows.add(first)
        with pytest.raises(BackupError, match="Duplicate"):
            rows.add(first)
        assert len(rows) == 1 and rows[first.id] == first
    db.engine.dispose()


@pytest.mark.parametrize("corruption", ["missing_evidence", "identity", "credentials", "raw_event"])
def test_shared_disk_validation_rejects_bad_references_and_private_fields(corruption):
    db = Database("sqlite://", testing=True)
    seed(db)
    _, data = read_backup(make_backup(db))
    original = copy.deepcopy(data)
    if corruption == "missing_evidence":
        next(row for row in data.records if row.kind == "saved").payload["bundle_id"] = "missing"
    elif corruption == "identity":
        next(row for row in data.records if row.kind == "asset").id = "asset:wrong"
    elif corruption == "credentials":
        next(row for row in data.records if row.kind == "settings").payload["token"] = "synthetic-private"
    else:
        data.events[0].payload.data["token"] = "synthetic-private"
    with backup_index.temporary_index() as index:
        for table in ("records", "jobs", "events"):
            for row in getattr(data, table):
                getattr(index, table).add(row)
        with pytest.raises(ValueError):
            index.validate()
    assert read_backup(make_backup(db))[1] == original
    db.engine.dispose()


def test_failed_snapshot_removes_scratch_and_leaves_original_library(monkeypatch, tmp_path):
    monkeypatch.setattr(backup_index, "TemporaryDirectory", partial(TemporaryDirectory, dir=tmp_path))
    db = Database("sqlite://", testing=True)
    seed(db)
    _, before = read_backup(make_backup(db))
    def fail(_self):
        raise RuntimeError("Synthetic validation interruption")
    monkeypatch.setattr(backup_index.LibraryIndex, "validate", fail)
    with pytest.raises(RuntimeError, match="Synthetic"):
        with backup_index.indexed_snapshot(db):
            pytest.fail("Invalid index must not be published")
    assert list(tmp_path.iterdir()) == []
    assert read_backup(make_backup(db))[1] == before
    db.engine.dispose()


def test_paused_iterator_can_close_after_index_context_without_closed_database_error():
    db = Database("sqlite://", testing=True)
    seed(db)
    with backup_index.indexed_snapshot(db) as index:
        paused = index.records.values()
        assert next(paused).id
        assert len(index.cursors) == 1
    assert not index.cursors
    paused.close()
    db.engine.dispose()
