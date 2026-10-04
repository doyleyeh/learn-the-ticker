# Retained market return calculations — 2026-10-04

Scope: M4-T01f3 / DEC-041. Application-owned private history now retains distinct price-return and provider-adjusted total-return-estimate results. This does not enable live page scheduling, charts or historical valuation.

Both results use the same source/version and actual endpoints. Split-adjusted close supplies price return; distribution-adjusted close supplies the separately labelled estimate using Yahoo's adjustment method as a reinvestment proxy. No event is applied again, no cross-provider data is joined and no missing value is imputed. Exact rational arithmetic precedes six-decimal percentage rounding with ties to even. Fees, taxes, currency changes and annualization are excluded. The source/method references and limits are recorded in [DEC-041](../../DECISIONS.md#dec-041-retained-adjustment-aware-return-methods).

YTD uses the prior year-end boundary; one/three/five-year windows use anniversaries of the latest retained day. Preserve the closest prior observed start within seven days and both actual dates. Missing baseline, any declared missing rows, a single point or an observed gap over seven days produces no value and an explicit reason. This is a conservative availability check, not a complete exchange-calendar qualification. The exact retained interval is a separate result, never labelled five years if its required baseline is absent.

New evidence fingerprints include method/results. Original pre-calculation fingerprints remain readable with absent defaults, and old/offline reads generate no new results. Rechecking stored calculation consistency is validation only. The existing private cloud/export boundary removes these derived values along with their source history; same-user backups retain them.

## Verification

- **30 method cases**, **78 combined method/admission cases**, passed: positive/negative returns, values beyond binary-float integer precision, tiny decimals, half-even ties/negative zero, price versus adjusted return, no double-counted actions, YTD/anniversary/weekend/leap-day boundaries, single/missing/sparse histories, recomputed-checksum tampering and old fingerprint compatibility.
- Q passed **1,539 Python / 38 frontend tests**, Ruff/ESLint, contracts/types, docs/whitespace, static evaluations and frontend build. Existing Starlette/httpx warning only.
- Actual D passed the owned API/PostgreSQL lifecycle, atomic failure/commit/restart and separate-cluster archive restore/restart. Saved synthetic retained-interval results `27.272727%` price return and `40%` adjusted estimate, endpoint dates, source references and unavailable-window reasons survived byte-equivalent normalized record restoration alongside SEC, legacy and retained-import evidence. Original dates and network-consent reset remain correct.
- No new live provider call, optional dependency, frontend interaction or native artifact. Earlier live numerical-admission evidence remains in [the private-evidence checkpoint](2026-10-04-private-market-evidence.md) with its original scope/date/counts.

Remaining: production retrieval/review/cancellation integration, visible charts/method/source labels and browser/native acceptance; aligned share-based valuation inputs and other M4 sections. These checks do not close M4 or public Windows v1.
