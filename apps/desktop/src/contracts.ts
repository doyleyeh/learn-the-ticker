/* Generated from backend/app/contracts.py. Do not edit. */

export type SchemaVersion = "1";
export type Decision = "deny" | "cancel";
export type SchemaVersion1 = "1";
export type Id = string;
export type RunId = string;
export type Provider = "codex" | "gemini" | "claude";
export type Kind = "command" | "file_change" | "permissions";
export type ExpiresAt = string;
export type Message = string;
export type SchemaVersion2 = "1";
export type Id1 = string;
export type Symbol = string;
export type Name = string;
export type AssetType =
  "stock" | "etf" | "fund" | "bond" | "crypto" | "option" | "future" | "index" | "other" | "unknown";
export type Exchange = string | null;
export type Currency = string | null;
export type SchemaVersion3 = "1";
export type FormatVersion = "1" | "2";
export type DatabaseRevision = "0001";
export type CreatedAt = string;
export type Fingerprint = string;
export type Assets = number;
export type EvidenceVersions = number;
export type Conversations = number;
export type SavedReports = number;
export type TermExplanations = number;
export type RetainedImports = number;
export type ImportExplanations = number;
export type AttachmentBytes = number;
export type Jobs = number;
export type CredentialsIncluded = false;
export type CanRestore = boolean;
export type Reason = string | null;
export type SchemaVersion4 = "1";
export type Id2 = string;
export type AssetId = string;
export type Section = string;
export type Text = string;
export type Kind1 = "fact" | "calculation" | "interpretation" | "unverified_note";
export type SourceIds = string[];
export type AsOf = string | null;
export type Value = number | null;
export type Unit = string | null;
export type InputClaimIds = string[];
export type SchemaVersion5 = "1";
export type Id3 = string;
export type AssetId1 = string;
export type SchemaVersion6 = "1";
export type Role = "user" | "assistant" | "scope";
export type Text1 = string | null;
export type AssetId2 = string | null;
export type BundleId = string | null;
export type Messages = ConversationMessage[];
export type Bookmarked = boolean;
export type CreatedAt1 = string;
export type LastActivity = string | null;
export type SchemaVersion7 = "1";
export type Id4 = string;
export type CreatedAt2 = string;
export type SchemaVersion8 = "1";
export type Id5 = string;
export type AssetId3 = string;
export type Url = string;
export type Title = string;
export type Publisher = string;
export type RetrievedAt = string;
export type PublishedAt = string | null;
export type AsOf1 = string | null;
export type ContentHash = string;
export type SourcePolicy = "full_text_allowed" | "summary_allowed" | "metadata_only" | "link_only" | "rejected";
export type Official = boolean;
export type Verified = boolean;
export type Excerpt = string;
export type Provenance =
  "agent_candidate" | "structured_adapter" | "market_adapter" | "verified_retrieval" | "user_import";
export type UsageScope = "standard" | "private_yahoo_v1";
export type SchemaVersion9 = "1";
export type Authority = "sec-submissions-v1";
export type Cik = string;
export type Accession = string;
export type Form = string;
export type Filed = string;
export type ReportDate = string | null;
export type DocumentUrl = string;
export type IndexUrl = string;
export type IndexHash = string;
export type RetrievedAt1 = string;
export type Sources = Source[];
export type Claims = Claim[];
export type Notes = Claim[];
export type State = "partial" | "available" | "stale" | "unavailable";
export type Completion = "complete" | "section_checkpoint";
export type Language = "en" | "zh-TW";
export type Level = ("beginner" | "intermediate") | null;
export type SchemaVersion10 = "1";
export type Authority1 = string;
export type SourceUrl = string;
export type RetrievedAt2 = string;
export type ContentHash1 = string;
export type IdentityHash = string;
export type SchemaVersion11 = "1";
export type Scope = "issuer";
export type Association = "sec-common-stock-concordance-v1";
export type CheckedAt = string;
export type SchemaVersion12 = "1";
export type Id6 = string;
export type Cik1 = string;
export type Concept = string;
export type Value1 = string;
export type Unit1 = string;
export type Start = string | null;
export type End = string;
export type Period = "annual" | "quarter" | "instant" | "other_duration";
export type Accession1 = string;
export type Filed1 = string;
export type Form1 = "10-K" | "10-K/A" | "10-Q" | "10-Q/A" | "20-F" | "20-F/A" | "40-F" | "40-F/A";
export type ReportedFiscalYear = number;
export type ReportedFiscalPeriod = "FY" | "Q1" | "Q2" | "Q3" | "Q4";
export type SourceId = string;
export type Revision = "current" | "superseded" | "conflict";
/**
 * @maxItems 128
 */
