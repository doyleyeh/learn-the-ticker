"""Authenticated, bounded preview transport. Request content is never logged or stored."""
import asyncio
import json

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from backend.app.import_documents import MAX_INPUT, ImportFailure
from backend.app.import_previews import import_message


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
