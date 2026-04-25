import { SearchBox } from "../components/SearchBox";

export default function HomePage() {
  return (
    <main data-home-workflow-baseline="single-asset-search-first">
      <section className="hero-band" data-home-primary-workflow="single-supported-stock-or-etf-search">
        <div className="hero-copy">
          <p className="eyebrow">Beginner asset learning</p>
          <h1>Understand a stock or ETF in plain English</h1>
          <p>
            Search a U.S. stock or non-leveraged U.S. equity ETF to see beginner-friendly explanations, source
            citations, top risks, recent context, and grounded follow-up answers.
          </p>
        </div>
        <SearchBox />
      </section>
      <section className="content-band">
        <div className="section-heading home-next-steps-heading">
          <p className="eyebrow">How the workflow stays focused</p>
          <h2>What happens next</h2>
        </div>
        <ol className="home-next-steps" aria-label="Educational secondary workflows" data-home-secondary-workflow="lightweight-next-steps">
          <li data-home-workflow-card="single-asset-search">
            <strong>Open one supported asset.</strong>
            Search rows identify stock vs ETF results, exchange or issuer, and support-state chips before opening a generated page.
          </li>
          <li data-home-workflow-card="separate-comparison">
            <strong>Compare only when asked.</strong>
            Clear searches like VOO vs QQQ route to <a href="/compare">the comparison workflow</a>.
          </li>
          <li data-home-workflow-card="source-backed-learning">
            <strong>Keep reading with sources.</strong>
            Asset pages keep citations, freshness, contextual glossary help, chat, and Weekly News Focus in the learning flow.
          </li>
        </ol>
      </section>
    </main>
  );
}
