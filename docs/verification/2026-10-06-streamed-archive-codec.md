# Streamed archive codec and transactional restore

Date: 2026-10-06. Scope: M9-T01g2 / DEC-064, building on the [private index foundation](2026-10-06-backup-index.md). This checkpoint concerns file-based backend operations. HTTP/browser/native archive transport remains M9-T01g work, and public Windows v1 remains incomplete.

## Behavior and compatibility

Format 3 writes fixed `records.ndjson`, `jobs.ndjson`, `events.ndjson`, `manifest.json` and registered original attachment members. Each table has exact byte/row counts and SHA-256. Each row is individually serialized, read and staged in a private disk index; the shared validator retains original identity, financial calculations, citation references, usage rights, permission, job and normalized-event checks. Restoring uses the existing locked empty-library transaction, explicit preview fingerprint, network/startup consent reset, pending-run interruption and event-sequence recovery. Flush each row to bound the ORM pending set; no model/retrieval is replayed.

ZIP/ZIP64 directory metadata is bounded before constructing the ZIP member list. Reject duplicate/unregistered/encrypted/unsupported members, inconsistent offsets, oversized/nonterminated rows, counts/checksums, changed archives and malformed references. Compressed and expanded data each have a 64-GiB defensive ceiling, rows 64 MiB, directory 256 KiB and manifest 64 KiB. Original table/attachment-count and retained-document capacity limits remain. ZIP64 end-record behavior is exercised with a lowered synthetic boundary, not a physical multi-GiB file.

Formats 1/2 remain readable with their original bounded parser/limits; they are not claimed to use streaming memory. The PostgreSQL schema stays `0001`, and no existing archive is rewritten. Format 3 is not readable by older app versions; coordinated rollback remains M10. No new dependency, credential handling, source permission or provider capability. Created outputs/indexes use owned temporary directories, with no user-selected path overwrite or archive extraction. Disk failures remove unpublished partial files.

## Repairs and deterministic checks

The first focused run passed 103 tests but exposed `PytestUnraisableExceptionWarning`: an exception traceback retained a paused SQLite row iterator until after its index connection closed. The index now owns active cursors and closes them before the connection; later iterator cleanup sees that ownership was already released. A regression deliberately keeps the iterator alive beyond context exit. This fixes lifetime ownership without suppressing the exception/warning.

Final targeted command: `python -m pytest tests/desktop/test_backup_stream.py tests/desktop/test_backup.py tests/desktop/test_backup_index.py tests/desktop/test_retained_imports.py -q -W error::pytest.PytestUnraisableExceptionWarning`: **104 passed**, with only the existing Starlette/httpx deprecation warning. Cases include both legacy formats, original retained bytes, changed checksums and recomputed malicious content, exact reference/credential rejection, malformed/duplicate members, row and ZIP-directory bounds, ZIP64/truncation, preview/target races, nonempty refusal, late write rollback, disk failure and cleanup.

Q `python -m scripts.verify milestone`: **2,123 Python / 94 frontend**, lint/contracts/docs/static checks and TypeScript production build passed. Generated schema/TypeScript include the new summary format discriminator; no UI behavior changed. F passed after canonical-document updates. Browser/native checks are not claimed for this backend codec slice.

## Actual PostgreSQL experiment

`python -m scripts.smoke_stream_archive` creates two new owned PostgreSQL **17.5** clusters. The synthetic library contains original cited evidence, one retained CSV and one pending run, plus 30,000 deliberately high-entropy synthetic job results. These are volume fixtures, not generated financial answers. Source records/jobs/events: **6 / 30,001 / 1**.

Initial actual result: **227,707,169 archive bytes** and **311,405,637 table-content bytes**, above the old 128-MiB compressed and 256-MiB JSON ceilings. Backup 42.2729 s, validation 19.2926 s, late failed-restore rollback 42.0234 s, full restore 114.5801 s and restart/full-row comparison 7.5624 s. Measured Python peak allocations: backup **1,312,913**, validation **2,593,157**, restore **2,550,904 bytes**. These are tracemalloc allocations for this small-row scenario, not RSS, a universal maximum or a 64-GiB performance claim.

Every original row/reference/timestamp and attachment was checked; the pending job was interrupted explicitly. Injecting failure on the final event restored the target's original settings and left no inserted records/jobs. A nonempty target was refused without changes. Actual cluster restart preserved restored data and allowed the next event ID. The source fingerprints stayed unchanged; the temporary archive was removed and owned clusters stopped. Initial metrics: ignored `.local/stream-archive-1c57ac621a39/baseline.json`.

Final complete D `python -m scripts.verify database` **passed** after the last bounded-fingerprint/error-normalization edits. Its larger-file experiment produced **227,707,147 archive bytes**, **311,405,637 table-content bytes**; backup 42.5274 s, validation 31.0956 s, failed-restore rollback 35.6046 s, restore 72.6569 s and restart 6.8781 s. Python peaks: **1,310,543 / 2,591,052 / 2,550,741 bytes** for backup/validation/restore. Final metrics: ignored `.local/stream-archive-84c4dc9e355c/baseline.json`. Existing private lifecycle, comprehensive restore, 1,000-asset/24-attachment, deletion/admission and cache/admission checks all passed. Full staged review found no credentials, raw provider material, runtime binaries or test archives in the checkpoint. M9-T01g2 is complete within the file-codec scope.

## Remaining acceptance

Connect the codec to authenticated streamed upload/download, with cancellation, temporary-file/concurrency ownership and readable progress/failure states; preserve header-only credentials. Verify actual browser/native file workflows and larger transport. The public API still uses the old in-memory formats and limits in this slice. Full 10-GB/dense-five-year/native installation/upgrade/rollback acceptance is not established by these results.
