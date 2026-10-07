# First local-model prototype roadmap

Date: 2026-10-07 (Asia/Taipei). Documentation checkpoint for DEC-067; M8-T06 and M8-T06a remain TODO.

The owner selected the existing Codex harness with Ollama as the first local-inference prototype after DEC-066's active commercial-agent targets, with LM Studio as the runtime comparison. The decision, plan, tasks, current status, README and review guidance now agree. OpenCode and agent libraries remain evaluation candidates, not adopted dependencies.

Acceptance for this checkpoint is a durable, consistent evaluation order that preserves the current WSL sign-in handoff and makes no production-support claim. No application code, dependency, runtime, model, credentials, database or release capability changed. The local API boundary is distinguished from metered inference, and hosted search must be evaluated independently.

Verification on native Windows:

- `.venv/Scripts/python.exe -m scripts.verify milestone`: passed; Ruff, ESLint, schema/type drift, local Markdown links/anchors, whitespace, static evaluations, 2,154 Python tests and 94 frontend tests, TypeScript and frontend build.
- Two Linux-only Python cases skipped on Windows; existing FastAPI/Starlette `httpx` deprecation warning remains.
- Reviewed all changed documentation for scope, ordering and qualification claims. No new test was needed for this documentation-only change.

This check does not qualify Codex with local models, Ollama, LM Studio, any search service, Linux app workflows or installers. No live provider or model execution occurred. Existing commercial integration and release acceptance remain incomplete.
