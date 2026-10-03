/* Generated from backend/app/contracts.py. Do not edit. */

export type SchemaVersion = "1";
export type Id = string;
export type Symbol = string;
export type Name = string;
export type AssetType =
  "stock" | "etf" | "fund" | "bond" | "crypto" | "option" | "future" | "index" | "other" | "unknown";
export type Exchange = string | null;
export type Currency = string | null;
export type SchemaVersion1 = "1";
export type FormatVersion = "1";
export type DatabaseRevision = "0001";
export type CreatedAt = string;
export type Fingerprint = string;
export type Assets = number;
export type EvidenceVersions = number;
export type Conversations = number;
export type SavedReports = number;
export type TermExplanations = number;
export type Jobs = number;
export type CredentialsIncluded = false;
export type CanRestore = boolean;
export type Reason = string | null;
export type SchemaVersion2 = "1";
export type Id1 = string;
export type AssetId = string;
export type Section = string;
export type Text = string;
export type Kind = "fact" | "calculation" | "interpretation" | "unverified_note";
export type SourceIds = string[];
export type AsOf = string | null;
export type Value = number | null;
export type Unit = string | null;
export type InputClaimIds = string[];
export type SchemaVersion3 = "1";
export type Id2 = string;
export type AssetId1 = string;
export type SchemaVersion4 = "1";
export type Role = "user" | "assistant" | "scope";
export type Text1 = string | null;
export type AssetId2 = string | null;
export type BundleId = string | null;
export type Messages = ConversationMessage[];
export type Bookmarked = boolean;
export type CreatedAt1 = string;
export type LastActivity = string | null;
export type SchemaVersion5 = "1";
export type Id3 = string;
export type CreatedAt2 = string;
export type SchemaVersion6 = "1";
export type Id4 = string;
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
export type Provenance = "agent_candidate" | "structured_adapter" | "verified_retrieval" | "user_import";
export type Sources = Source[];
export type Claims = Claim[];
export type Notes = Claim[];
export type State = "partial" | "available" | "stale" | "unavailable";
export type Language = "en" | "zh-TW";
export type SchemaVersion7 = "1";
export type Provider = "codex";
export type Status = "idle" | "pending" | "authenticated" | "cancelled" | "expired" | "failed";
export type VerificationUrl = "https://auth.openai.com/codex/device" | null;
export type UserCode = string | null;
export type ExpiresAt = string | null;
export type Message = string;
export type SchemaVersion8 = "1";
export type Query = string;
export type AssetId4 = string | null;
export type Provider1 = "codex" | "gemini" | "claude";
export type Model = string | null;
export type Language1 = "en" | "zh-TW";
export type Level = "beginner" | "intermediate";
export type Refresh = boolean;
export type ConversationId = string | null;
export type SchemaVersion9 = "1";
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
export type SchemaVersion10 = "1";
export type Provider2 = "codex" | "gemini" | "claude";
export type Installed = boolean;
export type Authentication = "unknown" | "authenticated" | "required" | "unsupported";
export type Version = string | null;
export type Qualification = "unqualified" | "protocol_only" | "live";
export type Generation = boolean;
export type Browsing = boolean;
export type Streaming = boolean;
export type Cancellation = boolean;
export type Approvals = boolean;
export type Reason1 = string | null;
export type SchemaVersion11 = "1";
export type Sequence = number;
export type RunId = string;
export type Kind1 =
  | "run.started"
  | "message.delta"
  | "tool.started"
  | "evidence.registered"
  | "approval.required"
  | "run.completed"
  | "run.failed"
  | "run.cancelled";
export type Timestamp = string;
export type Text2 = string;
export type SchemaVersion12 = "1";
export type Id5 = string;
export type Name1 = string;
export type IsDefault = boolean;
export type SchemaVersion13 = "1";
export type Provider3 = "codex" | "gemini" | "claude";
export type Status1 = "available" | "authentication_required" | "unavailable";
/**
 * @maxItems 200
 */
export type Models = RuntimeModel[];
export type Message1 = string;
export type SchemaVersion14 = "1";
export type Id6 = string;
export type BundleId1 = string;
export type Title1 = string;
export type CreatedAt3 = string;
export type SchemaVersion15 = "1";
export type CloudEnabled = boolean;
export type Provider4 = "codex" | "gemini" | "claude";
export type Model1 = string | null;
export type Language2 = "en" | "zh-TW";
export type ManualSourceReview = boolean;
export type UpdateMode = "notify" | "manual" | "automatic";
export type StartAtLogin = boolean;
export type RetentionDays = number;
export type CacheGb = number;
export type SchemaVersion16 = "1";
export type Explanation = string;
export type Basis = "general" | "snapshot";
/**
 * @maxItems 20
 */
export type SourceIds1 =
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
export type Id7 = string;
export type Term = string;
export type BundleId2 = string;
export type AssetId5 = string;
export type Language3 = "en" | "zh-TW";
export type Level1 = "beginner" | "intermediate";
export type Provider5 = "codex" | "gemini" | "claude";
export type Model2 = string | null;
export type CreatedAt4 = string;
export type Interpretation = true;
export type SchemaVersion17 = "1";
export type Purpose = "term_explanation";
export type Term1 = string;
export type BundleId3 = string;
export type Language4 = "en" | "zh-TW";
export type Level2 = "beginner" | "intermediate";
export type Provider6 = "codex" | "gemini" | "claude";
export type Model3 = string | null;
export type SchemaVersion18 = "1";
export type Explanation1 = string;
export type Basis1 = "general" | "snapshot";
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

