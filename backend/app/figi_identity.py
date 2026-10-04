"""Unauthenticated, read-only OpenFIGI metadata lookups; no AI-attested identities."""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import unicodedata
from collections import OrderedDict
from datetime import timedelta

from backend.app.contracts import AssetIdentity, IdentityVerification, now
from backend.app.evidence import MAX_BYTES, fetch_public_bytes
from backend.app.identity import ResolvedIdentity, SecIdentityResolver, identity_hash, normalized

MAPPING_URL = "https://api.openfigi.com/v3/mapping"
SEARCH_URL = "https://api.openfigi.com/v3/search"
_RATE_LOCK = threading.Lock()
_LAST_REQUEST: dict[str, float] = {}


class IdentityChoiceRequired(ValueError):
    def __init__(self, candidates=()):
        super().__init__("Identity lookup needs a more specific selection")
        self.candidates = list(candidates)[:20]


def valid_figi(value: str) -> bool:
    if not re.fullmatch(r"[B-DF-HJ-NP-TV-Z]{2}G[0-9B-DF-HJ-NP-TV-Z]{8}[0-9]", value):
        return False
    total = 0
    for i, char in enumerate(value[:11]):
        number = int(char) if char.isdigit() else ord(char) - ord("A") + 10
        total += sum(int(digit) for digit in str(number * (2 if i % 2 else 1)))
    return int(value[-1]) == (-total) % 10


def text_field(value, limit=300, *, required=False):
    if value is None and not required:
        return None
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or any(unicodedata.category(char).startswith("C") for char in value)):
        raise ValueError("Invalid identity metadata")
    return value.strip()


def instrument_type(record):
    # Do not equate ETP with ETF or generic futures with a dated contract.
    kind, sector, detail = record.get("securityType2"), record.get("marketSector"), record.get("securityType")
    if detail == "ETP" or (detail and "generic" in detail.casefold()):
        return "unknown"
    if kind in ("Common Stock", "Preferred Stock") and sector in ("Equity", "Pfd"):
        return "stock"
    if kind == "Mutual Fund" and detail in ("Mutual Fund", "Open-End Fund", "Closed-End Fund"):
        return "fund"
    if kind == "Option":
        return "option"
    if kind in ("Future", "Daily Future"):
        return "future"
    if kind == "CRYPTO" and detail == "Crypto":
        return "crypto"
    if kind == "Index" and sector == "Index":
        return "index"
    if kind in ("Bond", "Bond/Note", "Bill", "Note") and sector in ("Corp", "Govt", "Muni"):
        return "bond"
    if kind in ("OTHER", "Right", "Warrant"):
        return "other"
    return "unknown"


def parse_figi_response(raw: bytes, *, query: str, search: bool, retrieved_at):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError("Identity document exceeds retrieval limit")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate identity field")
            result[key] = value
        return result
    data = json.loads(raw, object_pairs_hook=unique)
    if not search:
        if not isinstance(data, list) or len(data) != 1:
            raise ValueError("Uncorrelated identity response")
        data = data[0]
    if not isinstance(data, dict) or set(data) - {"data", "next", "warning", "error"}:
        raise ValueError("Unrecognized identity response")
    if "warning" in data or "error" in data:
        # Do not echo provider text, treat warning/error as a complete negative result,
        # or silently try another identifier after a rate/error response.
        raise IdentityChoiceRequired()
    records = data.get("data")
    if not isinstance(records, list) or len(records) > 15_000:
        raise ValueError("Invalid identity result size")
    digest, rows, ids = hashlib.sha256(raw).hexdigest(), [], set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid identity record")
        if "metadata" in record:
            raise IdentityChoiceRequired()
        permitted = {"figi", "ticker", "name", "exchCode", "securityType", "securityType2", "marketSector",
                     "securityDescription", "compositeFIGI", "shareClassFIGI"}
        if set(record) - permitted:
            raise ValueError("Unreviewed identity metadata")
        figi = text_field(record.get("figi"), 12, required=True)
        if not valid_figi(figi) or figi in ids:
            raise ValueError("Invalid or conflicting FIGI")
        ids.add(figi)
        name = text_field(record.get("name"), required=True)
        ticker = text_field(record.get("ticker"), 100, required=True)
        exchange = text_field(record.get("exchCode"), 40)
        identifiers = {"figi": figi}
        for field, key in (("compositeFIGI", "composite_figi"), ("shareClassFIGI", "share_class_figi")):
            value = text_field(record.get(field), 12)
            if value is not None:
                if not valid_figi(value):
                    raise ValueError("Invalid related FIGI")
                identifiers[key] = value
        for field in ("securityType", "securityType2", "marketSector", "securityDescription"):
            value = text_field(record.get(field))
            if value is not None:
                identifiers["openfigi_" + field] = value
        kind = instrument_type(record)
        if kind in ("option", "future") and not record.get("securityDescription"):
            raise IdentityChoiceRequired()
        asset = AssetIdentity(id="FIGI:" + figi, symbol=ticker, name=name, asset_type=kind,
                              exchange=exchange, identifiers=identifiers)
        proof = IdentityVerification(authority="openfigi-v3", source_url=SEARCH_URL if search else MAPPING_URL,
                                     retrieved_at=retrieved_at, content_hash=digest, identity_hash=identity_hash(asset))
        rows.append(ResolvedIdentity(asset, proof))
    key = normalized(query)
    exact = [row for row in rows if key in {normalized(row.asset.id), normalized(row.asset.identifiers["figi"]),
                                           normalized(row.asset.symbol), normalized(row.asset.name)}]
    if "next" in data or len(exact) > 20:
        # A partial page can never establish uniqueness. Offer only verified choices.
        raise IdentityChoiceRequired(exact)
    if not search and not exact and rows:
        raise ValueError("Identity response does not match the requested identifier")
    return exact


