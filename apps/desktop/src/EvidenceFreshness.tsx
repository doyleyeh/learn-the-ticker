import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { BundleFreshness, EvidenceBundle, SourceAge } from "./contracts";
import { api } from "./client";

const AgeContext = createContext<BundleFreshness | undefined>(undefined);
const reasons: Record<SourceAge["reason"], string> = {
  within_age_limit: "Recorded dates are within the source age limit; latest coverage is not established.",
  old_dates: "Stale for current research — recorded dates exceed the source age limit. Historical evidence remains available.",
  missing_dates: "Unknown freshness — publication and as-of dates are missing. Retrieval time alone is insufficient.",
  future_dates: "Unknown freshness — a recorded date is in the future.",
  unverified: "Unknown freshness — independent source verification is missing.",
  unregistered: "Unknown freshness — no applicable source age rule is registered.",
  rights_changed: "Unknown freshness — the current source-use rule does not match this saved source.",
};

export function SnapshotStatus({ bundle }: { bundle: EvidenceBundle }) {
  const available = { available: "Available", partial: "Partially available", stale: "Stale", unavailable: "Unavailable" };
  return <div className="snapshot-status"><p>Snapshot saved: {bundle.created_at ?? "Unknown"}</p>
    <p>Availability when saved: {bundle.state ? available[bundle.state] : "Unknown"}. Saving or opening a version does not refresh its evidence.</p>
  </div>;
}

export function EvidenceFreshness({ bundleId, children }: { bundleId?: string; children: ReactNode }) {
  const [value, setValue] = useState<BundleFreshness>();
  const [failed, setFailed] = useState<string>();
  useEffect(() => {
    if (!bundleId) return;
    const controller = new AbortController();
    void api<BundleFreshness>(`/api/bundles/${encodeURIComponent(bundleId)}/freshness`, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted && result.bundle_id === bundleId) setValue(result);
      }).catch(() => { if (!controller.signal.aborted) setFailed(bundleId); });
    return () => controller.abort();
  }, [bundleId]);
  // Never flash another saved version's assessment during navigation.
  const assessment = value?.bundle_id === bundleId ? value : undefined;
  return <AgeContext.Provider value={assessment}>
    <section className="plain-panel" aria-label="Evidence freshness">
      <h2>Evidence freshness</h2>
      {assessment ? <><p>Source age assessed {assessment.assessed_at} from saved dates only. No new source retrieval.</p>
        <p>{assessment.sources.filter((source) => source.state === "stale").length} stale · {assessment.sources.filter((source) => source.state === "unknown").length} unknown · {assessment.sources.filter((source) => source.state === "within_age_limit").length} within source age limits.</p>
        {!assessment.sources.length && <p>No source dates are available in this version.</p>}
      </> : <p>{failed === bundleId && bundleId ? "Source-age assessment unavailable. Original saved evidence remains readable." : "Source age has not been assessed for this version."}</p>}
      <p>Source age does not establish a live quote or complete latest coverage. Inspect original dates and limits in Sources; refresh evidence online to check for newer information.</p>
    </section>{children}
  </AgeContext.Provider>;
}

export function SourceAgeLabel({ sourceId }: { sourceId: string }) {
  const row = useContext(AgeContext)?.sources.find((source) => source.source_id === sourceId);
  return <p className="ticker-meta" data-source-age={row?.state ?? "unknown"}>{row ? reasons[row.reason] : "Freshness unassessed for this saved source."}</p>;
}
