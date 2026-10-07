from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from ipaddress import ip_address
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from backend.data import normalize_ticker
from backend.models import (
    EvidenceState,
    FreshnessState,
    SourceAllowlistStatus,
    SourceParserStatus,
    SourceQuality,
    SourceUsePolicy,
    WeeklyNewsEventType,
    WeeklyNewsPeriodBucket,
)
from backend.repositories.source_snapshots import (
    SourceSnapshotArtifactCategory,
    SourceSnapshotArtifactRow,
    SourceSnapshotDiagnosticCategory,
    SourceSnapshotDiagnosticRow,
    SourceSnapshotRepositoryRecords,
    SourceSnapshotScopeKind,
    validate_source_snapshot_records,
)
from backend.repositories.weekly_news import (
    WEEKLY_NEWS_OFFICIAL_SOURCE_PARSER_ADAPTER_BOUNDARY,
    WeeklyNewsEventCandidateRow,
    WeeklyNewsOfficialSourceParserDiagnostic,
    WeeklyNewsSourceRankTier,
)
from backend.source_policy import (
    SourcePolicyAction,
    resolve_source_policy,
    source_can_support_generated_output,
    source_handoff_fields_from_policy,
    validate_source_handoff,
)
from backend.weekly_news import compute_weekly_news_window


WEEKLY_NEWS_OFFICIAL_DOCUMENT_DISCOVERY_BOUNDARY = "weekly-news-official-document-discovery-boundary-v1"
WEEKLY_NEWS_OFFICIAL_DOCUMENT_FETCH_BOUNDARY = "weekly-news-official-document-fetch-boundary-v1"
WEEKLY_NEWS_OFFICIAL_DOCUMENT_PARSER_BOUNDARY = "weekly-news-official-document-parser-boundary-v1"
WEEKLY_NEWS_OFFICIAL_SOURCE_SNAPSHOT_BOUNDARY = "weekly-news-official-source-snapshot-boundary-v1"

DEFAULT_WEEKLY_NEWS_OFFICIAL_FETCH_TIMEOUT_SECONDS = 10.0
DEFAULT_WEEKLY_NEWS_OFFICIAL_FETCH_MAX_BYTES = 2_000_000
DEFAULT_WEEKLY_NEWS_OFFICIAL_FETCH_MAX_REDIRECTS = 3
DEFAULT_WEEKLY_NEWS_OFFICIAL_USER_AGENT = "LearnTheTicker/weekly-news-source-handoff contact=local-contract"

_ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/xhtml+xml",
    "text/html",
    "text/plain",
}
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "credential",
    "key",
    "password",
    "secret",
    "signature",
    "signed",
    "token",
}
_GOLDEN_REQUESTS: dict[str, tuple[dict[str, Any], ...]] = {
    "AAPL": (
        {
            "source_document_id": "aapl-sec-submissions-json",
            "url": "https://data.sec.gov/submissions/CIK0000320193.json",
            "source_rank_tier": WeeklyNewsSourceRankTier.official_filing.value,
            "source_type": "official_filing",
            "source_title": "Apple SEC submissions JSON",
            "source_publisher": "SEC",
            "event_type": WeeklyNewsEventType.earnings.value,
            "source_rank": 1,
            "source_quality": SourceQuality.official.value,
        },
        {
            "source_document_id": "aapl-investor-newsroom",
            "url": "https://investor.apple.com/news-and-events/news-room/default.aspx",
            "source_rank_tier": WeeklyNewsSourceRankTier.investor_relations_release.value,
            "source_type": "investor_relations_release",
            "source_title": "Apple investor relations newsroom",
            "source_publisher": "Apple Investor Relations",
            "event_type": WeeklyNewsEventType.product_announcement.value,
            "source_rank": 2,
            "source_quality": SourceQuality.issuer.value,
        },
    ),
    "VOO": (
        {
            "source_document_id": "voo-vanguard-profile",
            "url": "https://investor.vanguard.com/investment-products/etfs/profile/voo",
            "source_rank_tier": WeeklyNewsSourceRankTier.etf_issuer_announcement.value,
            "source_type": "etf_issuer_announcement",
            "source_title": "Vanguard VOO issuer profile",
            "source_publisher": "Vanguard",
            "event_type": WeeklyNewsEventType.sponsor_update.value,
            "source_rank": 3,
            "source_quality": SourceQuality.issuer.value,
        },
        {
            "source_document_id": "voo-vanguard-fact-sheet",
            "url": "https://investor.vanguard.com/investment-products/etfs/profile/voo#portfolio-composition",
            "source_rank_tier": WeeklyNewsSourceRankTier.fact_sheet_change.value,
            "source_type": "fact_sheet_change",
            "source_title": "Vanguard VOO fact sheet metadata",
            "source_publisher": "Vanguard",
            "event_type": WeeklyNewsEventType.methodology_change.value,
            "source_rank": 5,
            "source_quality": SourceQuality.issuer.value,
        },
    ),
    "QQQ": (
        {
            "source_document_id": "qqq-invesco-product",
            "url": "https://www.invesco.com/qqq-etf/en/home.html",
            "source_rank_tier": WeeklyNewsSourceRankTier.etf_issuer_announcement.value,
            "source_type": "etf_issuer_announcement",
            "source_title": "Invesco QQQ product page",
            "source_publisher": "Invesco",
            "event_type": WeeklyNewsEventType.sponsor_update.value,
            "source_rank": 3,
            "source_quality": SourceQuality.issuer.value,
        },
        {
            "source_document_id": "qqq-invesco-prospectus",
            "url": "https://www.invesco.com/qqq-etf/en/prospectus.html",
            "source_rank_tier": WeeklyNewsSourceRankTier.prospectus_update.value,
            "source_type": "prospectus_update",
            "source_title": "Invesco QQQ prospectus page",
            "source_publisher": "Invesco",
            "event_type": WeeklyNewsEventType.methodology_change.value,
            "source_rank": 4,
            "source_quality": SourceQuality.issuer.value,
        },
    ),
}


