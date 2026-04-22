import { notFound } from "next/navigation";
import { AssetHeader } from "../../../components/AssetHeader";
import { AssetChatPanel } from "../../../components/AssetChatPanel";
import { AssetEtfSections } from "../../../components/AssetEtfSections";
import { AssetStockSections } from "../../../components/AssetStockSections";
import { CitationChip } from "../../../components/CitationChip";
import { FreshnessLabel } from "../../../components/FreshnessLabel";
import { GlossaryPopover } from "../../../components/GlossaryPopover";
import { SourceDrawer } from "../../../components/SourceDrawer";
import {
  assetFixtures,
  citationLabel,
  getCitationContextsForSource,
  getAssetFixture,
  getPrimarySource
} from "../../../lib/fixtures";

type AssetPageProps = {
  params: Promise<{
    ticker: string;
  }>;
};

export function generateStaticParams() {
  return Object.keys(assetFixtures).map((ticker) => ({ ticker }));
}

export default async function AssetPage({ params }: AssetPageProps) {
  const { ticker } = await params;
  const asset = getAssetFixture(ticker);

  if (!asset) {
    notFound();
  }

  const primarySource = getPrimarySource(asset);
  const firstClaim = asset.claims[0];
  const hasStockPrdSections = asset.assetType === "stock" && Boolean(asset.stockSections?.length);
  const hasEtfPrdSections = asset.assetType === "etf" && Boolean(asset.etfSections?.length);
  const hasPrdSections = hasStockPrdSections || hasEtfPrdSections;
  const sectionSourceDocumentIds = new Set(
    [...(asset.stockSections ?? []), ...(asset.etfSections ?? [])].flatMap((section) => section.sourceDocumentIds)
  );
  const sectionSources = asset.sourceDocuments.filter((source) => sectionSourceDocumentIds.has(source.sourceDocumentId));

  return (
    <main>
      <AssetHeader asset={asset} />
      <section className="content-band two-column">
        <div className="section-stack">
          <section className="plain-panel">
            <div className="section-heading">
              <p className="eyebrow">Stable facts</p>
              <h2>Beginner overview</h2>
            </div>
            <p>
              {asset.beginnerSummary.whatItIs}{" "}
              <CitationChip citation={asset.citations[0]} />
            </p>
            <p>{asset.beginnerSummary.whyPeopleConsiderIt}</p>
            <p className="notice-text">{asset.beginnerSummary.mainCatch}</p>
            <div className="inline-tools">
              <GlossaryPopover term="expense ratio" />
              <GlossaryPopover term={asset.assetType === "etf" ? "index tracking" : "market risk"} />
            </div>
          </section>

          <AssetChatPanel ticker={asset.ticker} assetName={asset.name} />

          {hasStockPrdSections ? (
            <AssetStockSections asset={asset} />
          ) : hasEtfPrdSections ? (
            <AssetEtfSections asset={asset} />
          ) : (
            <>
              <section className="plain-panel" aria-labelledby="top-risks">
                <div className="section-heading">
                  <p className="eyebrow">Exactly three shown first</p>
                  <h2 id="top-risks">Top risks</h2>
                </div>
                <div className="risk-grid" data-risk-count={asset.topRisks.length}>
                  {asset.topRisks.map((risk) => (
                    <article className="risk-card" key={risk.title}>
                      <h3>{risk.title}</h3>
                      <p>{risk.plainEnglishExplanation}</p>
                      <CitationChip citation={asset.citations[0]} label={citationLabel(risk.citationIds[0])} />
                    </article>
                  ))}
                </div>
              </section>

              <section className="plain-panel stable-section" aria-labelledby="details">
                <div className="section-heading">
                  <p className="eyebrow">What this is</p>
                  <h2 id="details">{asset.assetType === "etf" ? "Fund facts" : "Business facts"}</h2>
                </div>
                <dl className="fact-list">
                  {asset.facts.map((fact) => (
                    <div key={fact.label}>
                      <dt>{fact.label}</dt>
                      <dd>
                        {fact.value}{" "}
                        {fact.citationId ? (
                          <CitationChip citation={asset.citations[0]} label={citationLabel(fact.citationId)} />
                        ) : null}
                      </dd>
                    </div>
                  ))}
                </dl>
              </section>

              <section className="plain-panel recent-section" aria-labelledby="recent">
                <div className="section-heading">
                  <p className="eyebrow">Recent developments</p>
                  <h2 id="recent">Separate from stable facts</h2>
                </div>
                <FreshnessLabel label="Recent developments checked" value={asset.freshness.recentEventsAsOf} state="fresh" />
                {asset.recentDevelopments.map((item) => (
                  <article className="timeline-item" key={item.title}>
                    <h3>{item.title}</h3>
                    <p>{item.summary}</p>
                    <CitationChip citation={asset.citations[0]} label={citationLabel(item.citationIds[0])} />
                  </article>
                ))}
              </section>

              <section className="plain-panel unknown-state" aria-labelledby="unknowns">
                <div className="section-heading">
                  <p className="eyebrow">Uncertainty</p>
                  <h2 id="unknowns">Stale and unknown treatment</h2>
                </div>
                <div className="state-row">
                  <FreshnessLabel label="Valuation context" value="Unknown in local fixture" state="unknown" />
                  <FreshnessLabel label="Live market quote" value="Unavailable by design" state="stale" />
                </div>
                <p>
                  Missing live facts are labeled instead of being filled in from model memory. This skeleton uses local fixture
                  data only.
                </p>
              </section>
            </>
          )}
        </div>

        <aside className="sidebar" aria-label="Source and learning tools">
          {hasPrdSections ? null : (
            <section className="plain-panel">
              <h2>Educational framing</h2>
              <p>{asset.suitabilitySummary.mayFit}</p>
              <p>{asset.suitabilitySummary.mayNotFit}</p>
              <p>{asset.suitabilitySummary.learnNext}</p>
            </section>
          )}
          {hasPrdSections
            ? sectionSources.map((source) => (
                <SourceDrawer
                  key={source.sourceDocumentId}
                  source={source}
                  claim={getCitationContextsForSource(asset, source.sourceDocumentId)[0]?.claimContext ?? firstClaim.claimText}
                  contexts={getCitationContextsForSource(asset, source.sourceDocumentId)}
                />
              ))
            : <SourceDrawer source={primarySource} claim={firstClaim.claimText} />}
        </aside>
      </section>
    </main>
  );
}
