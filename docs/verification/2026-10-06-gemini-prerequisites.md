# Gemini prerequisites and Windows launcher

Date: 2026-10-06 (Asia/Taipei). Scope: M8-T01a prerequisite/launcher slice. M8-T01 remains in progress and no subscription capability is enabled.

The host inventory found no `gemini`/`claude` command on PATH, no corresponding standard npm package and no usual native Claude entry. This establishes installation discovery only; it does not determine the user's account or subscription state. Official Gemini CLI 0.62.0 was then staged under ignored `.local/gemini-qualification`, using `npm install --prefix .local/gemini-qualification --no-audit --no-fund --ignore-scripts --save-exact @google/gemini-cli@0.62.0`. Seven packages were added without global PATH changes or project dependency changes. npm integrity: `sha512-A1rw0Tf2sHLpGncfYdaq5WaJIufKAP8il4BmHD5Yw4ewmB/Wo0vRQb2bEvx7OqyaPFPZCh0hVhcMKsICZyIBww==`.

## Findings and repair

The actual package declares `bundle/gemini.js`; our Windows launcher assumed only `dist/index.js`. Resolution now validates bounded official package metadata and accepts only those two reviewed paths, both under a global npm root and a local `node_modules/.bin` shim. Missing, malformed, excessive, unknown or escaping entries fail closed. Node invokes the JS entry directly; no shell shim runs. The reviewed Codex/Claude entry filenames and all provider qualification gates remain unchanged.

Official [installation guidance](https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/installation.mdx) documents Windows/Node support and the npm package; the staged metadata declares Node >=20 and Apache-2.0. [Authentication guidance](https://geminicli.com/docs/get-started/authentication/) distinguishes Google sign-in from API-key/Vertex paths and says headless use can reuse previously cached authentication. This inspection did not sign in or use any subscription/API credential.

[Enterprise configuration](https://geminicli.com/docs/cli/enterprise/) documents profile isolation and tool allowlists; [policy documentation](https://geminicli.com/docs/reference/policy-engine/) describes explicit denials and policy precedence. These are mechanisms to investigate, not proven enforcement. The staged source also shows native keytar can silently fall back to file storage. That behavior must be excluded before real credentials or generation are permitted. The current transport remains disabled.

## Verification

- Actual isolated `--version` and `--help` both exited zero with no stderr. Version **0.62.0**; only documented help/version paths invoked (`.local/m8-gemini-inspect.log`).
- Repaired resolver launched the actual staged package through Node, returned exact 0.62.0, and left generation/browsing disabled under the existing policy (`.local/m8-entry-actual.log`).
- Native keytar loaded and completed a unique synthetic Windows Credential Manager write/read/delete; both round trip and removal were true (`.local/m8-gemini-vault.log`). No real credential was enumerated, read or copied. This proves host capability only, not provider no-fallback enforcement.
- Targeted runtime entry/policy suite: **35 passed** (`.local/m8-entry-targeted.log`). Final Q `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1`: **1,999 Python/94 frontend tests passed**, lint, unchanged contract equality, documentation, static evaluations, TypeScript and production build (`.local/m8-entry-q.log`). Complete/staged diff and final documentation checks precede the local commit.

Next: establish a bounded dedicated configuration and complete tool declaration/denial proof, native-only credential handling and model routing/catalog semantics before onboarding or live qualification. Account sign-in, quotas or extra charges remain stop conditions. No installer, provider auth state, source rights or public readiness was changed.
