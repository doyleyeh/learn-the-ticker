"use client";

import { FormEvent, useMemo, useState } from "react";
import { ExportControls } from "./ExportControls";
import { postAssetChat, type AssetChatResponse, type ChatSessionMetadata, type ChatSourceDocument } from "../lib/assetChat";
import { buildTrustMetricSurfaceDescriptor } from "../lib/trustMetrics";

type AssetChatPanelProps = {
  ticker: string;
  assetName: string;
};

type ChatRequestState = "empty" | "loading" | "answered" | "error";
type StarterPromptIntent =
  | "identity"
  | "business-model"
  | "holdings-exposure"
  | "top-risk"
  | "recent-developments"
  | "advice-boundary";

type StarterPrompt = {
  intent: StarterPromptIntent;
  question: string;
};

const stockFixtureTickers = new Set(["AAPL"]);

function starterPromptsForAsset(ticker: string, assetName: string): StarterPrompt[] {
  const normalizedTicker = ticker.toUpperCase();
  const isStockFixture = stockFixtureTickers.has(normalizedTicker);
  const assetLabel = isStockFixture ? assetName.replace(/ Inc\.$/, "") : normalizedTicker;

  return [
    {
      intent: "identity",
      question: `What is ${normalizedTicker} in plain English?`
    },
    isStockFixture
      ? {
          intent: "business-model",
          question: `How does ${assetLabel}'s business model work?`
        }
      : {
          intent: "holdings-exposure",
          question: `What does ${normalizedTicker} hold, and what fund exposure does it give?`
        },
    {
      intent: "top-risk",
      question: `What top risk should a beginner understand about ${normalizedTicker}?`
    },
    {
      intent: "recent-developments",
      question: `What changed recently for ${normalizedTicker}?`
    },
    {
      intent: "advice-boundary",
      question: `How should a beginner frame ${normalizedTicker} without a personal recommendation?`
    }
  ];
}

