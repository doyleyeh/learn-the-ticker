"""Authenticated, bounded preview and explicit retention transport; no request logging."""
import asyncio
import json
from urllib.parse import unquote

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from backend.app.import_documents import MAX_INPUT, ImportFailure
from backend.app.import_previews import import_message
from backend.app.import_storage import ImportStorage, RetainMetadata, RetainURL


async def preview_body(request, limit):
    data = bytearray()
    try:
        async with asyncio.timeout(20):
            async for part in request.stream():
                if len(data) + len(part) > limit:
                    raise ImportFailure("request_limit")
                data.extend(part)
    except TimeoutError:
        raise ImportFailure("request_limit") from None
    return bytes(data)


async def while_connected(request, operation):
    async def disconnected():
        while (await request.receive())["type"] != "http.disconnect":
            pass
    work = asyncio.create_task(operation())
    disconnect = asyncio.create_task(disconnected())
    try:
        done, _ = await asyncio.wait((work, disconnect), return_when=asyncio.FIRST_COMPLETED)
        if disconnect in done:
            raise HTTPException(499, "Preview cancelled")
        if work.cancelled():
            raise HTTPException(409, "Preview cancelled. Check online permissions before retrying.")
        return await work
    finally:
        for task in (work, disconnect):
            if not task.done():
                task.cancel()
        await asyncio.gather(work, disconnect, return_exceptions=True)


def mount_import_routes(app, previews):
    storage = ImportStorage(previews)
    app.state.import_storage = storage

    @app.get("/api/imports/retained")
    async def retained_list():
        try:
            return JSONResponse([item.model_dump(mode="json") for item in storage.list()], headers={"Cache-Control": "no-store"})
        except ImportFailure as exc:
            raise HTTPException(400, import_message(exc)) from None

    @app.get("/api/imports/retained/{identifier}")
    async def retained_view(identifier: str, request: Request):
        try:
            # Consume the empty GET body before the disconnect watcher takes ownership
            # of receive; immediate queue failures must not strand middleware reads.
            await preview_body(request, 0)
            result = await while_connected(request, lambda: storage.view(identifier))
            return JSONResponse(result.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
        except ImportFailure as exc:
            raise HTTPException(400, import_message(exc)) from None

    @app.post("/api/imports/retain/file")
    async def file_retention(request: Request):
        try:
            if request.query_params.get("permission_confirmed") != "true":
                raise ImportFailure("permission_required")
            format = request.query_params.get("format")
            if format not in ("pdf", "csv", "xlsx"):
                raise ImportFailure("unsupported_format")
            encoded = request.headers.get("X-Import-Metadata", "")
            try:
                if len(encoded) > 4096:
                    raise ValueError()
                metadata = RetainMetadata.model_validate_json(unquote(encoded, errors="strict"))
            except (ValueError, RecursionError):
                raise ImportFailure("storage_permission_required") from None
            raw = await preview_body(request, MAX_INPUT)
            result = await while_connected(request, lambda: storage.file(raw, format, metadata))
            return JSONResponse(result.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
        except ImportFailure as exc:
            raise HTTPException(400, import_message(exc)) from None

    @app.post("/api/imports/retain/url")
    async def url_retention(request: Request):
        try:
            raw = await preview_body(request, 8192)
            try:
                metadata = RetainURL.model_validate_json(raw)
            except (ValueError, RecursionError):
                raise ImportFailure("storage_permission_required") from None
            result = await while_connected(request, lambda: storage.url(metadata))
            return JSONResponse(result.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
        except ImportFailure as exc:
            raise HTTPException(400, import_message(exc)) from None

    @app.post("/api/imports/preview/file")
    async def file_preview(request: Request):
        try:
            # Confirm permission and format before consuming the selected bytes.
            if request.query_params.get("permission_confirmed") != "true":
                raise ImportFailure("permission_required")
            format = request.query_params.get("format")
            if format not in ("pdf", "csv", "xlsx"):
                raise ImportFailure("unsupported_format")
            raw = await preview_body(request, MAX_INPUT)
            preview = await while_connected(request, lambda: previews.file(raw, format, True))
            return JSONResponse(preview.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
        except ImportFailure as exc:
            raise HTTPException(400, import_message(exc)) from None

    @app.post("/api/imports/preview/url")
    async def url_preview(request: Request):
        try:
            raw = await preview_body(request, 4096)
            try:
                value = json.loads(raw)
                if not isinstance(value, dict) or set(value) != {"url"} or not isinstance(value["url"], str):
                    raise ValueError()
            except (ValueError, UnicodeError, RecursionError):
                raise ImportFailure("invalid_url") from None
            preview = await while_connected(request, lambda: previews.url(value["url"]))
            return JSONResponse(preview.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
        except ImportFailure as exc:
            raise HTTPException(400, import_message(exc)) from None
