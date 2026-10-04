# Bounded import parser checkpoint

Date: 2026-10-04. Scope: M3-T01a under DEC-029; M3 remains incomplete. These are synthetic local documents, not live retrieval or native file-selection acceptance.

## Implemented boundary

Production parser entry uses an owned subprocess for PDF, UTF-8/BOM UTF-16 CSV, XLSX and HTML. Input is capped at 5 MiB, expansion at 20 MiB with 4 MiB per archive entry/PDF stream, PDF pages at 100, worksheets at 20, rows at 2,000, columns at 100, cells at 10,000 and content at 200,000 characters. Output JSON is at most 2 MB. Windows workers start suspended and receive per-process/aggregate 512 MiB committed-memory limits before resuming; a 20-second deadline and cancellation close the process tree. Existing provider ownership defaults remain unchanged. POSIX CI/development uses resource limits; this is not Linux release qualification.

Original bytes receive a SHA-256; PDF pages and table cells retain locators. Workbook decimal XML is preserved rather than rounded through floating point, and original serial values/formats remain alongside parsed dates. Formulas remain inert text; cached results do not become calculations. Imports are explicitly unverified and cannot create facts or chart inputs. The parser does not persist attachments or call a provider.

Reject archive traversal/duplicates/expansion, XML DTDs/entities, external workbook relationships/macros, active PDF actions/attachments, encrypted/text-unavailable PDFs and oversized/malformed material. No external PDF decoder, Office or OCR is invoked. The worker receives only submitted bytes/format/permission, not document paths, database credentials, provider environment or SEC contact. Strict JSON and fixed error codes exclude raw parser diagnostics. This does not claim an OS network sandbox; containment combines reviewed non-executing parsers, process ownership and resource limits.

Pinned dependencies and retained license texts are in [notices](../THIRD_PARTY_NOTICES.md). The sidecar includes those license files and a narrow --parse-import entry separate from database startup. No SQL or archive migration, frontend route, provider capability or tool-permission change occurred.

## Verification and repairs

- Forty new import tests cover all formats, UTF-8/UTF-16, literal decimals/cell/page references, inert formulas, malformed/expanded/active documents, permission before launch, actual owned workers, fixed failures, credential-free environment, deadline/cancellation and real Windows memory allocation refusal. Existing process-tree ownership/parent-crash tests still pass.
- Initial test output exposed excessively long parameter IDs on Windows; explicit short IDs fixed the test harness. XLSX success cases then identified the OOXML root `.rels` part as a valid dotfile lacking a normal suffix. The parser now recognizes that standard part while retaining traversal, external-link and macro rejection. The focused parser/ownership suite passed 44 tests, followed by 47 parser/verification tests after packaged-smoke integration.
- Q: `powershell -ExecutionPolicy Bypass -File scripts/run_quality_gate.ps1` passed **1,120 Python/seven frontend tests**, Ruff/ESLint, contract drift, docs/static checks, TypeScript and Vite build. Existing Starlette/httpx deprecation remains a warning. `pip check` reported no broken dependencies.
- D: `.venv/Scripts/python.exe -m scripts.verify database` passed actual separate PostgreSQL lifecycle, atomic rollback/commit, whole-library restore/restart, original conversation citation reuse, interruption handling and non-empty-target rejection. No production library was used.
- Packaged: `.venv/Scripts/python.exe -m scripts.verify packaged` built the Windows x64 sidecar, passed authenticated API/private PostgreSQL startup and clean shutdown, then parsed four synthetic formats through actual frozen worker processes. PyInstaller emitted optional-module/excluded-keyring-test warnings; the exercised database and parser paths passed. No installer or clean-machine claim follows from this result.

Microsoft's [extended Job Object limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information) and [limit flags](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information) were reviewed, and a real child allocation exceeding its limit was refused without affecting unrelated processes. Permission and library data are not inferred from successful parsing.

**M3-T01a is complete.** M3-T01b still requires authenticated URL/file preview, source rights/private-address checks, file selection and browser/native acceptance. M3-T02 must extend and actually restore retained permitted attachments before durable import storage is enabled. No imported content is exposed or stored by this parser-only checkpoint.

Final staged review found trailing whitespace in the upstream defusedxml license. Its copyright/license wording was preserved while normalizing whitespace in a follow-up checkpoint. The parser/runtime Q/D/packaged results above are unchanged; final staged F/whitespace checks are required for that correction.
