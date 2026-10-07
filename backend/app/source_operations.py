"""Operation boundaries apply to current and historical records, not model promises."""
from urllib.parse import urlsplit

PRIVATE_NOTICE = "Yahoo numerical evidence supports personal cloud learning and same-user private backups; Yahoo data and dependent interpretations are omitted from shareable exports."


def private_source(source):
    # URL recognition prevents a legacy record or model metadata downgrade from
    # removing export restrictions. Typed numeric cloud context is separate (DEC-046).
    host = (urlsplit(str(source.url)).hostname or "").casefold()
    return (source.usage_scope == "private_yahoo_v1" or source.provenance == "market_adapter"
            or host == "finance.yahoo.com" or host.endswith(".finance.yahoo.com")
            or host == "query1.finance.yahoo.com" or host == "query2.finance.yahoo.com")


def external_claims(bundle):
    blocked_sources = {s.id for s in bundle.sources if private_source(s)}
    blocked_sources.update(ref.id for ref in bundle.context_references)
    rows = [*bundle.claims, *bundle.notes]
    blocked = {c.id for c in rows if blocked_sources.intersection(c.source_ids)}
    # Propagate through calculation references, including multi-hop derivatives.
    while True:
        next_ids = {c.id for c in rows if blocked.intersection(c.input_claim_ids)} - blocked
        if not next_ids:
            break
        blocked.update(next_ids)
    return [c for c in bundle.claims if c.id not in blocked]


def has_private_content(bundle):
    return bool(bundle.market or bundle.context_references or any(private_source(s) for s in bundle.sources))


def shareable_view(bundle):
    """A filtered rendering view, never written back as the original snapshot."""
    if not has_private_content(bundle):
        return bundle, None
    return bundle.model_copy(update={"market": None, "context_references": [], "claims": external_claims(bundle), "notes": [],
        "sources": [s for s in bundle.sources if not private_source(s)]}), PRIVATE_NOTICE
