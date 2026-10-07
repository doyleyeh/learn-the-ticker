# Typed numeric admission checkpoint — 2026-10-04

Follow-up to the [SEC adapter checkpoint](2026-10-04-sec-financial-observations.md), commit `d7f9679`. M2 research orchestration and public release remain incomplete. This component adds a typed numeric document, validation, exports and actual database/restore acceptance; it does not yet schedule structured retrieval from production research.

## Scope and review

`EvidenceBundle.financials` contains a separate issuer identity/proof and association checkpoint. Observations preserve exact decimal strings, original concept/units/dates, filing/accession, source IDs, superseded versions and unresolved conflicts. Source fingerprints and publication/as-of/retrieval dates remain linked. Neither the instrument identity nor model Claim.value supplies the issuer financial numbers.

The application validates scope, rights, source references, decimal/period/value fingerprints, disclosed history gaps and recomputed revision relationships before database publication and archive restoration. Mixed retrievals for one concept, duplicate observations, changed source dates, dangling references, wrong issuer and incompatible units fail closed. Current numeric context contains only unconflicted current observations; notes and provider-supplied values cannot enter. ResearchResult rejects the financial document. Financial cache reuse stays disabled until structured refresh is integrated.

Generated JSON Schema/TypeScript are updated. Legacy documents remain readable with null financials, without retroactive verification. SQL revision and archive format remain unchanged; older binaries are not qualified rollback targets. Checksums and internal consistency do not authenticate an externally rewritten archive. Saved snapshots remain immutable. Markdown/JSON exports retain exact values, periods, revisions, uncertainty and source references; source bodies remain excluded.

No new dependency, credential, provider inference, paid service or native permission. No component/layout changed; export endpoints were exercised through authenticated HTTP tests. Current UI does not yet present financial charts. The previously recorded live source parsing result remains a separate dated result.

## Verification

- Initial related parser/adapter/storage/backup suite: **77 passed**.
- New numeric admission suite: **37 passed**. Moving its fixtures into a shared deterministic helper initially exposed an invalid synthetic FIGI checksum; corrected the fixture generation without changing production validation, then all 37 passed. No unresolved repair cycle.
- Initial Q passed **998 Python/seven frontend tests**, Ruff/ESLint, non-writing schema/types, documentation/whitespace checks, static evals, TypeScript and Vite build. Existing Starlette/httpx deprecation remains.
- D passed actual private PostgreSQL startup/authentication, atomic transaction rollback/commit, lock/recovery, full-library restore failure rollback and restart. The archive held both legacy snapshots and new issuer observations. Exact values above JavaScript's safe-integer range, independent identity proofs, source dates and conflict/revision references matched after restore and restart; completed job results also matched. Non-empty restore was refused and no subscriptions were called.
- Added the explicit helper's numeric-contract round trip and fixed-error check. Parser/adapter/admission suite: **97 passed**. Final Q passed **999 Python/seven frontend tests**, contracts/lint/docs/static/TypeScript/build. D remained applicable because only the helper and its test changed after that passing restore.

## Explicit live numeric-contract check

After final Q, `python -m scripts.qualify_sec_financials --live --query FIGI:BBG000BPHFS9` passed with `numeric_contract_validated: true`. Nine SEC concepts (291 retained observations including revisions) passed adapter retrieval, typed admission and JSON round trip in memory. Source hashes, counts, units and underlying dates matched the preceding [live observation table](2026-10-04-sec-financial-observations.md#explicit-live-result). Instrument/issuer hashes likewise matched that table. Old revenue dates and incomplete quarterly history stayed explicit, as did unavailable prices/corporate actions. The authorized SEC contact remained process-local; no library writes, numeric-value logs or subscription inference occurred.

M2-T02a/b and M2-T02's applicable official-source admission checkpoint are complete within this scope. This does not certify every instrument/history source or finish M2; unavailable coverage is disclosed, and production research orchestration still requires its own acceptance.

## Remaining acceptance

Production structured-first orchestration, concurrency/cancellation, live gap search/page reading and source-appropriate refresh remain M2-T03. Prices, corporate actions and unavailable quarters remain explicit gaps; no other financial provider or instrument is silently substituted. Charts/alignment and public installer/provider acceptance remain their owning milestones.
