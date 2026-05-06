# Learn the Ticker Deployment Guide

This guide documents the intended low-cost deployment path for Learn the Ticker. It is a planning and operations reference, not an instruction to deploy immediately.

The current project is still a personal MVP/framework demo with deterministic local quality gates. Production deployment, recurring production jobs, broad paid-provider integrations, admin auth hardening, rate limiting, and launch-sized reviewed manifests remain later work until a narrow launch-readiness task promotes them.

## Project Alignment

Use this guide together with:

- `docs/learn_the_ticker_PRD.md`
- `docs/learn_the_ticker_technical_design_spec.md`
- `docs/LIGHTWEIGHT_DATA_POLICY.md`
- `SPEC.md`
- `TASKS.md`
- `EVALS.md`

Current repository layout:

| Area | Current path |
|---|---|
| Web app | `apps/web` |
| Backend API package | `backend` |
| API Dockerfile | `docker/api/Dockerfile` |
| Local web Dockerfile | `docker/web/Dockerfile` |
| Local stack | `docker-compose.yml` |
| Root npm workspace scripts | `package.json` |
| Backend dependencies | `requirements.txt` |
| Local env examples | `.env.example`, `apps/web/.env.example` |

Do not use `services/api`, `services/worker`, `doc/`, `pnpm`, or `uv` commands for this repository unless those paths or tools are intentionally introduced later. The current workflow uses root npm workspace scripts and the root FastAPI package.

## Target Architecture

| Component | Provider | Default direction |
|---|---|---|
| Frontend | Vercel Hobby | Next.js app from `apps/web` |
| Backend API | Google Cloud Run | Container built from `docker/api/Dockerfile`, `min-instances=0`, conservative max instances |
| Jobs | Cloud Run Jobs later | Manual-first only after a real production worker entrypoint exists |
| Database | Neon Free Postgres | Pooled connection string with SSL for production-like durable storage |
| Object storage | Google Cloud Storage later | Private regional bucket; local scaffold uses MinIO/S3-style env names |
| Queue | Postgres first | Use `ingestion_jobs`; no Redis/Pub/Sub production queue for first deploy |
| Monitoring | Google Cloud | Cloud Logging and Error Reporting first |
| LLM | Mock by default, optional OpenRouter | Server-side only; live generation gated by env flags and operator limits |

The product remains educational only. Deployed output must not provide buy/sell/hold recommendations, price targets, personalized allocations, portfolio construction, guaranteed-return claims, brokerage instructions, or tax advice.

## Deployment Readiness Gates

Before a public or semi-public deployment, complete these gates:

- `bash scripts/run_quality_gate.sh` passes locally.
- `docker compose config` validates the local scaffold.
- Local web/API smoke confirms `NEXT_PUBLIC_API_BASE_URL`, `API_BASE_URL`, `CORS_ALLOWED_ORIGINS`, and the Next `/api/:path*` rewrite behavior.
- Admin ingestion and pre-cache routes have production-appropriate auth and rate limiting, or are disabled from public access.
- Production env values are placeholders or deployment-managed secrets only; no real secrets are committed or copied into docs.
- Any live provider or OpenRouter use is explicitly enabled, server-side only, budget/rate limited outside the repo, and validated through citation/safety gates.
- Full production deployment work has an explicit task in `TASKS.md`; ordinary docs or local-MVP work should not silently expand the deployment surface.

## Cost Guardrails

- Create a Google Cloud billing budget alert before deploying Cloud Run resources.
- Keep Cloud Run services on request-based billing with `--min-instances=0`.
- Set a conservative Cloud Run `--max-instances` value, such as `2`, for the first personal deployment.
- Do not add always-on Redis, Pub/Sub, Cloud SQL, VMs, or paid queues for v1.
- Use Postgres as the first production job ledger/queue.
- Keep Cloud Scheduler disabled until manual Cloud Run Jobs are proven useful.
- Keep OpenRouter in mock mode until a key, explicit model chain, platform/API-key limits, rate limits, citation validation, and `LLM_LIVE_GENERATION_ENABLED=true` are intentionally configured.
- Store only source snapshots, parsed text, generated artifacts, and diagnostics that the product is allowed to retain.

## Source Governance Defaults

- `docs/LIGHTWEIGHT_DATA_POLICY.md` is the active personal-MVP data policy: official sources first, reputable third-party/provider fallback when official data is incomplete, source labels everywhere, and partial rendering instead of manual source-pack blocking.
- The top-500 U.S. common-stock universe remains manifest-owned at `data/universes/us_common_stocks_top500.current.json`; `TOP500_UNIVERSE_MANIFEST_URI` is the private production mirror variable.
- Monthly top-500 candidates should be written as `data/universes/us_common_stocks_top500.candidate.YYYY-MM.json`, validated, diffed, manually approved, then promoted to `data/universes/us_common_stocks_top500.current.json`.
- Supported ETF generated-output coverage should remain split from broader ETF/ETP recognition. The supported ETF manifest is `data/universes/us_equity_etfs_supported.current.json`; recognition-only rows must not unlock generated pages, chat, comparisons, Weekly News Focus, AI Comprehensive Analysis, or exports.
- Lightweight personal-MVP rendering may use source-labeled official/provider fallback data for eligible assets, but clearly unsupported products such as leveraged, inverse, active, commodity, crypto, fixed income, single-stock, option-income/buffer, ETN, ETV, CEF, and unclear products must remain blocked.
- Golden Asset Source Handoff remains the strict/audit-quality approval layer between retrieval and evidence use. Lightweight display may use rights-safe source-labeled records before full handoff only when provenance, freshness, partial states, and export limits remain visible.
- Raw source text storage is rights-tiered. Restricted provider payloads, full article text, secrets, hidden prompts, and raw model reasoning must not appear in public citation resolution or exports.

