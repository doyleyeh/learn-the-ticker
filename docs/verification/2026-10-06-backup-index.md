# Shared disk-index archive validation

Date: 2026-10-06. Scope: M9-T01g1 and DEC-062; foundation for large archives, not completion of M9-T01g.

## Behavior

The legacy format-1/2 validator now delegates to one index-based validator. It preserves typed normalization, identity hashes, claim/source support, original context references, attachment rights/checksums/capacity, comparison/report/term/import interpretation relationships and job/event rules. A bundle lookup loads individual originals without retaining all bodies. Legacy callers still enforce duplicate IDs before validation; scratch-table primary keys enforce the same rule for the new disk path.

`backup_index.indexed_snapshot` uses one-row SQLAlchemy server cursors over records/jobs/events in one PostgreSQL repeatable-read transaction. A fresh owned temporary directory holds a standard-library SQLite scratch index with fixed application-owned SQL and bound row values. It never opens an archive-supplied database. Page cache is configured to 2 MiB; Python working memory still depends on individual row size and model validation. Connections and scratch directories close/remove on success, failure and context exit; source data is unchanged.

This index is not yet wired into the user-facing ZIP serializer, upload or download routes. Existing 128-MiB compressed / 256-MiB content limits and whole-body transport remain. Streamed serialization, versioned compatibility, large-file bounds/disk exhaustion, actual larger restore/restart and browser/native transfer are the next archive slice. No new dependency, SQL migration, archive format or installer is introduced.

## Repair and verification

Initial focused legacy checks passed **67 tests**; the new disk-index scenarios increased this to **76**. Initial Q then exposed an equal-timestamp ordering defect in the prior term-deletion round trip: identical timestamps had no tie-breaker, so restore insertion order could change the displayed order. Added a test that deliberately sets all explanation timestamps equal; it failed before the repair. `Database.list` now orders by descending update time, then immutable record ID. The original failing assertion is preserved.

Final targeted command: `.venv/Scripts/python.exe -m pytest tests/desktop/test_backup_index.py tests/desktop/test_backup.py tests/desktop/test_retained_imports.py tests/desktop/test_term_deletion.py -q`: **83 passed**. Ten new cases cover exact row agreement, all three duplicate-ID kinds, missing originals, changed identity, credential/raw-event rejection, scratch cleanup on validation interruption, and deterministic restored list order.

Repaired Q (`python -m scripts.verify milestone`) passed **2,084 Python / 94 frontend tests**, lint, contracts, local documentation, static evaluations, TypeScript and production build. Existing Starlette/httpx deprecation remains. Actual full D passed both the initial disk-index implementation and the final rerun after the ordering repair: service startup, database/retention, rich restore, scale, deletion and protected-cache lifecycles all passed. Final scale evidence is `.local/library-scale-05a08e050df4/baseline.json`; its index stage took 12.862 seconds. Final code/diff review retained all original checks and found no archive-format, source-rights, credential or production-provider changes.

The initial actual PostgreSQL 17.5 scale run staged/validated all **3,325 records / 2,000 jobs / 2,000 events**, including 24 parser-produced attachments totaling **62,941,114 bytes**. It compared every canonical payload/reference/timestamp and left the source unchanged. Index collection/validation/comparison took **12.7178 seconds** and tracemalloc reported **24,464,326 bytes** peak Python allocations for that stage. This is not process RSS, a latency threshold, an end-to-end archive-memory ceiling or a 10-GB qualification. The same run passed exact archive restore, late-failure rollback, nonempty-target preservation and restart. Original baseline dates/measurements remain unchanged in their own evidence.

Ignored logs: `.local/m9-backup-index-targeted.log`, `.local/m9-backup-index-q.log` (initial failure), `.local/m9-backup-index-q-repair.log`, `.local/m9-backup-index-d.log`, `.local/m9-backup-index-d-final.log`; initial scale details `.local/library-scale-bc8f24a7918d/baseline.json`. No live provider, user library, native installer or browser transfer was exercised by this slice.
