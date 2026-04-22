import { CitationChip } from "../../components/CitationChip";
import { ComparisonSourceDetails } from "../../components/ComparisonSourceDetails";
import { ExportControls } from "../../components/ExportControls";
import { FreshnessLabel } from "../../components/FreshnessLabel";
import { getComparePageFixture, getComparisonCitationMetadata, type CompareAssetIdentity } from "../../lib/compare";
import { comparisonExportUrl } from "../../lib/exportControls";
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
  const comparison = getComparePageFixture(leftTicker, rightTicker);
  const leftFixture = getAssetFixture(comparison.leftAsset.ticker);
  const rightFixture = getAssetFixture(comparison.rightAsset.ticker);
  const { citationsById, contextsBySourceDocumentId } = getComparisonCitationMetadata(comparison);
  const bottomLine = comparison.bottomLineForBeginners;
  const hasSourceBackedComparison =
    comparison.state.status === "supported" &&
    comparison.keyDifferences.length > 0 &&
    bottomLine !== null;

  return (
    <main>
      <section className="asset-hero">
        <p className="eyebrow">Fixture-backed comparison</p>
        <h1>
          {comparison.leftAsset.ticker} vs {comparison.rightAsset.ticker}
        </h1>
        <p>
          This page compares deterministic local fixtures for broad-market exposure, concentration, costs, and beginner
          learning context. It does not make a personal recommendation.
        </p>
        <div className="freshness-row">
          <FreshnessLabel label="Comparison data as of" value="2026-04-01" state="fresh" />
          <FreshnessLabel label="Live quotes" value="Unavailable in skeleton" state="unknown" />
        </div>
      </section>

      <section className="content-band">
        <div className="compare-grid" aria-label="VOO and QQQ deterministic comparison">
          <CompareColumn asset={comparison.leftAsset} fixture={leftFixture} />
          <CompareColumn asset={comparison.rightAsset} fixture={rightFixture} />
        </div>

        {hasSourceBackedComparison && bottomLine ? (
          <>
            <ExportControls
              title={`Save ${comparison.leftAsset.ticker} vs ${comparison.rightAsset.ticker} comparison`}
              marker={`comparison-export-${comparison.leftAsset.ticker.toLowerCase()}-${comparison.rightAsset.ticker.toLowerCase()}`}
              helper="Save the deterministic comparison export with cited differences, source metadata, freshness context, the educational disclaimer, and licensing scope."
              controls={[
                {
                  kind: "link",
                  controlId: "comparison",
                  label: "Open comparison Markdown export",
                  href: comparisonExportUrl(comparison.leftAsset.ticker, comparison.rightAsset.ticker),
                  helper: "Uses the local comparison export route for this supported fixture-backed pair."
                }
              ]}
            />

            <section className="plain-panel" aria-labelledby="differences">
              <div className="section-heading">
                <p className="eyebrow">Key differences</p>
                <h2 id="differences">Plain-English comparison</h2>
              </div>
              <div className="difference-list">
                {comparison.keyDifferences.map((difference) => (
                  <article className="difference-item" key={difference.dimension}>
                    <h3>{difference.dimension}</h3>
                    <p>{difference.plainEnglishSummary}</p>
                    <span className="chip-row">
                      {difference.citationIds.map((citationId) => {
                        const citation = citationsById.get(citationId);
                        return citation ? <CitationChip key={citationId} citation={citation} label={citationId} /> : null;
                      })}
                    </span>
                  </article>
                ))}
              </div>
            </section>

            <section className="plain-panel bottom-line" aria-labelledby="bottom-line">
              <p className="eyebrow">Bottom line for beginners</p>
              <h2 id="bottom-line">Educational context, not a decision rule</h2>
              <p>{bottomLine.summary}</p>
              <span className="chip-row">
                {bottomLine.citationIds.map((citationId) => {
                  const citation = citationsById.get(citationId);
                  return citation ? <CitationChip key={citationId} citation={citation} label={citationId} /> : null;
                })}
              </span>
            </section>

            <section className="plain-panel" aria-labelledby="comparison-sources">
              <div className="section-heading">
                <p className="eyebrow">Comparison source metadata</p>
                <h2 id="comparison-sources">Sources behind these citations</h2>
              </div>
              <div className="section-stack" aria-label="Comparison source metadata">
                {comparison.sourceDocuments.map((sourceDocument) => (
                  <ComparisonSourceDetails
                    key={sourceDocument.sourceDocumentId}
                    sourceDocument={sourceDocument}
                    contexts={contextsBySourceDocumentId.get(sourceDocument.sourceDocumentId) ?? []}
                  />
                ))}
              </div>
            </section>
          </>
        ) : (
          <section className="plain-panel unknown-state" aria-labelledby="comparison-unavailable">
            <div className="section-heading">
              <p className="eyebrow">
                {comparison.state.status === "unsupported" ? "Unsupported comparison" : "Insufficient evidence"}
              </p>
              <h2 id="comparison-unavailable">Comparison evidence unavailable</h2>
            </div>
            <FreshnessLabel label="Comparison source pack" value="Unavailable in local fixtures" state="unavailable" />
            <p>{comparison.state.message}</p>
            <p className="notice-text">
              No factual citation chips or source drawers are shown because this local fixture has no source-backed
              comparison pack for the requested pair.
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
    <article className="compare-column">
      <h2>{asset.name}</h2>
      <p>
        {fixture?.beginnerSummary.whatItIs ??
          "Unknown in the local skeleton data. No facts are invented for assets without fixture-backed evidence."}
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
