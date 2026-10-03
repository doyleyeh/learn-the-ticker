"""Conservative evidence admission. Model self-attestation is never verification."""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import urlparse

from backend.app.contracts import AssetIdentity, Claim, EvidenceBundle, Source, SourcePolicy, now
from backend.safety import find_forbidden_output_phrases

# Reviewed policy entries, not an asset coverage allowlist. Extend with tests and a rights rationale.
SOURCE_RULES = {"www.sec.gov": SourcePolicy.full_text, "www.investor.gov": SourcePolicy.full_text}
MAX_BYTES = 2_000_000


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.ignored = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.ignored:
            self.ignored -= 1

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def public_address(host: str) -> str:
    addresses = {row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Source resolves to a non-public address")
    return sorted(addresses)[0]


def fetch_public_text(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Only public HTTPS sources on port 443 are allowed")
    address = public_address(parsed.hostname)
    # Connect to the validated address, retain the hostname for TLS and Host, and never follow redirects.
    connection = http.client.HTTPSConnection(parsed.hostname, timeout=15)
    connection.sock = ssl.create_default_context().wrap_socket(socket.create_connection((address, 443), timeout=15), server_hostname=parsed.hostname)
    try:
        connection.request("GET", parsed.path + ("?" + parsed.query if parsed.query else ""), headers={"User-Agent": "LearnTheTicker/0.2 (personal educational research)", "Accept": "text/html,text/plain"})
        response = connection.getresponse()
        if response.status != 200 or response.getheader("Content-Type", "").split(";")[0] not in ("text/html", "text/plain"):
            raise ValueError("Source cannot be verified as a readable document")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Source exceeds retrieval limit")
        parser = VisibleText()
        parser.feed(raw.decode("utf-8", errors="replace"))
        return " ".join(parser.parts)
    finally:
        connection.close()


def verify_candidate(candidate: Source, asset: AssetIdentity, fetcher=fetch_public_text) -> Source:
    # Discard every model-controlled verification, rights and provenance field.
    source = candidate.model_copy(update={"verified": False, "official": False, "policy": SourcePolicy.link, "excerpt": "", "content_hash": "", "provenance": "agent_candidate", "retrieved_at": now(), "published_at": None, "as_of": None})
    if candidate.policy == SourcePolicy.rejected:
        return source.model_copy(update={"policy": SourcePolicy.rejected})
    if candidate.asset_id != asset.id:
        return source
    policy = SOURCE_RULES.get(candidate.url.host)
    if policy is None:
        return source
    text = fetcher(str(candidate.url))
    # Identity requires the full issuer/asset name. A short ticker alone is insufficient.
    if len(asset.name) < 4 or normalize(asset.name) not in normalize(text):
        return source
    return source.model_copy(update={"verified": True, "official": True, "policy": policy, "provenance": "verified_retrieval", "excerpt": text[:20000], "content_hash": hashlib.sha256(text.encode()).hexdigest()})


def admit_bundle(asset: AssetIdentity, sources: list[Source], claims: list[Claim], *, language="en") -> EvidenceBundle:
    by_id = {s.id: s for s in sources if s.asset_id == asset.id and s.policy != SourcePolicy.rejected}
    if len({s.id for s in sources}) != len(sources):
        raise ValueError("Duplicate source IDs")
    admitted, notes = [], []
    rejected_ids = {s.id for s in sources if s.policy == SourcePolicy.rejected}
    for claim in claims:
        if claim.asset_id != asset.id or rejected_ids.intersection(claim.source_ids) or find_forbidden_output_phrases(claim.text):
            continue
        supports = [by_id[sid] for sid in claim.source_ids if sid in by_id]
        # This initial validator only admits literal source-supported prose. Paraphrase entailment
        # and structured numeric adapters require independent validators before promotion.
        supported = bool(supports) and len(supports) == len(claim.source_ids) and all(s.verified for s in supports)
        supported = supported and any(normalize(claim.text) in normalize(s.excerpt) for s in supports)
        # Date extraction is an adapter responsibility. Model-supplied publication dates
        # cannot establish weekly relevance, even when the quoted text can be retrieved.
        if claim.section in ("weekly_news", "earlier_context"):
            supported = False
        if claim.kind == "fact" and claim.value is None and supported:
            admitted.append(claim.model_copy(update={"as_of": None}))
        else:
            notes.append(claim.model_copy(update={"kind": "unverified_note", "value": None, "unit": None, "input_claim_ids": [], "source_ids": [s.id for s in supports]}))
    return EvidenceBundle(asset=asset, sources=list(by_id.values()), claims=admitted, notes=notes, language=language, state="partial")


def factual_context(bundle: EvidenceBundle) -> dict:
    """Unverified notes and provider raw output never become future factual evidence."""
    ids = {sid for claim in bundle.claims for sid in claim.source_ids}
    return {"asset": bundle.asset.model_dump(mode="json"), "claims": [c.model_dump(mode="json") for c in bundle.claims], "sources": [s.model_dump(mode="json") for s in bundle.sources if s.id in ids]}
