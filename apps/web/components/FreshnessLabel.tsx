import type { FreshnessState } from "../lib/fixtures";

type FreshnessLabelProps = {
  label: string;
  value: string | undefined;
  state: FreshnessState;
};

export function FreshnessLabel({ label, value, state }: FreshnessLabelProps) {
  return (
    <span className={`freshness-label freshness-${state}`} data-freshness-state={state}>
      <span>{label}</span>
      <strong>{value ?? "Unknown"}</strong>
      <em>{state}</em>
    </span>
  );
}
