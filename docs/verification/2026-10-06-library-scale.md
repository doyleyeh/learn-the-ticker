# Library scale and attachment restore baseline

Date: 2026-10-06 (Asia/Taipei). Scope: M9-T01a, part of P-043/P-044. M9-T01 and public Windows v1 remain incomplete.

## Change and observed acceptance

Added `scripts.smoke_library_scale` to D/full verification. It creates two new private PostgreSQL clusters under ignored `.local`; it accepts no existing library path. Synthetic input uses the production evidence publication transactions and owned document parsers. No provider, retrieval, user-library mutation, dependency, SQL schema, archive format or capacity change is involved.

The dataset contains 1,000 distinct synthetic assets, 2,000 cited versions, 2,000 completed jobs/events, 100 older saved pages, 100 bookmarked conversations selecting old evidence and 100 immutable historical reports. Four small PDF/CSV/XLSX/HTML imports plus twenty text-and-image PDFs supply 24 retained documents. Deterministic uncompressed image bytes prevent the test from reducing nominally large attachments to a tiny compressed archive. All attachments remain explicitly unverified.

Passed on Windows AMD64, Python 3.12.0, PostgreSQL 17.5:

- 3,325 records, 2,000 jobs and 2,000 events transferred.
- 62,941,113 attachment bytes; 63,603,644 archive bytes; 1,705,450 serialized asset-list bytes.
- Every record's kind, parent, timestamp and payload, plus every job and event, matched the source fingerprint after restore and actual PostgreSQL restart. The only expected payload changes were cloud/Yahoo/start-at-login consent reset.
- Every retained attachment retained its original byte count/hash, parser metadata, locators, permissions and unverified state. Older saved versions stayed distinct from the current asset.
- Injected an event-write failure after records/jobs were staged: all three target tables remained empty. Successful retry used the same archive, then nonempty-target restore was rejected without changes.
- The event sequence continued after restart. The source library was unchanged. Both owned clusters stopped; no `postmaster.pid` remained.

## Measured timings

Single run, warm developer machine; Q ran concurrently during part of setup. These observations are not performance thresholds or statistically stable percentiles.

| Operation | Seconds |
| --- | ---: |
| Initialize two private clusters | 17.6755 |
| Publish 2,000 cited versions and saved references | 13.7177 |
| Parse and retain 24 attachments | 34.3121 |
| List/serialize 1,000 cached assets | 0.0467 |
| Read 100 old saved pages and current-version pointers | 0.2965 |
| Build backup | 5.2419 |
| Validate preview | 2.0377 |
| Failed restore and rollback | 11.5703 |
| Successful restore | 12.4608 |
| Compare every restored payload and attachment | 3.2708 |
| Reject nonempty target and confirm preservation | 3.3058 |
| Restart and compare every payload/attachment | 4.3770 |

Ignored reproducible output: `.local/library-scale-7405c30dd6fa/baseline.json` and `.local/m9-scale-d.log`. The synthetic archive is in the same isolated run directory.

## Repair and verification

The first standalone attempt stopped before building the library because the synthetic assets lacked the identity proof required by historical-report selection. Added explicit synthetic proofs with matching full-identity hashes; did not weaken report validation. A small two-asset archive round trip and a real 3-MiB PDF parse then passed. The subsequent complete D lane passed, including existing service lifecycle, transactional publication and rich financial/comparison/report/import restore checks, followed by the new scale scenario.

F passed before the first actual run. Final code Q passed: **2,026 Python tests, 94 frontend tests**, lint, contracts, static evaluations, TypeScript/build. Existing Starlette/httpx deprecation warning remains. No UI or production behavior changed, so B/live/native repetition is not acceptance for this slice. Final documentation F is recorded in the commit checkpoint.

Fresh scope review: P-044's 1,000-asset measured storage baseline and this bounded P-043 attachment/large-library restore scenario pass. This is not a dense five-year financial-history benchmark, browser performance measurement, peak-memory study, 10-GB archive, streaming archive implementation or cache eviction/deletion acceptance. Existing 128-MiB compressed/256-MiB metadata/64-MiB attachment limits remain. Protected cache controls, saved deletion/retention integration and native lifecycle are still M9 work; all three live subscriptions and clean-machine release acceptance remain mandatory.
