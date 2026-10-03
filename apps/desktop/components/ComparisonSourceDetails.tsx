import type { ComparisonClaimContext, ComparisonEvidenceAvailability, ComparisonSourceDocument } from "../lib/compare";

type ComparisonSourceDetailsProps = {
  sourceDocument: ComparisonSourceDocument;
  contexts: ComparisonClaimContext[];
  sourceReference?: ComparisonEvidenceAvailability["source_references"][number];
};

export function ComparisonSourceDetails({
  sourceDocument,
  contexts,
  sourceReference
}: ComparisonSourceDetailsProps) {
  const publishedOrAsOf = sourceDocument.published_at ?? sourceDocument.as_of_date ?? "Unknown";

  return (
    <details
      className="source-drawer"
      id={`source-${sourceDocument.source_document_id}`}
      data-comparison-source-document-id={sourceDocument.source_document_id}
      data-source-freshness-state={sourceDocument.freshness_state}
      data-comparison-source-quality={sourceDocument.source_quality}
      data-comparison-source-use-policy={sourceDocument.source_use_policy}
      data-comparison-source-asset={sourceReference?.asset_ticker ?? ""}
      open
    >
      <summary>Comparison source metadata</summary>
      <div className="source-body">
        <div className="source-title-row">
          <h3>{sourceDocument.title}</h3>
          {sourceDocument.is_official ? <span className="source-badge">Official source</span> : null}
        </div>
        <dl className="source-meta">
          <div>
            <dt>Source document ID</dt>
            <dd>{sourceDocument.source_document_id}</dd>
          </div>
          <div>
            <dt>Title</dt>
            <dd>{sourceDocument.title}</dd>
          </div>
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
            <dd>{publishedOrAsOf}</dd>
          </div>
          <div>
            <dt>Retrieved</dt>
            <dd>{sourceDocument.retrieved_at}</dd>
          </div>
          <div>
            <dt>Freshness</dt>
            <dd>{sourceDocument.freshness_state}</dd>
          </div>
          <div>
            <dt>Source quality</dt>
            <dd>{sourceDocument.source_quality}</dd>
          </div>
          <div>
            <dt>Allowlist status</dt>
            <dd>{sourceDocument.allowlist_status}</dd>
          </div>
          <div>
            <dt>Source-use policy</dt>
            <dd>{sourceDocument.source_use_policy}</dd>
          </div>
          <div>
            <dt>Full-text export allowed</dt>
            <dd>{String(sourceDocument.permitted_operations.can_export_full_text)}</dd>
          </div>
          {sourceReference ? (
            <div>
              <dt>Asset ticker</dt>
              <dd>{sourceReference.asset_ticker}</dd>
            </div>
          ) : null}
          <div>
            <dt>URL</dt>
            <dd>{sourceDocument.url}</dd>
          </div>
        </dl>

        <div>
          <h4>Related comparison claims</h4>
          {contexts.length > 0 ? (
            <ul className="source-context-list">
              {contexts.map((context) => (
                <li key={`${context.citation_id}-${context.section}-${context.label}`}>
                  <strong>{context.citation_id}</strong> supports {context.section.toLowerCase()} "{context.label}": {context.claim_text}
                </li>
              ))}
            </ul>
          ) : (
            <p>No rendered generated comparison claims are bound to this source in the current deterministic contract.</p>
          )}
        </div>

        <p>
          <strong>Supporting passage</strong>
        </p>
        <blockquote>{sourceDocument.supporting_passage}</blockquote>
        <a href={sourceDocument.url}>Open source URL</a>
      </div>
    </details>
  );
}
