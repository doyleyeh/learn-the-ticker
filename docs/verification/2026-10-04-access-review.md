# Correlated access review — 2026-10-04

Scope: M1-T03b deterministic review/deny/cancel behavior under the existing research policy. No permitted tool scope was expanded. Positive grants are unavailable, as explained in [DEC-012](../../DECISIONS.md#dec-012-access-review-cannot-expand-research-policy). M1 remains incomplete until cancellation/session and live qualification pass.

Implemented memory-only reviews tied to one active job and the runtime thread/turn/request identifiers. The API rejects grant payloads, foreign jobs and replayed/expired decisions. Only sanitized request categories appear in the interface. Command/file requests receive decline or cancel; permission requests receive an empty turn-scoped grant. Cancellation, expiry and consent revocation stop work. Cached-evidence explanations cannot request additional access. No persisted schema or dependency change.

## Verification

- Focused approval/Codex/model/term suites: 83 passed. Fifteen new approval cases include three protocol families, invalid/foreign identifiers, request floods, deadline, duplicate responses, authenticated API, grant rejection, cancellation, cloud revocation and absence of raw vendor fields from persisted events.
- Shared milestone gate passed: 391 Python tests, static evaluations, seven frontend tests, lint, non-writing schema/type checks, links, whitespace and production TypeScript/Vite build. Existing Starlette/httpx test-client warning remains.
- Playwright CLI against `tests.desktop.preview_server --approvals-demo --login-demo`: denial continued to a completed synthetic partial asset; Shift+Tab/Enter activated cancellation and retained the previous snapshot; an unanswered review disappeared at its deadline and displayed an expiry error without retry. The synthetic fixture invoked no provider.
- Visually inspected normal and 640-pixel review panels; measured no horizontal overflow at 640. Missing sections and snapshot dates remained explicit. Source/citation inspection in the preceding [model-selection browser run](2026-10-04-model-selection.md) covers the unchanged source renderer. Screenshots are ignored local evidence at `.local/output/playwright/access-review-normal.png` and `.local/output/playwright/access-review-640.png`. Browser and preview services were stopped afterward.
- Browser console contained the existing developer shim/Permissions-Policy warnings and favicon 404; no application exception was observed.

## Unqualified boundaries

Generated installed-version schemas establish response shapes only; synthetic results do not prove live approval behavior or sandbox enforcement. The production qualification registry still enables no generation or approvals. Process death while a review waits and complete process-tree/session recovery belong to M1-T04; live subscription checks to M1-T05. Native packaging and clean-machine release remain blocked.
