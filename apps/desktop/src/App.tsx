import { useEffect, useState, type FormEvent } from "react";
import { api, bootstrap, connect, download } from "./client";
import type { EvidenceBundle, Settings, Claim, Source, Conversation as ConversationContract, SavedResearch, ResearchRequest } from "./contracts";
import { FreshnessLabel } from "../components/FreshnessLabel";
import { CitationChip } from "../components/CitationChip";
import { bundleRoute, pages, routeFromHash, sourceRoute } from "./routes";
import { LibraryBackup } from "./LibraryBackup";
import { ImportDocuments } from "./ImportDocuments";
import { FinancialHistory } from "./FinancialHistory";
import { EvidenceSections, contextSections } from "./EvidenceSections";
import { CodexConnection } from "./CodexConnection";
import { Connections } from "./Connections";
import { AccessReview } from "./AccessReview";
import { TermLearning } from "./TermLearning";
import { ResearchJobs } from "./ResearchJobs";
import { activeResearch, observeResearch } from "./researchObservation";

type Job = { id: string; status: string; request?: ResearchRequest; error?: string; result?: EvidenceBundle & { candidates?: EvidenceBundle["asset"][]; educational_redirect?: string; message?: string } };
type Saved = SavedResearch & { id: string };
type Conversation = ConversationContract & { id: string; bookmarked: boolean; messages: NonNullable<ConversationContract["messages"]> };

