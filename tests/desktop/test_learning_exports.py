import pytest
from fastapi.testclient import TestClient

from backend.app.api import create_app
from backend.app.contracts import Claim
from backend.app.db import Database
from tests.desktop.market_fixture import market_bundle
from tests.desktop.test_application import TOKEN
from tests.desktop.test_evidence_reuse import snapshot


@pytest.mark.parametrize("language", ["en", "zh-TW"])
@pytest.mark.parametrize("level", ["beginner", "intermediate"])
@pytest.mark.parametrize("private", [False, True])
def test_bilingual_exports_keep_permitted_note_references_and_filter_private_dependencies(tmp_path, language, level, private):
    bundle = market_bundle(financials=False, estimates=True) if private else snapshot(
        text="Synthetic Example Company reported revenue of 12 million USD.")
    sid = bundle.market.estimates.source_id if private else bundle.sources[0].id
    text = "The figure of 12 million USD is historical; this explanation is unverified." if language == "en" else "12 million USD 是原始歷史數字；這段說明未經獨立查證。"
    bundle = bundle.model_copy(update={"language": language, "level": level, "notes": [
        Claim(asset_id=bundle.asset.id, text=text, source_ids=[sid]),
        Claim(asset_id=bundle.asset.id, text="Generic educational interpretation.")]})
    original = bundle.model_dump(mode="json")
    db = Database("sqlite://", testing=True)
    db.put("bundle:" + bundle.id, "bundle", original)
    with TestClient(create_app(db, TOKEN, tmp_path, adapters={"codex": object()}),
                    headers={"Authorization": "Bearer " + TOKEN}) as client:
        exported = client.get("/api/export/" + bundle.id).json()
        markdown = client.get("/api/export/" + bundle.id + "?format=markdown").text
        assert exported["language"] == language and exported["level"] == level
        if private:
            assert exported["notes"] == [] and "export_notice" in exported
            assert text not in markdown and sid not in markdown
        else:
            assert exported["notes"][0]["source_ids"] == [sid]
            assert text + " References (not independent verification): " + sid in markdown
            assert "Generic educational interpretation. No source reference supplied." in markdown
            assert str(bundle.sources[0].url) in markdown and bundle.sources[0].retrieved_at.isoformat() in markdown
            assert "These notes are not factual evidence." in markdown
            assert all("excerpt" not in row for row in exported["sources"])
        assert db.get("bundle:" + bundle.id) == original
