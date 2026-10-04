import { useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "./client";
import type { RetainedImportSummary, RetainedImportView } from "./contracts";

export function RetainedDocuments({ revision, renderDocument }: { revision: number; renderDocument: (view: RetainedImportView) => ReactNode }) {
  const [items, setItems] = useState<RetainedImportSummary[]>([]);
  const [view, setView] = useState<RetainedImportView>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [opening, setOpening] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const request = useRef<AbortController | undefined>(undefined);
  useEffect(() => () => { request.current?.abort(); request.current = undefined; }, []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    api<RetainedImportSummary[]>("/api/imports/retained", { signal: controller.signal }).then((rows) => {
      if (!controller.signal.aborted) setItems(rows);
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) { setItems([]); setError(error instanceof Error ? error.message : "Retained documents could not be loaded."); }
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [revision, refresh]);

  async function open(id: string) {
    if (request.current) return;
    const controller = new AbortController(); request.current = controller;
    setOpening(true); setView(undefined); setError("");
    try {
      const value = await api<RetainedImportView>(`/api/imports/retained/${encodeURIComponent(id)}`, { signal: controller.signal });
      if (request.current === controller) setView(value);
    } catch (error) {
      if (request.current === controller) setError(error instanceof Error ? error.message : "The document could not be opened.");
    } finally {
      if (request.current === controller) { request.current = undefined; setOpening(false); }
    }
  }

  return <section className="plain-panel" aria-labelledby="retained-documents-heading">
    <h2 id="retained-documents-heading">Retained documents</h2>
    <p>Copies you chose to keep are included in your library backups. They remain unverified and are not sent to an AI provider by saving or opening them.</p>
    <p>Up to 100 documents and 64 MiB total. Each selected file can be up to 5 MiB.</p>
    <button disabled={loading || opening} onClick={() => setRefresh((value) => value + 1)}>Refresh retained documents</button>
    {loading && <p role="status">Loading retained documents…</p>}
    {!loading && !error && !items.length && <p>No documents have been retained.</p>}
    {!!items.length && <ul>{items.map((item) => <li key={item.id}>
      <button disabled={opening} onClick={() => void open(item.id)}>{item.title}</button>
      <span> · {item.format.toUpperCase()} · Unverified · Retained {new Date(item.retained_at).toLocaleString()}</span>
    </li>)}</ul>}
    {opening && <p role="status">Checking the original document…</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {view && renderDocument(view)}
  </section>;
}
