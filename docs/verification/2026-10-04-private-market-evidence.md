# Private market evidence — 2026-10-04

Scope: M4-T01f2 implements the accepted DEC-039 exception using DEC-040's typed storage and output boundaries. It does not activate production market scheduling, charts, calculations or a packaged feed.

## Behavior

Optional application-owned `market` evidence retains exact daily decimals, ordered action ratios/amounts, currency/timezone, adjustment bases, original Yahoo URL/hash/retrieval/as-of and the independent OpenFIGI listing checkpoint. Model output has no market field. A strict explicit personal-mode boolean is required for admission. Publication and archive validation reject wrong identity/source/rights/dates, malformed or reordered/duplicate values, open-day history, and changed record fingerprints. The fingerprint detects corruption; it is not an authenticity signature, permission grant or calendar-completeness certificate.

Cloud research, conversation reuse and term explanations use the filtered factual context. Direct and transitive private-source claim dependencies are excluded; permitted SEC observations keep their original dates/references. Shareable JSON/Markdown omits private history, private sources, dependent claims and unverified notes with uncertain derivation; a fixed notice identifies the omission. Local evidence versions remain unchanged. Legacy Yahoo Finance references cannot evade the restriction through source flags. Source URLs additionally reject `api_token`, `access_key` and `crumb` parameters.

Same-user private backups retain these records. Restore resets `experimental_yahoo_enabled`, cloud consent and start-at-login. SQL revision `0001` and archive formats remain unchanged; older binaries are not qualified rollback targets. No production dependency or native package changed.

## Deterministic and database verification

- 48 focused admission/operation cases passed; combined admission/retrieval run: **58 passed**.
- Q passed **1,509 Python tests / 38 frontend tests**, Ruff/ESLint, schema/type drift, documentation/whitespace, static evaluations and frontend build. Existing Starlette/httpx deprecation warning only.
- Actual `python -m scripts.verify database` passed owned service/private PostgreSQL lifecycle, migrations/authenticated API, atomic failure/commit/restart and two-cluster full-library restore. The archive includes ten evidence versions alongside retained documents, completed and pending jobs, SEC and legacy evidence. Exact market volume `9007199254740993`, distribution decimal `0.123456789012345678`, ratio `3/2`, source URL/hash/dates and private restrictions survived actual restore/restart. These are **synthetic fixtures**, not real financial values. Failed restore rolled back; non-empty destination was refused; network consent reset; owned processes stopped.
- Authenticated endpoint tests verify local bundle retention versus both filtered export formats; research/term/conversation tests cover multi-hop derivatives and private-only context gaps. No deterministic test invokes providers.

## Live admission

After Q, `.venv/Scripts/python.exe -m scripts.qualify_market_history --live --symbol NVDA --check-admission` passed. It made one EODHD request, four bounded anonymous Yahoo requests and one OpenFIGI lookup. No retry, model call, library write, paid setting change or raw body/price logging.

Requested 2021-10-04 through 2026-10-03. Primary EODHD: 250 rows, 2025-10-06 through 2026-10-02; original SHA-256 `4ec031bcdb5d42e04dca5c45b4c2df8f9a0550582e29d79f6435b071e857b39b`; retrieved `2026-10-04T15:23:37.157267+00:00`. It remains an unmapped candidate; Yahoo proof is not transferred to it.

Selected Yahoo: 1,255 rows / 21 actions, 2021-10-04 through 2026-10-02, USD, NMS/NasdaqGS, EQUITY, America/New_York, split-adjusted close. Original JSON SHA-256 `9cf3cb29bffe5084f518b440d178e78335d6e0cc2079a6d478ac252d8ddceb89`; retrieved `2026-10-04T15:23:41.073334+00:00`. A changed raw hash alone is not a restatement finding.

Independent listing: `FIGI:BBG000BBK0R0` / UW; identity hash `a46db7411e9eb722dfa57fb3fc2985dda13d792605a2436f207e96e6f27282b3`; identity-source hash `0b95cf5af7bfe17289bf506580351713ef8eaf17687a88354292781934ba81cc`; lookup checkpoint `2026-10-04T15:23:41.074332+00:00`.

Typed numerical admission and JSON round-trip passed with source ID `yahoo:b35e2b54ea8cd9cf488b411453e8b98a8524e94c0e2744a8c1e3b539824dbc7a`, normalized-record fingerprint `3970d262b6eca1d5a457931f028bd8d03d32657e0c9d6ac656e8781ad111852c`, `private_yahoo_v1` scope, empty numerical/source cloud context and empty private shareable view. `calendar_completeness_unverified` remains explicit. This in-memory live check plus separate real synthetic database restore qualifies this storage boundary, not native distribution or full M4 acceptance.

Next: adjustment-aware returns, production adapter scheduling/cancellation/review, opt-in UI, populated charts/source restrictions, applicable financial gaps and D/B/native integration. Public Windows v1 remains incomplete.
