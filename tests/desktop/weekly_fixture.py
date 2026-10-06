"""Date-proven synthetic filing inputs; never a live coverage claim."""
import json

from backend.app.contracts import Claim, EvidenceBundle, Source
from backend.app.evidence import verify_candidate
from backend.app.sec_filings import parse_filings
from tests.desktop.financial_fixture import AT, financial_bundle, financial_result


def weekly_bundle(days=("2026-09-30", "2026-10-01", "2026-09-17")):
    bundle, issuer = financial_bundle(), financial_result().issuer
    sources, claims = list(bundle.sources), []
    for index, day in enumerate(days):
        raw = json.dumps({"cik": issuer.asset.identifiers["cik"], "name": issuer.asset.name, "filings": {"recent": {
            "accessionNumber": [f"0000000001-26-{index + 10:06}"], "filingDate": [day], "reportDate": [day],
            "form": ["8-K"], "primaryDocument": [f"event{index}.htm"]}}}).encode()
        proof = parse_filings(raw, issuer, retrieved_at=AT)[0]
        quote = f"SYNTHETIC COMPANY reported material event {index + 1}."
        source = verify_candidate(Source(id=f"dated-{index}", asset_id=issuer.asset.id, url=proof.document_url,
            title="Untrusted title ignored", publisher="candidate"), issuer.asset, lambda _: quote)
        source = source.model_copy(update={"asset_id": bundle.asset.id, "retrieved_at": AT,
            "published_at": proof.filed, "as_of": proof.report_date, "filing_publication": proof})
        sources.append(source)
        claims.append(Claim(id=f"news-{index}", asset_id=bundle.asset.id, section="news", kind="fact", text=quote, source_ids=[source.id]))
    return EvidenceBundle.model_validate({**bundle.model_dump(), "sources": sources, "claims": claims})
