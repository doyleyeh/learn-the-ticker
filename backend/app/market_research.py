"""Opted-in private retrieval using the production research queues and review scope."""
import asyncio
from dataclasses import replace
from datetime import timedelta
from zoneinfo import ZoneInfo

from backend.app.data_credentials import DataCredentialStore
from backend.app.market_history import MarketDataError
from backend.app.market_mapping import map_yahoo_history
from backend.app.market_retrieval import retrieve_history
from backend.app.market_returns import years_before
from backend.app.market_transport import fetch_free_eodhd_prices
from backend.app.yfinance_worker import fetch_yahoo_history, fetch_yahoo_valuations


class MarketResearch:
    def __init__(self, research, *, store_factory=DataCredentialStore, primary=fetch_free_eodhd_prices,
                 yahoo=fetch_yahoo_history, valuations=fetch_yahoo_valuations):
        self.research, self.store_factory, self.primary, self.yahoo = research, store_factory, primary, yahoo
        self.valuations = valuations

    def require_enabled(self, cancelled):
        self.research.require_consent()
        if cancelled.is_set() or not self.research.settings().experimental_yahoo_enabled:
            raise asyncio.CancelledError()

    async def retrieve(self, resolved, cancelled, review):
        service = self.research
        if not service.settings().experimental_yahoo_enabled:
            return None, ""
        if (resolved is None or resolved.asset.asset_type != "stock" or resolved.verification.authority != "openfigi-v3"
                or resolved.asset.exchange not in ("UW", "UQ", "UR", "UN")):
            return None, "Private price history is unavailable for this unqualified listing."
        symbol = resolved.asset.symbol
        primary_url, yahoo_url = f"https://eodhd.com/api/eod/{symbol}.US", f"https://finance.yahoo.com/quote/{symbol}/history/"
        valuation_url = f"https://finance.yahoo.com/quote/{symbol}/key-statistics/"
        allowed = await review.select(resolved.asset.id, [primary_url, yahoo_url, valuation_url], private_market=True)
        self.require_enabled(cancelled)
        credential = None
        try:
            if primary_url in allowed:
                credential = await service.retrieve(lambda: self.store_factory().load("eodhd"), cancelled=cancelled)
            self.require_enabled(cancelled)
            day = service.clock().astimezone(ZoneInfo("America/New_York")).date()
            # Include a prior-observation buffer for the five-year return baseline.
            start, end = years_before(day, 5) - timedelta(days=7), day - timedelta(days=1)
            async def primary(*args):
                self.require_enabled(cancelled)
                if not review.allowed(primary_url):
                    raise MarketDataError("source_review_required")
                def fetch():
                    self.require_enabled(cancelled)
                    if not review.allowed(primary_url):
                        raise MarketDataError("source_review_required")
                    return self.primary(*args, cancelled=cancelled)
                result = await service.retrieve(fetch, cancelled=cancelled)
                self.require_enabled(cancelled)
                return result
            async def yahoo(*args):
                self.require_enabled(cancelled)
                if yahoo_url not in allowed or not review.allowed(yahoo_url):
                    raise MarketDataError("source_review_required")
                # Owned worker cancellation closes its process before this slot releases.
                async with service.retrieval:
                    self.require_enabled(cancelled)
                    if not review.allowed(yahoo_url):
                        raise MarketDataError("source_review_required")
                    result = await self.yahoo(*args)
                    self.require_enabled(cancelled)
                    return result
            result = await retrieve_history(symbol, start.isoformat(), end.isoformat(), credential=credential,
                eodhd_start=years_before(day, 1).isoformat(), eodhd_fetch_async=primary, yahoo_fetch=yahoo)
            self.require_enabled(cancelled)
            if result.selected is None or result.selected.provider != "yahoo_yfinance" or not review.allowed(yahoo_url):
                return None, "Private market history is unavailable or was not selected; no equivalent retry was made."
            mapped = map_yahoo_history(result.selected, resolved, at=service.clock())
            if valuation_url not in allowed or not review.allowed(valuation_url):
                return replace(mapped, valuation_gap="not_selected"), ""
            try:
                async with service.retrieval:
                    self.require_enabled(cancelled)
                    if not review.allowed(valuation_url):
                        return replace(mapped, valuation_gap="not_selected"), ""
                    values, _ = await self.valuations(symbol, start.isoformat(), end.isoformat())
                    self.require_enabled(cancelled)
                if not review.allowed(valuation_url):
                    return replace(mapped, valuation_gap="not_selected"), ""
                if not values.points:
                    return replace(mapped, valuation_gap="no_observations"), ""
                return replace(mapped, valuations=values), ""
            except MarketDataError:
                return replace(mapped, valuation_gap="source_unavailable"), ""
        except asyncio.CancelledError:
            raise
        except InterruptedError:
            if cancelled.is_set():
                raise asyncio.CancelledError() from None
            return None, "Private market retrieval was interrupted."
        except Exception:
            return None, "Private market history could not be independently admitted. No automatic retry was made."
