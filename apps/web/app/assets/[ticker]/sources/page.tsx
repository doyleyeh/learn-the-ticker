import { AssetHeader } from "../../../../components/AssetHeader";
import {
  SourceDrawer,
  sourceDrawerStateFromFreshnessState,
  sourceDrawerStateFromSupportState,
  type SourceDrawerState
} from "../../../../components/SourceDrawer";
import { resolveSearchResponse } from "../../../../lib/search";
import { fetchSupportedSourceDrawerResponse } from "../../../../lib/sourceDrawer";
import {
  assetFixtures,
  getAssetFixture,
  getCitationContextsForSource,
  toSourceDrawerDocument
} from "../../../../lib/fixtures";

type AssetSourcesPageProps = {
  params: Promise<{
    ticker: string;
  }>;
};

const SOURCE_LIST_SECTION_ORDER =
  "header,source_inspection_summary,freshness_source_use_overview,source_entries,educational_source_use_note";

type SourceListSource = ReturnType<typeof toSourceDrawerDocument> & {
  allowedExcerptNote?: string | null;
};

type SourceListEntry = {
  source: SourceListSource;
  claim: string;
  contexts: ReturnType<typeof getCitationContextsForSource>;
  drawerState: SourceDrawerState;
};

function sourceListStateFromSearch(status: string) {
  if (status === "supported") {
    return "available";
  }
  if (status === "ingestion_needed") {
    return "eligible_not_cached";
  }
  if (status === "unsupported") {
    return "unsupported";
  }
  if (status === "out_of_scope") {
    return "out_of_scope";
  }
  return sourceDrawerStateFromSupportState(status);
}

function sourceListUnavailableMessage(state: SourceDrawerState) {
  if (state === "unsupported") {
    return "No source metadata is rendered because this ticker is recognized as unsupported in the current MVP scope.";
  }
  if (state === "out_of_scope") {
    return "No source metadata is rendered because this ticker is outside the Top-500 manifest-backed support scope.";
  }
  if (state === "unknown") {
    return "No source metadata is rendered because this ticker is unknown in local deterministic data.";
  }
  if (state === "eligible_not_cached") {
    return "No source metadata is rendered because this ticker is eligible but not locally cached yet.";
  }
  if (state === "unavailable") {
    return "No source metadata is rendered because the local source pack is currently unavailable.";
  }
  if (state === "partial") {
    return "No source metadata is rendered because source coverage is still partial for this local view.";
  }
  if (state === "stale") {
    return "No source metadata is rendered from a stale support state in this fallback source-list path.";
  }
  if (state === "insufficient_evidence") {
    return "No source metadata is rendered because local evidence is insufficient for source-list output.";
  }
  return "No source metadata is rendered for this source-list state.";
}

function displayValue(value?: string | null) {
  return value && value.trim().length ? value : "Unknown";
}

function humanizePolicy(value?: string | null) {
  return displayValue(value).replaceAll("_", " ");
}

function isOfficialOrStructuredSource(source: SourceListSource) {
  const sourceType = source.source_type.toLowerCase();
  const sourceQuality = source.source_quality.toLowerCase();
  return (
    source.isOfficial ||
    sourceQuality === "official" ||
    sourceQuality === "issuer" ||
    sourceType.includes("sec") ||
    sourceType.includes("issuer") ||
    sourceType.includes("prospectus") ||
    sourceType.includes("fact") ||
    sourceType.includes("holdings") ||
    sourceType.includes("structured")
  );
}

export function generateStaticParams() {
  return Object.keys(assetFixtures).map((ticker) => ({ ticker }));
}

