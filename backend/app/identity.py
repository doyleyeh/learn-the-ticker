"""Independent identity records. Provider proposals never certify themselves."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.app.contracts import AssetIdentity, IdentityVerification, now
from backend.app.evidence import MAX_BYTES, fetch_public_bytes, valid_sec_contact

INDEX_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
MAX_LISTINGS = 100_000


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def identity_hash(asset: AssetIdentity) -> str:
    # Exact security attributes, including contracts/share classes, not symbol alone.
    return hashlib.sha256(json.dumps(asset.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class ResolvedIdentity:
    asset: AssetIdentity
    verification: IdentityVerification

    def valid(self, at: datetime) -> bool:
        return (self.verification.identity_hash == identity_hash(self.asset)
                and timedelta(0) <= at - self.verification.retrieved_at < timedelta(days=1))


def select_exact(query: str, assets: list[ResolvedIdentity]) -> list[ResolvedIdentity]:
    key = normalized(query)
    exact = [row for row in assets if normalized(row.asset.id) == key]
    return exact or [row for row in assets if key in {normalized(row.asset.symbol), normalized(row.asset.name)}]


def parse_sec_listings(raw: bytes, retrieved_at: datetime) -> list[ResolvedIdentity]:
    """The SEC mapping establishes issuer/listing, not instrument type or currency."""
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
    if (not isinstance(data, dict) or set(data) != {"fields", "data"}
            or data["fields"] != ["cik", "name", "ticker", "exchange"]
            or not isinstance(data["data"], list) or not 0 < len(data["data"]) <= MAX_LISTINGS):
        raise ValueError("Unrecognized SEC identity response")
    digest = hashlib.sha256(raw).hexdigest()
    rows, ids = [], set()
    for record in data["data"]:
        if not isinstance(record, list) or len(record) != 4:
            raise ValueError("Invalid SEC listing")
        cik, name, symbol, exchange = record
        if (type(cik) is not int or not 0 < cik < 10**10
                or not isinstance(name, str) or not name.strip() or len(name) > 300
                or any(unicodedata.category(char).startswith("C") for char in name)
                or not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,39}", symbol)
                or (exchange is not None and (not isinstance(exchange, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .-]{0,39}", exchange)))):
            raise ValueError("Invalid SEC listing attributes")
        # Missing listing metadata stays unresolved rather than merging OTC/foreign securities.
        if exchange is None:
            continue
        asset = AssetIdentity(id=f"SEC:{cik:010}:{exchange.upper()}:{symbol.upper()}", symbol=symbol.upper(),
                              name=name.strip(), asset_type="unknown", exchange=exchange,
                              identifiers={"cik": f"{cik:010}"})
        if asset.id in ids:
            raise ValueError("Conflicting SEC identity records")
        ids.add(asset.id)
        rows.append(ResolvedIdentity(asset, IdentityVerification(authority="sec-listings-v1", source_url=INDEX_URL,
                    retrieved_at=retrieved_at, content_hash=digest, identity_hash=identity_hash(asset))))
    return rows


class SecIdentityResolver:
    """One bounded public request, no subscription/API key or arbitrary provider URL."""
    def __init__(self, fetcher=fetch_public_bytes, *, user_agent: str | None = None, clock=now):
        self.fetcher, self.clock = fetcher, clock
        self.user_agent = user_agent if user_agent is not None else os.environ.get("LTT_SEC_USER_AGENT", "")
        self._lock = threading.Lock()
        self._rows: list[ResolvedIdentity] = []
        self._retrieved_at = None
        self._attempted = 0.0

    def resolve(self, query: str) -> list[ResolvedIdentity]:
        # SEC asks automated clients to identify a contact. Never invent one or send credentials.
        if not valid_sec_contact(self.user_agent):
            return []
        with self._lock:
            at = self.clock()
            if self._retrieved_at is None or not timedelta(0) <= at - self._retrieved_at < timedelta(hours=1):
                # Bound repeated failures as well as successful requests; no retry loop.
                if time.monotonic() - self._attempted < 60:
                    return []
                self._attempted = time.monotonic()
                raw = self.fetcher(INDEX_URL, accept="application/json", user_agent=self.user_agent)
                rows = parse_sec_listings(raw, at)
                self._rows, self._retrieved_at = rows, at
            return select_exact(query, self._rows)
