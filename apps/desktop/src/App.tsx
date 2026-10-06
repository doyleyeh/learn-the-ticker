import { useEffect, useState, type FormEvent } from "react";
import { api, bootstrap, connect, download } from "./client";
import type { EvidenceBundle, Settings, Conversation as ConversationContract, SavedResearch, ResearchRequest } from "./contracts";
import { SnapshotStatus } from "./EvidenceFreshness";
import { bundleRoute, comparisonRoute, conversationRoute, pages, reportRoute, routeFromHash } from "./routes";
import { Comparisons } from "./Comparisons";
import { Reports } from "./Reports";
import { LibraryBackup } from "./LibraryBackup";
import { ImportDocuments } from "./ImportDocuments";
import { EvidenceView } from "./TickerDashboard";
export { EvidenceView } from "./TickerDashboard";
import { CodexConnection } from "./CodexConnection";
import { Connections } from "./Connections";
import { ConversationPanel } from "./ConversationPanel";
import { AccessReview } from "./AccessReview";
import { SourceReview } from "./SourceReview";
import { TermLearning } from "./TermLearning";
import { ResearchJobs } from "./ResearchJobs";
import { DeleteSavedItem } from "./DeleteSavedItem";
import { LibraryCache } from "./LibraryCache";
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
  const [comparisonSelection, setComparisonSelection] = useState(() => routeFromHash(location.hash));
  const [sourceTarget, setSourceTarget] = useState(routeFromHash(location.hash).source);
  const [notice, setNotice] = useState("");
  const [asset, setAsset] = useState<EvidenceBundle>();
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<"beginner" | "intermediate">("beginner");
  const [job, setJob] = useState<Job>();
  const [progress, setProgress] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(routeFromHash(location.hash).conversation);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [libraryRevision, setLibraryRevision] = useState(0);
  const activeConversation = conversations.find((item) => item.id === conversationId);
  const busy = activeResearch(job?.status ?? "");
  const fail = (error: unknown) => setError(error instanceof Error ? error.message : "The operation could not be completed.");

  async function reload() {
    const [items, preferences, reports, chats] = await Promise.all([api<EvidenceBundle[]>("/api/library"), api<Settings>("/api/settings"), api<Saved[]>("/api/saved"), api<Conversation[]>("/api/conversations")]);
    setLibrary(items); setSettings(preferences); setSaved(reports); setConversations(chats); setReady(true);
    const route = routeFromHash(location.hash);
    setSourceTarget(route.source);
    setConversationId(route.conversation);
    if (route.page === "asset" && route.bundle) setAsset(await api<EvidenceBundle>(`/api/bundles/${encodeURIComponent(route.bundle)}`));
  }
  useEffect(() => {
    const navigate = () => {
      const fragment = location.hash.slice(1) || "library";
      const route = routeFromHash(location.hash);
      if (pages.includes(fragment.split("?")[0])) {
        setPage(route.page);
        setComparisonSelection(route);
        setSourceTarget(route.source);
        setConversationId(route.conversation);
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
    let shownBundle = job.result?.id;
    const close = observeResearch<Job>(job.id, (next) => {
      if (!active) return;
      setJob(next);
      if (!next.request?.conversation_id && next.result?.asset && next.result.completion === "section_checkpoint" && next.result.id !== shownBundle) {
        shownBundle = next.result.id;
        setAsset(next.result); location.hash = bundleRoute(next.result.id!);
      }
      if (next.status === "completed" && next.result?.asset) {
        if (next.request?.conversation_id) location.hash = conversationRoute(next.request.conversation_id);
        else { setAsset(next.result); location.hash = bundleRoute(next.result.id!); }
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
    if (next.request?.conversation_id) location.hash = conversationRoute(next.request.conversation_id);
    else if (next.result?.asset) { setAsset(next.result); location.hash = bundleRoute(next.result.id!); }
    // A fast completion can arrive before an observer is attached (for example
    // after source review). Refresh persisted chat messages on this path too.
    if (next.status === "completed") await reload();
  }

  async function research(event?: FormEvent, refresh = false, question?: string, chat?: Conversation) {
    event?.preventDefault(); setError(""); setProgress("");
    try {
      const next = await api<Job>("/api/research", { method: "POST", body: JSON.stringify({ query: question || query, provider: settings?.provider ?? "codex", language: settings?.language ?? "en", level, refresh, asset_id: chat?.asset_id ?? (question || refresh ? asset?.asset.id : null), conversation_id: chat?.id ?? null }) });
      setJob(next);
      if (next.status === "cached" && next.result) { setAsset(next.result); location.hash = bundleRoute(next.result.id!); }
      return true;
    } catch (error) { fail(error); return false; }
  }
  async function saveSettings(value: Settings) { try { setSettings(await api<Settings>("/api/settings", { method: "PUT", body: JSON.stringify(value) })); setError(""); } catch (error) { fail(error); } }
  function openAsset(value: EvidenceBundle) { setAsset(value); setConversationId(null); location.hash = bundleRoute(value.id!); }

  async function startConversation() {
    if (!asset) return;
    try {
      const chat = await api<Conversation>("/api/conversations", { method: "POST", body: JSON.stringify({ asset_id: asset.asset.id, context_bundle_id: asset.id }) });
      setConversations((items) => [...items, chat]);
      location.hash = conversationRoute(chat.id);
    } catch (error) { fail(error); }
  }

  async function updateConversation(change: { bookmarked?: boolean; asset_id?: string; context_bundle_id?: string }) {
    if (!activeConversation) return;
    const updated = await api<Conversation>(`/api/conversations/${activeConversation.id}`, { method: "PUT", body: JSON.stringify(change) });
    setConversations((items) => items.map((item) => item.id === updated.id ? updated : item));
  }

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="#library">Learn the Ticker</a><nav aria-label="Primary navigation"><a href="#library">Library</a><a href="#saved">Saved research</a><a href="#conversations">Conversations</a><a href="#comparisons">Comparisons</a><a href="#reports">Reports</a><a href="#imports">Sources</a><a href="#connections">Connections</a></nav></header>
    <main className="desktop-main">
      <p className="notice-text">Desktop developer preview · Your library stays on this computer. Educational research, not investment advice.</p>
      {error && <div role="alert" className="notice-text error"><p>{error}</p><button onClick={() => setError("")}>Dismiss</button></div>}
      {notice && <p role="status">{notice}</p>}
      {!ready ? <Connect onConnect={async (endpoint, token) => { try { connect({ endpoint, token }); await reload(); } catch (error) { fail(error); } }} /> : <>
        <AccessReview />
        <SourceReview onReviewed={(runId) => { void reopenResearch(runId).catch(fail); }}/>
        <form className="research-bar" onSubmit={research}><label htmlFor="research-query">Understand an asset<input id="research-query" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ticker, asset name, exchange or contract" required maxLength={1000}/></label><label>Explanation level<select value={level} onChange={(e) => setLevel(e.target.value as typeof level)}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option></select></label><button disabled={busy}>{settings?.cloud_enabled ? "Research" : "Open cached research"}</button></form>
        {!settings?.cloud_enabled && <p>Online research is off. Enable your chosen provider in <a href="#connections">Connections</a>. Cached pages remain available.</p>}
        <ResearchJobs currentId={job?.id} revision={`${job?.id}:${job?.status}:${libraryRevision}`} onOpen={reopenResearch}/>
        {job?.id && <section aria-live="polite" className="plain-panel research-job-status"><h2>Viewed research job</h2><p>{job.request?.query}</p><p>Status: {job.status.replaceAll("_", " ")}</p>
          {job.request?.conversation_id && job.result?.completion === "section_checkpoint" && <a href={`#${bundleRoute(job.result.id!, job.request.conversation_id)}`}>Open checked sections (incomplete)</a>}
          {busy ? <><p>{progress || "Reading existing research progress"}</p><button onClick={() => api<Job>(`/api/jobs/${encodeURIComponent(job.id)}/cancel`, { method: "POST" }).then(setJob).catch(fail)}>Cancel research</button></>
            : ["failed", "cancelled", "interrupted"].includes(job.status) && <p>This job has stopped. Earlier saved research is unchanged. Any independently checked section remains labeled incomplete. Review the request and connection before explicitly starting new research.</p>}
        </section>}
        {job?.status === "needs_identity" && <section className="plain-panel"><h2>Choose a more specific identity</h2><p>{job.result?.message ?? "Choose a listing or contract, then submit the selected identity. Cached matches reuse their saved evidence."}</p>{job.result?.candidates?.map((item) => <button key={item.id} onClick={() => setQuery(item.id)}>{item.name} · {item.symbol} · {item.exchange ?? item.asset_type}</button>)}</section>}
        {job?.result?.educational_redirect && <p>{job.result.educational_redirect}</p>}
        {page === "connections" && settings && <Connections key={settings.provider} settings={settings} onSave={saveSettings}/> }
        {page === "imports" && <ImportDocuments online={!!settings?.cloud_enabled} settings={settings} level={level}/>}
        {page === "comparisons" && <Comparisons key={`${comparisonSelection.comparison}:${comparisonSelection.bundle}`} library={library} saved={saved} settings={settings} resultId={comparisonSelection.comparison} initialLeft={comparisonSelection.bundle}/>}
        {page === "reports" && <Reports key={`${comparisonSelection.report}:${comparisonSelection.bundle}`} library={library} saved={saved} settings={settings} reportId={comparisonSelection.report} initialBundle={comparisonSelection.bundle}/>}
        {page === "library" && <section><h1>Your research library</h1><p>Search any asset. Available sections depend on verifiable evidence.</p>{library.length === 0 && <section className="plain-panel"><h2>Start with one asset</h2><p>Connect your subscription runtime, then research a ticker or name. Evidence and dated explanations will be saved here.</p></section>}<div className="library-grid">{library.map((item) => <button className="plain-panel" key={item.asset.id} onClick={() => openAsset(item)}><strong>{item.asset.name}</strong><span>{item.asset.symbol} · {item.asset.asset_type}</span><span>Snapshot {new Date(item.created_at!).toLocaleString()}</span></button>)}</div></section>}
        {page === "saved" && <section><h1>Saved research</h1><p>Bookmarks reference a fixed evidence version; refresh does not overwrite it.</p>{saved.length === 0 && <p>No saved research yet.</p>}{saved.map((report) => <article className="plain-panel" key={report.id} data-saved-id={report.id}>
          <button onClick={() => api<EvidenceBundle>(`/api/bundles/${encodeURIComponent(report.bundle_id)}`).then(openAsset).catch(fail)}>{report.title}</button>
          <DeleteSavedItem kind="saved" id={report.id} title={report.title} onDeleted={reload}/>
        </article>)}</section>}
        {page === "conversations" && <section><h1>Persistent conversations</h1><p>Unbookmarked conversations expire after {settings?.retention_days ?? 180} days without activity. Bookmark a conversation to keep it.</p>
          <nav aria-label="Saved conversations">{conversations.map((chat) => <a key={chat.id} href={`#${conversationRoute(chat.id)}`}>{chat.asset_id} · {chat.messages.length} messages{chat.bookmarked ? " · Bookmarked" : ""}</a>)}</nav>
          {activeConversation ? <ConversationPanel key={activeConversation.id} conversation={activeConversation} library={library} settings={settings} busy={!!busy} onUpdate={updateConversation} onAsk={(question) => research(undefined, false, question, activeConversation)}/> : <p>{conversationId ? "This conversation is unavailable or has expired. Saved evidence remains in the library." : "Select a conversation, or start one from a ticker page."}</p>}
          {activeConversation && <DeleteSavedItem key={`delete:${activeConversation.id}`} kind="conversation" id={activeConversation.id} title={`Conversation about ${activeConversation.asset_id}`} onDeleted={async () => {
            if (job?.request?.conversation_id === activeConversation.id) { setJob(undefined); setProgress(""); }
            setLibraryRevision((revision) => revision + 1);
            setNotice("Conversation deleted. Original evidence remains in the library.");
            setConversationId(null); location.hash = "conversations"; await reload();
          }}/>}
        </section>}
        {page === "connections" && <><CodexConnection/><LibraryCache onCleaned={reload}/><LibraryBackup onRestored={async () => { setConversationId(null); setAsset(undefined); setJob(undefined); await reload(); }}/></>}
        {page === "asset" && asset && <>
          {activeConversation && <a href={`#${conversationRoute(activeConversation.id)}`}>Return to conversation</a>}
          <CheckpointNotice completion={asset.completion}/>
          <section className="plain-panel"><p className="eyebrow">{asset.asset.asset_type} · {asset.asset.exchange ?? "Listing details unconfirmed"}</p><h1>{asset.asset.name} <small>{asset.asset.symbol}</small></h1><SnapshotStatus bundle={asset}/><p>Scope: {asset.asset.id} · {asset.level ? `${asset.level} explanations` : "Reader level not recorded"} · {asset.language}</p><div className="actions"><button disabled={busy || !settings?.cloud_enabled || asset.completion === "section_checkpoint"} onClick={() => void research(undefined, true, `Refresh research for ${asset.asset.name}`)}>Refresh evidence</button><button onClick={() => api("/api/saved", { method: "POST", body: JSON.stringify({ bundle_id: asset.id, title: asset.asset.name }) }).then(async () => { await reload(); setNotice("Research version bookmarked."); }).catch(fail)}>Bookmark this version</button><button onClick={() => download(asset.id!, "markdown").catch(fail)}>Export Markdown</button><button onClick={() => download(asset.id!, "json").catch(fail)}>Export JSON</button></div></section>
          <TermLearning key={`${asset.id}:${level}:${settings?.language}`} bundle={asset} level={level} settings={settings}><EvidenceView bundle={asset}/></TermLearning>
          {asset.completion !== "section_checkpoint" && <section className="plain-panel"><h2>Continue learning</h2><p>Start a conversation scoped to {asset.asset.name}, or return to an existing conversation. Original cited responses remain separate saved versions.</p><button onClick={() => void startConversation()}>Start a conversation</button><a href={`#${comparisonRoute(undefined, asset.id)}`}>Compare this saved page</a><a href={`#${reportRoute(undefined, asset.id)}`}>Create report from this page</a></section>}
        </>}
      </>}
    </main></div>;
}

function Connect({ onConnect }: { onConnect: (endpoint: string, token: string) => Promise<void> }) {
  const [endpoint, setEndpoint] = useState("http://127.0.0.1:"); const [token, setToken] = useState("");
  return <section className="plain-panel"><h1>Open your local research library</h1><p>The desktop application connects automatically after PostgreSQL and the local service are ready.</p><details><summary>Developer browser connection</summary><form onSubmit={(e) => { e.preventDefault(); void onConnect(endpoint, token).then(() => setToken("")); }}><label>Local endpoint<input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} required/></label><label>Temporary session credential<input type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} required/></label><button>Connect locally</button></form></details></section>;
}


export function CheckpointNotice({ completion }: { completion: EvidenceBundle["completion"] }) {
  return completion === "section_checkpoint" ? <section className="plain-panel" role="status"><h2>Incomplete research — checked sections</h2><p>This version contains only independently admitted evidence available before the overall run finished. The run may still be active or may have stopped. Missing sections remain unavailable. Earlier completed research is unchanged.</p></section> : null;
}
