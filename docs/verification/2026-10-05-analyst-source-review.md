# Analyst source review and proposed scope — 2026-10-05

M4-T01g8 remains unqualified. The production analyst panel is unavailable-only, and the existing source rules cover SEC/OpenFIGI plus separately scoped Yahoo prices/returns/valuations. None registers analyst estimates. This review completes read-only preparation for a concrete source decision; it does not activate a dataset or widen a rule.

## Existing-account routes

The previous credential check established account presence and reviewed stored plan labels without exposing them. It did not establish analyst endpoint entitlement. No real account credential or authenticated data endpoint was accessed during this review.

| Candidate | Current official evidence | Consequence for this application |
| --- | --- | --- |
| EODHD | [Pricing](https://eodhd.com/pricing) places fundamental coverage in distinct plans; [fundamental API overview](https://eodhd.com/lp/fundamental-data-api) describes restricted free access. [Terms](https://eodhd.com/financial-apis/terms-conditions) permit private storage/analysis but restrict retransmission/access by others. | Earlier free-account history acceptance does not establish estimates entitlement or chosen-cloud-provider permission. Do not activate a paid plan or probe around a denial. |
| Finnhub | [Terms](https://finnhub.io/terms-of-service) require written approval to share data/derived results with third parties and require deletion when data subscriptions end. | Permanent cited snapshots and cloud learning are not qualified by possession of a personal key. |
| FMP | [Terms](https://site.financialmodelingprep.com/terms-of-service), sections 2.2–2.2.2, restrict copying, downloading, third-party tools and multi-user display without applicable approval. | No new permission for storage/cloud/shared application use was established. |
| Alpha Vantage | [Documentation](https://www.alphavantage.co/documentation/) describes `EARNINGS_ESTIMATES` and points to its official AI/MCP integration; [terms](https://www.alphavantage.co/terms_of_service/) grant conditional personal noncommercial access/use. | A useful candidate, but exact account coverage and permanent retained/backup/cloud operations remain unqualified. The documented API example puts authentication in query parameters; no compliant alternative transport has been verified under AGENTS' credential-in-URL prohibition. The public `demo` request returned only an information response asking for a real key; it supplied no estimate data or entitlement evidence. |

These are scoped engineering findings, not a claim that every personal use is prohibited or that a paid plan is necessary. No provider contact, signup, upgrade, cookie import, quota workaround or credential change occurred. The public demo response contained no financial values and was not saved as evidence.

## Reviewable private Yahoo proposal

The installed pinned yfinance analysis module and its official [earnings estimate](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.get_earnings_estimate.html) and [revenue estimate](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.get_revenue_estimate.html) references expose period-specific consensus estimates, bounds and analyst counts. Its code retrieves the separate `earningsTrend` module. That is outside the existing history/timeseries transport allowlist. A current attempt to retrieve [Yahoo's terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) again returned HTTP 999; no restriction was bypassed and no new permission finding is claimed.

Proposed extension of the existing developer/private project policy:

- Add only consensus EPS and revenue estimates for independently resolved stock listings. Preserve the provider's original period/end date, currency/unit, exact average/low/high values, analyst counts when supplied, retrieval timestamp and original citation/hash. Missing original publication/as-of dates remain unknown; retrieval time does not become analyst publication time.
- Display them as external opinions separate from realized financial results and app calculations. No buy/sell/hold ratings, price targets, allocation or trading behavior. Do not infer missing estimates from prices or generated text.
- Permit local saved snapshots, same-user backup/restore and the existing selected-provider learning context under cloud consent and source review. Keep shareable exports/public dataset distribution excluded. Public-release permission remains a separate gate.
- Reuse the existing pinned anonymous worker and owned lifecycle. Add a narrow bounded request policy for the required module only, with sticky denial/redirect/quota failure; no broad Yahoo URL permission or paid fallback. Validate raw JSON before admitting typed opinions; do not reuse dataframe-rounded values.
- Require deterministic mapping/date/unit/opinion/export/context checks, actual restore, normal/640-pixel browser parity, packaged-worker checks and bounded live retrieval before any delivered-integration claim.

No new dependency, paid service or destructive SQL migration is proposed. Approval would establish a project-policy scope choice, not third-party legal permission. An alternative is a documented existing-account grant covering the exact operations above, with verified endpoint coverage and safe credential transport.

## Blocked action

Activating analyst retrieval/storage/cloud use under a newly expanded source policy is pending an established decision or owner approval. [AGENTS](../../AGENTS.md) requires approval for scope/security changes; DEC-035 requires operation-specific review and the existing Yahoo exceptions concern historical numerics. Implementation preparation can continue, but a source rule must not silently inherit the history exception. M4 and dependent milestone acceptance remain open; no sequencing exception is inferred.

Documentation-checkpoint F passed (Ruff/ESLint, contracts/types, links/whitespace and TypeScript). This review changes no production code and supplies no analyst integration/live acceptance. The preceding independent saved-question checkpoint is committed at `702961b` with its separate Q/D/B/L evidence. TASKS/STATUS retain g8 as blocked pending the source decision; required implementation and qualification checks have not been waived.
