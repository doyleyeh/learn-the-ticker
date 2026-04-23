Review this pull request for Learn the Ticker, a citation-first beginner U.S. stock and ETF learning assistant.

Authority order:

1. Safety and advice-boundary rules
2. docs/learn_the_ticker_PRD.md
3. docs/learn_the_ticker_technical_design_spec.md
4. docs/learn-the-ticker_proposal.md
5. SPEC.md
6. TASKS.md
7. EVALS.md

Focus on P0/P1 issues only:

- broken tests or missing required quality-gate coverage
- changes that conflict with the PRD/TDS/proposal authority order
- missing citation validation
- unsupported factual claims
- buy/sell/hold recommendation leakage
- personalized allocation advice
- unsupported price targets
- Weekly News Focus or AI Comprehensive Analysis mixed into stable canonical facts
- Weekly News Focus using non-allowlisted, duplicate, promotional, irrelevant, or license-disallowed sources
- AI Comprehensive Analysis generated without enough high-signal Weekly News Focus evidence
- stale, unknown, unavailable, partial, or insufficient-evidence states missing where evidence is incomplete
- source-use policy or raw-text-rights violations
- unsupported, out-of-scope, or pending-ingestion assets receiving generated pages, chat, comparisons, or risk summaries
- live provider, market-data, news, or LLM calls required in normal CI
- OpenRouter or provider secrets exposed in browser code, `NEXT_PUBLIC_*`, docs, logs, health responses, or env examples
- root npm scripts no longer delegating to `apps/web`
- Docker Compose/local-stack scaffolding becoming required for CI
- destructive Git or deployment behavior
- changes that conflict with AGENTS.md, SPEC.md, TASKS.md, or EVALS.md

Do not nitpick style unless it affects correctness, trust, safety, source rights, deployment safety, or maintainability.

Return:

- summary
- high-risk findings
- suggested fixes
- whether the PR should merge
