import asyncio
import json
from datetime import timedelta

import pytest

from backend.app.api import create_app
from backend.app.contracts import ResearchRequest, SourcePolicy, now
from backend.app.db import Database
from backend.app.evidence import fetch_public_bytes
from backend.app.figi_identity import (
    MAPPING_URL, SEARCH_URL, FigiIdentityResolver, IdentityChoiceRequired, RegisteredIdentityResolver,
    fetch_figi, instrument_type, parse_figi_response, valid_figi,
)
from backend.app.source_registry import source_rule
from tests.desktop.test_application import FakeRuntime, TOKEN, payload


def synthetic_figi(index=0):
    base = f"BBG{index:08}"
    return next(base + str(digit) for digit in range(10) if valid_figi(base + str(digit)))


def record(index=0, **kwargs):
    return {"figi": synthetic_figi(index), "ticker": "SYN", "name": "SYNTHETIC COMPANY", "exchCode": "TEST",
            "securityType": "Common Stock", "securityType2": "Common Stock", "marketSector": "Equity",
            "securityDescription": "SYN", "compositeFIGI": None, "shareClassFIGI": None, **kwargs}


def document(rows=None, *, search=False, **kwargs):
    content = {"data": [record()] if rows is None else rows, **kwargs}
    return json.dumps(content if search else [content]).encode()


def parse(raw, query="SYN", search=False):
    return parse_figi_response(raw, query=query, search=search, retrieved_at=now())


def test_figi_validation_uses_the_documented_checksum():
    assert valid_figi("BBG000BLNNH6") and valid_figi("BBG000BLNQ16")
    for value in ("BBG000BLNNH7", "BBG000ALNNH6", "bad", "", "BBG000BLNNH66"):
        assert not valid_figi(value)


def test_independent_records_keep_listing_contract_and_share_class_metadata():
    rows = parse(document([record(1, compositeFIGI=synthetic_figi(3), shareClassFIGI=synthetic_figi(4)), record(2)]))
    assert len(rows) == 2 and all(row.valid(now()) for row in rows)
    assert rows[0].asset.currency is None and rows[0].asset.exchange == "TEST"
    assert rows[0].asset.identifiers["share_class_figi"] == synthetic_figi(4)
    assert rows[0].asset.id != rows[1].asset.id
    assert all(str(row.verification.source_url) == MAPPING_URL for row in rows)
    assert not parse(document(search=True), query="SYNTH", search=True)
    assert len(parse(document(search=True), query="synthetic  company", search=True)) == 1


@pytest.mark.parametrize("kind,sector,detail,expected", [
    ("Common Stock", "Equity", "Common Stock", "stock"),
    ("Preferred Stock", "Pfd", "Preferred", "stock"),
    ("Mutual Fund", "Equity", "Open-End Fund", "fund"),
    ("Mutual Fund", "Equity", "ETP", "unknown"),
    ("Note", "Govt", "US GOVERNMENT", "bond"),
    ("CRYPTO", "Curncy", "Crypto", "crypto"),
    ("Option", "Equity", "Equity Option", "option"),
    ("Future", "Comdty", "Physical commodity future.", "future"),
    ("Future", "Comdty", "Physical commodity generic.", "unknown"),
    ("Index", "Index", "Equity Index", "index"),
    ("Warrant", "Equity", "Equity WRT", "other"),
    ("NewKind", "Equity", "Not reviewed", "unknown"),
    ("Common Stock", "Comdty", "Common Stock", "unknown"),
    (None, None, None, "unknown"),
])
def test_category_is_conservative_and_never_inferred_from_name(kind, sector, detail, expected):
    item = record(securityType2=kind, marketSector=sector, securityType=detail)
    assert instrument_type(item) == expected
    assert parse(document([item]))[0].asset.asset_type == expected


