from __future__ import annotations

from dataclasses import dataclass

from backend.data import (
    ASSETS,
    OUT_OF_SCOPE_COMMON_STOCKS,
    UNSUPPORTED_ASSET_SEARCH_METADATA,
    UNSUPPORTED_ASSETS,
    load_top500_stock_universe_manifest,
    normalize_ticker,
    top500_stock_universe_entry,
)
from backend.etf_universe import blocked_etf_entries, eligible_not_cached_etf_entries, etf_universe_entry
from backend.models import (
    AssetIdentity,
    AssetType,
    ETFUniverseEntry,
    ETFUniverseSupportState,
    SearchBlockedCapabilityFlags,
    SearchBlockedExplanation,
    SearchBlockedExplanationDiagnostics,
    SearchResponse,
    SearchResponseStatus,
    SearchResult,
    SearchResultStatus,
    SearchState,
    SearchSupportClassification,
)


@dataclass(frozen=True)
class SearchCandidate:
    ticker: str
    name: str
    asset_type: AssetType
    exchange: str | None
    issuer: str | None
    support_classification: SearchSupportClassification
    message: str
    aliases: tuple[str, ...] = ()


SUPPORTED_V1_SCOPE_REMINDER = (
    "Supported MVP coverage is limited to U.S.-listed common stocks in the current Top-500 manifest "
    "and ETFs in the approved supported ETF manifest."
)

UNSUPPORTED_EXPLANATION_CATEGORY_LABELS = {
    "crypto": "crypto_assets",
    "leveraged_etf": "leveraged_etf",
    "inverse_etf": "inverse_etf",
    "active_etf": "active_etf",
    "fixed_income_etf": "fixed_income_etf",
    "commodity_etf": "commodity_etf",
    "multi_asset_etf": "multi_asset_etf",
    "etn": "etn",
    "other_unsupported": "unsupported_etf_like_product",
}


def search_assets(q: str) -> SearchResponse:
    raw_query = q.strip()
    normalized_ticker = normalize_ticker(q)
    candidates = _ranked_candidates(raw_query, normalized_ticker)

    if candidates:
        results = [_candidate_to_result(candidate) for _, candidate in candidates]
        if len(results) > 1:
            return SearchResponse(
                query=q,
                results=results,
                state=SearchState(
                    status=SearchResponseStatus.ambiguous,
                    message=(
                        "Multiple deterministic local candidates matched this search. "
                        "Choose a ticker before opening any generated asset experience."
                    ),
                    result_count=len(results),
                    requires_disambiguation=True,
                ),
            )

        result = results[0]
        blocked_explanation = _blocked_explanation_for_result(result)
        if blocked_explanation is not None:
            result = result.model_copy(update={"blocked_explanation": blocked_explanation})
            results = [result]
        return SearchResponse(
            query=q,
            results=results,
            state=_state_for_single_result(result, blocked_explanation=blocked_explanation),
        )

    unknown = SearchResult(
        ticker=normalized_ticker,
        name=normalized_ticker,
        asset_type=AssetType.unknown,
        supported=False,
        status=SearchResultStatus.unknown,
        support_classification=SearchSupportClassification.unknown,
        eligible_for_ingestion=False,
        requires_ingestion=False,
        can_open_generated_page=False,
        can_answer_chat=False,
        can_compare=False,
        generated_route=None,
        message="No deterministic local fixture or recognized eligible asset matched this query.",
    )
    return SearchResponse(
        query=q,
        results=[unknown],
        state=SearchState(
            status=SearchResponseStatus.unknown,
            message="Unknown or unavailable in local deterministic search data; no facts are invented.",
            result_count=1,
            support_classification=SearchSupportClassification.unknown,
        ),
    )


def _ranked_candidates(raw_query: str, normalized_ticker: str) -> list[tuple[int, SearchCandidate]]:
    if not raw_query:
        return []

    candidates = _all_candidates()
    exact_ticker_matches = [candidate for candidate in candidates if candidate.ticker == normalized_ticker]
    if exact_ticker_matches:
        return [(100, exact_ticker_matches[0])]

    scored: list[tuple[int, SearchCandidate]] = []
    query = raw_query.lower()
    for candidate in candidates:
        score = _score_candidate(query, normalized_ticker, candidate)
        if score > 0:
            scored.append((score, candidate))

    scored.sort(key=lambda item: (-item[0], item[1].ticker))
    return scored


