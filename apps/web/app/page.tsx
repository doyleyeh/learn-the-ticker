import { SearchBox } from "../components/SearchBox";

export default function HomePage() {
  return (
    <main>
      <section className="hero-band">
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
        <div className="section-heading">
          <p className="eyebrow">How the workflow stays focused</p>
          <h2>Start with one asset, then branch into sources, comparison, or follow-up learning</h2>
        </div>
        <div className="example-grid home-workflow-grid" aria-label="Educational secondary workflows">
          <span className="example-card" data-home-workflow-card="single-asset-search">
            <strong>Single search first</strong>
            <span>
              Search rows identify stock vs ETF results, exchange or issuer, and support-state chips before opening
              a generated page.
            </span>
          </span>
          <a className="example-card" href="/compare" data-home-workflow-card="separate-comparison">
            <strong>Compare separately</strong>
            <span>
              Comparison stays in its own workflow. Clear searches like VOO vs QQQ route to the comparison page.
            </span>
          </a>
          <span className="example-card" data-home-workflow-card="source-backed-learning">
            <strong>Learn with sources</strong>
            <span>
              Supported asset pages keep stable facts, Weekly News Focus, citations, freshness, glossary help, and chat
              in their reading flow.
            </span>
          </span>
        </div>
      </section>
    </main>
  );
}
