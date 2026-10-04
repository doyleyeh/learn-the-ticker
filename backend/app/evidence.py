"""Conservative evidence admission. Model self-attestation is never verification."""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import os
import re
import socket
import ssl
import threading
import time
from html.parser import HTMLParser
from urllib.parse import urlparse

from backend.app.contracts import AssetIdentity, Claim, EvidenceBundle, Source, SourcePolicy, now
from backend.app.source_registry import SOURCE_RULES, source_rule
from backend.safety import find_forbidden_output_phrases

MAX_BYTES = 2_000_000
_SEC_LOCK = threading.Lock()
_SEC_LAST_REQUEST = 0.0


class SourceFetchError(ValueError):
    def __init__(self, status: int):
        super().__init__("Public source request was unavailable")
        self.status = status


def valid_sec_contact(value: str) -> bool:
    return (10 <= len(value) <= 200 and value.isascii()
            and not any(ord(c) < 32 or ord(c) == 127 for c in value)
            and bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value)))


class VisibleText(HTMLParser):
    # Inline formatting may split a word or put a closing quote in another node.
    # Insert whitespace at structural boundaries, never between every data node.
    blocks = {"address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "fieldset",
              "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
              "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul"}

    def __init__(self):
        super().__init__()
        self.parts, self.ignored = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.ignored += 1
        elif not self.ignored and tag in self.blocks:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.ignored:
            self.ignored -= 1
        elif not self.ignored and tag in self.blocks:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)

    def text(self):
        return " ".join("".join(self.parts).split())


def normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def public_address(host: str) -> str:
    addresses = {row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Source resolves to a non-public address")
    return sorted(addresses)[0]


def fetch_public_bytes(url: str, *, accept="text/html,text/plain", user_agent="LearnTheTicker/0.2 (personal educational research)", json_body: bytes | None = None) -> bytes:
    global _SEC_LAST_REQUEST
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Only public HTTPS sources on port 443 are allowed")
    if json_body is not None and (url not in ("https://api.openfigi.com/v3/mapping", "https://api.openfigi.com/v3/search")
                                  or not isinstance(json_body, bytes) or not 0 < len(json_body) <= 4096):
        raise ValueError("Only bounded registered identity lookups may use POST")
    if parsed.hostname in ("www.sec.gov", "data.sec.gov"):
        if user_agent == "LearnTheTicker/0.2 (personal educational research)":
            user_agent = os.environ.get("LTT_SEC_USER_AGENT", "")
        if not valid_sec_contact(user_agent):
            raise ValueError("Configure an SEC application contact before live retrieval")
        with _SEC_LOCK:
            # A shared maximum of five starts/sec for every SEC retrieval in this process.
            delay = .2 - (time.monotonic() - _SEC_LAST_REQUEST)
            if delay > 0:
                time.sleep(delay)
            _SEC_LAST_REQUEST = time.monotonic()
    address = public_address(parsed.hostname)
    # Connect to the validated address, retain the hostname for TLS and Host, and never follow redirects.
    connection = http.client.HTTPSConnection(parsed.hostname, timeout=15)
    try:
        connection.sock = ssl.create_default_context().wrap_socket(socket.create_connection((address, 443), timeout=15), server_hostname=parsed.hostname)
        headers = {"User-Agent": user_agent, "Accept": accept}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        connection.request("POST" if json_body is not None else "GET", parsed.path + ("?" + parsed.query if parsed.query else ""), body=json_body, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise SourceFetchError(response.status)
        if response.getheader("Content-Type", "").split(";")[0].strip() not in accept.split(","):
            raise ValueError("Source cannot be verified as a readable document")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Source exceeds retrieval limit")
        return raw
    finally:
        connection.close()


def fetch_public_text(url: str) -> str:
    parser = VisibleText()
    parser.feed(fetch_public_bytes(url).decode("utf-8", errors="replace"))
    return parser.text()


def candidate_metadata(candidate: Source, *, rules=SOURCE_RULES) -> Source:
    # Discard every model-controlled verification, rights and provenance field.
    source = candidate.model_copy(update={"verified": False, "official": False, "policy": SourcePolicy.link, "excerpt": "", "content_hash": "", "provenance": "agent_candidate", "retrieved_at": now(), "published_at": None, "as_of": None, "filing_publication": None})
    if candidate.policy == SourcePolicy.rejected:
        return source.model_copy(update={"policy": SourcePolicy.rejected})
    rule = source_rule(str(candidate.url), rules)
    if rule:
        source = source.model_copy(update={"policy": rule.policy, "publisher": rule.publisher, "official": rule.official})
    return source


def verify_candidate(candidate: Source, asset: AssetIdentity, fetcher=fetch_public_text, *, rules=SOURCE_RULES) -> Source:
    source = candidate_metadata(candidate, rules=rules)
    if candidate.asset_id != asset.id:
        return source
    rule = source_rule(str(candidate.url), rules)
    if rule is None or source.policy != SourcePolicy.full_text:
        return source
    # A mention of the same name in another issuer's filing does not establish scope.
    if rule.id == "sec-filings-v1":
        cik = asset.identifiers.get("cik", "")
        match = re.fullmatch(rule.path_pattern, candidate.url.path)
        if not re.fullmatch(r"[0-9]{10}", cik) or not match or int(candidate.url.path.split("/")[4]) != int(cik):
            return source
    text = fetcher(str(candidate.url))
    # Identity requires the full issuer/asset name. A short ticker alone is insufficient.
    if len(asset.name) < 4 or normalize(asset.name) not in normalize(text):
        return source
    return source.model_copy(update={"verified": True, "provenance": "verified_retrieval", "excerpt": text[:20000], "content_hash": hashlib.sha256(text.encode()).hexdigest()})


def admit_bundle(asset: AssetIdentity, sources: list[Source], claims: list[Claim], *, language="en", level=None, identity_verification=None, created_at=None, financials=None) -> EvidenceBundle:
    by_id = {s.id: s for s in sources if s.asset_id == asset.id and s.policy != SourcePolicy.rejected}
    if len({s.id for s in sources}) != len(sources):
        raise ValueError("Duplicate source IDs")
    admitted, notes = [], []
    rejected_ids = {s.id for s in sources if s.policy == SourcePolicy.rejected}
    for claim in claims:
        if claim.asset_id != asset.id or rejected_ids.intersection(claim.source_ids) or find_forbidden_output_phrases(claim.text):
            continue
        supports = [by_id[sid] for sid in claim.source_ids if sid in by_id]
        # Link/metadata permissions do not authorize copying provider-supplied derivatives
        # into notes, archives or later exports. Missing citations also cannot bypass this.
        if claim.source_ids and (len(supports) != len(claim.source_ids) or any(s.policy != SourcePolicy.full_text for s in supports)):
            continue
        # This initial validator only admits literal source-supported prose. Paraphrase entailment
        # and structured numeric adapters require independent validators before promotion.
        supported = bool(supports) and len(supports) == len(claim.source_ids) and all(s.verified for s in supports)
        if asset.asset_type == "unknown" and claim.section != "overview":
            supported = False
        supported = supported and any(normalize(claim.text) in normalize(s.excerpt) for s in supports)
        # Date extraction is an adapter responsibility. Model-supplied publication dates
        # cannot establish weekly relevance, even when the quoted text can be retrieved.
        if claim.section in ("weekly_news", "earlier_context"):
            supported = False
        if claim.kind == "fact" and claim.value is None and supported:
            admitted.append(claim.model_copy(update={"as_of": None}))
        else:
            notes.append(claim.model_copy(update={"kind": "unverified_note", "value": None, "unit": None, "input_claim_ids": [], "source_ids": [s.id for s in supports]}))
    return EvidenceBundle(asset=asset, sources=list(by_id.values()), claims=admitted, notes=notes, language=language, level=level, identity_verification=identity_verification, created_at=created_at or now(), financials=financials, state="partial")


def validate_claim_sources(bundle: EvidenceBundle):
    """A published fact and its source records form one indivisible snapshot."""
    sources = {source.id: source for source in bundle.sources}
    if len(sources) != len(bundle.sources) or any(source.asset_id != bundle.asset.id or source.policy == SourcePolicy.rejected for source in bundle.sources):
        raise ValueError("Invalid evidence sources")
    claims = [*bundle.claims, *bundle.notes]
    if len({claim.id for claim in claims}) != len(claims):
        raise ValueError("Duplicate claims")
    for claim in claims:
        if claim.asset_id != bundle.asset.id or any(sid not in sources for sid in claim.source_ids):
            raise ValueError("Missing or wrong-asset citation")
    for claim in bundle.claims:
        if claim.kind not in ("fact", "calculation") or not claim.source_ids or any(not sources[sid].verified for sid in claim.source_ids):
            raise ValueError("Facts require verified citations")
    if any(note.kind != "unverified_note" or note.value is not None or note.input_claim_ids for note in bundle.notes):
        raise ValueError("Unverified notes cannot contain calculation inputs")


def factual_context(bundle: EvidenceBundle) -> dict:
    """Unverified notes and provider raw output never become future factual evidence."""
    from backend.app.financial_evidence import numeric_context
    validate_claim_sources(bundle)
    observations = numeric_context(bundle)
    # Preserve permitted admitted legacy snapshots (including summary rights). New
    # research admission and historical candidate reuse apply their own current rules.
    claims = bundle.claims
    ids = {sid for claim in claims for sid in claim.source_ids}
    ids.update(row["source_id"] for row in observations)
    context = {"bundle_id": bundle.id, "created_at": bundle.created_at.isoformat(), "asset": bundle.asset.model_dump(mode="json"),
               "claims": [c.model_dump(mode="json") for c in claims], "sources": [s.model_dump(mode="json") for s in bundle.sources if s.id in ids]}
    if bundle.financials:
        context["financials"] = {"scope": "issuer", "issuer": bundle.financials.issuer.model_dump(mode="json"),
                                 "observations": observations, "gaps": bundle.financials.gaps}
    return context