def _all_candidates() -> list[SearchCandidate]:
    candidates: list[SearchCandidate] = []

    for payload in ASSETS.values():
        identity: AssetIdentity = payload["identity"]
        aliases = _supported_aliases(identity)
        candidates.append(
            SearchCandidate(
                ticker=identity.ticker,
                name=identity.name,
                asset_type=identity.asset_type,
                exchange=identity.exchange,
                issuer=identity.issuer,
                support_classification=SearchSupportClassification.cached_supported,
                message="Cached supported asset with deterministic local page, chat, and comparison data.",
                aliases=aliases,
            )
        )

    etf_manifest_tickers = {entry.ticker for entry in blocked_etf_entries().values()}
    for ticker, reason in UNSUPPORTED_ASSETS.items():
        if ticker in etf_manifest_tickers:
            continue
        metadata = UNSUPPORTED_ASSET_SEARCH_METADATA.get(ticker, {})
        candidates.append(
            SearchCandidate(
                ticker=ticker,
                name=str(metadata.get("name") or ticker),
                asset_type=AssetType.unsupported,
                exchange=None,
                issuer=None,
                support_classification=SearchSupportClassification.recognized_unsupported,
                message=reason,
                aliases=tuple(str(alias) for alias in metadata.get("aliases") or ()),
            )
        )

    for entry in load_top500_stock_universe_manifest().entries:
        if entry.ticker in ASSETS:
            continue
        candidates.append(
            SearchCandidate(
                ticker=entry.ticker,
                name=entry.name,
                asset_type=AssetType.stock,
                exchange=entry.exchange,
                issuer=None,
                support_classification=SearchSupportClassification.eligible_not_cached,
                message=(
                    "Top-500 manifest-backed U.S.-listed common stock, but no local cached knowledge pack "
                    "is available yet. On-demand ingestion would be required later."
                ),
                aliases=tuple(entry.aliases),
            )
        )

    for entry in eligible_not_cached_etf_entries().values():
        candidates.append(_etf_entry_to_candidate(entry))

    for entry in blocked_etf_entries().values():
        candidates.append(_etf_entry_to_candidate(entry))

    for ticker, metadata in OUT_OF_SCOPE_COMMON_STOCKS.items():
        if etf_universe_entry(ticker) is not None:
            continue
        candidates.append(
            SearchCandidate(
                ticker=ticker,
                name=str(metadata["name"]),
                asset_type=AssetType(str(metadata.get("asset_type") or AssetType.stock.value)),
                exchange=str(metadata["exchange"]) if metadata.get("exchange") else None,
                issuer=None,
                support_classification=SearchSupportClassification.out_of_scope,
                message=str(metadata["reason"]),
                aliases=tuple(str(alias) for alias in metadata.get("aliases") or ()),
            )
        )

    return candidates


def _etf_entry_to_candidate(entry: ETFUniverseEntry) -> SearchCandidate:
    asset_type = (
        AssetType.unsupported
        if entry.support_state is ETFUniverseSupportState.recognized_unsupported
        else AssetType.etf
    )
    return SearchCandidate(
        ticker=entry.ticker,
        name=entry.fund_name,
        asset_type=asset_type,
        exchange=entry.exchange,
        issuer=entry.issuer,
        support_classification=_support_classification_for_etf_entry(entry),
        message=_message_for_etf_entry(entry),
        aliases=tuple(entry.aliases),
    )


def _support_classification_for_etf_entry(entry: ETFUniverseEntry) -> SearchSupportClassification:
    if entry.support_state is ETFUniverseSupportState.eligible_not_cached:
        return SearchSupportClassification.eligible_not_cached
    if entry.support_state is ETFUniverseSupportState.recognized_unsupported:
        return SearchSupportClassification.recognized_unsupported
    if entry.support_state is ETFUniverseSupportState.out_of_scope:
        return SearchSupportClassification.out_of_scope
    return SearchSupportClassification.unknown