def fetch_figi(url, body):
    # Shared process-wide bounds are below unauthenticated quotas (25 and 5/min).
    with _RATE_LOCK:
        delay = (3 if url == MAPPING_URL else 15) - (time.monotonic() - _LAST_REQUEST.get(url, float("-inf")))
        if delay > 0:
            raise IdentityChoiceRequired()
        _LAST_REQUEST[url] = time.monotonic()
    return fetch_public_bytes(url, accept="application/json", json_body=body)


class FigiIdentityResolver:
    def __init__(self, fetcher=None, *, clock=now):
        self.fetcher, self.clock = fetcher or fetch_figi, clock
        self._cache = OrderedDict()
        self._lock = threading.Lock()

    def resolve(self, query):
        query = text_field(query, 300, required=True)
        bare = query[5:].upper() if query.upper().startswith("FIGI:") else query.upper()
        if query.upper().startswith("FIGI:") or valid_figi(bare):
            if not valid_figi(bare):
                raise IdentityChoiceRequired()
            query, search = "FIGI:" + bare, False
            payload = [{"idType": "ID_BB_GLOBAL", "idValue": bare}]
        elif re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./-]{0,63}", query):
            search, payload = False, [{"idType": "TICKER", "idValue": query.upper()}]
        else:
            search, payload = True, {"query": query}
        url, key = (SEARCH_URL if search else MAPPING_URL), normalized(query)
        with self._lock:
            at = self.clock()
            saved = self._cache.get(key)
            if saved and timedelta(0) <= at - saved[0] < timedelta(hours=1):
                return saved[1]
            try:
                raw = self.fetcher(url, json.dumps(payload, separators=(",", ":")).encode())
                rows = parse_figi_response(raw, query=query, search=search, retrieved_at=at)
            except IdentityChoiceRequired:
                raise
            except (ValueError, OSError) as exc:
                raise IdentityChoiceRequired() from exc
            self._cache[key] = (at, rows)
            self._cache.move_to_end(key)
            while len(self._cache) > 256:
                self._cache.popitem(last=False)
            return rows


class RegisteredIdentityResolver:
    """Separate identity namespaces; symbol/name resemblance never merges issuers."""
    def __init__(self, *, sec=None, figi=None):
        self.sec, self.figi = sec or SecIdentityResolver(), figi or FigiIdentityResolver()

    def resolve(self, query):
        if query.upper().startswith("SEC:"):
            return self.sec.resolve(query)
        if query.upper().startswith("FIGI:") or valid_figi(query.upper()):
            return self.figi.resolve(query)
        try:
            sec_rows = self.sec.resolve(query)
        except (ValueError, OSError):
            # An unavailable source must not erase verified choices from the other
            # registry, but it also cannot establish unique cross-registry scope.
            raise IdentityChoiceRequired(self.figi.resolve(query)) from None
        try:
            rows = sec_rows + self.figi.resolve(query)
        except IdentityChoiceRequired as exc:
            raise IdentityChoiceRequired(sec_rows + exc.candidates) from None
        if len(rows) > 20:
            raise IdentityChoiceRequired(rows)
        return rows
