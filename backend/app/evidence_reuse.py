"""Read original cited snapshots for follow-up context without making them current evidence."""
import hashlib
import json

from backend.app.contracts import ContextReference, EvidenceBundle, SourcePolicy
from backend.app.evidence import factual_context
from backend.app.identity import identity_hash
from backend.app.source_registry import source_rule


MAX_HISTORY_VERSIONS = 5
MAX_HISTORY_CHARACTERS = 400_000


def citation_id(bundle_id, source_id):
    return "saved:" + hashlib.sha256(json.dumps([bundle_id, source_id]).encode()).hexdigest()


def market_source_ids(context):
    market = context.get("market")
    return ({market["source_id"]} | ({market["valuations"]["source_id"]} if market.get("valuations") else set())) if market else set()


def alias_context(context, aliases):
    context["sources"] = [{**source, "id": aliases.get(source["id"], source["id"]), "original_source_id": source["id"]}
                          for source in context["sources"]]
    for claim in context["claims"]:
        claim["source_ids"] = [aliases.get(sid, sid) for sid in claim["source_ids"]]
    for row in context.get("financials", {}).get("observations", []):
        row["source_id"] = aliases.get(row["source_id"], row["source_id"])
    for row in context.get("financials", {}).get("ratios", []):
        row["source_ids"] = [aliases.get(sid, sid) for sid in row["source_ids"]]
    if context.get("market"):
        market = context["market"]
        market["source_id"] = aliases.get(market["source_id"], market["source_id"])
        for row in market["returns"]:
            row["source_id"] = aliases.get(row["source_id"], row["source_id"])
        if market.get("valuations"):
            values = market["valuations"]
            values["source_id"] = aliases.get(values["source_id"], values["source_id"])
    return context


def cached_context(bundle):
    context = factual_context(bundle)
    return alias_context(context, {sid: citation_id(bundle.id, sid) for sid in market_source_ids(context)})


def context_references(contexts):
    return {source["id"]: ContextReference(id=source["id"], bundle_id=context["bundle_id"], source_id=source["original_source_id"])
            for context in contexts for source in context["sources"] if source["id"] in market_source_ids(context)}


def admit_numeric_interpretations(bundle, claims, references):
    """Model wording can cite typed numbers, but never becomes a new numerical fact."""
    from backend.safety import find_forbidden_output_phrases
    available = {source.id for source in bundle.sources if source.verified} | references.keys()
    numeric = market_source_ids(factual_context(bundle)) | references.keys()
    existing = {claim.id for claim in [*bundle.claims, *bundle.notes]}
    for claim in claims:
        if (claim.id in existing or claim.asset_id != bundle.asset.id or not numeric.intersection(claim.source_ids)
                or set(claim.source_ids) - available or find_forbidden_output_phrases(claim.text)):
            continue
        bundle.notes.append(claim.model_copy(update={"kind": "unverified_note", "value": None, "unit": None, "input_claim_ids": []}))
        existing.add(claim.id)
    # Retain provenance even if the model omits a citation: an unattributed
    # interpretation of this context must not bypass the export boundary.
    bundle.context_references = list(references.values())
    return bundle


def filter_market_context(context, permitted):
    """Apply current source review without modifying the saved version."""
    market = context.get("market")
    if not market:
        return context
    ids = market_source_ids(context)
    if market["source_id"] not in permitted:
        context.pop("market")
        context.pop("market_description", None)
    elif market.get("valuations") and market["valuations"]["source_id"] not in permitted:
        market["valuations"] = None
        market["valuation_gap"] = "not_selected"
    keep = market_source_ids(context)
    context["sources"] = [source for source in context["sources"] if source["id"] not in ids or source["id"] in keep]
    return context


def validate_context_references(bundle, lookup):
    """Resolve original references from the same library/restore transaction."""
    from backend.app.evidence import validate_claim_sources
    for ref in bundle.context_references:
        payload = lookup(ref.bundle_id)
        if not payload:
            raise ValueError("Original numerical evidence is missing")
        original = payload if isinstance(payload, EvidenceBundle) else EvidenceBundle.model_validate(payload)
        validate_claim_sources(original)
        if (original.id != ref.bundle_id or identity_hash(original.asset) != identity_hash(bundle.asset)
                or original.created_at > bundle.created_at
                or ref.source_id not in market_source_ids(factual_context(original))):
            raise ValueError("Original numerical citation does not match its evidence")


def conversation_evidence(db, asset, history):
    """Return bounded factual contexts and application-owned candidates for revalidation.

    Historical proofs remain in their original bundles. A new response may reuse their
    URLs, but must independently retrieve/admit new support before publishing facts.
    """
    contexts, candidates, seen = [], {}, set()
    remaining = MAX_HISTORY_CHARACTERS
    pending = list(reversed(history[-20:]))
    while pending:
        message = pending.pop(0)
        if message.get("role") == "scope":
            break
        if message.get("role") != "assistant" or message.get("asset_id") != asset.id:
            continue
        version = message.get("bundle_id")
        if not isinstance(version, str) or version in seen:
            continue
        seen.add(version)
        if len(seen) > MAX_HISTORY_VERSIONS:
            break
        payload = db.get("bundle:" + version)
        if not payload:
            continue
        try:
            bundle = EvidenceBundle.model_validate(payload)
            if bundle.id != version or identity_hash(bundle.asset) != identity_hash(asset):
                continue
            context = factual_context(bundle)
            validate_context_references(bundle, lambda bid: db.get("bundle:" + bid))
        except ValueError:
            continue
        # A recent interpretation may point to a numerical version older than
        # the transcript window. Follow its original evidence, never its prose.
        versions = dict.fromkeys(ref.bundle_id for ref in bundle.context_references)
        pending[:0] = [{"role": "assistant", "asset_id": asset.id, "bundle_id": bid} for bid in versions if bid not in seen]
        allowed = {}
        for source in bundle.sources:
            rule = source_rule(str(source.url))
            if source.asset_id == asset.id and source.verified and (source.id in market_source_ids(context)
                    or (rule and rule.policy == source.policy == SourcePolicy.full_text)):
                allowed[source.id] = source
        context["claims"] = [claim for claim in context["claims"] if claim["source_ids"] and all(sid in allowed for sid in claim["source_ids"])]
        if "financials" in context:
            context["financials"]["observations"] = [row for row in context["financials"]["observations"] if row["source_id"] in allowed]
            if "ratios" in context["financials"]:
                context["financials"]["ratios"] = [row for row in context["financials"]["ratios"]
                    if row["source_ids"] and all(sid in allowed for sid in row["source_ids"])]
        used = {sid for claim in context["claims"] for sid in claim["source_ids"]}
        used.update(row["source_id"] for row in context.get("financials", {}).get("observations", []))
        used.update(market_source_ids(context))
        if not used and not context.get("context_gaps"):
            continue
        aliases = {sid: citation_id(version, sid) for sid in used}
        context["sources"] = [source for source in context["sources"] if source["id"] in used]
        alias_context(context, aliases)
        size = len(json.dumps(context))
        if size > remaining:
            continue
        remaining -= size
        contexts.append(context)
        candidates.update({aliases[sid]: allowed[sid].model_copy(update={"id": aliases[sid]}) for sid in used})
    return contexts, candidates
