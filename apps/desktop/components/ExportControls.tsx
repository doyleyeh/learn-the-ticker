"use client";

import { useState } from "react";
import {
  EXPORT_LICENSING_CONTEXT,
  EXPORT_TRUST_CONTEXT,
  postChatTranscriptExport,
  type AssetExportContractRendering,
  type AssetExportContractValidation,
  type ExportResponsePreview
} from "../lib/exportControls";
import { buildTrustMetricSurfaceDescriptor } from "../lib/trustMetrics";

type LinkExportControl = {
  kind: "link";
  controlId: "asset-page" | "asset-source-list" | "comparison";
  label: string;
  href: string;
  helper: string;
  contract?: AssetExportContractValidation | null;
};

type ChatTranscriptExportControl = {
  kind: "chat-transcript";
  controlId: "chat-transcript";
  label: string;
  ticker: string;
  question: string;
  conversationId?: string | null;
  sessionLifecycleState?: string;
  sessionExportAvailable?: boolean;
  sessionExpiresAt?: string | null;
  helper: string;
};

type ExportControlItem = LinkExportControl | ChatTranscriptExportControl;

type ExportControlsProps = {
  title: string;
  controls: ExportControlItem[];
  marker: string;
  helper?: string;
};

type ChatExportState = "idle" | "loading" | "ready" | "copied" | "error";

export function ExportControls({ title, controls, marker, helper = EXPORT_TRUST_CONTEXT }: ExportControlsProps) {
  const trustMetricDescriptor = buildTrustMetricSurfaceDescriptor({
    eventType: "export_usage",
    workflowArea: "export",
    selectedSection: marker,
    exportContentType: controls.map((control) => control.controlId).join(","),
    exportFormat: "markdown",
    citationCount: controls.reduce((count, control) => count + (control.kind === "link" ? control.contract?.citationCount ?? 0 : 0), 0),
    sourceDocumentCount: controls.reduce((count, control) => count + (control.kind === "link" ? control.contract?.sourceCount ?? 0 : 0), 0)
  });

  return (
    <section
      className="plain-panel export-controls"
      aria-labelledby={`${marker}-heading`}
      data-export-controls={marker}
      data-export-format="markdown"
      data-export-supported-scope="markdown-json-citations-sources-freshness-disclaimer"
      data-export-mobile-behavior="compact-stacked-controls"
      data-export-mobile-no-overlap="in-flow-compact-panel"
      data-export-unrestricted-raw-text="false"
      data-export-restricted-provider-payloads="false"
      data-export-hidden-prompts="false"
      data-export-raw-model-reasoning="false"
      data-export-secret-exposure="false"
      data-export-relative-api
      data-export-no-live-external
      data-trust-metric-schema-version={trustMetricDescriptor.schemaVersion}
      data-trust-metric-mode={trustMetricDescriptor.mode}
      data-trust-metric-event={trustMetricDescriptor.eventType}
      data-trust-metric-workflow-area={trustMetricDescriptor.workflowArea}
      data-trust-metric-occurred-at={trustMetricDescriptor.occurredAt}
      data-trust-metric-persistence={trustMetricDescriptor.persistence}
      data-trust-metric-external-analytics={trustMetricDescriptor.externalAnalytics}
      data-trust-metric-live-external-calls={trustMetricDescriptor.liveExternalCalls}
      data-trust-metric-export-content-type={trustMetricDescriptor.exportContentType}
      data-trust-metric-export-format={trustMetricDescriptor.exportFormat}
      data-trust-metric-citation-count={trustMetricDescriptor.citationCount}
      data-trust-metric-source-document-count={trustMetricDescriptor.sourceDocumentCount}
      data-trust-metric-citation-coverage-event="citation_coverage"
      data-trust-metric-freshness-accuracy-event="freshness_accuracy"
    >
      <div className="section-heading export-controls-header">
        <p className="eyebrow">Save output</p>
        <h2 id={`${marker}-heading`}>{title}</h2>
      </div>
      <p className="export-helper-copy">{helper}</p>
      <p className="source-gap-note" data-export-licensing-context>
        {EXPORT_LICENSING_CONTEXT}
      </p>
      <div className="export-control-list" aria-label={`${title} controls`}>
        {controls.map((control) => {
          if (control.kind === "link") {
            const controlTrustMetricDescriptor = buildTrustMetricSurfaceDescriptor({
              eventType: "export_usage",
              workflowArea: "export",
              selectedSection: control.controlId,
              exportContentType: control.contract?.contentType ?? control.controlId,
              exportFormat: "markdown",
              citationCount: control.contract?.citationCount ?? 0,
              sourceDocumentCount: control.contract?.sourceCount ?? 0,
              freshnessState: control.contract?.freshnessState ?? "unknown",
              evidenceState: control.contract?.exportState ?? "local_fallback",
              comparisonLeftTicker: control.contract?.leftTicker,
              comparisonRightTicker: control.contract?.rightTicker
            });

            return (
            <a
              className="export-button"
              href={control.href}
              key={control.controlId}
              data-export-control={control.controlId}
              data-export-href={control.href}
              data-export-contract-rendering={control.contract?.rendering ?? "local_fallback"}
              data-export-contract-source={control.contract?.rendering ?? "local_fallback"}
              data-export-contract-content-type={control.contract?.contentType ?? control.controlId}
              data-export-control-mobile-behavior="compact-full-width"
              data-export-control-supported-formats="markdown-json"
              data-export-control-scope="citations-sources-freshness-disclaimer"
              data-trust-metric-event={controlTrustMetricDescriptor.eventType}
              data-trust-metric-workflow-area={controlTrustMetricDescriptor.workflowArea}
              data-trust-metric-export-content-type={controlTrustMetricDescriptor.exportContentType}
              data-trust-metric-export-format={controlTrustMetricDescriptor.exportFormat}
              data-trust-metric-citation-count={controlTrustMetricDescriptor.citationCount}
              data-trust-metric-source-document-count={controlTrustMetricDescriptor.sourceDocumentCount}
              data-trust-metric-freshness-state={controlTrustMetricDescriptor.freshnessState}
              data-trust-metric-evidence-state={controlTrustMetricDescriptor.evidenceState}
              data-trust-metric-left-ticker={controlTrustMetricDescriptor.comparisonLeftTicker ?? ""}
              data-trust-metric-right-ticker={controlTrustMetricDescriptor.comparisonRightTicker ?? ""}
              aria-label={`${control.label}. ${control.helper}`}
            >
              <span>{control.label}</span>
              <small>{control.helper}</small>
              <ExportContractMarker rendering={control.contract?.rendering ?? "local_fallback"} contract={control.contract} />
            </a>
            );
          }

          return <ChatTranscriptExportButton control={control} key={control.controlId} />;
        })}
      </div>
    </section>
  );
}

