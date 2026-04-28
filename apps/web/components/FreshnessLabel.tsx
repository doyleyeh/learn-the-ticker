import type { FreshnessState } from "../lib/fixtures";

type FreshnessLabelProps = {
  label: string;
  value: string | undefined;
  state: FreshnessState;
};

export function FreshnessLabel({ label, value, state }: FreshnessLabelProps) {
  const freshnessLabel = {
    fresh: "Current evidence",
    stale: "Stale evidence",
    unknown: "Unknown",
    unavailable: "Unavailable",
    partial: "Partially available",
    insufficient_evidence: "Insufficient evidence"
  }[state];

  return (
    <span
      className={`freshness-label freshness-${state}`}
      data-freshness-state={state}
      data-governed-golden-freshness-label="api-backed-section-state"
    >
      <span>{label}</span>
      <strong>{value ?? "Unknown"}</strong>
      <em>{freshnessLabel ?? state}</em>
    </span>
  );
}
