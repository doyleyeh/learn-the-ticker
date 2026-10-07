const DEFAULT_OPTIONAL_BACKEND_FETCH_TIMEOUT_MS = 3000;

export function optionalBackendFetcher(timeoutMs = DEFAULT_OPTIONAL_BACKEND_FETCH_TIMEOUT_MS): typeof fetch {
  return async (input, init) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await globalThis.fetch(input, { ...init, signal: controller.signal });
    } finally {
      clearTimeout(timeout);
    }
  };
}