## Frontend: Vercel Hobby

Create one Vercel project for the web app.

Recommended project settings:

- Framework preset: Next.js
- Root directory: `apps/web`
- Install command: Vercel default npm install, or `npm install` if an explicit command is required
- Build command: `npm run build`
- Output directory: Vercel default for Next.js
- Production environment variable: `NEXT_PUBLIC_API_BASE_URL=https://<cloud-run-api-url>`

Alternative monorepo-root setup:

- Root directory: repository root
- Build command: `npm --workspace apps/web run build`
- Keep the Vercel output configuration aligned with the `apps/web` Next.js app

Keep API keys, OpenRouter secrets, market/reference-provider secrets, and storage credentials out of Vercel frontend variables. The browser should call only the project API through `NEXT_PUBLIC_API_BASE_URL` or the Next `/api/:path*` rewrite configured in `apps/web/next.config.mjs`.

Preview deployments may point to the same API at first. If preview data isolation becomes necessary, create a separate Cloud Run API service and database branch later.

## Backend API: Cloud Run

The current API deploys from the repository root using `docker/api/Dockerfile`, which starts:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Default Cloud Run choices:

- Region: `us-central1`
- Billing: request-based
- Minimum instances: `0`
- Maximum instances: `2` initially
- CPU/memory: start small, for example `1 CPU`, `512Mi`
- Authentication: public HTTP only after app-level auth/rate-limit decisions are resolved for admin routes
- Secrets: Google Secret Manager or deployment-managed secrets, injected as environment variables

Build the container with the repository root as the Docker context:

```bash
PROJECT_ID="<gcp-project-id>"
REGION="us-central1"
API_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/learn-the-ticker/api:latest"

gcloud artifacts repositories create learn-the-ticker \
  --repository-format=docker \
  --location="${REGION}"

gcloud auth configure-docker "${REGION}-docker.pkg.dev"
docker build -f docker/api/Dockerfile -t "${API_IMAGE}" .
docker push "${API_IMAGE}"
```

Then deploy with production-safe defaults. Start with mock providers and deterministic behavior:

```bash
gcloud run deploy learn-the-ticker-api \
  --image="${API_IMAGE}" \
  --region="${REGION}" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=2 \
  --cpu=1 \
  --memory=512Mi \
  --set-env-vars="APP_ENV=production,PORT=8000,DATA_POLICY_MODE=lightweight,LIGHTWEIGHT_LIVE_FETCH_ENABLED=false,LIGHTWEIGHT_PROVIDER_FALLBACK_ENABLED=true,LIGHTWEIGHT_FETCH_TIMEOUT_SECONDS=15,LLM_PROVIDER=mock,LLM_LIVE_GENERATION_ENABLED=false,OPENROUTER_PAID_FALLBACK_ENABLED=false,TOP500_UNIVERSE_MANIFEST_URI=data/universes/us_common_stocks_top500.current.json"
```

Before pointing real traffic at the service:

- Set `CORS_ALLOWED_ORIGINS` to the Vercel production URL and any allowed preview URLs.
- Move `DATABASE_URL`, OpenRouter keys, provider keys, and object-storage credentials into Secret Manager or deployment-managed secrets.
- Use a real production mirror URI for `TOP500_UNIVERSE_MANIFEST_URI` only after the launch manifest is reviewed and uploaded.
- Add production mirror env vars for ETF manifests only when the strict supported/recognition split is ready for that deployment mode.
- Confirm `/health`, `/api/health`, `/api/search?q=VOO`, `/api/assets/VOO`, `/api/assets/VOO/overview`, and `/api/assets/VOO/sources` respond without live external calls.

Rollback:

```bash
gcloud run revisions list --service=learn-the-ticker-api --region="${REGION}"
gcloud run services update-traffic learn-the-ticker-api \
  --region="${REGION}" \
  --to-revisions="<previous-revision>=100"
```

## Jobs: Cloud Run Jobs

The repository currently has an `ingestion-worker` Docker Compose scaffold that intentionally prints a placeholder and does not start live ingestion. Do not deploy it as a production worker as-is.

Cloud Run Jobs are the intended later production shape, but only after:

- a real job entrypoint exists in the repo;
- admin auth and rate limiting are handled for job-triggering API routes;
- durable `ingestion_jobs` storage is configured;
- source snapshot, knowledge-pack, Weekly News, and generated-output cache persistence are configured with rights-safe storage;
- live acquisition is explicitly gated and passes readiness checks.

