# EVALS.md

## Main quality gate

Run for every task:

```bash
bash scripts/run_quality_gate.sh
```

## Task-specific checks

The quality gate is required for all tasks. Add the focused checks below when the task touches the related area.

When a task spans multiple categories, run the checks for every touched category. Normal CI must stay deterministic and must not require live provider, news, market-data, or LLM calls.

### Frontend UI tasks

Use for asset pages, comparison pages, citation chips, source drawer, freshness labels, glossary UI, export controls, chat UI, and responsive layout.

Required checks:

```bash
npm test
npm run typecheck
npm run build
bash scripts/run_quality_gate.sh
```

Verify in the changed UI:

- citation chips remain visible near supported claims
- source drawer/source metadata still exposes title, type, publisher, URL, dates, freshness, related claim, and supporting passage
- freshness, stale, unknown, unavailable, and insufficient-evidence states are visible where relevant
- beginner copy avoids buy/sell/hold, allocation, price-target, tax, and brokerage language
- recent developments remain visually separate from stable facts
- mobile and desktop layouts keep Beginner Mode, source access, glossary, chat, and comparison flows usable

### Backend API, schema, retrieval, and comparison tasks

Use for FastAPI routes, response models, retrieval fixtures, comparison generation, overview generation, source metadata, and data-contract changes.

Required checks:

```bash
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Also run a focused pytest slice for the changed module when one exists, for example:

```bash
python3 -m pytest tests/unit/test_retrieval.py tests/unit/test_overview.py -q
```

Verify:

- schema validation covers supported, unsupported, unknown, stale, and insufficient-evidence states
- generated citations bind only to same-asset or same-comparison-pack evidence
- unsupported assets are blocked from generated pages, generated chat, and generated comparisons
- normal CI uses local fixtures or mocks, not live external calls

### Citation, safety, summaries, suitability, and chat tasks

Use for citation validation, generated summaries, recent developments, grounded chat, suitability text, and advice-boundary copy.

Required checks:

```bash
python3 -m pytest tests/unit/test_safety_guardrails.py -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Verify:

- important factual claims have citations or explicit uncertainty
- recent-development claims cite recent-development evidence
- stale sources are labeled stale or suppressed according to the section behavior
- advice-like prompts redirect into educational framing
- no output tells the user to buy, sell, hold, allocate, trade, use a broker, rely on tax advice, or accept a price target

### Ingestion, provider, caching, and freshness tasks

Use for provider adapters, on-demand ingestion, pre-cache workflows, refresh logic, source checksums, freshness hashes, and cache invalidation.

Required checks:

```bash
python3 -m pytest tests -q
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Verify:

- tests use mocked provider responses or local provider fixtures
- no API keys, paid-provider credentials, or live network calls are required in normal CI
- unsupported assets are blocked from generated pages, generated chat, and generated comparisons
- freshness fields include page-level and section-level dates or explicit unknown/stale/unavailable states
- pre-cache and on-demand ingestion paths expose pending, succeeded, failed, unsupported, and stale states where relevant
- provider licensing and export/download constraints are documented before exposing paid or restricted content

### Search, support classification, and entity-resolution tasks

Use for ticker/name search, ambiguous-match states, supported/unsupported classification, and on-demand ingestion routing.

Required checks:

```bash
python3 -m pytest tests -q
npm test
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Verify:

- supported U.S.-listed common stocks and plain-vanilla ETFs resolve by ticker and name
- ambiguous searches show disambiguation instead of silently guessing
- recognized-but-unsupported assets do not link to generated asset pages, chat, or comparisons
- unknown searches say unknown or unavailable without invented facts

### Glossary and beginner-education tasks

Use for curated glossary terms, glossary popovers or bottom sheets, asset-specific glossary context, and beginner readability changes.

Required checks:

```bash
npm test
npm run typecheck
python3 -m pytest tests/unit/test_safety_guardrails.py -q
bash scripts/run_quality_gate.sh
```

Verify:

- core term definitions are generic, beginner-readable, and do not need citations unless they include asset-specific facts
- asset-specific glossary context is grounded in the selected asset knowledge pack
- glossary UI does not obscure citations, source access, chat, or primary page content on mobile

### Export and download tasks

Use for asset-page exports, comparison exports, source-list exports, chat transcript exports, PDF/Markdown/copy output, and export licensing rules.

Required checks:

```bash
python3 -m pytest tests -q
npm test
python3 evals/run_static_evals.py
bash scripts/run_quality_gate.sh
```

Verify:

- exported content includes citations, source metadata, freshness or as-of dates, and the educational disclaimer
- exports preserve advice boundaries and uncertainty labels
- source-list exports include allowed source titles, URLs, dates, retrieved timestamps, and attribution
- paid news or restricted provider content is omitted or summarized unless redistribution rights are documented

### Documentation/control-plane tasks

Use for AGENTS.md, SPEC.md, TASKS.md, EVALS.md, PRD, technical design, and agent-loop process changes.

Required checks:

```bash
bash scripts/run_quality_gate.sh
```

Verify:

- task instructions are narrow enough for one agent-loop cycle
- TASKS.md has a current task or backlog when continuous agent work is expected
- backlog headings are small, sequential, and aligned with MVP scope
- docs do not contradict safety, citation, freshness, or no-live-calls rules
