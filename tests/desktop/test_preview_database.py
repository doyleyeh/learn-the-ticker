from concurrent.futures import ThreadPoolExecutor

from tests.desktop.preview_server import preview_database


def test_preview_reads_cannot_observe_or_rollback_another_request_transaction(tmp_path):
    db = preview_database(tmp_path)
    try:
        db.put("settings", "settings", {"cloud_enabled": True})
        with db.session.begin() as session:
            db._put(session, "settings", "settings", {"cloud_enabled": True, "experimental_yahoo_enabled": True})
            db._put(session, "saved:example", "saved", {"title": "synthetic bookmark"})
            session.flush()
            with ThreadPoolExecutor(max_workers=1) as pool:
                assert pool.submit(db.get, "settings").result(timeout=3) == {"cloud_enabled": True}
                assert pool.submit(db.get, "saved:example").result(timeout=3) is None
        assert db.get("settings")["experimental_yahoo_enabled"] is True
        assert db.get("saved:example")["title"] == "synthetic bookmark"
    finally:
        db.engine.dispose()
