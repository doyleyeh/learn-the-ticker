"""Explicit bounded candidate coverage check; no library writes or model calls."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
from zoneinfo import ZoneInfo

from backend.app.market_returns import years_before
from backend.app.yfinance_worker import fetch_yahoo_valuations
from backend.app.market_history import MarketDataError, valid_symbol


async def check(symbol):
    valid_symbol(symbol)
    day = datetime.now(timezone.utc).astimezone(ZoneInfo("America/New_York")).date()
    start, end = years_before(day, 5), day - timedelta(days=1)
    try:
        candidate, requests = await fetch_yahoo_valuations(symbol, start.isoformat(), end.isoformat())
    except MarketDataError as exc:
        return {"status": "unavailable", "code": str(exc), "retried": False}
    series = []
    for metric, sampling in sorted({(p.metric, p.sampling) for p in candidate.points}):
        rows = [p for p in candidate.points if (p.metric, p.sampling) == (metric, sampling)]
        series.append({"metric": metric, "sampling": sampling, "observations": len(rows),
            "available": sum(p.value is not None for p in rows), "first": rows[0].date, "last": rows[-1].date})
    return {"status": "candidate_retrieved", "admitted": False, "source": candidate.source_url,
        "retrieved_at": candidate.retrieved_at.isoformat(), "sha256": candidate.content_hash,
        "requested_start": start.isoformat(), "requested_end": end.isoformat(), "requests": requests, "series": series}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--symbol")
    args = parser.parse_args()
    if not args.live:
        print(json.dumps({"status": "not_run", "network": False}))
        return 0
    if not args.symbol:
        parser.error("--symbol is required with --live")
    result = asyncio.run(check(args.symbol))
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "candidate_retrieved" else 2


if __name__ == "__main__":
    raise SystemExit(main())
