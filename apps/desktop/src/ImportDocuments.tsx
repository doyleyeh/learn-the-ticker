import { useEffect, useRef, useState } from "react";
import { api } from "./client";
import type { ImportPreview } from "./contracts";

const limits: Record<string, string> = {
  unverified_import: "Imported content has not been checked against the original publisher or an asset identity. It cannot supply facts or chart values.",
  formulas_not_evaluated: "Spreadsheet formulas are displayed as text and have not been calculated.",
  pdf_layout_not_verified: "PDF reading order and table layout may be inaccurate. Compare page references with the original document.",
  empty_pages: "Some pages have no readable text. Images and scanned text are not extracted.",
  merged_cells_not_expanded: "Merged cells are not expanded into repeated values.",
};

export function ImportDocuments({ online }: { online: boolean }) {
  const [file, setFile] = useState<File>();
  const [permission, setPermission] = useState(false);
  const [url, setUrl] = useState("");
  const [preview, setPreview] = useState<ImportPreview>();
  const [filename, setFilename] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const request = useRef<AbortController | undefined>(undefined);
  useEffect(() => () => { request.current?.abort(); request.current = undefined; }, []);

  function clearPreview() { setPreview(undefined); setMessage(""); setError(""); }
  async function run(path: string, body: BodyInit, name = "") {
    if (request.current) return;
    const controller = new AbortController(); request.current = controller;
    clearPreview(); setBusy(true); setFilename(name);
    try {
      const result = await api<ImportPreview>(path, { method: "POST", body, signal: controller.signal,
        headers: { "Content-Type": name ? "application/octet-stream" : "application/json" } });
      if (request.current === controller) setPreview(result);
    } catch (error) {
      if (request.current === controller) {
        if (controller.signal.aborted) setMessage("Preview cancelled. Nothing was saved.");
        else setError(error instanceof Error ? error.message : "The document could not be previewed.");
      }
    } finally {
      if (request.current === controller) { request.current = undefined; setBusy(false); }
    }
  }

  return <section className="imports" aria-labelledby="imports-heading">
    <h1 id="imports-heading">Preview a source</h1>
    <p>Inspect a document and its page or cell references before using it in your research. Previews stay on this computer and are discarded when you leave this screen.</p>
    <div className="library-grid">
      <form className="plain-panel" onSubmit={(event) => {
        event.preventDefault();
        if (!file || !permission) return;
        const format = file.name.split(".").pop()?.toLowerCase();
        if (!format || !["pdf", "csv", "xlsx"].includes(format)) { clearPreview(); setError("Choose a PDF, CSV or XLSX file."); return; }
        if (!file.size || file.size > 5 * 1024 * 1024) { clearPreview(); setError("Select a non-empty document no larger than 5 MiB."); return; }
        void run(`/api/imports/preview/file?format=${format}&permission_confirmed=true`, file, file.name);
      }}>
        <h2>From your computer</h2>
        <p>PDF, CSV or XLSX · Up to 5 MiB · Works offline</p>
        <label>Document file<input type="file" accept=".pdf,.csv,.xlsx" disabled={busy} onChange={(event) => { setFile(event.target.files?.[0]); setPermission(false); clearPreview(); }}/></label>
        <label><input type="checkbox" checked={permission} disabled={busy || !file} onChange={(event) => setPermission(event.target.checked)}/> I have permission to process this document locally.</label>
        <button disabled={busy || !file || !permission}>Preview selected file</button>
      </form>
      <form className="plain-panel" onSubmit={(event) => { event.preventDefault(); void run("/api/imports/preview/url", JSON.stringify({ url })); }}>
        <h2>From a public URL</h2>
        <p>Public HTTPS pages only. Content is downloaded only when the app has a registered usage permission for that source; other URLs remain links.</p>
        <label>Source URL<input type="url" value={url} required maxLength={2000} placeholder="https://…" disabled={busy} onChange={(event) => { setUrl(event.target.value); clearPreview(); }}/></label>
        {!online && <p>Online retrieval is off. Enable online research in <a href="#connections">Connections</a> to preview a URL.</p>}
        <button disabled={busy || !online || !url}>Preview URL</button>
      </form>
    </div>
    {busy && <div className="plain-panel"><p role="status">Reading your source…</p><button onClick={() => request.current?.abort()}>Cancel preview</button></div>}
    {error && <p role="alert" className="error">{error}</p>}
    {message && <p role="status">{message}</p>}
    {preview && <ImportPreviewDetails preview={preview} filename={filename}/>}
  </section>;
}

export function ImportPreviewDetails({ preview, filename }: { preview: ImportPreview; filename: string }) {
  const [page, setPage] = useState(0);
  const blocks = preview.document?.blocks ?? [];
  const count = Math.max(1, Math.ceil(blocks.length / 20));
  return <section className="plain-panel import-result" aria-labelledby="preview-heading">
    <h2 id="preview-heading">{preview.state === "link_only" ? "Source link only" : "Unverified document preview"}</h2>
    <p role="status">This document has not been added to your library.</p>
    {preview.source ? <>
      <p>{preview.source.publisher}</p>
      <a href={preview.source.url} target="_blank" rel="noopener noreferrer">{preview.source.url}</a>
      <p>Usage permission: {preview.source.policy?.replaceAll("_", " ")}</p>
      <p>Published: {preview.source.published_at ?? "Unknown"} · As of: {preview.source.as_of ?? "Unknown"}</p>
      {preview.document && <p>Retrieved: {new Date(preview.source.retrieved_at!).toLocaleString()}</p>}
    </> : <><p>Selected file: {filename}</p><p>Publisher, publication date and as-of date: Unknown. File timestamps do not establish these dates.</p><p>Permission: Confirmed by you for local processing.</p></>}
    <p>Preview checked: {new Date(preview.checked_at).toLocaleString()}</p>
    {preview.state === "link_only" && <p>No document content was downloaded. A link alone does not verify claims or grant permission to retain its content.</p>}
    {preview.document && <>
      <ul>{preview.document.limitations?.map((key) => <li key={key}>{limits[key]}</li>)}</ul>
      <details><summary>Document fingerprint</summary><p>SHA-256: {preview.document.content_hash}</p></details>
      <h3>Extracted content</h3>
      {blocks.slice(page * 20, (page + 1) * 20).map((block) => <article className="import-block" key={block.locator}>
        <h4>{block.locator}</h4>
        {block.text && <p className="import-text">{block.text}</p>}
        {!!block.cells?.length && <dl className="import-cells">{block.cells.map((cell) => <div key={cell.locator}><dt>{cell.locator} · {cell.kind}</dt><dd>{cell.text || "(empty)"}{cell.number_format && <span className="import-cell-detail">Number format: {cell.number_format}</span>}{cell.raw_value != null && cell.raw_value !== cell.text && <span className="import-cell-detail">Original stored value: {cell.raw_value}</span>}</dd></div>)}</dl>}
      </article>)}
      {count > 1 && <nav aria-label="Extracted content pages"><button disabled={page === 0} onClick={() => setPage(page - 1)}>Previous content</button><p aria-live="polite">Page {page + 1} of {count}</p><button disabled={page + 1 === count} onClick={() => setPage(page + 1)}>Next content</button></nav>}
    </>}
  </section>;
}
