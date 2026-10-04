"""Read original cited snapshots for follow-up context without making them current evidence."""
import hashlib
import json

from backend.app.contracts import EvidenceBundle, SourcePolicy
from backend.app.evidence import factual_context
from backend.app.identity import identity_hash
from backend.app.source_registry import source_rule


MAX_HISTORY_VERSIONS = 5
MAX_HISTORY_CHARACTERS = 400_000


def citation_id(bundle_id, source_id):
    return "saved:" + hashlib.sha256(json.dumps([bundle_id, source_id]).encode()).hexdigest()


def conversation_evidence(db, asset, history):
    """Return bounded factual contexts and application-owned candidates for revalidation.

    Historical proofs remain in their original bundles. A new response may reuse their
    URLs, but must independently retrieve/admit new support before publishing facts.
    """
    contexts, candidates, seen = [], {}, set()
    remaining = MAX_HISTORY_CHARACTERS
    for message in reversed(history[-20:]):
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
        except ValueError:
            continue
        allowed = {}
        for source in bundle.sources:
            rule = source_rule(str(source.url))
            if source.asset_id == asset.id and source.verified and rule and rule.policy == source.policy == SourcePolicy.full_text:
                allowed[source.id] = source
        context["claims"] = [claim for claim in context["claims"] if claim["source_ids"] and all(sid in allowed for sid in claim["source_ids"])]
        if "financials" in context:
            context["financials"]["observations"] = [row for row in context["financials"]["observations"] if row["source_id"] in allowed]
        used = {sid for claim in context["claims"] for sid in claim["source_ids"]}
        used.update(row["source_id"] for row in context.get("financials", {}).get("observations", []))
        if not used and not context.get("context_gaps"):
            continue
        aliases = {sid: citation_id(version, sid) for sid in used}
        context["sources"] = [{**source, "id": aliases[source["id"]], "original_source_id": source["id"]}
                              for source in context["sources"] if source["id"] in used]
        for claim in context["claims"]:
            claim["source_ids"] = [aliases[sid] for sid in claim["source_ids"]]
        for row in context.get("financials", {}).get("observations", []):
            row["source_id"] = aliases[row["source_id"]]
        size = len(json.dumps(context))
        if size > remaining:
            continue
        remaining -= size
        contexts.append(context)
        candidates.update({aliases[sid]: allowed[sid].model_copy(update={"id": aliases[sid]}) for sid in used})
    return contexts, candidates
