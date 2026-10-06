# Conversation retention under concurrent admission

Date: 2026-10-06 (Asia/Taipei). Scope: M9-T01b/P-043 retention; M9 remains incomplete.

## Reproduction and repair

Inspection found that expiry read all jobs before obtaining conversation row locks. A new question could hold a conversation lock, commit its job after that earlier job snapshot, and then lose its conversation to the waiting expiry operation. Question admission also left the idle timestamp unchanged until a successful answer. A newly attempted question could therefore be treated as 180-day-idle after failure or cancellation.

Added a coordinated two-thread PostgreSQL scenario to the existing database smoke. Queue admission pauses while holding the conversation row lock; expiry reaches that lock concurrently; admission then commits. The unchanged implementation reproducibly failed with `Retention deleted a concurrently admitted conversation` in `.local/m9-retention-reproduction.log`. This was an actual isolated PostgreSQL failure, not an inferred SQLite result.

The repair renews `last_activity` atomically with locked question admission and job creation. Failed admission rolls the timestamp back. Expiry now acquires conversation locks before reading job metadata, preserving the committed question and refreshed activity. It reads only job IDs/status/conversation IDs rather than materializing unrelated requests/results. Old transcript/job/event deletion remains transactional and never deletes evidence bundles.

## Verification

- **36 targeted tests passed**: storage, conversation context and archive scenarios. Newly admitted activity survives failed/cancelled/interrupted answers until more than 180 idle days; the exact boundary remains retained. Failed admission and failed retention roll back; source versions and saved references persist.
- The first targeted run found six existing archive assertions comparing against the pre-admission conversation timestamp. Updated their expected snapshot after successful admission, retaining their missing/foreign context tampering assertions and full restored-record equality. Stored renewal time uses canonical UTC serialization; no validation or retention boundary was relaxed.
- Actual PostgreSQL queue-first ordering preserves the conversation and queued job. The reverse ordering lets expiry remove the idle conversation first, then rejects admission without creating an orphan job. Thread events coordinate the lock ordering; there are no timing sleeps or retry loops.
- A real PostgreSQL restart preserves the surviving conversation, idle timestamp, saved version, current asset and job; deleted conversation/job remain absent. The resulting full archive validates all references.
- F and Q passed: **2,031 Python tests, 94 frontend tests**, lint/contracts/static evaluations/TypeScript/build. Existing Starlette/httpx deprecation warning remains.
- Full D passed, including authenticated service lifecycle, transaction recovery, rich financial/comparison/report/import restore, and the 1,000-asset/24-attachment rollback/restore/restart baseline. Later scale run is `.local/library-scale-fbaaf35e5372/baseline.json`; the original baseline retains its original timings.

Ignored logs: `.local/m9-retention-targeted.log`, `.local/m9-retention-repair.log`, `.local/m9-retention-f.log`, `.local/m9-retention-q.log`, `.local/m9-retention-d.log`. Final documentation F is part of the checkpoint.

Fresh review confirms P-043's idle renewal, bookmark/active-job protection, atomic deletion and immutable evidence requirements for this slice. No provider calls, UI, SQL migration, archive format, cache capacity or native artifacts changed. Explicit saved-item deletion controls, protected cache eviction, larger archives and native lifecycle remain separate M9 work. Gemini account qualification remains blocked and Claude remains owner-paused.