export type Supersedes = string[];
/**
 * @maxItems 40000
 */
export type Observations = FinancialObservation[];
/**
 * @maxItems 100
 */
export type Gaps = string[];
export type RatioMethod = "sec-net-income-revenue-v1" | null;
export type SchemaVersion13 = "1";
export type DenominatorConcept = "us-gaap:Revenues" | "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax";
export type Start1 = string;
export type End1 = string;
export type Period1 = "annual" | "quarter";
/**
 * @maxItems 40000
 */
export type InputIds = string[];
/**
 * @maxItems 2
 */
export type SourceIds1 = [] | [string] | [string, string];
export type Percent = string | null;
export type Reason1 =
  | (
      | "missing_income"
      | "conflicting_inputs"
      | "ambiguous_inputs"
      | "different_units"
      | "different_filings"
      | "nonpositive_revenue"
    )
  | null;
/**
 * @maxItems 34
 */
export type Ratios = FinancialRatio[];
export type SchemaVersion14 = "1";
export type Provider1 = "yahoo_yfinance";
export type Association1 = "yahoo-openfigi-common-stock-v1";
export type UsageScope1 = "private_yahoo_v1";
export type SourceId1 = string;
export type CheckedAt1 = string;
export type Name1 = string;
export type Exchange1 = string;
export type ExchangeLabel = string;
export type Currency1 = "USD";
export type InstrumentType = "EQUITY";
export type Timezone = "America/New_York";
export type RequestedStart = string;
export type RequestedEnd = string;
export type CloseBasis = "split_adjusted";
export type AdjustedCloseBasis = "splits_and_distributions";
export type VolumeBasis = "provider_reported";
/**
 * @minItems 1
 * @maxItems 2000
 */
export type Bars = [MarketBar, ...MarketBar[]];
export type SchemaVersion15 = "1";
export type Date = string;
export type Open = string;
export type High = string;
export type Low = string;
export type Close = string;
export type AdjustedClose = string;
export type Volume = string;
export type SchemaVersion16 = "1";
export type Date1 = string;
export type Kind2 = "dividends" | "splits" | "capitalGains";
export type Value2 = string;
/**
 * @maxItems 2000
 */
export type Actions = MarketCorporateAction[];
/**
 * @maxItems 2
 */
export type Gaps1 =
  | []
  | ["missing_price_rows" | "calendar_completeness_unverified"]
  | [
      "missing_price_rows" | "calendar_completeness_unverified",
      "missing_price_rows" | "calendar_completeness_unverified"
    ];
export type ReturnMethod = "yahoo-adjusted-ratio-v1" | null;
/**
 * @maxItems 5
 */
export type Returns =
  | []
  | [MarketReturn]
  | [MarketReturn, MarketReturn]
  | [MarketReturn, MarketReturn, MarketReturn]
  | [MarketReturn, MarketReturn, MarketReturn, MarketReturn]
  | [MarketReturn, MarketReturn, MarketReturn, MarketReturn, MarketReturn];
export type SchemaVersion17 = "1";
export type Period2 = "ytd" | "1y" | "3y" | "5y" | "retained";
export type SourceId2 = string;
export type RequestedStart1 = string;
export type Start2 = string | null;
export type End2 = string;
export type PricePercent = string | null;
export type TotalReturnEstimatePercent = string | null;
export type Reason2 =
  ("start_boundary_missing" | "insufficient_observations" | "missing_price_rows" | "history_gap") | null;
