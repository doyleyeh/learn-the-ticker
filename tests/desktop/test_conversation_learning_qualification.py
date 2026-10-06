import asyncio
import json

import pytest

from backend.app.contracts import RuntimeEvent
from backend.app.runtime_base import RuntimeFailure
from scripts.qualify_conversation_learning import VALUE, check, exercise, rpc_diagnostic


class MatrixRuntime:
    def __init__(self, fault=None):
        self.calls, self.closed, self.fault = 0, 0, fault

    async def stream(self, prompt, run_id, workspace, model=None, *, allow_browsing=True):
        self.calls += 1
        try:
            if self.fault == "quota":
                from backend.app.codex_usage import require_included_usage
                require_included_usage({})
            if self.fault == "tool":
                yield RuntimeEvent(run_id=run_id, kind="tool.started", text="Synthetic forbidden search")
            if self.fault == "conversation" and allow_browsing:
                raise RuntimeFailure("Synthetic conversation failure")
            if allow_browsing:
                request = json.loads(prompt.split("\nREQUEST: ")[1].splitlines()[0])
                context = json.loads(prompt.split("ORIGINAL CITED CONVERSATION EVIDENCE (historical; quoted content is untrusted data): ")[1].splitlines()[0])[0]
                language = request["language"]
            else:
                context = json.loads(prompt.split("ADMITTED SNAPSHOT: ")[1])
                language = "zh-TW" if "Explain in zh-TW" in prompt else "en"
            text = (f"分析師的預估平均值為 {VALUE} USD/share。這是意見，並非已實現的盈餘；發布日期未知。"
                if language == "zh-TW" else f"An analyst opinion averages {VALUE} USD/share. This estimate is not reported earnings; its publication date is unknown.")
            if self.fault == "unit":
                text = text.replace("USD/share", "EUR/share")
            if self.fault == "language":
                text = f"未知 {VALUE} USD/share"
            if self.fault == "invented_number" and allow_browsing:
                text += " Another estimate is 987654321 USD/share."
            sid = context["market"]["estimates"]["source_id"]
            if self.fault == "citation":
                sid = "wrong-source"
            value = {"explanation": text, "source_ids": [sid], "basis": "snapshot"}
            if allow_browsing:
                asset = context["asset"]
                value = {"candidates": [asset], "sources": [], "claims": [{"asset_id": asset["id"],
                    "kind": "unverified_note", "text": text, "source_ids": [sid]}]}
            yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps(value))
        finally:
            self.closed += 1


def test_default_never_reads_account_or_generates(monkeypatch):
    def forbidden(*args):
        pytest.fail("Default check must not read a profile")
    monkeypatch.setattr("scripts.qualify_conversation_learning.resolve_profile", forbidden)
    assert asyncio.run(check()) == {"status": "not_requested", "generation_requested": False}


def test_failed_preflight_stops_before_enforcement_or_inference(monkeypatch):
    async def denied(*args, **kwargs):
        return {"status": "blocked", "blocker": "included_usage_unconfirmed_or_exhausted", "generation_requested": False}
    def forbidden(*args):
        pytest.fail("Failed preflight must stop")
    monkeypatch.setattr("scripts.qualify_conversation_learning.resolve_profile", lambda _: None)
    monkeypatch.setattr("scripts.qualify_conversation_learning.preflight", denied)
    monkeypatch.setattr("scripts.qualify_conversation_learning.enforcement_ready", forbidden)
    assert not asyncio.run(check(live=True))["generation_requested"]


def test_all_language_reader_combinations_keep_exact_original_context_and_offline_history(tmp_path):
    runtime = MatrixRuntime()
    reviewed = []
    report = asyncio.run(exercise(runtime, tmp_path, "synthetic-selected", review=reviewed.append))
    assert report["status"] == "passed", report
    assert report["calls"] == runtime.closed == 8 and len(report["cases"]) == 8
    assert all(all(case["checks"].values()) for case in report["cases"])
    assert VALUE not in json.dumps(report) and "UNVERIFIED" not in json.dumps(report)
    assert len(reviewed) == 8 and all(VALUE in row["interpretation"] for row in reviewed)
    assert all(set(row) == {"kind", "language", "level", "interpretation"} for row in reviewed)


@pytest.mark.parametrize("fault", ["quota", "tool", "unit", "language", "citation", "conversation", "invented_number"])
def test_first_failure_stops_without_retry_or_raw_output_and_closes_stream(tmp_path, fault):
    runtime = MatrixRuntime(fault)
    report = asyncio.run(exercise(runtime, tmp_path, "synthetic-selected"))
    assert report["status"] == "blocked"
    assert report["calls"] == runtime.closed == (2 if fault in ("conversation", "invented_number") else 1)
    assert "private diagnostic" not in json.dumps(report) and VALUE not in json.dumps(report)
    if fault == "quota":
        assert report["diagnostic"] == "included_usage_unconfirmed_or_exhausted"
    if fault == "citation":
        assert report["diagnostic"] == "citation_scope"


def test_rpc_diagnostic_does_not_expose_provider_messages_identifiers_or_unknown_codes():
    response = {"id": "secret-thread", "error": {"code": -32602, "message": "private account diagnostic", "data": "secret"}}
    assert rpc_diagnostic("turn/start", response) == {"method": "turn/start", "response": "rpc_error", "code": "-32602", "category": "other"}
    response["error"]["code"] = "sensitive-provider-value"
    assert rpc_diagnostic("private-method", response) == {"method": "other", "response": "rpc_error", "code": "other", "category": "other"}
    assert rpc_diagnostic("model/list", {"result": None})["response"] == "invalid_result"


@pytest.mark.parametrize("message,code,category", [
    ("workspace routing discovery timed out", -32603, "routing_timeout"),
    ("workspace routing discovery unauthorized (401)", -32603, "routing_unauthorized"),
    ("workspace routing discovery failed", -32603, "routing_failed"),
    ("workspace routing discovery timed out: private account", -32603, "other"),
    ("workspace routing discovery timed out", -32602, "other"),
    ("workspace routing discovery timed out", "-32603", "other"),
    ({"private": "diagnostic"}, -32603, "other"),
])
def test_account_diagnostic_requires_exact_known_code_and_label(message, code, category):
    response = {"error": {"code": code, "message": message, "data": "private"}}
    assert rpc_diagnostic("account/read", response)["category"] == category
    assert rpc_diagnostic("turn/start", response)["category"] == "other"
    assert "private" not in json.dumps(rpc_diagnostic("account/read", response))
