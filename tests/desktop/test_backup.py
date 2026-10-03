import hashlib
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.api import create_app
from backend.app.backup import BackupError, make_backup, preview_backup, read_backup, restore_backup
from backend.app.contracts import AssetIdentity, Claim, Conversation, EvidenceBundle, RuntimeEvent, SavedResearch, Settings, Source, SourcePolicy
from backend.app.db import Database, Event, Job, Record

TOKEN = "backup-test-session-" * 4


def seed(db):
    identity = AssetIdentity(id="TEST:TRANSFER", symbol="TRANSFER", name="Synthetic transfer example", asset_type="other")
    source = Source(id="portable-source", asset_id=identity.id, url="https://www.sec.gov/synthetic", title="Synthetic portable evidence", publisher="Test", policy=SourcePolicy.summary, provenance="user_import", verified=True, excerpt="Synthetic transfer example has portable evidence.")
    bundle = EvidenceBundle(asset=identity, sources=[source], claims=[Claim(asset_id=identity.id, text=source.excerpt, kind="fact", source_ids=[source.id])])
    original = bundle.model_dump(mode="json")
    db.put("bundle:" + bundle.id, "bundle", original, identity.id)
    db.put("asset:" + identity.id, "asset", original)
    report = SavedResearch(bundle_id=bundle.id, title="Saved transfer research")
    db.put("saved:" + report.id, "saved", report.model_dump(mode="json"), identity.id)
    chat = Conversation(asset_id=identity.id, bookmarked=True)
    db.put("conversation:" + chat.id, "conversation", chat.model_dump(mode="json"))
    db.put("settings", "settings", Settings(cloud_enabled=True, start_at_login=True, language="zh-TW").model_dump(mode="json"))
    with db.session.begin() as session:
        session.add(Job(id="pending", status="running", request={"query": "A synthetic question", "asset_id": identity.id, "conversation_id": chat.id}))
    with db.session.begin() as session:
        session.add(Event(job_id="pending", payload=RuntimeEvent(run_id="pending", kind="run.started").model_dump(mode="json")))
    return bundle.id


def alter(raw, *, change=None, manifest_change=None, extra=None):
    with zipfile.ZipFile(io.BytesIO(raw)) as original:
        content = json.loads(original.read("library.json"))
        manifest = json.loads(original.read("manifest.json"))
    if change:
        change(content)
    payload = json.dumps(content).encode()
    manifest.update(content_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    if manifest_change:
        manifest_change(manifest)
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("library.json", payload)
        if extra:
            archive.writestr(extra, "Never extract this file")
    return result.getvalue()


def test_backup_roundtrip_preserves_evidence_and_prevents_subscription_replay(monkeypatch):
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda *args: pytest.fail("Backup must not read credentials"))
    monkeypatch.setenv("OPENAI_API_KEY", "test-excluded-secret")
    source = Database("sqlite://", testing=True)
    target = Database("sqlite://", testing=True)
    bundle_id = seed(source)
    raw = make_backup(source)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert archive.namelist() == ["manifest.json", "library.json"]
        assert "test-excluded-secret" not in archive.read("library.json").decode()
    summary = preview_backup(target, raw)
    assert summary.can_restore and summary.assets == 1 and summary.evidence_versions == 1 and summary.saved_reports == 1
    restore_backup(target, raw, summary.fingerprint)
    assert target.get("bundle:" + bundle_id) == source.get("bundle:" + bundle_id)
    assert target.list("conversation")[0]["bookmarked"]
    assert target.get("settings")["language"] == "zh-TW"
    assert not target.get("settings")["cloud_enabled"] and not target.get("settings")["start_at_login"]
    assert target.job("pending")["status"] == "interrupted"
    assert len(target.events("pending")) == 1
    assert target.expire_conversations(180) == 0