export type Fingerprint1 = string;
export type SchemaVersion18 = "1";
export type State1 = "unverified" | "link_only";
export type Origin = "local_file" | "public_url";
export type CheckedAt2 = string;
export type Format = "csv" | "xlsx" | "pdf" | "html";
export type ContentHash2 = string;
export type Verified1 = false;
export type Locator = string;
export type Text2 = string;
export type Locator1 = string;
export type Text3 = string;
export type Kind3 = "text" | "number" | "date" | "boolean" | "error" | "formula";
export type NumberFormat = string | null;
export type RawValue = string | null;
/**
 * @maxItems 100
 */
export type Cells = ImportCell[];
/**
 * @maxItems 2000
 */
export type Blocks = ImportBlock[];
export type Limitations = (
  | "unverified_import"
  | "formulas_not_evaluated"
  | "pdf_layout_not_verified"
  | "empty_pages"
  | "merged_cells_not_expanded"
)[];
export type Saved = false;
export type SchemaVersion19 = "1";
export type Id7 = string;
export type Title1 = string;
export type Format1 = "csv" | "xlsx" | "pdf" | "html";
export type Origin1 = "local_file" | "public_url";
export type CheckedAt3 = string;
export type RetainedAt = string;
export type ByteCount = number;
export type ContentHash3 = string;
export type Verified2 = false;
export type SchemaVersion20 = "1";
export type SchemaVersion21 = "1";
export type DocumentId = string;
export type ContentHash4 = string;
export type Language1 = "en" | "zh-TW";
export type Level1 = "beginner" | "intermediate";
export type Explanation = string;
/**
 * @minItems 1
 * @maxItems 8
 */
export type References =
  | [ImportReference]
  | [ImportReference, ImportReference]
  | [ImportReference, ImportReference, ImportReference]
  | [ImportReference, ImportReference, ImportReference, ImportReference]
  | [ImportReference, ImportReference, ImportReference, ImportReference, ImportReference]
  | [ImportReference, ImportReference, ImportReference, ImportReference, ImportReference, ImportReference]
  | [
      ImportReference,
      ImportReference,
      ImportReference,
      ImportReference,
      ImportReference,
      ImportReference,
      ImportReference
    ]
  | [
      ImportReference,
      ImportReference,
      ImportReference,
      ImportReference,
      ImportReference,
      ImportReference,
      ImportReference,
      ImportReference
    ];
export type SchemaVersion22 = "1";
export type Locator2 = string;
export type Quote = string;
export type Id8 = string;
export type Provider2 = "codex" | "gemini" | "claude";
export type Model = string | null;
export type CreatedAt3 = string;
export type Interpretation = true;
export type Verified3 = false;
export type SchemaVersion23 = "1";
export type DocumentId1 = string;
export type ContentHash5 = string;
export type Language2 = "en" | "zh-TW";
export type Level2 = "beginner" | "intermediate";
export type Purpose = "import_explanation";
export type Provider3 = "codex" | "gemini" | "claude";
export type Model1 = string | null;
export type TransmissionConfirmed = true;
export type SchemaVersion24 = "1";
export type DocumentId2 = string;
export type ContentHash6 = string;
export type Language3 = "en" | "zh-TW";
export type Level3 = "beginner" | "intermediate";
export type SchemaVersion25 = "1";
export type Provider4 = "codex";
export type Status = "idle" | "pending" | "authenticated" | "cancelled" | "expired" | "failed";
export type VerificationUrl = "https://auth.openai.com/codex/device" | null;
export type UserCode = string | null;
export type ExpiresAt1 = string | null;
export type Message1 = string;
export type SchemaVersion26 = "1";
export type Id9 = string;
export type Status1 = "queued" | "running" | "completed" | "failed" | "cancelled" | "interrupted" | "needs_identity";
export type SchemaVersion27 = "1";
export type Query = string;
export type AssetId4 = string | null;
export type Provider5 = "codex" | "gemini" | "claude";
export type Model2 = string | null;
export type Language4 = "en" | "zh-TW";
export type Level4 = "beginner" | "intermediate";
export type Refresh = boolean;
export type ConversationId = string | null;
export type CreatedAt4 = string;
export type SchemaVersion28 = "1";
/**
 * @maxItems 20
 */
