# Cited evidence reuse and corrected browsing acceptance

Date: 2026-10-04. Scope: M2-T03b follow-up under user-approved DEC-028. This report does not replace or retrospectively pass the [earlier failed checks](2026-10-04-dated-research.md).

## Diagnosis and accepted change

The pinned Codex web tool emits `response.results` in completed events but sends `response.output` to the model through a separate output object. Event results are optional opaque JSON; they are not a contract for the page text the model saw. The previous gate searched arbitrary event strings for an exact quotation, which did not test the intended behavior reliably. The user approved separate browsing observation and independent fact admission, and requested source-preserving reuse of stored facts.

Primary implementation reviewed: [web tool](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/ext/web-search/src/tool.rs) and [model output](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/ext/web-search/src/output.rs). Completed navigation is observable; full content delivery/reading and every per-page error are not independently observable through that event projection. We do not claim otherwise.

The new helper correlates completed absolute-URL navigation with independently dated cited evidence and requires search and subsequent investigation. It separately checks admitted quotation support, typed financial observations, freshness disclosure and exclusion of model numeric fields. Bounded returned URL fingerprints and structured failure counts are diagnostic only; titles, bodies, raw errors, queries and contact details are not retained. Wrong URLs, explicit failed navigation, search snippets alone and unsupported facts fail their respective checks. This changes the flawed browsing check, not source rights, identity, literal factual admission or numeric validation.

## Durable citations

The database already stores immutable evidence versions containing claims and their source records. Follow-up prompts previously passed assistant bundle IDs without hydrating the answer's factual evidence. They now read up to five distinct versions from the latest twenty messages after the latest scope change, with full identity matching and a 400,000-character context budget. Claims travel with source URLs, original publication/as-of/retrieval dates, provenance and version IDs. Source aliases include the original version to prevent ID collisions. Notes and interpretations do not enter factual context. Removed rights, missing versions, changed scope and malformed references are excluded.

The application resolves a reused citation to its original stored URL even if the provider omits or replaces the source object. New factual publication still independently retrieves and validates support; historical proofs are not copied as current verification. Manual review, failed retrieval and the combined 100-source candidate limit remain enforced. Older answers remain accessible after refresh or source disappearance. Publication and restore share citation-reference validation; orphaned facts cannot be partially published.

No dependency, SQL/schema, archive-format, UI route, permission, credential-storage or provider-qualification change. Existing citations still open exact evidence versions. This is a bounded recent-context feature, not unlimited semantic recall of the whole library.

## Verification record

- Initial focused run: 65 passed/four failures. A too-narrow full-text filter excluded already-admitted summary-permitted legacy term snapshots. Repaired by preserving their existing factual-context behavior while applying current rights to new historical reuse. The affected focused suites then passed 75 tests.
- Intermediate Q: 1,078 Python/seven frontend tests passed. Review then added explicit rejection of interpretations misplaced in canonical claims; Q passed 1,079 Python/seven frontend tests.
- Initial D: private PostgreSQL startup/API/lifecycle and atomic rollback/commit/restart passed; restore extension failed because the smoke passed Pydantic messages to a function whose production input is stored JSON. Corrected the harness to use the persisted representation. No production library or provider was involved.
- Final Q: `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` passed **1,080 Python/seven frontend tests**, Ruff/ESLint, schema/TypeScript drift, docs/static checks and production build. The existing Starlette/httpx deprecation remains a warning.
- Final D: `.venv/Scripts/python.exe -m scripts.verify database` passed private PostgreSQL startup/API, lifecycle, atomic rollback/commit and actual full-library restore/restart. Original follow-up factual context, version-specific citation IDs, URLs and source dates compared equal before backup, after restore and after restart; failure rollback and non-empty-target refusal passed.
- New live check: passed after Q/D; details below. No provider capability registry was changed.

## M2 acceptance review

| Requirement | Evidence and remaining condition |
| --- | --- |
| P-010 independent identity/disambiguation | Existing SEC/FIGI registry qualification and wrong-asset/unknown-type tests remain applicable; no fixed universe or model identity promotion |
| P-011 structured retrieval, browsing, follow-up and freshness | Current production orchestration and latest/stale-cache cases; corrected navigation observer passed the new production-path live check below |
| P-012 rights and independent support | Candidate flags/proofs remain cleared; automatic/manual/failure paths unchanged; historical sources revalidated under current rules |
| P-013 numbers, units, revisions and conflicts | Typed observations remain adapter-owned; prose and notes cannot become chart inputs; original missing-price/history limitations remain explicit |
| P-014 durable source attribution | Version/URL/date/claim links, collision isolation, model-source substitution and orphaned-publication tests; actual restore/restart extension passed |
| P-023/P-024 follow-up scope and saved versions | Same full identity, latest scope boundary, bounded historical context, note exclusion, immutable old answers and unchanged current page after narrow follow-up |
| Bounded work, consent and cancellation | Existing two-retrieval/one-inference, cancelled-I/O ownership and consent tests retained; reused plus new source candidates share a 100-source ceiling |

Other product workflows, Gemini/Claude, installer/update/rollback and public Windows acceptance remain M3-M11 work. This checkpoint cannot certify their completion.

## New live result and M2 conclusion

The explicit production-path run started at `2026-10-04T07:46:22.715018+00:00` with qualified native Windows Codex `0.158.0-alpha.2.1`, selected `gpt-6-astra`, real registered sources and a disposable library. All eight acceptance checks passed: search, page navigation, subsequent investigation, independent dated support, navigation of the cited source, structured observations, freshness/unavailability disclosure and exclusion of model numeric fields.

Observed actions: openPage/openPage/search/openPage/openPage. Four completed absolute-URL navigations and sixteen returned URL references were observed, with zero exposed structured failure indicators. This does not prove every page returned complete text or that no unexposed failure occurred. One dated fact and 291 structured observations were published. Ten claims were proposed, including three fact candidates; one cited verified page support and matched the independent excerpt. Four explanatory notes were retained. No model numeric fields or deferred weekly-report sections were supplied.

The cited [SEC filing](https://www.sec.gov/Archives/edgar/data/789019/000119312526380280/d291965d8k.htm) retained publication/report date `2026-09-02`, independently retrieved at `2026-10-04T07:46:38.946093+00:00`. Visible-text SHA-256: `cca0416570b96941984decadca1ab46c67db1fe3045136b72c19e5b12ac7ae38`; submissions-index SHA-256: `2484a2a3b5677d892a1b25af573ce4eda7b6f449f5eda41bac6b3f106dc3139c`. The nine concept fingerprints match the [financial adapter evidence](2026-10-04-sec-financial-observations.md). Eight concepts retain period `2026-06-30` and filing date `2026-07-29`; legacy Revenues remains `2010-12-31`/`2011-01-27`, explicitly historical. Their current retrieval does not certify current prices or news.

The authorized SEC contact was process-local and excluded from source control, reports, provider context and distributed configuration. No persistent user library, sign-in, permission grant, paid fallback or provider qualification was changed. The helper's `live_qualified:false` deliberately remains unchanged: passing this scoped research check does not promote runtime capabilities.

Separate acceptance review against PLAN M2 and the requirement table above found its scoped research-pipeline conditions satisfied by combined independent identity, financial/date, deterministic scheduling/admission, actual database and new live evidence. **M2-T03/M2-T03b and M2 are complete.** This conclusion does not qualify all source/asset combinations, unavailable prices/corporate actions/quarters, charts, imports, weekly reports, other providers or native release. Those retain their existing scope and explicit gaps. Next dependency-unblocked task: M3-T01.
