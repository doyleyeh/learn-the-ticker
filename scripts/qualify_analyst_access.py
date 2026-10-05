"""Explicit Alpha Vantage estimate access check; no admission, model call or archive."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
import re
import time

import httpx

from backend.app.data_credentials import DataCredentialStore
from backend.app.market_history import MarketDataError, _json
from backend.app.market_transport import status_error

ENDPOINT = "https://mcp.alphavantage.co/mcp"
PROTOCOLS = frozenset({"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"})
MAX_RESPONSE = 1024 * 1024
CODES = frozenset({"invalid_symbol", "credential_missing", "source_access_denied", "source_rate_limited",
    "source_unavailable", "source_redirect", "source_not_found", "response_size", "protocol_unqualified",
    "response_unqualified", "source_entitlement_required", "credential_echo"})


def payload_error(value):
    """Inspect privately; only a fixed code can cross the reporting boundary."""
    if not isinstance(value, dict):
        return None
    errors = [value[k] for k in ("error", "Error Message", "Information", "Note") if k in value]
    if not errors:
        return None
    message = json.dumps(errors, default=str).lower()
    if any(word in message for word in ("premium", "subscribe", "subscription required", "entitlement")):
        return "source_entitlement_required"
    if any(word in message for word in ("rate limit", "rate_limit", "frequency", "quota", "calls per")):
        return "source_rate_limited"
    if any(word in message for word in ("api key", "apikey", "unauthorized", "forbidden", "invalid_key")):
        return "source_access_denied"
    return "source_unavailable"


def probe(symbol, credential, *, _transport=None):
    """One fixed data tool, no discovery, retries, redirects, resources or callbacks."""
    requests = 0
    deadline = time.monotonic() + 45
    with httpx.Client(verify=True, trust_env=False, follow_redirects=False, timeout=15, transport=_transport,
            headers={"X-API-Key": credential.api_key, "User-Agent": "LearnTheTicker/0.2",
                     "Accept": "application/json, text/event-stream"}) as client:
        def post(body, *, limit=MAX_RESPONSE, notification=False):
            nonlocal requests
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MarketDataError("source_unavailable")
            requests += 1
            with client.stream("POST", ENDPOINT, json=body, timeout=min(15, remaining)) as response:
                if notification and response.status_code in (200, 202, 204):
                    return None, None
                error = status_error(response.status_code)
                if error:
                    raise MarketDataError(error)
                if response.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
                    raise MarketDataError("protocol_unqualified")
                raw = bytearray()
                for chunk in response.iter_bytes(chunk_size=8192):
                    if time.monotonic() >= deadline:
                        raise MarketDataError("source_unavailable")
                    raw.extend(chunk)
                    if len(raw) > limit:
                        raise MarketDataError("response_size")
                if credential.api_key.encode() in raw:
                    raise MarketDataError("credential_echo")
                session = response.headers.get("mcp-session-id")
                if session:
                    if not re.fullmatch(r"[A-Za-z0-9._~-]{1,256}", session):
                        raise MarketDataError("protocol_unqualified")
                    client.headers["Mcp-Session-Id"] = session
                value = _json(bytes(raw))
                if (not isinstance(value, dict) or value.get("jsonrpc") != "2.0"
                        or type(value.get("id")) is not int or value["id"] != body["id"]):
                    raise MarketDataError("protocol_unqualified")
                if error := payload_error(value):
                    raise MarketDataError(error)
                if not isinstance(value.get("result"), dict):
                    raise MarketDataError("protocol_unqualified")
                return value["result"], bytes(raw)

        init, _ = post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "LearnTheTicker-access-check", "version": "0.2"}}}, limit=65536)
        if init.get("protocolVersion") not in PROTOCOLS:
            raise MarketDataError("protocol_unqualified")
        client.headers["MCP-Protocol-Version"] = init["protocolVersion"]
        post({"jsonrpc": "2.0", "method": "notifications/initialized"}, notification=True)
        result, raw = post({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "EARNINGS_ESTIMATES", "arguments": {"symbol": symbol, "return_full_data": True}}})
        # Explicit full data avoids the server's large-response object-storage preview.
        # Never follow a resource/data URL or accept generated text as estimate data.
        content = result.get("content")
        if (not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict)
                or content[0].get("type") != "text" or not isinstance(content[0].get("text"), str)):
            raise MarketDataError("response_unqualified")
        if result.get("isError", False) is not False:
            raise MarketDataError(payload_error({"error": content[0]["text"]}) or "source_unavailable")
        data = _json(content[0]["text"].encode())
        if error := payload_error(data):
            raise MarketDataError(error)
        if not isinstance(data, dict) or data.get("symbol") != symbol:
            raise MarketDataError("response_unqualified")
        arrays = [data[key] for key in ("estimates", "annualEstimates", "quarterlyEstimates") if key in data]
        if (not arrays or any(not isinstance(rows, list) or len(rows) > 1000
                or any(not isinstance(row, dict) for row in rows) for rows in arrays)):
            raise MarketDataError("response_unqualified")
        count = sum(len(rows) for rows in arrays)
        if not count:
            raise MarketDataError("response_unqualified")
        return {"status": "access_observed", "requests": requests, "estimate_rows": count,
                "response_sha256": hashlib.sha256(raw).hexdigest(), "admitted": False}


def check(*, live=False, symbol="", store=None, _transport=None):
    if not live:
        return {"status": "not_run", "network": False}
    try:
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,29}", symbol):
            raise MarketDataError("invalid_symbol")
        credential = (store or DataCredentialStore()).load("alpha-vantage")
        if credential is None:
            raise MarketDataError("credential_missing")
        report = probe(symbol, credential, _transport=_transport)
    except Exception as exc:
        code = str(exc) if isinstance(exc, MarketDataError) and str(exc) in CODES else "source_unavailable"
        report = {"status": "blocked", "code": code, "retried": False, "admitted": False}
    return {**report, "checked_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Existing-key estimate access only; no identity, units, date, retention, library or model qualification."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--symbol", default="")
    args = parser.parse_args()
    # Suppress installed-library log configuration; reporting below is allowlisted.
    logging.disable(logging.CRITICAL)
    report = check(live=args.live, symbol=args.symbol)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "access_observed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
