import type { RuntimeSectionDiagnosticValue } from "../lib/runtimeSectionStates";

export type SectionStateForDisplay = {
  sectionId: string;
  label: string;
  rendering: string;
  evidenceState: string;
  reason: string;
  message: string;
  dataOrigin: string;
  sectionStatus: string;
  fallbackReason: string | null;
  freshnessState: string | null;
  sourceHandoffState: string;
  cacheState: string | null;
  diagnostics: Record<string, RuntimeSectionDiagnosticValue>;
};

type SectionStateNoteProps = {
  state?: SectionStateForDisplay | null;
  weeklyNewsFailureNotice?: boolean;
};

export function isDisplayLiveEvidence(state: SectionStateForDisplay) {
  return state.rendering === "backend_contract" || state.rendering === "source_labeled_live";
}

export function isBackendSectionRequestFailure(state: SectionStateForDisplay) {
  return (
    state.reason === "api_base_unconfigured" ||
    state.reason === "timeout_or_aborted" ||
    state.reason === "backend_status_error" ||
    state.reason === "invalid_contract" ||
    state.reason === "unexpected_error"
  );
}

export function shouldShowSectionStateNote(state: SectionStateForDisplay) {
  if (state.sectionId === "glossary_context") {
    return false;
  }
  if (isDisplayLiveEvidence(state)) {
    return false;
  }
  return isBackendSectionRequestFailure(state) || state.reason === "partial_backend_contract";
}

export function hasUserFacingBackendIssue(states: readonly SectionStateForDisplay[]) {
  return states.some((state) => isBackendSectionRequestFailure(state));
}

export function SectionStateNote({ state, weeklyNewsFailureNotice = false }: SectionStateNoteProps) {
  if (!state || !shouldShowSectionStateNote(state)) {
    return null;
  }

  return (
    <div
      className="source-gap-note section-state-note"
      role="note"
      aria-label={`${state.label} evidence note`}
      data-asset-inline-section-state={state.sectionId}
      data-asset-section-state-placement="inside-panel"
      data-asset-section-rendering={state.rendering}
      data-asset-section-failure-reason={state.reason}
      data-asset-section-evidence-state={state.evidenceState}
      data-asset-section-data-origin={state.dataOrigin}
      data-asset-section-status={state.sectionStatus}
      data-asset-section-fallback-reason={state.fallbackReason ?? state.reason}
      data-asset-section-generation-used-fallback={
        state.diagnostics.used_fallback === true ? "true" : state.diagnostics.used_fallback === false ? "false" : "unknown"
      }
    >
      <strong>{state.label}:</strong> {sectionStateNoteCopy(state)}
      {weeklyNewsFailureNotice ? (
        <span data-weekly-news-fetch-failure-notice>
          {" "}
          This is different from a verified no-high-signal Weekly News result.
        </span>
      ) : null}
    </div>
  );
}

function sectionStateNoteCopy(state: SectionStateForDisplay) {
  if (state.reason === "api_base_unconfigured") {
    return "The live backend is not connected for this render, so this section is showing deterministic local evidence.";
  }
  if (state.reason === "timeout_or_aborted") {
    return "This section timed out before backend evidence returned.";
  }
  if (state.reason === "backend_status_error") {
    return "The backend returned an error for this section.";
  }
  if (state.reason === "invalid_contract") {
    return "The backend returned data, but it did not match the expected section contract.";
  }
  if (state.reason === "partial_backend_contract") {
    return `${state.label} is ${state.sectionStatus.replaceAll("_", " ")} from ${sectionDataOriginLabel(state)}.`;
  }
  return "This section could not load backend evidence for this render.";
}

function sectionDataOriginLabel(state: SectionStateForDisplay) {
  if (state.rendering === "backend_contract") {
    return "live backend evidence";
  }
  if (state.rendering === "source_labeled_live") {
    return "source-labeled local evidence";
  }
  if (state.dataOrigin === "deterministic_fixture") {
    return "deterministic fixture evidence";
  }
  return state.dataOrigin.replaceAll("_", " ");
}
