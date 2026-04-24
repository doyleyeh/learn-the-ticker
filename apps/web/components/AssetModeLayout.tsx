import type { ReactNode } from "react";
import type { AssetFixture } from "../lib/fixtures";

type AssetModeLayoutProps = {
  asset: AssetFixture;
  beginnerMode: ReactNode;
  deepDiveMode: ReactNode;
  afterDeepDive: ReactNode;
  sourceTools: ReactNode;
  helperRail: ReactNode;
  footerContent: ReactNode;
};

export function AssetModeLayout({
  asset,
  beginnerMode,
  deepDiveMode,
  afterDeepDive,
  sourceTools,
  helperRail,
  footerContent
}: AssetModeLayoutProps) {
  const beginnerHeadingId = `beginner-mode-${asset.ticker.toLowerCase()}`;
  const deepDiveHeadingId = `deep-dive-mode-${asset.ticker.toLowerCase()}`;
  const sourcesHeadingId = `asset-sources-${asset.ticker.toLowerCase()}`;

  return (
    <section
      className="content-band two-column asset-mode-layout"
      data-asset-mode-layout
      data-asset-ticker={asset.ticker}
      data-prd-learning-flow="supported-asset-page-v1"
      data-prd-section-order="beginner_summary,top_risks,key_facts,what_it_does_or_holds,weekly_news_focus,ai_comprehensive_analysis,deep_dive,ask_about_this_asset,sources,educational_disclaimer"
    >
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

      <div className="section-stack mode-stack" data-asset-prd-content-flow>
        <section
          className="asset-mode-region beginner-mode-region"
          aria-labelledby={beginnerHeadingId}
          data-asset-mode-region="beginner"
          data-beginner-mode-region={asset.ticker}
        >
          <div className="mode-heading">
            <p className="eyebrow">Beginner Mode</p>
            <h2 id={beginnerHeadingId}>Beginner Mode</h2>
          </div>
          {beginnerMode}
        </section>

        <section
          className="asset-mode-region deep-dive-mode-region"
          aria-labelledby={deepDiveHeadingId}
          data-asset-mode-region="deep-dive"
          data-deep-dive-mode-region={asset.ticker}
        >
          <div className="mode-heading">
            <p className="eyebrow">Deep-Dive Mode</p>
            <h2 id={deepDiveHeadingId}>Deep-Dive Mode</h2>
          </div>
          {deepDiveMode}
        </section>

        {afterDeepDive}

        <section
          id="asset-sources"
          className="asset-mode-region asset-source-region"
          aria-labelledby={sourcesHeadingId}
          data-prd-section="sources"
          data-asset-source-region={asset.ticker}
        >
          <div className="mode-heading">
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
