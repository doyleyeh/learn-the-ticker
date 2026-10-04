"""Independent listing concordance. A mapped candidate still needs usage admission."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re

from backend.app.figi_identity import MAPPING_URL, SEARCH_URL, fetch_figi, parse_figi_response, valid_figi
from backend.app.identity import ResolvedIdentity, normalized
from backend.app.market_history import HistoryCandidate, MarketDataError

# Require both Yahoo's code and its full label, then match the exact OpenFIGI venue.
# Do not treat the US country composite or another Nasdaq tier as this listing.
YAHOO_VENUES = {
    ("NMS", "NasdaqGS"): "UW",
    ("NGM", "NasdaqGM"): "UQ",
    ("NCM", "NasdaqCM"): "UR",
    ("NYQ", "NYSE"): "UN",
}


def company_name(value):
    # Only terminal legal-form expansions, never share-class or contract removal.
    value = normalized(value).rstrip(".")
    words = value.split()
    if words:
        words[-1] = {"corporation": "corp", "incorporated": "inc", "limited": "ltd"}.get(words[-1], words[-1])
    return " ".join(words)


@dataclass(frozen=True)
class MappedHistoryCandidate:
    history: HistoryCandidate
    instrument: ResolvedIdentity
    checked_at: datetime
    association: str = "yahoo-openfigi-common-stock-v1"


def map_yahoo_history(history: HistoryCandidate, instrument: ResolvedIdentity, *, at: datetime):
    """No source/permission boolean, model assertion or ticker alone proves scope."""
    asset, proof = instrument.asset, instrument.verification
    try:
        if (at.tzinfo is None or not instrument.valid(at)
                or history.retrieved_at is None or history.retrieved_at.tzinfo is None
                or not timedelta(0) <= at - history.retrieved_at < timedelta(days=1)
                or proof.authority != "openfigi-v3" or str(proof.source_url) not in (MAPPING_URL, SEARCH_URL)
                or not valid_figi(asset.identifiers.get("figi", ""))
                or asset.id != "FIGI:" + asset.identifiers["figi"]
                or asset.asset_type != "stock" or asset.identifiers.get("openfigi_securityType2") != "Common Stock"
                or asset.identifiers.get("openfigi_marketSector") != "Equity"
                or history.provider != "yahoo_yfinance" or history.instrument_type != "EQUITY"
                or history.close_basis != "split_adjusted" or history.currency != "USD"
                or asset.currency not in (None, history.currency)
                or history.timezone != "America/New_York"
                or not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,29}", history.symbol)
                or history.symbol != asset.symbol or not history.name
                or company_name(history.name) != company_name(asset.name)
                or YAHOO_VENUES.get((history.exchange, history.exchange_label)) != asset.exchange
                or history.source_url != f"https://finance.yahoo.com/quote/{history.symbol}/history/"
                or not re.fullmatch(r"[0-9a-f]{64}", history.content_hash)):
            raise ValueError
    except (ValueError, TypeError, KeyError, AttributeError):
        raise MarketDataError("instrument_mapping_unverified") from None
    # Do not mutate the independent asset's currency or turn the candidate into a fact.
    return MappedHistoryCandidate(history, instrument, at)


def resolve_yahoo_listing(history: HistoryCandidate, *, at: datetime, fetcher=fetch_figi):
    """One public OpenFIGI lookup scoped by explicit ticker and venue, no model use."""
    venue = YAHOO_VENUES.get((history.exchange, history.exchange_label))
    if (history.provider != "yahoo_yfinance" or venue is None
            or not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,29}", history.symbol)):
        raise MarketDataError("instrument_mapping_unverified")
    try:
        payload = json.dumps([{"idType": "TICKER", "idValue": history.symbol, "exchCode": venue}]).encode()
        rows = parse_figi_response(fetcher(MAPPING_URL, payload), query=history.symbol, search=False, retrieved_at=at)
        # The exact venue response must itself be unique; do not select a resemblance.
        if len(rows) != 1:
            raise ValueError
        return map_yahoo_history(history, rows[0], at=at)
    except (ValueError, OSError):
        raise MarketDataError("instrument_mapping_unverified") from None
