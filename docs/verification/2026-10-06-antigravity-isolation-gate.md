# Antigravity credential isolation gate

Date: 2026-10-06. Follow-up to the [verified prerequisite checkpoint](2026-10-06-antigravity-prerequisites.md), committed as `caf2c9a`. Owner approval DEC-061 remains valid; Claude remains paused.

The next blocked action is starting authenticated Antigravity under an app-owned native-only credential namespace, without reading or altering the developer's default provider credentials. This is an integration-interface gap, not a finding that the personal Google account is ineligible. Production remains disabled.

Investigations completed:

1. Actual signed Windows 1.3.0 version/help in fresh profiles, fixed artifact/hash/output checks and owned cleanup passed. Its exposed flags contain no auth-store/profile selector or unauthenticated tool inventory. Profile redirection does not prove vault isolation.
2. Reviewed official [installation/authentication](https://antigravity.google/docs/cli/install/), [CLI reference](https://antigravity.google/docs/cli/reference/) and [settings](https://antigravity.google/docs/settings?tab=cli). Authentication can silently reuse the OS keyring, then open sign-in. The reviewed configuration does not document a native credential namespace selector or native-only failure mode suitable for this wrapper. This does not prove no undocumented mechanism exists.
3. Examined the official [SDK](https://antigravity.google/docs/sdk/overview/). Its documented quickstart uses a Gemini API key and its enterprise path uses Cloud credentials/project selection. Neither establishes the approved consumer subscription route; no SDK or billing service was activated.
4. Checked [upstream issue 381](https://github.com/google-antigravity/antigravity-cli/issues/381), a directly relevant request for supported auth-profile isolation in wrappers. It remains open as inspected, with no resolution shown. This is corroborating interface evidence, not a maintainer guarantee about all versions or proof of Windows 1.3.0 behavior.
5. Reviewed the [permission interface](https://antigravity.google/docs/permissions/): declarative deny rules are available, but effective inventory/default-deny/URL enforcement must still be measured. No-account inspection is not exposed in the pinned help. Static native-keyring/fallback symbols cannot establish runtime behavior; no binary patch, credential interception or token swapping was attempted.

No repeated login attempt can resolve the missing isolation proof. Do not use the default keyring, file tokens, account swapping, an API-key fallback or unsupported environment guesses to bypass it. A supported namespace/native-only interface or a separately reviewed isolation mechanism is needed before synthetic vault tests and login. A new OS account/VM would be a different deployment/security design, not an automatic workaround. No upstream message was sent.

M8-T01e is **BLOCKED at credential isolation**. Actual policies, included usage/model catalog, cancellation/reconnect and original-evidence live behavior remain unqualified. Resume on concrete new interface evidence, rather than repeating an unchanged probe. Continue independent M9 archive work. This documentation-only follow-up retains the prerequisite Q **2,096 Python/94 frontend**; it makes no new live, browser, database or installer claim.
