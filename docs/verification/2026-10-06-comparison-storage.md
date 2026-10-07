# Comparison storage and alignment

Date: 2026-10-06 (Asia/Taipei). Scope: M6-T01, source-level deterministic desktop comparison backend. M6-T02 browser workflow and public Windows release acceptance remain separate.

DEC-053 replaces fixture-only comparison eligibility with two explicit independently identified saved pages. The production service retains exact decimal strings, period/unit/method distinctions and original per-side citation/input references. Fund descriptions and missing dimensions remain visible without promoting notes or inferring numerical fields. Mixed asset types are accepted with applicability gaps, not a fixed ticker eligibility list. Stored return measures are copied, never recalculated; supplied valuation sampling remains distinct. No LLM call, retrieval, investment ranking or shareable private-data export is introduced.

Publication is transactional and immutable. Full-library archives validate both page fingerprints and reproduce the registered alignment to reject changed values, sources, scope or alignment even with recomputed archive checksums. Ordinary list/detail reads do not invoke the builder, and offline creation fails before it. Refresh leaves the original references intact.

## Repairs and evidence

- Initial targeted run: 26 passed and seven failed. Six failures were a test calling the existing keyword-only archive mutator positionally; one expected the comparison identity message even though typed financial validation correctly rejected the missing proof earlier. Corrected the harness and retained rejection assertions; 48 then passed.
- Added private-market coverage found that different valuation sampling domains shared a date. The initial implementation withheld them as ambiguous; corrected selection to keep annual, quarterly and trailing rows separate. The newer missing quarterly P/E stays missing while the distinct trailing observation retains `29.5`. Final targeted comparison/retained regression/archive suite: **50 passed**.
- F passed (`.local/m6-comparison-fast.log`).
- D passed (`.local/m6-comparison-d.log`): real private PostgreSQL startup/locks/transactions plus two-cluster full-library restore and restart. Both aligned exact financial values and a mixed-type private-history comparison survive; injected restored-event failure leaves no comparison or partial library. Original evidence/citation versions persist and restored cloud/private retrieval consent is off.
- Initial Q reached **1,948 passed / one failed**: the explicit repository schema-model inventory omitted the new comparison contracts. Added those models while preserving full schema equality; focused inventory checks then passed four tests.
- Repaired Q passed (`.local/m6-comparison-q-repaired.log`): **1,949 Python / 87 frontend tests**, Ruff/ESLint, exact non-writing schema/types, documentation links, static evaluations, TypeScript and production Vite build. Complete diff and whitespace review passed. No required M6-T01 check remains failing; M6 remains incomplete pending T02.

No provider, finance API, account, user library or packaged binary was touched. Existing Starlette/httpx deprecation is non-failing. No dependency or SQL/archive-format revision was added; older binaries remain unqualified rollback targets for the new record kind.
