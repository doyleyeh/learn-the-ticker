"""Translate only correlated v2 access requests; never echo vendor scopes or grants."""
import asyncio
from backend.app.runtime_base import RuntimeFailure


METHODS = {
    "item/commandExecution/requestApproval": "command",
    "item/fileChange/requestApproval": "file_change",
    "item/permissions/requestApproval": "permissions",
}


def identifier(value) -> bool:
    return type(value) is str and 0 < len(value) <= 200 and all(char.isalnum() or char in "-_.:" for char in value)


class PendingTools:
    """Recognize proposed work only so it can be declined, never executed."""
    methods = {"item/commandExecution/requestApproval": "commandExecution", "item/fileChange/requestApproval": "fileChange"}

    def __init__(self):
        self.items = {}

    def activity(self, item, *, completed):
        item_id, kind, status = item.get("id"), item.get("type"), item.get("status")
        valid = identifier(item_id) and kind in self.methods.values()
        # A pending declaration cannot carry output or a completed execution result.
        valid = valid and item.get("aggregatedOutput") in (None, "") and item.get("exitCode") is None
        if not valid:
            raise RuntimeFailure("Codex reported activity outside the permitted research tools.")
        if not completed:
            if status != "inProgress" or item_id in self.items or len(self.items) >= 3:
                raise RuntimeFailure("Codex returned invalid or repeated pending tool activity.")
            self.items[item_id] = (kind, "pending")
        else:
            if status != "declined" or self.items.get(item_id) != (kind, "denied"):
                raise RuntimeFailure("Codex reported tool completion without a confirmed denial.")
            self.items[item_id] = (kind, "completed")

    def request(self, raw):
        method = raw.get("method")
        kind = self.methods.get(method) if isinstance(method, str) else None
        if kind is None: return None  # Other requests still pass the strict approval handler.
        params = raw.get("params")
        item_id = params.get("itemId") if isinstance(params, dict) else None
        if not identifier(item_id) or self.items.get(item_id) != (kind, "pending"):
            raise RuntimeFailure("Codex requested access without matching pending tool activity.")
        return item_id

    def denied(self, item_id):
        if item_id is not None:
            kind, _ = self.items[item_id]
            self.items[item_id] = (kind, "denied")

    def finish(self):
        if any(state != "completed" for _, state in self.items.values()):
            raise RuntimeFailure("Codex ended a turn with unresolved tool activity.")


class CodexApprovals:
    def __init__(self, rpc, broker, run_id: str, thread_id: str, turn_id: str):
        self.rpc, self.broker, self.run_id = rpc, broker, run_id
        self.thread_id, self.turn_id = thread_id, turn_id
        self.seen = set()

    async def handle(self, raw: dict):
        method, params, request_id = raw.get("method"), raw.get("params"), raw.get("id")
        valid_id = identifier(request_id) or (type(request_id) is int and 0 <= request_id <= 2**53 - 1)
        if (not isinstance(method, str) or method not in METHODS or not valid_id or not isinstance(params, dict)
                or params.get("threadId") != self.thread_id or params.get("turnId") != self.turn_id
                or not identifier(params.get("itemId"))):
            raise RuntimeFailure("Codex requested unsupported or uncorrelated access. No permission was granted.")
        # Disallow repeated IDs and bound requests per operation, including after denial.
        key = (type(request_id), request_id)
        if key in self.seen or len(self.seen) >= 3:
            raise RuntimeFailure("Codex repeated or exceeded access requests. No permission was granted.")
        self.seen.add(key)
        if self.broker is None:
            raise RuntimeFailure("Access review is unavailable. No permission was granted.")
        review = asyncio.create_task(self.broker.review(self.run_id, "codex", METHODS[method]))
        disconnected = asyncio.create_task(self.rpc.wait_disconnected())
        try:
            done, _ = await asyncio.wait((review, disconnected), return_when=asyncio.FIRST_COMPLETED)
            if disconnected in done:
                await disconnected
            outcome = await review
        finally:
            for task in (review, disconnected):
                if not task.done(): task.cancel()
            await asyncio.gather(review, disconnected, return_exceptions=True)
        result = {"permissions": {}, "scope": "turn"} if METHODS[method] == "permissions" else {"decision": "decline" if outcome == "deny" else "cancel"}
        await self.rpc.send({"id": request_id, "result": result})
        if outcome == "cancel":
            # The application owns cancellation even when the protocol has no cancel decision.
            raise asyncio.CancelledError
        if outcome == "expired":
            raise RuntimeFailure("Access review expired. Research stopped without granting permission; retry explicitly.")
