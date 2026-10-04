import json
import threading
from datetime import timedelta

import pytest

from backend.app.figi_identity import parse_figi_response
from backend.app.evidence import SourceFetchError
from backend.app.identity import ResolvedIdentity, identity_hash, parse_sec_listings
from backend.app.structured_financials import SecFinancialAdapter, matching_issuer
from tests.desktop.test_figi_identity import document, record
from tests.desktop.test_identity import listing_bytes
from tests.desktop.test_sec_financials import AT, entry, raw


def identities():
    instrument = parse_figi_response(document([record(exchCode="UW")]), query="SYN", search=False, retrieved_at=AT)[0]
    issuer = parse_sec_listings(listing_bytes([[1, "SYNTHETIC COMPANY", "SYN", "Nasdaq"]]), AT)[0]
    return instrument, issuer


class Resolver:
    def __init__(self, instrument=None, issuer=None):
        first, second = identities()
        self.instrument, self.issuer = instrument or first, issuer or second
        self.sec = self
        self.calls = []

    def resolve(self, query):
        self.calls.append(query)
        return [self.issuer] if query == "SYN" else [self.instrument]


def test_association_keeps_both_proofs_without_modifying_instrument_identifiers():
    instrument, issuer = identities()
    assert matching_issuer(instrument, [issuer], at=AT) == issuer
    assert "cik" not in instrument.asset.identifiers
    assert not matching_issuer(instrument, [issuer, issuer], at=AT)
    assert not matching_issuer(instrument, [issuer], at=AT + timedelta(days=2))


@pytest.mark.parametrize("attributes", [
    {"name": "SYNTHETIC COMPANY INC"}, {"symbol": "DIFFERENT"}, {"exchange": "US"},
    {"exchange": "UN"}, {"asset_type": "unknown"}, {"asset_type": "etf"},
    {"identifiers": {"openfigi_securityType2": "Preferred Stock"}},
])
def test_resemblance_composite_and_unreviewed_types_cannot_establish_issuer(attributes):
    instrument, issuer = identities()
    asset = instrument.asset.model_copy(update=attributes)
    proof = instrument.verification.model_copy(update={"identity_hash": identity_hash(asset)})
    assert matching_issuer(ResolvedIdentity(asset, proof), [issuer], at=AT) is None


def test_foreign_authority_and_wrong_listing_reference_fail():
    instrument, issuer = identities()
    for field, value in (("authority", "agent"), ("source_url", "https://example.com/")):
        assert matching_issuer(instrument, [ResolvedIdentity(issuer.asset, issuer.verification.model_copy(update={field: value}))], at=AT) is None
    asset = issuer.asset.model_copy(update={"id": "WRONG:SYN"})
    assert matching_issuer(instrument, [ResolvedIdentity(asset, issuer.verification.model_copy(update={"identity_hash": identity_hash(asset)}))], at=AT) is None


def test_partial_financials_are_normalized_with_original_source_scope_and_explicit_gaps():
    calls = []
    def fetch(url, **kwargs):
        calls.append((url, kwargs))
        concept = url.rsplit("/", 1)[-1].removesuffix(".json")
        if concept == "Assets":
            return raw(concept=concept, units={"USD": [{key: value for key, value in entry().items() if key != "start"}]})
        if concept == "Revenues":
            return raw()
        raise OSError("PRIVATE rate-limit diagnostic")
    resolver = Resolver()
    result = SecFinancialAdapter(resolver, fetch, clock=lambda: AT).retrieve("FIGI:chosen", concepts=("Assets", "Revenues", "NetIncomeLoss"))
    assert len(result.concepts) == 2 and all(row.cik == result.issuer.asset.identifiers["cik"] for row in result.concepts)
    assert resolver.calls == ["FIGI:chosen", "SYN"]
    assert "cik" not in result.instrument.asset.identifiers
    assert all(url.startswith("https://data.sec.gov/api/xbrl/companyconcept/CIK0000000001/us-gaap/") and kwargs == {"accept": "application/json"} for url, kwargs in calls)
    assert "NetIncomeLoss:source_unavailable_or_invalid" in result.gaps
    assert "price_history_unavailable" in result.gaps and "corporate_actions_unavailable" in result.gaps
    assert "PRIVATE" not in repr(result)


def test_scope_failure_stops_before_financial_retrieval():
    instrument, _ = identities()
    unconfirmed = instrument.asset.model_copy(update={"exchange": "US"})
    instrument = ResolvedIdentity(unconfirmed, instrument.verification.model_copy(update={"identity_hash": identity_hash(unconfirmed)}))
    adapter = SecFinancialAdapter(Resolver(instrument=instrument), lambda *a, **kw: pytest.fail("No issuer proof"), clock=lambda: AT)
    result = adapter.retrieve("FIGI:chosen")
    assert not result.concepts and result.issuer is None and "issuer_instrument_association_unconfirmed" in result.gaps


