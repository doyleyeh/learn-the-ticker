# Market listing concordance — 2026-10-04

Scope: M4-T01f1, an independent part of M4-T01f. This extends [candidate retrieval](2026-10-04-market-history-retrieval.md) with current independent listing concordance. It does not grant source-use permission, persist prices or enable a production feed.

## Implemented boundary

Yahoo's code and full exchange label must agree with the exact OpenFIGI venue: NMS/NasdaqGS → UW, NGM/NasdaqGM → UQ, NCM/NasdaqCM → UR, NYQ/NYSE → UN. The [official OpenFIGI exchange vocabulary](https://www.openfigi.com/docs/OpenFIGI-exchange-codes.csv) was retrieved successfully to check these venue names. The US country composite and other Nasdaq tiers cannot stand in for the selected venue.

Require a current, fingerprint-bound OpenFIGI common-stock/Equity identity; exact symbol, reviewed venue and Yahoo EQUITY metadata; USD and the New York timezone; compatible explicit identity currency if known; matching company name; canonical history URL/hash and current retrieval time. Only terminal Corporation/Corp, Incorporated/Inc and Limited/Ltd variants normalize; class and contract wording is never removed. Independent identity fields, including unknown currency, remain unchanged. The mapper wraps a candidate with its independent proof; it does not remove the candidate's unverified-admission marker or certify every price.

The optional helper lookup makes one exact symbol/venue OpenFIGI request and requires one result. Ambiguous/wrong/expired/model-attested identities fail; transport diagnostics stay fixed. No ticker allowlist was added. This initial mapping scope excludes funds, preferred stock, derivatives, foreign venues and ambiguous names rather than guessing them.

## Verification

- **122 focused tests passed**, including 31 mapping cases and all prior history/transport/selection checks.
- Q passed **1,461 Python tests, 38 frontend tests**, lint, contracts/types, documentation/whitespace, static evaluations and frontend build. The existing Starlette/httpx warning remains.
- Helper default returned `not_run` with no vault/network access.
- After Q, `.venv/Scripts/python.exe -m scripts.qualify_market_history --live --symbol NVDA --check-mapping` passed. This made one additional EODHD request, four Yahoo requests and one OpenFIGI request; no retry, subscription inference, library write, account modification or other provider access.

Actual selected result: 1,255 daily rows, 21 actions, 2021-10-04 through 2026-10-02, USD, NMS/NasdaqGS, EQUITY, America/New_York, split-adjusted close. Original Yahoo JSON SHA-256: `d871bae0772eff04e50b150ac07bca99cf168d77d99862935ff8b5f341a675ac`; retrieval recorded at `2026-10-04T15:05:25.676331+00:00`. This is a new response fingerprint, not a claim that a changed hash proves a financial restatement.

Independent match: `FIGI:BBG000BBK0R0`, venue UW. Identity hash `a46db7411e9eb722dfa57fb3fc2985dda13d792605a2436f207e96e6f27282b3`; original OpenFIGI response hash `0b95cf5af7bfe17289bf506580351713ef8eaf17687a88354292781934ba81cc`; lookup checkpoint `2026-10-04T15:05:25.678330+00:00`.

Primary EODHD retained 250 daily rows, 2025-10-06 through 2026-10-02, unadjusted close, original hash `4ec031bcdb5d42e04dca5c45b4c2df8f9a0550582e29d79f6435b071e857b39b`, retrieval `2026-10-04T15:05:21.584812+00:00`. This price endpoint still supplies no independent listing/action metadata; the Yahoo proof is not transferred to it.

No DTO/SQL/archive/UI/native packaging changes occurred; D/B/native financial integration remains required after admission implementation. The actual source-mode Windows worker executed and closed its owned process/temp cache. No numeric values, raw bodies, credentials or anonymous session artifacts were saved to the repository.

## Accepted private-mode policy and next work

The user selected the library; that choice is implemented. The owner then explicitly accepted [the concrete private-mode proposal](2026-10-04-market-admission-proposal.md), now DEC-039: local experimental cache/display and private backups, excluding Yahoo content from cloud prompts/shareable exports and keeping public release gated. This resolves the project-policy decision; do not request it again or imply Yahoo granted a license. Independent mapping is verified; subsequent typed admission, operation guards, calculations, original-source persistence/reuse, UI and D/B/native checks still must be implemented and passed before closing M4.