export type Candidates =
  | []
  | [AssetIdentity]
  | [AssetIdentity, AssetIdentity]
  | [AssetIdentity, AssetIdentity, AssetIdentity]
  | [AssetIdentity, AssetIdentity, AssetIdentity, AssetIdentity]
  | [AssetIdentity, AssetIdentity, AssetIdentity, AssetIdentity, AssetIdentity]
  | [AssetIdentity, AssetIdentity, AssetIdentity, AssetIdentity, AssetIdentity, AssetIdentity]
  | [AssetIdentity, AssetIdentity, AssetIdentity, AssetIdentity, AssetIdentity, AssetIdentity, AssetIdentity]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ]
  | [
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity,
      AssetIdentity
    ];
/**
 * @maxItems 100
 */
export type Sources1 = Source[];
/**
 * @maxItems 200
 */
export type Claims1 = Claim[];
export type SchemaVersion29 = "1";
export type Provider6 = "codex" | "gemini" | "claude";
export type Installed = boolean;
export type Authentication = "unknown" | "authenticated" | "required" | "unsupported";
export type Version = string | null;
export type Qualification = "unqualified" | "protocol_only" | "live";
export type Generation = boolean;
export type Browsing = boolean;
export type Streaming = boolean;
export type Cancellation = boolean;
export type Approvals = boolean;
export type Reason3 = string | null;
export type SchemaVersion30 = "1";
export type Sequence = number;
export type RunId1 = string;
export type Kind4 =
  | "run.started"
  | "message.delta"
  | "tool.started"
  | "evidence.registered"
  | "approval.required"
  | "run.completed"
  | "run.failed"
  | "run.cancelled";
export type Timestamp = string;
export type Text4 = string;
export type SchemaVersion31 = "1";
export type Id10 = string;
export type Name2 = string;
export type IsDefault = boolean;
export type SchemaVersion32 = "1";
export type Provider7 = "codex" | "gemini" | "claude";
export type Status2 = "available" | "authentication_required" | "unavailable";
/**
 * @maxItems 200
 */
export type Models = RuntimeModel[];
export type Message2 = string;
export type SchemaVersion33 = "1";
export type Id11 = string;
export type BundleId1 = string;
export type Title2 = string;
export type CreatedAt5 = string;
export type SchemaVersion34 = "1";
export type CloudEnabled = boolean;
export type ExperimentalYahooEnabled = boolean;
export type Provider8 = "codex" | "gemini" | "claude";
export type Model3 = string | null;
export type Language5 = "en" | "zh-TW";
export type ManualSourceReview = boolean;
export type UpdateMode = "notify" | "manual" | "automatic";
export type StartAtLogin = boolean;
export type RetentionDays = number;
export type CacheGb = number;
export type SchemaVersion35 = "1";
export type Explanation1 = string;
export type Basis = "general" | "snapshot";
/**
 * @maxItems 20
 */
export type SourceIds2 =
  | []
  | [string]
  | [string, string]
  | [string, string, string]
  | [string, string, string, string]
  | [string, string, string, string, string]
  | [string, string, string, string, string, string]
  | [string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string, string, string, string]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ];
export type Id12 = string;
export type Term = string;
export type BundleId2 = string;
export type AssetId5 = string;
export type Language6 = "en" | "zh-TW";
export type Level5 = "beginner" | "intermediate";
export type Provider9 = "codex" | "gemini" | "claude";
export type Model4 = string | null;
export type CreatedAt6 = string;
export type Interpretation1 = true;
export type SchemaVersion36 = "1";
export type Purpose1 = "term_explanation";
export type Term1 = string;
export type BundleId3 = string;
export type Language7 = "en" | "zh-TW";
export type Level6 = "beginner" | "intermediate";
export type Provider10 = "codex" | "gemini" | "claude";
export type Model5 = string | null;
export type SchemaVersion37 = "1";
export type Explanation2 = string;
export type Basis1 = "general" | "snapshot";
/**
 * @maxItems 20
 */
