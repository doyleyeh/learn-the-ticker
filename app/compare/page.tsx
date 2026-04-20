import { CitationChip } from "../../components/CitationChip";
import { FreshnessLabel } from "../../components/FreshnessLabel";
import { SourceDrawer } from "../../components/SourceDrawer";
import { compareFixture, getAssetFixture, getPrimarySource } from "../../lib/fixtures";

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
  const left = getAssetFixture(leftTicker) ?? getAssetFixture("VOO")!;
  const right = getAssetFixture(rightTicker) ?? getAssetFixture("QQQ")!;

  return (
    <main>
      <section className="asset-hero">
        <p className="eyebrow">Fixture-backed comparison</p>
        <h1>
          {left.ticker} vs {right.ticker}
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
          <article className="compare-column">
            <h2>{left.name}</h2>
            <p>{left.beginnerSummary.whatItIs}</p>
            <dl className="fact-list compact">
              {left.facts.slice(0, 4).map((fact) => (
                <div key={fact.label}>
                  <dt>{fact.label}</dt>
                  <dd>{fact.value}</dd>
                </div>
              ))}
            </dl>
          </article>
          <article className="compare-column">
            <h2>{right.name}</h2>
            <p>{right.beginnerSummary.whatItIs}</p>
            <dl className="fact-list compact">
              {right.facts.slice(0, 4).map((fact) => (
                <div key={fact.label}>
                  <dt>{fact.label}</dt>
                  <dd>{fact.value}</dd>
                </div>
              ))}
            </dl>
          </article>
        </div>

        <section className="plain-panel" aria-labelledby="differences">
          <div className="section-heading">
            <p className="eyebrow">Key differences</p>
            <h2 id="differences">Plain-English comparison</h2>
          </div>
          <div className="difference-list">
            {compareFixture.keyDifferences.map((difference) => (
              <article className="difference-item" key={difference.dimension}>
                <h3>{difference.dimension}</h3>
                <p>{difference.plainEnglishSummary}</p>
                <span className="chip-row">
                  {difference.citationIds.map((citationId) => (
                    <CitationChip
                      key={citationId}
                      citation={citationId.startsWith("c_voo") ? left.citations[0] : right.citations[0]}
                      label={citationId}
                    />
                  ))}
                </span>
              </article>
            ))}
          </div>
        </section>

        <section className="plain-panel bottom-line" aria-labelledby="bottom-line">
          <p className="eyebrow">Bottom line for beginners</p>
          <h2 id="bottom-line">Educational context, not a decision rule</h2>
          <p>{compareFixture.bottomLineForBeginners.summary}</p>
          <span className="chip-row">
            {compareFixture.bottomLineForBeginners.citationIds.map((citationId) => (
              <CitationChip
                key={citationId}
                citation={citationId.startsWith("c_voo") ? left.citations[0] : right.citations[0]}
                label={citationId}
              />
            ))}
          </span>
        </section>

        <SourceDrawer source={getPrimarySource(left)} claim={compareFixture.keyDifferences[0].plainEnglishSummary} />
      </section>
    </main>
  );
}
