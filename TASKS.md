# Actionable delivery tasks

Recover [STATUS](STATUS.md) and [PLAN](PLAN.md) before choosing work. TODO means not acceptance-complete, even if a draft exists. IN_PROGRESS is active work; BLOCKED requires an exact dependency/input/failure and next action in STATUS; DONE requires the listed acceptance evidence. A completed slice never completes its whole milestone automatically.

Prioritize table order among unblocked tasks. Group names and actual commands are defined in [EVALS](EVALS.md). M1–M11 rows preserve the approved scope; deferred D21/platform work is tracked in [the audit](docs/project-audit.md), outside Windows completion.

| Task | Milestone | State | Dependencies | Action | Acceptance/checks |
| --- | --- | --- | --- | --- | --- |
| M0-T01 | M0 | DONE | — | Audit/migrate canonical documents and P/D traceability; update all entry points and archive notices | F documentation checks; audit every requirement/default |
| M0-T02 | M0 | DONE | M0-T01 | Add shared checks, correctness lint, read-only contract checks and prerequisite/failure tests | F, Q; tests/unit/test_verification.py |
| M0-T03 | M0 | DONE | M0-T02 | Create tracked delivery skill, portable wrappers and deterministic/manual database CI | Skill validation; actual wrapper pass/failure; workflow inspection |
| M0-T04 | M0 | DONE | M0-T03 | Review whole diff, record dated foundation evidence and commit checkpoint | Q; staged diff and no secret/unrelated files |
| M1-T01 | M1 | DONE | M0 | Separate installed/authenticated/qualified capabilities; preserve exact versions; block unsupported execution before inference | R provider capability/auth/version negative tests; Q, C |
| M1-T02 | M1 | DONE | M1-T01 | Qualify Codex configuration/tool isolation against the installed official protocol; prohibit inherited hooks/MCP/execution | Synthetic adversarial config/events; installed no-inference handshake; R, Q; live sandbox enforcement remains M1-T05 |
| M1-T03 | M1 | DONE | M1-T02 | Expose supported models and implement bounded, correlated interactive approvals without broad frontend privileges | Both M1-T03a and M1-T03b; API/UI auth, expiry/denial/cancel/foreign request tests; C, B, Q; positive grants remain forbidden under DEC-012 |
| M1-T03a | M1 | DONE | M1-T02 | Normalize bounded model catalogs, save explicit selection and reject silent model/provider fallback | Catalog/auth/malformed/pagination/selection tests; C, D, B, Q |
| M1-T03b | M1 | DONE | M1-T03a | Implement ephemeral correlated approval requests and UI within the app-owned tool policy; current prohibited grants remain unavailable | Timeout/denial/cancel/foreign/replay/forbidden scope tests; C, B, Q; live qualification remains M1-T05 |
| M1-T04 | M1 | DONE | M1-T02 | Complete owned process-tree interruption/cancellation and session/reconnect without replay | Crash/disconnect/cancel/consent-revocation scenarios; R, D, Q; actual Windows owned-descendant checks; packaged-host acceptance remains M9/M11 |
| M1-T05 | M1 | BLOCKED | M1-T03, M1-T04; dedicated ChatGPT sign-in | Harness/preflight implemented; sign-in blocker reconfirmed on delivery resume; complete actual subscription accounting, sandbox, source capture and provider-failure qualification before pinning live capabilities | Q passed again on 2026-10-04; L still blocked before generation; [resume evidence](docs/verification/2026-10-04-delivery-resume.md); exact version/model/date and sanitized live result remain required |
| M2-T01 | M2 | TODO | M1 | Create independent identity resolution and source/rights registration with exact cache scope | Ambiguity, wrong asset, unknown/rejected rights and cache/freshness tests; R, C, Q |
| M2-T02 | M2 | TODO | M2-T01 | Implement official/free structured financial adapters and normalized period/unit/history/restatement/conflict admission | Recorded/synthetic malformed, rate-limit, unit, corporate-action and conflict scenarios; explicit permitted retrieval check; Q |
| M2-T03 | M2 | TODO | M2-T02 | Refactor cache-first orchestration into bounded structured retrieval then agent gap research with no unverified numeric input | Two retrieval/one inference, partial failures, cancellation, refresh and persistent publication; D, R, Q |
| M3-T01 | M3 | TODO | M2 | Add URL/PDF/CSV/XLSX parsers, native file selection and untrusted import admission | Limits, redirects/private addresses, prompt injection, malformed files, rights; R, B, Q |
| M3-T02 | M3 | TODO | M3-T01 | Extend portable archives for retained permitted attachments before enabling durable import storage | Checksums/references/limits and real restore with attachments; D, Q |
| M4-T01 | M4 | TODO | M2 | Wire retained financial sections/charts/returns to admitted normalized evidence | Aligned values, absent inputs, price versus total returns; R, Q |
| M4-T02 | M4 | TODO | M4-T01 | Implement progressive admitted sections, source-review queue and interrupted stream recovery | Invalid candidates never flash as facts; source dates/rights/citations; C, D, B, Q |
| M4-T03 | M4 | TODO | M4-T02 | Add repeatable browser interaction coverage and finish responsive/keyboard section parity | Normal/640-pixel views, missing/stale/partial states and exact-version source navigation; B, Q |
| M5-T01 | M5 | TODO | M4 | Complete visible scope/provider/model transitions and immutable chat/report refresh behavior | Scope while busy, provider switching, saved-versus-current versions; D, B, Q |
| M5-T02 | M5 | TODO | M5-T01 | Qualify bilingual beginner/intermediate term/conversation output and permitted exports | Numbers/units/citations, unsourced generic labels, hover read-only, no note contamination; R, L, Q |
| M6-T01 | M6 | TODO | M4 | Migrate comparison alignment/gap behavior and persist immutable comparison results | Mixed types/incompatible metrics, citations, restore; C, D, Q |
| M6-T02 | M6 | TODO | M6-T01 | Connect comparison UI and enforce cached-only offline behavior | No online requests/new calculation offline; no winner/advice; B, R, Q |
| M7-T01 | M7 | TODO | M2, M4 | Migrate date-verified weekly selection and separately labeled Earlier context | Eastern DST/range boundaries, duplicates, rights, sparse/two-item thresholds; R, Q |
| M7-T02 | M7 | TODO | M7-T01 | Deliver independent historical reports, immutable saves and cited exports | No recent-news minimum, version preservation, permitted content; D, B, Q |
| M8-T01 | M8 | TODO | M1, M5 | Implement and qualify Gemini subscription onboarding, models, isolation and shared protocol/evidence behavior | R, B, L Gemini; Q; no enablement from version detection alone |
| M8-T02 | M8 | TODO | M8-T01 | Implement and qualify Claude subscription onboarding, models, isolation and shared protocol/evidence behavior | R, B, L Claude; Q; unsupported auth never falls back to API billing |
| M9-T01 | M9 | TODO | M3, M5, M6, M7 | Implement protected cache eviction/deletion/retention and large-library archive/scale behavior | Saved evidence protected; 1,000-asset measured baseline; actual large/attachment restore; D, Q |
| M9-T02 | M9 | TODO | M9-T01 | Compile native shell and complete private database/owned-process failure matrix | Ports/locks/crash recovery/tray/Quit/parent loss; R, D, N, Q |
| M10-T01 | M10 | TODO | M9 | Implement compatible app/schema upgrade staging and verified separate-cluster restore before activation | Interrupted migrations, unknown schemas, preserved newer research; D, N, Q |
| M10-T02 | M10 | TODO | M10-T01 | Implement signed artifact update modes, coordinated rollback and opt-in start-at-login | Interrupted artifact activation/rollback, setting enforcement, no loss; R, N, Q |
| M11-T01 | M11 | TODO | M1–M10 | Assemble reviewed runtime resources, licenses/notices, signatures and Windows installer/prerequisites | N, W; no core developer-tool requirement |
| M11-T02 | M11 | TODO | M11-T01 | Run clean-machine full product/provider/update/restore matrix and fresh SPEC compliance review | Full gate and Q/C/R/D/B/N/L/W; every P requirement evidenced |
