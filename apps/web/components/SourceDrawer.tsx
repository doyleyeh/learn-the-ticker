import type { CitationContext, SourceDocument } from "../lib/fixtures";

type SourceDrawerProps = {
  source: SourceDocument;
  claim: string;
  contexts?: CitationContext[];
};

export function SourceDrawer({ source, claim, contexts = [] }: SourceDrawerProps) {
  const publishedOrAsOf = source.publishedAt ?? source.asOfDate ?? "Unknown";
  const supportingPassages = contexts.length
    ? [...new Set(contexts.map((context) => context.supportingPassage))]
    : [source.supportingPassage];

  return (
    <details
      className="source-drawer"
      id={`source-${source.sourceDocumentId}`}
      data-source-document-id={source.sourceDocumentId}
      data-source-freshness-state={source.freshnessState}
      open
    >
      <summary>Source drawer</summary>
      <div className="source-body">
        <div className="source-title-row">
          <h2>{source.title}</h2>
          {source.isOfficial ? <span className="source-badge">Official source</span> : null}
        </div>
        <dl className="source-meta">
          <div>
            <dt>Source document ID</dt>
            <dd>{source.sourceDocumentId}</dd>
          </div>
          <div>
            <dt>Title</dt>
            <dd>{source.title}</dd>
          </div>
          <div>
            <dt>Type</dt>
            <dd>{source.sourceType}</dd>
          </div>
          <div>
            <dt>Publisher</dt>
            <dd>{source.publisher}</dd>
          </div>
          <div>
            <dt>URL</dt>
            <dd>{source.url}</dd>
          </div>
          <div>
            <dt>Published or as of</dt>
            <dd>{publishedOrAsOf}</dd>
          </div>
          <div>
            <dt>Retrieved</dt>
            <dd>{source.retrievedAt}</dd>
          </div>
          <div>
            <dt>Freshness</dt>
            <dd>{source.freshnessState}</dd>
          </div>
          <div>
            <dt>Official source</dt>
            <dd>{source.isOfficial ? "Yes" : "No"}</dd>
          </div>
        </dl>

        <div>
          <h3>Related claim context</h3>
          {contexts.length ? (
            <ul className="source-context-list">
              {contexts.map((context) => (
                <li key={`${context.citationId}-${context.sectionId}-${context.claimContext}`}>
                  <strong>{context.citationId}</strong> supports {context.sectionTitle}: {context.claimContext}
                </li>
              ))}
            </ul>
          ) : (
            <p className="source-claim">{claim}</p>
          )}
        </div>

        <div>
          <h3>Supporting passage</h3>
          {supportingPassages.map((passage) => (
            <blockquote key={passage}>{passage}</blockquote>
          ))}
        </div>
        <a href={source.url}>Open source URL</a>
      </div>
    </details>
  );
}