class WeeklyNewsOfficialSourceRetrievalError(ValueError):
    def __init__(self, reason_code: str, *, diagnostics: dict[str, Any] | None = None) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.diagnostics = _sanitize_diagnostics(diagnostics or {"reason_code": reason_code})


@dataclass(frozen=True)
class WeeklyNewsOfficialSourceRequest:
    ticker: str
    source_document_id: str
    url: str
    source_rank_tier: str
    source_type: str
    source_title: str
    source_publisher: str
    event_type: str
    source_rank: int
    source_quality: str
    is_official: bool = True

    def normalized_ticker(self) -> str:
        return normalize_ticker(self.ticker)


@dataclass(frozen=True)
class WeeklyNewsOfficialHttpResponse:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes


@dataclass(frozen=True)
class WeeklyNewsOfficialFetchedDocument:
    boundary: str
    request: WeeklyNewsOfficialSourceRequest
    status: str
    final_url: str
    content_type: str
    payload: bytes
    text: str
    checksum: str
    retrieved_at: str
    byte_size: int
    sanitized_diagnostics: dict[str, Any] = field(default_factory=dict)
    no_live_external_calls: bool = False
    stores_raw_article_text: bool = False
    stores_raw_provider_payload: bool = False
    stores_secret: bool = False


@dataclass(frozen=True)
class WeeklyNewsOfficialDocumentParseResult:
    boundary: str
    ticker: str
    candidates: tuple[WeeklyNewsEventCandidateRow, ...]
    diagnostics: tuple[WeeklyNewsOfficialSourceParserDiagnostic, ...]
    parser_diagnostic_count: int
    no_live_external_calls: bool
    sanitized_diagnostics: dict[str, Any]


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass(frozen=True)
class WeeklyNewsOfficialSourceDiscoverer:
    def discover(self, ticker: str, *, as_of: str) -> list[WeeklyNewsOfficialSourceRequest]:
        normalized = normalize_ticker(ticker)
        if normalized not in _GOLDEN_REQUESTS:
            return []
        compute_weekly_news_window(as_of)
        return [
            WeeklyNewsOfficialSourceRequest(
                ticker=normalized,
                source_document_id=str(row["source_document_id"]),
                url=str(row["url"]),
                source_rank_tier=str(row["source_rank_tier"]),
                source_type=str(row["source_type"]),
                source_title=str(row["source_title"]),
                source_publisher=str(row["source_publisher"]),
                event_type=str(row["event_type"]),
                source_rank=int(row["source_rank"]),
                source_quality=str(row["source_quality"]),
                is_official=True,
            )
            for row in _GOLDEN_REQUESTS[normalized]
        ]


