"""Explicit read-only OpenFIGI check. No API key, inference or library writes."""
import argparse
import json

from backend.app.contracts import now
from backend.app.figi_identity import FigiIdentityResolver, IdentityChoiceRequired


def check(*, live=False, query="FIGI:BBG000BLNNH6", resolver=None):
    if not live:
        return {"status": "not_run", "reason": "Pass --live to retrieve public instrument identity metadata."}
    try:
        rows = (resolver or FigiIdentityResolver()).resolve(query)
    except IdentityChoiceRequired as exc:
        return {"status": "needs_identity", "candidate_count": len(exc.candidates),
                "reason": "Lookup is incomplete or unavailable; narrow the query or retry later explicitly."}
    except (ValueError, OSError):
        return {"status": "blocked", "reason": "Public identity validation failed; no automatic retry was made."}
    if len(rows) != 1 or not rows[0].valid(now()):
        return {"status": "needs_identity", "candidate_count": len(rows), "reason": "One independently resolved instrument is required."}
    row = rows[0]
    return {"status": "passed", "asset_id": row.asset.id, "asset_type": row.asset.asset_type,
            "source_url": str(row.verification.source_url), "authority": row.verification.authority,
            "content_hash": row.verification.content_hash, "identity_hash": row.verification.identity_hash,
            "retrieved_at": row.verification.retrieved_at.isoformat(), "currency_unconfirmed": row.asset.currency is None,
            "scope": "Identifier metadata only; no current listing status, financial values or full category qualification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--query", default="FIGI:BBG000BLNNH6")
    args = parser.parse_args()
    result = check(live=args.live, query=args.query)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
