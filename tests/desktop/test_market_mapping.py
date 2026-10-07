from dataclasses import replace
from datetime import timedelta
import json

import pytest

from backend.app.identity import ResolvedIdentity, identity_hash
from backend.app.market_history import MarketDataError, parse_yahoo_chart
from backend.app.market_mapping import map_yahoo_history, resolve_yahoo_listing
from tests.desktop.test_figi_identity import document, record
from tests.desktop.test_market_history import yahoo, result, START, END
from tests.desktop.test_structured_financials import identities
from tests.desktop.test_sec_financials import AT


def history():
    data = yahoo()
    result(data)["meta"].update({"symbol": "SYN", "longName": "Synthetic company", "fullExchangeName": "NasdaqGS"})
    return replace(parse_yahoo_chart(json.dumps(data).encode(), "SYN", START, END), retrieved_at=AT)


def test_independent_exact_venue_and_class_proof_is_preserved_without_fact_promotion():
    instrument, _ = identities()
    value = map_yahoo_history(history(), instrument, at=AT)
    assert value.instrument is instrument and value.history.source_url.endswith("/SYN/history/")
    assert value.instrument.asset.currency is None
    assert value.history.currency == "USD" and "instrument_mapping_unverified" in value.history.gaps


@pytest.mark.parametrize("changes", [
    {"symbol": "OTHER"}, {"provider": "eodhd"}, {"instrument_type": "ETF"}, {"currency": "EUR"},
    {"exchange": "NYQ"}, {"exchange_label": "NasdaqGM"}, {"exchange_label": None},
    {"name": "Synthetic company Class B"}, {"timezone": "UTC"}, {"close_basis": "unadjusted"},
    {"retrieved_at": None}, {"retrieved_at": AT - timedelta(days=1)},
    {"retrieved_at": AT + timedelta(seconds=1)}, {"retrieved_at": AT.replace(tzinfo=None)},
    {"content_hash": "invalid"}, {"source_url": "https://example.com/"},
])
def test_mismatched_provider_scope_is_not_a_mapped_candidate(changes):
    with pytest.raises(MarketDataError, match="instrument_mapping_unverified"):
        map_yahoo_history(replace(history(), **changes), identities()[0], at=AT)


@pytest.mark.parametrize("changes", [
    {"symbol": "OTHER"}, {"exchange": "US"}, {"exchange": "UQ"}, {"exchange": "UN"},
    {"asset_type": "unknown"}, {"asset_type": "fund"}, {"name": "Different company"},
    {"currency": "EUR"}, {"id": "FIGI:wrong"}, {"identifiers": {"figi": "WRONG"}},
])
def test_country_composites_other_venues_and_asset_types_cannot_match(changes):
    instrument, _ = identities()
    asset = instrument.asset.model_copy(update=changes)
    proof = instrument.verification.model_copy(update={"identity_hash": identity_hash(asset)})
    with pytest.raises(MarketDataError):
        map_yahoo_history(history(), ResolvedIdentity(asset, proof), at=AT)


def test_expired_or_model_attested_identity_cannot_certify_mapping():
    instrument, _ = identities()
    for changes in ({"authority": "agent"}, {"source_url": "https://example.com/"},
                    {"retrieved_at": AT - timedelta(days=1)}, {"identity_hash": "a" * 64}):
        with pytest.raises(MarketDataError):
            map_yahoo_history(history(), ResolvedIdentity(instrument.asset,
                instrument.verification.model_copy(update=changes)), at=AT)


def test_legal_form_expansion_does_not_erase_security_classes():
    instrument, _ = identities()
    asset = instrument.asset.model_copy(update={"name": "Synthetic Corp"})
    proof = instrument.verification.model_copy(update={"identity_hash": identity_hash(asset)})
    mapped = ResolvedIdentity(asset, proof)
    map_yahoo_history(replace(history(), name="Synthetic Corporation"), mapped, at=AT)
    with pytest.raises(MarketDataError):
        map_yahoo_history(replace(history(), name="Synthetic Corporation Class A"), mapped, at=AT)


def test_lookup_uses_exact_venue_and_rejects_ambiguous_or_different_results():
    calls = []
    def fetch(url, body):
        calls.append((url, json.loads(body)))
        return document([record(exchCode="UW")])
    mapped = resolve_yahoo_listing(history(), at=AT, fetcher=fetch)
    assert mapped.instrument.asset.exchange == "UW"
    assert calls == [("https://api.openfigi.com/v3/mapping", [{"idType": "TICKER", "idValue": "SYN", "exchCode": "UW"}])]
    for rows in ([], [record(exchCode="UQ")], [record(exchCode="UW"), record(exchCode="UN")]):
        with pytest.raises(MarketDataError):
            resolve_yahoo_listing(history(), at=AT, fetcher=lambda *args: document(rows))


def test_no_lookup_with_unknown_venue_or_provider_and_no_raw_network_error():
    def forbidden(*args):
        pytest.fail("unscoped network request")
    with pytest.raises(MarketDataError):
        resolve_yahoo_listing(replace(history(), exchange_label=None), at=AT, fetcher=forbidden)
    def unavailable(*args):
        raise OSError("private raw diagnostic")
    with pytest.raises(MarketDataError, match="^instrument_mapping_unverified$"):
        resolve_yahoo_listing(history(), at=AT, fetcher=unavailable)