export default async function AssetSourcesPage({ params }: AssetSourcesPageProps) {
  const { ticker } = await params;
  const search = await resolveSearchResponse(ticker);
  const searchState = sourceListStateFromSearch(search.state.status);
  const asset = getAssetFixture(ticker);
  const listState: SourceDrawerState = asset && searchState === "available" ? "available" : searchState;

  if (listState === "available" && !asset) {
    return (
      <main>
        <section className="plain-panel" data-source-list-state="available" data-source-list-asset={ticker}>
          <div className="section-heading">
            <p className="eyebrow">Source list</p>
            <h1>Source list unavailable</h1>
          </div>
          <p className="source-gap-note">
            This ticker is marked as available in search contracts, but no local fixture exists for deterministic source-list rendering.
          </p>
        </section>
      </main>
    );
  }

  if (listState !== "available" || !asset) {
    return (
      <main
        data-prd-source-list-marker="source-list-blocked-or-limited-flow-v1"
        data-source-list-section-order={SOURCE_LIST_SECTION_ORDER}
      >
        <section className="plain-panel" data-source-list-state={listState} data-source-list-asset={ticker}>
          <div className="section-heading">
            <p className="eyebrow">Source list</p>
            <h1>{ticker.toUpperCase()} source-list view</h1>
          </div>
          <p className="source-gap-note" data-source-list-unsupported>{sourceListUnavailableMessage(listState)}</p>
          <p className="source-gap-note" data-source-list-blocked-copy>
            Source access is limited to supported, same-asset evidence packs. This page does not create generated
            summaries, chat answers, comparisons, or risk explanations for blocked or unavailable asset states.
          </p>
          <nav className="source-list-nav" aria-label="Source-list navigation">
            <a href="/">Back to search</a>
          </nav>
        </section>
      </main>
    );
  }

  const backendSourceDrawer = await (async () => {
    try {
      return await fetchSupportedSourceDrawerResponse(asset.ticker);
    } catch {
      return null;
    }
  })();
  const localDrawerSources = asset.sourceDocuments.map((source) => {
    const drawerSource = toSourceDrawerDocument(source);
    const sourceContexts = getCitationContextsForSource(asset, drawerSource.source_document_id);
    return {
      source: drawerSource,
      claim:
        sourceContexts[0]?.claimContext ??
        `${drawerSource.title} is included in this supported deterministic source list.`,
      contexts: sourceContexts,
      drawerState: sourceDrawerStateFromFreshnessState(drawerSource.freshness_state)
    };
  });
  const drawerEntries: SourceListEntry[] = backendSourceDrawer ? backendSourceDrawer.entries : localDrawerSources;
  const renderedListState = backendSourceDrawer?.drawerState ?? listState;
  const renderingMode = backendSourceDrawer ? "backend_contract" : "local_fixture";
  const sourceCount = drawerEntries.length;
  const officialOrStructuredSourceCount = drawerEntries.filter((entry) => isOfficialOrStructuredSource(entry.source)).length;
  const citationContextCount = drawerEntries.reduce((total, entry) => total + entry.contexts.length, 0);
  const firstRetrievedAt = drawerEntries[0]?.source.retrieved_at;
  const freshnessStates = [...new Set(drawerEntries.map((entry) => entry.source.freshness_state))];
  const sourceUsePolicies = [...new Set(drawerEntries.map((entry) => entry.source.source_use_policy))];
  const allowlistStatuses = [...new Set(drawerEntries.map((entry) => entry.source.allowlist_status))];
  const canExportFullTextCount = drawerEntries.filter((entry) => entry.source.permitted_operations?.can_export_full_text).length;

  return (
    <main
      data-prd-source-list-marker="supported-source-list-inspection-flow-v1"
      data-source-list-section-order={SOURCE_LIST_SECTION_ORDER}
      data-source-list-rendering={renderingMode}
      data-source-list-no-api-base-fallback={backendSourceDrawer ? "not_used" : "deterministic_local_fixture"}
      data-source-list-trust-metric-readiness="source_drawer_usage,citation_coverage,freshness_accuracy"
    >
      <AssetHeader asset={asset} layoutMarker="source_list_header" />
      <section
        className="plain-panel"
        aria-labelledby="source-inspection-summary"
        data-prd-section="source_inspection_summary"
        data-source-list-state={renderedListState}
        data-source-list-asset={asset.ticker}
        data-source-list-rendering={renderingMode}
        data-source-list-source-count={sourceCount}
        data-source-list-official-structured-count={officialOrStructuredSourceCount}
        data-source-list-citation-context-count={citationContextCount}
      >
        <div className="section-heading">
          <p className="eyebrow">Source inspection</p>
          <h2 id="source-inspection-summary">Source review for {asset.ticker}</h2>
        </div>
        <nav className="source-list-nav" aria-label="Source-list navigation">
          <a href={`/assets/${asset.ticker}`}>Back to {asset.ticker} learning page</a>
        </nav>
        <p className="source-gap-note">
          Source entries are evidence for learning. They explain where cited claims came from, how fresh each source is,
          and what source-use rights allow; they are not buy, sell, hold, allocation, tax, or trading guidance.
        </p>
        <dl className="source-list-summary-grid">
          <div>
            <dt>Rendering mode</dt>
            <dd>{renderingMode === "backend_contract" ? "Backend source-drawer contract" : "Local fixture fallback"}</dd>
          </div>
          <div>
            <dt>Source count</dt>
            <dd>{sourceCount}</dd>
          </div>
          <div>
            <dt>Official or structured</dt>
            <dd>{officialOrStructuredSourceCount}</dd>
          </div>
          <div>
            <dt>Citation contexts</dt>
            <dd>{citationContextCount}</dd>
          </div>
        </dl>
      </section>
      <section
        className="plain-panel"
        aria-labelledby="source-freshness-source-use-overview"
        data-prd-section="freshness_source_use_overview"
        data-source-list-freshness-overview
        data-source-list-freshness-states={freshnessStates.join(",") || "unknown"}
        data-source-list-source-use-policies={sourceUsePolicies.join(",") || "unknown"}
        data-source-list-allowlist-statuses={allowlistStatuses.join(",") || "unknown"}
        data-source-list-full-text-export-count={canExportFullTextCount}
      >
        <div className="section-heading">
          <p className="eyebrow">Freshness and source use</p>
          <h2 id="source-freshness-source-use-overview">Inspection overview</h2>
        </div>
        <dl className="source-list-summary-grid">
          <div>
            <dt>Freshness states</dt>
            <dd>{freshnessStates.map(humanizePolicy).join(", ") || "Unknown"}</dd>
          </div>
          <div>
            <dt>First retrieved timestamp</dt>
            <dd>{displayValue(firstRetrievedAt)}</dd>
          </div>
          <div>
            <dt>Source-use policies</dt>
            <dd>{sourceUsePolicies.map(humanizePolicy).join(", ") || "Unknown"}</dd>
          </div>
          <div>
            <dt>Allowlist statuses</dt>
            <dd>{allowlistStatuses.map(humanizePolicy).join(", ") || "Unknown"}</dd>
          </div>
          <div>
            <dt>Full-text export allowed</dt>
            <dd>{canExportFullTextCount} sources where the drawer contract permits it</dd>
          </div>
        </dl>
        <p className="source-gap-note" data-source-list-rendering-note>
          {renderingMode === "backend_contract"
            ? "This page is rendering the existing backend source-drawer contract for same-asset sources."
            : "No API-base source-drawer contract is available, so this page uses the deterministic local fixture fallback."}
        </p>
      </section>
      <section
        className="plain-panel source-list-entry-section"
        aria-labelledby="source-list-entries"
        data-prd-section="source_entries"
        data-source-list-entry-count={sourceCount}
      >
        <div className="section-heading">
          <p className="eyebrow">Citation and claim context</p>
          <h2 id="source-list-entries">Source drawers</h2>
        </div>
        {drawerEntries.length === 0 ? (
          <p className="source-gap-note" data-source-list-empty-state>
            No source documents are available for this supported source-list state.
          </p>
        ) : (
          drawerEntries.map((entry) => (
            <SourceDrawer
              key={entry.source.source_document_id}
              source={entry.source}
              claim={entry.claim}
              contexts={entry.contexts}
              drawerState={entry.drawerState}
            />
          ))
        )}
      </section>
      <section
        className="plain-panel"
        aria-labelledby="source-use-note"
        data-prd-section="educational_source_use_note"
        data-source-list-educational-note
      >
        <div className="section-heading">
          <p className="eyebrow">How to read sources</p>
          <h2 id="source-use-note">Educational source-use note</h2>
        </div>
        <p>
          Official and structured sources are preferred for stable facts. Stale, unknown, unavailable, partial, and
          insufficient-evidence states should be read as limits on what the product can verify, not as signals to trade.
        </p>
      </section>
    </main>
  );
}
