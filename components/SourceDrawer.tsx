import type { SourceDocument } from "../lib/fixtures";

type SourceDrawerProps = {
  source: SourceDocument;
  claim: string;
};

export function SourceDrawer({ source, claim }: SourceDrawerProps) {
  return (
    <details className="source-drawer" id={`source-${source.sourceDocumentId}`} open>
      <summary>Source drawer</summary>
      <div className="source-body">
        <div className="source-title-row">
          <h2>{source.title}</h2>
          {source.isOfficial ? <span className="source-badge">Official source</span> : null}
        </div>
        <dl className="source-meta">
          <div>
            <dt>Type</dt>
            <dd>{source.sourceType}</dd>
          </div>
          <div>
            <dt>Publisher</dt>
            <dd>{source.publisher}</dd>
          </div>
          <div>
            <dt>Published</dt>
            <dd>{source.publishedAt}</dd>
          </div>
          <div>
            <dt>Retrieved</dt>
            <dd>{source.retrievedAt}</dd>
          </div>
          <div>
            <dt>Freshness</dt>
            <dd>{source.freshnessState}</dd>
          </div>
        </dl>
        <p className="source-claim">{claim}</p>
        <blockquote>{source.supportingPassage}</blockquote>
        <a href={source.url}>Open source URL</a>
      </div>
    </details>
  );
}