export function App() {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [library, setLibrary] = useState<EvidenceBundle[]>([]);
  const [saved, setSaved] = useState<Saved[]>([]);
  const [settings, setSettings] = useState<Settings>();
  const [page, setPage] = useState(routeFromHash(location.hash).page);
  const [sourceTarget, setSourceTarget] = useState(routeFromHash(location.hash).source);
  const [notice, setNotice] = useState("");
  const [asset, setAsset] = useState<EvidenceBundle>();
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<"beginner" | "intermediate">("beginner");
  const [job, setJob] = useState<Job>();
  const [progress, setProgress] = useState("");
  const [conversation, setConversation] = useState<Conversation>();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const activeConversation = conversations.find((item) => item.id === conversation?.id) ?? conversation;
  const busy = activeResearch(job?.status ?? "");
  const fail = (error: unknown) => setError(error instanceof Error ? error.message : "The operation could not be completed.");

  async function reload() {
    const [items, preferences, reports, chats] = await Promise.all([api<EvidenceBundle[]>("/api/library"), api<Settings>("/api/settings"), api<Saved[]>("/api/saved"), api<Conversation[]>("/api/conversations")]);
    setLibrary(items); setSettings(preferences); setSaved(reports); setConversations(chats); setReady(true);
    const route = routeFromHash(location.hash);
    setSourceTarget(route.source);
    if (route.page === "asset" && route.bundle) setAsset(await api<EvidenceBundle>(`/api/bundles/${encodeURIComponent(route.bundle)}`));
  }
  useEffect(() => {
    const navigate = () => {
      const fragment = location.hash.slice(1) || "library";
      const route = routeFromHash(location.hash);
      if (pages.includes(fragment.split("?")[0])) {
        setPage(route.page);
        setSourceTarget(route.source);
        if (route.page === "asset" && route.bundle) void api<EvidenceBundle>(`/api/bundles/${encodeURIComponent(route.bundle)}`).then((value) => { if (location.hash.slice(1) === fragment) setAsset(value); }).catch(fail);
      }
      else if (fragment.startsWith("source-")) {
        const target = document.getElementById(fragment);
        if (target instanceof HTMLDetailsElement) target.open = true;
        target?.scrollIntoView({ block: "center" });
      }
    };
    window.addEventListener("hashchange", navigate);
    if ("__TAURI_INTERNALS__" in window) bootstrap().then(reload).catch(fail);
    return () => window.removeEventListener("hashchange", navigate);
  }, []);
  useEffect(() => {
    if (page !== "asset" || !sourceTarget || asset?.id !== routeFromHash(location.hash).bundle) return;
    const target = document.getElementById(`source-${sourceTarget}`);
    if (target instanceof HTMLDetailsElement) target.open = true;
    target?.scrollIntoView({ block: "center" });
  }, [asset, page, sourceTarget]);
  useEffect(() => {
    if (!job?.id || !busy) return;
    let active = true;
    const close = observeResearch<Job>(job.id, (next) => {
      if (!active) return;
      setJob(next);
      if (next.status === "completed" && next.result?.asset) {
        setAsset(next.result); location.hash = bundleRoute(next.result.id!);
        void reload().catch(fail);
      }
      if (next.error) setError(next.error);
    }, (event) => { setProgress(event.text || event.kind.replaceAll(".", " ")); if (event.text?.startsWith("Refreshing ")) setNotice(event.text); }, fail);
    return () => { active = false; close(); };
  }, [job?.id, busy]);

  async function reopenResearch(id: string) {
    const next = await api<Job>(`/api/jobs/${encodeURIComponent(id)}`);
    setJob(next); setProgress(""); setError(next.error ?? ""); setNotice("");
    if (next.request) { setQuery(next.request.query); setLevel(next.request.level ?? "beginner"); }
    setConversation(next.request?.conversation_id ? conversations.find((item) => item.id === next.request?.conversation_id) : undefined);
    if (next.status === "completed" && next.result?.asset) { setAsset(next.result); location.hash = bundleRoute(next.result.id!); }
  }

  async function research(event?: FormEvent, refresh = false, question?: string) {
    event?.preventDefault(); setError(""); setProgress("");
    try {
      const next = await api<Job>("/api/research", { method: "POST", body: JSON.stringify({ query: question || query, provider: settings?.provider ?? "codex", language: settings?.language ?? "en", level, refresh, asset_id: question || refresh ? asset?.asset.id : null, conversation_id: question && !refresh ? conversation?.id : null }) });
      setJob(next);
      if (next.status === "cached" && next.result) { setAsset(next.result); location.hash = bundleRoute(next.result.id!); }
    } catch (error) { fail(error); }
  }
  async function saveSettings(value: Settings) { try { setSettings(await api<Settings>("/api/settings", { method: "PUT", body: JSON.stringify(value) })); setError(""); } catch (error) { fail(error); } }
  function openAsset(value: EvidenceBundle) { setAsset(value); setConversation(undefined); location.hash = bundleRoute(value.id!); }

  async function updateConversation(change: { bookmarked?: boolean; asset_id?: string }) {
    if (!activeConversation) return;
    try {
      const updated = await api<Conversation>(`/api/conversations/${activeConversation.id}`, { method: "PUT", body: JSON.stringify(change) });
      if (change.asset_id) openAsset(await api<EvidenceBundle>(`/api/assets/${encodeURIComponent(change.asset_id)}`));
      setConversation(updated); await reload();
    } catch (error) { fail(error); }
  }

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="#library">Learn the Ticker</a><nav aria-label="Primary navigation"><a href="#library">Library</a><a href="#saved">Saved research</a><a href="#conversations">Conversations</a><a href="#imports">Sources</a><a href="#connections">Connections</a></nav></header>
    <main className="desktop-main">
      <p className="notice-text">Desktop developer preview · Your library stays on this computer. Educational research, not investment advice.</p>
      {error && <div role="alert" className="notice-text error"><p>{error}</p><button onClick={() => setError("")}>Dismiss</button></div>}
      {notice && <p role="status">{notice}</p>}
      {!ready ? <Connect onConnect={async (endpoint, token) => { try { connect({ endpoint, token }); await reload(); } catch (error) { fail(error); } }} /> : <>
        <AccessReview />
        <form className="research-bar" onSubmit={research}><label htmlFor="research-query">Understand an asset<input id="research-query" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ticker, asset name, exchange or contract" required maxLength={1000}/></label><label>Explanation level<select value={level} onChange={(e) => setLevel(e.target.value as typeof level)}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option></select></label><button disabled={busy}>{settings?.cloud_enabled ? "Research" : "Open cached research"}</button></form>
        {!settings?.cloud_enabled && <p>Online research is off. Enable your chosen provider in <a href="#connections">Connections</a>. Cached pages remain available.</p>}
        <ResearchJobs currentId={job?.id} revision={`${job?.id}:${job?.status}`} onOpen={reopenResearch}/>
        {job?.id && <section aria-live="polite" className="plain-panel research-job-status"><h2>Viewed research job</h2><p>{job.request?.query}</p><p>Status: {job.status.replaceAll("_", " ")}</p>
          {busy ? <><p>{progress || "Reading existing research progress"}</p><button onClick={() => api<Job>(`/api/jobs/${encodeURIComponent(job.id)}/cancel`, { method: "POST" }).then(setJob).catch(fail)}>Cancel research</button></>
            : ["failed", "cancelled", "interrupted"].includes(job.status) && <p>This job has stopped. Existing saved research is unchanged. Review the request and connection before explicitly starting new research.</p>}
        </section>}
        {job?.status === "needs_identity" && <section className="plain-panel"><h2>Choose a more specific identity</h2><p>{job.result?.message ?? "Choose a listing or contract, then submit the selected identity. Cached matches reuse their saved evidence."}</p>{job.result?.candidates?.map((item) => <button key={item.id} onClick={() => setQuery(item.id)}>{item.name} · {item.symbol} · {item.exchange ?? item.asset_type}</button>)}</section>}
        {job?.result?.educational_redirect && <p>{job.result.educational_redirect}</p>}
        {page === "connections" && settings && <Connections key={settings.provider} settings={settings} onSave={saveSettings}/> }
        {page === "imports" && <ImportDocuments online={!!settings?.cloud_enabled} settings={settings} level={level}/>}
        {page === "library" && <section><h1>Your research library</h1><p>Search any asset. Available sections depend on verifiable evidence.</p>{library.length === 0 && <section className="plain-panel"><h2>Start with one asset</h2><p>Connect your subscription runtime, then research a ticker or name. Evidence and dated explanations will be saved here.</p></section>}<div className="library-grid">{library.map((item) => <button className="plain-panel" key={item.asset.id} onClick={() => openAsset(item)}><strong>{item.asset.name}</strong><span>{item.asset.symbol} · {item.asset.asset_type}</span><span>Snapshot {new Date(item.created_at!).toLocaleString()}</span></button>)}</div></section>}
        {page === "saved" && <section><h1>Saved research</h1><p>Bookmarks reference a fixed evidence version; refresh does not overwrite it.</p>{saved.length === 0 && <p>No saved research yet.</p>}{saved.map((report) => <button key={report.id} onClick={() => api<EvidenceBundle>(`/api/bundles/${report.bundle_id}`).then(openAsset).catch(fail)}>{report.title}</button>)}</section>}
        {page === "conversations" && <section><h1>Persistent conversations</h1><p>Unbookmarked conversations expire after {settings?.retention_days ?? 180} days without activity. Bookmark a conversation to keep it.</p>{conversations.map((chat) => <button key={chat.id} onClick={() => api<EvidenceBundle>(`/api/assets/${encodeURIComponent(chat.asset_id)}`).then((bundle) => { openAsset(bundle); setConversation(chat); }).catch(fail)}>{chat.asset_id} · {chat.messages.length} messages{chat.bookmarked ? " · Bookmarked" : ""}</button>)}</section>}
        {page === "connections" && <><CodexConnection/><LibraryBackup onRestored={async () => { setConversation(undefined); setAsset(undefined); setJob(undefined); await reload(); }}/></>}
        {page === "asset" && asset && <>
          <section className="plain-panel"><p className="eyebrow">{asset.asset.asset_type} · {asset.asset.exchange ?? "Listing details unconfirmed"}</p><h1>{asset.asset.name} <small>{asset.asset.symbol}</small></h1><FreshnessLabel label="Research snapshot" value={new Date(asset.created_at!).toLocaleString()} state={Date.now() - Date.parse(asset.created_at!) > 86400000 ? "stale" : "partial"}/><p>Scope: {asset.asset.id} · {asset.level ? `${asset.level} explanations` : "Reader level not recorded"} · {asset.language}</p><div className="actions"><button disabled={busy || !settings?.cloud_enabled} onClick={() => void research(undefined, true, `Refresh research for ${asset.asset.name}`)}>Refresh evidence</button><button onClick={() => api("/api/saved", { method: "POST", body: JSON.stringify({ bundle_id: asset.id, title: asset.asset.name }) }).then(async () => { await reload(); setNotice("Research version bookmarked."); }).catch(fail)}>Bookmark this version</button><button onClick={() => download(asset.id!, "markdown").catch(fail)}>Export Markdown</button><button onClick={() => download(asset.id!, "json").catch(fail)}>Export JSON</button></div></section>
          <TermLearning key={`${asset.id}:${level}:${settings?.language}`} bundle={asset} level={level} settings={settings}><EvidenceView bundle={asset}/></TermLearning>
          <section className="plain-panel"><h2>Continue learning</h2><p>Conversation scope starts with {asset.asset.name}. Resolve a new asset through research before changing scope.</p>{!activeConversation ? <button onClick={() => api<Conversation>("/api/conversations", { method: "POST", body: JSON.stringify({ asset_id: asset.asset.id }) }).then(setConversation).catch(fail)}>Start a conversation</button> : <><p>Conversation {activeConversation.id.slice(0, 8)} · Current scope: {activeConversation.asset_id}</p><button onClick={() => void updateConversation({ bookmarked: !activeConversation.bookmarked })}>{activeConversation.bookmarked ? "Remove conversation bookmark" : "Bookmark conversation"}</button><label>Conversation asset<select disabled={busy} value={activeConversation.asset_id} onChange={(event) => void updateConversation({ asset_id: event.target.value })}>{library.map((entry) => <option key={entry.asset.id} value={entry.asset.id}>{entry.asset.name} · {entry.asset.symbol}</option>)}</select></label>{activeConversation.messages.map((message, i) => <p key={i}>{message.role}: {message.bundle_id ? <a href={`#${bundleRoute(message.bundle_id)}`}>Open cited response</a> : message.text}{message.asset_id && <small> · {message.asset_id}</small>}</p>)}<FollowUp busy={!!busy || !settings?.cloud_enabled} onAsk={(question) => void research(undefined, false, question)}/></>}</section>
        </>}
      </>}
    </main></div>;
}