For the top-500 manifest refresh specifically, prefer GitHub Actions first because the output is a source-controlled candidate manifest and diff report that requires manual approval. Cloud Scheduler plus Cloud Run Job is a later option and must still require manual approval before promotion to `us_common_stocks_top500.current.json`.

## Database: Neon Free Postgres

Create one Neon project for production-like durable storage.

- Use the pooled connection string for Cloud Run.
- Include SSL, for example `sslmode=require`, in `DATABASE_URL`.
- Enable `pgvector` only before vector features are intentionally enabled.
- Keep database storage small by limiting raw text retention and pruning stale snapshots when allowed by source-use policy.
- Keep `DATABASE_MIGRATIONS_ENABLED=false` unless a narrow migration task explicitly enables migration execution.

Current backend dependencies use SQLAlchemy, Alembic, and psycopg from `requirements.txt`, but production migration execution should be promoted as a separate deployment-hardening task.

## Storage

Local Docker Compose uses MinIO-compatible S3-style placeholders:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`

Production direction is a private Google Cloud Storage regional bucket in `us-central1`, but the current code/config examples still use the local S3-style placeholders. Add GCS-specific adapter configuration only when production object storage is implemented.

Recommended object key families once private object storage is live:

- `raw/<asset_type>/<ticker>/<source_document_id>.<ext>`
- `parsed/<asset_type>/<ticker>/<source_document_id>.txt`
- `generated/<schema_version>/<ticker>/<artifact_id>.json`
- `diagnostics/<job_id>.json`
- `universe/us_common_stocks_top500.current.json`
- `universe/us_equity_etfs_supported.current.json`
- `universe/us_etp_recognition.current.json`

Do not make the bucket public.

## OpenRouter

OpenRouter must remain server-side only. Safe first boot keeps:

- `LLM_PROVIDER=mock`
- `LLM_LIVE_GENERATION_ENABLED=false`
- `OPENROUTER_PAID_FALLBACK_ENABLED=false`

When live generation is intentionally enabled later:

- Provide `OPENROUTER_API_KEY` through Secret Manager or the server-side process environment only.
- Set `LLM_PROVIDER=openrouter` and `LLM_LIVE_GENERATION_ENABLED=true`.
- Configure `OPENROUTER_BASE_URL`, `OPENROUTER_FREE_MODEL_ORDER`, `OPENROUTER_PAID_FALLBACK_MODEL`, `OPENROUTER_SITE_URL`, and `OPENROUTER_APP_TITLE` through environment variables.
- Configure OpenRouter platform/API-key spend and rate limits outside the repo before enabling paid fallback.
- Cache only validated outputs.
- Never store or show raw model reasoning, hidden prompts, unrestricted source text, failed raw responses, or provider secrets.

## Provider API Keys

All provider keys are server-side only. They must never be added to Vercel frontend variables, `NEXT_PUBLIC_*`, docs with real values, logs, `/health`, exports, or browser responses.

Local live-provider runs may inherit these variables from the developer's WSL Bash environment:

- `OPENROUTER_API_KEY`
- `FMP_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `FINNHUB_API_KEY`
- `TIINGO_API_KEY`
- `EODHD_API_KEY`

Do not run commands that print key values. If a local live run needs a key, verify presence without echoing the value, then start the API or worker from the same WSL shell. The committed env examples keep these values blank.

## Monitoring

Use Cloud Logging and Error Reporting first.

- Log request IDs, route names, provider mode, job IDs, citation-validation failures, safety redirects, source retrieval failures, and OpenRouter usage/cost metadata when available.
- Do not log raw chat transcripts in product analytics.
- Do not log full source text, raw provider payloads, raw failed model responses, raw model reasoning, hidden prompts, or secret values.
- Add Sentry Developer plan later only if frontend or backend errors become hard to debug from Google Cloud logs.

## Required Environment References

Use the current committed examples as the source of truth for placeholder names:

- `.env.example`
- `apps/web/.env.example`
- `docker-compose.yml`

Never commit filled production env files. If future deployment-specific examples are added under `deploy/env/`, they must contain placeholders only and must stay aligned with the actual backend settings and frontend config.

## Smoke Checks

Local deterministic checks:

```bash
python3 -m pytest tests/unit/test_repo_contract.py -q
npm test
docker compose config
bash scripts/run_quality_gate.sh
```

Production smoke after web and API are deployed:

```bash
curl -fsS https://<cloud-run-api-url>/health
curl -fsS "https://<cloud-run-api-url>/api/search?q=VOO"
curl -fsS https://<cloud-run-api-url>/api/assets/VOO
curl -fsS https://<cloud-run-api-url>/api/assets/VOO/overview
curl -fsS https://<your-vercel-production-domain>/
```

Then verify in a browser:

- home page single-asset search remains the primary action;
- `VOO`, `QQQ`, and `AAPL` pages render;
- comparison remains a separate connected workflow;
- citations, freshness, source drawer, export links, glossary, and chat helper still point through the configured backend API/proxy path;
- Deep Dive does not duplicate dashboard table/chart content;
- no live provider or LLM call happens unless explicitly enabled.
