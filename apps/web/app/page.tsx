import { SearchBox } from "../components/SearchBox";

export default function HomePage() {
  return (
    <main>
      <section className="hero-band">
        <div className="hero-copy">
          <p className="eyebrow">Beginner asset learning</p>
          <h1>Search a U.S. stock or plain-vanilla ETF.</h1>
          <p>
            Start with deterministic local examples, then open a fixture-backed
            asset page with citations, freshness labels, risks, recent context,
            and glossary help.
          </p>
        </div>
        <SearchBox />
      </section>
      <section className="content-band">
        <div className="section-heading">
          <p className="eyebrow">Example states</p>
          <h2>Try supported, ambiguous, ingestion-needed, blocked, and unknown searches</h2>
        </div>
        <div className="example-grid" aria-label="Example ticker searches">
          <a className="example-card" href="/assets/VOO">
            <strong>VOO</strong>
            <span>ETF page with source-backed beginner summary</span>
          </a>
          <span className="example-card muted-card" data-home-search-example-state="ambiguous">
            <strong>S&amp;P 500 ETF</strong>
            <span>Ambiguous search that requires choosing between deterministic candidates</span>
          </span>
          <span className="example-card muted-card" data-home-search-example-state="ingestion_needed">
            <strong>SPY</strong>
            <span>Eligible but not locally cached, so ingestion is still needed</span>
          </span>
          <span className="example-card muted-card" data-home-search-example-state="unsupported">
            <strong>BTC</strong>
            <span>Recognized unsupported crypto scope message in search</span>
          </span>
          <span className="example-card muted-card" data-home-search-example-state="out_of_scope">
            <strong>GME</strong>
            <span>Recognized stock outside the current Top-500 manifest-backed MVP scope</span>
          </span>
          <span className="example-card muted-card" data-home-search-example-state="unknown">
            <strong>ZZZZ</strong>
            <span>Unknown ticker state with no invented facts</span>
          </span>
        </div>
      </section>
    </main>
  );
}
