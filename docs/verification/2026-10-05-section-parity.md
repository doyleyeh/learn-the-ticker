# Ticker section parity — 2026-10-05

M4-T01g6 repairs two findings from the final M4 review. Admitted `news` claims now appear under reported filing news in ticker context instead of the stable overview. The display explicitly distinguishes retained filing context from an unavailable complete live news feed. Individual-stock valuation applicability is now unknown for an unresolved instrument and not applicable for a confirmed non-stock instrument.

The browser harness adds explicit synthetic fund/unknown examples through the existing production prose-admission function and fake page retrieval. The unresolved example withholds type-dependent facts. This is test-only data behind `--parity-demo`; it does not create a new production source or turn generated text into evidence.

## Verification

The affected Python suites passed **52 tests**. B (`npm run test:browser`) passed **two workflows**, covering the existing stock/numerical/review/offline workflow plus fund objective/holdings/construction/costs, keyboard risk disclosure, filing news placement, original-version source links, missing dates, unknown-type suppression and applicability. Normal/640-pixel captures were inspected for readable labels, source dates, values and overflow. The tests reported no external browser requests, page errors or research replay for the added fixture flow.

Ignored captures are in `output/playwright/automated/research-fund-and-unresolv-0f080-ls-and-applicability-states/`: fund overview at both widths, fund applicability at narrow width and unresolved overview at narrow width. B owns and shuts down its synthetic services.

The first frontend unit run caught an expectation for the previous applicability wording. Updated that exact expectation to the new unknown-state wording without relaxing the check. Final Q passed **1,697 Python/75 frontend tests**, Ruff/ESLint, schema/types, documentation/whitespace/static checks and production TypeScript/Vite build. The initial gate process finished but its result was lost in truncated tool output, so a new logged Q run was used as the reviewable final result. No check was skipped. Existing Starlette/httpx and Playwright color-environment warnings remain.

This slice changes presentation and synthetic browser fixtures only. It adds no production storage/schema/retrieval/provider behavior, so a new D or live check is not needed. It does not qualify native WebView or clean-machine behavior, analyst data, complete current news or the remaining sufficient-context request gap. M4 overall remains incomplete.
