import type { ReactNode } from "react";
import type { AssetFixture } from "../lib/fixtures";

type AssetLearningLayoutProps = {
  asset: AssetFixture;
  beginnerSections: ReactNode;
  deepDiveSections: ReactNode;
  afterDeepDive: ReactNode;
  sourceTools: ReactNode;
  helperRail: ReactNode;
  footerContent: ReactNode;
};

export function AssetLearningLayout({
  asset,
  beginnerSections,
  deepDiveSections,
  afterDeepDive,
  sourceTools,
  helperRail,
  footerContent
}: AssetLearningLayoutProps) {
  const learningFlowLabelId = `asset-learning-flow-${asset.ticker.toLowerCase()}`;
  const deepDiveHeadingId = `deep-dive-${asset.ticker.toLowerCase()}`;
  const sourcesHeadingId = `asset-sources-${asset.ticker.toLowerCase()}`;

  return (
    <section
      className="content-band two-column asset-learning-layout"
      aria-labelledby={learningFlowLabelId}
      data-asset-learning-layout
      data-asset-ticker={asset.ticker}
      data-prd-learning-flow="supported-asset-page-v1"
      data-prd-section-order="beginner_summary,top_risks,key_facts,what_it_does_or_holds,weekly_news_focus,ai_comprehensive_analysis,deep_dive,ask_about_this_asset,sources,educational_disclaimer"
    >
      <h2 id={learningFlowLabelId} className="sr-only">
        Asset learning flow
      </h2>
      <nav
        className="asset-mobile-actions"
        aria-label="Asset page quick actions"
        data-mobile-sticky-actions="ask-compare-sources"
        data-mobile-actions-no-overlap="in-flow-sticky"
      >
        <a href="#ask-about-this-asset" data-mobile-action="ask">
          Ask
        </a>
        <a href="#compare-this-asset" data-mobile-action="compare">
          Compare
        </a>
        <a href="#asset-sources" data-mobile-action="sources">
          Sources
        </a>
      </nav>

      <div className="section-stack learning-stack" data-asset-prd-content-flow>
        <section
          className="asset-section-region beginner-section-region"
          aria-label="Beginner learning sections"
          data-asset-section-region="beginner"
          data-beginner-section-region={asset.ticker}
        >
          {beginnerSections}
        </section>

        <section
          className="asset-section-region deep-dive-section-region"
          aria-labelledby={deepDiveHeadingId}
          data-asset-section-region="deep-dive"
          data-deep-dive-section-region={asset.ticker}
          data-prd-section="deep_dive"
        >
          <div className="section-shell-heading">
            <p className="eyebrow">More detail</p>
            <h2 id={deepDiveHeadingId}>Deep Dive</h2>
          </div>
          {deepDiveSections}
        </section>

        {afterDeepDive}

        <section
          id="asset-sources"
          className="asset-section-region asset-source-region"
          aria-labelledby={sourcesHeadingId}
          data-prd-section="sources"
          data-asset-source-region={asset.ticker}
        >
          <div className="section-shell-heading">
            <p className="eyebrow">Sources</p>
            <h2 id={sourcesHeadingId}>Sources</h2>
          </div>
          {sourceTools}
        </section>

        {footerContent}
      </div>

      <aside
        className="sidebar asset-helper-rail"
        aria-label="Asset helper rail"
        data-asset-helper-rail
        data-helper-rail-tools="ask,compare,freshness,sources"
      >
        {helperRail}
      </aside>
    </section>
  );
}