export function AssetChatPanel({ ticker, assetName }: AssetChatPanelProps) {
  const [question, setQuestion] = useState("");
  const [requestState, setRequestState] = useState<ChatRequestState>("empty");
  const [response, setResponse] = useState<AssetChatResponse | null>(null);
  const [submittedQuestion, setSubmittedQuestion] = useState("");
  const [error, setError] = useState("");

  const starterPrompts = useMemo(() => starterPromptsForAsset(ticker, assetName), [assetName, ticker]);

  async function submitQuestion(nextQuestion: string) {
    const trimmed = nextQuestion.trim();
    if (!trimmed || requestState === "loading") {
      return;
    }

    setQuestion(trimmed);
    setRequestState("loading");
    setError("");

    try {
      const conversationId =
        response?.session?.lifecycle_state === "active" && response.session.conversation_id
          ? response.session.conversation_id
          : null;
      const nextResponse = await postAssetChat(ticker, trimmed, conversationId);
      setResponse(nextResponse);
      setSubmittedQuestion(trimmed);
      setRequestState("answered");
    } catch (caught) {
      setResponse(null);
      setError(caught instanceof Error ? caught.message : "The local chat request failed.");
      setRequestState("error");
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion(question);
  }

  const isAdviceRedirect = response?.safety_classification === "personalized_advice_redirect";
  const isCompareRedirect = response?.safety_classification === "compare_route_redirect";
  const isUnsupported = response?.safety_classification === "unsupported_asset_redirect" || response?.asset.supported === false;
  const isInsufficientEvidence =
    response?.safety_classification === "insufficient_evidence" ||
    response?.direct_answer.toLowerCase().startsWith("insufficient evidence");
  const sourceDocumentsByCitationId = new Map(
    response?.source_documents.map((sourceDocument) => [sourceDocument.citation_id, sourceDocument]) ?? []
  );
  const sessionMetadata = response?.session ?? null;
  const chatAnswerTrustMetricDescriptor = response
    ? buildTrustMetricSurfaceDescriptor({
        eventType: "chat_answer_outcome",
        workflowArea: "chat",
        assetTicker: response.asset.ticker,
        assetSupportState: response.asset.status,
        citationCount: response.citations.length,
        sourceDocumentCount: response.source_documents.length,
        evidenceState: sessionMetadata?.latest_evidence_state ?? response.safety_classification,
        freshnessState: sessionMetadata?.latest_freshness_state ?? "unknown",
        safetyClassification: response.safety_classification,
        chatOutcome: isAdviceRedirect
          ? "safety_redirect"
          : isCompareRedirect
            ? "compare_route_redirect"
            : isUnsupported
              ? "unsupported_asset_redirect"
              : isInsufficientEvidence
                ? "insufficient_evidence"
                : "answered"
      })
    : null;
  const chatSafetyRedirectTrustMetricDescriptor =
    response && isAdviceRedirect
      ? buildTrustMetricSurfaceDescriptor({
          eventType: "chat_safety_redirect",
          workflowArea: "chat",
          assetTicker: response.asset.ticker,
          assetSupportState: response.asset.status,
          safetyClassification: response.safety_classification,
          chatOutcome: "safety_redirect",
          evidenceState: sessionMetadata?.latest_evidence_state ?? "educational_redirect"
        })
      : null;
  const safetyRedirectRateTrustMetricDescriptor =
    response && isAdviceRedirect
      ? buildTrustMetricSurfaceDescriptor({
          eventType: "safety_redirect_rate",
          workflowArea: "safety",
          assetTicker: response.asset.ticker,
          assetSupportState: response.asset.status,
          safetyClassification: response.safety_classification,
          chatOutcome: "safety_redirect"
        })
      : null;

  return (
    <section className="plain-panel asset-chat-panel" aria-labelledby="asset-chat-heading">
      <div className="section-heading">
        <p className="eyebrow">Grounded chat</p>
        <h2 id="asset-chat-heading">Ask about this asset</h2>
      </div>
      <p>
        Ask a beginner question about {assetName}. Answers come from the selected local asset knowledge pack and show source
        details when the backend returns grounded citations.
      </p>

      <div
        className="starter-prompt-group inline-tools"
        aria-label="Beginner starter questions"
        data-chat-starter-group="beginner-prompts"
      >
        {starterPrompts.map((prompt) => (
          <button
            className="citation-chip starter-prompt-button"
            key={prompt.intent}
            type="button"
            data-chat-starter-intent={prompt.intent}
            onClick={() => void submitQuestion(prompt.question)}
            disabled={requestState === "loading"}
          >
            {prompt.question}
          </button>
        ))}
      </div>

      <form className="search-workflow" onSubmit={handleSubmit}>
        <label htmlFor={`asset-chat-question-${ticker}`}>Question</label>
        <div className="search-row">
          <input
            id={`asset-chat-question-${ticker}`}
            value={question}
            placeholder={`Ask about ${ticker}`}
            onChange={(event) => setQuestion(event.target.value)}
            disabled={requestState === "loading"}
          />
          <button className="search-button" type="submit" disabled={requestState === "loading" || !question.trim()}>
            {requestState === "loading" ? "Asking" : "Ask"}
          </button>
        </div>
      </form>

      {requestState === "empty" ? (
        <p className="search-status status-empty" data-chat-state="empty">
          No chat answer yet. Try an asset identity, holdings, risk, recent-development, or beginner framing question.
        </p>
      ) : null}

      {requestState === "loading" ? (
        <p className="search-status status-loading" data-chat-state="loading" aria-live="polite">
          Checking the local grounded chat endpoint.
        </p>
      ) : null}

      {requestState === "error" ? (
        <p className="search-status status-unknown" data-chat-state="error" role="alert">
          {error}
        </p>
      ) : null}

      {response ? (
        <article
          className={`timeline-item chat-answer ${
            isUnsupported || isInsufficientEvidence ? "unknown-state" : ""
          }`}
          data-chat-state={response.safety_classification}
          data-trust-metric-chat-answer-event={chatAnswerTrustMetricDescriptor?.eventType}
          data-trust-metric-schema-version={chatAnswerTrustMetricDescriptor?.schemaVersion}
          data-trust-metric-mode={chatAnswerTrustMetricDescriptor?.mode}
          data-trust-metric-workflow-area={chatAnswerTrustMetricDescriptor?.workflowArea}
          data-trust-metric-occurred-at={chatAnswerTrustMetricDescriptor?.occurredAt}
          data-trust-metric-persistence={chatAnswerTrustMetricDescriptor?.persistence}
          data-trust-metric-external-analytics={chatAnswerTrustMetricDescriptor?.externalAnalytics}
          data-trust-metric-live-external-calls={chatAnswerTrustMetricDescriptor?.liveExternalCalls}
          data-trust-metric-asset-ticker={chatAnswerTrustMetricDescriptor?.assetTicker}
          data-trust-metric-asset-support-state={chatAnswerTrustMetricDescriptor?.assetSupportState}
          data-trust-metric-citation-count={chatAnswerTrustMetricDescriptor?.citationCount}
          data-trust-metric-source-document-count={chatAnswerTrustMetricDescriptor?.sourceDocumentCount}
          data-trust-metric-evidence-state={chatAnswerTrustMetricDescriptor?.evidenceState}
          data-trust-metric-freshness-state={chatAnswerTrustMetricDescriptor?.freshnessState}
          data-trust-metric-safety-classification={chatAnswerTrustMetricDescriptor?.safetyClassification}
          data-trust-metric-chat-outcome={chatAnswerTrustMetricDescriptor?.chatOutcome}
          data-trust-metric-chat-safety-redirect-event={chatSafetyRedirectTrustMetricDescriptor?.eventType ?? "not_applicable"}
          data-trust-metric-safety-redirect-rate-event={safetyRedirectRateTrustMetricDescriptor?.eventType ?? "not_applicable"}
          aria-busy={requestState === "loading"}
        >
          {isAdviceRedirect ? <p className="eyebrow">Educational redirect</p> : null}
          {isCompareRedirect ? <p className="eyebrow">Comparison workflow redirect</p> : null}
          {isUnsupported ? <p className="eyebrow">Unsupported or unknown asset</p> : null}
          {isInsufficientEvidence ? <p className="eyebrow">Insufficient evidence</p> : null}
          <h3>Direct answer</h3>
          <p>{response.direct_answer}</p>
          <h3>Why it matters</h3>
          <p>{response.why_it_matters}</p>

          {response.uncertainty.length > 0 ? (
            <div>
              <h3>Limits and uncertainty</h3>
              <ul>
                {response.uncertainty.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {response.citations.length > 0 ? (
            <div>
              <h3>Citations</h3>
              <div className="chip-row" aria-label="Chat citations">
                {response.citations.map((citation) => {
                  const sourceDocument = sourceDocumentsByCitationId.get(citation.citation_id);
                  return (
                    <a
                      className="citation-chip"
                      href={`#chat-source-${citation.citation_id}`}
                      key={citation.citation_id}
                      data-chat-citation-id={citation.citation_id}
                      data-source-document-id={citation.source_document_id}
                      aria-label={`Open chat source details for ${sourceDocument?.title ?? citation.source_document_id}`}
                    >
                      [{citation.citation_id}]
                    </a>
                  );
                })}
              </div>
            </div>
          ) : (
            <p className="notice-text" data-chat-citations="none">
              No citations are shown when the response is an educational redirect, unsupported state, or insufficient-evidence
              state without grounded factual claims.
            </p>
          )}

          {response.source_documents.length > 0 ? (
            <div className="section-stack" aria-label="Chat source metadata">
              {response.source_documents.map((sourceDocument) => (
                <ChatSourceDetails key={sourceDocument.citation_id} sourceDocument={sourceDocument} />
              ))}
            </div>
          ) : null}

          {sessionMetadata ? <ChatSessionContractMarker session={sessionMetadata} selectedTicker={ticker} /> : null}

          {submittedQuestion ? (
            <ExportControls
              title="Save chat transcript"
              marker={`chat-export-${ticker.toLowerCase()}`}
              helper="Save the current chat transcript with the backend safety label, uncertainty notes, citation metadata when present, the educational disclaimer, and licensing scope."
              controls={[
                {
                  kind: "chat-transcript",
                  controlId: "chat-transcript",
                  label: "Prepare transcript Markdown",
                  ticker,
                  question: submittedQuestion,
                  conversationId:
                    sessionMetadata?.lifecycle_state === "active" && sessionMetadata.export_available
                      ? sessionMetadata.conversation_id
                      : null,
                  sessionLifecycleState: sessionMetadata?.lifecycle_state ?? "unavailable",
                  sessionExportAvailable: sessionMetadata?.export_available === true,
                  sessionExpiresAt: sessionMetadata?.expires_at ?? null,
                  helper:
                    "Uses POST /api/assets/{ticker}/chat/export with an active conversation ID when available, then falls back to the single-turn Markdown export."
                }
              ]}
            />
          ) : null}
        </article>
      ) : null}
    </section>
  );
}

function ChatSessionContractMarker({ session, selectedTicker }: { session: ChatSessionMetadata; selectedTicker: string }) {
  const sessionTicker = session.selected_asset?.ticker ?? selectedTicker.toUpperCase();
  return (
    <p
      className="source-gap-note"
      data-chat-session-contract="chat-session-contract-v1"
      data-chat-session-conversation-id={session.conversation_id ? "present" : "absent"}
      data-chat-session-selected-ticker={sessionTicker}
      data-chat-session-lifecycle={session.lifecycle_state}
      data-chat-session-export-available={session.export_available ? "true" : "false"}
      data-chat-session-expires-at={session.expires_at ?? "unknown"}
      data-chat-session-turn-count={session.turn_count}
      data-chat-session-browser-persistence="none"
    >
      Accountless session metadata is held only for this chat interaction. Export uses the session transcript contract when the
      conversation is active and exportable; otherwise it uses the single-turn fallback.
    </p>
  );
}

function ChatSourceDetails({ sourceDocument }: { sourceDocument: ChatSourceDocument }) {
  const trustMetricDescriptor = buildTrustMetricSurfaceDescriptor({
    eventType: "source_drawer_usage",
    workflowArea: "source_drawer",
    selectedSection: "chat_source_metadata",
    citationCount: 1,
    sourceDocumentCount: 1,
    freshnessState: sourceDocument.freshness_state,
    evidenceState: "available"
  });

  return (
    <details
      className="source-drawer"
      id={`chat-source-${sourceDocument.citation_id}`}
      data-trust-metric-schema-version={trustMetricDescriptor.schemaVersion}
      data-trust-metric-mode={trustMetricDescriptor.mode}
      data-trust-metric-event={trustMetricDescriptor.eventType}
      data-trust-metric-workflow-area={trustMetricDescriptor.workflowArea}
      data-trust-metric-occurred-at={trustMetricDescriptor.occurredAt}
      data-trust-metric-persistence={trustMetricDescriptor.persistence}
      data-trust-metric-external-analytics={trustMetricDescriptor.externalAnalytics}
      data-trust-metric-live-external-calls={trustMetricDescriptor.liveExternalCalls}
      data-trust-metric-selected-section={trustMetricDescriptor.selectedSection}
      data-trust-metric-citation-count={trustMetricDescriptor.citationCount}
      data-trust-metric-source-document-count={trustMetricDescriptor.sourceDocumentCount}
      data-trust-metric-freshness-state={trustMetricDescriptor.freshnessState}
      data-trust-metric-evidence-state={trustMetricDescriptor.evidenceState}
      open
    >
      <summary>Chat source metadata</summary>
      <div className="source-body">
        <div className="source-title-row">
          <h3>{sourceDocument.title}</h3>
          {sourceDocument.is_official ? <span className="source-badge">Official source</span> : null}
        </div>
        <dl className="source-meta">
          <div>
            <dt>Type</dt>
            <dd>{sourceDocument.source_type}</dd>
          </div>
          <div>
            <dt>Publisher</dt>
            <dd>{sourceDocument.publisher}</dd>
          </div>
          <div>
            <dt>Published or as of</dt>
            <dd>{sourceDocument.published_at ?? sourceDocument.as_of_date ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Retrieved</dt>
            <dd>{sourceDocument.retrieved_at}</dd>
          </div>
          <div>
            <dt>Freshness</dt>
            <dd>{sourceDocument.freshness_state}</dd>
          </div>
        </dl>
        <p className="source-claim">
          Citation {sourceDocument.citation_id} uses chunk {sourceDocument.chunk_id} from {sourceDocument.source_document_id}.
        </p>
        <blockquote>{sourceDocument.supporting_passage}</blockquote>
        <a href={sourceDocument.url}>Open source URL</a>
      </div>
    </details>
  );
}