export type SourceIds3 =
  | []
  | [string]
  | [string, string]
  | [string, string, string]
  | [string, string, string, string]
  | [string, string, string, string, string]
  | [string, string, string, string, string, string]
  | [string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string, string, string]
  | [string, string, string, string, string, string, string, string, string, string, string, string, string, string]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ]
  | [
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string,
      string
    ];
export type SchemaVersion38 = "1";
export type Cancel = boolean;
/**
 * @maxItems 100
 */
export type SourceIds4 = string[];
export type SchemaVersion39 = "1";
export type Id13 = string;
export type RunId2 = string;
export type AssetId6 = string;
/**
 * @minItems 1
 * @maxItems 100
 */
export type Sources2 = [ReviewSource, ...ReviewSource[]];
export type SchemaVersion40 = "1";
export type Id14 = string;
export type Url1 = string;
export type Publisher1 = string;
export type SourcePolicy1 = "full_text_allowed" | "summary_allowed" | "metadata_only" | "link_only" | "rejected";
export type RightsUrl = string;
export type ReviewedAt = string;
export type LocalNumericOnly = boolean;
export type ExpiresAt2 = string;

export interface DesktopContracts {
  ApprovalDecision?: ApprovalDecision;
  ApprovalRequest?: ApprovalRequest;
  AssetIdentity?: AssetIdentity;
  BackupSummary?: BackupSummary;
  Claim?: Claim;
  Conversation?: Conversation;
  EvidenceBundle?: EvidenceBundle;
  ImportPreview?: ImportPreview;
  RetainedImportSummary?: RetainedImportSummary;
  RetainedImportView?: RetainedImportView;
  ImportExplanation?: ImportExplanation;
  ImportLearningRequest?: ImportLearningRequest;
  ImportLearningScope?: ImportLearningScope;
  ProviderLogin?: ProviderLogin;
  ResearchJobSummary?: ResearchJobSummary;
  ResearchRequest?: ResearchRequest;
  ResearchResult?: ResearchResult;
  RuntimeCapabilities?: RuntimeCapabilities;
  RuntimeEvent?: RuntimeEvent;
  RuntimeModel?: RuntimeModel;
  RuntimeModelCatalog?: RuntimeModelCatalog;
  SavedResearch?: SavedResearch;
  Settings?: Settings;
  Source?: Source;
  TermExplanation?: TermExplanation;
  TermRequest?: TermRequest;
  TermResult?: TermResult;
  SourceReviewDecision?: SourceReviewDecision;
  SourceReviewRequest?: SourceReviewRequest;
}
export interface ApprovalDecision {
  schema_version?: SchemaVersion;
  decision: Decision;
}
/**
 * Ephemeral app-owned access review. No vendor arguments or granting authority.
 */
