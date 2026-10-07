# Restricted Codex catalog and actual permission review — 2026-10-04

Scope: M1-T05d, following the user's explicit approval of the [restricted-catalog/request-only proposal](2026-10-04-codex-tool-policy-investigation.md#proposed-repair--awaiting-scope-approval). DEC-020 records that approval. This checkpoint repairs tool exposure and exercises actual denial/cancellation; it does not complete M1 or enable production generation.

## Implementation and review

The runtime first checks the dedicated ChatGPT subscription and resolves the selected provider model. It obtains bounded metadata through the isolated, owned `debug models` diagnostic process, requiring the reviewed serialized model shape, unique identities and known tool fields. Unknown/missing fields, duplicates, malformed/oversized output and incompatible metadata stop the operation. Diagnostic output remains in bounded memory with stderr discarded; no raw catalog, prompt, transcript or credentials are retained in reports/Git.

A temporary single-model catalog preserves identity and all non-tool metadata. It narrows tool mode to direct, shell to disabled, patch to null, experimental tools to empty, discovery to false, multi-agent mode to disabled and node REPL to disabled. Additional model-driven agent exposure was found during source review; agents.enabled=false also enforces the configuration override. Plan/input/time and existing prohibited features are explicitly disabled. The exact model remains **gpt-6-astra**, using **Codex 0.158.0-alpha.2.1** and the existing ChatGPT subscription. No provider/model switch, API billing, new grant, dependency, OS provisioning or WFP change occurred.

App Server restarts with that catalog before creating a thread. File identity/content, selected model, effective configuration/features, subscription authentication and read-only/network-disabled thread isolation are verified before inference. The production server retains strict parsing. Only the diagnostic subcommand omits its unsupported strict flag, after a strict RPC verification. Research enables request_permissions solely for denial/cancellation; cached operations do not enable it. Every permission response contains empty permissions and turn scope. Repeated IDs/items and invalid review decisions fail closed. Optional permission function-output items must correspond to an actual prior denial and contain only empty/null permissions; arbitrary outputs or reported grants are rejected.

Temporary catalog files and owned process trees are closed on ordinary completion, startup failure and cancellation. Integrity failure stops inference; replacement files/links are preserved rather than recursively deleted. Metadata files abandoned by an abrupt host/OS termination are not reused. They contain provider model metadata, not account credentials or generated research. This is not packaged-host crash/installer acceptance.

The initial installed no-inference check exposed a serialization mismatch in the new validator: normalized agents includes default fields and normalized tools contains only legacy web_search=null, not the plan/input switches. Two incomplete comparison repairs still failed. Inspection established the precise representation; the third repair passed by validating the effective agents.enabled flag and exact unique strict sessionFlags tool/agent settings, plus the known normalized tools representation. No failing check was skipped or converted into a pass.

## Verification

- Focused new metadata, output and harness scenarios: **65 passed**. They include selected metadata preservation, unknown fields, duplicates, bounds, API-key/environment exclusion, owned diagnostic cancellation, catalog tampering/replacement/link rejection, restart failures/model drift, strict-layer boolean types, reauthentication and final-policy failure before a turn, replay, grant rejection and actual adapter/broker behavior over synthetic transport.
- Q before live checks: **655 Python tests**, seven frontend tests, static evaluations, Ruff/ESLint, contracts/docs/whitespace, TypeScript and production build passed. Ten additional deterministic scenarios were then added. **Final checkpoint Q passed 665 Python tests and seven frontend tests**, with the same static/lint/contracts/docs/TypeScript/build checks. Final document-state edits additionally passed documentation and whitespace checks.
- `python -m scripts.smoke_codex_protocol`: actual installed fresh-profile checks passed both browsing configurations, hostile-parent isolation and minimal elevated-setting compatibility; no inherited account, sign-in or inference. Capabilities remained protocol-only.
- `python -m scripts.qualify_codex_tools --model gpt-6-astra`: production catalog restart/thread preflight passed without inference at **03:20:00 UTC**. Research-mode configuration was also verified before each live research turn below.
- D, with PostgreSQL 17 and disposable private clusters: initialization/migrations/authenticated service, lock/transaction rollback/commit/recovery/restart, and full-library restore passed. Restore checked preserved saved versions/events, non-empty target rejection, rollback and actual restart. No live providers or user library were involved in D.

