"""Source of truth for the desktop wire contracts; export with scripts/contracts.py."""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal
from urllib.parse import parse_qsl
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


def public_reference_url(value: HttpUrl) -> HttpUrl:
    if value.username is not None or value.password is not None:
        raise ValueError("Source references cannot contain credentials")
    if any(key.casefold().replace("-", "_") in {"token", "access_token", "api_key", "apikey", "api_token", "access_key", "crumb", "password", "secret", "authorization", "signature"}
           for key, _ in parse_qsl(value.query or "")):
        raise ValueError("Source references cannot contain authentication parameters")
    return value


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1"] = "1"


class AssetIdentity(Contract):
    id: str = Field(min_length=1, max_length=200)
    symbol: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=300)
    asset_type: Literal["stock", "etf", "fund", "bond", "crypto", "option", "future", "index", "other", "unknown"]
    exchange: str | None = None
    currency: str | None = None
    identifiers: dict[str, str] = Field(default_factory=dict)


class SourcePolicy(str, Enum):
    full_text = "full_text_allowed"
    summary = "summary_allowed"
    metadata = "metadata_only"
    link = "link_only"
    rejected = "rejected"


class FilingPublication(Contract):
    authority: Literal["sec-submissions-v1"] = "sec-submissions-v1"
    cik: str = Field(pattern=r"^[0-9]{10}$")
    accession: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    form: str = Field(max_length=20)
    filed: date
    report_date: date | None = None
    document_url: HttpUrl
    index_url: HttpUrl
    index_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieved_at: AwareDatetime

    _public_urls = field_validator("document_url", "index_url")(public_reference_url)


class Source(Contract):
    id: str = Field(default_factory=uid)
    asset_id: str
    url: HttpUrl
    title: str = Field(min_length=1, max_length=1000)
    publisher: str = Field(min_length=1, max_length=300)
    retrieved_at: datetime = Field(default_factory=now)
    published_at: date | None = None
    as_of: date | None = None
    content_hash: str = ""
    policy: SourcePolicy = SourcePolicy.link
    official: bool = False
    verified: bool = False
    # This excerpt is set by an application-owned retriever, never trusted from a model.
    excerpt: str = Field(default="", max_length=20000)
    provenance: Literal["agent_candidate", "structured_adapter", "market_adapter", "verified_retrieval", "user_import"] = "agent_candidate"
    usage_scope: Literal["standard", "private_yahoo_v1"] = "standard"
    filing_publication: FilingPublication | None = None

    _public_url = field_validator("url")(public_reference_url)

    @model_validator(mode="after")
    def restrict_text(self):
        if self.policy in (SourcePolicy.link, SourcePolicy.metadata, SourcePolicy.rejected) and self.excerpt:
            raise ValueError("This source-use policy does not permit cached excerpts")
        if self.retrieved_at.tzinfo is None:
            raise ValueError("Retrieval timestamp must include a timezone")
        return self


class Claim(Contract):
    id: str = Field(default_factory=uid)
    asset_id: str
    section: str = Field(default="overview", max_length=100)
    text: str = Field(min_length=1, max_length=10000)
    kind: Literal["fact", "calculation", "interpretation", "unverified_note"] = "unverified_note"
    source_ids: list[str] = Field(default_factory=list)
    as_of: date | None = None
    value: float | None = Field(default=None, allow_inf_nan=False)
    unit: str | None = None
    # Calculations must reference admitted facts, not prose or other notes.
    input_claim_ids: list[str] = Field(default_factory=list)


class IdentityVerification(Contract):
    authority: str = Field(min_length=1, max_length=100)
    source_url: HttpUrl
    retrieved_at: AwareDatetime
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    _public_url = field_validator("source_url")(public_reference_url)


