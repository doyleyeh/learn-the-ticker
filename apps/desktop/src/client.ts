import { invoke } from "@tauri-apps/api/core";
import type { RuntimeEvent } from "./contracts";

export type Bootstrap = { endpoint: string; token: string };
let connection: Bootstrap | undefined;
export function connect(value: Bootstrap) {
  const url = new URL(value.endpoint);
  if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" || url.pathname !== "/" || url.search || url.hash || url.username || url.password || value.token.length < 32) {
    throw new Error("A loopback endpoint and valid local session credential are required.");
  }
  connection = { endpoint: url.origin, token: value.token };
}
export async function bootstrap() {
  const value = await invoke<Bootstrap>("bootstrap");
  connect(value);
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!connection) throw new Error("Open the desktop application or connect the local development service.");
  if (!path.startsWith("/api/") || path.includes("\\")) throw new Error("Invalid application endpoint");
  const response = await fetch(connection.endpoint + path, { ...init, redirect: "error", headers: { "Content-Type": "application/json", ...init.headers, Authorization: `Bearer ${connection.token}` } });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === "string" ? error.detail : "Local service request failed");
  }
  return response.json() as Promise<T>;
}
export function watchJob(id: string, onEvent: (event: RuntimeEvent) => void, onClose: () => void) {
  if (!connection) throw new Error("Local service is disconnected");
  const credential = connection.token;
  const socket = new WebSocket(connection.endpoint.replace("http:", "ws:") + `/api/events/${encodeURIComponent(id)}`);
  socket.onopen = () => socket.send(JSON.stringify({ token: credential, after: 0 }));
  socket.onmessage = (event) => { try { onEvent(JSON.parse(event.data)); } catch { socket.close(); } };
  socket.onclose = onClose;
  return () => { socket.onclose = null; socket.close(); };
}
export async function download(bundle: string, format: "markdown" | "json") {
  return downloadFile(`/api/export/${encodeURIComponent(bundle)}?format=${format}`, format === "json" ? "research.json" : "research.md");
}
export async function downloadBackup() {
  return downloadFile("/api/library/backup", "learn-the-ticker-library.lttbackup");
}
export async function downloadReport(id: string, format: "markdown" | "json") {
  return downloadFile(`/api/reports/${encodeURIComponent(id)}/export?format=${format}`, format === "json" ? "report.json" : "report.md");
}
async function downloadFile(path: string, filename: string) {
  if (!connection) throw new Error("Local service is disconnected");
  const response = await fetch(connection.endpoint + path, { redirect: "error", headers: { Authorization: `Bearer ${connection.token}` } });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === "string" ? error.detail : "Export failed");
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a"); link.href = url; link.download = filename;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
