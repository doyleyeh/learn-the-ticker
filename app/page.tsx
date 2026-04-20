import { SearchBox } from "../components/SearchBox";
import { assetFixtures, unsupportedAssets } from "../lib/fixtures";

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
        <SearchBox assets={assetFixtures} unsupportedAssets={unsupportedAssets} />
      </section>
      <section className="content-band">
        <div className="section-heading">
          <p className="eyebrow">Example states</p>
          <h2>Try supported, unsupported, and unknown searches</h2>
        </div>
        <div className="example-grid" aria-label="Example ticker searches">
          <a className="example-card" href="/assets/VOO">
            <strong>VOO</strong>
            <span>ETF page with source-backed beginner summary</span>
          </a>
          <a className="example-card" href="/assets/AAPL">
            <strong>AAPL</strong>
            <span>Stock page with company-specific risk framing</span>
          </a>
          <span className="example-card muted-card">
            <strong>BTC</strong>
            <span>Unsupported crypto scope message in search</span>
          </span>
          <span className="example-card muted-card">
            <strong>ZZZZ</strong>
            <span>Unknown ticker state with no invented facts</span>
          </span>
        </div>
      </section>
    </main>
  );
}