@dataclass(frozen=True)
class WeeklyNewsOfficialDocumentFetcher:
    transport: Callable[[str, dict[str, str], float], WeeklyNewsOfficialHttpResponse] | None = None
    timeout_seconds: float = DEFAULT_WEEKLY_NEWS_OFFICIAL_FETCH_TIMEOUT_SECONDS
    max_bytes: int = DEFAULT_WEEKLY_NEWS_OFFICIAL_FETCH_MAX_BYTES
    max_redirects: int = DEFAULT_WEEKLY_NEWS_OFFICIAL_FETCH_MAX_REDIRECTS
    user_agent: str = DEFAULT_WEEKLY_NEWS_OFFICIAL_USER_AGENT

    def fetch(self, request: WeeklyNewsOfficialSourceRequest, *, retrieved_at: str) -> WeeklyNewsOfficialFetchedDocument:
        current_url = request.url
        visited_hosts: list[str] = []
        redirect_count = 0
        while True:
            _validate_url_allowed(current_url)
            visited_hosts.append(_safe_host(current_url))
            headers = {"User-Agent": self.user_agent, "Accept": "application/json,text/html,text/plain;q=0.9,*/*;q=0.1"}
            response = self._fetch_once(current_url, headers)
            if response.status in {301, 302, 303, 307, 308}:
                redirect_count += 1
                if redirect_count > self.max_redirects:
                    raise WeeklyNewsOfficialSourceRetrievalError(
                        "weekly_news_source_redirect_limit_exceeded",
                        diagnostics={"source_document_id": request.source_document_id, "redirect_count": redirect_count},
                    )
                location = _header_value(response.headers, "location")
                if not location:
                    raise WeeklyNewsOfficialSourceRetrievalError(
                        "weekly_news_source_redirect_missing_location",
                        diagnostics={"source_document_id": request.source_document_id},
                    )
                current_url = urljoin(current_url, location)
                _validate_url_allowed(current_url)
                continue
            if response.status != 200:
                raise WeeklyNewsOfficialSourceRetrievalError(
                    "weekly_news_source_http_status_not_ok",
                    diagnostics={"source_document_id": request.source_document_id, "http_status": response.status},
                )
            content_type = _base_content_type(_header_value(response.headers, "content-type") or "application/octet-stream")
            if content_type not in _ALLOWED_CONTENT_TYPES:
                raise WeeklyNewsOfficialSourceRetrievalError(
                    "weekly_news_source_content_type_not_allowed",
                    diagnostics={"source_document_id": request.source_document_id, "content_type": content_type},
                )
            if len(response.body) > self.max_bytes:
                raise WeeklyNewsOfficialSourceRetrievalError(
                    "weekly_news_source_payload_too_large",
                    diagnostics={
                        "source_document_id": request.source_document_id,
                        "byte_size": len(response.body),
                        "max_bytes": self.max_bytes,
                    },
                )
            checksum = _checksum_bytes(response.body)
            return WeeklyNewsOfficialFetchedDocument(
                boundary=WEEKLY_NEWS_OFFICIAL_DOCUMENT_FETCH_BOUNDARY,
                request=request,
                status="fetched",
                final_url=response.url,
                content_type=content_type,
                payload=response.body,
                text=response.body.decode("utf-8", errors="replace"),
                checksum=checksum,
                retrieved_at=retrieved_at,
                byte_size=len(response.body),
                no_live_external_calls=self.transport is not None,
                sanitized_diagnostics=_sanitize_diagnostics(
                    {
                        "source_document_id": request.source_document_id,
                        "status": "fetched",
                        "content_type": content_type,
                        "byte_size": len(response.body),
                        "checksum": checksum,
                        "redirect_count": redirect_count,
                        "visited_hosts": visited_hosts,
                    }
                ),
            )

    def _fetch_once(self, url: str, headers: dict[str, str]) -> WeeklyNewsOfficialHttpResponse:
        if self.transport is not None:
            return self.transport(url, headers, self.timeout_seconds)
        request = Request(url, headers=headers, method="GET")
        opener = build_opener(_NoRedirectHandler)
        try:
            with opener.open(request, timeout=self.timeout_seconds) as response:
                body = _read_limited(response, self.max_bytes)
                return WeeklyNewsOfficialHttpResponse(
                    url=response.geturl(),
                    status=int(response.status),
                    headers={key.lower(): value for key, value in response.headers.items()},
                    body=body,
                )
        except HTTPError as exc:
            body = b""
            if exc.code not in {301, 302, 303, 307, 308}:
                try:
                    body = _read_limited(exc, self.max_bytes)
                except Exception:
                    body = b""
            return WeeklyNewsOfficialHttpResponse(
                url=exc.geturl(),
                status=int(exc.code),
                headers={key.lower(): value for key, value in exc.headers.items()},
                body=body,
            )


