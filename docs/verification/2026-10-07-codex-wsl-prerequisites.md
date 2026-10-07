# Codex WSL2 prerequisites and delivery order

Date: 2026-10-07 (Asia/Taipei). M8-T04a / DEC-066. This establishes a development prerequisite checkpoint, not authenticated Codex WSL support or public release readiness.

## Owner direction and preserved work

The owner explicitly prioritizes Codex WSL2, then Antigravity WSL2, then Claude Code on native Windows/WSL2 when subscription access becomes available. Native Windows Antigravity is deferred, with its existing isolation finding retained. OpenCode/Ollama and other open-source runtimes/models follow commercial agents; macOS is future work. Existing scoped Windows Codex remains qualified; Windows releases still require their own full acceptance.

Read-only inventory found Ubuntu-22.04 on WSL2, kernel `6.18.40.1-microsoft-standard-WSL2`. The existing `/home/ubuntu/Side Project/learn-the-ticker` is older `main` at `db42700` with untracked `NEW_STRUCTURE.md`; it was not modified. A separate qualification workspace was created under `/home/ubuntu/.local/share/learn-the-ticker/qualification/codex-wsl-inh9bxxj`, with runtime staging and a separate source clone from the canonical local Windows repository. No Windows database, virtual environment, default agent profile or provider credential was copied. The source clone is advanced to verified local checkpoints only; it does not supersede the canonical Windows checkout.

## Runtime provenance and scope

Official npm package `@openai/codex@0.158.0-alpha.2.1` selects `@openai/codex@0.158.0-alpha.2.1-linux-x64`. Installed with the existing Linux Node `22.22.2`, separate empty npm configurations/cache, the explicit npm registry, disabled install scripts and no audit/funding calls. The default WSL Node was `12.22.9` and default npm resolved into Windows; neither was used. The npm manifest declares Apache-2.0; upstream package notices remain with this developer-only installation. No runtime is added to application dependencies or release packaging.

- Linux package integrity: `sha512-dJfrsbKooySEcL8XB+uw/jfITNK8CGpjNEkpIZDIgw8ieDJwVpnKCB+XGRHg2a/Z2b35mMsagtqx4mL1TvvsjA==`.
- Native x64 executable: `284774856` bytes, SHA-256 `e8039ff5fdb49ad420a410903efae62dac2c904e616ca4261ede9e327c225619`.
- Public help SHA-256: `75c90681ba095160666d9884d1eccce391be95c80da27641a3c8e1481bb02fac` (5,769 stdout bytes). Version output is the exact pinned version. Each command also emitted 229 bounded stderr bytes; raw diagnostics are not retained or presented as a qualification result.

The new standard-library `scripts.inspect_codex_wsl` supports bootstrap Python 3.10, requires explicit WSL2 invocation and the exact Linux content pin, rejects linked/mounted Windows paths, and executes only `--version`/`--help` in disposable profiles. Its environment carries no inherited credential bus, Windows PATH, API key, token, endpoint or runtime hook. Both output streams and deadlines are bounded; owned processes/profiles are closed. Every result explicitly retains authentication/inference/credential/sandbox/generation qualification as false. This does not replace the production Windows-only identity guard.

Ubuntu packages were needed for later Linux enforcement and native credential probes: `bubblewrap 0.6.1-1ubuntu0.3`, `gnome-keyring 40.0-3ubuntu3`, `libsecret-tools 0.20.5-2`, with normal package dependencies from the configured signed Ubuntu repositories and `--no-install-recommends`. D-Bus was already present. Package notices remain installed; nothing is redistributed. Alternatives considered: bundled Codex sandbox helper, unavailable existing Secret Service, or file credentials. File credentials remain prohibited. Package presence alone is not secure-storage or enforcement evidence. The pre-install user Secret Service owner query was unavailable; no existing account or secret was read.

## Verification and repairs

- Targeted: `.venv/Scripts/python.exe -m pytest tests/desktop/test_codex_wsl_inspection.py -q` — **12 passed**. Scope includes explicit invocation, platform stop, environment isolation, content/size drift, command restrictions, malformed/flooded/timed-out output, file-credential rejection and owned cleanup.
- Windows Q: `.venv/Scripts/python.exe -m scripts.verify milestone` — **2,135 Python / 94 frontend passed**, plus static evaluations, lint, contracts, docs and production build. An initial run stopped at two new Markdown anchors; corrected both anchors and reran the complete gate without weakening it.
- Actual WSL2: `/usr/bin/python3 -m scripts.inspect_codex_wsl --inspect --binary <staged native executable>` passed before and after dependency installation. The second run confirmed all four inspected dependency commands present, with the same binary/help hashes and no authentication/inference.
- Initial npm staging failed under the original empty-config arrangement; distinct empty user/global config files succeeded. No credentials or account configuration were imported. No failed provider sign-in was retried.

Ignored Windows artifacts: `.local/codex-wsl-stage.json`, `.local/codex-wsl-inspection.json`, `.local/codex-wsl-prerequisites-q.log`, `.local/codex-wsl-apt-update.log`, `.local/codex-wsl-apt-install.log`. Linux package/cache/source files remain only in the named development workspace; do not copy its future credential state into Git or archives.

## Next gate

M8-T04b must establish a supported Linux Python/application environment, native keyring namespace isolation/persistence/failure behavior, actual Codex Linux sandbox/tool enforcement and process cleanup. Then obtain a dedicated subscription sign-in, check included usage/model/catalog, and pass Linux Q, applicable actual D/B and live app research/learning/conversation/offline acceptance. No Windows hash, account, sandbox result or model qualification transfers automatically. Antigravity WSL follows Codex WSL; Claude remains paused. No database, native package, browser, Linux full-quality or live-provider acceptance is claimed by this prerequisite checkpoint.
