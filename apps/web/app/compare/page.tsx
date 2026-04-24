import { CitationChip } from "../../components/CitationChip";
import { ComparisonSuggestions } from "../../components/ComparisonSuggestions";
import { ComparisonSourceDetails } from "../../components/ComparisonSourceDetails";
import { ExportControls } from "../../components/ExportControls";
import { FreshnessLabel } from "../../components/FreshnessLabel";
import {
  getComparisonAvailabilityState,
  getComparisonCitationMetadata,
  getComparePageFixture,
  isComparisonAvailable,
  fetchComparisonResponse,
  type CompareAssetIdentity,
  type ComparisonCitation
} from "../../lib/compare";
import { getComparePageSuggestions } from "../../lib/compareSuggestions";
import { comparisonExportUrl, fetchSupportedComparisonExportContract } from "../../lib/exportControls";
import { getAssetFixture, type AssetFixture } from "../../lib/fixtures";

type ComparePageProps = {
  searchParams?: Promise<{
    left?: string;
    right?: string;
  }>;
};

export default async function ComparePage({ searchParams }: ComparePageProps) {
  const query = await searchParams;
  const leftTicker = query?.left?.toUpperCase() ?? "VOO";
  const rightTicker = query?.right?.toUpperCase() ?? "QQQ";
  const comparison = await (async () => {
    try {
      return await fetchComparisonResponse(leftTicker, rightTicker);
    } catch {
      return getComparePageFixture(leftTicker, rightTicker);
    }
  })();
  const availabilityState = getComparisonAvailabilityState(comparison);
  const leftFixture = getAssetFixture(comparison.left_asset.ticker);
  const rightFixture = getAssetFixture(comparison.right_asset.ticker);
  const comparisonSuggestions = getComparePageSuggestions(comparison.left_asset.ticker, comparison.right_asset.ticker);
  const { citations_by_id, contexts_by_source_document_id } = getComparisonCitationMetadata(comparison);
  const bottomLine = comparison.bottom_line_for_beginners;
  const hasSourceBackedComparison =
    isComparisonAvailable(comparison) &&
    comparison.key_differences.length > 0 &&
    bottomLine !== null &&
    comparison.source_documents.length > 0;
  const sourceReferencesById = new Map(
    (comparison.evidence_availability?.source_references ?? []).map((sourceReference) => [
      sourceReference.source_document_id,
      sourceReference
    ])
  );
  const comparisonExportContract = hasSourceBackedComparison
    ? await (async () => {
        try {
          return await fetchSupportedComparisonExportContract(comparison.left_asset.ticker, comparison.right_asset.ticker);
        } catch {
          return null;
        }
      })()
    : null;

  return (
    <main data-compare-availability-state={availabilityState} data-compare-comparison-type={comparison.comparison_type}>
      <section className="asset-hero" data-compare-rendered-state={hasSourceBackedComparison ? "available" : "unavailable"}>
        <p className="eyebrow">{compareEyebrowForAvailability(availabilityState)}</p>
        <h1>
          {comparison.left_asset.ticker} vs {comparison.right_asset.ticker}
        </h1>
        <p>
          {hasSourceBackedComparison
            ? "This page renders a backend-aligned deterministic comparison contract for structure, cost, breadth, and beginner learning context. It does not make a personal recommendation."
            : unavailableSummaryForAvailability(availabilityState)}
        </p>
        <div className="freshness-row">
          {hasSourceBackedComparison ? (
            <>
              <FreshnessLabel label="Comparison data as of" value="2026-04-01" state="fresh" />
              <FreshnessLabel label="Live quotes" value="Unavailable in skeleton" state="unknown" />
            </>
          ) : (
            <>
              <FreshnessLabel label="Comparison availability" value={availabilityState.replace(/_/g, " ")} state="unavailable" />
              <FreshnessLabel label="Generated comparison output" value="Not rendered for this state" state="unavailable" />
            </>
          )}
        </div>
      </section>

      <section className="content-band">
        <div
          className="compare-grid"
          aria-label="Deterministic comparison request"
          data-compare-availability-state={availabilityState}
        >
          <CompareColumn asset={comparison.left_asset} fixture={leftFixture} />
          <CompareColumn asset={comparison.right_asset} fixture={rightFixture} />
        </div>

        <ComparisonSuggestions model={comparisonSuggestions} />

        {hasSourceBackedComparison && bottomLine ? (
          <>
            <ExportControls
              title={`Save ${comparison.left_asset.ticker} vs ${comparison.right_asset.ticker} comparison`}
              marker={`comparison-export-${comparison.left_asset.ticker.toLowerCase()}-${comparison.right_asset.ticker.toLowerCase()}`}
              helper="Save the deterministic comparison export with cited differences, source metadata, freshness context, the educational disclaimer, and licensing scope."
              controls={[
                {
                  kind: "link",
                  controlId: "comparison",
                  label: "Open comparison Markdown export",
                  href: comparisonExportUrl(comparison.left_asset.ticker, comparison.right_asset.ticker),
                  helper:
                    comparisonExportContract?.rendering === "backend_contract"
                      ? "Backend comparison export contract validated for this same-pack Markdown export."
                      : "Uses the local comparison export route for this supported fixture-backed pair.",
                  contract: comparisonExportContract
                }
              ]}
            />

            <section className="plain-panel" aria-labelledby="differences" data-compare-generated-section="key_differences">
              <div className="section-heading">
                <p className="eyebrow">Key differences</p>
                <h2 id="differences">Plain-English comparison</h2>
              </div>
              <div className="difference-list">
                {comparison.key_differences.map((difference) => (
                  <article className="difference-item" key={difference.dimension}>
                    <h3>{difference.dimension}</h3>
                    <p>{difference.plain_english_summary}</p>
                    <span className="chip-row">
                      {difference.citation_ids.map((citationId) => {
                        const citation = citations_by_id.get(citationId);
                        return citation ? (
                          <CitationChip key={citationId} citation={comparisonCitationToChip(citation)} label={citationId} />
                        ) : null;
                      })}
                    </span>
                  </article>
                ))}
              </div>
            </section>

            <section
              className="plain-panel bottom-line"
              aria-labelledby="bottom-line"
              data-compare-generated-section="bottom_line_for_beginners"
            >
              <p className="eyebrow">Bottom line for beginners</p>
              <h2 id="bottom-line">Educational context, not a decision rule</h2>
              <p>{bottomLine.summary}</p>
              <span className="chip-row">
                {bottomLine.citation_ids.map((citationId) => {
                  const citation = citations_by_id.get(citationId);
                  return citation ? (
                    <CitationChip key={citationId} citation={comparisonCitationToChip(citation)} label={citationId} />
                  ) : null;
                })}
              </span>
            </section>

            <section
              className="plain-panel"
              aria-labelledby="comparison-sources"
              data-compare-generated-section="source_documents"
            >
              <div className="section-heading">
                <p className="eyebrow">Comparison source metadata</p>
                <h2 id="comparison-sources">Sources behind these citations</h2>
              </div>
              <div className="section-stack" aria-label="Comparison source metadata">
                {comparison.source_documents.map((sourceDocument) => (
                  <ComparisonSourceDetails
                    key={sourceDocument.source_document_id}
                    sourceDocument={sourceDocument}
                    contexts={contexts_by_source_document_id.get(sourceDocument.source_document_id) ?? []}
                    sourceReference={sourceReferencesById.get(sourceDocument.source_document_id)}
                  />
                ))}
              </div>
            </section>
          </>
        ) : (
          <section
            className="plain-panel unknown-state"
            aria-labelledby="comparison-unavailable"
            data-compare-unavailable-state={availabilityState}
          >
            <div className="section-heading">
              <p className="eyebrow">{compareEyebrowForAvailability(availabilityState)}</p>
              <h2 id="comparison-unavailable">Comparison evidence unavailable</h2>
            </div>
            <FreshnessLabel
              label="Comparison source pack"
              value={availabilityState.replace(/_/g, " ")}
              state="unavailable"
            />
            <p>{comparison.state.message}</p>
            <p className="notice-text">
              {unavailableDetailForAvailability(availabilityState)}
            </p>
            <p className="source-gap-note" data-export-unavailable-state>
              Export controls stay unavailable until a deterministic local comparison pack exists for both requested assets.
            </p>
          </section>
        )}
      </section>
    </main>
  );
}

