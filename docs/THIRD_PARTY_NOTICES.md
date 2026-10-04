# Import parser dependencies

Reviewed 2026-10-04 for DEC-029. This inventory covers the newly introduced import parsers; the complete application/runtime distribution inventory remains M11 work.

| Package | Pinned version | License | Purpose |
| --- | --- | --- | --- |
| [pypdf](https://pypi.org/project/pypdf/6.19.0/) | 6.19.0 | [BSD-3-Clause](licenses/pypdf.txt) | PDF text extraction; configured stream/page/form limits and no external decoder |
| [openpyxl](https://pypi.org/project/openpyxl/3.1.5/) | 3.1.5 | [MIT](licenses/openpyxl.txt) | Read-only OOXML worksheets; formulas are never evaluated |
| [defusedxml](https://pypi.org/project/defusedxml/0.7.1/) | 0.7.1 | [PSF license](licenses/defusedxml.txt) | Reject DTDs/entities/external XML during archive preflight and secure openpyxl XML parsing |
| [et-xmlfile](https://pypi.org/project/et-xmlfile/2.0.0/) | 2.0.0 | [MIT](licenses/et-xmlfile.txt) | openpyxl dependency |

License text was retained from installed official wheels (pypdf/defusedxml) and the exact-version official PyPI source distributions (openpyxl/et-xmlfile), without extracting or executing source archives. Whitespace normalization preserves all copyright/license wording. Sidecar packaging includes these notices under `licenses`. No Office, OCR, external PDF decoder, paid service or additional credential is required. Parser behavior and frozen packaging need their own acceptance evidence; package installation is not qualification.

## Local native verification resources

The local PostgreSQL 17.5 staging directory includes its original `server_license.txt` and `commandlinetools_3rd_party_licenses.txt`. Their inventory includes the PostgreSQL license, BSD/zstd/LZ4 terms, LGPL 2.1 for gettext/libiconv/pthreads, Apache 2.0 for OpenSSL, ICU/Unicode terms and MIT-style libxml2 terms. File hashes are retained in the ignored runtime manifest. No database data or proprietary administration tools are staged. This is a developer verification copy; complete redistribution obligations, security updates and the Windows runtime inventory remain M11 acceptance work.

Rust/Cargo and Microsoft C++ Build Tools are developer prerequisites installed with user authorization, not application payloads. The existing Rust dependencies now have a Cargo.lock; their complete transitive notice inventory is still required before public distribution.

The native host directly pins **dunce 1.0.5**, already present in Tauri's resolved graph, to simplify Windows verbatim paths only where ordinary spelling preserves their meaning. Hand-written prefix removal was rejected because reserved names/trailing characters can change path meaning. Its reviewed implementation performs no I/O or network access. Package metadata offers `CC0-1.0 OR MIT-0 OR Apache-2.0`; the supplied [CC0 license text](../apps/desktop/src-tauri/licenses/dunce.txt) is retained with normalized whitespace and included in native resources. No new package version or paid service is introduced; the change adds a small native path-normalization dependency, not a frontend capability.
