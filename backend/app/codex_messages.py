"""Bounded answer assembly from authoritative v2 message completions."""
from dataclasses import dataclass

from backend.app.codex_approvals import identifier
from backend.app.runtime_base import RuntimeFailure


MAX_MESSAGES = 256
MAX_CHARACTERS = 1_000_000


@dataclass
class Message:
    phase: str | None
    completed: bool = False
    text: str = ""


class CodexMessages:
    def __init__(self):
        self.items: dict[str, Message] = {}
        self.streamed_characters = 0
        self.completed_characters = 0

    def item(self, item: dict, *, completed: bool):
        item_id, phase, text = item.get("id"), item.get("phase"), item.get("text")
        if not identifier(item_id) or phase not in (None, "commentary", "final_answer") or not isinstance(text, str):
            raise RuntimeFailure("Codex returned an invalid message item.")
        if not completed:
            if item_id in self.items or len(self.items) >= MAX_MESSAGES:
                raise RuntimeFailure("Codex repeated or exceeded message items.")
            self.count_streamed(text)
            self.items[item_id] = Message(phase)
            return
        message = self.pending(item_id)
        if message.phase is not None and phase is not None and phase != message.phase:
            raise RuntimeFailure("Codex changed a message phase unexpectedly.")
        self.completed_characters += len(text)
        if self.completed_characters > MAX_CHARACTERS:
            raise RuntimeFailure("Codex exceeded the answer size limit.")
        message.phase = phase if phase is not None else message.phase
        message.completed = True
        # Keep no progress text. Completion text is authoritative, not the deltas.
        if message.phase != "commentary":
            message.text = text

    def pending(self, item_id) -> Message:
        if not identifier(item_id) or item_id not in self.items or self.items[item_id].completed:
            raise RuntimeFailure("Codex returned an unknown or completed message item.")
        return self.items[item_id]

    def count_streamed(self, text: str):
        self.streamed_characters += len(text)
        if self.streamed_characters > MAX_CHARACTERS:
            raise RuntimeFailure("Codex exceeded the message stream size limit.")

    def delta(self, params: dict):
        self.pending(params.get("itemId"))
        text = params.get("delta")
        if not isinstance(text, str):
            raise RuntimeFailure("Codex returned an invalid message update.")
        self.count_streamed(text)

    def finish(self) -> str:
        if any(not message.completed for message in self.items.values()):
            raise RuntimeFailure("Codex ended a turn with incomplete message items.")
        # Prefer explicit final answers; absent phases retain legacy concatenation.
        # Downstream schema/evidence validation remains mandatory in both cases.
        phase = "final_answer" if any(message.phase == "final_answer" for message in self.items.values()) else None
        return "".join(message.text for message in self.items.values() if message.phase == phase)
