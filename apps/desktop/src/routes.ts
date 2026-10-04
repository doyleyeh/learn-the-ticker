export const pages = ["library", "saved", "conversations", "connections", "imports", "asset"];
export function routeFromHash(hash: string) {
  const [name, query = ""] = hash.replace(/^#/, "").split("?", 2);
  const params = new URLSearchParams(query);
  return { page: pages.includes(name) ? name : "library", bundle: params.get("bundle"), source: params.get("source") };
}
export function bundleRoute(id: string) { return `asset?bundle=${encodeURIComponent(id)}`; }
export function sourceRoute(bundleId: string, sourceId: string) { return `${bundleRoute(bundleId)}&source=${encodeURIComponent(sourceId)}`; }
