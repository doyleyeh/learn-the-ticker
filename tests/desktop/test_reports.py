from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.api import create_app
from backend.app.backup import make_backup, preview_backup, read_backup, restore_backup
from backend.app.contracts import Settings, uid
from backend.app.db import Database
from backend.app.reports import ReportRequest, build_report, create_report
from tests.desktop.financial_fixture import AT, financial_bundle
from tests.desktop.test_backup import alter
from tests.desktop.weekly_fixture import weekly_bundle

TOKEN = "synthetic-report-session-" * 3
AS_OF = AT + timedelta(hours=12)


def seed(bundle=None):
    db = Database("sqlite://", testing=True)
    bundle = bundle or weekly_bundle()
    db.put("bundle:" + bundle.id, "bundle", bundle.model_dump(mode="json"), bundle.asset.id)
    db.put("asset:" + bundle.asset.id, "asset", bundle.model_dump(mode="json"))
    db.put("settings", "settings", Settings(cloud_enabled=True).model_dump(mode="json"))
    return db, bundle


def test_historical_report_does_not_require_news_or_recalculate_original_financials():
    bundle = financial_bundle()
    before = bundle.model_dump(mode="json")
    result = build_report(bundle, created_at=AS_OF)
    assert result.bundle_id == bundle.id and result.focus.weekly == []
    assert result.reading_guide is None and result.guide_source_ids == []
    assert result.evidence_saved_at == bundle.created_at
    assert bundle.model_dump(mode="json") == before


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_reading_guide_requires_two_weekly_items_and_excludes_earlier_context(count):
    report = build_report(weekly_bundle(["2026-09-30"] * count + ["2026-09-17"]), created_at=AS_OF)
    assert bool(report.reading_guide) == (count >= 2)
    assert report.guide_source_ids == ([item.source_id for item in report.focus.weekly] if count >= 2 else [])
    assert not set(report.guide_source_ids).intersection(item.source_id for item in report.focus.earlier)


def test_immutable_report_api_original_version_restore_exports_and_offline_no_generation(tmp_path, monkeypatch):
    db, bundle = seed()
    monkeypatch.setattr("backend.app.reports.now", lambda: AS_OF)
    with TestClient(create_app(db, TOKEN, tmp_path)) as client:
        assert client.post("/api/reports", json={"bundle_id": bundle.id}).status_code == 401
        client.headers["Authorization"] = "Bearer " + TOKEN
        response = client.post("/api/reports", json={"bundle_id": bundle.id})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert len(payload["focus"]["weekly"]) == 2 and len(payload["focus"]["earlier"]) == 1
        assert payload["guide_source_ids"] == ["dated-1", "dated-0"]
        with pytest.raises(ValueError, match="immutable"):
            db.put("report:" + payload["id"], "report", {**payload, "created_at": (AS_OF + timedelta(seconds=1)).isoformat()}, bundle.id)
        newer = bundle.model_copy(update={"id": uid()})
        db.put("bundle:" + newer.id, "bundle", newer.model_dump(mode="json"), newer.asset.id)
        db.put("asset:" + newer.asset.id, "asset", newer.model_dump(mode="json"))
        archive = make_backup(db)
        target = Database("sqlite://", testing=True)
        preview = preview_backup(target, archive)
        assert preview.dated_reports == 1
        restore_backup(target, archive, preview.fingerprint)
        assert target.get("report:" + payload["id"]) == payload
        assert target.get("asset:" + bundle.asset.id)["id"] == newer.id
        db.put("settings", "settings", Settings().model_dump(mode="json"))
        def never(*a, **kw):
            raise AssertionError("A read or export regenerated report selection")
        monkeypatch.setattr("backend.app.reports.build_report", never)
        monkeypatch.setattr("backend.app.reports.select_weekly", never)
        assert client.get("/api/reports/" + payload["id"]).json() == payload
        assert client.get("/api/reports").json()[0]["bundle_id"] == bundle.id
        assert client.post("/api/reports", json={"bundle_id": bundle.id}).status_code == 409
        exported = client.get(f'/api/reports/{payload["id"]}/export').json()
        assert exported["report"] == payload and exported["evidence"]["id"] == bundle.id
        assert all("excerpt" not in source for source in exported["evidence"]["sources"])
        markdown = client.get(f'/api/reports/{payload["id"]}/export?format=markdown').text
        for expected in ("Earlier context (excluded from weekly counts)", "2026-09-17", "Weekly analysis", "dated-0", "Filing-date reference", "9007199254740992"):
            assert expected in markdown
        assert client.get("/api/reports/missing").status_code == 404
        assert client.get(f'/api/reports/{payload["id"]}/export?format=html').status_code == 400


@pytest.mark.parametrize("change", ["guide", "threshold", "bucket", "date", "source", "fingerprint", "missing", "parent"])
def test_report_archive_cannot_reassign_or_rewrite_derived_context(change, monkeypatch):
    db, bundle = seed()
    monkeypatch.setattr("backend.app.reports.now", lambda: AS_OF)
    create_report(db, ReportRequest(bundle_id=bundle.id))
    archive = make_backup(db)
    def mutate(data):
        record = next(row for row in data["records"] if row["kind"] == "report")
        value = record["payload"]
        if change == "guide": value["reading_guide"] = "Unsupported advice"
        elif change == "threshold": value["focus"]["analysis_available"] = False
        elif change == "bucket": value["focus"]["weekly"].extend(value["focus"]["earlier"])
        elif change == "date": value["focus"]["weekly"][0]["published"] = "2026-10-04"
        elif change == "source": value["guide_source_ids"] = ["missing"]
        elif change == "fingerprint": value["fingerprint"] = "a" * 64
        elif change == "parent": record["parent_id"] = "other"
        else: data["records"] = [row for row in data["records"] if row["id"] != "bundle:" + bundle.id]
    with pytest.raises(ValueError):
        read_backup(alter(archive, change=mutate))


def test_report_rejects_future_incomplete_or_missing_evidence_and_rolls_back_failed_write():
    db, bundle = seed()
    with pytest.raises(ValueError):
        build_report(bundle, created_at=AT - timedelta(seconds=1))
    incomplete = financial_bundle().model_copy(update={"completion": "section_checkpoint"})
    with pytest.raises(ValueError, match="completed original page"):
        build_report(incomplete, created_at=AS_OF)
    with pytest.raises(ValueError):
        create_report(db, ReportRequest(bundle_id="absent"))
    def fail(*a):
        raise RuntimeError("Interrupted report publication")
    event.listen(db.engine, "commit", fail)
    try:
        with pytest.raises(RuntimeError):
            create_report(db, ReportRequest(bundle_id=bundle.id))
    finally:
        event.remove(db.engine, "commit", fail)
    assert not db.list("report")


def test_report_exports_reuse_private_market_filter(tmp_path):
    from tests.desktop.test_market_evidence import market_bundle
    db, bundle = seed(market_bundle())
    report = create_report(db, ReportRequest(bundle_id=bundle.id))
    with TestClient(create_app(db, TOKEN, tmp_path)) as client:
        client.headers["Authorization"] = "Bearer " + TOKEN
        value = client.get(f"/api/reports/{report.id}/export").json()
        assert "market" not in value["evidence"] and "Yahoo" in value["evidence"]["export_notice"]
        assert not value["report"]["focus"]["weekly"]