def test_restore_never_overwrites_newer_work_or_accepts_a_changed_archive():
    source = Database("sqlite://", testing=True)
    seed(source)
    target = Database("sqlite://", testing=True)
    raw = make_backup(source)
    preview = preview_backup(target, raw)
    with pytest.raises(BackupError, match="changed after preview"):
        restore_backup(target, raw, "wrong-fingerprint")
    assert not target.list("asset")
    newer_id = seed(target)
    with pytest.raises(BackupError, match="empty library"):
        restore_backup(target, raw, preview.fingerprint)
    assert target.get("bundle:" + newer_id)
    assert target.get("settings")["cloud_enabled"]


@pytest.mark.parametrize("corrupt", [
    lambda raw: b"not a zip archive",
    lambda raw: raw[:40],
    lambda raw: alter(raw, extra="../auth.json"),
    lambda raw: alter(raw, manifest_change=lambda manifest: manifest.update(format_version="2")),
    lambda raw: alter(raw, manifest_change=lambda manifest: manifest.update(sha256="0" * 64)),
    lambda raw: alter(raw, change=lambda data: data["records"].append(data["records"][0])),
    lambda raw: alter(raw, change=lambda data: data["records"].append({"id": "credentials", "kind": "credentials", "parent_id": None, "updated_at": "2026-01-01T00:00:00Z", "payload": {"token": "not-portable"}})),
    lambda raw: alter(raw, change=lambda data: next(row for row in data["records"] if row["kind"] == "settings")["payload"].update(api_key="not-portable")),
    lambda raw: alter(raw, change=lambda data: next(row for row in data["records"] if row["kind"] == "saved")["payload"].update(bundle_id="missing")),
    lambda raw: alter(raw, change=lambda data: data["events"][0]["payload"]["data"].update(token="not-portable")),
])
def test_malformed_or_unsafe_archive_is_rejected_without_writes(corrupt):
    db = Database("sqlite://", testing=True)
    seed(db)
    target = Database("sqlite://", testing=True)
    raw = corrupt(make_backup(db))
    with pytest.raises(BackupError):
        preview_backup(target, raw)
    assert not target.list("asset") and not target.list("settings")


def test_failed_restore_rolls_back_settings_and_every_record():
    source = Database("sqlite://", testing=True)
    seed(source)
    raw = make_backup(source)
    target = Database("sqlite://", testing=True)
    target.put("settings", "settings", Settings(language="en").model_dump(mode="json"))
    original_settings = target.get("settings")

    def fail_write(*args):
        raise RuntimeError("Simulated restore failure")

    event.listen(Event, "before_insert", fail_write)
    try:
        with pytest.raises(RuntimeError, match="Simulated restore"):
            restore_backup(target, raw, preview_backup(target, raw).fingerprint)
    finally:
        event.remove(Event, "before_insert", fail_write)
    assert not target.list("asset") and not target.list("bundle") and not target.job("pending")
    assert target.get("settings") == original_settings


def test_authenticated_backup_preview_and_restore_endpoints(tmp_path):
    source = Database("sqlite://", testing=True)
    seed(source)
    headers = {"Authorization": "Bearer " + TOKEN}
    with TestClient(create_app(source, TOKEN, tmp_path)) as client:
        assert client.get("/api/library/backup").status_code == 401
        result = client.get("/api/library/backup", headers=headers)
        assert result.status_code == 200 and result.headers["content-type"] == "application/zip"
        archive = result.content
        preview = client.post("/api/library/restore/preview", headers=headers, content=archive)
        assert not preview.json()["can_restore"]
    target = Database("sqlite://", testing=True)
    with TestClient(create_app(target, TOKEN, tmp_path / "new")) as client:
        preview = client.post("/api/library/restore/preview", headers=headers, content=archive).json()
        restored = client.post("/api/library/restore", headers=headers | {"X-Backup-Fingerprint": preview["fingerprint"]}, content=archive)
        assert restored.status_code == 200 and restored.json()["restored"]
        assert len(client.get("/api/library", headers=headers).json()) == 1
        assert not client.get("/api/settings", headers=headers).json()["cloud_enabled"]
