# Public identity registry verification — 2026-10-04

M2-T01 follow-up to [the original identity checkpoint](2026-10-04-research-identity.md). The user supplied and authorized a contact for the SEC developer check. It was passed only in that command's process environment; this record, Git and distribution artifacts omit the address. It was not inferred from the user's subscription. Public Windows v1 remains incomplete.

## Scope and implementation

The SEC adapter's first real request passed. OpenFIGI adds an independent public namespace for instrument metadata, with no login, API key or charge. General queries preserve separate SEC/FIGI matches; explicit IDs choose one registry. Name/ticker resemblance does not merge records or add a CIK. FIGI checksum, exact response/request association, duplicate rejection, bounded text/rows, class/composite identifiers, conservative type classification and complete identity fingerprints precede publication.

Incomplete pages or more than twenty exact matches cannot establish uniqueness. At most twenty verified choices are offered before inference. Missing metadata, transport errors and rate limits produce a fixed selection/unavailable state without automatic retry. A model-proposed instrument independently verified after an unresolved original request still requires user confirmation before facts can be fetched/stored. Existing scope/rights/numeric/date guards remain in place.

Only fixed mapping/search URLs accept JSON POST, limited to 4 KB. The existing 2 MB response bound, public-address pinning, hostname TLS, no redirects and closure remain. Anonymous request starts are spaced at least three seconds for mapping and fifteen seconds for search across resolver instances in one process. Cache contains at most 256 queries for one hour. Only identity metadata permissions are registered; no financial/raw-page rights follow from a FIGI.

