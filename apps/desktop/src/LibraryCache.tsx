import { useEffect, useRef, useState } from "react";
import { api } from "./client";
import type { CacheSummary } from "./contracts";

const size = (bytes: number) => `${new Intl.NumberFormat("en", { maximumFractionDigits: 2 }).format(bytes / 1_000_000)} MB`;

export function LibraryCache({ onCleaned }: { onCleaned: () => Promise<void> }) {
  const [summary, setSummary] = useState<CacheSummary>();
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const pending = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    api<CacheSummary>("/api/library/cache", { signal: controller.signal }).then((value) => {
      if (!controller.signal.aborted) setSummary(value);
    }).catch((failure: unknown) => {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Cache status unavailable.");
    });
    return () => controller.abort();
  }, []);
  async function cleanup() {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError("");
    try {
      setSummary(await api<CacheSummary>("/api/library/cache/cleanup", { method: "POST" }));
      await onCleaned();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Cleanup status unavailable. Refresh before trying again."); }
    finally { pending.current = false; setBusy(false); }
  }
  return <section className="plain-panel" aria-labelledby="library-cache-heading">
    <h2 id="library-cache-heading">Disposable cache</h2>
    <p>Cleanup removes the oldest unsaved page versions and their related research history only when disposable content exceeds the budget. Bookmarks, conversations, reports, comparisons, retained documents and learning explanations keep their original evidence.</p>
    <p>Cleanup runs at startup and every five minutes, and waits while research is active. Saved work is outside this disposable budget. These amounts count stored content; database files and backups can use additional disk space.</p>
    {summary && <><dl><dt>Disposable budget</dt><dd>{size(summary.budget_bytes)}</dd><dt>Disposable content</dt><dd>{size(summary.disposable_bytes)}</dd><dt>Protected content</dt><dd>{size(summary.protected_bytes)}</dd></dl>
      {summary.deferred_for_active_work && <p role="status">Cleanup is waiting for active research to finish.</p>}
      {(summary.removed_items ?? 0) > 0 && <p role="status">Removed {size(summary.removed_bytes ?? 0)} of disposable content. Protected work remains available.</p>}</>}
    {!summary && !error && <p role="status">Reading cache usage…</p>}
    <button disabled={busy || !summary} onClick={() => void cleanup()}>{busy ? "Cleaning disposable cache…" : "Clean disposable cache now"}</button>
    {error && <p role="alert">{error}</p>}
  </section>;
}
