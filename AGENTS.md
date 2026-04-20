# AGENTS.md

## Project identity

This project is a citation-first beginner U.S. stock and ETF learning assistant.

The product helps beginners understand U.S.-listed common stocks and plain-vanilla ETFs using:

- official or structured sources first
- plain-English explanations
- visible citations
- source freshness
- separated stable facts and recent developments
- educational framing instead of investment advice

This product is not:

- a stock picker
- a trading bot
- a brokerage app
- a portfolio optimizer
- a personalized financial advisor

## Required reading before work

Before changing code, read:

1. SPEC.md
2. TASKS.md
3. EVALS.md
4. docs/learn_the_ticker_PRD.md
5. docs/learn_the_ticker_technical_design_spec.md

If these files conflict, follow this order:

1. Safety and advice-boundary rules
2. SPEC.md
3. TASKS.md
4. EVALS.md
5. PRD / technical design details

## Development loop

For every task:

1. Run `git status --short`.
2. Restate the current task and acceptance criteria.
3. Inspect relevant files before editing.
4. Make the smallest high-confidence change.
5. Run the required tests/evals from EVALS.md.
6. If tests fail, diagnose the failure before editing again.
7. Write a short summary of changed files, tests run, results, and risks.

## Git rules

You may run:

- `git status`
- `git diff`
- `git log`
- `git branch`
- `git show`

Do not run these unless the user or harness explicitly allows it:

- `git commit`
- `git push`
- `git reset --hard`
- `git clean -fd`
- `git rebase`
- `git merge`
- `git checkout main`
- `git push --force`

The harness script handles branch creation, journaling, tests, and commits.

## Product guardrails

Never introduce:

- buy/sell/hold recommendations
- personalized allocation advice
- exact position sizing
- unsupported price targets
- tax advice
- brokerage/trading behavior
- unsupported claims presented as facts
- recent news that overwrites canonical facts

Advice-like user questions must be redirected into educational framing.

Example:

User: “Should I buy QQQ?”

Safe style:

“I can’t tell you whether to buy it. I can help you understand what QQQ holds, how concentrated it is, how it differs from a broader ETF, and what risks a beginner should understand.”

## Citation rules

Important factual claims must have citations.

A citation is valid only if:

- the source exists
- the source belongs to the same asset or comparison pack
- the source supports the claim
- recent-development claims cite recent-development sources
- stale sources are labeled stale
- wrong-asset citations are rejected

If evidence is missing, say unknown, stale, mixed evidence, or insufficient evidence.

## Testing expectations

When touching retrieval, summaries, chat, citations, or safety, run:

- citation evals
- safety evals
- golden asset tests

When touching frontend UI, verify:

- citation chips
- source drawer
- freshness labels
- stale/unknown states
- beginner readability

When touching backend APIs, verify:

- schema validation
- unit tests
- endpoint tests
- no live external calls in normal CI

## Dependency policy

Do not add production dependencies without explaining:

- why the dependency is needed
- alternatives considered
- security/licensing risk
- whether it affects deployment
