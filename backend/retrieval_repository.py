from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from backend.models import KnowledgePackBuildResponse
from backend.repositories.knowledge_packs import (
    AssetKnowledgePackRepository,
    KnowledgePackRepositoryContractError,
    KnowledgePackRepositoryRecords,
)


RETRIEVAL_REPOSITORY_BOUNDARY = "retrieval-knowledge-pack-read-boundary-v1"


class KnowledgePackRecordReader(Protocol):
    def read_knowledge_pack_records(self, ticker: str) -> KnowledgePackRepositoryRecords | None:
        ...


@dataclass(frozen=True)
class RetrievalRepositoryReadResult:
    status: str
    ticker: str
    response: KnowledgePackBuildResponse | None = None
    records: KnowledgePackRepositoryRecords | None = None
    message: str = ""

    @property
    def found(self) -> bool:
        return self.status == "found" and self.response is not None


def read_persisted_knowledge_pack_response(
    ticker: str,
    *,
    reader: KnowledgePackRecordReader | Any | None = None,
    repository: AssetKnowledgePackRepository | None = None,
) -> RetrievalRepositoryReadResult:
    normalized = ticker.strip().upper()
    if reader is None:
        return RetrievalRepositoryReadResult(
            status="not_configured",
            ticker=normalized,
            message="No persisted knowledge-pack reader is configured; deterministic fixtures remain authoritative.",
        )

    try:
        records = _read_records(reader, normalized)
    except KnowledgePackRepositoryContractError as exc:
        return RetrievalRepositoryReadResult(
            status="contract_error",
            ticker=normalized,
            message=str(exc),
        )
    except Exception as exc:  # pragma: no cover - message is asserted through public status.
        return RetrievalRepositoryReadResult(
            status="reader_error",
            ticker=normalized,
            message=f"Injected persisted knowledge-pack reader failed: {exc.__class__.__name__}.",
        )

    if records is None:
        return RetrievalRepositoryReadResult(
            status="miss",
            ticker=normalized,
            message="No persisted knowledge-pack record exists for this ticker.",
        )

    try:
        response = (repository or AssetKnowledgePackRepository()).deserialize(records)
    except KnowledgePackRepositoryContractError as exc:
        return RetrievalRepositoryReadResult(
            status="contract_error",
            ticker=normalized,
            records=records,
            message=str(exc),
        )

    if response.ticker != normalized:
        return RetrievalRepositoryReadResult(
            status="contract_error",
            ticker=normalized,
            records=records,
            message=f"Persisted knowledge-pack response belongs to {response.ticker}, not requested ticker {normalized}.",
        )

    return RetrievalRepositoryReadResult(
        status="found",
        ticker=normalized,
        response=response,
        records=records,
        message="Persisted knowledge-pack metadata record was found and validated.",
    )


def _read_records(reader: KnowledgePackRecordReader | Any, ticker: str) -> KnowledgePackRepositoryRecords | None:
    if isinstance(reader, dict):
        return reader.get(ticker)
    if hasattr(reader, "read_knowledge_pack_records"):
        return reader.read_knowledge_pack_records(ticker)
    if hasattr(reader, "read"):
        return reader.read(ticker)
    if hasattr(reader, "get"):
        return reader.get(ticker)
    raise KnowledgePackRepositoryContractError(
        "Injected persisted knowledge-pack reader must expose read_knowledge_pack_records(ticker), read(ticker), or get(ticker)."
    )
