# Addressable conversations and explicit scope

Date: 2026-10-06. M5-T01a follows the verified M4 checkpoint `ee054a3`. M5 remains incomplete.

## Behavior

Conversation selection now has its own `conversations?conversation=...` route and dedicated view. Reload restores the selected conversation from the local library. Its current asset, next selected provider/model/language, bookmark and scope-change messages remain visible. Original answers link to their immutable evidence version and provide a return link to the conversation. Opening an old response cannot redirect a subsequent question into that old response's asset: the conversation form submits its explicit current scope, separately from ticker-page research/refresh.

The new view preserves the existing backend restrictions on pending scope changes and provider/model changes, and keeps saved messages readable with cloud off. Failed submissions retain the draft. Progressive conversation sections remain accessible through the viewed-job link without replacing the conversation view. No production storage contract, source permissions, inference tooling or provider qualification changed.

Browser verification exposed a real completion race: source review can reopen a job after it has already completed. That terminal path never attaches a running-job observer and previously left the visible transcript stale despite successful database publication. It now reloads persisted library/conversation state immediately. This does not repeat the inference or rewrite the saved answer.

## Verification and repairs

- The affected storage/model/term suites passed **58 cases**.
- Actual D passed isolated PostgreSQL lifecycle, full-library backup/restore and restart. The extended scenario moves a bookmarked conversation between two asset scopes and back, retains its original answer pointing at the older saved bundle, and requires the entire normalized conversation to match after restore and restart while the current asset still points at the newer bundle.
- Initial D compared the unnormalized update dictionary with the archive's validated contract, so optional absent message fields differed. The expected conversation is now normalized through the same public `Conversation` contract before comparison; all messages, dates, IDs, scopes and bookmarks remain subject to exact equality. No restore requirement was removed.
- Two initial browser harness defects were diagnosed separately: a controlled setting needed an assertion after the asynchronous save, and successive source-review cards needed to wait for the old card to detach before selecting the next stage. The following run exposed the production completion race above. After its repair, all three browser workflows passed. Final coverage was then extended to a subsequent selected-provider/model answer and manual refresh preserving the original report and response links; final results follow below.

The preview's additional provider/model catalog is explicit synthetic test injection under `--conversations-demo`. It never launches or qualifies Claude/Codex subscriptions and adds no network fallback. Existing financial/review/normal/narrow scenarios remain required. Reviewed the React changes for state ownership, async completion, hook cleanup, keyboard labels, escaped transcript text and component boundaries using project-delivery and React best-practices.

The extended refresh assertion initially observed the previous job's completed label before the newly submitted refresh appeared, then tried to navigate during progressive publication. It now requires the new refresh request's text before checking completion. This repairs test synchronization; no production status or evidence check was relaxed. Each diagnosed issue had a successful correction before the next distinct issue; no product issue reached three failed repair attempts.

Q passed **1,842 Python / 87 frontend tests**, lint, non-writing contract/schema checks, local links, whitespace, static evaluations and production TypeScript/Vite build. Final B passed **three workflows** including the newly extended explicit provider/model continuation and immutable refresh checks. Wide and 640-pixel conversation screenshots were inspected: readable scope/provider and original-response links, wrapped text, enabled/disabled controls and no page overflow. Existing financial/review flows still passed. Preview listeners on 1420/18764 exited.

The final fixture review added a fail-fast requirement that `--conversations-demo` must also select `--source-review-demo`, preventing its delegate from being a real runtime when the flag is used alone. An explicit negative CLI check passed before opening a preview database/server. No live provider call, native artifact rebuild, new dependency or SQL migration was needed for this UI-only production change. Existing native artifacts predate this view.

Ignored logs: `.local/m5-conversation-q.log`, `.local/m5-conversation-d2.log`, `.local/m5-conversation-b-verified.log`, `.local/m5-fixture-isolation.log`; earlier diagnosed failures retain their separate log names. Captures are under `output/playwright/automated/research-conversation-scop-05c84-riginal-response-navigation/`: `conversation-provider-wide.png`, `conversation-scope-narrow.png` and `conversation-offline-narrow.png`. Existing Starlette/httpx and Playwright color-environment warnings remain. Final F passed; M5-T01a is complete and no failing check is waived.

## Remaining M5 acceptance

The conversation still starts from an asset ID, not an explicit immutable page-context version. Review/implement that starting-context link and its refresh semantics before claiming complete P-023 page-context parity. Full bilingual beginner/intermediate conversation/term and export/live acceptance remains M5-T02. Current selected-provider display does not attest the actual model of older responses whose provenance was not recorded. M5-T01 and M5 remain open.
