"""Synthetic retained documents for explicit PostgreSQL restore checks only."""
from backend.app.contracts import Source, now
from backend.app.evidence import candidate_metadata
from backend.app.import_previews import ImportPreview
from backend.app.import_worker import extract_document
from backend.app.retained_imports import retain_import
from tests.desktop.test_import_documents import pdf_bytes, workbook_bytes
import asyncio
import json
from backend.app.contracts import RuntimeEvent


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


class ImportLearningFixture:
    """No provider connection. Quotes only the supplied synthetic parsed context."""
    def __init__(self, delay=1):
        self.delay = delay

    async def stream(self, prompt, run_id, workspace, model=None, *, allow_browsing=True):
        assert not allow_browsing
        context = json.loads(prompt.split("\nUNTRUSTED DOCUMENT: ", 1)[1])
        locator, quote = next(iter(context["passages"].items()))
        quote = quote[:500]
        explanation = "這是文件內容的未驗證解讀。引用保留了原始文字。" if "in zh-TW" in prompt else "This is an unverified interpretation of the document. The reference preserves its original text."
        await asyncio.sleep(self.delay)
        yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({"explanation": explanation, "references": [{"locator": locator, "quote": quote}]}))


async def explain_synthetic_document(db, item, workspace):
    from backend.app.import_learning import ImportLearningRequest
    from backend.app.import_learning_service import ImportLearning
    from backend.app.import_previews import ImportPreviews
    from backend.app.import_storage import ImportStorage
    from backend.app.research import ResearchService
    service = ResearchService(db, {"codex": ImportLearningFixture()}, workspace)
    learning = ImportLearning(service, ImportStorage(ImportPreviews(service)))
    request = ImportLearningRequest(document_id=item.id, content_hash=item.document.content_hash, transmission_confirmed=True)
    job = await learning.submit(request)
    await service.tasks[job["id"]]
    result = db.job(job["id"])
    assert result["status"] == "completed"
    await service.close()
    return result
