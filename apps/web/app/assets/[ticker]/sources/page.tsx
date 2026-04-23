import { AssetHeader } from "../../../../components/AssetHeader";
import {
  SourceDrawer,
  sourceDrawerStateFromFreshnessState,
  sourceDrawerStateFromSupportState,
  type SourceDrawerState
} from "../../../../components/SourceDrawer";
import { resolveLocalSearchResponse } from "../../../../lib/search";
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

export function generateStaticParams() {
  return Object.keys(assetFixtures).map((ticker) => ({ ticker }));
}

export default async function AssetSourcesPage({ params }: AssetSourcesPageProps) {
  const { ticker } = await params;
  const search = resolveLocalSearchResponse(ticker);
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
      <main>
        <section className="plain-panel" data-source-list-state={listState} data-source-list-asset={ticker}>
          <div className="section-heading">
            <p className="eyebrow">Source list</p>
            <h1>{ticker.toUpperCase()} source-list view</h1>
          </div>
          <p className="source-gap-note" data-source-list-unsupported>{sourceListUnavailableMessage(listState)}</p>
        </section>
      </main>
    );
  }

  const drawerSources = asset.sourceDocuments.map(toSourceDrawerDocument);

  return (
    <main>
      <AssetHeader asset={asset} />
      <section className="plain-panel" data-source-list-state={listState} data-source-list-asset={asset.ticker}>
        <div className="section-heading">
          <p className="eyebrow">Source list</p>
          <h1>Source list for {asset.ticker}</h1>
        </div>
        <p className="source-gap-note">Source list entries include source metadata and allowed excerpts from the local evidence pack.</p>
      </section>
      <section className="plain-panel" aria-label="Source list entries">
        {drawerSources.length === 0 ? (
          <p className="source-gap-note" data-source-list-empty-state>
            No source documents are available for this supported fixture in source-list mode.
          </p>
        ) : (
          drawerSources.map((source) => {
            const sourceContexts = getCitationContextsForSource(asset, source.source_document_id);
            return (
              <SourceDrawer
                key={source.source_document_id}
                source={source}
                claim={
                  sourceContexts[0]?.claimContext ??
                  `${source.title} is included in this supported deterministic source list.`
                }
                contexts={sourceContexts}
                drawerState={sourceDrawerStateFromFreshnessState(source.freshness_state)}
              />
            );
          })
        )}
      </section>
    </main>
  );
}
