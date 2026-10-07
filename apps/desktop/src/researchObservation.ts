import { api, watchJob } from "./client";
import type { RuntimeEvent } from "./contracts";

export const activeResearch = (status: string) => status === "queued" || status === "running";

// A socket carries progress only. Authoritative state is always read from the
// existing job; reconnect, polling and cleanup never submit another generation.
export function observeResearch<T extends { status: string }>(id: string, onJob: (job: T) => void,
  onEvent: (event: RuntimeEvent) => void, onError: (error: unknown) => void) {
  const controller = new AbortController();
  let busy = false, finished = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const refresh = async () => {
    if (busy || finished || controller.signal.aborted) return;
    busy = true;
    if (timer) clearTimeout(timer);
    try {
      const value = await api<T>(`/api/jobs/${encodeURIComponent(id)}`, { signal: controller.signal });
      if (!controller.signal.aborted) {
        finished = !activeResearch(value.status);
        onJob(value);
      }
    } catch (error) { if (!controller.signal.aborted) onError(error); }
    finally {
      busy = false;
      if (!finished && !controller.signal.aborted) timer = setTimeout(() => { void refresh(); }, 2000);
    }
  };
  const close = watchJob(id, (event) => {
    if (controller.signal.aborted || finished) return;
    onEvent(event);
    if (event.kind.startsWith("run.") || event.kind === "evidence.registered") void refresh();
  }, () => { void refresh(); });
  void refresh();
  return () => { controller.abort(); if (timer) clearTimeout(timer); close(); };
}
