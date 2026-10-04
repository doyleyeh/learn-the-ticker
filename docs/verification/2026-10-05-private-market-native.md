# Private market native checkpoint

Date: 2026-10-05. M4-T01f6 verified within the private developer scope; results below apply only to the stated check. Public Windows v1 remains incomplete.

## Dependency and boundary review

DEC-043 pins the 24-package non-extra closure and retains 33 package/native notices with source URLs and hashes. All 24 exact-version PyPI JSON responses contained empty vulnerability lists on this date. This is a Python advisory signal, not a native security audit. Installed closure size is approximately 139 MiB before packaging. No package upgrade, paid service or credentials were introduced.

The loaded curl DLL reports libcurl 8.21.0-IMPERSONATE, BoringSSL, zlib 1.3.1, brotli 1.2.0, zstd 1.5.7, WinIDN, nghttp2 1.63.0, ngtcp2 1.20.0 and nghttp3 1.15.0. The [upstream curl version table](https://curl.se/docs/vuln-8.21.0.html) lists nine advisories. [nghttp2 GHSA-6933-cjhr-5qg6](https://github.com/nghttp2/nghttp2/security/advisories/GHSA-6933-cjhr-5qg6) affects versions through 1.68.0 under its documented frame/assertion conditions. A Python-only scan would miss these native components.

The private worker now forces HTTP/1.1 after browser-profile setup, disables HTTP/proxy authentication, and keeps the existing HTTPS/host/redirect/TLS/proxy restrictions. The real native configuration check verifies the final options without performing a request. This avoids exposing HTTP/2/3 parsing to this workflow; it does not patch the bundled libraries. The cookie advisories require public-suffix/sibling destinations or clear-text HTTP, neither allowed here. The native-CA reuse issue requires changing that setting within a session; this worker never does. The pinning issue requires disabled certificate verification; verification remains on. Negotiate authentication is explicitly disabled. The wolfSSL, OpenSSL provider management and LDAP paths are outside this BoringSSL anonymous HTTPS workflow. Public distribution still requires native dependency updates and a complete audit; no blanket security-clear claim is made.

Retained wheel notices include NumPy's OpenBLAS/GCC exception and lxml's LGPL iconv notices. Full corresponding-source/relink obligations and final runtime inventory remain M11 work. The existing developer Python 3.12.0/PostgreSQL 17.5 resources are not release-security qualification.

## Checks

- 49 targeted deterministic packaging/retrieval/transport scenarios passed. A new test initially used pytest's reserved `request` parameter name; renamed it to `payload` and reran successfully.
- Actual source dependency/owned-process smoke passed without network. Initial diagnostics exposed Curl's lack of context-manager support and the configuration helper's required two-entry option lists; explicit close and complete option lists repaired both before native/live qualification.
- Final Q passed **1,571 Python / 51 frontend tests**, correctness lint, contracts, documentation, static evaluations, TypeScript and production build. The existing Starlette/httpx deprecation remains.
- D passed actual isolated PostgreSQL startup, lock/transaction recovery and complete 12-version restore/restart, including private history/returns and original references.
- Final packaged build passed authenticated service startup/shutdown, exact CSV preview/retention/backup, all four frozen import formats and the no-network market import/options/owned-shutdown check.
- The additional `scripts.smoke_packaged_restore` check then passed actual frozen API restore into a new PostgreSQL cluster, exact market/issuer/citation/return preservation after restart, same-user backup, non-empty target rejection and reset cloud/private settings. It is now included in the packaged dispatcher; no binary changes followed the final build.
- N native passed the locked Tauri release build and NSIS assembly. No installer was installed or published.
- Final F passed after the evidence, canonical state, README and review guidance updates; all 33 notice files match the retained manifest. The staged check caught one extra cffi license blank line; normalization preserved all license wording and the final F was rerun.

The new worker uses the same executable in frozen mode, fresh temporary cwd/TEMP/TMP, allowlisted environment, bounded input/output, 1 GiB Job Object memory and 55-second timeout. The disposable extraction/cookie tree is removed after owned shutdown. No host Python fallback is permitted. The no-network diagnostic entry can only check dependencies; ordinary retrieval requests retain their strict symbol/date contract.


## Scoped frozen live check

After Q/D/packaged/native checks, ran `python -m scripts.qualify_market_research --live --asset-id FIGI:BBG000BBK0R0 --packaged-worker` once. Independent OpenFIGI identity, guarded EODHD account/one-year history and the bounded Yahoo worker completed. **1,260 daily rows and 21 corporate actions**, requested/first day **2021-09-27**, last day **2026-10-02**. YTD/1y/3y/5y/retained return windows were available under `yahoo-adjusted-ratio-v1`. Retrieval time: **2026-10-04T16:21:55.041213+00:00** (2026-10-05 local date).

Original reference: [Yahoo NVDA daily history](https://finance.yahoo.com/quote/NVDA/history/). Original response SHA-256: `cf2f5b0550cfa5d3278bbadcbca09d97545b128dadd88a20f902bf9e163f104d`; normalized private record fingerprint: `21a3c6225392af63c55b25df780dbf83c5d59fe08120b369b2214d5954a88d19`. The earlier immutable checkpoint remained readable and private values/references were excluded from model context and shareable exports. No model request or durable user-library write occurred. Only the Yahoo worker was frozen; orchestration and the discarded SQLite test database ran from source. This check does not establish native WebView live research, all tickers, full calendar completeness or public source rights.

## Local artifacts and review

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| `dist/ltt-service.exe` | 56,748,761 | `d05b665896d496487e02d798c1e33d0c5a7eda36fd420049b0f399d5107742cf` |
| `learn-the-ticker.exe` | 11,104,768 | `2f7d5d78872c51cb9ed6dbe333b9a763b75c39cea314678811fcae56a72c8980` |
| `Learn the Ticker_0.2.0_x64-setup.exe` | 78,147,510 | `f570abb8e3e0e6a5755e6e545abe5221f4ee6fe3b909e63628f5842c5e1cf895` |

Artifacts are ignored local developer outputs from the qualification build. The final staged whitespace check removed one trailing blank line from the cffi notice and updated its notice hash afterward; runtime code is unchanged, but these local binaries precede that notice-only normalization. The installer grew from the previously recorded roughly 50.7 MB to 78.1 MB; the comparison includes all intervening M4 changes, not a dependency-only controlled measurement. The reviewed 33 notices are included in the sidecar. No development environment, anonymous cookie cache, credential, user library or live price dataset enters Git or the installer.

Reviewed complete code/doc diff, same-executable dispatch, bounded errors/environment/output, exact dependency pins/notices, final curl restrictions and preservation of source/operation rules. The old test that asserted all frozen retrieval was unavailable was replaced by a fail-closed missing-worker/no-host-fallback check; no validation was skipped. Historical valuation compatibility and remaining M4 parity remain open. Full subscription parity, lifecycle/tray, native dependency upgrades/redistribution, clean-machine install/update/rollback and signing remain later release gates.
