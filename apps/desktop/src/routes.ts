export const pages = ["library", "saved", "conversations", "connections", "imports", "asset", "comparisons"];
export function routeFromHash(hash: string) {
  const [name, query = ""] = hash.replace(/^#/, "").split("?", 2);
  const params = new URLSearchParams(query);
  return { page: pages.includes(name) ? name : "library", bundle: params.get("bundle"), source: params.get("source"), conversation: params.get("conversation"), comparison: params.get("comparison") };
}
export function bundleRoute(id: string, conversation?: string) { return `asset?bundle=${encodeURIComponent(id)}${conversation ? `&conversation=${encodeURIComponent(conversation)}` : ""}`; }
export function conversationRoute(id: string) { return `conversations?conversation=${encodeURIComponent(id)}`; }
export function sourceRoute(bundleId: string, sourceId: string) { return `${bundleRoute(bundleId)}&source=${encodeURIComponent(sourceId)}`; }
export function comparisonRoute(id?: string, leftBundle?: string) { return `comparisons${id ? `?comparison=${encodeURIComponent(id)}` : leftBundle ? `?bundle=${encodeURIComponent(leftBundle)}` : ""}`; }
