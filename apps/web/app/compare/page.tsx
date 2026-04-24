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
  type ComparisonCitation,
  type StockEtfRelationshipModel
} from "../../lib/compare";
import { getAssetComparisonSuggestions, getComparePageSuggestions } from "../../lib/compareSuggestions";
import { comparisonExportUrl, fetchSupportedComparisonExportContract } from "../../lib/exportControls";
import { getAssetFixture, type AssetFixture } from "../../lib/fixtures";
import { buildTrustMetricSurfaceDescriptor } from "../../lib/trustMetrics";

type ComparePageProps = {
  searchParams?: Promise<{
    left?: string;
    right?: string;
  }>;
};

export default async function ComparePage({ searchParams }: ComparePageProps) {
  const query = await searchParams;
  const leftTicker = normalizeCompareParam(query?.left);
  const rightTicker = normalizeCompareParam(query?.right);

  if (!leftTicker && !rightTicker) {
    return <CompareBuilderState mode="empty" />;
  }

  if (!leftTicker || !rightTicker) {
    const selectedTicker = leftTicker ?? rightTicker ?? "";
    const selectedSide = leftTicker ? "left" : "right";
    return <CompareBuilderState mode="one_side_selected" selectedTicker={selectedTicker} selectedSide={selectedSide} />;
  }

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
  const stockEtfRelationship =
    comparison.comparison_type === "stock_vs_etf" && comparison.stock_etf_relationship
      ? comparison.stock_etf_relationship
      : null;
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
  const comparisonTrustMetricDescriptor = buildTrustMetricSurfaceDescriptor({
    eventType: "comparison_usage",
    workflowArea: "comparison",
    comparisonLeftTicker: comparison.left_asset.ticker,
    comparisonRightTicker: comparison.right_asset.ticker,
    comparisonState: availabilityState,
    selectedSection: "compare_page",
    citationCount: citations_by_id.size,
    sourceDocumentCount: comparison.source_documents.length,
    evidenceState: hasSourceBackedComparison ? "available" : availabilityState
  });

  return (
    <main
      data-prd-compare-marker="separate-comparison-workflow-v1"
      data-prd-compare-result-layout="source-backed-deterministic-pack"
      data-prd-section-order={
        stockEtfRelationship
          ? "header,selected_assets,beginner_bottom_line,stock_vs_etf_relationship_context,key_differences,export_controls,suggested_comparisons,source_metadata"
          : "header,selected_assets,beginner_bottom_line,key_differences,export_controls,suggested_comparisons,source_metadata"
      }
      data-compare-availability-state={availabilityState}
      data-compare-comparison-type={comparison.comparison_type}
      data-trust-metric-schema-version={comparisonTrustMetricDescriptor.schemaVersion}
      data-trust-metric-mode={comparisonTrustMetricDescriptor.mode}
      data-trust-metric-event={comparisonTrustMetricDescriptor.eventType}
      data-trust-metric-workflow-area={comparisonTrustMetricDescriptor.workflowArea}
      data-trust-metric-occurred-at={comparisonTrustMetricDescriptor.occurredAt}
      data-trust-metric-persistence={comparisonTrustMetricDescriptor.persistence}
      data-trust-metric-external-analytics={comparisonTrustMetricDescriptor.externalAnalytics}
      data-trust-metric-live-external-calls={comparisonTrustMetricDescriptor.liveExternalCalls}
      data-trust-metric-left-ticker={comparisonTrustMetricDescriptor.comparisonLeftTicker}
      data-trust-metric-right-ticker={comparisonTrustMetricDescriptor.comparisonRightTicker}
      data-trust-metric-comparison-state={comparisonTrustMetricDescriptor.comparisonState}
      data-trust-metric-citation-count={comparisonTrustMetricDescriptor.citationCount}
      data-trust-metric-source-document-count={comparisonTrustMetricDescriptor.sourceDocumentCount}
      data-trust-metric-evidence-state={comparisonTrustMetricDescriptor.evidenceState}
    >
      <section
        className="asset-hero"
        data-prd-section="header"
        data-compare-rendered-state={hasSourceBackedComparison ? "available" : "unavailable"}
      >
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
          data-prd-section="selected_assets"
          data-compare-availability-state={availabilityState}
        >
          <CompareColumn asset={comparison.left_asset} fixture={leftFixture} />
          <CompareColumn asset={comparison.right_asset} fixture={rightFixture} />
        </div>

        {hasSourceBackedComparison && bottomLine ? (
          <>
            <section
              className="plain-panel bottom-line"
              aria-labelledby="bottom-line"
              data-prd-section="beginner_bottom_line"
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

            {stockEtfRelationship ? (
              <StockEtfRelationshipSection model={stockEtfRelationship} citationsById={citations_by_id} />
            ) : null}

            <section
              className="plain-panel"
              aria-labelledby="differences"
              data-prd-section="key_differences"
              data-compare-generated-section="key_differences"
            >
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
              data-prd-section="export_controls"
              data-compare-result-export-section="same_comparison_pack"
            >
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
            </section>

            <section data-prd-section="suggested_comparisons" data-compare-result-suggestions="connected-workflow-aid">
              <ComparisonSuggestions model={comparisonSuggestions} />
            </section>

            <section
              className="plain-panel"
              aria-labelledby="comparison-sources"
              data-prd-section="source_metadata"
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
            data-prd-section="blocked_or_limited_state"
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

function CompareBuilderState({
  mode,
  selectedTicker,
  selectedSide
}: {
  mode: "empty" | "one_side_selected";
  selectedTicker?: string;
  selectedSide?: "left" | "right";
}) {
  const selectedFixture = selectedTicker ? getAssetFixture(selectedTicker) : undefined;
  const suggestions = selectedTicker ? getAssetComparisonSuggestions(selectedTicker) : null;

  return (
    <main
      data-prd-compare-marker="separate-comparison-workflow-v1"
      data-prd-compare-builder-state={mode}
      data-prd-section-order="header,compare_builder,selected_asset_when_present,suggested_comparisons"
      data-compare-builder-generates-output="false"
      data-compare-builder-live-external-calls="false"
    >
      <section className="asset-hero" data-prd-section="header" data-compare-rendered-state={mode}>
        <p className="eyebrow">Separate comparison workflow</p>
        <h1>{mode === "empty" ? "Compare two supported assets" : `Compare ${selectedTicker} with another asset`}</h1>
        <p>
          {mode === "empty"
            ? "Choose two supported stocks or ETFs to open a source-backed comparison page. This builder is separate from the home page single-asset search."
            : "One asset is selected. Add a second supported stock or ETF to open a source-backed comparison page; no two-asset comparison is generated from a one-sided state."}
        </p>
        <div className="freshness-row">
          <FreshnessLabel label="Comparison output" value="Not generated in builder state" state="unavailable" />
          <FreshnessLabel label="Live provider calls" value="None" state="fresh" />
        </div>
      </section>

      <section className="content-band compare-builder-flow" data-prd-section="compare_builder">
        <section className="plain-panel compare-builder-panel" aria-labelledby="compare-builder-heading">
          <div className="section-heading">
            <p className="eyebrow">{mode === "empty" ? "Empty builder" : "One side selected"}</p>
            <h2 id="compare-builder-heading">
              {mode === "empty" ? "Select two assets to compare" : "Add the second asset"}
            </h2>
          </div>
          <form className="compare-builder-form" action="/compare" method="get">
            {mode === "one_side_selected" && selectedSide === "left" ? (
              <input type="hidden" name="left" value={selectedTicker} />
            ) : null}
            {mode === "one_side_selected" && selectedSide === "right" ? (
              <input type="hidden" name="right" value={selectedTicker} />
            ) : null}

            {mode === "empty" || selectedSide === "right" ? (
              <label>
                <span>Left ticker</span>
                <input name="left" placeholder="VOO" defaultValue={selectedSide === "right" ? "" : undefined} />
              </label>
            ) : (
              <SelectedBuilderCard label="Left asset selected" ticker={selectedTicker ?? ""} fixture={selectedFixture} />
            )}

            {mode === "empty" || selectedSide === "left" ? (
              <label>
                <span>Right ticker</span>
                <input name="right" placeholder="QQQ" defaultValue={selectedSide === "left" ? "" : undefined} />
              </label>
            ) : (
              <SelectedBuilderCard label="Right asset selected" ticker={selectedTicker ?? ""} fixture={selectedFixture} />
            )}

            <button className="search-button" type="submit">
              Open comparison
            </button>
          </form>
          <p className="source-gap-note" data-compare-builder-no-generated-output>
            Builder states do not render citation chips, source drawers, generated key differences, or export controls until two
            supported assets have an available deterministic comparison pack.
          </p>
        </section>

        {mode === "one_side_selected" && selectedTicker ? (
          <section
            className="plain-panel"
            aria-labelledby="selected-asset-heading"
            data-prd-section="selected_asset_when_present"
            data-compare-builder-selected-side={selectedSide}
            data-compare-builder-selected-ticker={selectedTicker}
          >
            <div className="section-heading">
              <p className="eyebrow">Selected asset</p>
              <h2 id="selected-asset-heading">{selectedTicker}</h2>
            </div>
            <CompareColumn
              asset={{
                ticker: selectedTicker,
                name: selectedFixture?.name ?? selectedTicker,
                asset_type: selectedFixture?.assetType ?? "unknown",
                exchange: selectedFixture?.exchange ?? null,
                issuer: selectedFixture?.issuer ?? null,
                status: selectedFixture ? "supported" : "unknown",
                supported: Boolean(selectedFixture)
              }}
              fixture={selectedFixture}
            />
          </section>
        ) : null}

        <section data-prd-section="suggested_comparisons" data-compare-builder-suggestions="examples-not-recommendations">
          {suggestions ? (
            <ComparisonSuggestions model={suggestions} />
          ) : (
            <section className="plain-panel comparison-suggestions" aria-labelledby="empty-builder-examples">
              <div className="section-heading">
                <p className="eyebrow">Learning examples</p>
                <h2 id="empty-builder-examples">Available deterministic examples</h2>
              </div>
              <p>
                These links are fixture-backed comparison examples for learning the workflow. They are not recommendations or
                personalized suitability guidance.
              </p>
              <div className="comparison-suggestion-list" aria-label="Available deterministic comparison examples">
                <BuilderExampleLink leftTicker="VOO" rightTicker="QQQ" description="ETF-vs-ETF example for benchmark, cost, holdings breadth, and beginner role." />
                <BuilderExampleLink leftTicker="AAPL" rightTicker="VOO" description="Stock-vs-ETF example for single-company and ETF-basket relationship context." />
              </div>
            </section>
          )}
        </section>
      </section>
    </main>
  );
}

function SelectedBuilderCard({
  label,
  ticker,
  fixture
}: {
  label: string;
  ticker: string;
  fixture?: AssetFixture;
}) {
  return (
    <div className="selected-builder-card">
      <span>{label}</span>
      <strong>{ticker}</strong>
      <small>{fixture ? `${fixture.name} · ${fixture.assetType.toUpperCase()}` : "Unknown in local deterministic data"}</small>
    </div>
  );
}

function BuilderExampleLink({
  leftTicker,
  rightTicker,
  description
}: {
  leftTicker: string;
  rightTicker: string;
  description: string;
}) {
  const href = `/compare?left=${encodeURIComponent(leftTicker)}&right=${encodeURIComponent(rightTicker)}`;

  return (
    <a
      className="comparison-suggestion-link"
      href={href}
      data-comparison-suggestion-left={leftTicker}
      data-comparison-suggestion-right={rightTicker}
      data-comparison-suggestion-url={href}
    >
      <strong>
        {leftTicker} vs {rightTicker}
      </strong>
      <span>{description}</span>
    </a>
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

function StockEtfRelationshipSection({
  model,
  citationsById
}: {
  model: StockEtfRelationshipModel;
  citationsById: Map<string, ComparisonCitation>;
}) {
  return (
    <section
      className="plain-panel stock-etf-relationship"
      aria-labelledby="stock-etf-relationship"
      data-prd-section="stock_vs_etf_relationship_context"
      data-stock-etf-relationship-schema={model.schema_version}
      data-stock-etf-comparison-type={model.comparison_type}
      data-stock-etf-stock-ticker={model.stock_ticker}
      data-stock-etf-etf-ticker={model.etf_ticker}
      data-stock-etf-relationship-state={model.relationship_state}
      data-stock-etf-evidence-state={model.evidence_state}
    >
      <div className="section-heading">
        <p className="eyebrow">Stock-vs-ETF relationship</p>
        <h2 id="stock-etf-relationship">Single company vs ETF basket</h2>
      </div>

      <div className="relationship-badge-grid" aria-label="Relationship badges">
        {model.badges.map((badge) => (
          <article
            className="relationship-badge"
            key={badge.marker}
            data-relationship-badge={badge.marker}
            data-relationship-state={badge.relationship_state}
            data-relationship-evidence-state={badge.evidence_state}
          >
            <span>{badge.label}</span>
            <strong>{badge.value}</strong>
            {badge.citation_ids.length > 0 ? (
              <span className="chip-row">
                {badge.citation_ids.map((citationId) => {
                  const citation = citationsById.get(citationId);
                  return citation ? (
                    <CitationChip key={citationId} citation={comparisonCitationToChip(citation)} label={citationId} />
                  ) : null;
                })}
              </span>
            ) : null}
          </article>
        ))}
      </div>

      <div
        className="stock-etf-basket-structure"
        data-stock-etf-basket-structure="single-company-vs-etf-basket"
        data-stock-etf-overlap-state={model.basket_structure.overlap_or_membership_state}
        data-stock-etf-basket-evidence-state={model.basket_structure.evidence_state}
      >
        <article>
          <span>{model.basket_structure.stock_ticker}</span>
          <h3>Single company</h3>
          <p>{model.basket_structure.stock_role_summary}</p>
        </article>
        <article>
          <span>{model.basket_structure.etf_ticker}</span>
          <h3>ETF basket</h3>
          <p>{model.basket_structure.etf_basket_summary}</p>
        </article>
        <article className="relationship-summary">
          <span>Relationship</span>
          <h3>Verified holding membership, partial overlap evidence</h3>
          <p>{model.basket_structure.relationship_summary}</p>
          {model.basket_structure.unavailable_detail ? (
            <p className="source-gap-note">{model.basket_structure.unavailable_detail}</p>
          ) : null}
          <span className="chip-row">
            {model.basket_structure.citation_ids.map((citationId) => {
              const citation = citationsById.get(citationId);
              return citation ? (
                <CitationChip key={citationId} citation={comparisonCitationToChip(citation)} label={citationId} />
              ) : null;
            })}
          </span>
        </article>
      </div>
    </section>
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

function normalizeCompareParam(value?: string) {
  const normalized = value?.trim().toUpperCase();
  return normalized ? normalized : null;
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
