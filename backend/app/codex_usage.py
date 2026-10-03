"""Do not infer included subscription permission from balances or percentages."""
from backend.app.runtime_base import RuntimeFailure


def require_included_usage(value: dict):
    # The pinned App Server schema documents this as a backend permission that
    # has been validated against the active account. Null/missing is unknown.
    if value.get("ordinaryUsageAllowed") is not True:
        raise RuntimeFailure("Included subscription usage is unavailable or unconfirmed. Check quota and plan access; no paid credit, API billing or automatic retry was enabled.")
