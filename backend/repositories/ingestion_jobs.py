from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from backend.data import (
    ASSETS,
    ELIGIBLE_NOT_CACHED_ASSETS,
    OUT_OF_SCOPE_COMMON_STOCKS,
    UNSUPPORTED_ASSETS,
    normalize_ticker,
)
from backend.models import AssetIdentity, IngestionJobResponse, PreCacheJobResponse
from backend.repositories.knowledge_packs import RepositoryMetadata, RepositoryTableDefinition, StrictRow


INGESTION_JOB_LEDGER_REPOSITORY_BOUNDARY = "ingestion-job-ledger-repository-contract-v1"
INGESTION_JOB_LEDGER_TABLES = (
    "ingestion_job_ledger_records",
    "ingestion_job_ledger_source_refs",
    "ingestion_job_ledger_diagnostics",
)
BLOCKED_GENERATED_OUTPUT_STATES = {"failed", "unsupported", "out_of_scope", "unknown", "unavailable"}


class IngestionJobLedgerContractError(ValueError):
    """Raised when an ingestion job ledger row breaks MVP scope or storage boundaries."""


class IngestionJobCategory(str, Enum):
    manual_pre_cache = "manual_pre_cache"
    approved_on_demand = "approved_on_demand"
    refresh = "refresh"
    source_revalidation = "source_revalidation"