@dataclass(frozen=True)
class WeeklyNewsOfficialSourceParserAdapter:
    def parse(
        self,
        documents: list[WeeklyNewsOfficialFetchedDocument],
        *,
        ticker: str,
        as_of: str,
        created_at: str,
    ) -> WeeklyNewsOfficialDocumentParseResult:
        normalized = normalize_ticker(ticker)
        candidates: list[WeeklyNewsEventCandidateRow] = []
        diagnostics: list[WeeklyNewsOfficialSourceParserDiagnostic] = []
        for index, document in enumerate(documents, start=1):
            event = _event_from_document(document, as_of=as_of)
            if event is None:
                diagnostics.append(
                    WeeklyNewsOfficialSourceParserDiagnostic(
                        boundary=WEEKLY_NEWS_OFFICIAL_SOURCE_PARSER_ADAPTER_BOUNDARY,
                        candidate_event_id=f"unparsed:{document.request.source_document_id}",
                        source_document_id=document.request.source_document_id,
                        parser_status=SourceParserStatus.failed,
                        evidence_state=EvidenceState.unavailable,
                        freshness_state=FreshnessState.unavailable,
                        code="weekly_news_document_parser_failed",
                        parser_failure_diagnostics="parseable_official_event_not_found",
                        no_live_external_calls=document.no_live_external_calls,
                    )
                )
                continue
            candidate = _candidate_from_event(
                document,
                event,
                ticker=normalized,
                as_of=as_of,
                created_at=created_at,
                ordinal=index,
            )
            candidates.append(candidate)
            diagnostics.append(
                WeeklyNewsOfficialSourceParserDiagnostic(
                    boundary=WEEKLY_NEWS_OFFICIAL_SOURCE_PARSER_ADAPTER_BOUNDARY,
                    candidate_event_id=candidate.candidate_event_id,
                    source_document_id=document.request.source_document_id,
                    parser_status=SourceParserStatus.parsed,
                    evidence_state=EvidenceState(candidate.evidence_state),
                    freshness_state=FreshnessState(candidate.freshness_state),
                    code="weekly_news_document_parser_parsed",
                    no_live_external_calls=document.no_live_external_calls,
                )
            )
        return WeeklyNewsOfficialDocumentParseResult(
            boundary=WEEKLY_NEWS_OFFICIAL_DOCUMENT_PARSER_BOUNDARY,
            ticker=normalized,
            candidates=tuple(candidates),
            diagnostics=tuple(diagnostics),
            parser_diagnostic_count=len(diagnostics),
            no_live_external_calls=all(document.no_live_external_calls for document in documents),
            sanitized_diagnostics=_sanitize_diagnostics(
                {
                    "ticker": normalized,
                    "document_count": len(documents),
                    "candidate_count": len(candidates),
                    "parser_diagnostic_count": len(diagnostics),
                    "document_checksums": [document.checksum for document in documents],
                }
            ),
        )


