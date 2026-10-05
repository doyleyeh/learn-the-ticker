import { useMemo, type ReactNode } from "react";
import type { Claim, EvidenceBundle, Source } from "./contracts";
import { CitationChip } from "../components/CitationChip";
import { EvidenceSections, contextSections } from "./EvidenceSections";
import { FinancialHistory, ObservationCitation } from "./FinancialHistory";
import { MarketHistory } from "./MarketHistory";
import { FinancialRatios } from "./FinancialRatios";
import { ValuationAvailability } from "./ValuationAvailability";
import { ProviderValuations } from "./ProviderValuations";
import { privateClaims, privateSource } from "./marketPresentation";
import { concepts, displayNumber, financialSeries } from "./financialSeries";
import { sourceRoute } from "./routes";

const sections = [
  ["overview", "Overview"], ["prices", "Charts & returns"], ["statistics", "Statistics"],
  ["financials", "Financials"], ["news", "News & context"], ["analysts", "Analyst insights"],
  ["sources", "Sources"], ["learning", "Learn about this ticker"],
];

function goToSection(id: string) {
  const section = document.getElementById(`ticker-${id}`);
  section?.focus({ preventScroll: true });
  section?.scrollIntoView({ block: "start" });
}

function DashboardSection({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return <section id={`ticker-${id}`} tabIndex={-1} aria-labelledby={`ticker-${id}-title`} className="ticker-section">
    <h2 id={`ticker-${id}-title`}>{title}</h2>{children}
  </section>;
}

export function EvidenceView({ bundle }: { bundle: EvidenceBundle }) {
  const sources = useMemo(() => new Map((bundle.sources ?? []).map((source) => [source.id, source])), [bundle.sources]);
  const references = useMemo(() => new Map((bundle.context_references ?? []).map((ref) => [ref.id, ref])), [bundle.context_references]);
  const privateIds = useMemo(() => privateClaims(bundle), [bundle]);
  const privateContent = Boolean(bundle.market || bundle.context_references?.length || bundle.sources?.some(privateSource));
  function renderClaim(claim: Claim) {
    return <article key={claim.id} data-local-only={privateIds.has(claim.id) || undefined}><p>{claim.text}</p><div className="chip-row">{claim.source_ids?.map((id) => {
      const source = sources.get(id);
      const ref = references.get(id);
      if (ref) return <CitationChip key={id} href={`#${sourceRoute(ref.bundle_id, ref.source_id)}`} label="Original saved evidence" citation={{ citationId: id, sourceDocumentId: ref.source_id, title: "Original saved numerical evidence", publisher: "Original provider", freshnessState: "unknown" }}/>;
      return source ? <div key={id}><CitationChip href={`#${sourceRoute(bundle.id!, id)}`} citation={{ citationId: id, sourceDocumentId: id, title: source.title, publisher: source.publisher, freshnessState: "unknown" }}/><p className="ticker-meta">Published {source.published_at ?? "unknown"} · As of {source.as_of ?? "unknown"} · Retrieved {source.retrieved_at ?? "unknown"}</p></div> : null;
    })}</div></article>;
  }
  const asset = bundle.asset;
  return <div className="ticker-dashboard">
    <aside className="ticker-navigation"><p className="eyebrow">Explore {asset.symbol}</p><nav aria-label="Ticker sections">{sections.map(([id, title]) => <button key={id} type="button" onClick={() => goToSection(id)}>{title}</button>)}</nav></aside>
    <div className="ticker-content">
      <DashboardSection id="overview" title="Ticker overview">
        <div className="plain-panel"><h3>Basic listing information</h3><dl className="ticker-facts">
          <div><dt>Symbol</dt><dd>{asset.symbol}</dd></div><div><dt>Asset type</dt><dd>{asset.asset_type === "unknown" ? "Unconfirmed" : asset.asset_type}</dd></div>
          <div><dt>Exchange / venue</dt><dd>{asset.exchange ?? "Unconfirmed"}</dd></div><div><dt>Listing currency</dt><dd>{asset.currency ?? "Unconfirmed"}</dd></div>
        </dl>{bundle.identity_verification ? <p className="ticker-meta"><a href={bundle.identity_verification.source_url} target="_blank" rel="noopener noreferrer">Original identity source</a> · {bundle.identity_verification.authority} · Checked {bundle.identity_verification.retrieved_at}</p> : <p className="source-gap-note">Original identity verification is not recorded in this snapshot.</p>}
          <p className="ticker-meta">Evidence saved {bundle.created_at ?? "at an unknown time"}. A saved or recently retrieved page does not establish current market data.</p>
        </div>
        <EvidenceSections bundle={bundle} renderClaim={renderClaim}/>
      </DashboardSection>
      <DashboardSection id="prices" title="Charts and returns"><MarketHistory bundle={bundle}/></DashboardSection>
      <DashboardSection id="statistics" title="Key statistics"><KeyStatistics bundle={bundle}/></DashboardSection>
      <DashboardSection id="financials" title="Reported financials"><FinancialHistory key={bundle.id} bundle={bundle} includePriceAvailability={false}/></DashboardSection>
      <DashboardSection id="news" title="Ticker news and context">
        <p>Current ticker news: unavailable. The dated evidence below is retained research; it is not a complete or live news feed.</p>
        <div className="library-grid" data-evidence-layer="context">{contextSections.map((section) => {
          const claims = bundle.claims?.filter((claim) => claim.section === section) ?? [];
          return <section className="plain-panel" key={section}><h3>{section === "recent_developments" ? "Other reported developments" : section.replaceAll("_", " ")}</h3>{claims.length ? claims.map(renderClaim) : <p className="source-gap-note">Unavailable — no admitted evidence for this section.</p>}</section>;
        })}</div>
      </DashboardSection>
      <DashboardSection id="analysts" title="Analyst insights"><div className="plain-panel"><p className="source-gap-note">Unavailable — this snapshot has no qualified analyst estimates or outlooks.</p><p>External estimates are opinions about the future, separate from reported results. Missing estimates are not inferred from prices or generated explanations.</p></div></DashboardSection>
      <DashboardSection id="sources" title="Sources and evidence">
        <div className="plain-panel">{[...sources.values()].map((source) => <SourceDetails source={source} key={source.id}/>)}{!sources.size && <p>No source documents have been registered.</p>}</div>
        <section className="plain-panel" data-evidence-layer="notes" data-local-only={privateContent || undefined}><h3>Unverified research notes</h3><p>These explanations have not passed factual validation. Candidate citations may be incomplete. These notes do not feed facts, charts or calculations.</p>{bundle.notes?.map(renderClaim)}{!bundle.notes?.length && <p>No unverified notes.</p>}</section>
      </DashboardSection>
    </div>
  </div>;
}

export function KeyStatistics({ bundle }: { bundle: EvidenceBundle }) {
  const { series, sources, excluded } = useMemo(() => financialSeries(bundle), [bundle]);
  return <div className="plain-panel"><p>Reported issuer figures by concept, unit and period. These are historical observations, not a current quote, trailing-twelve-month estimate or forecast.</p>
    <ProviderValuations bundle={bundle}/><ValuationAvailability bundle={bundle}/>
    {excluded > 0 && <p className="error">Some figures are hidden because their numeric source references could not be validated.</p>}
    {!series.length && <p className="source-gap-note">Unavailable — no independently admitted financial statistics.</p>}
    <div className="ticker-statistics">{series.map((value) => {
      const latest = value.points.at(-1);
      // Never substitute an older figure for an unresolved most recent period.
      const last = value.rows.at(-1);
      const usable = latest && latest.row.end === last?.end && latest.row.start === last.start;
      return <article key={value.key}><h3>{concepts[value.concept].label}</h3><p className="ticker-meta">{value.period.replaceAll("_", " ")} · {value.unit}</p>
        {usable ? <><p className="financial-value">{displayNumber(latest.row.value)} <span>{latest.row.unit}</span></p><p>{latest.row.start ? `${latest.row.start} through ${latest.row.end}` : `As of ${latest.row.end}`}</p>
          {latest.citations.map((row) => <ObservationCitation key={row.id} row={row} bundle={bundle} source={sources.get(row.source_id)!}/>)}
        </> : <p className="source-gap-note">Latest period unavailable — conflicting or superseded evidence. Inspect all retained filing versions in Financials.</p>}
        <p className="ticker-meta">Source concept: {value.concept}</p>
      </article>;
    })}</div><FinancialRatios bundle={bundle}/>
  </div>;
}

function SourceDetails({ source }: { source: Source }) {
  const restricted = privateSource(source);
  return <details className="source-drawer" id={`source-${source.id}`} data-local-only={restricted || undefined}><summary>{source.title} · {source.verified ? "Verified retrieval" : "Unverified candidate"}</summary><p>{source.publisher}</p><a href={source.url} target="_blank" rel="noopener noreferrer">Inspect original source</a><p>Published: {source.published_at ?? "Unknown"} · As of: {source.as_of ?? "Unknown"} · Retrieved: {source.retrieved_at}</p><p>Source-use policy: {source.policy} · Provenance: {source.provenance}</p>{restricted && <p>Experimental private numerical use only. Admitted numerical observations support consented cloud learning with their original citations. Shareable exports omit Yahoo data.</p>}{source.content_hash && <details><summary>Original response fingerprint</summary><p>{source.content_hash}</p></details>}{source.excerpt && <blockquote>{source.excerpt}</blockquote>}</details>;
}