export interface DesktopContracts {
  AssetIdentity?: AssetIdentity;
  BackupSummary?: BackupSummary;
  Claim?: Claim;
  Conversation?: Conversation;
  EvidenceBundle?: EvidenceBundle;
  ProviderLogin?: ProviderLogin;
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
}
export interface AssetIdentity {
  schema_version?: SchemaVersion;
  id: Id;
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
  schema_version?: SchemaVersion1;
  format_version?: FormatVersion;
  database_revision?: DatabaseRevision;
  created_at: CreatedAt;
  fingerprint: Fingerprint;
  assets: Assets;
  evidence_versions: EvidenceVersions;
  conversations: Conversations;
  saved_reports: SavedReports;
  term_explanations?: TermExplanations;
  jobs: Jobs;
  credentials_included?: CredentialsIncluded;
  can_restore: CanRestore;
  reason?: Reason;
}
export interface Claim {
  schema_version?: SchemaVersion2;
  id?: Id1;
  asset_id: AssetId;
  section?: Section;
  text: Text;
  kind?: Kind;
  source_ids?: SourceIds;
  as_of?: AsOf;
  value?: Value;
  unit?: Unit;
  input_claim_ids?: InputClaimIds;
}
export interface Conversation {
  schema_version?: SchemaVersion3;
  id?: Id2;
  asset_id: AssetId1;
  messages?: Messages;
  bookmarked?: Bookmarked;
  created_at?: CreatedAt1;
  last_activity?: LastActivity;
}
export interface ConversationMessage {
  schema_version?: SchemaVersion4;
  role: Role;
  text?: Text1;
  asset_id?: AssetId2;
  bundle_id?: BundleId;
}
export interface EvidenceBundle {
  schema_version?: SchemaVersion5;
  id?: Id3;
  asset: AssetIdentity;
  created_at?: CreatedAt2;
  sources?: Sources;
  claims?: Claims;
  notes?: Notes;
  state?: State;
  language?: Language;
}
export interface Source {
  schema_version?: SchemaVersion6;
  id?: Id4;
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
}
/**
 * Ephemeral connection UI state. Never stored in the library or exports.
 */
export interface ProviderLogin {
  schema_version?: SchemaVersion7;
  provider?: Provider;
  status?: Status;
  verification_url?: VerificationUrl;
  user_code?: UserCode;
  expires_at?: ExpiresAt;
  message?: Message;
}
export interface ResearchRequest {
  schema_version?: SchemaVersion8;
  query: Query;
  asset_id?: AssetId4;
  provider?: Provider1;
  model?: Model;
  language?: Language1;
  level?: Level;
  refresh?: Refresh;
  conversation_id?: ConversationId;
}
/**
 * Provider output is a proposal; admission happens separately.
 */
export interface ResearchResult {
  schema_version?: SchemaVersion9;
  candidates?: Candidates;
  sources?: Sources1;
  claims?: Claims1;
}
export interface RuntimeCapabilities {
  schema_version?: SchemaVersion10;
  provider: Provider2;
  installed?: Installed;
  authentication?: Authentication;
  version?: Version;
  qualification?: Qualification;
  generation?: Generation;
  browsing?: Browsing;
  streaming?: Streaming;
  cancellation?: Cancellation;
  approvals?: Approvals;
  reason?: Reason1;
}
export interface RuntimeEvent {
  schema_version?: SchemaVersion11;
  sequence?: Sequence;
  run_id: RunId;
  kind: Kind1;
  timestamp?: Timestamp;
  text?: Text2;
  data?: Data;
}
export interface Data {
  [k: string]: unknown;
}
export interface RuntimeModel {
  schema_version?: SchemaVersion12;
  id: Id5;
  name: Name1;
  is_default?: IsDefault;
}
export interface RuntimeModelCatalog {
  schema_version?: SchemaVersion13;
  provider: Provider3;
  status?: Status1;
  models?: Models;
  message?: Message1;
}
export interface SavedResearch {
  schema_version?: SchemaVersion14;
  id?: Id6;
  bundle_id: BundleId1;
  title: Title1;
  created_at?: CreatedAt3;
}
export interface Settings {
  schema_version?: SchemaVersion15;
  cloud_enabled?: CloudEnabled;
  provider?: Provider4;
  model?: Model1;
  language?: Language2;
  manual_source_review?: ManualSourceReview;
  update_mode?: UpdateMode;
  start_at_login?: StartAtLogin;
  retention_days?: RetentionDays;
  cache_gb?: CacheGb;
}
export interface TermExplanation {
  schema_version?: SchemaVersion16;
  explanation: Explanation;
  basis: Basis;
  source_ids?: SourceIds1;
  id: Id7;
  term: Term;
  bundle_id: BundleId2;
  asset_id: AssetId5;
  language: Language3;
  level: Level1;
  provider: Provider5;
  model?: Model2;
  created_at?: CreatedAt4;
  interpretation?: Interpretation;
}
export interface TermRequest {
  schema_version?: SchemaVersion17;
  purpose?: Purpose;
  term: Term1;
  bundle_id: BundleId3;
  language?: Language4;
  level?: Level2;
  provider?: Provider6;
  model?: Model3;
}
export interface TermResult {
  schema_version?: SchemaVersion18;
  explanation: Explanation1;
  basis: Basis1;
  source_ids?: SourceIds2;
}