def source_snapshot_records_from_weekly_news_documents(
    documents: list[WeeklyNewsOfficialFetchedDocument],
    candidates: list[WeeklyNewsEventCandidateRow],
    *,
    ticker: str,
    created_at: str,
    storage_prefix: str = "weekly-news-official-source-snapshots",
) -> SourceSnapshotRepositoryRecords:
    normalized = normalize_ticker(ticker)
    candidate_by_source = {candidate.source_document_id: candidate for candidate in candidates}
    artifacts: list[SourceSnapshotArtifactRow] = []
    diagnostics: list[SourceSnapshotDiagnosticRow] = []
    for document in documents:
        candidate = candidate_by_source.get(document.request.source_document_id)
        if candidate is None:
            diagnostics.append(_snapshot_diagnostic(document, normalized, created_at, "parser_failed"))
            continue
        handoff = validate_source_handoff(candidate, action=SourcePolicyAction.generated_claim_support)
        if not handoff.allowed:
            diagnostics.append(_snapshot_diagnostic(document, normalized, created_at, "source_policy_blocked"))
            continue
        decision = resolve_source_policy(url=document.final_url)
        for category in _artifact_categories_for_candidate(candidate):
            artifacts.append(
                SourceSnapshotArtifactRow(
                    artifact_id=f"snapshot-{normalized.lower()}-{document.request.source_document_id}-{category.value}",
                    scope_kind=SourceSnapshotScopeKind.asset.value,
                    asset_ticker=normalized,
                    source_document_id=document.request.source_document_id,
                    source_reference_id=document.request.source_document_id,
                    source_asset_ticker=normalized,
                    artifact_category=category.value,
                    storage_key=(
                        f"{storage_prefix.strip('/')}/{normalized.lower()}/"
                        f"{document.request.source_document_id}/{category.value}.json"
                    ),
                    checksum=document.checksum if category is SourceSnapshotArtifactCategory.raw_source else _checksum_payload(
                        {
                            "document_checksum": document.checksum,
                            "artifact_category": category.value,
                            "candidate_event_id": candidate.candidate_event_id,
                            "evidence_checksum": candidate.evidence_checksum,
                        }
                    ),
                    byte_size=document.byte_size if category is SourceSnapshotArtifactCategory.raw_source else 0,
                    content_type=document.content_type
                    if category is SourceSnapshotArtifactCategory.raw_source
                    else "application/json",
                    retrieved_at=document.retrieved_at,
                    created_at=created_at,
                    source_use_policy=candidate.source_use_policy,
                    allowlist_status=candidate.allowlist_status,
                    source_quality=candidate.source_quality,
                    permitted_operations=decision.permitted_operations.model_dump(mode="json"),
                    source_type=candidate.source_type,
                    source_identity=candidate.source_identity,
                    is_official=candidate.is_official,
                    storage_rights=candidate.storage_rights,
                    export_rights=candidate.export_rights,
                    review_status=candidate.review_status,
                    approval_rationale=candidate.approval_rationale,
                    parser_status=candidate.parser_status,
                    parser_failure_diagnostics=candidate.parser_failure_diagnostics,
                    freshness_state=candidate.freshness_state,
                    evidence_state=candidate.evidence_state,
                    can_feed_generated_output=True,
                    can_support_citations=decision.permitted_operations.can_support_citations,
                    cache_allowed=decision.permitted_operations.can_cache,
                    export_allowed=decision.permitted_operations.can_export_metadata,
                    generated_output_available=False,
                    compact_diagnostics={
                        "boundary": WEEKLY_NEWS_OFFICIAL_SOURCE_SNAPSHOT_BOUNDARY,
                        "asset_ticker": normalized,
                        "source_document_id": document.request.source_document_id,
                        "artifact_category": category.value,
                        "document_checksum": document.checksum,
                        "evidence_checksum": candidate.evidence_checksum,
                        "content_type": document.content_type,
                        "byte_size": document.byte_size,
                    },
                )
            )
        diagnostics.append(_snapshot_diagnostic(document, normalized, created_at, "parsed"))
    return validate_source_snapshot_records(SourceSnapshotRepositoryRecords(artifacts=artifacts, diagnostics=diagnostics))


def _event_from_document(document: WeeklyNewsOfficialFetchedDocument, *, as_of: str) -> dict[str, Any] | None:
    if document.content_type == "application/json":
        event = _sec_event_from_json(document.text)
        if event is not None:
            return event
    if document.content_type in {"text/html", "application/xhtml+xml", "text/plain"}:
        event = _html_event(document.text, document.request, as_of=as_of)
        if event is not None:
            return event
    return None


