# Retained import archive verification

Date: 2026-10-04. M3-T02 checkpoint. M3 remains incomplete; preview endpoints still do not retain files and provider/source admission remains M3-T03.

## Change and review boundary

Implemented [DEC-030](../../DECISIONS.md#dec-030-portable-retained-imports-before-storage-exposure): immutable bounded `import` records in the existing private document table, with original bytes, parser fingerprint/page/cell locators, timestamps, source metadata and distinct storage/backup permission. Raw content is excluded from model repr and archive-preview responses. Neither the storage boundary nor archive code contacts a provider, emits financial facts or executes imported instructions. Local processing permission alone cannot save a copy.

Format-2 archives contain the existing manifest/library JSON plus exactly the registered UUID-derived attachment members. The manifest and every record must agree on identity, bytes and SHA-256. No filesystem path is extracted, and archive reading invokes no parser. URL attachments require current registered full-text rights and cannot self-attest asset/publication/claim verification. All restored imports remain unverified; subsequent use must revalidate/reparse them.

The reader still accepts format 1. Libraries without retained files still produce the original two-member format-1 structure, without new manifest fields that older readers would reject. SQL revision remains 0001; new record kinds/format 2 are not an older-binary rollback guarantee. No destructive migration, new dependency/service, credential copy, public listener or production library change occurred.

Capacity is bounded at 5 MiB per input, 100 retained records and 64 MiB aggregate raw bytes. The existing compressed archive/JSON bounds remain 128/256 MiB. PostgreSQL serializes capacity checks with writers so concurrent admissions cannot exceed the limit. These are initial bounded import limits; the larger streamed archive/cache/scale requirements remain M9.

## Verification

- Focused retained-import, archive and preview suites: **98 passed**. Includes four-format original-byte/locator/provenance round trips; explicit permission and immutable/unverified records; link-only/changed-content rejection; invalid identity/metadata/rights and revoked registry policy; missing/orphan/duplicate/traversal archive members; inconsistent hashes/references/sizes; legacy compatibility; capacity; authenticated preview/restore and secret-free summaries; all-or-nothing rollback and changed/nonempty destinations.
- C regenerated from Pydantic and checked: BackupSummary adds format 2, retained-import count and byte total. Raw attachment payloads are not frontend contracts.
- Q passed **1,203 Python / 25 frontend tests**, Ruff/ESLint, contracts, documentation, whitespace, static evaluations, TypeScript and production frontend build. Only the existing Starlette/httpx warning remains.
- D passed against the staged PostgreSQL 17.5 runtime in fresh isolated clusters: source lifecycle/authentication/offline preview and owned shutdown; transaction/recovery; actual full archive restore/restart. Existing financial values, original source URLs/dates and reusable version-specific citations remained unchanged.
- The D restore scenario produced PDF/CSV/XLSX/HTML through actual bounded workers, then retained them. Two PostgreSQL threads competed for one remaining capacity slot under a temporary test-only lower limit; exactly one succeeded. All **five documents across four formats** participated in the archive. A later injected event-write failure rolled back records and bytes. Successful restore and a real PostgreSQL stop/start preserved every original byte, locator, timestamp, permission and unverified flag. Restored cloud consent remained off; active work was interrupted without replay. No live retrieval/subscription call occurred.

No required test failed in this slice. Full diff review covered typed/private payload boundaries, manifest/member mapping, current rights, transaction consistency and generated-contract drift. Final documentation F and staged whitespace checks passed at the local checkpoint.

## Remaining acceptance

Durable storage controls, retained-document navigation, explicit cloud transmission, no-browsing explanations and source admission are not enabled by this infrastructure. They remain M3-T03. The native executable/NSIS hashes in [native import evidence](2026-10-04-native-build.md) identify the prior native-preview checkpoint; they are not evidence that this new archive code has been packaged. Updated native end-to-end checks follow the complete retained-import workflow. No installer, live-provider or public release acceptance is claimed here.
