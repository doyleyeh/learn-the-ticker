import type { ComparisonClaimContext, ComparisonSourceDocument } from "../lib/compare";

type ComparisonSourceDetailsProps = {
  sourceDocument: ComparisonSourceDocument;
  contexts: ComparisonClaimContext[];
};

export function ComparisonSourceDetails({ sourceDocument, contexts }: ComparisonSourceDetailsProps) {
  const publishedOrAsOf = sourceDocument.publishedAt ?? sourceDocument.asOfDate ?? "Unknown";

  return (
    <details
      className="source-drawer"
      id={`source-${sourceDocument.sourceDocumentId}`}
      data-comparison-source-document-id={sourceDocument.sourceDocumentId}
      data-source-freshness-state={sourceDocument.freshnessState}
      open
    >
      <summary>Comparison source metadata</summary>
      <div className="source-body">
        <div className="source-title-row">
          <h3>{sourceDocument.title}</h3>
          {sourceDocument.isOfficial ? <span className="source-badge">Official source</span> : null}
        </div>
        <dl className="source-meta">
          <div>
            <dt>Source document ID</dt>
            <dd>{sourceDocument.sourceDocumentId}</dd>
          </div>
          <div>
            <dt>Title</dt>
            <dd>{sourceDocument.title}</dd>
          </div>
          <div>
            <dt>Type</dt>
            <dd>{sourceDocument.sourceType}</dd>
          </div>
          <div>
            <dt>Publisher</dt>
            <dd>{sourceDocument.publisher}</dd>
          </div>
          <div>
            <dt>Published or as of</dt>
            <dd>{publishedOrAsOf}</dd>
          </div>
          <div>
            <dt>Retrieved</dt>
            <dd>{sourceDocument.retrievedAt}</dd>
          </div>
          <div>
            <dt>Freshness</dt>
            <dd>{sourceDocument.freshnessState}</dd>
          </div>
        </dl>

        <div>
          <h4>Related comparison claims</h4>
          <ul className="source-context-list">
            {contexts.map((context) => (
              <li key={`${context.citationId}-${context.section}-${context.label}`}>
                <strong>{context.citationId}</strong> supports {context.section.toLowerCase()} "{context.label}": {context.claimText}
              </li>
            ))}
          </ul>
        </div>

        <blockquote>{sourceDocument.supportingPassage}</blockquote>
        <a href={sourceDocument.url}>Open source URL</a>
      </div>
    </details>
  );
}