class FinancialObservation(Contract):
    id: str = Field(pattern=r"^[0-9a-f]{64}$")
    cik: str = Field(pattern=r"^[0-9]{10}$")
    concept: str = Field(max_length=100)
    # Exact source decimals stay strings across JSON/JavaScript and database round trips.
    value: str = Field(max_length=80, pattern=r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")
    unit: str = Field(max_length=20)
    start: date | None = None
    end: date
    period: Literal["annual", "quarter", "instant", "other_duration"]
    accession: str = Field(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
    filed: date
    form: Literal["10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "40-F/A"]
    reported_fiscal_year: int = Field(strict=True, ge=1900, le=9999)
    reported_fiscal_period: Literal["FY", "Q1", "Q2", "Q3", "Q4"]
    source_id: str = Field(max_length=200)
    revision: Literal["current", "superseded", "conflict"]
    supersedes: list[str] = Field(default_factory=list, max_length=128)


class FinancialEvidence(Contract):
    scope: Literal["issuer"] = "issuer"
    association: Literal["sec-common-stock-concordance-v1"] = "sec-common-stock-concordance-v1"
    issuer: AssetIdentity
    issuer_verification: IdentityVerification
    checked_at: AwareDatetime
    observations: list[FinancialObservation] = Field(default_factory=list, max_length=40000)
    gaps: list[str] = Field(default_factory=list, max_length=100)


class MarketBar(Contract):
    date: date
    open: str = Field(max_length=80)
    high: str = Field(max_length=80)
    low: str = Field(max_length=80)
    close: str = Field(max_length=80)
    adjusted_close: str = Field(max_length=80)
    volume: str = Field(max_length=80)


class MarketCorporateAction(Contract):
    date: date
    kind: Literal["dividends", "splits", "capitalGains"]
    value: str = Field(max_length=161)


class MarketEvidence(Contract):
    """Application-owned daily history; never an LLM output field."""
    provider: Literal["yahoo_yfinance"] = "yahoo_yfinance"
    association: Literal["yahoo-openfigi-common-stock-v1"] = "yahoo-openfigi-common-stock-v1"
    usage_scope: Literal["private_yahoo_v1"] = "private_yahoo_v1"
    source_id: str = Field(max_length=200)
    checked_at: AwareDatetime
    name: str = Field(min_length=1, max_length=300)
    exchange: str = Field(max_length=20)
    exchange_label: str = Field(max_length=100)
    currency: Literal["USD"] = "USD"
    instrument_type: Literal["EQUITY"] = "EQUITY"
    timezone: Literal["America/New_York"] = "America/New_York"
    requested_start: date
    requested_end: date
    close_basis: Literal["split_adjusted"] = "split_adjusted"
    adjusted_close_basis: Literal["splits_and_distributions"] = "splits_and_distributions"
    volume_basis: Literal["provider_reported"] = "provider_reported"
    bars: list[MarketBar] = Field(min_length=1, max_length=2000)
    actions: list[MarketCorporateAction] = Field(default_factory=list, max_length=2000)
    gaps: list[Literal["missing_price_rows", "calendar_completeness_unverified"]] = Field(max_length=2)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvidenceBundle(Contract):
    id: str = Field(default_factory=uid)
    asset: AssetIdentity
    created_at: datetime = Field(default_factory=now)
    sources: list[Source] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    notes: list[Claim] = Field(default_factory=list)
    state: Literal["partial", "available", "stale", "unavailable"] = "partial"
    completion: Literal["complete", "section_checkpoint"] = "complete"
    language: Literal["en", "zh-TW"] = "en"
    # Missing on older snapshots: keep readable, never infer independent verification.
    level: Literal["beginner", "intermediate"] | None = None
    identity_verification: IdentityVerification | None = None
    financials: FinancialEvidence | None = None
    market: MarketEvidence | None = None

    @model_validator(mode="after")
    def financial_references(self):
        from backend.app.market_evidence import validate_market
        validate_market(self)
        if self.financials is not None:
            # Delayed import keeps wire definitions independent of adapter initialization.
            from backend.app.financial_evidence import validate_financials
            validate_financials(self)
        if any(source.filing_publication is not None for source in self.sources):
            from backend.app.sec_filings import validate_publications
            validate_publications(self)
        if self.completion == "section_checkpoint":
            from backend.app.research_progress import validate_checkpoint
            validate_checkpoint(self)
        return self


class RuntimeCapabilities(Contract):
    provider: Literal["codex", "gemini", "claude"]
    installed: bool = False
    authentication: Literal["unknown", "authenticated", "required", "unsupported"] = "unknown"
    version: str | None = None
    qualification: Literal["unqualified", "protocol_only", "live"] = "unqualified"
    generation: bool = False
    browsing: bool = False
    streaming: bool = False
    cancellation: bool = False
    approvals: bool = False
    reason: str | None = None


class RuntimeEvent(Contract):
    sequence: int = 0
    run_id: str
    kind: Literal["run.started", "message.delta", "tool.started", "evidence.registered", "approval.required", "run.completed", "run.failed", "run.cancelled"]
    timestamp: datetime = Field(default_factory=now)
    text: str = ""
    data: dict = Field(default_factory=dict)


class RuntimeModel(Contract):
    id: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
    name: str = Field(min_length=1, max_length=200)
    is_default: bool = False


class ApprovalRequest(Contract):
    """Ephemeral app-owned access review. No vendor arguments or granting authority."""
    id: str = Field(default_factory=uid)
    run_id: str
    provider: Literal["codex", "gemini", "claude"]
    kind: Literal["command", "file_change", "permissions"]
    expires_at: AwareDatetime
    message: str = "This access is outside the research policy and cannot be approved. Deny it to let the provider continue with permitted tools, or cancel research."


class ApprovalDecision(Contract):
    decision: Literal["deny", "cancel"]


class RuntimeModelCatalog(Contract):
    provider: Literal["codex", "gemini", "claude"]
    status: Literal["available", "authentication_required", "unavailable"] = "unavailable"
    models: list[RuntimeModel] = Field(default_factory=list, max_length=200)
    message: str = "Model discovery is not qualified for this connection."


class ProviderLogin(Contract):
    """Ephemeral connection UI state. Never stored in the library or exports."""
    provider: Literal["codex"] = "codex"
    status: Literal["idle", "pending", "authenticated", "cancelled", "expired", "failed"] = "idle"
    verification_url: Literal["https://auth.openai.com/codex/device"] | None = None
    user_code: str | None = Field(default=None, max_length=32)
    expires_at: AwareDatetime | None = None
    message: str = "Sign in to the dedicated Codex connection."


class ResearchRequest(Contract):
    query: str = Field(min_length=1, max_length=1000)
    asset_id: str | None = None
    provider: Literal["codex", "gemini", "claude"] = "codex"
    model: str | None = Field(default=None, max_length=200)
    language: Literal["en", "zh-TW"] = "en"
    level: Literal["beginner", "intermediate"] = "beginner"
    refresh: bool = False
    conversation_id: str | None = None


class ResearchResult(Contract):
    """Provider output is a proposal; admission happens separately."""
    candidates: list[AssetIdentity] = Field(default_factory=list, max_length=20)
    sources: list[Source] = Field(default_factory=list, max_length=100)
    claims: list[Claim] = Field(default_factory=list, max_length=200)


class ResearchJobSummary(Contract):
    """Read-only recovery metadata; no raw events, provider output or credentials."""
    id: str = Field(min_length=1, max_length=36)
    status: Literal["queued", "running", "completed", "failed", "cancelled", "interrupted", "needs_identity"]
    request: ResearchRequest
    created_at: AwareDatetime


class TermRequest(Contract):
    purpose: Literal["term_explanation"] = "term_explanation"
    term: str = Field(min_length=1, max_length=120)
    bundle_id: str = Field(min_length=1, max_length=200)
    language: Literal["en", "zh-TW"] = "en"
    level: Literal["beginner", "intermediate"] = "beginner"
    provider: Literal["codex", "gemini", "claude"] = "codex"
    model: str | None = Field(default=None, max_length=200)

    @field_validator("term")
    @classmethod
    def concise_term(cls, value):
        import unicodedata
        value = " ".join(unicodedata.normalize("NFKC", value).split())
        if not value or any(unicodedata.category(char).startswith("C") for char in value) or len(value.split()) > 16:
            raise ValueError("Select a concise term of up to 16 words")
        return value


class TermResult(Contract):
    explanation: str = Field(min_length=1, max_length=1600)
    basis: Literal["general", "snapshot"]
    source_ids: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("explanation")
    @classmethod
    def readable_text(cls, value):
        if not value.strip():
            raise ValueError("Explanation cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def citation_basis(self):
        if self.basis == "snapshot" and not self.source_ids:
            raise ValueError("Snapshot explanations require citations")
        if self.basis == "general" and self.source_ids:
            raise ValueError("General explanations cannot claim snapshot support")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("Duplicate citations")
        return self


class TermExplanation(TermResult):
    id: str = Field(pattern=r"^[0-9a-f]{64}$")
    term: str = Field(min_length=1, max_length=120)
    bundle_id: str = Field(min_length=1, max_length=200)
    asset_id: str = Field(min_length=1, max_length=200)
    language: Literal["en", "zh-TW"]
    level: Literal["beginner", "intermediate"]
    provider: Literal["codex", "gemini", "claude"]
    model: str | None = None
    created_at: AwareDatetime = Field(default_factory=now)
    interpretation: Literal[True] = True


class Settings(Contract):
    cloud_enabled: bool = False
    experimental_yahoo_enabled: bool = Field(default=False, strict=True)
    provider: Literal["codex", "gemini", "claude"] = "codex"
    model: str | None = Field(default=None, min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
    language: Literal["en", "zh-TW"] = "en"
    manual_source_review: bool = False
    update_mode: Literal["notify", "manual", "automatic"] = "notify"
    start_at_login: bool = False
    retention_days: int = Field(default=180, ge=7, le=3650)
    cache_gb: int = Field(default=10, ge=1, le=1000)


class ConversationMessage(Contract):
    role: Literal["user", "assistant", "scope"]
    text: str | None = Field(default=None, max_length=10000)
    asset_id: str | None = Field(default=None, max_length=200)
    bundle_id: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def cited_answer(self):
        if self.role == "assistant" and not self.bundle_id:
            raise ValueError("Assistant answers must reference a cited snapshot")
        if self.role != "assistant" and (not self.text or self.bundle_id):
            raise ValueError("User/scope messages require text and cannot attest a research snapshot")
        return self


class Conversation(Contract):
    id: str = Field(default_factory=uid, max_length=200)
    asset_id: str = Field(max_length=200)
    messages: list[ConversationMessage] = Field(default_factory=list)
    bookmarked: bool = False
    created_at: AwareDatetime = Field(default_factory=now)
    last_activity: AwareDatetime | None = None


class SavedResearch(Contract):
    id: str = Field(default_factory=uid, max_length=200)
    bundle_id: str = Field(max_length=200)
    title: str = Field(min_length=1, max_length=200)
    created_at: AwareDatetime = Field(default_factory=now)


class BackupSummary(Contract):
    format_version: Literal["1", "2"] = "1"
    database_revision: Literal["0001"] = "0001"
    created_at: AwareDatetime
    fingerprint: str
    assets: int
    evidence_versions: int
    conversations: int
    saved_reports: int
    term_explanations: int = 0
    retained_imports: int = 0
    import_explanations: int = 0
    attachment_bytes: int = 0
    jobs: int
    credentials_included: Literal[False] = False
    can_restore: bool
    reason: str | None = None
