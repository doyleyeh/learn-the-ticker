# Installed Codex tool serialization — 2026-10-04

Scope: M1-T05, native Windows Codex 0.158.0-alpha.2.1, selected gpt-6-astra and DEC-020 restrictions. This records direct local serialization and its transport-equivalence review; it is not a local imitation of live subscription inference. Earlier evidence retains its original dates and limitations.

## Measurement and isolation

The installed protocol's complete experimental ClientRequest schema has no finalized built-in tool inventory endpoint. modelProvider/capabilities/read returns three capability booleans. debug prompt-input renders messages, not the final tool declaration. Raw rollout traces would persist request/response contents, so they were not enabled. No authenticated traffic was intercepted and no provider was replaced in production.

scripts.qualify_codex_inventory reads the selected restricted catalog through the app-owned authenticated profile without requesting a turn, then closes that process. It fingerprints the native executable before and after the check. For each browsing mode, scripts.codex_inventory starts the same binary in a new temporary profile/workspace, verifies account/read returns no account and compares all three typed provider capabilities against the subscription connection. The exact restricted catalog bytes and production tool flags are reused and verified.

The only provider changes are test transport/auth/retry fields: a loopback URL, random in-memory bearer environment variable, no OpenAI account authentication, HTTP transport and zero retries. The provider name remains OpenAI; its separate test ID does not change the reviewed is_openai branch. The local listener is bounded to one authenticated accepted request, 16-KiB headers, a 1-MB body and deadlines. It parses only in memory, validates the entire serialized additional_tools set and returns an empty HTTP 400. No model response or tool execution can result. Reports contain allowlisted tool names, declaration hashes and fixed booleans, never prompts, credentials, reasoning, raw tool schemas or provider diagnostics. Profiles, catalogs, owned processes and listener connections are closed on success/failure/cancellation.

## Source review of equivalence

The measurement itself comes from the installed executable, rather than source/configuration or a model assertion. Source review limits the inference connecting that measurement to the real subscription transport:

- [Pinned response construction](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/core/src/client.rs) serializes prompt.tools into the first developer additional_tools item for use_responses_lite, with top-level tools absent/null. Catalog bytes and namespaceTools capability match; the HTTP and subscription transport share this builder. Authentication does not select a different tool serializer.
- [Provider identity](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/model-provider-info/src/lib.rs) uses the provider name OpenAI for is_openai. The test provider preserves it and compares namespaceTools, imageGeneration and webSearch capabilities exactly. Account headers, endpoint, transport framing and retry behavior differ; no live transport/authentication claim comes from the local peer.
- [Core tool construction](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/core/src/tools/spec_plan.rs) gates account-plan-dependent image generation behind the disabled image feature. Shell/patch/agent/REPL/discovery/experimental metadata is restricted; auxiliary flags and effective layers are verified.
- [Installed App Server extensions](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/app-server/src/extensions.rs) determine contributors. [History notes](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/ext/history-notes/src/extension.rs) require token-budget configuration, which the [disabled token-budget feature](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/core/src/config/mod.rs) removes before the auth-dependent branch. Memories, goals, guardian and agent-message-board features are off. Queue and Git attribution contribute lifecycle/context, not callable model tools.
- [Hosted web](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/ext/web-search/src/extension.rs) uses the preserved OpenAI provider branch and browsing policy. Its actual retrieval/auth behavior is verified separately by live source checks.
- [Skills tools](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/ext/skills/src/tools/mod.rs) require a cloud provider with cloud skills enabled, or selected executor roots. App Server installs host/executor providers; cloud skills are additionally disabled explicitly. No roots/plugins/skills are selected, discovery/instructions/bundled skills are disabled and workspaces are isolated. Plugins/apps/MCP are disabled/empty. These cannot add an account-dependent tool to the inspected set.

This supports the same tool declaration for the measured binary/model/catalog/policy in the real connection. It does not establish general compatibility for other models or future catalog/binary/policy changes. Such changes require new direct measurement and affected live acceptance before production enablement. Existing actual subscription source, denial/cancellation and lifecycle checks remain necessary; the helper never modifies qualification records.

## Observed inventory

The final installed check began at **2026-10-04T03:42:11.277548+00:00** and exited 0 with serialized_inventory_verified_review_required. Both modes reported one local request, complete_serialized_set, credential_free_profile, provider_capabilities_match, tool_policy_matches, owned_process_closed and catalog_removed as true; cloud_inference_requested was false. Earlier successful local runs at 03:34:25 and 03:36:32 had the same inventories/digests.

| Item | Result |
| --- | --- |
| Cached explanation | Empty complete tool set |
| Research | functions.request_permissions, web.run only |
| Native executable SHA-256 | 8f0554ede25bbc5450921897c468b2e84635aa513c5017457997af0954581f49 |
| Restricted catalog SHA-256 | f63c9c65e5fa7df6b724ab3e91fe704213d8fa9af5968969f7dba61a8e9ddbf7 |
| Permission declaration SHA-256 | 85afc854f41d310b9a24cfe303cd3f467a7bc6682c7ed3f46c59913561e5c303 |
| Web declaration SHA-256 | b23e3156b759b5fa469436495753c5d7839afeb2c5f257328abb97c40ed2d447 |

## Verification and repair

- Initial prototype nested provider configuration used JSON object syntax where CLI expects TOML; dotted leaf overrides fixed startup without weakening strict parsing.
- The incomplete-request test exposed Python 3.12 server shutdown waiting on accepted transports. Closing tracked transports and cancelling handlers before server.wait_closed fixed cleanup, including tasks not yet started. The repaired focused inventory/policy suites passed 103 tests; the final inventory suite, including authenticated-process ordering and binary-change stops, passed 51 tests.
- F passed through python -m scripts.verify fast. An initial invocation used the wrong wrapper directory and failed before executing checks; EVALS' actual dispatcher was then used.
- Q passed **716 Python tests**, **seven frontend tests**, static evaluations, Ruff/ESLint, contracts, local documentation/whitespace, TypeScript and production build. Existing Starlette/httpx test-client deprecation remains.
- No dependency, database/native process implementation or frontend behavior changed. Prior D/restore and browser evidence remain dated separately. The new test listener's actual and deterministic lifecycle checks are recorded above; it is not a packaged application service.

## Live recheck and acceptance review

After the passing Q gate, qualify_codex_tools --live --model gpt-6-astra began at **2026-10-04T03:42:39.916812+00:00**. Fresh actual extended sandbox enforcement passed before four bounded subscription turns. Denial and cancellation each observed a real permission request, one turn, only empty turn-scoped responses, no pending reviews and closed processes/removed catalogs. Source search returned a validated official URL and a quotation independently supported by Investor.gov document SHA-256 91823047edeec76d24579121f19c4c1c8b884ab23514c1554f14c3d87e4dcdd5. Cached output preserved its synthetic number/citation without search. The helper's nonzero review-required outcome is deliberate, not automatic qualification.

The direct complete declaration plus the bounded equivalence review resolves the previously missing inventory evidence for this exact Windows binary/model/catalog/policy. The separate subscription recheck supplies actual denial/cancel/source/cached behavior; [earlier live lifecycle evidence](2026-10-04-codex-restricted-catalog.md) covers consent/disconnect and cleanup. No new sign-in, administrator action, permission grant, paid fallback or model switch occurred. Production remains disabled at this checkpoint: the existing version-only registry cannot yet express the narrower measured binary/platform/model/catalog scope. The next unblocked M1 work is to enforce that scope before any reviewed enablement and finish the milestone acceptance review. Other models, WSL and clean-machine/public release remain unqualified.
