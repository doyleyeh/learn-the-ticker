"""Subscription-only research through the application's dedicated Codex profile."""
import asyncio
from pathlib import Path

from backend.app.codex_rpc import CodexRPC
from backend.app.codex_approvals import CodexApprovals, identifier
from backend.app.contracts import RuntimeEvent, RuntimeModelCatalog
from backend.app.codex_models import read_models, select_model
from backend.app.codex_usage import require_included_usage
from backend.app.codex_policy import require_execution_sandbox
from backend.app.runtime_base import AIRuntime, RuntimeFailure
from backend.app.runtime_policy import apply_qualification


def subscription_account(value: dict) -> bool:
    account = value.get("account")
    # External tokens are not accepted: this app uses provider-managed authentication.
    return isinstance(account, dict) and account.get("type") == "chatgpt"


class CodexRuntime(AIRuntime):
    provider = "codex"

    def __init__(self, profile: Path | None = None):
        self.profile = profile
        self.approvals = None

    async def check(self):
        result = await super().check()
        if not result.installed or result.qualification == "unqualified" or not self.profile:
            return result
        rpc = CodexRPC(self.profile, self.profile / "status", allow_browsing=False)
        try:
            await rpc.open()
            account = await rpc.request("account/read", {"refreshToken": False})
            result.authentication = "authenticated" if subscription_account(account) else ("required" if account.get("account") is None else "unsupported")
            apply_qualification(result)
        except (RuntimeFailure, OSError):
            result.authentication = "unknown"
            result.reason = "Codex connection check failed. Check runtime compatibility and reconnect."
        finally:
            await rpc.close()
        return result

    async def models(self) -> RuntimeModelCatalog:
        capabilities = await super().check()
        result = RuntimeModelCatalog(provider=self.provider)
        if not self.profile or not capabilities.installed or capabilities.qualification == "unqualified":
            result.message = capabilities.reason or "Connect a compatible Codex subscription first."
            return result
        rpc = CodexRPC(self.profile, self.profile / "catalog", allow_browsing=False)
        try:
            await rpc.open()
            account = await rpc.request("account/read", {"refreshToken": False})
            if not subscription_account(account):
                result.status = "authentication_required" if account.get("account") is None else "unavailable"
                result.message = "Connect the dedicated ChatGPT subscription. API-key and external-token authentication are unsupported."
                return result
            result.models = await read_models(rpc)
            result.status = "available"
            result.message = "Provider catalog only. Model access, quota and research compatibility must still be checked when a request runs."
            return result
        except (RuntimeFailure, OSError):
            result.message = "Model discovery failed. Reconnect or refresh; no model or provider was changed."
            return result
        finally:
            await rpc.close()

    async def stream(self, prompt, run_id, workspace, model=None, *, allow_browsing=True):
        await self.require_generation(allow_browsing=allow_browsing)
        profile = self.profile or workspace.parent.parent / "connections" / "codex"
        rpc = CodexRPC(profile, workspace, allow_browsing=allow_browsing)
        thread_id, turn_id, completed = None, None, False
        try:
            async with asyncio.timeout(180):
                await rpc.open()
                if not subscription_account(await rpc.request("account/read", {"refreshToken": False})):
                    raise RuntimeFailure("Sign in to ChatGPT / Codex in Connections. API-key billing is not enabled.")
                selected = select_model(await read_models(rpc), model)
                thread_id = await rpc.start_thread(selected)
                await require_execution_sandbox(rpc)
                require_included_usage(await rpc.request("account/rateLimits/read", {}))
                response = await rpc.request("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": prompt}]})
                turn = response.get("turn")
                if not isinstance(turn, dict) or not identifier(turn.get("id")):
                    raise RuntimeFailure("Codex did not identify the active turn.")
                turn_id = turn["id"]
                approvals = CodexApprovals(rpc, self.approvals, run_id, thread_id, turn_id)
                while True:
                    raw = await rpc.event()
                    method, params = raw.get("method"), raw.get("params", {})
                    if not isinstance(params, dict):
                        raise RuntimeFailure("Codex returned invalid event parameters.")
                    if "id" in raw:
                        # Term explanations have no permission to request additional tools.
                        if not allow_browsing:
                            raise RuntimeFailure("Cached-evidence explanations cannot request expanded access.")
                        yield RuntimeEvent(run_id=run_id, kind="approval.required", text="Review requested access. Research is waiting; no permission has been granted.")
                        await approvals.handle(raw)
                        continue
                    if method in ("item/agentMessage/delta", "item/started", "item/completed", "turn/started", "turn/completed"):
                        event_turn = params.get("turn", {}).get("id") if isinstance(params.get("turn"), dict) else params.get("turnId")
                        if params.get("threadId") != thread_id or event_turn != turn_id:
                            raise RuntimeFailure("Codex returned activity for an unexpected thread or turn.")
                    if method == "item/agentMessage/delta":
                        if not isinstance(params.get("delta"), str) or not identifier(params.get("itemId")):
                            raise RuntimeFailure("Codex returned an invalid message update.")
                        yield RuntimeEvent(run_id=run_id, kind="message.delta", text=params["delta"])
                    elif method in ("item/started", "item/completed"):
                        item = params.get("item")
                        if not isinstance(item, dict):
                            raise RuntimeFailure("Codex returned an invalid item.")
                        kind = item.get("type")
                        if kind == "webSearch" and allow_browsing:
                            if method == "item/started":
                                yield RuntimeEvent(run_id=run_id, kind="tool.started", text="Searching online sources")
                        elif kind not in ("agentMessage", "userMessage", "reasoning"):
                            raise RuntimeFailure("Codex reported activity outside the permitted research tools.")
                    elif method == "turn/completed":
                        if params.get("turn", {}).get("status") != "completed":
                            raise RuntimeFailure("Codex turn did not complete. Check quota, authentication or cancellation.")
                        completed = True
                        break
                    elif method == "error":
                        raise RuntimeFailure("Codex reported a provider error; no automatic retry was attempted.")
        finally:
            try:
                if thread_id and turn_id and not completed:
                    await rpc.interrupt(thread_id, turn_id)
            finally:
                await rpc.close()
