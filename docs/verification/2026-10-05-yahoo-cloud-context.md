# Shared numerical cloud context — 2026-10-05

Owner-directed M4-T01g4 implements DEC-046. The owner explicitly requested that yfinance use the same data path as other providers for personal noncommercial learning. No further policy approval was needed. This supersedes earlier cloud exclusions, not their original verification records. Shareable exports and public-release source permission remain separate.

## Behavior and integrity

Validated Yahoo daily bars, corporate actions, retained returns and provider valuation observations now enter the common factual-context builder used by research and term learning. The original dates, units, adjustment bases, methods, missing states and source IDs remain attached. Existing cloud consent, provider/model selection and runtime/tool boundaries apply; there is no extra Yahoo cloud toggle or paid fallback. Disabling new Yahoo retrieval preserves cached numerical learning; disabling cloud research prevents new cloud explanations.

Fresh numerical sources are application-owned through research admission, so a model cannot replace their URL or verification metadata. Generated wording is saved only as an unverified interpretation. Historical contexts use version-specific citation aliases and application-owned `context_references`; publication and archive validation resolve those against the original immutable library records. Later rounds can follow these references within the existing history/version/character bounds, including when the originating turn has left the transcript window. They never reuse explanation prose as facts or relabel historical retrieval as current verification. Missing, tampered, wrong-asset or future references fail validation. Source review is checked before inference and again before publication.

Term explanations can copy numbers from their cited numerical observations. Unsupported values and borrowing a number from a different source are rejected. Decimal comparison does not round at the ambient 28-digit precision; ISO date separators are distinct from negative signs. The numerical check is conservative token validation, not a proof of semantic entailment; explanations remain visibly unverified and cannot feed charts or calculations.

Dashboard numerical panels now allow automatic term selection. Notes, untyped Yahoo prose and raw source metadata retain their guards. Generated explanations and original-version notes expose citation links. Shareable exports still omit Yahoo data and dependent/unattributed interpretations, including reference-only answers. Same-user backups retain originals and interpretations and reset cloud/retrieval consent after restore. No dependency, SQL revision or archive-format change; older application rollback remains unqualified.

## Verification

- Q passed: **1,680 Python / 72 frontend tests**, Ruff/ESLint, generated schema/types, Markdown links, whitespace, static evaluations, TypeScript and production build. Deterministic cases exercise all three provider selections through the common path without contacting any live provider; this does not qualify Gemini/Claude runtimes.
- D passed: actual isolated PostgreSQL lifecycle, atomic rollback, full archive restore and restart. The expanded archive contains 16 evidence versions, including original numerical data and a later interpretation referencing it. Original values/dates/references and export filtering survive restart.
- B passed the integrated workflow in **23.1 seconds** (test body **14.1 seconds**): unchecked review, numerical selection, generated cited daily-close explanation, original source navigation, exact values and missing states, reload/offline behavior, consent/opt-out and normal/640-pixel layouts. Images were inspected for readable text, citation navigation and overflow; a stale local-only review label and opaque term citation label were corrected before the final run.
- Packaged checks passed after rebuilding the final source: authenticated frozen service startup/shutdown, four import formats, actual market dependency loading and owned cancellation, and frozen API restore/restart into real PostgreSQL. The archive preserves numerical term explanations and original-version research references; filtered exports and reset network consent pass.
- N passed the locked Tauri release build and NSIS assembly. This is a rebuilt developer artifact, not clean-machine installer/update/rollback or public-release acceptance. No installer was installed or published.
- One live Codex term-learning turn passed after Q using synthetic typed numerical evidence, the existing dedicated subscription and normal production `TermService`/`CodexRuntime` path. Preflight at **2026-10-05T08:36:15.156436+00:00** verified Codex **0.158.0-alpha.2.1**, **gpt-6-astra**, included usage and sandbox enforcement. The admitted response used snapshot basis, copied the retained P/E value, cited the original valuation source, remained interpretation-only, preserved original evidence, emitted no raw deltas and was reused with cloud off. The temporary database/profile workspace was cleaned up; the user library was untouched. No Yahoo retrieval, paid fallback or Gemini/Claude qualification was claimed by this check. The ignored `.local/cloud-live-check.py` invoked the existing preflight/enforcement helpers and production term service; `.local/cloud-live.json` retains sanitized booleans/scope only.

## Repairs and review

Initial targeted checks exposed old cloud-omission assertions and prompt-header coupling in the historical-reuse fixture. Kept the established header, replaced blanket exclusions with positive typed-context checks and retained the unverified-prose/export negative checks. The first full Q found another old issuer/market exclusion assertion. Subsequent gates identified an extra EOF blank line and two old UI-copy assertions; repaired each and ran the focused frontend suite before the passing Q. Initial B expected the superseded review wording; initial D expected 13 versions before the three new reference-scenario records. Updated their exact expectations without skipping any checks or increasing timeouts.

Final code review found long-decimal rounding and reference-only follow-up gaps; both received regression cases and repairs, followed by passing Q/D/B. Packaged output was rebuilt and all required affected checks passed after those final code changes. Review covers original source authority, model spoof rejection, cited numeric support, consent, review changes during generation, immutable references, actual restore, export boundaries and generated-contract drift. No credentials, real financial datasets or provider transcripts enter Git; ignored qualification outputs contain metadata only. Prior live Yahoo coverage remains in the [valuation evidence](2026-10-05-provider-valuations.md); no new coverage claim is made here.

Remaining public-release gates, M4 final parity review, later workflows and other subscription qualifications are unchanged. This private project-policy choice does not establish provider permission or public redistribution rights.

Final F passed after canonical documentation and evidence updates: lint, contract drift, local Markdown links, whitespace and TypeScript.

## Rebuilt developer artifacts

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| `dist/ltt-service.exe` | 56,772,804 | `8469c455a599920e0c7b2bab3a179e1db5b66c401bf7384d6a9c246c9e82df32` |
| `learn-the-ticker.exe` | 11,108,864 | `357d42a175659d45e91acb8aefb93ee0515b0ab2fc6105e76ef644dd18ebcd01` |
| `Learn the Ticker_0.2.0_x64-setup.exe` | 78,166,054 | `06c2216ed812414195415fca6b3e3d6a4ac5db5bc623f09f13b3a71c48f65453` |

Existing Starlette/httpx deprecation and optional PyInstaller hidden-import warnings remain; actual packaged checks passed. Ignored developer evidence is in `.local/cloud-{quality,database,browser,packaged,native}.log` and `output/playwright/automated/`. No production dependencies changed.
