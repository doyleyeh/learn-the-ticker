import { useState } from "react";
import type { Conversation, EvidenceBundle, Settings } from "./contracts";
import { bundleRoute, conversationRoute } from "./routes";

type Change = { bookmarked?: boolean; asset_id?: string; context_bundle_id?: string };

export function ConversationPanel({ conversation, library, settings, busy, onUpdate, onAsk }: {
  conversation: Conversation; library: EvidenceBundle[]; settings?: Settings; busy: boolean;
  onUpdate: (change: Change) => Promise<void>; onAsk: (question: string) => Promise<boolean>;
}) {
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const current = library.find((entry) => entry.asset.id === conversation.asset_id);
  async function update(change: Change) {
    if (pending) return;
    setPending(true); setError("");
    try { await onUpdate(change); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "The conversation could not be changed."); }
    finally { setPending(false); }
  }
  async function ask() {
    if (pending || busy || !settings?.cloud_enabled || !current) return;
    setPending(true); setError("");
    try { if (await onAsk(question)) setQuestion(""); }
    finally { setPending(false); }
  }
  return <section className="plain-panel" aria-labelledby="conversation-title">
    <h2 id="conversation-title">Conversation about {current?.asset.name ?? conversation.asset_id}</h2>
    <p>Current scope: {conversation.asset_id}. Opening an earlier cited response does not change this scope.</p>
    <p>Next answer: {settings?.provider ?? "No provider selected"} · {settings?.model ?? "Provider’s current default model"} · {settings?.language ?? "en"}. Change the connection in <a href="#connections">Connections</a>; saved messages and citations stay in this library.</p>
    {error && <p role="alert">{error}</p>}
    <button disabled={pending} onClick={() => void update({ bookmarked: !conversation.bookmarked })}>{conversation.bookmarked ? "Remove conversation bookmark" : "Bookmark conversation"}</button>
    <label>Conversation asset<select disabled={busy || pending} value={conversation.asset_id} onChange={(event) => void update({ asset_id: event.target.value })}>
      {!current && <option value={conversation.asset_id}>{conversation.asset_id} · unavailable</option>}
      {library.map((entry) => <option key={entry.asset.id} value={entry.asset.id}>{entry.asset.name} · {entry.asset.symbol}</option>)}
    </select></label>
    <p>Only independently resolved library assets can be selected. Finish or cancel the active answer before changing scope.</p>
    {conversation.context_bundle_id ? <p><a href={`#${bundleRoute(conversation.context_bundle_id, conversation.id)}`}>Open selected page evidence</a>. This version stays selected when the ticker page refreshes. Original source dates and units remain historical; new research is checked separately.</p>
      : <p>This older conversation has no recorded starting page version. Its cited answers remain available. Select current ticker evidence explicitly to supply page context.</p>}
    {current && current.id !== conversation.context_bundle_id && <p>The current ticker page has a different evidence version. <button disabled={busy || pending} onClick={() => void update({ context_bundle_id: current.id! })}>Use current ticker evidence</button></p>}
    {current && <a href={`#${bundleRoute(current.id!, conversation.id)}`}>Open current ticker evidence</a>}
    <div aria-label="Conversation history">{conversation.messages?.map((message, index) => <p key={index}>
      {message.role === "scope" ? "Context" : message.role === "assistant" ? "Agent" : "You"}: {message.bundle_id ? <a href={`#${bundleRoute(message.bundle_id, conversation.id)}`}>Open cited response</a> : message.text}
      {message.context_bundle_id && <> · <a href={`#${bundleRoute(message.context_bundle_id, conversation.id)}`}>Open recorded page evidence</a></>}
      {message.asset_id && <span className="ticker-meta"> · {message.asset_id}</span>}
    </p>)}</div>
    {!conversation.messages?.length && <p>No messages yet. Your question will use admitted ticker evidence and its original references.</p>}
    <form onSubmit={(event) => { event.preventDefault(); void ask(); }}>
      <label>Ask a follow-up or explain a term<textarea required value={question} maxLength={1000} onChange={(event) => setQuestion(event.target.value)}/></label>
      <button disabled={busy || pending || !settings?.cloud_enabled || !current}>Ask your connected agent</button>
    </form>
    <a href={`#${conversationRoute(conversation.id!)}`}>Link to this conversation</a>
  </section>;
}
