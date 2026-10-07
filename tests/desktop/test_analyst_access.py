import json

import httpx
import pytest

from backend.app.data_credentials import DataCredential
from scripts import qualify_analyst_access as access

SECRET = "synthetic-private-key"


class Store:
    def load(self, provider):
        assert provider == "alpha-vantage"
        return DataCredential(SECRET)


def success_response(request):
    body = json.loads(request.content)
    if body["method"] == "initialize":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1,
            "result": {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}}},
            headers={"Mcp-Session-Id": "synthetic-session"})
    if body["method"] == "notifications/initialized":
        return httpx.Response(202)
    return tool_response({"symbol": "TEST", "estimates": [{"date": "2027-01-01", "eps_estimate_average": "2.50"}]})


def tool_response(data, **extra):
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": 2, "result": {
        "content": [{"type": "text", "text": json.dumps(data)}], **extra}})


def run(handler):
    return access.check(live=True, symbol="TEST", store=Store(), _transport=httpx.MockTransport(handler))


def test_default_and_invalid_symbol_do_not_read_vault_or_network(monkeypatch):
    monkeypatch.setattr(access, "DataCredentialStore", lambda: pytest.fail("unexpected vault access"))
    assert access.check() == {"status": "not_run", "network": False}
    assert access.check(live=True, symbol="../TEST")["code"] == "invalid_symbol"


def test_fixed_header_auth_three_requests_and_only_explicit_estimate_tool():
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == "POST" and str(request.url) == access.ENDPOINT
        assert request.headers["X-API-Key"] == SECRET
        assert SECRET not in str(request.url) and SECRET.encode() not in request.content
        if len(calls) > 1:
            assert request.headers["Mcp-Session-Id"] == "synthetic-session"
            assert request.headers["MCP-Protocol-Version"] == "2025-03-26"
        return success_response(request)
    report = run(handler)
    assert report["status"] == "access_observed" and report["requests"] == len(calls) == 3
    assert report["estimate_rows"] == 1 and report["admitted"] is False
    assert len(report["response_sha256"]) == 64
    assert json.loads(calls[-1].content)["params"] == {
        "name": "EARNINGS_ESTIMATES", "arguments": {"symbol": "TEST", "return_full_data": True}}
    assert SECRET not in json.dumps(report) and "2.50" not in json.dumps(report)


@pytest.mark.parametrize("stage", [1, 2, 3])
@pytest.mark.parametrize("status,code", [(401, "source_access_denied"), (403, "source_access_denied"),
    (429, "source_rate_limited"), (302, "source_redirect"), (500, "source_unavailable")])
def test_denial_or_redirect_stops_at_each_stage_without_retry_or_secret_output(stage, status, code):
    calls = []
    def handler(request):
        calls.append(request)
        return (httpx.Response(status, text=SECRET, headers={"Location": "https://other.example/"})
                if len(calls) == stage else success_response(request))
    report = run(handler)
    assert report["code"] == code and report["retried"] is False
    assert len(calls) == stage and SECRET not in json.dumps(report)


@pytest.mark.parametrize("data,code", [
    ({"Information": "Use premium subscription " + SECRET}, "source_entitlement_required"),
    ({"Note": "API rate limit reached"}, "source_rate_limited"),
    ({"error": {"code": "invalid_key"}}, "source_access_denied"),
    ({"symbol": "OTHER", "estimates": [{}]}, "response_unqualified"),
    ({"symbol": "TEST", "estimates": []}, "response_unqualified"),
    ({"symbol": "TEST", "estimates": "not rows"}, "response_unqualified"),
    ({"symbol": "TEST", "estimates": [{}] * 1001}, "response_unqualified"),
    ({"symbol": "TEST", "estimates": ["not a row"]}, "response_unqualified"),
    ({"data_url": "https://other.example/", "max_tokens_exceeded": True}, "response_unqualified"),
])
def test_http_200_errors_unknown_schema_and_previews_never_qualify(data, code):
    calls = []
    def handler(request):
        calls.append(request)
        return tool_response(data) if len(calls) == 3 else success_response(request)
    report = run(handler)
    # Even an otherwise classifiable error must not retain or report an echoed key.
    assert report["code"] == ("credential_echo" if SECRET in json.dumps(data) else code)
    assert len(calls) == 3 and report["admitted"] is False
    assert SECRET not in json.dumps(report) and "response_sha256" not in report


@pytest.mark.parametrize("response", [
    httpx.Response(200, json={"jsonrpc": "2.0", "id": 4, "result": {}}),
    httpx.Response(200, json={"jsonrpc": "2.0", "id": True, "result": {}}),
    httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "unknown"}}),
    httpx.Response(200, json={"method": "roots/list", "id": 1}),
    httpx.Response(200, text="event: message\ndata: {}", headers={"Content-Type": "text/event-stream"}),
])
def test_unqualified_protocol_never_reaches_data_tool(response):
    calls = []
    def handler(request):
        calls.append(request)
        return response
    assert run(handler)["code"] == "protocol_unqualified"
    assert len(calls) == 1


def test_limits_and_raw_exception_redaction():
    for response, code in [(httpx.Response(200, content=b"x" * 65537,
            headers={"Content-Type": "application/json"}), "response_size"),
            (httpx.Response(200, content=b'{"jsonrpc":"2.0","jsonrpc":"2.0"}',
            headers={"Content-Type": "application/json"}), "source_unavailable")]:
        assert run(lambda request: response)["code"] == code
    def failed(request):
        raise httpx.ReadError(SECRET, request=request)
    report = run(failed)
    assert report["code"] == "source_unavailable" and SECRET not in json.dumps(report)


def test_missing_credential_never_requests():
    class Missing:
        def load(self, provider):
            return None
    report = access.check(live=True, symbol="TEST", store=Missing(),
        _transport=httpx.MockTransport(lambda _: pytest.fail("unexpected network")))
    assert report["code"] == "credential_missing"


def test_elapsed_deadline_stops_a_trickling_response(monkeypatch):
    ticks = iter([0, 1, 46])
    monkeypatch.setattr(access.time, "monotonic", lambda: next(ticks))
    calls = []
    def handler(request):
        calls.append(request)
        return success_response(request)
    assert run(handler)["code"] == "source_unavailable"
    assert len(calls) == 1


def test_plain_text_mcp_error_is_classified_without_reporting_it():
    def handler(request):
        if json.loads(request.content)["method"] != "tools/call":
            return success_response(request)
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 2, "result": {
            "isError": True, "content": [{"type": "text", "text": "Premium subscription required"}]}})
    assert run(handler)["code"] == "source_entitlement_required"
