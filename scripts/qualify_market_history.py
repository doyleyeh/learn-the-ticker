"""Explicit personal-use market retrieval check; sanitized counts, no library writes."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
from zoneinfo import ZoneInfo

from backend.app.data_credentials import DataCredentialStore
from backend.app.market_history import valid_symbol
from backend.app.market_retrieval import covers_boundaries, retrieve_history
from backend.app.market_mapping import resolve_yahoo_listing


def years_before(day, years):
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


async def check(*, live=False, symbol="", store=None, retrieve=retrieve_history, at=None,
                check_mapping=False, resolve=resolve_yahoo_listing):
    if not live:
        return {"status": "not_run", "reason": "Pass --live and --symbol after deterministic verification."}
    try:
        valid_symbol(symbol)
        day = (at or datetime.now(ZoneInfo("America/New_York"))).astimezone(ZoneInfo("America/New_York")).date()
        end, start = day - timedelta(days=1), years_before(day, 5)
        credential = (store or DataCredentialStore()).load("eodhd")
        value = await retrieve(symbol, start.isoformat(), end.isoformat(), credential=credential,
                               eodhd_start=years_before(day, 1).isoformat())
    except Exception:
        return {"status": "blocked", "reason": "History check unavailable; no automatic retry or library write."}
    def summary(candidate):
        if candidate is None:
            return None
        return {"provider": candidate.provider, "symbol": candidate.symbol, "source_url": candidate.source_url,
                "sha256": candidate.content_hash, "rows": len(candidate.bars), "actions": len(candidate.actions),
                "first_date": candidate.bars[0].date if candidate.bars else None,
                "last_date": candidate.bars[-1].date if candidate.bars else None,
                "currency": candidate.currency, "exchange": candidate.exchange,
                "exchange_label": candidate.exchange_label,
                "instrument_type": candidate.instrument_type, "timezone": candidate.timezone,
                "close_basis": candidate.close_basis, "gaps": list(candidate.gaps),
                "retrieved_at": candidate.retrieved_at.isoformat() if candidate.retrieved_at else None}
    covered = value.selected is not None and covers_boundaries(value.selected, start.isoformat(), end.isoformat())
    mapping = None
    if covered and check_mapping:
        try:
            mapped = resolve(value.selected, at=at or datetime.now(timezone.utc))
            mapping = {"status": "matched", "association": mapped.association,
                "asset_id": mapped.instrument.asset.id, "exchange": mapped.instrument.asset.exchange,
                "identity_hash": mapped.instrument.verification.identity_hash,
                "identity_source_hash": mapped.instrument.verification.content_hash,
                "checked_at": mapped.checked_at.isoformat()}
        except Exception:
            mapping = {"status": "unverified"}
    passed = covered and (not check_mapping or mapping["status"] == "matched")
    return {"status": "retrieval_passed" if passed else "blocked", "start": start.isoformat(), "end": end.isoformat(),
            "primary": summary(value.primary), "selected": summary(value.selected),
            "gaps": list(value.gaps), "yahoo_requests": value.yahoo_requests, "mapping": mapping,
            "scope": "Candidate retrieval and optional independent listing match only; not calendar completeness, numerical admission, storage rights or installed-app qualification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--symbol", default="")
    parser.add_argument("--check-mapping", action="store_true")
    args = parser.parse_args()
    report = asyncio.run(check(live=args.live, symbol=args.symbol, check_mapping=args.check_mapping))
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "retrieval_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
