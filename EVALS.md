# EVALS.md

## Main quality gate

Run for every task:

```bash
bash scripts/run_quality_gate.sh
```

## Task-specific checks

The quality gate is required for all tasks. Add the focused checks below when the task touches the related area.

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
- provider licensing and export/download constraints are documented before exposing paid or restricted content

### Documentation/control-plane tasks

Use for AGENTS.md, SPEC.md, TASKS.md, EVALS.md, PRD, technical design, and agent-loop process changes.

Required checks:

```bash
bash scripts/run_quality_gate.sh
```

Verify:

- task instructions are narrow enough for one agent-loop cycle
- TASKS.md has a current task or backlog when continuous agent work is expected
- docs do not contradict safety, citation, freshness, or no-live-calls rules
