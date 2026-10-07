# Paid-agent subscription disclosure

Date: 2026-10-07 (Asia/Taipei). Scope: M8-T03 / DEC-065, owner-requested prerequisite disclosure. This completes an independent UI/documentation slice, not M8 or public Windows v1.

## Change and acceptance

One shared, semantic notice appears before local setup, with an empty library and in Connections. It explains that the application is free/open source but users bring their own compatible paid commercial-agent subscription for new AI work. It describes source finding/review, analysis, summarization and explanations; consented cloud transmission; saved research/conversations/explanations and built-in definitions; included-usage stops; and no paid API fallback or automatic overages.

The notice and README identify the current scoped ChatGPT/Codex path and unfinished Gemini/Claude support. They do not promise free-account integration or equate payment/login with compatible model/runtime access. Empty-library guidance and Codex sign-in instructions agree. Existing runtime/account/model/usage, source verification and consent checks are unchanged. The component has no effect, request or authentication action; its optional link changes only the local route.

## Verification

- F: `.venv/Scripts/python.exe -m scripts.verify fast` passed.
- Q: `.venv/Scripts/python.exe -m scripts.verify milestone` passed: **2,123 Python tests**, static evaluations, **94 frontend tests**, lint/contracts/docs and production build. One Python warning remained; no failing or skipped required gate.
- B: `npm.cmd run test:browser` passed **all nine workflows** in 49.3 seconds. Existing source review, source/citation/freshness/missing-state presentation, reconnect, conversations, comparisons, reports and offline deletion/cache workflows remained intact.
- Actual browser visual inspection: pre-connection setup, empty library and Connections were readable at normal desktop and 640-pixel widths. The notice precedes first research controls; navigation/text wrap and empty-state guidance remain readable. Keyboard Enter on **Set up your agent** navigates to Connections. Cloud research remained unchecked, the library remained empty and the model selector remained unavailable; no sign-in, generation, model refresh or provider enablement was invoked.
- React review: a directly imported, stateless shared component uses existing layout styles and a uniquely labelled `aside`; no additional hooks, listeners, dependency or network call was introduced.
- Full diff review found only the authorized disclosure and owning-document changes; no credential, generated artifact, provider registry, backend, schema or test weakening changes.

The browser review used an empty disposable SQLite fixture through the production API factory and the explicit synthetic preview credential. Default runtime adapters were constructed but no runtime checks, sign-in or generation were invoked. This is UI evidence, not PostgreSQL, native, installer, free-account or live-provider qualification. The older browser skill backend was unavailable; the available in-app browser control supplied visual/keyboard review. Existing B used its deterministic fixture services. The temporary viewport was reset and the review tab/services were stopped; both loopback ports were confirmed closed.

Ignored local artifacts: `.local/subscription-disclosure-f.log`, `.local/subscription-disclosure-q.log`, `.local/subscription-disclosure-b.log`; screenshots under `output/playwright/subscription-disclosure/` (`setup-desktop.png`, `setup-narrow.png`, `empty-desktop.png`, `empty-narrow.png`, `empty-state-desktop.png`, `empty-state-narrow.png`, `connections-desktop.png`, `connections-narrow.png`, `connections-controls-narrow.png`). Final fast/doc/whitespace review after this evidence update is recorded in `.local/subscription-disclosure-final-f.log`.

## Remaining delivery state

Antigravity retains its credential-isolation blocker and Claude remains owner-paused. No subscription purchase, paid API, provider promotion or resumption was performed. M9-T01g3 is the next independent implementation task; the new notice does not resolve provider or release acceptance gates.