class IngestionLedgerJobState(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    unsupported = "unsupported"
    out_of_scope = "out_of_scope"
    unknown = "unknown"
    unavailable = "unavailable"
    stale = "stale"


class IngestionScopeDecision(str, Enum):
    cached_supported_asset = "cached_supported_asset"
    approved_pending_ingestion = "approved_pending_ingestion"
    blocked_unsupported_asset = "blocked_unsupported_asset"
    blocked_out_of_scope_asset = "blocked_out_of_scope_asset"
    unknown_or_unavailable_asset = "unknown_or_unavailable_asset"


class SanitizedErrorCategory(str, Enum):
    source_unavailable = "source_unavailable"
    provider_unavailable = "provider_unavailable"
    parser_failed = "parser_failed"
    source_policy_blocked = "source_policy_blocked"
    scope_blocked = "scope_blocked"
    validation_failed = "validation_failed"
    unknown = "unknown"


class IngestionScopeBoundaryRow(StrictRow):
    ticker: str
    asset_type: str
    asset_name: str | None = None
    exchange: str | None = None
    issuer: str | None = None
    scope_decision: str
    support_status: str
    approval_basis: str
    top500_manifest_member: bool = False
    approved_for_on_demand_ingestion: bool = False
    generated_output_allowed: bool = False


class IngestionJobLedgerRecordRow(StrictRow):
    job_id: str
    job_category: str
    ticker: str
    asset_type: str
    job_state: str
    worker_status: str | None = None
    scope_decision: str
    support_status: str
    approval_basis: str
    retryable: bool = False
    generated_route: str | None = None
    generated_output_available: bool = False
    can_open_generated_page: bool = False
    can_answer_chat: bool = False
    can_compare: bool = False
    can_request_ingestion: bool = False
    status_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    batch_id: str | None = None
    launch_group: str | None = None
    compact_metadata: dict[str, Any] = Field(default_factory=dict)
    no_live_external_calls: bool = True
    raw_provider_payload_stored: bool = False
    raw_article_text_stored: bool = False
    raw_user_text_stored: bool = False
    unrestricted_source_text_stored: bool = False
    secrets_stored: bool = False

    @field_validator("ticker")
    @classmethod
    def _ticker_is_normalized(cls, value: str) -> str:
        normalized = normalize_ticker(value)
        if value != normalized:
            raise ValueError("ticker must be normalized uppercase")
        return value


class IngestionJobLedgerSourceRefRow(StrictRow):
    job_id: str
    source_ref_id: str
    source_type: str
    source_use_policy: str
    allowlist_status: str
    checksum: str | None = None
    source_policy_ref: str | None = None
    retrieved_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    stores_raw_text: bool = False


class IngestionJobLedgerDiagnosticRow(StrictRow):
    job_id: str
    diagnostic_id: str
    category: str
    error_code: str | None = None
    sanitized_message: str | None = None
    retryable: bool = False
    occurred_at: str | None = None
    stores_secret: bool = False
    stores_user_text: bool = False
    stores_provider_payload: bool = False
    stores_raw_source_text: bool = False


class IngestionJobLedgerRecords(StrictRow):
    ledger: IngestionJobLedgerRecordRow
    scope: IngestionScopeBoundaryRow
    source_refs: list[IngestionJobLedgerSourceRefRow] = Field(default_factory=list)
    diagnostics: list[IngestionJobLedgerDiagnosticRow] = Field(default_factory=list)

    @property
    def table_names(self) -> tuple[str, ...]:
        return INGESTION_JOB_LEDGER_TABLES


def ingestion_job_ledger_repository_metadata() -> RepositoryMetadata:
    return RepositoryMetadata(
        boundary=INGESTION_JOB_LEDGER_REPOSITORY_BOUNDARY,
        table_definitions=(
            RepositoryTableDefinition(
                name="ingestion_job_ledger_records",
                primary_key=("job_id",),
                columns=tuple(IngestionJobLedgerRecordRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="ingestion_job_ledger_source_refs",
                primary_key=("job_id", "source_ref_id"),
                columns=tuple(IngestionJobLedgerSourceRefRow.model_fields),
            ),
            RepositoryTableDefinition(
                name="ingestion_job_ledger_diagnostics",
                primary_key=("job_id", "diagnostic_id"),
                columns=tuple(IngestionJobLedgerDiagnosticRow.model_fields),
            ),
        ),
    )


@dataclass
class IngestionJobLedgerRepository:
    session: Any | None = None
    commit_on_write: bool = False

    def classify_scope(self, ticker: str) -> IngestionScopeBoundaryRow:
        return classify_ingestion_scope(ticker)

    def serialize_response(
        self,
        response: IngestionJobResponse | PreCacheJobResponse,
        *,
        category: IngestionJobCategory | str | None = None,
    ) -> IngestionJobLedgerRecords:
        return serialize_ingestion_job_response(response, category=category)

    def persist(self, records: IngestionJobLedgerRecords) -> IngestionJobLedgerRecords:
        validated = validate_ingestion_job_ledger_records(records)
        if self.session is None:
            return validated
        _persist_records(
            self.session,
            collection="ingestion_job_ledger",
            key=validated.ledger.job_id,
            records=validated,
            rows=records_to_row_list(validated),
            commit_on_write=self.commit_on_write,
        )
        return validated

    def save(self, records: IngestionJobLedgerRecords) -> None:
        self.persist(records)

    def get(self, job_id: str) -> IngestionJobLedgerRecords | None:
        if self.session is None:
            return None
        raw = _read_records(self.session, "ingestion_job_ledger", job_id)
        if raw is None:
            return None
        records = raw if isinstance(raw, IngestionJobLedgerRecords) else IngestionJobLedgerRecords.model_validate(raw)
        return validate_ingestion_job_ledger_records(records)

    def read(self, job_id: str) -> IngestionJobLedgerRecords | None:
        return self.get(job_id)


def classify_ingestion_scope(ticker: str) -> IngestionScopeBoundaryRow:
    normalized = normalize_ticker(ticker)
    cached = ASSETS.get(normalized)
    if cached:
        identity: AssetIdentity = cached["identity"]
        return IngestionScopeBoundaryRow(
            ticker=identity.ticker,
            asset_type=identity.asset_type.value,
            asset_name=identity.name,
            exchange=identity.exchange,
            issuer=identity.issuer,
            scope_decision=IngestionScopeDecision.cached_supported_asset.value,
            support_status="supported",
            approval_basis="cached_launch_knowledge_pack",
            top500_manifest_member=identity.asset_type.value == "stock",
            approved_for_on_demand_ingestion=False,
            generated_output_allowed=True,
        )

    eligible = ELIGIBLE_NOT_CACHED_ASSETS.get(normalized)
    if eligible:
        return IngestionScopeBoundaryRow(
            ticker=normalized,
            asset_type=str(eligible["asset_type"]),
            asset_name=str(eligible["name"]),
            exchange=str(eligible["exchange"]) if eligible.get("exchange") else None,
            issuer=str(eligible["issuer"]) if eligible.get("issuer") else None,
            scope_decision=IngestionScopeDecision.approved_pending_ingestion.value,
            support_status="pending_ingestion",
            approval_basis=_approval_basis(eligible),
            top500_manifest_member=eligible.get("asset_type") == "stock",
            approved_for_on_demand_ingestion=True,
            generated_output_allowed=False,
        )

    if normalized in UNSUPPORTED_ASSETS:
        return IngestionScopeBoundaryRow(
            ticker=normalized,
            asset_type="unsupported",
            asset_name=normalized,
            scope_decision=IngestionScopeDecision.blocked_unsupported_asset.value,
            support_status="unsupported",
            approval_basis="blocked_unsupported_or_complex_asset",
        )

    out_of_scope = OUT_OF_SCOPE_COMMON_STOCKS.get(normalized)
    if out_of_scope:
        return IngestionScopeBoundaryRow(
            ticker=normalized,
            asset_type=str(out_of_scope["asset_type"]),
            asset_name=str(out_of_scope["name"]),
            exchange=str(out_of_scope["exchange"]) if out_of_scope.get("exchange") else None,
            issuer=str(out_of_scope["issuer"]) if out_of_scope.get("issuer") else None,
            scope_decision=IngestionScopeDecision.blocked_out_of_scope_asset.value,
            support_status="out_of_scope",
            approval_basis="outside_top500_manifest_without_approved_on_demand_ingestion",
        )

    return IngestionScopeBoundaryRow(
        ticker=normalized,
        asset_type="unknown",
        asset_name=normalized,
        scope_decision=IngestionScopeDecision.unknown_or_unavailable_asset.value,
        support_status="unknown",
        approval_basis="not_recognized_by_deterministic_fixture_or_manifest",
    )


def serialize_ingestion_job_response(
    response: IngestionJobResponse | PreCacheJobResponse,
    *,
    category: IngestionJobCategory | str | None = None,
) -> IngestionJobLedgerRecords:
    scope = classify_ingestion_scope(response.ticker)
    job_id = response.job_id
    if not job_id:
        raise IngestionJobLedgerContractError("Only created ingestion jobs are persisted in the ledger.")

    job_category = _coerce_category(category, response)
    job_state = _ledger_state(response.job_state.value)
    compact_metadata = {
        "message": response.message,
        "asset_name": getattr(response, "name", None),
    }
    if hasattr(response, "deterministic"):
        compact_metadata["deterministic"] = getattr(response, "deterministic")

    ledger = IngestionJobLedgerRecordRow(
        job_id=job_id,
        job_category=job_category.value,
        ticker=response.ticker,
        asset_type=response.asset_type.value,
        job_state=job_state.value,
        worker_status=response.worker_status.value if response.worker_status else None,
        scope_decision=scope.scope_decision,
        support_status=scope.support_status,
        approval_basis=scope.approval_basis,
        retryable=response.retryable,
        generated_route=response.generated_route,
        generated_output_available=getattr(response, "generated_output_available", bool(response.generated_route)),
        can_open_generated_page=response.capabilities.can_open_generated_page,
        can_answer_chat=response.capabilities.can_answer_chat,
        can_compare=response.capabilities.can_compare,
        can_request_ingestion=response.capabilities.can_request_ingestion,
        status_url=response.status_url,
        created_at=response.created_at,
        updated_at=response.updated_at,
        started_at=response.started_at,
        finished_at=response.finished_at,
        batch_id=getattr(response, "batch_id", None),
        launch_group=getattr(response, "launch_group", None),
        compact_metadata={key: value for key, value in compact_metadata.items() if value is not None},
    )
    diagnostics = []
    if response.error_metadata:
        diagnostics.append(
            IngestionJobLedgerDiagnosticRow(
                job_id=job_id,
                diagnostic_id=f"{job_id}-diagnostic-1",
                category=SanitizedErrorCategory.validation_failed.value,
                error_code=response.error_metadata.code,
                sanitized_message=response.error_metadata.message,
                retryable=response.error_metadata.retryable,
                occurred_at=response.finished_at or response.updated_at,
            )
        )

    records = IngestionJobLedgerRecords(ledger=ledger, scope=scope, diagnostics=diagnostics)
    validate_ingestion_job_ledger_records(records)
    return records


def records_to_row_list(records: IngestionJobLedgerRecords) -> list[StrictRow]:
    validate_ingestion_job_ledger_records(records)
    return [records.ledger, *records.source_refs, *records.diagnostics]


def validate_ingestion_job_ledger_records(records: IngestionJobLedgerRecords) -> IngestionJobLedgerRecords:
    _validate_records(records)
    return records


def _approval_basis(metadata: dict[str, str | list[str] | None]) -> str:
    if metadata.get("manifest_id"):
        return "top500_manifest_approved_pending_ingestion"
    return "supported_non_leveraged_us_equity_etf_pending_ingestion"


def _coerce_category(
    category: IngestionJobCategory | str | None,
    response: IngestionJobResponse | PreCacheJobResponse,
) -> IngestionJobCategory:
    if category is not None:
        return IngestionJobCategory(category)
    job_type = response.job_type.value if response.job_type else None
    if job_type == "pre_cache":
        return IngestionJobCategory.manual_pre_cache
    if job_type == "on_demand":
        return IngestionJobCategory.approved_on_demand
    if job_type == "refresh":
        return IngestionJobCategory.refresh
    return IngestionJobCategory.source_revalidation


def _ledger_state(job_state: str) -> IngestionLedgerJobState:
    if job_state == "refresh_needed":
        return IngestionLedgerJobState.stale
    return IngestionLedgerJobState(job_state)


def _validate_records(records: IngestionJobLedgerRecords) -> None:
    ledger = records.ledger
    scope = records.scope
    if ledger.ticker != scope.ticker:
        raise IngestionJobLedgerContractError("Ledger ticker must match scope ticker.")
    if ledger.scope_decision != scope.scope_decision:
        raise IngestionJobLedgerContractError("Ledger scope decision must match the deterministic scope row.")
    if ledger.no_live_external_calls is not True:
        raise IngestionJobLedgerContractError("Ledger contract must remain dormant and deterministic.")
    if (
        ledger.raw_provider_payload_stored
        or ledger.raw_article_text_stored
        or ledger.raw_user_text_stored
        or ledger.unrestricted_source_text_stored
        or ledger.secrets_stored
    ):
        raise IngestionJobLedgerContractError("Ledger rows may store only compact sanitized metadata.")

    blocked_state = ledger.job_state in BLOCKED_GENERATED_OUTPUT_STATES
    blocked_scope = scope.scope_decision in {
        IngestionScopeDecision.blocked_unsupported_asset.value,
        IngestionScopeDecision.blocked_out_of_scope_asset.value,
        IngestionScopeDecision.unknown_or_unavailable_asset.value,
    }
    if blocked_state or blocked_scope:
        _assert_no_generated_output(ledger)

    if scope.scope_decision == IngestionScopeDecision.approved_pending_ingestion.value and ledger.job_state != "succeeded":
        _assert_no_generated_output(ledger)
    if scope.scope_decision == IngestionScopeDecision.unknown_or_unavailable_asset.value:
        _assert_no_generated_output(ledger)

    if ledger.job_category == IngestionJobCategory.approved_on_demand.value and not scope.approved_for_on_demand_ingestion:
        raise IngestionJobLedgerContractError("On-demand ledger jobs require explicit pending-ingestion approval.")

    for source in records.source_refs:
        if source.job_id != ledger.job_id:
            raise IngestionJobLedgerContractError("Source references must bind to the same job.")
        if source.stores_raw_text:
            raise IngestionJobLedgerContractError("Ledger source references must not store raw source text.")
        if source.source_use_policy == "rejected":
            raise IngestionJobLedgerContractError("Rejected sources cannot feed ingestion job ledger source refs.")

    for diagnostic in records.diagnostics:
        if diagnostic.job_id != ledger.job_id:
            raise IngestionJobLedgerContractError("Diagnostics must bind to the same job.")
        if (
            diagnostic.stores_secret
            or diagnostic.stores_user_text
            or diagnostic.stores_provider_payload
            or diagnostic.stores_raw_source_text
        ):
            raise IngestionJobLedgerContractError("Diagnostics must store sanitized categories only.")


def _assert_no_generated_output(ledger: IngestionJobLedgerRecordRow) -> None:
    if (
        ledger.generated_output_available
        or ledger.generated_route
        or ledger.can_open_generated_page
        or ledger.can_answer_chat
        or ledger.can_compare
    ):
        raise IngestionJobLedgerContractError(
            "Unsupported, out-of-scope, unknown, unavailable, stale pending, and unapproved jobs cannot expose generated output."
        )


def _persist_records(
    session: Any,
    *,
    collection: str,
    key: str,
    records: IngestionJobLedgerRecords,
    rows: list[StrictRow],
    commit_on_write: bool,
) -> None:
    if hasattr(session, "save_repository_record"):
        session.save_repository_record(collection, key, records.model_copy(deep=True))
    elif hasattr(session, "save"):
        session.save(collection, key, records.model_copy(deep=True))
    elif hasattr(session, "add_all"):
        session.add_all(rows)
    else:
        raise IngestionJobLedgerContractError(
            "Injected ledger session must expose save_repository_record(collection, key, records), save(...), or add_all(records)."
        )
    if commit_on_write and hasattr(session, "commit"):
        session.commit()


def _read_records(session: Any, collection: str, key: str) -> Any | None:
    if hasattr(session, "get_repository_record"):
        return session.get_repository_record(collection, key)
    if hasattr(session, "read_repository_record"):
        return session.read_repository_record(collection, key)
    if hasattr(session, "get"):
        return session.get(collection, key)
    return None
