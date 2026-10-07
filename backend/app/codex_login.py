"""Ephemeral device authorization. Codex owns token storage and refresh."""
from __future__ import annotations

import asyncio
import re
from datetime import timedelta
from pathlib import Path

from backend.app.codex_rpc import CodexRPC
from backend.app.codex_runtime import subscription_account
from backend.app.contracts import ProviderLogin, now
from backend.app.runtime_base import RuntimeFailure

DEVICE_URL = "https://auth.openai.com/codex/device"


class CodexLogin:
    def __init__(self, profile: Path, *, rpc_factory=CodexRPC, lifetime=600):
        self.profile, self.rpc_factory, self.lifetime = profile, rpc_factory, lifetime
        self.state = ProviderLogin()
        self.task = None
        self.lock = asyncio.Lock()

    def snapshot(self) -> ProviderLogin:
        return self.state.model_copy(deep=True)

    def finish(self, status, message):
        # Clear device code and URL for every terminal outcome.
        self.state = ProviderLogin(status=status, message=message)

    async def start(self) -> ProviderLogin:
        async with self.lock:
            if self.task and not self.task.done():
                return self.snapshot()
            rpc = self.rpc_factory(self.profile, self.profile / "onboarding")
            try:
                await rpc.open()
                if subscription_account(await rpc.request("account/read", {"refreshToken": False})):
                    self.finish("authenticated", "ChatGPT sign-in is connected. No content was generated.")
                    await rpc.close()
                    return self.snapshot()
                result = await rpc.request("account/login/start", {"type": "chatgptDeviceCode"})
                login_id, code = result.get("loginId"), result.get("userCode")
                if (result.get("type") != "chatgptDeviceCode" or result.get("verificationUrl") != DEVICE_URL
                        or not isinstance(login_id, str) or not 1 <= len(login_id) <= 200
                        or not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9-]{4,32}", code)):
                    raise RuntimeFailure("Unsupported authorization response")
                self.state = ProviderLogin(status="pending", verification_url=DEVICE_URL, user_code=code,
                    expires_at=now() + timedelta(seconds=self.lifetime),
                    message="Open the official sign-in page and enter this code. Only authorize a request you started here.")
                self.task = asyncio.create_task(self.monitor(rpc, login_id))
                # Enter the monitor's cleanup scope before an immediate Cancel can run.
                await asyncio.sleep(0)
                return self.snapshot()
            except (RuntimeFailure, OSError, ValueError, TypeError):
                self.finish("failed", "Codex sign-in could not start. Check the installed runtime, network and device authorization availability.")
                await rpc.close()
                return self.snapshot()
            except BaseException:
                await rpc.close()
                raise

    async def monitor(self, rpc, login_id):
        try:
            async with asyncio.timeout(self.lifetime):
                while True:
                    event = await rpc.event()
                    if "id" in event:
                        raise RuntimeFailure("Unexpected authorization request")
                    if event.get("method") == "error":
                        raise RuntimeFailure("Authorization failed")
                    params = event.get("params", {})
                    if not isinstance(params, dict):
                        raise RuntimeFailure("Malformed authorization event")
                    if event.get("method") == "account/login/completed" and params.get("loginId") == login_id:
                        if params.get("success") is not True:
                            raise RuntimeFailure("Authorization did not complete")
                        if not subscription_account(await rpc.request("account/read", {"refreshToken": False})):
                            raise RuntimeFailure("Subscription authentication required")
                        self.finish("authenticated", "ChatGPT sign-in is connected. Enable cloud research when you are ready.")
                        return
        except asyncio.CancelledError:
            self.finish("cancelled", "Sign-in cancelled. You can start again when ready.")
            await self.cancel_provider(rpc, login_id)
        except TimeoutError:
            self.finish("expired", "Sign-in expired. Start again to request a new code.")
            await self.cancel_provider(rpc, login_id)
        except (RuntimeFailure, OSError, ValueError, TypeError):
            self.finish("failed", "Sign-in did not complete. Check the provider connection and start again.")
        finally:
            await rpc.close()

    async def cancel_provider(self, rpc, login_id):
        try:
            await rpc.request("account/login/cancel", {"loginId": login_id}, timeout=3)
        except (RuntimeFailure, OSError):
            pass  # Closing the owned process also terminates the pending flow.

    async def cancel(self) -> ProviderLogin:
        async with self.lock:
            if self.task and not self.task.done():
                self.task.cancel()
                await self.task
            return self.snapshot()

    async def close(self):
        await self.cancel()