export interface ApprovalRequest {
  schema_version?: SchemaVersion1;
  id?: Id;
  run_id: RunId;
  provider: Provider;
  kind: Kind;
  expires_at: ExpiresAt;
  message?: Message;
}
export interface AssetIdentity {
  schema_version?: SchemaVersion2;
  id: Id1;
  symbol: Symbol;
  name: Name;
  asset_type: AssetType;
  exchange?: Exchange;
  currency?: Currency;
  identifiers?: Identifiers;
}
export interface Identifiers {
  [k: string]: string;
}
export interface BackupSummary {
  schema_version?: SchemaVersion3;
  format_version?: FormatVersion;
  database_revision?: DatabaseRevision;
  created_at: CreatedAt;
  fingerprint: Fingerprint;
  assets: Assets;
  evidence_versions: EvidenceVersions;
  conversations: Conversations;
  saved_reports: SavedReports;
  term_explanations?: TermExplanations;
  retained_imports?: RetainedImports;
  import_explanations?: ImportExplanations;
  attachment_bytes?: AttachmentBytes;
  jobs: Jobs;
  credentials_included?: CredentialsIncluded;
  can_restore: CanRestore;
  reason?: Reason;
}
export interface Claim {
  schema_version?: SchemaVersion4;
  id?: Id2;
  asset_id: AssetId;
  section?: Section;
  text: Text;
  kind?: Kind1;
  source_ids?: SourceIds;
  as_of?: AsOf;
  value?: Value;
  unit?: Unit;
  input_claim_ids?: InputClaimIds;
}
export interface Conversation {
  schema_version?: SchemaVersion5;
  id?: Id3;
  asset_id: AssetId1;
  messages?: Messages;
  bookmarked?: Bookmarked;
  created_at?: CreatedAt1;
  last_activity?: LastActivity;
}
export interface ConversationMessage {
  schema_version?: SchemaVersion6;
  role: Role;
  text?: Text1;
  asset_id?: AssetId2;
  bundle_id?: BundleId;
}
export interface EvidenceBundle {
  schema_version?: SchemaVersion7;
  id?: Id4;
  asset: AssetIdentity;
  created_at?: CreatedAt2;
  sources?: Sources;
  claims?: Claims;
  notes?: Notes;
  state?: State;
  completion?: Completion;
  language?: Language;
  level?: Level;
  identity_verification?: IdentityVerification | null;
  financials?: FinancialEvidence | null;
  market?: MarketEvidence | null;
}
export interface Source {
  schema_version?: SchemaVersion8;
  id?: Id5;
  asset_id: AssetId3;
  url: Url;
  title: Title;
  publisher: Publisher;
  retrieved_at?: RetrievedAt;
  published_at?: PublishedAt;
  as_of?: AsOf1;
  content_hash?: ContentHash;
  policy?: SourcePolicy;
  official?: Official;
  verified?: Verified;
  excerpt?: Excerpt;
  provenance?: Provenance;
  usage_scope?: UsageScope;
  filing_publication?: FilingPublication | null;
}
export interface FilingPublication {
  schema_version?: SchemaVersion9;
  authority?: Authority;
  cik: Cik;
  accession: Accession;
  form: Form;
  filed: Filed;
  report_date?: ReportDate;
  document_url: DocumentUrl;
  index_url: IndexUrl;
  index_hash: IndexHash;
  retrieved_at: RetrievedAt1;
}
export interface IdentityVerification {
  schema_version?: SchemaVersion10;
  authority: Authority1;
  source_url: SourceUrl;
  retrieved_at: RetrievedAt2;
  content_hash: ContentHash1;
  identity_hash: IdentityHash;
}
export interface FinancialEvidence {
  schema_version?: SchemaVersion11;
  scope?: Scope;
  association?: Association;
  issuer: AssetIdentity;
  issuer_verification: IdentityVerification;
  checked_at: CheckedAt;
  observations?: Observations;
  gaps?: Gaps;
  ratio_method?: RatioMethod;
  ratios?: Ratios;
}
export interface FinancialObservation {
  schema_version?: SchemaVersion12;
  id: Id6;
  cik: Cik1;
  concept: Concept;
  value: Value1;
  unit: Unit1;
  start?: Start;
  end: End;
  period: Period;
  accession: Accession1;
  filed: Filed1;
  form: Form1;
  reported_fiscal_year: ReportedFiscalYear;
  reported_fiscal_period: ReportedFiscalPeriod;
  source_id: SourceId;
  revision: Revision;
  supersedes?: Supersedes;
}
/**
 * Retained application calculation, separate from reported observations.
 */
export interface FinancialRatio {
  schema_version?: SchemaVersion13;
  denominator_concept: DenominatorConcept;
  start: Start1;
  end: End1;
  period: Period1;
  input_ids: InputIds;
  source_ids: SourceIds1;
  percent?: Percent;
  reason?: Reason1;
}
/**
 * Application-owned daily history; never an LLM output field.
 */
