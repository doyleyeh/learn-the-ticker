"""Explicit SEC financial normalization check; never publishes instrument facts."""
import argparse
import json

from backend.app.structured_financials import SecFinancialAdapter


def check(*, live=False, query="", adapter=None):
    if not live:
        return {"status": "not_run", "reason": "Pass --live and an exact instrument identity with local SEC contact configured."}
    try:
        result = (adapter or SecFinancialAdapter()).retrieve(query)
    except (ValueError, OSError):
        return {"status": "blocked", "reason": "Structured retrieval could not be verified; no automatic retry was made."}
    summaries = [{"concept": row.concept, "count": len(row.observations),
                  "periods": sorted({o.period for o in row.observations}), "units": sorted({o.unit for o in row.observations}),
                  "source_hashes": sorted({o.source_hash for o in row.observations}),
                  "latest_period_end": max((o.end.isoformat() for o in row.observations), default=None),
                  "latest_filed": max((o.filed.isoformat() for o in row.observations), default=None)} for row in result.concepts]
    passed = result.instrument is not None and result.issuer is not None and any(row["count"] for row in summaries)
    return {"status": "passed" if passed else "blocked", "gaps": list(result.gaps), "concepts": summaries,
            "instrument_identity_hash": result.instrument.verification.identity_hash if result.instrument else None,
            "issuer_identity_hash": result.issuer.verification.identity_hash if result.issuer else None,
            "scope": "Partial issuer history only; no price/corporate-action, pipeline, subscription or release qualification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--query", default="")
    args = parser.parse_args()
    report = check(live=args.live, query=args.query)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
