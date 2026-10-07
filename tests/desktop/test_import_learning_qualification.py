import asyncio

from scripts.qualify_import_learning import check


def test_default_check_never_contacts_a_provider(monkeypatch):
    def forbidden(*args):
        raise AssertionError("No qualification or provider without explicit live flag")
    monkeypatch.setattr("scripts.qualify_import_learning.resolve_profile", forbidden)
    assert asyncio.run(check()) == {"status": "not_requested", "generation_requested": False, "live_qualified": False}


def test_sign_in_or_quota_preflight_stops_before_enforcement_or_generation(tmp_path, monkeypatch):
    async def blocked(*args):
        return {"status": "blocked", "blocker": "included_usage_unconfirmed_or_exhausted", "generation_requested": False}
    def forbidden(*args):
        raise AssertionError("Failed preflight must stop")
    monkeypatch.setattr("scripts.qualify_import_learning.preflight", blocked)
    monkeypatch.setattr("scripts.qualify_import_learning.enforcement_ready", forbidden)
    result = asyncio.run(check(live=True, profile=str(tmp_path)))
    assert result["status"] == "blocked" and not result["generation_requested"]
