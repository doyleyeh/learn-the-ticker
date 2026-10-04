"""Synthetic retained documents for explicit PostgreSQL restore checks only."""
from backend.app.contracts import Source, now
from backend.app.evidence import candidate_metadata
from backend.app.import_previews import ImportPreview
from backend.app.import_worker import extract_document
from backend.app.retained_imports import retain_import
from tests.desktop.test_import_documents import pdf_bytes, workbook_bytes


async def retain_synthetic_documents(db):
    inputs = [("csv", '公司,數值\n例子,9007199254740993\n=1+1,0.12345678901234567890\n'.encode()),
              ("xlsx", workbook_bytes()), ("pdf", pdf_bytes()),
              ("html", b"<p>Synthetic permitted source. Unverified import.</p>")]
    retained = []
    for format, raw in inputs:
        document = await extract_document(raw, format, permission_confirmed=True)
        source = None
        if format == "html":
            source = candidate_metadata(Source(id="import-preview", asset_id="unassigned",
                url="https://www.sec.gov/Archives/edgar/data/1/000000000100000001/synthetic.htm",
                title="Synthetic imported URL", publisher="Unverified source"))
            source = source.model_copy(update={"content_hash": document.content_hash, "provenance": "user_import"})
        preview = ImportPreview(state="unverified", origin="public_url" if source else "local_file",
                                source=source, document=document, checked_at=now())
        retained.append(retain_import(db, raw, preview, title="Synthetic " + format, storage_and_backup_confirmed=True))
    return retained
