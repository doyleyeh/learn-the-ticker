"""Synthetic scale inputs; never a provider, public data set or user library."""
import hashlib
import io
import random
from datetime import datetime, timedelta, timezone

from backend.app.contracts import AssetIdentity, Claim, Conversation, EvidenceBundle, IdentityVerification, ResearchRequest, SavedResearch, Settings, Source, SourcePolicy
from backend.app.db import Job
from backend.app.identity import identity_hash
from backend.app.reports import build_report
from tests.desktop.test_import_documents import pdf_bytes

AT = datetime(2026, 10, 1, tzinfo=timezone.utc)


def seed_assets(db, count=1000):
    """Publish two cited versions per asset through the production transaction."""
    db.put("settings", "settings", Settings(cloud_enabled=True, start_at_login=True).model_dump(mode="json"))
    for index in range(count):
        identity = AssetIdentity(id=f"TEST:SCALE:{index:04}", symbol=f"SYN{index:04}",
            name=f"Synthetic scale company {index:04}", asset_type="other")
        original = None
        for version in range(2):
            at = AT + timedelta(days=version)
            excerpt = f"Synthetic scale company {index:04} published test record version {version}."
            source = Source(id=f"source-{index}-{version}", asset_id=identity.id,
                url=f"https://www.sec.gov/synthetic-scale/{index}/{version}",
                title="Synthetic scale evidence", publisher="Synthetic fixture",
                policy=SourcePolicy.summary, provenance="user_import", verified=True,
                content_hash=hashlib.sha256(excerpt.encode()).hexdigest(), excerpt=excerpt,
                retrieved_at=at, published_at=at.date(), as_of=at.date())
            bundle = EvidenceBundle(id=f"scale-{index}-{version}", asset=identity,
                identity_verification=IdentityVerification(authority="synthetic-scale", source_url="https://identity.example/scale",
                    retrieved_at=at, content_hash="a" * 64, identity_hash=identity_hash(identity)),
                created_at=at, level="beginner", sources=[source], claims=[Claim(
                    id=f"claim-{index}-{version}", asset_id=identity.id, kind="fact",
                    text=excerpt, as_of=at.date(), source_ids=[source.id])])
            job_id = f"scale-job-{index}-{version}"
            with db.session.begin() as session:
                session.add(Job(id=job_id, status="running", created_at=at,
                    request=ResearchRequest(query=identity.id, asset_id=identity.id).model_dump(mode="json")))
            db.complete_research(job_id, bundle.model_dump(mode="json"))
            if version == 0:
                original = bundle
        if index % 10 == 0:
            saved = SavedResearch(bundle_id=original.id, title=f"Older scale version {index}")
            db.put("saved:" + saved.id, "saved", saved.model_dump(mode="json"), identity.id)
            chat = Conversation(asset_id=identity.id, context_bundle_id=original.id, bookmarked=True,
                messages=[{"role": "assistant", "asset_id": identity.id, "bundle_id": original.id}])
            db.put("conversation:" + chat.id, "conversation", chat.model_dump(mode="json"))
            report = build_report(original, created_at=AT + timedelta(days=2))
            db.put("report:" + report.id, "report", report.model_dump(mode="json"), original.id)


def substantial_pdf(index):
    """One text page with a deterministic 3 MiB uncompressed RGB image.

    Noncompressible synthetic pixels exercise archive byte volume instead of
    turning tens of MiB of repeated padding into a tiny ZIP. No external assets.
    """
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject
    writer = PdfWriter()
    writer.add_page(PdfReader(io.BytesIO(pdf_bytes()), strict=True).pages[0])
    page = writer.pages[0]
    bitmap = DecodedStreamObject()
    bitmap.set_data(random.Random(index).randbytes(1024 * 1024 * 3))
    bitmap.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
        NameObject("/Width"): NumberObject(1024), NameObject("/Height"): NumberObject(1024),
        NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8)})
    page["/Resources"][NameObject("/XObject")] = DictionaryObject({NameObject("/ScaleImage"): writer._add_object(bitmap)})
    content = DecodedStreamObject()
    content.set_data(page.get_contents().get_data() + b"\nq 50 0 0 50 10 10 cm /ScaleImage Do Q")
    page[NameObject("/Contents")] = writer._add_object(content)
    output = io.BytesIO()
    writer.write(output)
    writer.close()
    return output.getvalue()


async def seed_attachments(db):
    from backend.app.contracts import now
    from backend.app.import_previews import ImportPreview
    from backend.app.import_worker import extract_document
    from backend.app.retained_imports import retain_import
    from tests.desktop.import_fixture import retain_synthetic_documents
    documents = await retain_synthetic_documents(db)
    for index in range(20):
        raw = substantial_pdf(index)
        parsed = await extract_document(raw, "pdf", permission_confirmed=True)
        preview = ImportPreview(state="unverified", origin="local_file", document=parsed, checked_at=now())
        documents.append(retain_import(db, raw, preview, title=f"Synthetic scale PDF {index}",
            storage_and_backup_confirmed=True))
    return {item.id: (item.byte_count, item.document.content_hash) for item in documents}