function CompareColumn({ asset, fixture }: { asset: CompareAssetIdentity; fixture?: AssetFixture }) {
  return (
    <article className="compare-column" data-compare-asset-status={asset.status} data-compare-asset-type={asset.asset_type}>
      <h2>{asset.name}</h2>
      <p>
        {fixture?.beginnerSummary.whatItIs ??
          unsupportedAssetSummary(asset)}
      </p>
      {fixture ? (
        <dl className="fact-list compact">
          {fixture.facts.slice(0, 4).map((fact) => (
            <div key={fact.label}>
              <dt>{fact.label}</dt>
              <dd>{fact.value}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <FreshnessLabel label="Evidence state" value={asset.status} state="unknown" />
      )}
    </article>
  );
}

function comparisonCitationToChip(citation: ComparisonCitation) {
  return {
    citationId: citation.citation_id,
    sourceDocumentId: citation.source_document_id,
    title: citation.title,
    publisher: citation.publisher,
    freshnessState: citation.freshness_state
  };
}

function compareEyebrowForAvailability(availabilityState: string) {
  if (availabilityState === "available") {
    return "Backend-aligned deterministic comparison";
  }
  if (availabilityState === "unsupported") {
    return "Unsupported comparison";
  }
  if (availabilityState === "out_of_scope") {
    return "Out-of-scope comparison";
  }
  if (availabilityState === "eligible_not_cached") {
    return "Eligible but not cached";
  }
  if (availabilityState === "no_local_pack") {
    return "No local comparison pack";
  }
  if (availabilityState === "unknown") {
    return "Unknown comparison";
  }
  return "Comparison unavailable";
}

function unavailableSummaryForAvailability(availabilityState: string) {
  if (availabilityState === "unsupported") {
    return "The requested pair includes an unsupported asset category, so no generated comparison claims, citation chips, source drawers, or export controls are rendered.";
  }
  if (availabilityState === "out_of_scope") {
    return "The requested pair includes a recognized stock outside the current Top-500 manifest-backed scope, so this page stays in an educational blocked state without generated comparison output.";
  }
  if (availabilityState === "eligible_not_cached") {
    return "The requested pair includes an eligible but not locally cached asset, so this page does not invent comparison facts or expose supported comparison output.";
  }
  if (availabilityState === "no_local_pack") {
    return "Both assets are supported individually, but no deterministic local comparison pack exists for this pair yet, so generated comparison output stays hidden.";
  }
  return "The requested pair is unavailable in deterministic local compare data, so this page avoids invented facts and renders only the blocked-state explanation.";
}

function unavailableDetailForAvailability(availabilityState: string) {
  if (availabilityState === "unsupported") {
    return "No factual citation chips or source drawers are shown because unsupported assets must stay blocked from generated comparison output.";
  }
  if (availabilityState === "out_of_scope") {
    return "No factual citation chips or source drawers are shown because out-of-scope assets cannot receive generated comparison output in the current MVP.";
  }
  if (availabilityState === "eligible_not_cached") {
    return "No factual citation chips or source drawers are shown because the requested pair needs a cached local pack before deterministic comparison output can exist.";
  }
  if (availabilityState === "no_local_pack") {
    return "No factual citation chips or source drawers are shown because this requested supported pair has no deterministic local comparison pack yet.";
  }
  return "No factual citation chips or source drawers are shown because this local compare request has no source-backed comparison pack for the requested pair.";
}

function unsupportedAssetSummary(asset: CompareAssetIdentity) {
  if (asset.status === "unsupported") {
    return "This selected asset is recognized but blocked from generated comparison output in the current MVP scope.";
  }
  if (asset.asset_type === "stock" || asset.asset_type === "etf") {
    return "No local comparison facts are rendered for this asset in the current compare request. Use the asset page or an available local comparison pack instead.";
  }
  return "Unknown in the local deterministic data. No facts are invented for assets without fixture-backed evidence.";
}
