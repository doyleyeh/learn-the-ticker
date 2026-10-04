"""Explicit, bounded public SEC identity check. No provider or library writes."""
import argparse
import json

from backend.app.identity import SecIdentityResolver


def check(*, live=False, query="MSFT", resolver=None):
    if not live:
        return {"status": "not_run", "reason": "Pass --live with a configured local SEC contact to retrieve public identity metadata."}
    resolver = resolver or SecIdentityResolver()
    try:
        rows = resolver.resolve(query)
    except (ValueError, OSError):
        return {"status": "blocked", "reason": "Public identity retrieval or validation failed; no automatic retry was made."}
    if len(rows) != 1:
        return {"status": "blocked", "reason": "A configured contact and one independently resolved listing are required."}
    row = rows[0]
    return {"status": "passed", "source_url": str(row.verification.source_url), "authority": row.verification.authority,
            "content_hash": row.verification.content_hash, "identity_hash": row.verification.identity_hash,
            "retrieved_at": row.verification.retrieved_at.isoformat(), "type_unconfirmed": row.asset.asset_type == "unknown",
            "scope": "Public listing identity only; no financial, subscription or release qualification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--query", default="MSFT")
    args = parser.parse_args()
    result = check(live=args.live, query=args.query)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
