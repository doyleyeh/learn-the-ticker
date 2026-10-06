import { useRef, useState } from "react";
import { api } from "./client";
import type { SavedItemDeletion } from "./contracts";

const names: Record<SavedItemDeletion["kind"], string> = {
  saved: "bookmark", conversation: "conversation", comparison: "comparison", report: "report",
};

export function DeleteSavedItem({ kind, id, title, onDeleted }: {
  kind: SavedItemDeletion["kind"]; id: string; title: string; onDeleted: () => void | Promise<void>;
}) {
  const details = useRef<HTMLDetailsElement>(null), submitting = useRef(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  async function remove() {
    if (submitting.current) return;
    submitting.current = true; setBusy(true); setError("");
    let deleted = false;
    try {
      await api<SavedItemDeletion>(`/api/library/items/${kind}/${encodeURIComponent(id)}`, { method: "DELETE" });
      deleted = true;
      await onDeleted();
    } catch (failure) {
      setError(deleted ? "The item was deleted, but the list could not be refreshed. Reload to see the current library."
        : failure instanceof Error ? failure.message : "Deletion could not be confirmed. Refresh the list before trying again.");
    } finally { submitting.current = false; setBusy(false); }
  }
  return <details className="delete-saved-item" ref={details}>
    <summary>Delete {names[kind]}</summary>
    <section aria-label={`Delete ${names[kind]} confirmation`}>
      <p>Delete <strong>{title}</strong> from this library?</p>
      <p>{kind === "conversation" ? "This removes the transcript and its research-job history. An active answer must finish or be cancelled first. " : "This removes the saved item. "}
        Original evidence and items saved elsewhere in the library remain available. Previously downloaded backups and exports keep their own copies.</p>
      <p>This deletion cannot be undone in the app.</p>
      <div className="actions">
        <button disabled={busy} onClick={() => { if (details.current) { details.current.open = false; details.current.querySelector("summary")?.focus(); } setError(""); }}>Cancel deletion</button>
        <button disabled={busy} onClick={() => void remove()}>Delete permanently</button>
      </div>
      {busy && <p role="status">Deleting saved item…</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  </details>;
}
