# MVP Go/No-Go Checklist

Task: T-114

This checklist records production-readiness gates. It does not approve deployment, enable recurring jobs, add paid providers, configure production credentials, or change live-provider defaults.

## Go Criteria

| Gate | Status | Required before public production |
| --- | --- | --- |
| Safety and advice boundary | Regression-covered | Keep zero known buy/sell/hold, allocation, tax, brokerage, guaranteed-return, or unsupported price-target violations in golden tests. |
| Deterministic CI | Regression-covered | Required commands pass without live provider, market-data, news, database, object-storage, Redis, or LLM calls. |
| Search and support states | Regression-covered | Search preserves stock-vs-ETF identity, support-state chips, exact unsupported/no-result behavior, Top-500 manifest-backed stock support, and `A vs B` compare routing. |
| Launch pre-cache readiness | Regression-covered | Cached supported assets render from existing fixtures; eligible-not-cached launch assets remain pending/non-generated until validated source packs exist. |
| Golden Asset Source Handoff | Partially covered, follow-up required | Full enforcement must block unapproved, unclear-rights, parser-invalid, hidden/internal, pending-review, and rejected sources across evidence storage, generation, citations, source drawer, cache, and exports. |
| Top-500 runtime coverage | Regression-covered for fixture manifest | Runtime reads `data/universes/us_common_stocks_top500.current.json`; monthly candidate refresh and promotion workflow remains follow-up. |
| Weekly News Focus | Regression-covered | Official-source priority, U.S. Eastern market-week windows, evidence limits, no padding, and empty states remain covered. |
| AI Comprehensive Analysis | Regression-covered | Suppressed unless at least two high-signal Weekly News items and required canonical citations are available; section order remains fixed when present. |
| Frontend v0.4 workflow | Regression-covered | Home single search, separate comparison workflow, contextual glossary, mobile source/glossary/chat surfaces, and stock-vs-ETF relationship structure remain intact. |
| Exports | Regression-covered | Markdown/JSON exports include citations, freshness, uncertainty, source-use metadata, and disclaimer while excluding restricted raw content. |

## No-Go Until Resolved

| Open risk | Required resolution |
| --- | --- |
| Production admin auth | Add and verify admin ingestion/pre-cache protection before exposing admin routes outside a controlled environment. |
| Rate limiting | Enforce configured search, chat, and ingestion limits before expensive provider, retrieval, ingestion, or LLM work begins. |
| Deployment environment validation | Validate Cloud Run, Vercel, Neon, storage, production CORS origins, and server-only secret configuration without exposing secret values. T-119 covers local CORS/proxy plumbing only. |
| ETF launch manifest coverage | T-120 split implemented; launch expansion required | Keep supported ETF and ETF/ETP recognition manifests separate. Before production launch, replace fixture-sized ETF coverage with reviewed launch manifests and private mirrors. Recognition-only rows must not unlock generated output. |
| Private object storage | Prove private snapshot/artifact storage behavior and safe object namespace validation before production source snapshots or generated artifacts are written. |
| Database migration execution | Run and verify production migration strategy, rollback approach, connection pooling, and read/write permissions. |
| Cloud Run API settings | Review region, `PORT`, min instances, max instances, CORS origins, budget guardrails, logging, and error handling. |
| Cloud Run Job settings | Review manual job trigger, service account scope, job timeout, retries, rate limits, and repository writer readiness. |
| Recurring job decisions | Defer scheduler setup until manual jobs are reliable and source-use review is complete. |
| Source allowlist review | Review every production source domain, source type, official-source status, storage rights, export rights, parser status, source-use policy, and rationale. |
| Live-provider opt-in | Keep live generation disabled by default until server-side keys, budget, validation, fallback, logging, cache gates, and local live-AI review are complete. |
| Paid or broad provider expansion | Defer paid market/reference/news providers until licensing, display, caching, attribution, export, and cost risks are reviewed. |
| Monitoring and alerting | Add operational logging, error reporting, budget alerts, and trust-metric monitoring without raw user text, transcripts, source text, prompts, reasoning, or secrets. |
| Rollback | Define rollback for frontend, API, worker, migrations, generated-output cache, and source snapshot writes. |
| Cost controls | Establish LLM, Cloud Run, database, storage, and provider budget limits before live use. |
| Launch support | Prepare incident response, source correction workflow, safety escalation, and user-facing outage/partial-data copy. |
| Legal/compliance review | Review disclaimer, advice boundaries, data-provider rights, export behavior, source attribution, and Golden Asset Source Handoff approval rules. |

## Production Readiness Decision

Current T-114 decision: **No-go for production deployment**.

Reason: deterministic MVP regression coverage can pass, but launch-sized manifests, repo-native governed source handoff tooling, live-AI local validation, production admin auth, rate limiting, deployment environment validation, private object storage, database migration execution, Cloud Run service settings, Cloud Run Job settings, recurring job policy, full source governance review, live-provider opt-in, monitoring, rollback, cost controls, launch support, and legal/compliance review remain open.

## Explicit Non-Actions In T-114

- No public route path, status-code, or response-schema changes.
- No live OpenRouter, LLM, SEC, issuer, market-data, news, RSS, database, object-storage, Redis, scheduler, Cloud Run, Neon, GCS, Secret Manager, monitoring vendor, or deployment wiring.
- No production dependency additions.
- No edits to current stock or ETF universe manifests.
- No broader source allowlist expansion.
- No generated pages, generated chat answers, generated comparisons, generated risk summaries, prompt rewrites, or live generated-output content changes.
- No credentials, real provider payloads, raw restricted source text, hidden prompts, raw model reasoning, raw user text, raw transcripts, public storage paths, or temporary storage access links.
