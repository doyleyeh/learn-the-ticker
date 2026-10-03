"""Subscription-only research through the application's dedicated Codex profile."""
import asyncio
from pathlib import Path

from backend.app.codex_rpc import CodexRPC
from backend.app.contracts import RuntimeEvent, RuntimeModelCatalog
from backend.app.codex_models import read_models, select_model
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
        try:
            async with asyncio.timeout(180):
                await rpc.open()
                if not subscription_account(await rpc.request("account/read", {"refreshToken": False})):
                    raise RuntimeFailure("Sign in to ChatGPT / Codex in Connections. API-key billing is not enabled.")
                selected = select_model(await read_models(rpc), model)
                thread_id = await rpc.start_thread(selected)
                await rpc.request("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": prompt}]})
                while True:
                    raw = await rpc.event()
                    method, params = raw.get("method"), raw.get("params", {})
                    if not isinstance(params, dict):
                        raise RuntimeFailure("Codex returned invalid event parameters.")
                    if "id" in raw:
                        yield RuntimeEvent(run_id=run_id, kind="approval.required", text="Expanded access requested. This preview stops rather than approving it.")
                        raise RuntimeFailure("Expanded access requires an implemented approval flow.")
                    if method == "item/agentMessage/delta":
                        if not isinstance(params.get("delta"), str):
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
                        break
                    elif method == "error":
                        raise RuntimeFailure("Codex reported a provider error; no automatic retry was attempted.")
        finally:
            await rpc.close()