function ExportContractMarker({
  rendering,
  contract
}: {
  rendering: AssetExportContractRendering;
  contract?: AssetExportContractValidation | null;
}) {
  return (
    <small
      className="export-contract-marker"
      data-export-contract-marker={rendering}
      data-export-contract-schema={contract?.validationSchemaVersion ?? "local_fallback"}
      data-export-contract-binding-scope={contract?.bindingScope ?? "local_fallback"}
      data-export-contract-state={contract?.exportState ?? "local_fallback"}
      data-export-contract-freshness={contract?.freshnessState ?? "local_fallback"}
      data-export-contract-as-of={contract?.asOfDate ?? "local_fallback"}
      data-export-contract-citation-count={contract?.citationCount ?? 0}
      data-export-contract-source-count={contract?.sourceCount ?? 0}
      data-export-contract-left-ticker={contract?.leftTicker ?? "local_fallback"}
      data-export-contract-right-ticker={contract?.rightTicker ?? "local_fallback"}
      data-export-contract-comparison-id={contract?.comparisonId ?? "local_fallback"}
    >
      {rendering === "backend_contract"
        ? "Backend export contract validated; relative Markdown link remains the baseline."
        : "Local fallback rendering; relative Markdown link remains available."}
    </small>
  );
}

function ChatTranscriptExportButton({ control }: { control: ChatTranscriptExportControl }) {
  const [state, setState] = useState<ChatExportState>("idle");
  const [exportResponse, setExportResponse] = useState<ExportResponsePreview | null>(null);
  const [error, setError] = useState("");
  const buttonTrustMetricDescriptor = buildTrustMetricSurfaceDescriptor({
    eventType: "export_usage",
    workflowArea: "export",
    assetTicker: control.ticker.toUpperCase(),
    selectedSection: "chat_transcript",
    exportContentType: "chat_transcript",
    exportFormat: "markdown",
    citationCount: 0,
    sourceDocumentCount: 0,
    evidenceState: control.sessionExportAvailable === true ? "available" : control.sessionLifecycleState ?? "unavailable"
  });
  const resultTrustMetricDescriptor = exportResponse
    ? buildTrustMetricSurfaceDescriptor({
        eventType: "export_usage",
        workflowArea: "export",
        assetTicker: exportResponse.selectedTicker,
        selectedSection: "chat_transcript",
        exportContentType: "chat_transcript",
        exportFormat: "markdown",
        citationCount: exportResponse.citationCount,
        sourceDocumentCount: exportResponse.sourceCount,
        evidenceState: exportResponse.export_state
      })
    : null;

  async function prepareTranscript() {
    if (state === "loading") {
      return;
    }

    setState("loading");
    setError("");

    try {
      const nextResponse = await postChatTranscriptExport(control.ticker, control.question, control.conversationId);
      setExportResponse(nextResponse);
      setState("ready");
    } catch (caught) {
      setExportResponse(null);
      setError(caught instanceof Error ? caught.message : "The local transcript export failed.");
      setState("error");
    }
  }

  async function copyMarkdown() {
    if (!exportResponse?.rendered_markdown) {
      return;
    }

    try {
      await navigator.clipboard.writeText(exportResponse.rendered_markdown);
      setState("copied");
    } catch {
      setState("ready");
    }
  }

  return (
    <div
      className="chat-export-control"
      data-export-control={control.controlId}
      data-export-control-mobile-behavior="compact-full-width"
      data-export-control-supported-formats="markdown"
      data-export-control-scope="chat-transcript-citations-session-metadata-disclaimer"
    >
      <button
        className="export-button"
        type="button"
        onClick={() => void prepareTranscript()}
        disabled={state === "loading"}
        data-export-post-url={`/api/assets/${encodeURIComponent(control.ticker.toUpperCase())}/chat/export`}
        data-chat-export-conversation-id={control.conversationId ? "present" : "absent"}
        data-chat-export-session-lifecycle={control.sessionLifecycleState ?? "unavailable"}
        data-chat-export-session-export-available={control.sessionExportAvailable === true ? "true" : "false"}
        data-chat-export-session-expires-at={control.sessionExpiresAt ?? "unknown"}
        data-chat-export-no-raw-transcript-analytics="true"
        data-chat-export-no-hidden-prompts="true"
        data-chat-export-no-raw-model-reasoning="true"
        data-trust-metric-event={buttonTrustMetricDescriptor.eventType}
        data-trust-metric-workflow-area={buttonTrustMetricDescriptor.workflowArea}
        data-trust-metric-asset-ticker={buttonTrustMetricDescriptor.assetTicker}
        data-trust-metric-export-content-type={buttonTrustMetricDescriptor.exportContentType}
        data-trust-metric-export-format={buttonTrustMetricDescriptor.exportFormat}
        data-trust-metric-citation-count={buttonTrustMetricDescriptor.citationCount}
        data-trust-metric-source-document-count={buttonTrustMetricDescriptor.sourceDocumentCount}
        data-trust-metric-evidence-state={buttonTrustMetricDescriptor.evidenceState}
        aria-label={`${control.label}. ${control.helper}`}
      >
        <span>{state === "loading" ? "Preparing transcript" : control.label}</span>
        <small>{control.helper}</small>
      </button>
      {state === "error" ? (
        <p className="search-status status-unknown" role="alert" data-export-state="error">
          {error}
        </p>
      ) : null}
      {exportResponse ? (
        <div
          className="export-result"
          data-export-state={exportResponse.export_state}
          data-chat-export-contract-source={exportResponse.contractSource}
          data-chat-export-conversation-id={exportResponse.conversationIdPresent ? "present" : "absent"}
          data-chat-export-session-lifecycle={exportResponse.sessionLifecycleState}
          data-chat-export-session-export-available={exportResponse.sessionExportAvailable ? "true" : "false"}
          data-chat-export-session-expires-at={exportResponse.sessionExpiresAt}
          data-chat-export-validation-schema={exportResponse.validationSchemaVersion}
          data-chat-export-binding-scope={exportResponse.bindingScope}
          data-chat-export-citation-count={exportResponse.citationCount}
          data-chat-export-source-count={exportResponse.sourceCount}
          data-chat-export-safe-session-records={exportResponse.sourceFromSafeSessionRecords ? "true" : "false"}
          data-chat-export-used-existing-chat-contract={exportResponse.usedExistingChatContract ? "true" : "false"}
          data-chat-export-no-live-external={exportResponse.noLiveExternalCalls ? "true" : "false"}
          data-chat-export-mobile-result="internal-scroll"
          data-chat-export-no-raw-transcript-analytics="true"
          data-chat-export-no-hidden-prompts="true"
          data-chat-export-no-raw-model-reasoning="true"
          data-trust-metric-event={resultTrustMetricDescriptor?.eventType}
          data-trust-metric-workflow-area={resultTrustMetricDescriptor?.workflowArea}
          data-trust-metric-asset-ticker={resultTrustMetricDescriptor?.assetTicker}
          data-trust-metric-export-content-type={resultTrustMetricDescriptor?.exportContentType}
          data-trust-metric-export-format={resultTrustMetricDescriptor?.exportFormat}
          data-trust-metric-citation-count={resultTrustMetricDescriptor?.citationCount}
          data-trust-metric-source-document-count={resultTrustMetricDescriptor?.sourceDocumentCount}
          data-trust-metric-evidence-state={resultTrustMetricDescriptor?.evidenceState}
        >
          <p className="search-status" aria-live="polite">
            Transcript export is {exportResponse.export_state} from{" "}
            {exportResponse.contractSource === "session_contract" ? "the session contract" : "the single-turn fallback"}.
            Markdown is ready to copy from the local API response.
          </p>
          <button className="citation-chip" type="button" onClick={() => void copyMarkdown()} data-export-copy-markdown>
            {state === "copied" ? "Copied Markdown" : "Copy Markdown"}
          </button>
          <textarea
            readOnly
            value={exportResponse.rendered_markdown}
            aria-label="Chat transcript Markdown"
            data-export-rendered-markdown
          />
        </div>
      ) : null}
    </div>
  );
}
