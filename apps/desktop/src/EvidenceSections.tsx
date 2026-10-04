import { useState, type ReactNode } from "react";
import type { Claim, EvidenceBundle } from "./contracts";

type Section = { id: string; title: string; aliases: string[]; risk?: boolean };
const common: Section[] = [
  { id: "overview", title: "Overview", aliases: ["overview"] },
  { id: "business_model", title: "Business model", aliases: ["business_model", "business_overview"] },
  { id: "financial_trends", title: "Financial trends and quality", aliases: ["financial_trends", "financial_quality"] },
  { id: "valuation", title: "Valuation context", aliases: ["valuation", "valuation_context"] },
  { id: "risks", title: "Risks and uncertainty", aliases: ["risks", "top_risks", "etf_specific_risks"], risk: true },
];
const fund: Section[] = [
  common[0], { id: "business_model", title: "Fund objective and role", aliases: ["business_model", "fund_objective_role"] },
  { id: "holdings", title: "Holdings and exposures", aliases: ["holdings", "holdings_exposure"] },
  { id: "construction", title: "Fund construction", aliases: ["construction_methodology"] },
  { id: "costs", title: "Costs and trading context", aliases: ["cost_trading_context"] },
  common[2], common[3], common[4],
];
export const contextSections = ["weekly_news", "earlier_context", "historical_research", "recent_developments"];

export function EvidenceSections({ bundle, renderClaim }: { bundle: EvidenceBundle; renderClaim: (claim: Claim) => ReactNode }) {
  const type = bundle.asset.asset_type;
  const uncertain = type === "unknown";
  const sections = type === "etf" || type === "fund" ? fund : type === "stock" ? [common[0], common[1],
    { id: "products", title: "Products and services", aliases: ["products_services"] },
    { id: "strengths", title: "Reported business strengths", aliases: ["strengths"] }, ...common.slice(2)] :
    uncertain ? [common[0]] : [common[0], { ...common[1], title: "Asset characteristics" }, ...common.slice(2)];
  const used = new Set(sections.flatMap((section) => section.aliases).concat(contextSections));
  const claims = bundle.claims ?? [];
  const extras: Section[] = uncertain ? [] : [...new Set(claims.map((claim) => claim.section ?? "overview"))]
    .filter((section) => !used.has(section)).map((section) => ({ id: section, title: section.replaceAll("_", " "), aliases: [section] }));
  return <>
    {uncertain && <p className="notice-text">Asset type is unconfirmed. Type-dependent sections are unavailable until identity is resolved.</p>}
    <div className="library-grid" data-evidence-layer="canonical">{[...sections, ...extras].map((section) => <EvidenceSection key={`${bundle.id}:${section.id}`} section={section}
      claims={claims.filter((claim) => section.aliases.includes(claim.section ?? "overview"))} renderClaim={renderClaim}/>)}</div>
  </>;
}

function EvidenceSection({ section, claims, renderClaim }: { section: Section; claims: Claim[]; renderClaim: (claim: Claim) => ReactNode }) {
  const [expanded, setExpanded] = useState(false);
  const visible = section.risk && !expanded ? claims.slice(0, 3) : claims;
  return <section className="plain-panel"><h2>{section.title}</h2>
    {visible.length ? visible.map(renderClaim) : <p className="source-gap-note">Unavailable — no admitted evidence for this section.</p>}
    {section.risk && claims.length > 3 && <button aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? "Show fewer risks" : `Show ${claims.length - 3} more risks`}</button>}
  </section>;
}