export interface MarketEvidence {
  schema_version?: SchemaVersion14;
  provider?: Provider1;
  association?: Association1;
  usage_scope?: UsageScope1;
  source_id: SourceId1;
  checked_at: CheckedAt1;
  name: Name1;
  exchange: Exchange1;
  exchange_label: ExchangeLabel;
  currency?: Currency1;
  instrument_type?: InstrumentType;
  timezone?: Timezone;
  requested_start: RequestedStart;
  requested_end: RequestedEnd;
  close_basis?: CloseBasis;
  adjusted_close_basis?: AdjustedCloseBasis;
  volume_basis?: VolumeBasis;
  bars: Bars;
  actions?: Actions;
  gaps: Gaps1;
  return_method?: ReturnMethod;
  returns?: Returns;
  fingerprint: Fingerprint1;
}
export interface MarketBar {
  schema_version?: SchemaVersion15;
  date: Date;
  open: Open;
  high: High;
  low: Low;
  close: Close;
  adjusted_close: AdjustedClose;
  volume: Volume;
}
export interface MarketCorporateAction {
  schema_version?: SchemaVersion16;
  date: Date1;
  kind: Kind2;
  value: Value2;
}
export interface MarketReturn {
  schema_version?: SchemaVersion17;
  period: Period2;
  source_id: SourceId2;
  requested_start: RequestedStart1;
  start?: Start2;
  end: End2;
  price_percent?: PricePercent;
  total_return_estimate_percent?: TotalReturnEstimatePercent;
  reason?: Reason2;
}
export interface ImportPreview {
  schema_version?: SchemaVersion18;
  state: State1;
  origin: Origin;
  source?: Source | null;
  checked_at: CheckedAt2;
  document?: ParsedDocument | null;
  saved?: Saved;
}
export interface ParsedDocument {
  format: Format;
  content_hash: ContentHash2;
  verified?: Verified1;
  blocks: Blocks;
  limitations: Limitations;
}
export interface ImportBlock {
  locator: Locator;
  text?: Text2;
  cells?: Cells;
}
export interface ImportCell {
  locator: Locator1;
  text: Text3;
  kind?: Kind3;
  number_format?: NumberFormat;
  raw_value?: RawValue;
}
export interface RetainedImportSummary {
  schema_version?: SchemaVersion19;
  id: Id7;
  title: Title1;
  format: Format1;
  origin: Origin1;
  source: Source | null;
  checked_at: CheckedAt3;
  retained_at: RetainedAt;
  byte_count: ByteCount;
  content_hash: ContentHash3;
  verified?: Verified2;
}
export interface RetainedImportView {
  schema_version?: SchemaVersion20;
  item: RetainedImportSummary;
  document: ParsedDocument;
}
export interface ImportExplanation {
  schema_version?: SchemaVersion21;
  document_id: DocumentId;
  content_hash: ContentHash4;
  language?: Language1;
  level?: Level1;
  explanation: Explanation;
  references: References;
  id: Id8;
  provider: Provider2;
  model?: Model;
  created_at?: CreatedAt3;
  interpretation?: Interpretation;
  verified?: Verified3;
}
export interface ImportReference {
  schema_version?: SchemaVersion22;
  locator: Locator2;
  quote: Quote;
}
export interface ImportLearningRequest {
  schema_version?: SchemaVersion23;
  document_id: DocumentId1;
  content_hash: ContentHash5;
  language?: Language2;
  level?: Level2;
  purpose?: Purpose;
  provider?: Provider3;
  model?: Model1;
  transmission_confirmed: TransmissionConfirmed;
}
export interface ImportLearningScope {
  schema_version?: SchemaVersion24;
  document_id: DocumentId2;
  content_hash: ContentHash6;
  language?: Language3;
  level?: Level3;
}
/**
 * Ephemeral connection UI state. Never stored in the library or exports.
 */
export interface ProviderLogin {
  schema_version?: SchemaVersion25;
  provider?: Provider4;
  status?: Status;
  verification_url?: VerificationUrl;
  user_code?: UserCode;
  expires_at?: ExpiresAt1;
  message?: Message1;
}
/**
 * Read-only recovery metadata; no raw events, provider output or credentials.
 */
