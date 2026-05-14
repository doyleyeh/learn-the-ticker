export type RuntimeSectionState = {
  schemaVersion: "runtime-section-state-v1";
  sectionId: string;
  label: string | null;
  dataOrigin: string;
  sectionStatus: string;
  fallbackReason: string | null;
  freshnessState: string | null;
  sourceHandoffState: string;
  cacheState: string | null;
  evidenceState: string | null;
  diagnostics: Record<string, string | number | boolean | null | string[]>;
};

type BackendRuntimeSectionState = {
  schema_version: string;
  section_id: string;
  label?: string | null;
  data_origin: string;
  section_status: string;
  fallback_reason?: string | null;
  freshness_state?: string | null;
  source_handoff_state?: string;
  cache_state?: string | null;
  evidence_state?: string | null;
  diagnostics?: Record<string, string | number | boolean | null | string[]>;
};

export function runtimeSectionStatesFromPayload(value: unknown): RuntimeSectionState[] {
  if (!value || typeof value !== "object") {
    return [];
  }
  const states = (value as { section_states?: unknown }).section_states;
  if (!Array.isArray(states)) {
    return [];
  }
  return states.filter(isBackendRuntimeSectionState).map((state) => ({
    schemaVersion: "runtime-section-state-v1",
    sectionId: state.section_id,
    label: state.label ?? null,
    dataOrigin: state.data_origin,
    sectionStatus: state.section_status,
    fallbackReason: state.fallback_reason ?? null,
    freshnessState: state.freshness_state ?? null,
    sourceHandoffState: state.source_handoff_state ?? "unknown",
    cacheState: state.cache_state ?? null,
    evidenceState: state.evidence_state ?? null,
    diagnostics: state.diagnostics ?? {}
  }));
}

function isBackendRuntimeSectionState(value: unknown): value is BackendRuntimeSectionState {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<BackendRuntimeSectionState>;
  return (
    candidate.schema_version === "runtime-section-state-v1" &&
    typeof candidate.section_id === "string" &&
    typeof candidate.data_origin === "string" &&
    typeof candidate.section_status === "string"
  );
}
