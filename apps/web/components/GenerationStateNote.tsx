import type { GenerationDiagnostics } from "../lib/fixtures";
import type { RuntimeSectionState } from "../lib/runtimeSectionStates";

type GenerationState =
  | "live_generated"
  | "deterministic_fallback"
  | "live_timeout_fallback"
  | "suppressed_insufficient_evidence"
  | "backend_error"
  | "unknown";

type GenerationStateNoteProps = {
  label: string;
  diagnostics?: GenerationDiagnostics | null;
  sectionState?: RuntimeSectionState | null;
  analysisAvailable?: boolean;
  compact?: boolean;
};

export function GenerationStateNote({
  label,
  diagnostics,
  sectionState,
  analysisAvailable = true,
  compact = false
}: GenerationStateNoteProps) {
  const state = generationState(diagnostics, sectionState, analysisAvailable);
  const reasonCodes = diagnostics?.fallbackReasonCodes ?? fallbackReasonCodesFromSection(sectionState);

  return (
    <p
      className={compact ? "source-gap-note compact-generation-state" : "source-gap-note generation-state-note"}
      data-generation-state={state}
      data-generation-label={label}
      data-generation-attempted-live={diagnostics?.attemptedLive ? "true" : "false"}
      data-generation-used-fallback={diagnostics?.usedFallback ? "true" : "false"}
      data-generation-fallback-reason-codes={reasonCodes.join(",") || "none"}
      data-generation-attempt-count={diagnostics?.attemptCount ?? 0}
      data-generation-section-status={sectionState?.sectionStatus ?? "unknown"}
    >
      <strong>{label}:</strong> {generationStateCopy(state, diagnostics, reasonCodes)}
    </p>
  );
}

export function generationState(
  diagnostics?: GenerationDiagnostics | null,
  sectionState?: RuntimeSectionState | null,
  analysisAvailable = true
): GenerationState {
  if (!analysisAvailable || sectionState?.sectionStatus === "insufficient_evidence") {
    return "suppressed_insufficient_evidence";
  }
  if (sectionState?.sectionStatus === "unavailable" || sectionState?.dataOrigin === "unavailable") {
    return "backend_error";
  }
  if (!diagnostics) {
    return "unknown";
  }
  if (!diagnostics.usedFallback && diagnostics.attemptedLive) {
    return "live_generated";
  }
  if (diagnostics.usedFallback && diagnostics.fallbackReasonCodes.some((code) => code.includes("timeout"))) {
    return "live_timeout_fallback";
  }
  if (diagnostics.usedFallback) {
    return "deterministic_fallback";
  }
  return "unknown";
}

function generationStateCopy(
  state: GenerationState,
  diagnostics?: GenerationDiagnostics | null,
  reasonCodes: string[] = []
) {
  if (state === "live_generated") {
    return `Live LLM generation passed validation${diagnostics?.modelName ? ` with ${diagnostics.modelName}` : ""}.`;
  }
  if (state === "live_timeout_fallback") {
    return "Live LLM generation timed out, so this section shows validated deterministic fallback output.";
  }
  if (state === "deterministic_fallback") {
    if (reasonCodes.some((code) => code.includes("schema_validation") || code.includes("structured_output_validation"))) {
      return `Live LLM output did not pass structured validation, so validated deterministic fallback output is shown (${reasonCodes.join(", ")}).`;
    }
    return reasonCodes.length
      ? `Validated deterministic fallback output is shown (${reasonCodes.join(", ")}).`
      : "Validated deterministic fallback output is shown.";
  }
  if (state === "suppressed_insufficient_evidence") {
    return "Analysis is suppressed until enough approved evidence is available.";
  }
  if (state === "backend_error") {
    return "Generation state is unavailable because backend evidence did not load for this section.";
  }
  return "Generation provenance is not available for this render.";
}

function fallbackReasonCodesFromSection(sectionState?: RuntimeSectionState | null) {
  const reasonCodes = sectionState?.diagnostics?.fallback_reason_codes;
  if (Array.isArray(reasonCodes)) {
    return reasonCodes.filter((code): code is string => typeof code === "string");
  }
  return sectionState?.fallbackReason ? sectionState.fallbackReason.split(",").filter(Boolean) : [];
}
