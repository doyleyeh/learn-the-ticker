# SPEC.md

## Product success

The product helps beginners understand U.S. stocks and plain-vanilla ETFs using plain-English, source-backed explanations.

A successful answer or asset page must help the user understand:

- what the asset is
- what the company does or what the ETF holds
- why people consider it
- the top risks
- how it compares with similar choices
- what changed recently
- which sources support the important claims

## Hard product rules

The product must:

- use source-backed facts before model-written explanations
- separate stable canonical facts from recent developments
- show visible citations for important claims
- show freshness or as-of information
- say unknown, stale, mixed evidence, or insufficient evidence when needed
- keep chat grounded in the selected asset knowledge pack
- avoid personalized investment advice

The product must not:

- tell users what to buy
- tell users what to sell
- tell users how much to allocate
- provide tax advice
- provide unsupported price targets
- present recent news as stable asset identity
- invent facts when evidence is missing

## Technical success

A task is complete only when:

- the requested behavior is implemented
- relevant unit tests pass
- relevant integration tests pass, if applicable
- relevant golden tests pass, if applicable
- citation validation passes when citations are touched
- safety evals pass when summaries, chat, or suitability text are touched
- no unrelated behavior is changed
- the final summary explains changed files, tests run, and remaining risks

## MVP success checklist

MVP is ready when:

- search resolves supported stocks and ETFs
- unsupported assets show a clear unsupported state
- stock and ETF pages render beginner summaries
- top risks show exactly three items first
- recent developments are visually separate from stable facts
- key claims have visible citations
- source drawer shows source metadata and supporting passages
- freshness labels are visible
- comparison works for at least the golden assets
- chat answers only from the selected asset knowledge pack
- safety guardrails block buy/sell, price-target, and allocation advice
