# Dedicated WSL Codex sign-in handoff

Date: 2026-10-07 (Asia/Taipei). M8-T04b2a, developer qualification only. This does not establish WSL generation support or a production credential-session integration.

## Prepared behavior

`scripts.login_codex_wsl` requires an interactive WSL2 terminal and the exact reviewed Linux Codex binary. It checks the binary before starting, before device authorization and after authentication. Its fixed app-owned credential root is `/home/ubuntu/.local/share/learn-the-ticker/wsl-codex-credentials` on this machine, outside both Git checkouts. Root ownership, private directory modes, a role marker, absence of linked contents and absence of auth.json are required. Existing unmarked state is refused without overwriting it. An exclusive lock prevents concurrent sessions.

The user privately types a nonempty local keyring password with hidden terminal input, confirming it for a new keyring. No password is accepted from arguments, environment, files or chat. A separate D-Bus and GNOME Secret Service use this root's encrypted keyring; a synthetic store/read/delete must succeed before provider authorization starts. Empty/unavailable/locked storage stops without file fallback. No Windows credential, personal keyring or default Codex profile is imported.

The helper uses the existing strict production Codex RPC and device-login validators through a developer-only factory supplying this private bus and pinned executable. It does not change the production runtime registry or model/usage guards. Only the validated official OpenAI device URL and ephemeral code are shown in the interactive terminal; reports retain neither. Successful sign-in keeps the owned session open until Enter/Ctrl+C. `session.json` contains only local process/binary/environment coordinates with mode 0600, never passwords/tokens/codes, and is removed on normal cleanup. The encrypted native keyring remains for later user unlock. These development coordinates are not a production service-discovery mechanism.

## Verification

- New targeted tests: Windows **8 passed / 2 Linux-only skips**; actual Linux **10 passed**. The Linux cases exercise real temporary ownership/modes/links, not a Windows approximation.
- Actual disposable session-composition experiment: the real private D-Bus/keyring accepted and cleared a synthetic canary; the helper's RPC factory opened the actual pinned Codex app server, passed strict effective-policy checks and read an empty account. The experiment replaced only the device-login controller with a no-login controller, so no account/login/start or inference was requested. Expected authentication-required termination closed the session and left no auth.json/session coordinates. This is composition evidence, not a fake successful sign-in.
- Actual account-free app-server enforcement experiment: pinned binary rechecked before/after; fresh isolated HOME/profile, strict effective policy, empty account and validated isolated thread. The production `CodexRPC` transport executed the boundary helper's fixed file/network canaries through `command/exec` with `sandboxPolicy={type:readOnly,networkAccess:false}`, an explicit owned workspace and a 15-second command deadline. Read control succeeded, the file stayed unmodified, and all IPv4/IPv6 TCP/UDP listener controls succeeded while sandbox traffic was denied. The application RPC/profile closed with no auth.json or inference. The harness supplied only owned environment/binary dependencies and the command executor; it did not alter permission settings or qualification. Sanitized report: `.local/codex-wsl-app-server-sandbox.json`. Model-facing tool inventory and authenticated enforcement still require later checks.
- Actual noninteractive invocation stopped with `interactive_terminal_required` before creating/changing its credential root or requesting login.
- Windows Q for this helper: **2,154 Python / 2 Linux-only skips / 94 frontend**, static evals, lint, contracts, docs and production build passed, including the final bounded-marker repair. Prior full Linux Q and boundary results are in [boundary evidence](2026-10-07-codex-wsl-boundaries.md); the ten new helper tests also passed on actual Linux.
- Complete Linux Q at helper commit `1544df2`: **2,136 Python / 20 Windows-only skips / 94 frontend** plus static evals, lint, contracts, docs and production build passed. Both full gates retain platform-specific checks; no failing check was skipped. The qualification clone contains the reviewed helper; the old WSL checkout remains `db42700` with only its original untracked `NEW_STRUCTURE.md`. The persistent interactive credential root has not been created and no user sign-in has started.

## User interaction

In an interactive **Ubuntu-22.04 WSL terminal**, after the source clone has advanced to the verified helper checkpoint:

```bash
cd /home/ubuntu/.local/share/learn-the-ticker/qualification/codex-wsl-inh9bxxj/source
.venv/bin/python -m scripts.login_codex_wsl --login --binary /home/ubuntu/.local/share/learn-the-ticker/qualification/codex-wsl-inh9bxxj/runtime/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex
```

Enter the local keyring password privately, complete the official ChatGPT device sign-in shown in that terminal, and leave it open for qualification. Never send the password or device code in chat. Press Enter to close the credential session when qualification is finished. No model call is made by this helper.

User availability for this required interactive step was requested. Authentication has not been attempted. Next: verify real persistence/restart/refresh under user unlock, authenticated app-server/model-facing restrictions, account/model/included usage, then the production WSL route with Q, real private PostgreSQL lifecycle/restore, browser and live workflow acceptance. No production promotion is permitted merely because sign-in succeeds.