def _message_for_etf_entry(entry: ETFUniverseEntry) -> str:
    if entry.support_state is ETFUniverseSupportState.eligible_not_cached:
        return (
            "Eligible non-leveraged U.S.-listed equity ETF from the ETF universe metadata contract, "
            "but no local cached knowledge pack is available yet. On-demand ingestion would be required later."
        )
    if entry.support_state is ETFUniverseSupportState.recognized_unsupported:
        metadata = UNSUPPORTED_ASSET_SEARCH_METADATA.get(entry.ticker, {})
        return str(metadata.get("reason") or UNSUPPORTED_ASSETS.get(entry.ticker) or entry.entry_provenance)
    if entry.support_state is ETFUniverseSupportState.out_of_scope:
        metadata = OUT_OF_SCOPE_COMMON_STOCKS.get(entry.ticker, {})
        return str(metadata.get("reason") or entry.entry_provenance)
    if entry.support_state is ETFUniverseSupportState.unavailable:
        return entry.evidence.unavailable_reason or (
            "Required ETF classification metadata is unavailable in the deterministic fixture."
        )
    return "ETF classification metadata is unknown in the deterministic fixture; no facts are invented."


def _supported_aliases(identity: AssetIdentity) -> tuple[str, ...]:
    aliases: list[str] = []
    if identity.issuer:
        aliases.append(identity.issuer)
    if identity.asset_type is AssetType.etf:
        entry = etf_universe_entry(identity.ticker)
        if entry:
            aliases.extend(entry.aliases)
    elif identity.asset_type is AssetType.stock:
        entry = top500_stock_universe_entry(identity.ticker)
        if entry:
            aliases.extend(entry.aliases)
            aliases.append("top-500 manifest common stock")
    return tuple(aliases)


def _score_candidate(query: str, normalized_ticker: str, candidate: SearchCandidate) -> int:
    name = candidate.name.lower()
    aliases = [alias.lower() for alias in candidate.aliases]
    issuer = candidate.issuer.lower() if candidate.issuer else ""

    if normalized_ticker and candidate.ticker.startswith(normalized_ticker):
        return 80
    if query == name:
        return 75
    if query in name:
        return 60
    if any(query == alias for alias in aliases):
        return 58
    if any(query in alias for alias in aliases):
        return 50
    if issuer and query in issuer:
        return 35
    return 0


def _candidate_to_result(candidate: SearchCandidate) -> SearchResult:
    cached_supported = candidate.support_classification is SearchSupportClassification.cached_supported
    eligible_not_cached = candidate.support_classification is SearchSupportClassification.eligible_not_cached
    recognized_unsupported = candidate.support_classification is SearchSupportClassification.recognized_unsupported
    out_of_scope = candidate.support_classification is SearchSupportClassification.out_of_scope

    if cached_supported:
        status = SearchResultStatus.supported
    elif eligible_not_cached:
        status = SearchResultStatus.ingestion_needed
    elif recognized_unsupported:
        status = SearchResultStatus.unsupported
    elif out_of_scope:
        status = SearchResultStatus.out_of_scope
    else:
        status = SearchResultStatus.unknown

    generated_route = f"/assets/{candidate.ticker}" if cached_supported else None
    return SearchResult(
        ticker=candidate.ticker,
        name=candidate.name,
        asset_type=candidate.asset_type,
        exchange=candidate.exchange,
        issuer=candidate.issuer,
        supported=cached_supported,
        status=status,
        support_classification=candidate.support_classification,
        eligible_for_ingestion=eligible_not_cached,
        requires_ingestion=eligible_not_cached,
        can_open_generated_page=cached_supported,
        can_answer_chat=cached_supported,
        can_compare=cached_supported,
        generated_route=generated_route,
        can_request_ingestion=eligible_not_cached,
        ingestion_request_route=f"/api/admin/ingest/{candidate.ticker}" if eligible_not_cached else None,
        message=candidate.message,
    )