export interface ResearchJobSummary {
  schema_version?: SchemaVersion26;
  id: Id9;
  status: Status1;
  request: ResearchRequest;
  created_at: CreatedAt4;
}
export interface ResearchRequest {
  schema_version?: SchemaVersion27;
  query: Query;
  asset_id?: AssetId4;
  provider?: Provider5;
  model?: Model2;
  language?: Language4;
  level?: Level4;
  refresh?: Refresh;
  conversation_id?: ConversationId;
}
/**
 * Provider output is a proposal; admission happens separately.
 */
export interface ResearchResult {
  schema_version?: SchemaVersion28;
  candidates?: Candidates;
  sources?: Sources1;
  claims?: Claims1;
}
export interface RuntimeCapabilities {
  schema_version?: SchemaVersion29;
  provider: Provider6;
  installed?: Installed;
  authentication?: Authentication;
  version?: Version;
  qualification?: Qualification;
  generation?: Generation;
  browsing?: Browsing;
  streaming?: Streaming;
  cancellation?: Cancellation;
  approvals?: Approvals;
  reason?: Reason3;
}
export interface RuntimeEvent {
  schema_version?: SchemaVersion30;
  sequence?: Sequence;
  run_id: RunId1;
  kind: Kind4;
  timestamp?: Timestamp;
  text?: Text4;
  data?: Data;
}
export interface Data {
  [k: string]: unknown;
}
export interface RuntimeModel {
  schema_version?: SchemaVersion31;
  id: Id10;
  name: Name2;
  is_default?: IsDefault;
}
export interface RuntimeModelCatalog {
  schema_version?: SchemaVersion32;
  provider: Provider7;
  status?: Status2;
  models?: Models;
  message?: Message2;
}
export interface SavedResearch {
  schema_version?: SchemaVersion33;
  id?: Id11;
  bundle_id: BundleId1;
  title: Title2;
  created_at?: CreatedAt5;
}
export interface Settings {
  schema_version?: SchemaVersion34;
  cloud_enabled?: CloudEnabled;
  experimental_yahoo_enabled?: ExperimentalYahooEnabled;
  provider?: Provider8;
  model?: Model3;
  language?: Language5;
  manual_source_review?: ManualSourceReview;
  update_mode?: UpdateMode;
  start_at_login?: StartAtLogin;
  retention_days?: RetentionDays;
  cache_gb?: CacheGb;
}
export interface TermExplanation {
  schema_version?: SchemaVersion35;
  explanation: Explanation1;
  basis: Basis;
  source_ids?: SourceIds2;
  id: Id12;
  term: Term;
  bundle_id: BundleId2;
  asset_id: AssetId5;
  language: Language6;
  level: Level5;
  provider: Provider9;
  model?: Model4;
  created_at?: CreatedAt6;
  interpretation?: Interpretation1;
}
export interface TermRequest {
  schema_version?: SchemaVersion36;
  purpose?: Purpose1;
  term: Term1;
  bundle_id: BundleId3;
  language?: Language7;
  level?: Level6;
  provider?: Provider10;
  model?: Model5;
}
export interface TermResult {
  schema_version?: SchemaVersion37;
  explanation: Explanation2;
  basis: Basis1;
  source_ids?: SourceIds3;
}
export interface SourceReviewDecision {
  schema_version?: SchemaVersion38;
  cancel?: Cancel;
  source_ids?: SourceIds4;
}
export interface SourceReviewRequest {
  schema_version?: SchemaVersion39;
  id?: Id13;
  run_id: RunId2;
  asset_id: AssetId6;
  sources: Sources2;
  expires_at: ExpiresAt2;
}
export interface ReviewSource {
  schema_version?: SchemaVersion40;
  id?: Id14;
  url: Url1;
  publisher: Publisher1;
  policy: SourcePolicy1;
  rights_url: RightsUrl;
  reviewed_at: ReviewedAt;
  local_numeric_only?: LocalNumericOnly;
}
