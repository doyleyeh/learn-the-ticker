# Bilingual learning and M5 acceptance review

Date: 2026-10-06 (Asia/Taipei). M5-T02a's deterministic changes are verified; M5-T02b and M5 acceptance are blocked by an installed-runtime account RPC failure. No public-release, Gemini/Claude or native-installer qualification is claimed.

## Changes and deterministic verification

The bounded qualification harness exercises English/Traditional Chinese and beginner/intermediate term explanations plus persistent conversation rounds, using a disposable synthetic library and the real selected Codex adapter only when explicitly invoked with `--live`. It preserves production model/tool/isolation/usage guards and stops on the first failure, without retries or fallback. Synthetic retrieval adapters supply identity and saved numerical context; no live financial source is part of this check. Reports contain aggregate checks only. Optional ignored language-review output contains admitted synthetic interpretations, never raw provider events, source payloads or account diagnostics.

The export review found that Markdown omitted source-reference IDs on unverified notes. The repair retains those IDs beside the notes, preserves their unverified label, and marks notes without references. Shareable exports still omit private Yahoo observations and dependent notes. Both languages and reader levels have authenticated JSON/Markdown regression cases for exact text/units, reference IDs, original source URLs/dates, excerpt omission and unchanged local versions.

- Targeted term/export/market-context/financial suites: **101 passed**, including 10 harness scenarios, in `.local/m5-learning-targeted-final.log`. Earlier 100-case and nine-case harness logs retain their original scope.
- Final checkpoint Q: **1,878 Python / 87 frontend tests**, lint, schema/types, local links, static evaluations, TypeScript and build passed in `.local/m5-learning-q-checkpoint.log`, including all 11 diagnostic-harness scenarios. The earlier `.local/m5-learning-q-final.log` retains its 1,877-test result before RPC classification was added.
- Default qualification invocation returned `not_requested`, `generation_requested=false`; no profile/account access.
- Current M5 D/B evidence is unchanged from [context acceptance](2026-10-06-conversation-context.md): actual PostgreSQL restore/restart and three browser workflows with normal/640-pixel inspection. T02 changes export rendering and qualification coverage, not the database contract or UI.
- Existing Starlette/httpx and test-runner color warnings remain non-failing. No failed gate or weakened assertion is hidden.
- Full change review covered the export renderer, qualification-only synthetic adapters, bounded calls, account/tool guards, stream cleanup, diagnostic allowlists, generated-text isolation and all owning documentation. Final documentation/whitespace checks passed; no source-policy, dependency or native package changed. The T02a commit is a verified partial checkpoint, not M5 completion.

## Live check and language review

The first command, `python -m scripts.qualify_conversation_learning --live --review-output .local/m5-learning-review.json`, stopped after one adapter call at `term_not_admitted`, with no completed cases. Its preflight timestamp was 2026-10-05T23:00:59.428036+00:00 (2026-10-06 local); version 0.158.0-alpha.2.1 and model gpt-6-astra passed preflight/enforcement. Aggregate output is `.local/m5-learning-live.log`. The initial helper omitted the rejection category, so this observation does not establish whether inference completed or identify its cause. The disposable database and raw output were not retained; no user library changed.

The first diagnostic repair reuses the saved-question helper's allowlisted candidate categories and the existing runtime failure classifier, without printing exception strings or candidate text. Tests verify quota classification, citation rejection, early stop and stream cleanup. Its invocation at 2026-10-05T23:04:57.448582+00:00 admitted five cases, then stopped on the sixth adapter call (English intermediate conversation) with `rpc_rejected`. Log: `.local/m5-learning-live-diagnostic.log`. Read-only `python -m scripts.qualify_codex` at 2026-10-05T23:08:40.475201+00:00 passed preflight with `generation_requested=false`; it does not establish that the rejected call succeeded or remove the failure.

