import asyncio
import hashlib
import json
from types import SimpleNamespace
from urllib.parse import quote

import pytest
from sqlalchemy import select

from backend.app.contracts import Settings
from backend.app.db import Database, Record
from backend.app.import_documents import parse_document
from backend.app.import_previews import ImportPreviews
from backend.app.import_storage import ImportStorage, RetainMetadata
from tests.desktop.test_import_documents import pdf_bytes, workbook_bytes
from tests.desktop.test_import_previews import FILING, HEADERS, enable_online, preview_app as preview_app

CSV = 'Metric,Value\nRevenue,9007199254740993\n文字,保留\n'.encode()
FILE_ROUTE = "/api/imports/retain/file?format=csv&permission_confirmed=true"


def metadata(raw=CSV, **overrides):
    return {"title": "保留的來源", "preview_hash": hashlib.sha256(raw).hexdigest(), "storage_and_backup_confirmed": True, **overrides}


def headers(raw=CSV, **overrides):
    return HEADERS | {"X-Import-Metadata": quote(json.dumps(metadata(raw, **overrides), ensure_ascii=False))}


@pytest.mark.parametrize("raw,format", [(CSV, "csv"), (workbook_bytes(), "xlsx"), (pdf_bytes(), "pdf")], ids=["csv", "xlsx", "pdf"])
def test_storage_and_reopen_through_authenticated_transport_keep_original_references_and_no_facts(preview_app, raw, format):
    app, client, db = preview_app
    result = client.post(f"/api/imports/retain/file?format={format}&permission_confirmed=true", content=raw, headers=headers(raw))
    assert result.status_code == 200, result.text
    item = result.json()
    assert item["title"] == "保留的來源" and item["format"] == format and item["verified"] is False
    assert "content_base64" not in result.text and "blocks" not in result.text
    assert result.headers["cache-control"] == "no-store"
    listing = client.get("/api/imports/retained", headers=HEADERS)
    assert listing.json() == [item] and "content_base64" not in listing.text
    opened = client.get("/api/imports/retained/" + item["id"], headers=HEADERS)
    assert opened.status_code == 200 and opened.json()["item"] == item
    assert opened.json()["document"] == parse_document(raw, format, permission_confirmed=True).model_dump(mode="json")
    assert not app.state.imports.active and not db.list("bundle") and not db.list("asset")


