from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.contracts import Claim, EvidenceBundle, SourcePolicy
from backend.app.db import Database
from backend.app.freshness import assess_freshness
from tests.desktop.test_application import IDENTITY, TOKEN, source
from tests.desktop.market_fixture import market_bundle

AT = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)


def snapshot(**updates):
    item = source(verified=True, content_hash="a" * 64, policy=SourcePolicy.full_text,
                  published_at=AT.date(), as_of=AT.date(), retrieved_at=AT - timedelta(hours=1))
    item = item.model_copy(update=updates)
    return EvidenceBundle(asset=IDENTITY, sources=[item], created_at=AT, state="available")


@pytest.mark.parametrize("updates, state, reason", [
    ({}, "within_age_limit", "within_age_limit"),
    ({"as_of": date(2020, 1, 1)}, "stale", "old_dates"),
    ({"published_at": date(2020, 1, 1)}, "stale", "old_dates"),
    ({"retrieved_at": AT - timedelta(days=1)}, "stale", "old_dates"),
    ({"retrieved_at": AT - timedelta(days=1) + timedelta(microseconds=1)}, "within_age_limit", "within_age_limit"),
    ({"as_of": None, "published_at": None}, "unknown", "missing_dates"),
    ({"as_of": AT.date() + timedelta(days=1)}, "unknown", "future_dates"),
    ({"retrieved_at": AT + timedelta(microseconds=1)}, "unknown", "future_dates"),
    ({"verified": False}, "unknown", "unverified"),
    ({"content_hash": ""}, "unknown", "unverified"),
    ({"asset_id": "foreign"}, "unknown", "unverified"),
    ({"policy": SourcePolicy.link}, "unknown", "rights_changed"),
])
def test_age_uses_original_dates_and_rules_not_the_new_snapshot(updates, state, reason):
    bundle = snapshot(**updates)
    before = bundle.model_dump_json()
    result = assess_freshness(bundle, at=AT)
    assert result.bundle_id == bundle.id and result.assessed_at == AT
    assert (result.sources[0].state, result.sources[0].reason) == (state, reason)
    assert result.sources[0].max_age_seconds == 86400
    assert bundle.model_dump_json() == before


def test_unregistered_rules_and_note_dates_cannot_establish_current_evidence():
    bundle = snapshot()
    bundle.sources[0].url = "https://unregistered.example/filing"
    assert assess_freshness(bundle, at=AT).sources[0].reason == "unregistered"
    bundle = snapshot(as_of=None, published_at=None)
    bundle.notes = [Claim(asset_id=IDENTITY.id, source_ids=["s1"], text="Unverified current note", as_of=AT.date())]
    assert assess_freshness(bundle, at=AT).sources[0].reason == "missing_dates"
    bundle.claims = [Claim(asset_id=IDENTITY.id, source_ids=["s1"], text="Claim without original source date", kind="fact", as_of=AT.date())]
    assert assess_freshness(bundle, at=AT).sources[0].reason == "missing_dates"


def test_original_claim_date_and_utc_day_prevent_a_false_recent_label():
    bundle = snapshot()
    bundle.claims = [Claim(asset_id=IDENTITY.id, source_ids=["s1"], text="Original dated fact", kind="fact", as_of=date(2020, 1, 1))]
    assert assess_freshness(bundle, at=AT).sources[0].state == "stale"
    bundle.claims = []
    local = datetime(2026, 10, 6, 1, tzinfo=timezone(timedelta(hours=14)))
    assert assess_freshness(bundle, at=local).sources[0].state == "within_age_limit"
    with pytest.raises(ValueError, match="timezone"):
        assess_freshness(bundle, at=AT.replace(tzinfo=None))


def test_private_numerics_use_their_registered_rules_and_keep_original_dates():
    bundle = market_bundle(valuations=True)
    before = bundle.model_dump_json()
    rows = {row.source_id: row for row in assess_freshness(bundle, at=AT).sources}
    assert rows[bundle.market.source_id].state == "stale"
    assert rows[bundle.market.valuations.source_id].state == "stale"
    assert bundle.model_dump_json() == before
    assert not assess_freshness(EvidenceBundle(asset=IDENTITY), at=AT).sources


def test_authenticated_offline_assessment_is_read_only_and_version_scoped(tmp_path, monkeypatch):
    import backend.app.freshness as freshness
    monkeypatch.setattr(freshness, "now", lambda: AT)
    db = Database("sqlite://", testing=True)
    old = snapshot(as_of=date(2020, 1, 1))
    new = snapshot()
    for bundle in (old, new):
        db.put("bundle:" + bundle.id, "bundle", bundle.model_dump(mode="json"), IDENTITY.id)
    before = db.list("bundle")
    with TestClient(create_app(db, TOKEN, tmp_path)) as client:
        path = f"/api/bundles/{old.id}/freshness"
        assert client.get(path).status_code == 401
        headers = {"Authorization": "Bearer " + TOKEN}
        assert client.get(path, headers=headers | {"Origin": "https://foreign.example"}).status_code == 403
        response = client.get(path, headers=headers)
        assert response.status_code == 200
        assert response.json()["sources"][0]["state"] == "stale"
        assert client.get(f"/api/bundles/{new.id}/freshness", headers=headers).json()["sources"][0]["state"] == "within_age_limit"
        assert client.get("/api/bundles/missing/freshness", headers=headers).status_code == 404
        assert not client.get("/api/settings", headers=headers).json()["cloud_enabled"]
        assert not db.research_jobs()
    assert db.list("bundle") == before
