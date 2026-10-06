# Gemini login-only acceptance and owner-paused Claude

Date: 2026-10-06. Branch: `codex/project-delivery-foundation`. Scope: M8-T01b/DEC-056; no production generation enablement or release qualification.

## Owner direction

The owner requested navigation to Gemini sign-in and temporary suspension of Claude/Claude Code because no subscribed Claude account is available. M8-T02 is PAUSED until the owner resumes it. Existing code and synthetic tests remain. Account-free development is possible, but live subscription acceptance cannot be established by synthetic responses. P-040 and M8's all-three-provider release requirement remain unchanged; independent M9 work can continue.

Official [Claude authentication requirements](https://code.claude.com/docs/en/setup#authenticate) exclude the free claude.ai plan from Claude Code. Paid API/Console alternatives are not this project's subscription path and were not activated. Official [Gemini authentication](https://geminicli.com/docs/get-started/authentication/) directs local users to Google sign-in, including the Google account associated with their applicable subscription.

## Implementation and review

`scripts/connect_gemini.py` uses the official staged 0.62.0 package from the [prerequisite checkpoint](2026-10-06-gemini-prerequisites.md). It verifies the reviewed OAuth core and four imported bundle hashes, sanitizes the child environment and requires an explicit `--check` or `--login`. It imports the OAuth implementation directly, never the CLI UI/configuration/model/tool startup. No new dependency or modification of the upstream package is required.

The reviewed source defaults to a legacy credential file unless its encrypted-storage flag is selected; that alternate path still has a file-keychain fallback. The bridge selects that path and replaces only native keychain initialization, failing if the native keychain is unavailable. It sets a dedicated Windows service namespace before all native access. Existing fallback/legacy credential paths in the dedicated profile cause a stop without reading or migrating them. The usual Gemini profile and credential namespace are not accessed.

OAuth opens the official Google page with a loopback state-validated callback. The user completes account choice/consent in the browser. Only fixed statuses leave the helper; raw provider output, account identifiers, tokens and callback URLs are not retained in reports/logs/Git. The provider's asynchronous storage errors remain terminal, and success additionally checks that the native saved access token matches the authenticated client. The user profile is outside the repository/library backup. No research prompt, model selection, tool call, cloud billing activation or application capability change occurs.

## Verification

- Six Python tests passed; the embedded JavaScript scenario suite covers native-unavailable rejection before auth, check-only behavior, isolated successful persistence, failed writes, foreign services, missing persistence and invalid modes. Other cases cover hostile inherited auth/billing/Node options, version/code drift and preserving file credentials without importing the provider. Synthetic tests use no provider package, account, vault or network.
- Actual `python -m scripts.connect_gemini --check`: `native_storage_ready`, using the pinned source and native Windows keychain's synthetic write/read/delete. No actual auth was read during this probe.
- Q: `python -m scripts.verify milestone` passed **2,005 Python / 94 frontend tests**, lint, contracts, Markdown checks, static evaluations, TypeScript and production build. Local log: ignored `.local/m8-login-q.log`. The file-credential test was strengthened to detect an unexpected provider import and all six targeted tests passed again. Existing Starlette/httpx deprecation warning remains.
- After Q and explicit owner authorization, actual `python -m scripts.connect_gemini --login` opened the Google flow and exited **0**, reporting `authenticated`. This includes real native credential persistence confirmation. No credential/account values were printed. No inference was requested.
- Final F and staged diff review passed; local Markdown links/anchors passed for 95 files. The dedicated profile contains neither legacy nor fallback credential files (existence-only check). Browser product, database/native installer and live inference lanes are not triggered or claimed by this login-only helper.

## Remaining acceptance

This is developer-only tooling tied to internal pinned exports. It is not production Connections onboarding, general Gemini CLI qualification or verification of a paid tier/available quota. M8-T01 still requires production credential integration, complete isolated tool inventory/denial tests, model catalog/routing, included-usage enforcement, cancellation/reconnect and live evidence behavior. Google sign-in alone enables none of these. Claude remains paused and unqualified; public Windows v1 remains incomplete.
