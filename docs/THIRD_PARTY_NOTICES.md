# Import parser dependencies

Reviewed 2026-10-04 for DEC-029. This inventory covers the newly introduced import parsers; the complete application/runtime distribution inventory remains M11 work.

| Package | Pinned version | License | Purpose |
| --- | --- | --- | --- |
| [pypdf](https://pypi.org/project/pypdf/6.19.0/) | 6.19.0 | [BSD-3-Clause](licenses/pypdf.txt) | PDF text extraction; configured stream/page/form limits and no external decoder |
| [openpyxl](https://pypi.org/project/openpyxl/3.1.5/) | 3.1.5 | [MIT](licenses/openpyxl.txt) | Read-only OOXML worksheets; formulas are never evaluated |
| [defusedxml](https://pypi.org/project/defusedxml/0.7.1/) | 0.7.1 | [PSF license](licenses/defusedxml.txt) | Reject DTDs/entities/external XML during archive preflight and secure openpyxl XML parsing |
| [et-xmlfile](https://pypi.org/project/et-xmlfile/2.0.0/) | 2.0.0 | [MIT](licenses/et-xmlfile.txt) | openpyxl dependency |

License text was retained from installed official wheels (pypdf/defusedxml) and the exact-version official PyPI source distributions (openpyxl/et-xmlfile), without extracting or executing source archives. Whitespace normalization preserves all copyright/license wording. Sidecar packaging includes these notices under `licenses`. No Office, OCR, external PDF decoder, paid service or additional credential is required. Parser behavior and frozen packaging need their own acceptance evidence; package installation is not qualification.