def _state_for_single_result(
    result: SearchResult,
    *,
    blocked_explanation: SearchBlockedExplanation | None = None,
) -> SearchState:
    if result.support_classification is SearchSupportClassification.cached_supported:
        return SearchState(
            status=SearchResponseStatus.supported,
            message="One cached supported asset matched and is safe to open as a local generated asset page.",
            result_count=1,
            support_classification=result.support_classification,
            can_open_generated_page=True,
            generated_route=result.generated_route,
        )
    if result.support_classification is SearchSupportClassification.eligible_not_cached:
        return SearchState(
            status=SearchResponseStatus.ingestion_needed,
            message=(
                "This asset appears eligible for future support, but it is not locally cached. "
                "No generated page, chat, or comparison output is available in this task."
            ),
            result_count=1,
            support_classification=result.support_classification,
            requires_ingestion=True,
            can_request_ingestion=True,
            ingestion_request_route=f"/api/admin/ingest/{result.ticker}",
        )
    if result.support_classification is SearchSupportClassification.recognized_unsupported:
        return SearchState(
            status=SearchResponseStatus.unsupported,
            message=result.message or "Recognized asset type is outside the current product scope.",
            result_count=1,
            support_classification=result.support_classification,
            blocked_explanation=blocked_explanation,
        )
    if result.support_classification is SearchSupportClassification.out_of_scope:
        return SearchState(
            status=SearchResponseStatus.out_of_scope,
            message=(
                result.message
                or "Recognized common stock is outside the current Top-500 manifest-backed support scope."
            ),
            result_count=1,
            support_classification=result.support_classification,
            blocked_explanation=blocked_explanation,
        )
    return SearchState(
        status=SearchResponseStatus.unknown,
        message="Unknown or unavailable in local deterministic search data; no facts are invented.",
        result_count=1,
        support_classification=SearchSupportClassification.unknown,
    )


def _blocked_explanation_for_result(result: SearchResult) -> SearchBlockedExplanation | None:
    if result.support_classification is SearchSupportClassification.recognized_unsupported:
        metadata = UNSUPPORTED_ASSET_SEARCH_METADATA.get(result.ticker, {})
        category = str(metadata.get("category") or "unsupported_asset")
        return SearchBlockedExplanation(
            status=SearchResponseStatus.unsupported,
            support_classification=result.support_classification,
            explanation_category=UNSUPPORTED_EXPLANATION_CATEGORY_LABELS.get(category, "unsupported_asset"),
            summary=(
                f"{result.ticker} is recognized, but this asset category is outside the current supported MVP coverage."
            ),
            scope_rationale=result.message or "This asset category is outside the current supported MVP scope.",
            supported_v1_scope=SUPPORTED_V1_SCOPE_REMINDER,
            blocked_capabilities=SearchBlockedCapabilityFlags(),
            ingestion_eligible=False,
            ingestion_request_route=None,
            diagnostics=SearchBlockedExplanationDiagnostics(),
        )

    if result.support_classification is SearchSupportClassification.out_of_scope:
        if result.asset_type is AssetType.etf:
            return SearchBlockedExplanation(
                status=SearchResponseStatus.out_of_scope,
                support_classification=result.support_classification,
                explanation_category="etf_like_product_scope",
                summary=(
                    f"{result.ticker} is recognized, but this ETF-like product is outside the current supported MVP coverage."
                ),
                scope_rationale=result.message or "This ETF-like product is outside the current supported MVP scope.",
                supported_v1_scope=SUPPORTED_V1_SCOPE_REMINDER,
                blocked_capabilities=SearchBlockedCapabilityFlags(),
                ingestion_eligible=False,
                ingestion_request_route=None,
                diagnostics=SearchBlockedExplanationDiagnostics(),
            )
        return SearchBlockedExplanation(
            status=SearchResponseStatus.out_of_scope,
            support_classification=result.support_classification,
            explanation_category="top500_manifest_scope",
            summary=(
                f"{result.ticker} is recognized, but it is outside the current Top-500 manifest-backed supported MVP stock coverage."
            ),
            scope_rationale=result.message or (
                "Recognized U.S.-listed common stock outside the current Top-500 manifest-backed MVP scope."
            ),
            supported_v1_scope=SUPPORTED_V1_SCOPE_REMINDER,
            blocked_capabilities=SearchBlockedCapabilityFlags(),
            ingestion_eligible=False,
            ingestion_request_route=None,
            diagnostics=SearchBlockedExplanationDiagnostics(),
        )

    return None
