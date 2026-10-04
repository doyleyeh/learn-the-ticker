import base64
import hashlib
import io
import json
import warnings
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.api import create_app
from backend.app.backup import BackupError, make_backup, preview_backup, read_backup, restore_backup
from backend.app.contracts import Source, now
from backend.app.db import Database, Event
from backend.app.evidence import candidate_metadata
from backend.app.import_documents import parse_document
from backend.app.import_previews import ImportPreview
from backend.app.retained_imports import RetainedImport, retain_import
from tests.desktop.test_backup import TOKEN, seed
from tests.desktop.test_import_documents import pdf_bytes, workbook_bytes

CSV = '公司,數值\n例子,9007199254740993\n=1+1,0.12345678901234567890\n'.encode()
URL = "https://www.sec.gov/Archives/edgar/data/1/000000000100000001/synthetic.htm"


def preview(raw=CSV, format="csv"):
    document = parse_document(raw, format, permission_confirmed=True)
    source = None
    if format == "html":
        source = candidate_metadata(Source(id="import-preview", asset_id="unassigned", url=URL, title="Imported URL", publisher="Unverified source"))
        source = source.model_copy(update={"content_hash": document.content_hash, "provenance": "user_import"})
    return ImportPreview(state="unverified", origin="public_url" if source else "local_file",
                         document=document, source=source, checked_at=now())


def retained(db, raw=CSV, format="csv"):
    return retain_import(db, raw, preview(raw, format), title="Synthetic permitted document", storage_and_backup_confirmed=True)


def rewrite(raw, *, manifest_change=None, content_change=None, member_change=None, omit=None, extra=None):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = {item.filename: archive.read(item) for item in archive.infolist()}
    manifest, data = json.loads(entries["manifest.json"]), json.loads(entries["library.json"])
    if content_change:
        content_change(data)
    entries["library.json"] = json.dumps(data).encode()
    manifest.update(content_bytes=len(entries["library.json"]), sha256=hashlib.sha256(entries["library.json"]).hexdigest())
    if manifest_change:
        manifest_change(manifest)
    entries["manifest.json"] = json.dumps(manifest).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            if omit and omit(name):
                continue
            archive.writestr(name, member_change(name, content) if member_change else content)
        if extra:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(*extra)
    return output.getvalue()


@pytest.mark.parametrize("raw,format", [(CSV, "csv"), (workbook_bytes(), "xlsx"), (pdf_bytes(), "pdf"), (b"<p>Synthetic permitted document.</p>", "html")])
def test_actual_bytes_original_locators_provenance_and_unverified_state_roundtrip(raw, format):
    source, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    document = retained(source, raw, format)
    archive = make_backup(source)
    with zipfile.ZipFile(io.BytesIO(archive)) as opened:
        names = opened.namelist()
        assert names == ["manifest.json", "library.json", "attachments/" + document.id + ".bin"]
        assert opened.read(names[-1]) == raw
        assert "content_base64" not in json.loads(opened.read("library.json"))["records"][0]["payload"]
    summary = preview_backup(target, archive)
    assert summary.format_version == "2" and summary.retained_imports == 1 and summary.attachment_bytes == len(raw)
    restore_backup(target, archive, summary.fingerprint)
    restored = RetainedImport.model_validate(target.get("import:" + document.id))
    assert restored == document and restored.content() == raw and not restored.verified
    assert not target.list("asset") and not target.list("bundle")
    assert source.get("import:" + document.id) == document.model_dump(mode="json")


def test_legacy_format_remains_readable_and_new_libraries_without_imports_stay_version_one():
    source, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    seed(source)
    archive = make_backup(source)
    with zipfile.ZipFile(io.BytesIO(archive)) as opened:
        manifest = json.loads(opened.read("manifest.json"))
        assert manifest["format_version"] == "1" and "attachments" not in manifest
    summary = preview_backup(target, archive)
    assert summary.retained_imports == summary.attachment_bytes == 0
    restore_backup(target, archive, summary.fingerprint)
    assert len(target.list("asset")) == 1


@pytest.mark.parametrize("confirmed", [False, None, 1, "yes"])
def test_processing_permission_does_not_authorize_storage_or_backup(confirmed):
    db = Database("sqlite://", testing=True)
    with pytest.raises(ValueError, match="Explicit"):
        retain_import(db, CSV, preview(), title="Permission boundary", storage_and_backup_confirmed=confirmed)
    assert not db.list("import")


