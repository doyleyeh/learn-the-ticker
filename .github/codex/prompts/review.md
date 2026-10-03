Use this checklist for an explicitly requested review of Learn the Ticker, a citation-first local desktop research and learning application for beginner and intermediate users. It is a manual review prompt; no automatic provider call, PR comment, approval or merge is authorized by this file.

Authority order:

1. Safety and advice-boundary rules
2. [PRD.md](../../../PRD.md): required product behavior
3. [TECHNICAL_DESIGN_SPEC.md](../../../TECHNICAL_DESIGN_SPEC.md): mechanisms and limitations
4. [NEW_STRUCTURE.md](../../../NEW_STRUCTURE.md): approved architecture and defaults
5. [PROPOSAL.md](../../../PROPOSAL.md): product purpose and priorities

Follow [AGENTS.md](../../../AGENTS.md) and [CONTRIBUTING.md](../../../CONTRIBUTING.md). Check [implementation status](../../../docs/IMPLEMENTATION.md), [testing](../../../docs/TESTING.md) and [migration](../../../docs/MIGRATION.md) to distinguish required behavior from implemented preview capabilities. The approved reboot supersedes the former hosted application and fixed-coverage requirements.

Focus on P0/P1 issues only:

- Missing evidence for completion claims, failed checks, or fixtures represented as live provider/installer qualification.
- Buy/sell/hold, allocation/position sizing, tax advice, unsupported targets or trading behavior.
- Wrong-asset or unsupported citations; fabricated dates, values or history; unit/period mismatches; stale or missing evidence presented as current fact.
- Unverified notes or generated term interpretations becoming factual context, chart inputs or calculations. Generic term definitions without a citation must disclose that limitation.
- Source credibility confused with usage rights; storing or exporting restricted text; source/import instructions changing tool permissions.
- A new fixed ticker universe or pre-ingestion eligibility gate. Uncached assets must be researchable, with identity disambiguation and partial/not-applicable sections where needed.
- Weekly material mixed into stable facts, duplicates or disallowed items counted as signals, or Earlier context counted as weekly evidence. Weekly analysis needs two weekly items; broader historical research has no recent-news minimum.
- Frontend dependence on vendor events, arbitrary native process access, leaked credentials or hidden reasoning, missing local API/WS authentication, non-loopback services, or provider permissions enforced only by prompts.
- Silent API billing, paid overages or provider fallback; unsupported runtime versions continuing with weaker restrictions. Public v1 requires Codex, Gemini and Claude subscription qualification.
- Lost conversation scope/history, overwritten saved evidence/term versions, automatic inference on hover, or new research/comparisons generated offline.
- Non-atomic publication/restore, credentials in backups, subscription calls replayed after a crash, or upgrades discarding newer research. A readable backup archive alone is not a restore test.
- Native supervision affecting unrelated PostgreSQL/processes, missing bounded startup/shutdown, unverified provider prerequisites or installer claims.
- Production mounting the fixture API or a hosted Next.js path; root npm scripts no longer delegating to `apps/desktop`.
- Live research/provider calls or Docker required by normal CI. Manual provider checks and native release checks remain separate.
- Destructive Git behavior, unauthorized external review posting, PR creation or merging.

Do not nitpick style unless it affects correctness, trust, safety, source rights, packaging or maintainability. Review the submitted change; identify existing gaps as context rather than attributing them to an unrelated diff.

Return:

- summary
- high-risk findings
- suggested fixes
- merge recommendation and unresolved verification limits; do not perform the merge
