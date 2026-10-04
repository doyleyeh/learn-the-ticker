import { useRef, useState } from "react";
import { api, downloadBackup } from "./client";
import type { BackupSummary } from "./contracts";

export function LibraryBackup({ onRestored }: { onRestored: () => Promise<void> }) {
  const [file, setFile] = useState<File>();
  const [preview, setPreview] = useState<BackupSummary>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  async function run(operation: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await operation(); }
    catch (error) { setError(error instanceof Error ? error.message : "The library operation failed."); }
    finally { setBusy(false); }
  }

  return <section className="plain-panel" aria-labelledby="library-backup-heading">
    <h2 id="library-backup-heading">Back up or transfer your library</h2>
    <p>Keep evidence versions, saved research, conversations, permitted retained documents and settings together. Provider sign-ins, API credentials and temporary connection secrets are excluded. Reconnect your provider after restoring on another computer.</p>
    <button disabled={busy} onClick={() => void run(async () => { await downloadBackup(); setMessage("Backup download requested. Save the archive with your personal backups."); })}>Download full library backup</button>
    <h3>Restore into an empty library</h3>
    <p>Restore preserves existing research by refusing to overwrite a library that already contains work. Choose a backup from your own installation. Validation checks its integrity and references; it does not establish who created it.</p>
    <label>Library archive<input ref={input} type="file" accept=".lttbackup,.zip" disabled={busy} onChange={(event) => { setFile(event.target.files?.[0]); setPreview(undefined); setMessage(""); setError(""); }}/></label>
    <button disabled={busy || !file} onClick={() => void run(async () => {
      if (!file) return;
      if (file.size > 128 * 1024 * 1024) throw new Error("This preview supports archives up to 128 MiB.");
      setPreview(await api<BackupSummary>("/api/library/restore/preview", { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file }));
    })}>Validate selected backup</button>
    {preview && <div className="backup-preview">
      <h3>Backup contents</h3>
      <p>Created {new Date(preview.created_at).toLocaleString()}</p>
      <dl><dt>Assets</dt><dd>{preview.assets}</dd><dt>Evidence versions</dt><dd>{preview.evidence_versions}</dd><dt>Conversations</dt><dd>{preview.conversations}</dd><dt>Saved reports</dt><dd>{preview.saved_reports}</dd><dt>Term explanations</dt><dd>{preview.term_explanations ?? 0}</dd><dt>Retained documents</dt><dd>{preview.retained_imports ?? 0}</dd><dt>Retained document bytes</dt><dd>{preview.attachment_bytes ?? 0}</dd></dl>
      <p>Credentials: excluded. Cloud research and start-at-login will remain off. Unfinished runs require an explicit retry.</p>
      {preview.reason && <p role="status">{preview.reason}</p>}
      <button disabled={busy || !file || !preview.can_restore} onClick={() => void run(async () => {
        if (!file) return;
        await api("/api/library/restore", { method: "POST", headers: { "Content-Type": "application/octet-stream", "X-Backup-Fingerprint": preview.fingerprint }, body: file });
        setPreview(undefined); setFile(undefined);
        if (input.current) input.current.value = "";
        await onRestored(); setMessage("Library restored. Your evidence and conversations are ready; online research remains off.");
      })}>Restore this backup</button>
    </div>}
    {busy && <p role="status">Checking your library…</p>}
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
