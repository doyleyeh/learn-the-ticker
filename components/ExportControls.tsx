"use client";

import { useState } from "react";
import {
  EXPORT_LICENSING_CONTEXT,
  EXPORT_TRUST_CONTEXT,
  postChatTranscriptExport,
  type ExportResponsePreview
} from "../lib/exportControls";

type LinkExportControl = {
  kind: "link";
  controlId: "asset-page" | "asset-source-list" | "comparison";
  label: string;
  href: string;
  helper: string;
};

type ChatTranscriptExportControl = {
  kind: "chat-transcript";
  controlId: "chat-transcript";
  label: string;
  ticker: string;
  question: string;
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
  return (
    <section
      className="plain-panel export-controls"
      aria-labelledby={`${marker}-heading`}
      data-export-controls={marker}
      data-export-format="markdown"
      data-export-relative-api
      data-export-no-live-external
    >
      <div className="section-heading">
        <p className="eyebrow">Save output</p>
        <h2 id={`${marker}-heading`}>{title}</h2>
      </div>
      <p>{helper}</p>
      <p className="source-gap-note" data-export-licensing-context>
        {EXPORT_LICENSING_CONTEXT}
      </p>
      <div className="export-control-list" aria-label={`${title} controls`}>
        {controls.map((control) =>
          control.kind === "link" ? (
            <a
              className="export-button"
              href={control.href}
              key={control.controlId}
              data-export-control={control.controlId}
              data-export-href={control.href}
              aria-label={`${control.label}. ${control.helper}`}
            >
              <span>{control.label}</span>
              <small>{control.helper}</small>
            </a>
          ) : (
            <ChatTranscriptExportButton control={control} key={control.controlId} />
          )
        )}
      </div>
    </section>
  );
}

function ChatTranscriptExportButton({ control }: { control: ChatTranscriptExportControl }) {
  const [state, setState] = useState<ChatExportState>("idle");
  const [exportResponse, setExportResponse] = useState<ExportResponsePreview | null>(null);
  const [error, setError] = useState("");

  async function prepareTranscript() {
    if (state === "loading") {
      return;
    }

    setState("loading");
    setError("");

    try {
      const nextResponse = await postChatTranscriptExport(control.ticker, control.question);
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
    <div className="chat-export-control" data-export-control={control.controlId}>
      <button
        className="export-button"
        type="button"
        onClick={() => void prepareTranscript()}
        disabled={state === "loading"}
        data-export-post-url={`/api/assets/${encodeURIComponent(control.ticker.toUpperCase())}/chat/export`}
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
        <div className="export-result" data-export-state={exportResponse.export_state}>
          <p className="search-status" aria-live="polite">
            Transcript export is {exportResponse.export_state}. Markdown is ready to copy from the local API response.
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