@pytest.mark.parametrize("changes", [
    {"figi": "BBG000BLNNH7"}, {"name": None}, {"ticker": ""}, {"exchCode": 1},
    {"name": "Synthetic\x00"}, {"name": "x" * 301}, {"shareClassFIGI": "invalid"},
    {"unreviewed": "value"}, {"securityType2": []}, {"metadata": "Metadata N/A"},
    {"securityType2": "Option", "securityDescription": None},
])
def test_malformed_or_missing_metadata_never_certifies(changes):
    with pytest.raises(ValueError):
        parse(document([record(**changes)]))


@pytest.mark.parametrize("raw", [
    b"{}", b"[]", b"[{},{}]", b'[ {"data":[],"data":[]} ]', b"null",
    document([record(), record()]), document(error="PRIVATE provider diagnostic"),
    document(warning="No identifier found."), document(**{"extra": True}),
])
def test_invalid_duplicate_error_and_warning_fail_closed(raw):
    with pytest.raises(ValueError):
        parse(raw)


def test_pagination_and_large_ambiguity_cannot_become_a_unique_result():
    with pytest.raises(IdentityChoiceRequired) as exc:
        parse(document(search=True, next="PRIVATE_CURSOR"), search=True)
    assert len(exc.value.candidates) == 1 and "PRIVATE" not in str(exc.value)
    with pytest.raises(IdentityChoiceRequired) as exc:
        parse(document([record(i) for i in range(25)]))
    assert len(exc.value.candidates) == 20
    with pytest.raises(ValueError):
        parse(document(), query="DIFFERENT")


def test_cache_scope_expiry_clock_and_bounded_request_shape():
    at, calls = now(), []
    def fetch(url, body):
        calls.append((url, json.loads(body)))
        return document(search=url == SEARCH_URL)
    resolver = FigiIdentityResolver(fetcher=fetch, clock=lambda: at)
    assert resolver.resolve("SYN") and resolver.resolve("syn") and len(calls) == 1
    assert resolver.resolve("Synthetic Company") and calls[-1] == (SEARCH_URL, {"query": "Synthetic Company"})
    figi = synthetic_figi()
    assert resolver.resolve("figi:" + figi.lower()) and calls[-1] == (MAPPING_URL, [{"idType": "ID_BB_GLOBAL", "idValue": figi}])
    at += timedelta(hours=2)
    assert resolver.resolve("SYN") and len(calls) == 4
    at -= timedelta(days=1)
    assert resolver.resolve("SYN") and len(calls) == 5
    with pytest.raises(IdentityChoiceRequired):
        resolver.resolve("FIGI:invalid")
    assert len(calls) == 5


def test_transport_failure_has_no_retry_or_stale_fallback():
    calls, at = [], now()
    def fetch(*args):
        calls.append(True)
        if len(calls) > 1:
            raise OSError("PRIVATE contact@example.invalid")
        return document()
    resolver = FigiIdentityResolver(fetcher=fetch, clock=lambda: at)
    assert resolver.resolve("SYN")
    at += timedelta(hours=2)
    with pytest.raises(IdentityChoiceRequired) as exc:
        resolver.resolve("SYN")
    assert len(calls) == 2 and "PRIVATE" not in str(exc.value) and not exc.value.candidates


def test_shared_anonymous_rate_limits_do_not_wait_or_retry(monkeypatch):
    from backend.app import figi_identity
    # The imported helper still uses a synthetic transport under the suite-wide guard.
    tick, calls = [100.0], []
    monkeypatch.setattr(figi_identity, "_LAST_REQUEST", {})
    monkeypatch.setattr(figi_identity.time, "monotonic", lambda: tick[0])
    monkeypatch.setattr(figi_identity, "fetch_public_bytes", lambda *a, **kw: calls.append((a, kw)) or b"{}")
    fetch_figi(MAPPING_URL, b"[]")
    with pytest.raises(IdentityChoiceRequired):
        fetch_figi(MAPPING_URL, b"[]")
    fetch_figi(SEARCH_URL, b"{}")
    tick[0] += 3
    fetch_figi(MAPPING_URL, b"[]")
    with pytest.raises(IdentityChoiceRequired):
        fetch_figi(SEARCH_URL, b"{}")
    assert len(calls) == 3
    assert all("user_agent" not in kwargs for _, kwargs in calls)