function Connect({ onConnect }: { onConnect: (endpoint: string, token: string) => Promise<void> }) {
  const [endpoint, setEndpoint] = useState("http://127.0.0.1:"); const [token, setToken] = useState("");
  return <section className="plain-panel"><h1>Open your local research library</h1><p>The desktop application connects automatically after PostgreSQL and the local service are ready.</p><details><summary>Developer browser connection</summary><form onSubmit={(e) => { e.preventDefault(); void onConnect(endpoint, token).then(() => setToken("")); }}><label>Local endpoint<input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} required/></label><label>Temporary session credential<input type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} required/></label><button>Connect locally</button></form></details></section>;
}

function FollowUp({ onAsk, busy }: { onAsk: (question: string) => void; busy: boolean }) {
  const [question, setQuestion] = useState("");
  return <form onSubmit={(e) => { e.preventDefault(); onAsk(question); setQuestion(""); }}><label>Ask a follow-up or explain a term<textarea required value={question} maxLength={1000} onChange={(e) => setQuestion(e.target.value)}/></label><button disabled={busy}>Ask your connected agent</button></form>;
}

export function EvidenceView({ bundle }: { bundle: EvidenceBundle }) {
  const sources = bundle.sources ?? [];
  function renderClaim(claim: Claim) { return <article key={claim.id}><p>{claim.text}</p><div className="chip-row">{claim.source_ids?.map((id) => { const source = sources.find((item) => item.id === id); return source ? <CitationChip key={id} href={`#${sourceRoute(bundle.id!, id)}`} citation={{ citationId: id, sourceDocumentId: id, title: source.title, publisher: source.publisher, freshnessState: "unknown" }}/> : null; })}</div></article>; }
  function renderSection(section: string) { const claims = bundle.claims?.filter((claim) => claim.section === section) ?? []; return <section className="plain-panel" key={section}><h2>{section === "recent_developments" ? "Other reported developments" : section.replaceAll("_", " ")}</h2>{claims.length ? claims.map(renderClaim) : <p className="source-gap-note">Unavailable — no admitted evidence for this section.</p>}</section>; }
  return <>
    <EvidenceSections bundle={bundle} renderClaim={renderClaim}/>
    <FinancialHistory bundle={bundle}/>
    <section data-evidence-layer="context"><h2>News and historical context</h2><p>Dated research stays separate from the asset’s stable facts. Weekly selection and historical report generation are still being integrated.</p><div className="library-grid">{contextSections.map(renderSection)}</div></section>
    <section className="plain-panel" data-evidence-layer="notes"><h2>Unverified research notes</h2><p>These explanations have not passed factual validation. Candidate citations may be incomplete. These notes do not feed facts, charts or calculations.</p>{bundle.notes?.map(renderClaim)}{!bundle.notes?.length && <p>No unverified notes.</p>}</section>
    <section className="plain-panel"><h2>Sources and evidence</h2>{sources.map((source) => <SourceDetails source={source} key={source.id}/>)}{!sources.length && <p>No source documents have been registered.</p>}</section>
  </>;
}

function SourceDetails({ source }: { source: Source }) {
  return <details className="source-drawer" id={`source-${source.id}`}><summary>{source.title} · {source.verified ? "Verified retrieval" : "Unverified candidate"}</summary><p>{source.publisher}</p><a href={source.url} target="_blank" rel="noopener noreferrer">Inspect original source</a><p>Published: {source.published_at ?? "Unknown"} · As of: {source.as_of ?? "Unknown"} · Retrieved: {source.retrieved_at}</p><p>Source-use policy: {source.policy} · Provenance: {source.provenance}</p>{source.excerpt && <blockquote>{source.excerpt}</blockquote>}</details>;
}
