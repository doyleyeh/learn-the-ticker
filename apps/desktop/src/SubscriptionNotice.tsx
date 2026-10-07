export function SubscriptionNotice({ showConnectionLink }: { showConnectionLink: boolean }) {
  return <aside className="plain-panel" aria-labelledby="subscription-requirement-title">
    <h2 id="subscription-requirement-title">A paid AI agent subscription is required for AI features</h2>
    <p>Learn the Ticker is free and open source. Bring your own paid subscription to a supported commercial AI agent service to create new research and answers.</p>
    <p>Your connected agent helps find and review sources, analyze evidence, summarize research and generate explanations. Selected questions and evidence are sent to that provider when you allow cloud research.</p>
    <p>Without a supported connection, you can still read saved research, conversations and explanations, and use built-in definitions. New AI content is unavailable. Free-account access has not been verified in this app.</p>
    <p><strong>Current preview: ChatGPT / Codex only.</strong> Gemini and Claude support is still in development. A paid plan alone does not guarantee a compatible connection. Usage stays within your included allowance; the app stops when access or quota is unavailable, with no paid API fallback or automatic overages.</p>
    {showConnectionLink && <a href="#connections">Set up your agent</a>}
  </aside>;
}
