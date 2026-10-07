"""Explicit private Yahoo candidate check; metadata only, no library or model call."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json

from backend.app.market_history import MarketDataError, valid_symbol
from backend.app.yfinance_worker import fetch_yahoo_estimates


async def qualify(symbol):
    valid_symbol(symbol)
    end = datetime.now(timezone.utc).date() - timedelta(days=1)
    candidate, requests = await fetch_yahoo_estimates(symbol, (end - timedelta(days=1)).isoformat(), end.isoformat())
    return {"provider": "yahoo_yfinance", "symbol": symbol, "requests": requests,
        "retrieved_at": candidate.retrieved_at.isoformat(), "content_hash": candidate.content_hash,
        "points": len(candidate.points), "usable": sum(p.reason is None for p in candidate.points),
        "periods": sorted({p.period for p in candidate.points}),
        "currencies": sorted({p.currency for p in candidate.points if p.currency}),
        "gaps": sorted({p.reason for p in candidate.points if p.reason}),
        "publication_time": "unknown", "library_admission": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--symbol", default="NVDA")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(asyncio.run(qualify(args.symbol)), sort_keys=True))
        return 0
    except MarketDataError:
        # No raw payload, exception text or provider diagnostic crosses stdout.
        print(json.dumps({"qualified": False, "reason": "estimate_candidate_unavailable"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