Reviewed primary sources: [API schema and anonymous limits](https://www.openfigi.com/api/documentation), [reuse FAQ](https://www.openfigi.com/about/faq), [terms](https://www.openfigi.com/docs/terms-of-service), [check digit](https://www.openfigi.com/docs/figi-check-digit.pdf), [allocation rules](https://www.openfigi.com/docs/figi-allocation-rules.pdf), [SEC access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data). DEC-024 records the choice and licensing/packaging limits. No dependency, schema or archive-format change.

## Deterministic verification and repairs

- Focused identity/admission/cache run initially had 152 passes and four failures: old rights tests selected the first registry rule by position. They now select `sec-filings-v1` by ID with all assertions retained; the same run passed 156 tests.
- The first full gate reached runtime tests that lacked explicit synthetic identity prerequisites. Nine failures were reproduced in the focused application/approval/live-helper suite; a subsequent runtime-recovery wait could never reach its provider and the original gate was interrupted. No milestone pass was claimed. Synthetic resolvers now explicitly enable those tests to exercise their intended runtime paths. The wait is bounded. The runtime-only developer lifecycle helper has an explicitly empty asset resolver, preventing real registry traffic or identity publication during a synthetic lifecycle probe.
- Application/approval/live-helper/recovery/FIGI rerun: **116 passed**. Full Q then passed **901 Python/seven frontend tests**.
- Review added the unresolved-request scope-confirmation guard and regression. Focused identity/FIGI/application run: **109 passed**. Final `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1`: **902 Python/seven frontend tests**, Ruff/ESLint, non-writing JSON/TypeScript contract checks, documentation links, whitespace, static evals, TypeScript and Vite build passed.
- `python -m scripts.verify database`: actual isolated private PostgreSQL lifecycle, migration/authentication, atomic rollback/commit, recovery/restart and complete-library restore passed. Restore rejected a non-empty target and preserved saved versions/events through restart. No user database was modified.
- Existing Starlette/httpx deprecation warning remains. Normal tests clear SEC contact and replace FIGI retrieval; no live request or subscription inference belongs to Q. No UI component/native change was made; the prior dated B evidence remains separate. No unresolved failed repair cycle remains.

## Separate live checks

All commands were explicit, after deterministic Q for their implementation. No provider inference, account sign-in, API billing or library write occurred.

`python -m scripts.qualify_sec_identity --live --query MSFT` passed at `2026-10-04T04:28:37.828108+00:00` using the unchanged prior Q-verified adapter. Authority `sec-listings-v1`; source `https://www.sec.gov/files/company_tickers_exchange.json`; content SHA-256 `2df6dbed748a66dfbb6ed403e1e88b4d7b5590e61188ea74d5548d0f8aec09c1`; identity SHA-256 `33eed38bb9828b585d4306ac746e2e77758a1edd4d8fb0e298c92d2a955773d9`. Type stayed unknown, as intended.

OpenFIGI probes used `python -m scripts.qualify_figi_identity --live --query QUERY`. Each row below passed one exact instrument check. All retained currency as unknown. Authority `openfigi-v3`; source `https://api.openfigi.com/v3/mapping`.

| Query / resolved FIGI | Observed type | Retrieved UTC | Response SHA-256 | Identity SHA-256 |
| --- | --- | --- | --- | --- |
| FIGI:BBG000BLNNH6 | stock | 04:36:53.893833 | c5557d18c510d57d906050f7f09c2c2d274e8a15c2594d2f1abe59ce608d013d | b34620cb8288a2c667a93f73f67d356c3843d152b855d1f00391a515858fc0da |
| FIGI:BBG0002ZTPD8 | option | 04:37:10.311565 | 3aa6276987e796a6a8a52562976efc0c2dcf092c93184f1af5e232732c9b3172 | 17ce192b6f474410c67517bc052c8124d345433cc6e43b4ef453d554e9fda7ce |
| FIGI:BBG009R4CLR3 | bond | 04:37:28.719847 | e2b7a9466bd296806313d7df461649a3081bcca81dd4a59fbc8ca6d9d4856f27 | a9a79466a1c8efce26facbf87e0171188318a339c48e721df7e39cc48db0aefd |
| VFIAX → BBG000BSRLX3 | fund | 04:37:32.075357 | 1a8748cdd97fe361ee73057eb0369d4ddae9f42db3196617dfe558667ee41bf0 | ad8bef9d9ab661424187e1217b18897029c86ba94d82cca9c3fcfaba27cc0c0a |
| FIGI:KKG000000M81 | crypto | 04:38:11.575004 | 63306ea1d07afddf4f26e6f1ea9a157c33e861f9d9de1f01f449da4c17acb036 | 5126661c42e4ef4c5d81d4a97dc56ca7fdabe914464b813be3d38b99681d908f |
| FIGI:BBG012FFK314 | future | 04:39:31.892904 | 6e6396a091efee79dba2503461c583c17b54be59446bb069349423589bccd521 | f74567779fd1575111a33213c099e51dc20e12edcb50abaf169224713e3af4b7 |
| FIGI:BBG0015VYNT4 | unknown (ETP) | 04:39:50.097239 | 4d3ff85544b5b7b9323a1b9d1e66bb09ad66524e6294e84b8e0ee9654b8e5e4e | 12b0bdbbf563b99d9c63349ef05a85da89787c6083f958d517dcbed46101728e |
| FIGI:BBG000H4FSM0 | index | 04:41:58.682115 | 0284ed847890d39af3aa3f5a85ad3ab6021ab8084d910b59d71f7a65dc52392e | e2e7b4c2c13e396be6f691cbcda02354c88a87968d9fb34327d7660e7ff2edad |

Actual `VOO` mapping yielded more than twenty matches and returned `needs_identity`, offering twenty distinct venue/composite choices. Actual `S&P 500 INDEX` search returned a partial page with six exact-name choices; it did not select one automatically. Their subsequent explicit FIGI checks above passed. The ETP label deliberately did not become ETF classification. The historical option/bond examples do not establish current trading availability.

The first `ESZ6` developer inspection returned `needs_identity` with no choices. The fixed report did not retain a raw reason, so its cause is unconfirmed. Separate bounded inspection then observed one public metadata record and an exact-FIGI parse succeeded; the exact-FIGI helper passed as recorded above. No parser/check was weakened, automatic retry added or broad symbol reliability claimed.

## Acceptance and remaining work

M2-T01's independent identity/source registration boundary now has dynamic multi-category metadata, real permitted retrieval, deliberate disambiguation, all-category scope fingerprints, uncertain-type suppression and wrong-asset/rights/cache checks. This closes the task within the specification's explicit allowance for unknown type. It does not establish universal instrument coverage, current trading status, exact ETF subtype, economic contract attributes, issuer/instrument crosswalks, financial/news rights or financial values. Unknown/unavailable records stay explicit and cannot enable type-dependent facts.

M2 remains incomplete. M2-T02 must independently bind structured financial evidence to issuer/instrument scope and normalize dates, units, history, conflicts and restatements. M2-T03 still owns bounded structured-first live gap investigation, latest-information freshness and publication. All later product, three-provider and clean-machine installer/update/rollback requirements remain required. The public app's SEC contact design is still pending; a project-managed contact is a recommendation, not a decision to distribute the user's personal email.