def _sec_event_from_json(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    recent = payload.get("filings", {}).get("recent", {}) if isinstance(payload, dict) else {}
    forms = recent.get("form") or []
    filing_dates = recent.get("filingDate") or []
    report_dates = recent.get("reportDate") or []
    accession_numbers = recent.get("accessionNumber") or []
    primary_documents = recent.get("primaryDocument") or []
    prioritized_forms = {"8-K", "10-Q", "10-K", "10-Q/A", "10-K/A"}
    rows = []
    for index, form in enumerate(forms):
        filing_date = _list_item(filing_dates, index)
        if not filing_date or not _looks_like_iso_date(filing_date):
            continue
        rows.append(
            {
                "priority": 0 if str(form) in prioritized_forms else 1,
                "event_date": filing_date,
                "published_at": f"{filing_date}T00:00:00Z",
                "form": str(form),
                "report_date": _list_item(report_dates, index),
                "accession_number": _list_item(accession_numbers, index),
                "primary_document": _list_item(primary_documents, index),
            }
        )
    if not rows:
        return None
    best_priority = min(row["priority"] for row in rows)
    selected = max((row for row in rows if row["priority"] == best_priority), key=lambda row: row["event_date"])
    form = selected["form"]
    event_type = WeeklyNewsEventType.earnings.value if form in {"10-Q", "10-K", "10-Q/A", "10-K/A"} else WeeklyNewsEventType.regulatory_event.value
    return {
        "event_type": event_type,
        "event_title": f"SEC filing update: {form}",
        "event_summary": f"Official SEC submissions data shows a recent {form} filing.",
        "event_date": selected["event_date"],
        "published_at": selected["published_at"],
        "parsed_fields": {
            "form": form,
            "report_date": selected["report_date"],
            "accession_number": selected["accession_number"],
            "primary_document": selected["primary_document"],
        },
    }


def _html_event(text: str, request: WeeklyNewsOfficialSourceRequest, *, as_of: str) -> dict[str, Any] | None:
    parser = _CompactHtmlParser()
    parser.feed(text)
    title = parser.title or request.source_title
    description = parser.description or parser.visible_text[:240] or request.source_title
    event_date = parser.first_date or _extract_date(text) or _fallback_recent_date(as_of)
    if not event_date:
        return None
    return {
        "event_type": request.event_type,
        "event_title": _compact_title(title),
        "event_summary": _compact_summary(description, request),
        "event_date": event_date,
        "published_at": f"{event_date}T00:00:00Z",
        "parsed_fields": {
            "html_title": _compact_title(title),
            "description_checksum": _checksum_text(description),
        },
    }


def _candidate_from_event(
    document: WeeklyNewsOfficialFetchedDocument,
    event: dict[str, Any],
    *,
    ticker: str,
    as_of: str,
    created_at: str,
    ordinal: int,
) -> WeeklyNewsEventCandidateRow:
    request = document.request
    decision = resolve_source_policy(url=document.final_url)
    handoff_fields = source_handoff_fields_from_policy(
        decision,
        source_identity=document.final_url,
        parser_status=SourceParserStatus.parsed,
        approval_rationale=(
            "Fetched official Weekly News source was parsed into a same-asset event and is approved by "
            "the local source-use allowlist for generated-claim support."
        ),
    )
    if not source_can_support_generated_output(decision):
        handoff_fields = source_handoff_fields_from_policy(
            decision,
            source_identity=document.final_url,
            parser_status=SourceParserStatus.pending_review,
            approval_rationale="Fetched official Weekly News source is not approved for generated-claim support.",
        )
    event_date = str(event["event_date"])
    freshness_state = _freshness_for_event(event_date, as_of)
    evidence_state = EvidenceState.stale.value if freshness_state == FreshnessState.stale.value else EvidenceState.supported.value
    event_payload = {
        "ticker": ticker,
        "source_document_id": request.source_document_id,
        "document_checksum": document.checksum,
        "event": event,
        "source_rank_tier": request.source_rank_tier,
    }
    evidence_checksum = _checksum_payload(event_payload)
    title_checksum = _checksum_payload({"document_checksum": document.checksum, "event_title": event["event_title"]})
    candidate_event_id = f"{ticker.lower()}:{request.source_document_id}:{ordinal}:{event_date.replace('-', '')}"
    citation_id = f"c_weekly_{ticker.lower()}_{_slug(request.source_document_id)}"
    return WeeklyNewsEventCandidateRow(
        candidate_event_id=candidate_event_id,
        window_id=f"wnf_window:{ticker}:{as_of}",
        asset_ticker=ticker,
        source_asset_ticker=ticker,
        event_type=str(event["event_type"]),
        event_title=str(event["event_title"]),
        event_summary=str(event["event_summary"]),
        event_date=event_date,
        published_at=str(event["published_at"]),
        retrieved_at=document.retrieved_at,
        period_bucket=WeeklyNewsPeriodBucket.current_week_to_date.value,
        source_document_id=request.source_document_id,
        source_chunk_id=f"chunk:{request.source_document_id}:parsed-event",
        citation_ids=[citation_id],
        citation_asset_tickers={citation_id: ticker},
        source_type=request.source_rank_tier,
        source_title=request.source_title,
        source_publisher=request.source_publisher,
        source_url=document.final_url,
        source_rank=request.source_rank,
        source_rank_tier=request.source_rank_tier,
        source_quality=request.source_quality,
        allowlist_status=decision.allowlist_status.value,
        source_use_policy=decision.source_use_policy.value,
        source_identity=document.final_url,
        is_official=request.is_official,
        storage_rights=handoff_fields["storage_rights"].value,
        export_rights=handoff_fields["export_rights"].value,
        review_status=handoff_fields["review_status"].value,
        approval_rationale=str(handoff_fields["approval_rationale"]),
        parser_status=handoff_fields["parser_status"].value,
        parser_failure_diagnostics=handoff_fields["parser_failure_diagnostics"],
        freshness_state=freshness_state,
        evidence_state=evidence_state,
        importance_score=10,
        license_allowed=decision.source_use_policy in {SourceUsePolicy.full_text_allowed, SourceUsePolicy.summary_allowed},
        recognized_source=decision.allowlist_status == SourceAllowlistStatus.allowed,
        duplicate_group_id=f"{ticker}:{request.source_rank_tier}:{event_date}:{title_checksum}",
        candidate_decision="candidate",
        suppression_reason_codes=[],
        title_checksum=title_checksum,
        evidence_checksum=evidence_checksum,
        stores_raw_article_text=False,
        stores_raw_provider_payload=False,
        stores_unrestricted_source_text=False,
        stores_secret=False,
    )


def _validate_url_allowed(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise WeeklyNewsOfficialSourceRetrievalError("weekly_news_source_url_scheme_not_allowed")
    if parsed.username or parsed.password:
        raise WeeklyNewsOfficialSourceRetrievalError("weekly_news_source_url_credentials_not_allowed")
    host = parsed.hostname
    if not host:
        raise WeeklyNewsOfficialSourceRetrievalError("weekly_news_source_url_host_missing")
    normalized_host = host.lower().rstrip(".")
    if normalized_host == "localhost" or normalized_host.endswith(".local"):
        raise WeeklyNewsOfficialSourceRetrievalError("weekly_news_source_host_not_allowed", diagnostics={"host": normalized_host})
    try:
        address = ip_address(normalized_host.strip("[]"))
    except ValueError:
        address = None
    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise WeeklyNewsOfficialSourceRetrievalError("weekly_news_source_host_not_allowed", diagnostics={"host": "ip_address"})
    if _query_has_sensitive_key(parsed.query):
        raise WeeklyNewsOfficialSourceRetrievalError("weekly_news_source_url_secret_query_not_allowed")
    decision = resolve_source_policy(url=url)
    if decision.allowlist_status is not SourceAllowlistStatus.allowed:
        raise WeeklyNewsOfficialSourceRetrievalError(
            "weekly_news_source_url_not_allowlisted",
            diagnostics={"host": normalized_host, "allowlist_status": decision.allowlist_status.value},
        )


def _query_has_sensitive_key(query: str) -> bool:
    if not query:
        return False
    for part in query.split("&"):
        key = part.split("=", 1)[0].lower()
        if key in _SENSITIVE_QUERY_KEYS or any(marker in key for marker in ("secret", "token", "credential", "password")):
            return True
    return False


def _read_limited(response: Any, max_bytes: int) -> bytes:
    body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise WeeklyNewsOfficialSourceRetrievalError(
            "weekly_news_source_payload_too_large",
            diagnostics={"byte_size": len(body), "max_bytes": max_bytes},
        )
    return body


def _artifact_categories_for_candidate(candidate: WeeklyNewsEventCandidateRow) -> tuple[SourceSnapshotArtifactCategory, ...]:
    if candidate.source_use_policy == SourceUsePolicy.full_text_allowed.value:
        return (SourceSnapshotArtifactCategory.raw_source, SourceSnapshotArtifactCategory.parsed_text)
    if candidate.source_use_policy == SourceUsePolicy.summary_allowed.value:
        return (SourceSnapshotArtifactCategory.summary,)
    return (SourceSnapshotArtifactCategory.checksum_metadata,)


def _snapshot_diagnostic(
    document: WeeklyNewsOfficialFetchedDocument,
    ticker: str,
    created_at: str,
    status: str,
) -> SourceSnapshotDiagnosticRow:
    return SourceSnapshotDiagnosticRow(
        diagnostic_id=f"snapshot-{ticker.lower()}-{document.request.source_document_id}-{status}",
        artifact_id=None,
        category=(
            SourceSnapshotDiagnosticCategory.unknown.value
            if status == "parsed"
            else SourceSnapshotDiagnosticCategory.source_policy_blocked.value
        ),
        retrieval_status=status,
        retryable=False,
        source_policy_ref="weekly-news-official-source-handoff",
        checksum=document.checksum,
        occurred_at=document.retrieved_at,
        created_at=created_at,
        compact_metadata={
            "boundary": WEEKLY_NEWS_OFFICIAL_SOURCE_SNAPSHOT_BOUNDARY,
            "asset_ticker": ticker,
            "source_document_id": document.request.source_document_id,
            "status": status,
            "checksum": document.checksum,
            "content_type": document.content_type,
            "byte_size": document.byte_size,
        },
    )


class _CompactHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self._skip_depth = 0
        self._chunks: list[str] = []
        self._title_chunks: list[str] = []
        self._meta_description: str | None = None
        self._dates: list[str] = []

    @property
    def title(self) -> str | None:
        value = _collapse_whitespace(" ".join(self._title_chunks))
        return value or None

    @property
    def description(self) -> str | None:
        return self._meta_description

    @property
    def visible_text(self) -> str:
        return _collapse_whitespace(" ".join(self._chunks))

    @property
    def first_date(self) -> str | None:
        return self._dates[0] if self._dates else None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        attr_map = {key.lower(): value for key, value in attrs if key}
        if lowered in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if lowered == "title":
            self._in_title = True
        if lowered == "meta":
            name = (attr_map.get("name") or attr_map.get("property") or "").lower()
            if name in {"description", "og:description"} and attr_map.get("content"):
                self._meta_description = _collapse_whitespace(str(attr_map["content"]))
        if lowered == "time":
            value = attr_map.get("datetime")
            if value:
                parsed = _extract_date(value)
                if parsed:
                    self._dates.append(parsed)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if lowered == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        compact = _collapse_whitespace(data)
        if not compact:
            return
        if self._in_title:
            self._title_chunks.append(compact)
        self._chunks.append(compact)
        parsed = _extract_date(compact)
        if parsed:
            self._dates.append(parsed)


def _extract_date(text: str) -> str | None:
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if iso:
        return iso.group(1)
    month = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
        r"([0-3]?\d),\s+(20\d{2})\b",
        text,
        flags=re.IGNORECASE,
    )
    if month:
        months = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }
        return date(int(month.group(3)), months[month.group(1).lower()], int(month.group(2))).isoformat()
    return None


