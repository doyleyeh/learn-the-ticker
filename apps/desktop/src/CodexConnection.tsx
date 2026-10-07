import { useEffect, useState } from "react";
import { api } from "./client";
import type { ProviderLogin } from "./contracts";

export function CodexConnection() {
  const [login, setLogin] = useState<ProviderLogin>();
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void api<ProviderLogin>("/api/connections/codex/login").then((value) => { if (active) setLogin(value); }).catch(() => { if (active) setError("Connection status is unavailable. Reconnect the local service."); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (login?.status !== "pending" || busy) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const value = await api<ProviderLogin>("/api/connections/codex/login");
        if (active) { setLogin(value); setError(""); }
      } catch { if (active) setError("Sign-in status is temporarily unavailable. Reconnecting…"); }
      if (active) timer = setTimeout(() => void poll(), 1500);
    };
    timer = setTimeout(() => void poll(), 1500);
    return () => { active = false; clearTimeout(timer); };
  }, [login?.status, busy]);

  async function action(cancel = false) {
    setBusy(true); setError("");
    try { setLogin(await api<ProviderLogin>(`/api/connections/codex/login${cancel ? "/cancel" : ""}`, { method: "POST" })); }
    catch (error) { setError(error instanceof Error ? error.message : "Sign-in is unavailable."); }
    finally { setBusy(false); }
  }

  return <section className="plain-panel" aria-labelledby="codex-connection-title">
    <h2 id="codex-connection-title">Connect ChatGPT / Codex</h2>
    <p>Install the Codex runtime first and connect a compatible paid ChatGPT subscription. Sign-in alone does not confirm model access or available usage. Codex manages authentication in a separate app profile; library backups exclude it.</p>
    <p>Sign-in opens no research session and does not enable cloud research automatically.</p>
    {error && <p role="alert">{error}</p>}
    <div role="status"><p>{login?.message ?? "Checking connection status…"}</p></div>
    {login?.status === "pending" && <>
      <p>Open <a href="https://auth.openai.com/codex/device" target="_blank" rel="noopener noreferrer">auth.openai.com/codex/device</a> in your browser. If a desktop link does not open, copy that address into your browser.</p>
      <p>One-time code: <strong className="device-code">{login.user_code}</strong></p>
      <p>This request expires at {new Date(login.expires_at!).toLocaleTimeString()}. Only enter a code for a sign-in you started.</p>
      <button disabled={busy} onClick={() => void action(true)}>Cancel sign-in</button>
    </>}
    {login?.status !== "pending" && <button disabled={busy} onClick={() => void action()}>{busy ? "Contacting Codex…" : login?.status === "authenticated" ? "Check ChatGPT sign-in" : "Sign in with ChatGPT"}</button>}
    <p>Research compatibility is still experimental. Gemini and Claude connection setup remain in development.</p>
  </section>;
}
