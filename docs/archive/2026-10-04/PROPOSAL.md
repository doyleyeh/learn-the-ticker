> Historical snapshot archived 2026-10-04. This document is no longer authoritative. See [the current source of truth](../../../SPEC.md) and [document ownership](../../../AGENTS.md). Original verification dates and claims below are preserved.

# Learn the Ticker proposal

Learn the Ticker turns a user's commercial agent subscription into a local, reusable financial learning library. A question about an unfamiliar asset should lead to sourced research, visible evidence gaps and follow-up explanations, with the evidence saved locally for reuse.

The initial audience is comfortable cloning a repository. The public Windows release should also serve ordinary beginners through a self-contained desktop installer. Beginner and intermediate research receive equal access. The application is free and open source; provider subscriptions, optional financial APIs and data rights remain the user's resources and constraints.

The product priority is one-asset understanding, then conversational research, then comparison. Broad dynamic identity resolution replaces a fixed launch universe. Structured financial sources complement agent browsing. Neither a model's confidence nor a plausible URL establishes a fact.

The advantage over a transient chat is durable evidence: dated sources, reusable normalized facts, persistent conversations, versioned reports and a consistent asset interface. The app should explain what it knows, what it cannot verify and what needs refreshing.

Preserve the useful financial interface while moving it to React/Vite in a Tauri desktop window. FastAPI and private PostgreSQL own application operations and durable state. Concise term learning, English and Traditional Chinese explanations, citations and dated saved research help users move between beginner and intermediate understanding without losing context.

Local-first describes ownership, not offline inference. PostgreSQL and the UI run on the user's machine; retrieval and commercial inference make disclosed outbound requests. No project-operated research backend or telemetry is required.

Scope excludes trading, brokerage execution, recommendations to buy/sell/hold, personalized allocations, price targets and tax advice. Advice-like questions are redirected into education. Important claims carry citations. Unverified notes remain distinct from factual evidence.

Implementation follows [NEW_STRUCTURE.md](NEW_STRUCTURE.md) and [PRD.md](PRD.md). Native Windows comes first; macOS, WSL and Linux follow. Public v1 requires working Codex, Gemini and Claude subscription connections, reliable private storage, complete research UX and tested packaging. The current implementation state is in [the backlog](IMPLEMENTATION.md); this proposal is not a declaration of release readiness.