def _fallback_recent_date(as_of: str) -> str | None:
    window = compute_weekly_news_window(as_of)
    return window.current_week_to_date_end or window.previous_market_week_end


def _freshness_for_event(event_date: str, as_of: str) -> str:
    try:
        event = date.fromisoformat(event_date)
        window = compute_weekly_news_window(as_of)
        if date.fromisoformat(window.news_window_start) <= event <= date.fromisoformat(window.news_window_end):
            return FreshnessState.fresh.value
    except Exception:
        return FreshnessState.unavailable.value
    return FreshnessState.stale.value


def _looks_like_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _list_item(items: Any, index: int) -> Any | None:
    if isinstance(items, list) and index < len(items):
        return items[index]
    return None


def _checksum_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _checksum_text(value: str) -> str:
    return _checksum_bytes(value.encode("utf-8"))


def _checksum_payload(payload: dict[str, Any]) -> str:
    return _checksum_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def _header_value(headers: dict[str, str], key: str) -> str | None:
    lowered = key.lower()
    for header, value in headers.items():
        if header.lower() == lowered:
            return value
    return None


def _base_content_type(value: str) -> str:
    return value.split(";", 1)[0].strip().lower()


def _safe_host(url: str) -> str:
    host = urlsplit(url).hostname or "unknown"
    parts = host.lower().split(".")
    if len(parts) <= 2:
        return host.lower()
    return ".".join(parts[-2:])


def _sanitize_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    sanitized = json.loads(json.dumps(diagnostics, sort_keys=True, default=str))
    text = repr(sanitized).lower()
    if any(marker in text for marker in ("secret", "authorization", "bearer ", "api_key", "access_token")):
        return {"sanitized": True, "diagnostic_status": "redacted_sensitive_marker"}
    return sanitized


def _compact_title(value: str) -> str:
    compact = _collapse_whitespace(value)
    return compact[:180] or "Official Weekly News source update"


def _compact_summary(value: str, request: WeeklyNewsOfficialSourceRequest) -> str:
    compact = _collapse_whitespace(value)
    if not compact:
        compact = f"Official {request.source_publisher} source was retrieved and parsed for {request.ticker}."
    return compact[:280]


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