def test_link_only_and_changed_bytes_cannot_be_retained():
    db = Database("sqlite://", testing=True)
    with pytest.raises(ValueError, match="bounded"):
        retain_import(db, CSV, ImportPreview(state="link_only", origin="public_url", checked_at=now()), title="Link", storage_and_backup_confirmed=True)
    with pytest.raises(ValueError, match="checksum"):
        retain_import(db, CSV + b"changed", preview(), title="Changed", storage_and_backup_confirmed=True)
    assert not db.list("import")


def test_immutable_imports_cannot_gain_verification_or_change_content():
    db = Database("sqlite://", testing=True)
    original = retained(db)
    payload = original.model_dump(mode="json")
    with pytest.raises(ValueError, match="immutable"):
        db.put("import:" + original.id, "import", {**payload, "title": "Replacement"})
    with pytest.raises(ValueError):
        db.put("import:" + original.id, "import", {**payload, "verified": True})
    assert db.get("import:" + original.id) == payload


@pytest.mark.parametrize("mutate", [
    lambda row: row.update(storage_and_backup_confirmed=False),
    lambda row: row.update(storage_and_backup_confirmed=1),
    lambda row: row.update(verified=True),
    lambda row: row.update(provider_token="not-portable"),
    lambda row: row.update(byte_count=1),
    lambda row: row.update(content_base64="%%%"),
    lambda row: row.update(content_base64=base64.b64encode(b"changed").decode()),
    lambda row: row.update(id="../../auth"),
    lambda row: row.update(source={}),
    lambda row: row.update(retained_at="2000-01-01T00:00:00Z"),
    lambda row: row["document"].update(verified=True),
    lambda row: row["document"].update(limitations=[]),
    lambda row: row["document"].update(blocks=[{"locator": "row 1", "text": "x" * 200001}]),
])
def test_storage_rejects_invalid_bytes_identity_permissions_and_untrusted_promotion(mutate):
    db = Database("sqlite://", testing=True)
    document = retained(db)
    data = document.model_dump(mode="json")
    mutate(data)
    with pytest.raises(ValueError):
        RetainedImport.model_validate(data)


@pytest.mark.parametrize("corrupt", [
    lambda raw: rewrite(raw, omit=lambda name: name.startswith("attachments/")),
    lambda raw: rewrite(raw, extra=("../outside", b"untrusted")),
    lambda raw: rewrite(raw, extra=("library.json", b"duplicate")),
    lambda raw: rewrite(raw, extra=("attachments/unregistered.bin", b"untrusted")),
    lambda raw: rewrite(raw, member_change=lambda name, data: b"changed" if name.startswith("attachments/") else data),
    lambda raw: rewrite(raw, manifest_change=lambda m: m.update(format_version="1")),
    lambda raw: rewrite(raw, manifest_change=lambda m: m["attachments"][0].update(id="../../outside")),
    lambda raw: rewrite(raw, manifest_change=lambda m: m["attachments"].append(m["attachments"][0])),
    lambda raw: rewrite(raw, manifest_change=lambda m: m["attachments"][0].update(sha256="0" * 64)),
    lambda raw: rewrite(raw, content_change=lambda d: d["records"][0]["payload"].update(content_base64=None)),
    lambda raw: rewrite(raw, content_change=lambda d: d["records"][0]["payload"].update(document=[])),
    lambda raw: rewrite(raw, content_change=lambda d: d["records"][0]["payload"]["document"].update(content_hash="0" * 64)),
    lambda raw: rewrite(raw, content_change=lambda d: d["records"][0].update(parent_id="asset:foreign")),
    lambda raw: rewrite(raw, content_change=lambda d: d["records"][0].update(id="import:missing")),
    lambda raw: rewrite(raw, content_change=lambda d: d.update(records=[])),
])
def test_corrupt_archive_has_no_partial_restore_or_file_extraction(corrupt, tmp_path, monkeypatch):
    source, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    retained(source)
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    invalid = corrupt(make_backup(source))
    with pytest.raises(BackupError):
        restore_backup(target, invalid, hashlib.sha256(invalid).hexdigest())
    assert not target.list("import") and set(tmp_path.iterdir()) == before


