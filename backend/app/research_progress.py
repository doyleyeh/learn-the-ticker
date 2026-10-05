"""Only independently admitted material can form a durable section checkpoint."""
from backend.app.contracts import SourcePolicy
from backend.app.identity import ResolvedIdentity


def validate_checkpoint(bundle):
    from backend.app.evidence import admit_bundle, validate_claim_sources
    if (bundle.state != "partial" or bundle.notes or not bundle.identity_verification
            or not ResolvedIdentity(bundle.asset, bundle.identity_verification).valid(bundle.created_at)
            or not (bundle.claims or (bundle.financials and bundle.financials.observations) or bundle.market)):
        raise ValueError("Section checkpoints require independently admitted evidence")
    numeric_ids = ({bundle.market.source_id} | ({bundle.market.valuations.source_id} if bundle.market.valuations else set())) if bundle.market else set()
    narrative = [s for s in bundle.sources if s.id not in numeric_ids]
    if any(not source.verified or source.policy != SourcePolicy.full_text
           or source.provenance not in ("verified_retrieval", "structured_adapter") for source in narrative):
        raise ValueError("Section checkpoints cannot expose candidate sources")
    admitted = admit_bundle(bundle.asset, narrative, bundle.claims,
        identity_verification=bundle.identity_verification, language=bundle.language,
        level=bundle.level, created_at=bundle.created_at, financials=bundle.financials)
    if admitted.claims != bundle.claims or admitted.notes:
        raise ValueError("Section claims must pass the same independent support gate")
    validate_claim_sources(bundle)