Existing Starlette/httpx test-client deprecation warning remains. No new frontend/database contract changed, so this checkpoint does not claim a new UI/native release acceptance result.

## Actual subscription observations

The restricted-tool run began its fresh preflight at **03:20:52 UTC**, then passed actual extended file-write and IPv4/IPv6 TCP/UDP sandbox enforcement before four bounded turns. Every turn independently required ordinaryUsageAllowed=true, the same model and the strict catalog policy. There was no automatic retry.

| Actual check | Result |
| --- | --- |
| Permission denial | A real item/permissions/requestApproval reached the application broker. It received only empty turn-scoped permissions; the model acknowledged denial and completed. Exactly one turn; no pending review, owned process or temporary catalog remained. |
| Permission cancellation | A second actual request reached the broker. An empty turn-scoped response was followed by application cancellation; the turn stopped. Exactly one turn; review/process/catalog cleanup passed. |
| Research tool observation | The model reported exactly functions.request_permissions and web.run. This is corroboration, not authoritative inventory. No functionCallOutput item was observed in either review turn; optional-output validation has deterministic coverage only. |
| Hosted source capture | Search activity occurred, the original Investor.gov URL passed validation, and an exact short quotation matched an independent public download. Only its fingerprint was retained: 91823047edeec76d24579121f19c4c1c8b884ab23514c1554f14c3d87e4dcdd5. This is not M2 asset/rights admission. |
| Cached operation | Preserved synthetic 100 and fixture-1, no search activity, and the model reported an empty tool list. Self-report does not certify inventory. |

The helper deliberately ended `probes_finished_review_required` with `live_qualified=false` and a nonzero review-required exit. That is not a Q failure or production promotion.

A second fresh preflight at **03:23:14 UTC**, followed by actual extended enforcement, preceded two additional bounded lifecycle turns through the application service and authenticated API using a disposable in-memory SQLite library:

- Revoking cloud consent produced the expected cancelled job, acknowledged interruption, closed owned process, cleared approvals, no raw message/candidate publication, unchanged selected model and one turn with no replay on repeated job reads.
- Disconnecting only the probe's owned provider process produced the expected failed job with the same publication/cleanup/model/no-replay protections.

These two live service checks use the existing `qualify_codex_acceptance.service_probe` with the repaired production adapter. SQLite is a disposable harness here; it is not a substitute for the separately passing PostgreSQL D lane.

## Remaining blocker and next action

The prior **unexercised denial/cancel blocker is resolved** on this developer machine. The restricted catalog is implemented and accepted by the actual runtime, and positive source/cached behavior survived it. The production capability registry remains unchanged.

Complete model-facing tool inventory is still not authoritative. The pinned App Server schema has no full built-in inventory endpoint, model/list omits tool schemas, and debug prompt-input returns messages rather than the final tool set. Settings, pinned source analysis and a model's own list cannot prove every tool presented by the installed process. Do not relabel those as full live isolation qualification or repeat equivalent refusal/self-report turns.

M1-T05 remains blocked on a supported complete inventory attestation for the actual selected-model thread, or a separately reviewed runtime/transport change that provides equivalent direct evidence. Any such change must preserve the approved no-execution/no-grant/subscription boundaries and pass deterministic and live acceptance. This is an evidence/interface gap, not another sign-in, sandbox setup or permission grant. M2–M11 remain dependent on M1; cargo and clean-machine packaging/update/rollback are separate known release blockers.

Reviewed source references: [pinned permission handler](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/core/src/tools/handlers/request_permissions.rs), [permission response format](https://github.com/openai/codex/blob/rust-v0.158.0-alpha.2.1/codex-rs/protocol/src/request_permissions.rs), and the pinned tool registration/configuration sources listed in the preceding investigation. No provider source was vendored.