def test_auth_origin_and_explicit_custom_header_preflight(preview_app):
    _, client, db = preview_app
    assert client.post(FILE_ROUTE, content=CSV).status_code == 401
    assert client.get("/api/imports/retained").status_code == 401
    assert client.get("/api/imports/retained/unknown").status_code == 401
    assert client.post(FILE_ROUTE, content=CSV, headers=headers() | {"Origin": "https://bad.example"}).status_code == 403
    allowed = client.options(FILE_ROUTE, headers={"Origin": "http://tauri.localhost", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type,x-import-metadata"})
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://tauri.localhost"
    assert not db.list("import")


@pytest.mark.parametrize("change", [
    {"storage_and_backup_confirmed": False}, {"storage_and_backup_confirmed": 1},
    {"preview_hash": "0" * 64}, {"title": ""}, {"title": "x" * 201},
    {"title": "private\nvalue"}, {"verified": True}, {"source": {"verified": True}},
])
def test_rejected_storage_metadata_never_writes_or_echoes_private_input(preview_app, change):
    _, client, db = preview_app
    response = client.post(FILE_ROUTE, content=CSV, headers=headers(**change))
    assert response.status_code == 400 and "private" not in response.text and len(response.text) < 300
    assert not db.list("import")


@pytest.mark.parametrize("route,content,extra", [
    ("/api/imports/retain/file?format=csv", CSV, {}),
    ("/api/imports/retain/file?format=html&permission_confirmed=true", CSV, {}),
    (FILE_ROUTE, CSV, {"X-Import-Metadata": "%invalid"}),
    (FILE_ROUTE, CSV, {"X-Import-Metadata": "x" * 4097}),
    (FILE_ROUTE, b"x" * (5 * 1024 * 1024 + 1), {}),
], ids=["permission", "format", "metadata", "metadata-limit", "input-limit"])
def test_storage_request_limits(preview_app, route, content, extra):
    _, client, db = preview_app
    result = client.post(route, content=content, headers=headers() | extra)
    assert result.status_code == 400 and not db.list("import")


def test_url_rechecks_bytes_rights_cloud_and_retains_original_source_then_reopens_offline(preview_app):
    app, client, db = preview_app
    raw = b"<p>Synthetic original text. Value 123.</p>"
    body = metadata(raw) | {"url": FILING}
    route = "/api/imports/retain/url"
    assert client.post(route, json=body, headers=HEADERS).status_code == 400
    enable_online(db)
    app.state.imports.resolver = lambda _: "93.184.216.34"
    calls = []
    app.state.imports.fetcher = lambda url: calls.append(url) or raw
    changed = client.post(route, json={**body, "preview_hash": "0" * 64}, headers=HEADERS)
    assert changed.status_code == 400 and not db.list("import")
    stored = client.post(route, json=body, headers=HEADERS).json()
    assert stored["source"]["url"] == FILING and stored["source"]["published_at"] is None
    assert stored["source"]["verified"] is False and stored["source"]["as_of"] is None
    db.put("settings", "settings", Settings(cloud_enabled=False).model_dump(mode="json"))
    opened = client.get("/api/imports/retained/" + stored["id"], headers=HEADERS)
    assert opened.status_code == 200 and opened.json()["item"] == stored
    assert calls == [FILING, FILING] and not db.list("bundle")


def test_link_only_cannot_be_retained_and_never_downloads_content(preview_app):
    app, client, db = preview_app
    enable_online(db)
    app.state.imports.resolver = lambda _: "93.184.216.34"
    response = client.post("/api/imports/retain/url", json=metadata() | {"url": "https://unknown.example/source"}, headers=HEADERS)
    assert response.status_code == 400 and not db.list("import")


def test_view_reparses_original_bytes_and_rejects_tampered_extraction(preview_app):
    _, client, db = preview_app
    item = client.post(FILE_ROUTE, content=CSV, headers=headers()).json()
    with db.session.begin() as session:
        row = session.scalar(select(Record).where(Record.kind == "import"))
        changed = json.loads(json.dumps(row.payload))
        changed["document"]["blocks"][0]["cells"][0]["text"] = "INJECTED extracted content"
        row.payload = changed
    response = client.get("/api/imports/retained/" + item["id"], headers=HEADERS)
    assert response.status_code == 400 and "INJECTED" not in response.text


def test_capacity_error_is_bounded_and_does_not_discard_prior_documents(preview_app, monkeypatch):
    import backend.app.retained_imports as retained
    _, client, db = preview_app
    item = client.post(FILE_ROUTE, content=CSV, headers=headers()).json()
    monkeypatch.setattr(retained, "MAX_ATTACHMENTS", 1)
    response = client.post(FILE_ROUTE, content=CSV, headers=headers())
    assert response.status_code == 400 and "100 documents" in response.text
    assert db.list("import")[0]["id"] == item["id"] and len(db.list("import")) == 1


def test_cancellation_during_reparse_prevents_retention():
    async def scenario():
        db = Database("sqlite://", testing=True)
        started, stopped = asyncio.Event(), asyncio.Event()
        async def extractor(*args, **kwargs):
            started.set()
            try:
                await asyncio.Future()
            finally:
                stopped.set()
        previews = ImportPreviews(SimpleNamespace(db=db, retrieval=asyncio.Semaphore(2)), extractor=extractor)
        task = asyncio.create_task(ImportStorage(previews).file(CSV, "csv", RetainMetadata(**metadata())))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert stopped.is_set() and not previews.active and not db.list("import")
    asyncio.run(scenario())


def test_rights_revocation_before_view_fails_without_reparsing(preview_app, monkeypatch):
    import backend.app.retained_imports as retained
    app, client, db = preview_app
    enable_online(db)
    raw = b"<p>Synthetic original</p>"
    app.state.imports.resolver = lambda _: "93.184.216.34"
    app.state.imports.fetcher = lambda _: raw
    item = client.post("/api/imports/retain/url", json=metadata(raw) | {"url": FILING}, headers=HEADERS).json()
    monkeypatch.setattr(retained, "source_rule", lambda _: None)
    async def forbidden(*args, **kwargs):
        pytest.fail("Revoked content must not be parsed")
    app.state.imports.extractor = forbidden
    response = client.get("/api/imports/retained/" + item["id"], headers=HEADERS)
    assert response.status_code == 400


def test_queue_limits_apply_to_retained_reads(preview_app):
    app, client, _ = preview_app
    item = client.post(FILE_ROUTE, content=CSV, headers=headers()).json()
    # Fixed synthetic sentinels exercise the guard without launching work.
    app.state.imports.active = {number: False for number in range(20)}
    try:
        response = client.get("/api/imports/retained/" + item["id"], headers=HEADERS)
        assert response.status_code == 400 and "queue" in response.text
    finally:
        app.state.imports.active.clear()