The second diagnostic repair adds an allowlisted RPC method and standard error-code classifier, preserving the normal RPC implementation and withholding all raw messages, identifiers and error data. The final bounded invocation began at 2026-10-05T23:11:09.294525+00:00. It admitted **six cases** (English beginner/intermediate and Traditional Chinese beginner, each as term and conversation), then stopped on its seventh adapter call: `account/read`, `rpc_error`, **-32603**. Log: `.local/m5-learning-live-rpc.log`. This identifies a runtime account RPC rejection before the remaining Traditional Chinese intermediate acceptance. It is not a numerical, citation or translation validation failure. The first observation's original cause remains unknown. There is no evidence that changing the research prompt or relaxing admission would repair this account method.

All three invocations stopped on their first failure: 1, 6 and 7 adapter calls attempted, respectively. There was no internal retry, model/provider switch, sign-in change, paid fallback or source API call. Normal account/usage/tool/validation gates stayed intact. No persistent user library changed. No further live attempt is running. The complete eight-case live matrix and its final offline assertions remain **unqualified**; deterministic success and partial live results cannot substitute for them.

Manually reviewed the admitted interpretations in ignored `.local/m5-learning-review-diagnostic.json` and `.local/m5-learning-review-rpc.json`. The six covered cases preserve `1.25000000000000001 USD/share`, the original forecast end `2026-03-31`, original numerical references and the distinction between estimates and actual earnings. Traditional Chinese beginner wording uses Traditional characters, explains EPS/units and labels unknown publication/as-of time. English intermediate wording addresses consensus precision and unavailable publication/contributing-analyst information without advice. Source precision is not described as forecast certainty. This is semantic review of those samples only; Traditional Chinese intermediate has not passed live review.

Required next action: restore reliable installed Codex account RPC behavior, then explicitly rerun the full guarded matrix and review all admitted wording. The application must continue to fail closed on rejected account reads. No project-code repair for the external `account/read` internal error has been established; do not convert the successful preflight into full qualification or bypass authentication. M5 remains incomplete.

## Requirement-by-requirement review

| M5 requirement | Implementation and evidence |
| --- | --- |
| Visible asset scope, provider/model transitions and history | Dedicated conversation routes/controls; T01a/B covers reload, explicit model switch, active-run rejection, old-answer navigation and offline history |
| Exact page context, original citations and refresh | DEC-051/T01b stores selected immutable versions, records explicit changes, snapshots jobs under the scope lock; C/R/D/B checks older-page creation, refresh, original dates and legacy compatibility |
| Saved versions and affected explanation regeneration | Reports reference original bundles; `test_refresh_regenerates_used_terms_and_preserves_old_snapshot` and B manual refresh retain old versions; saved questions remain bound to their selected page |
| Language/reader parity | Deterministic eight-case matrix passes values/units/citations, no tool use and history/cache separation; six live cases pass semantic review, but full live acceptance is blocked as recorded above |
| Passive hover/focus and generic labels | B checks focus causes lookup only, with no generation; TermLearning keeps curated/general material and missing source support explicit; generated explanations are labeled unverified |
| Notes/interpretations never become facts or chart inputs | `factual_context`, typed numeric admission, term/evidence-reuse/market tests exclude notes; context/source review is rechecked, with original alias references |
| Bookmarks and retention | Storage tests cover idle expiry, active/bookmarked protection, event/request cleanup and saved-evidence retention; actual D retains bookmarked scope/response history |
| Permitted exports | New bilingual export tests and existing financial/private export cases retain exact original references and uncertainty, omit excerpts/private dependencies and leave original records unchanged |

Native artifacts predate M5 UI/context changes. All-provider and clean-machine release requirements remain M8/M11; M5 acceptance cannot promote those scopes.

Subsequent 2026-10-06 recovery: the [account-routing repair and final M5 review](2026-10-06-account-routing-recovery.md) records further failed attempts, actual bounded timeout recovery, the complete eight-case live matrix and semantic review. That later evidence resolves this acceptance blocker; the original observations and counts above are preserved.
