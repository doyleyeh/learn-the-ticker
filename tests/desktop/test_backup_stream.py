import hashlib
import json
import struct
import warnings
import zipfile
from functools import partial
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import event

from backend.app import backup_index, backup_stream as codec
from backend.app.backup import BackupError, make_backup
from backend.app.contracts import Settings
from backend.app.db import Database, Event
from tests.desktop.test_backup import seed
from tests.desktop.test_retained_imports import CSV, retained


@pytest.fixture
def libraries():
    source, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    version = seed(source)
    document = retained(source)
    try:
        yield source, target, version, document
    finally:
        source.engine.dispose()
        target.engine.dispose()


def rewrite(path, target, mode):
    with zipfile.ZipFile(path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(members["manifest.json"])
    rows = [json.loads(line) for line in members["records.ndjson"].splitlines()]
    if mode == "duplicate":
        rows.append(rows[0])
    elif mode == "credentials":
        next(row for row in rows if row["kind"] == "settings")["payload"]["token"] = "synthetic-private"
    elif mode == "reference":
        next(row for row in rows if row["kind"] == "saved")["payload"]["bundle_id"] = "missing"
    elif mode == "inline_attachment":
        next(row for row in rows if row["kind"] == "import")["payload"]["content_base64"] = "YQ=="
    elif mode == "missing_import":
        rows = [row for row in rows if row["kind"] != "import"]
    payload = b"".join(json.dumps(row).encode() + b"\n" for row in rows)
    if mode == "unterminated":
        payload = payload[:-1]
    members["records.ndjson"] = payload
    manifest["tables"]["records"].update(row_count=len(rows), byte_count=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    if mode == "checksum":
        manifest["tables"]["records"]["sha256"] = "0" * 64
    elif mode == "row_count":
        manifest["tables"]["records"]["row_count"] -= 1
    elif mode == "table_size":
        manifest["tables"]["records"]["byte_count"] += 1
    elif mode == "version":
        manifest["format_version"] = "99"
    elif mode == "schema":
        manifest["database_revision"] = "9999"
    elif mode == "attachment":
        name = next(name for name in members if name.startswith("attachments/"))
        members[name] = b"x" * len(members[name])
    elif mode == "extra":
        members["../auth.json"] = b"never extract"
    elif mode == "raw_event":
        rows = [json.loads(line) for line in members["events.ndjson"].splitlines()]
        rows[0]["payload"]["data"]["token"] = "synthetic-private"
        payload = b"".join(json.dumps(row).encode() + b"\n" for row in rows)
        members["events.ndjson"] = payload
        manifest["tables"]["events"].update(byte_count=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    members["manifest.json"] = json.dumps(manifest).encode()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in members.items():
            archive.writestr(name, value)
        if mode == "duplicate_member":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr("manifest.json", members["manifest.json"])


def test_file_roundtrip_preserves_originals_and_clears_consent_without_replay(libraries, monkeypatch, tmp_path):
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda *args: pytest.fail("Archive read the vault"))
    monkeypatch.setattr(codec, "TemporaryDirectory", partial(TemporaryDirectory, dir=tmp_path))
    source, target, version, document = libraries
    before = source.get("import:" + document.id)
    with codec.create_backup_file(source) as path:
        with zipfile.ZipFile(path) as archive:
            assert archive.read("attachments/" + document.id + ".bin") == CSV
            assert b"content_base64" not in archive.read("records.ndjson")
        summary = codec.preview_backup_file(target, path)
        assert summary.format_version == "3" and summary.can_restore
        assert summary.retained_imports == 1 and summary.attachment_bytes == len(CSV)
        codec.restore_backup_file(target, path, summary.fingerprint)
        assert target.get("bundle:" + version) == source.get("bundle:" + version)
        assert target.get("import:" + document.id) == before == source.get("import:" + document.id)
        assert target.job("pending")["status"] == "interrupted"
        assert len(target.events("pending")) == 1
        assert not any(target.get("settings")[key] for key in ("cloud_enabled", "experimental_yahoo_enabled", "start_at_login"))
        assert source.get("settings")["cloud_enabled"]
    assert not path.exists() and not list(tmp_path.iterdir())


@pytest.mark.parametrize("attachments", [False, True])
def test_file_reader_accepts_legacy_archives(tmp_path, attachments):
    source, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    version = seed(source)
    if attachments:
        retained(source)
    path = tmp_path / "legacy.lttbackup"
    path.write_bytes(make_backup(source))
    summary = codec.preview_backup_file(target, path)
    assert summary.format_version == ("2" if attachments else "1")
    codec.restore_backup_file(target, path, summary.fingerprint)
    assert target.get("bundle:" + version) == source.get("bundle:" + version)
    source.engine.dispose()
    target.engine.dispose()


@pytest.mark.parametrize("mode", ["duplicate", "credentials", "reference", "raw_event", "inline_attachment", "missing_import",
    "checksum", "row_count", "table_size", "version", "schema", "attachment", "extra", "duplicate_member", "unterminated"])
def test_hostile_archives_fail_before_writes_and_remove_scratch(libraries, monkeypatch, tmp_path, mode):
    source, target, _, _ = libraries
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(backup_index, "TemporaryDirectory", partial(TemporaryDirectory, dir=scratch))
    with codec.create_backup_file(source) as path:
        changed = tmp_path / "bad.lttbackup"
        rewrite(path, changed, mode)
        with pytest.raises(BackupError):
            codec.restore_backup_file(target, changed, hashlib.sha256(changed.read_bytes()).hexdigest())
    assert not target.list("asset") and target.get("settings") is None and not target.job("pending")
    assert list(scratch.iterdir()) == []


def test_late_restore_failure_preserves_settings_and_all_target_tables(libraries):
    source, target, _, _ = libraries
    target.put("settings", "settings", Settings(language="en").model_dump(mode="json"))
    before = target.get("settings")
    def fail(*args):
        raise RuntimeError("Synthetic late write failure")
    with codec.create_backup_file(source) as path:
        summary = codec.preview_backup_file(target, path)
        event.listen(Event, "before_insert", fail)
        try:
            with pytest.raises(RuntimeError, match="Synthetic late"):
                codec.restore_backup_file(target, path, summary.fingerprint)
        finally:
            event.remove(Event, "before_insert", fail)
    assert target.get("settings") == before
    assert not target.list("asset") and not target.list("import") and not target.job("pending")


def test_preview_fingerprint_and_empty_target_rechecked(libraries, monkeypatch):
    source, target, _, _ = libraries
    with codec.create_backup_file(source) as path:
        summary = codec.preview_backup_file(target, path)
        with pytest.raises(BackupError, match="changed after preview"):
            codec.restore_backup_file(target, path, "wrong")
        original = codec.archive_summary
        def racing_summary(*args):
            summary = original(*args)
            target.put("asset:" + source.list("asset")[0]["asset"]["id"], "asset", source.list("asset")[0])
            return summary
        monkeypatch.setattr(codec, "archive_summary", racing_summary)
        with pytest.raises(BackupError, match="changed after preview"):
            codec.restore_backup_file(target, path, summary.fingerprint)
        monkeypatch.setattr(codec, "archive_summary", original)
        with pytest.raises(BackupError, match="empty library"):
            codec.restore_backup_file(target, path, summary.fingerprint)
        assert target.list("asset") == source.list("asset")


@pytest.mark.parametrize("limit", ["MAX_ARCHIVE_BYTES", "MAX_CONTENT_BYTES", "MAX_ROW_BYTES"])
def test_writer_capacity_failure_discards_partial_archive(libraries, tmp_path, monkeypatch, limit):
    monkeypatch.setattr(codec, "TemporaryDirectory", partial(TemporaryDirectory, dir=tmp_path))
    monkeypatch.setattr(codec, limit, 100)
    with pytest.raises(BackupError):
        with codec.create_backup_file(libraries[0]):
            pytest.fail("Partial archive was published")
    assert list(tmp_path.iterdir()) == []


def test_reader_bounds_rows_and_directory_before_large_allocation(libraries, tmp_path, monkeypatch):
    with codec.create_backup_file(libraries[0]) as path:
        monkeypatch.setattr(codec, "MAX_ROW_BYTES", 20)
        with pytest.raises(BackupError, match="oversized"):
            codec.preview_backup_file(libraries[1], path)
        monkeypatch.undo()
        raw = bytearray(path.read_bytes())
        offset = raw.rfind(b"PK\x05\x06")
        struct.pack_into("<I", raw, offset + 12, codec.MAX_DIRECTORY_BYTES + 1)
        changed = tmp_path / "huge-directory.lttbackup"
        changed.write_bytes(raw)
        monkeypatch.setattr(codec.zipfile, "ZipFile", lambda *args, **kwargs: pytest.fail("Directory allocation before preflight"))
        with pytest.raises(BackupError, match="directory"):
            codec.preview_backup_file(libraries[1], changed)


def test_zip64_directory_roundtrip_and_truncated_archive(libraries, monkeypatch, tmp_path):
    # Exercise actual ZIP64 end records without allocating multiple GiB in CI.
    monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 200)
    with codec.create_backup_file(libraries[0]) as path:
        assert codec.preview_backup_file(libraries[1], path).format_version == "3"
        truncated = tmp_path / "truncated.lttbackup"
        truncated.write_bytes(path.read_bytes()[:-12])
        with pytest.raises(BackupError):
            codec.preview_backup_file(libraries[1], truncated)


def test_disk_failure_discards_partial_output(libraries, monkeypatch, tmp_path):
    monkeypatch.setattr(codec, "TemporaryDirectory", partial(TemporaryDirectory, dir=tmp_path))
    def fail(self, data):
        raise OSError("Synthetic disk full")
    monkeypatch.setattr(codec.LimitedWriter, "write", fail)
    with pytest.raises(BackupError, match="no partial"):
        with codec.create_backup_file(libraries[0]):
            pytest.fail("Failed archive published")
    assert list(tmp_path.iterdir()) == []
