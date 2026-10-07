import type { FreshnessState } from "../lib/fixtures";

type FreshnessLabelProps = {
  label: string;
  value: string | undefined;
  state: FreshnessState;
  density?: "default" | "compact";
};

function freshnessStateLabel(state: FreshnessState) {
  return {
    fresh: "Current evidence",
    stale: "Stale evidence",
    unknown: "Unknown",
    unavailable: "Unavailable",
    partial: "Partially available",
    insufficient_evidence: "Insufficient evidence"
  }[state];
}

export function FreshnessLabel({ label, value, state, density = "default" }: FreshnessLabelProps) {
  const freshnessLabel = freshnessStateLabel(state);

  return (
    <span
      className={`freshness-label freshness-${state} freshness-${density}`}
      data-freshness-state={state}
      data-freshness-density={density}
      data-governed-golden-freshness-label="api-backed-section-state"
    >
      <span>{label}</span>
      <strong>{value ?? "Unknown"}</strong>
      <em>{freshnessLabel ?? state}</em>
    </span>
  );
}

export function FreshnessDisclosure({ label, value, state }: Omit<FreshnessLabelProps, "density">) {
  const freshnessLabel = freshnessStateLabel(state);

  return (
    <details
      className={`freshness-disclosure freshness-${state}`}
      data-freshness-state={state}
      data-freshness-density="micro"
      data-governed-golden-freshness-label="api-backed-section-state"
    >
      <summary>
        <span>{label}</span>
        <strong>{freshnessLabel ?? state}</strong>
      </summary>
      <div className="freshness-disclosure-body">
        <span>{label}</span>
        <strong>{value ?? "Unknown"}</strong>
        <em>{freshnessLabel ?? state}</em>
      </div>
    </details>
  );
}
