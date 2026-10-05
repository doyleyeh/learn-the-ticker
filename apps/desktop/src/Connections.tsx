import { useEffect, useRef, useState } from "react";
import type { RuntimeCapabilities, RuntimeModelCatalog, Settings } from "./contracts";
import { api } from "./client";

export function Connections({ settings, onSave }: { settings: Settings; onSave: (value: Settings) => Promise<void> }) {
  const [connections, setConnections] = useState<RuntimeCapabilities[]>([]);
  const [catalog, setCatalog] = useState<RuntimeModelCatalog>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  async function save(value: Settings) {
    setBusy(true); setError("");
    try { await onSave(value); }
    finally { setBusy(false); }
  }

  async function check(models: boolean) {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true); setError("");
    if (models) setCatalog(undefined);
    try {
      if (models) {
        const value = await api<RuntimeModelCatalog>(`/api/connections/${settings.provider}/models`, { signal: controller.signal });
        if (!controller.signal.aborted) setCatalog(value);
      } else {
        const value = await api<RuntimeCapabilities[]>("/api/connections", { signal: controller.signal });
        if (!controller.signal.aborted) setConnections(value);
      }
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Connection check failed.");
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }

  const models = catalog?.status === "available" ? catalog.models ?? [] : [];
  const missingSelection = Boolean(settings.model && !models.some((model) => model.id === settings.model));
  return <section className="plain-panel" aria-labelledby="connections-title">
    <h1 id="connections-title">Connections</h1>
    <p>Online research sends your question, selected evidence and scoped conversation to your chosen provider. Sources and configured financial services receive retrieval requests. There is no app telemetry.</p>
    {error && <p role="alert">{error}</p>}
    <fieldset disabled={busy}>
      <legend>Research connection</legend>
      <label><input type="checkbox" checked={settings.cloud_enabled ?? false} onChange={(event) => void save({ ...settings, cloud_enabled: event.target.checked })}/> Allow cloud research</label>
      <label>Selected subscription runtime<select value={settings.provider} onChange={(event) => void save({ ...settings, provider: event.target.value as Settings["provider"], model: null })}>
        <option value="codex">ChatGPT / Codex</option><option value="gemini">Gemini</option><option value="claude">Claude Code</option>
      </select></label>
      <button onClick={() => void check(true)}>Refresh provider models</button>
      <p role="status">{catalog?.message ?? "Refresh models after signing in. This reads the provider catalog without generating content."}</p>
      <label>Research model<select value={settings.model ?? ""} disabled={catalog?.status !== "available" || models.length === 0} onChange={(event) => void save({ ...settings, model: event.target.value || null })}>
        <option value="">Provider’s current default</option>
        {missingSelection && <option value={settings.model!} disabled>Previously selected: {settings.model}</option>}
        {models.map((model) => <option key={model.id} value={model.id}>{model.name}{model.is_default ? " (provider default)" : ""}</option>)}
      </select></label>
      {settings.model && <button onClick={() => void save({ ...settings, model: null })}>Clear saved model</button>}
      {catalog?.status === "available" && missingSelection && <p role="alert">Your saved model is absent from the current catalog. Select another model explicitly; research will not fall back automatically.</p>}
      <p>A catalog entry does not prove model access or research compatibility. The selected model and quota are checked again for each request.</p>
      <label>Explanation language<select value={settings.language} onChange={(event) => void save({ ...settings, language: event.target.value as Settings["language"] })}>
        <option value="en">English</option><option value="zh-TW">繁體中文</option>
      </select></label>
      <label><input type="checkbox" checked={settings.manual_source_review ?? false} onChange={(event) => void save({ ...settings, manual_source_review: event.target.checked })}/> Require source review before admission</label>
      <label><input type="checkbox" checked={settings.experimental_yahoo_enabled ?? false} onChange={(event) => void save({ ...settings, experimental_yahoo_enabled: event.target.checked })}/> Enable experimental private Yahoo data</label>
      <p>Optional personal-use history, provider valuations and analyst estimates through unofficial yfinance, after available entitled EODHD history is checked. This experiment does not establish Yahoo permission. Saved prices, valuations, analyst opinions, returns and citations support explanations through your selected AI provider when cloud research is enabled. Same-user backups retain them; shareable exports omit them. Retrieval is off by default and after restore. Disabling retrieval stops active research and keeps saved evidence available for learning. Turn off cloud research to prevent cloud explanations. Missing or unqualified runtime support remains unavailable.</p>
      <button onClick={() => void check(false)}>Check installed runtimes</button>
    </fieldset>
    {busy && <p role="status">Checking or saving the connection…</p>}
    <p>Checks do not generate content. No automatic provider switch or paid API fallback is enabled.</p>
    {connections.map((item) => <article key={item.provider}>
      <h2>{item.provider}</h2><p>{item.installed ? `Installed ${item.version ?? "unknown version"}` : "Not installed"} · Authentication: {item.authentication} · Qualification: {item.qualification}</p>
      <p>{item.reason}</p><p>{item.generation ? item.browsing ? "Qualified for online research." : "Qualified for explanations of admitted cached or imported evidence." : "New generation is unavailable. Previously cached research remains available."}</p>
    </article>)}
  </section>;
}