@pytest.mark.parametrize("url,body", [
    ("https://example.com/", b"{}"), (MAPPING_URL + "?token=private", b"{}"),
    ("https://api.openfigi.com/v3/filter", b"{}"), (MAPPING_URL, b"x" * 4097),
    (MAPPING_URL, "{}"), (MAPPING_URL, b""),
])
def test_post_cannot_expand_to_arbitrary_hosts_paths_or_large_bodies(url, body, monkeypatch):
    monkeypatch.setattr("backend.app.evidence.public_address", lambda *a: pytest.fail("Must fail before DNS"))
    with pytest.raises(ValueError):
        fetch_public_bytes(url, json_body=body)


def test_figi_registration_is_metadata_only_and_separate_from_sec():
    assert source_rule(MAPPING_URL).policy == SourcePolicy.metadata
    assert not source_rule("https://www.openfigi.com/anything")
    class Resolver:
        def __init__(self):
            self.calls = []
        def resolve(self, query):
            self.calls.append(query)
            return []
    sec, figi = Resolver(), Resolver()
    resolver = RegisteredIdentityResolver(sec=sec, figi=figi)
    resolver.resolve("SEC:0000000001:TEST:SYN")
    resolver.resolve("SYN")
    resolver.resolve("FIGI:" + synthetic_figi())
    assert sec.calls == ["SEC:0000000001:TEST:SYN", "SYN"] and len(figi.calls) == 2


def test_registries_preserve_choices_without_merging_similar_names_or_identifiers():
    from tests.desktop.test_application import StaticIdentityResolver
    sec = StaticIdentityResolver()
    figi = FigiIdentityResolver(fetcher=lambda *a: document([record(ticker="ALPHA")]))
    resolver = RegisteredIdentityResolver(sec=sec, figi=figi)
    rows = resolver.resolve("ALPHA")
    assert len(rows) == 2 and rows[0].asset.id != rows[1].asset.id
    assert "cik" in rows[0].asset.identifiers and "cik" not in rows[1].asset.identifiers
    unavailable = FigiIdentityResolver(fetcher=lambda *a: b"invalid")
    with pytest.raises(IdentityChoiceRequired) as exc:
        RegisteredIdentityResolver(sec=sec, figi=unavailable).resolve("ALPHA")
    assert len(exc.value.candidates) == 1 and exc.value.candidates[0].asset.id == rows[0].asset.id


def test_incomplete_identity_stops_before_inference_and_publication(tmp_path):
    async def run():
        db = Database("sqlite://", testing=True)
        db.put("settings", "settings", {"cloud_enabled": True})
        runtime = FakeRuntime(payload())
        resolver = FigiIdentityResolver(fetcher=lambda *a: document(search=True, next="PRIVATE_CURSOR"))
        service = create_app(db, TOKEN, tmp_path, adapters={"codex": runtime}, identity_resolver=resolver).state.service
        job = await service.submit(ResearchRequest(query="Synthetic Company"))
        await service.tasks[job["id"]]
        finished = db.job(job["id"])
        assert finished["status"] == "needs_identity" and runtime.calls == 0
        assert len(finished["result"]["candidates"]) == 1 and "PRIVATE" not in str(finished)
        assert not db.list("asset") and not db.list("bundle")
    asyncio.run(run())


def test_live_helper_is_explicit_and_reports_only_public_proof():
    from scripts.qualify_figi_identity import check
    class Failure:
        def resolve(self, query):
            raise OSError("PRIVATE contact@example.invalid")
    assert check(resolver=Failure())["status"] == "not_run"
    assert "PRIVATE" not in str(check(live=True, resolver=Failure()))
    resolver = FigiIdentityResolver(fetcher=lambda *a: document())
    result = check(live=True, query="SYN", resolver=resolver)
    assert result["status"] == "passed" and result["asset_type"] == "stock"
    assert "SYNTHETIC COMPANY" not in str(result)