@pytest.mark.parametrize("mutate", [
    lambda source: source.update(url="https://example.invalid/unregistered"),
    lambda source: source.update(policy="link_only"),
    lambda source: source.update(verified=True),
    lambda source: source.update(published_at="2026-01-01"),
    lambda source: source.update(asset_id="claimed-identity"),
    lambda source: source.update(content_hash="0" * 64),
    lambda source: source.update(excerpt="self-attested fact"),
    lambda source: source.update(url=URL + "?access_token=private"),
])
def test_url_retention_and_restore_require_current_registered_rights_without_self_attestation(mutate):
    db = Database("sqlite://", testing=True)
    retained(db, b"<p>Synthetic</p>", "html")
    raw = rewrite(make_backup(db), content_change=lambda d: mutate(d["records"][0]["payload"]["source"]))
    with pytest.raises(BackupError):
        read_backup(raw)


def test_capacity_checks_prevent_unbackable_growth(monkeypatch):
    import backend.app.retained_imports as imports
    import backend.app.backup as backups
    db = Database("sqlite://", testing=True)
    retained(db)
    monkeypatch.setattr(imports, "MAX_ATTACHMENTS", 1)
    with pytest.raises(ValueError, match="capacity"):
        retained(db)
    monkeypatch.setattr(imports, "MAX_ATTACHMENTS", 100)
    monkeypatch.setattr(imports, "MAX_ATTACHMENT_BYTES", len(CSV))
    with pytest.raises(ValueError, match="capacity"):
        retained(db)
    monkeypatch.setattr(backups, "MAX_ATTACHMENT_BYTES", len(CSV) - 1)
    with pytest.raises(BackupError):
        make_backup(db)
    assert len(db.list("import")) == 1


def test_archive_member_and_manifest_bounds_are_enforced_before_reading(monkeypatch):
    import backend.app.backup as backups
    db = Database("sqlite://", testing=True)
    retained(db)
    archive = make_backup(db)
    with pytest.raises(BackupError):
        read_backup(rewrite(archive, manifest_change=lambda m: m["attachments"][0].update(byte_count=len(CSV) - 1)))
    monkeypatch.setattr(backups, "MAX_MANIFEST_BYTES", 20)
    with pytest.raises(BackupError, match="size"):
        read_backup(archive)


def test_revoked_url_rights_prevent_backup_and_restore(monkeypatch):
    import backend.app.retained_imports as imports
    db = Database("sqlite://", testing=True)
    retained(db, b"<p>Synthetic</p>", "html")
    archive = make_backup(db)
    monkeypatch.setattr(imports, "source_rule", lambda _: None)
    with pytest.raises(BackupError):
        read_backup(archive)
    with pytest.raises(BackupError):
        make_backup(db)


def test_restore_rolls_back_attachments_with_failed_library_write_and_rejects_nonempty_target():
    source, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    seed(source)
    retained(source)
    raw = make_backup(source)
    summary = preview_backup(target, raw)
    def fail(*args):
        raise RuntimeError("Synthetic write failure")
    event.listen(Event, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="Synthetic"):
            restore_backup(target, raw, summary.fingerprint)
    finally:
        event.remove(Event, "before_insert", fail)
    assert not target.list("import") and not target.list("asset") and not target.list("settings")
    retained(target)
    with pytest.raises(BackupError, match="empty library"):
        restore_backup(target, raw, summary.fingerprint)


def test_authenticated_archive_api_reports_and_restores_retained_documents_without_exposing_them_in_summary(tmp_path):
    source, target = Database("sqlite://", testing=True), Database("sqlite://", testing=True)
    document = retained(source)
    headers = {"Authorization": "Bearer " + TOKEN}
    raw = make_backup(source)
    with TestClient(create_app(target, TOKEN, tmp_path)) as client:
        assert client.post("/api/library/restore/preview", content=raw).status_code == 401
        response = client.post("/api/library/restore/preview", headers=headers, content=raw)
        summary = response.json()
        assert summary["retained_imports"] == 1 and summary["attachment_bytes"] == len(CSV)
        assert document.content_base64 not in response.text and "9007199254740993" not in response.text
        result = client.post("/api/library/restore", headers=headers | {"X-Backup-Fingerprint": summary["fingerprint"]}, content=raw)
        assert result.status_code == 200
    assert RetainedImport.model_validate(target.get("import:" + document.id)) == document
