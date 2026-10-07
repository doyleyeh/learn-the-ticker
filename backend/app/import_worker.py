"""Single-document parser subprocess; fixed JSON over pipes, never document paths."""
import asyncio
import base64
import contextlib
import hashlib
import json
import logging
import os
from pathlib import Path
import sys

from backend.app.import_documents import ImportFailure, MAX_INPUT, ParsedDocument, parse_document
from backend.app.owned_process import close_owned, launch_owned

MAX_WIRE = MAX_INPUT * 2
MAX_OUTPUT = 2_000_000
MEMORY_LIMIT = 512 * 1024 * 1024
TIMEOUT = 20
ERRORS = frozenset({"permission_required", "input_limit", "content_limit", "table_limit", "archive_limit",
    "workbook_active_content", "workbook_external_reference", "safe_xml_unavailable", "sheet_limit",
    "unsupported_formula", "invalid_number", "unsupported_workbook_layout", "pdf_object_limit", "pdf_active_content",
    "invalid_pdf", "encrypted_pdf", "page_limit", "pdf_stream_limit", "pdf_text_unavailable", "unsupported_format",
    "empty_document", "malformed_or_unsupported_document", "worker_limit", "invalid_worker_request"})


def main():
    # POSIX CI/development boundary; Windows is limited by its suspended-start Job Object.
    if os.name != "nt":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
        resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT, TIMEOUT))
    logging.disable(logging.CRITICAL)
    try:
        wire = sys.stdin.buffer.read(MAX_WIRE + 1)
        if len(wire) > MAX_WIRE:
            raise ImportFailure("input_limit")
        request = json.loads(wire)
        if not isinstance(request, dict) or set(request) != {"format", "permission_confirmed", "data"}:
            raise ImportFailure("invalid_worker_request")
        if request["permission_confirmed"] is not True or not isinstance(request["format"], str):
            raise ImportFailure("permission_required")
        raw = base64.b64decode(request["data"], validate=True)
        # Third-party diagnostics cannot leak through either output stream.
        with contextlib.redirect_stdout(sys.stderr):
            document = parse_document(raw, request["format"], permission_confirmed=True)
        output = json.dumps({"document": document.model_dump(mode="json")}).encode("utf-8")
        if len(output) > MAX_OUTPUT:
            raise ImportFailure("content_limit")
    except ImportFailure as exc:
        code = str(exc) if str(exc) in ERRORS else "malformed_or_unsupported_document"
        output = json.dumps({"error": code}).encode()
    except (Exception, MemoryError):
        output = b'{"error":"malformed_or_unsupported_document"}'
    sys.stdout.buffer.write(output)


async def extract_document(raw, format, *, permission_confirmed=False):
    """Production parser entry; caller supplies only explicitly selected/imported bytes."""
    if permission_confirmed is not True:
        raise ImportFailure("permission_required")
    if not raw or len(raw) > MAX_INPUT:
        raise ImportFailure("input_limit")
    if format not in ("csv", "xlsx", "pdf", "html"):
        raise ImportFailure("unsupported_format")
    command = [sys.executable, "--parse-import"] if getattr(sys, "frozen", False) else [sys.executable, "-m", "backend.app.import_worker"]
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ}
    # Avoid optional BLAS thread pools when a developer environment includes numpy.
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "OPENPYXL_LXML": "False", "OPENPYXL_DEFUSEDXML": "True"})
    process = None
    try:
        process = await launch_owned(*command, cwd=Path(__file__).resolve().parents[2], env=environment,
            memory_limit=MEMORY_LIMIT, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        wire = json.dumps({"format": format, "permission_confirmed": True, "data": base64.b64encode(raw).decode("ascii")}).encode()
        async with asyncio.timeout(TIMEOUT):
            output, _ = await process.communicate(wire)
        if process.returncode != 0 or len(output) > MAX_OUTPUT:
            raise ImportFailure("worker_limit")
        value = json.loads(output)
        if isinstance(value, dict) and set(value) == {"error"} and value["error"] in ERRORS:
            raise ImportFailure(value["error"])
        if not isinstance(value, dict) or set(value) != {"document"}:
            raise ImportFailure("worker_limit")
        document = ParsedDocument.model_validate(value["document"])
        if document.format != format or document.content_hash != hashlib.sha256(raw).hexdigest():
            raise ImportFailure("worker_limit")
        return document
    except ImportFailure:
        raise
    except (OSError, ValueError, TypeError, TimeoutError):
        raise ImportFailure("worker_limit") from None
    finally:
        await close_owned(process)


if __name__ == "__main__":
    main()
