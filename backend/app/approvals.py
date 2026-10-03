"""Single-use, memory-only reviews; the frontend cannot expand runtime permissions."""
import asyncio
from dataclasses import dataclass
from datetime import timedelta

from backend.app.contracts import ApprovalDecision, ApprovalRequest, now
from backend.app.runtime_base import RuntimeFailure


@dataclass
class Pending:
    request: ApprovalRequest
    future: asyncio.Future
    deadline: float


class ApprovalBroker:
    def __init__(self, lifetime: float = 60):
        self.lifetime = lifetime
        self.pending: dict[str, Pending] = {}

    def snapshot(self) -> list[ApprovalRequest]:
        current = asyncio.get_running_loop().time()
        return [item.request.model_copy(deep=True) for item in self.pending.values()
                if not item.future.done() and current < item.deadline]

    async def review(self, run_id: str, provider: str, kind: str) -> str:
        if self.pending:
            raise RuntimeFailure("Another access review is pending; no permission was granted.")
        loop = asyncio.get_running_loop()
        request = ApprovalRequest(run_id=run_id, provider=provider, kind=kind, expires_at=now() + timedelta(seconds=self.lifetime))
        item = Pending(request, loop.create_future(), loop.time() + self.lifetime)
        self.pending[request.id] = item
        try:
            return await asyncio.wait_for(item.future, self.lifetime)
        except TimeoutError:
            return "expired"
        finally:
            self.pending.pop(request.id, None)

    def resolve(self, run_id: str, request_id: str, decision: ApprovalDecision):
        item = self.pending.get(request_id)
        if not item or item.request.run_id != run_id or item.future.done() or asyncio.get_running_loop().time() >= item.deadline:
            raise ValueError("Access review expired or no longer belongs to this active request. Nothing was approved.")
        item.future.set_result(decision.decision)

    def cancel(self, run_id: str | None = None):
        for item in self.pending.values():
            if (run_id is None or item.request.run_id == run_id) and not item.future.done():
                item.future.cancel()