def test_prepared_review_scope_expires_or_rejects_different_instrument_before_fetch():
    at = [AT]
    calls = []
    adapter = SecFinancialAdapter(Resolver(), lambda *a, **kw: calls.append(a) or raw(), clock=lambda: at[0])
    prepared = adapter.prepare("FIGI:chosen")
    assert prepared.issuer and not calls
    other = prepared.instrument.asset.model_copy(update={"id": "foreign"})
    with pytest.raises(ValueError, match="scope"):
        adapter.retrieve("FIGI:chosen", prepared=prepared, resolved=ResolvedIdentity(other, prepared.instrument.verification))
    at[0] += timedelta(days=2)
    with pytest.raises(ValueError, match="scope"):
        adapter.retrieve("FIGI:chosen", prepared=prepared)
    assert not calls


def test_identity_dates_are_checked_after_retrieval_completes():
    tick = [AT]
    class AdvancingResolver(Resolver):
        def resolve(self, query):
            tick[0] += timedelta(seconds=1)
            row = super().resolve(query)[0]
            return [ResolvedIdentity(row.asset, row.verification.model_copy(update={"retrieved_at": tick[0]}))]
    adapter = SecFinancialAdapter(AdvancingResolver(), lambda *a, **kw: raw(), clock=lambda: tick[0])
    result = adapter.retrieve("FIGI:chosen", concepts=("Revenues",))
    assert result.issuer is not None and len(result.concepts) == 1


def test_wrong_issuer_json_is_rejected_and_no_other_provider_is_tried():
    calls = []
    adapter = SecFinancialAdapter(Resolver(), lambda *a, **kw: calls.append(a) or raw(cik=2), clock=lambda: AT)
    result = adapter.retrieve("FIGI:chosen", concepts=("Revenues",))
    assert len(calls) == 1 and not result.concepts
    assert "Revenues:source_unavailable_or_invalid" in result.gaps


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_access_rate_or_server_failure_stops_remaining_requests(status):
    calls = []
    def fetch(*args, **kwargs):
        calls.append(args)
        raise SourceFetchError(status)
    result = SecFinancialAdapter(Resolver(), fetch, clock=lambda: AT).retrieve("FIGI:chosen")
    assert len(calls) == 1 and "source_access_or_rate_limited" in result.gaps and not result.concepts


def test_missing_concept_does_not_hide_an_available_different_concept():
    calls = []
    def fetch(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            raise SourceFetchError(404)
        return raw()
    result = SecFinancialAdapter(Resolver(), fetch, clock=lambda: AT).retrieve("FIGI:chosen", concepts=("Assets", "Revenues"))
    assert len(calls) == 2 and len(result.concepts) == 1
    assert "source_access_or_rate_limited" not in result.gaps


def test_cancellation_prevents_followup_calls_and_never_returns_partial_evidence():
    cancelled, calls = threading.Event(), []
    def fetch(*args, **kwargs):
        calls.append(args)
        cancelled.set()
        return raw()
    adapter = SecFinancialAdapter(Resolver(), fetch, clock=lambda: AT)
    with pytest.raises(InterruptedError):
        adapter.retrieve("FIGI:chosen", concepts=("Revenues", "NetIncomeLoss"), cancelled=cancelled)
    assert len(calls) == 1
    with pytest.raises(InterruptedError):
        adapter.retrieve("FIGI:chosen", cancelled=cancelled)
    assert len(calls) == 1


@pytest.mark.parametrize("concepts", [(), ("Unknown",), ("Assets", "Assets"), ("../private",)])
def test_unregistered_or_duplicate_requests_never_fetch(concepts):
    adapter = SecFinancialAdapter(Resolver(), lambda *a, **kw: pytest.fail("Unregistered request"))
    with pytest.raises(ValueError):
        adapter.retrieve("FIGI:chosen", concepts=concepts)


def test_live_financial_helper_needs_explicit_live_flag_and_sanitizes_failures():
    from scripts.qualify_sec_financials import check
    class Failure:
        def retrieve(self, query):
            raise OSError("PRIVATE contact@example.invalid")
    assert check(adapter=Failure())["status"] == "not_run"
    result = check(live=True, adapter=Failure())
    assert result["status"] == "blocked" and "PRIVATE" not in json.dumps(result) and "@" not in json.dumps(result)
