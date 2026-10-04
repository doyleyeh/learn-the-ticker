"""Explicit personal-use market retrieval check; sanitized counts, no library writes."""
import argparse
import asyncio
from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo

from backend.app.data_credentials import DataCredentialStore
from backend.app.market_history import valid_symbol
from backend.app.market_retrieval import covers_boundaries, retrieve_history


def years_before(day, years):
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


async def check(*, live=False, symbol="", store=None, retrieve=retrieve_history, at=None):
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
                "instrument_type": candidate.instrument_type, "timezone": candidate.timezone,
                "close_basis": candidate.close_basis, "gaps": list(candidate.gaps)}
    covered = value.selected is not None and covers_boundaries(value.selected, start.isoformat(), end.isoformat())
    return {"status": "retrieval_passed" if covered else "blocked", "start": start.isoformat(), "end": end.isoformat(),
            "primary": summary(value.primary), "selected": summary(value.selected),
            "gaps": list(value.gaps), "yahoo_requests": value.yahoo_requests,
            "scope": "Boundary coverage only; not trading-calendar completeness, independent identity, numerical admission, storage rights or installed-app qualification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--symbol", default="")
    args = parser.parse_args()
    report = asyncio.run(check(live=args.live, symbol=args.symbol))
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "retrieval_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
