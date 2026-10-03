"""Reviewed exact-version qualifications, never populated by model output or settings."""
from dataclasses import dataclass

from backend.app.contracts import RuntimeCapabilities


@dataclass(frozen=True)
class Qualification:
    live: bool = False
    generation: bool = False
    browsing: bool = False
    streaming: bool = False
    cancellation: bool = False
    approvals: bool = False


# This version passed only initialize/account-read, NOT inference or tool isolation.
# Evidence: docs/archive/2026-10-04/IMPLEMENTATION.md#verification-record-2026-10-03
# Add live capabilities only with the corresponding dated EVALS qualification.
QUALIFICATIONS = {("codex", "0.158.0-alpha.2.1"): Qualification()}


def apply_qualification(result: RuntimeCapabilities) -> RuntimeCapabilities:
    profile = QUALIFICATIONS.get((result.provider, result.version))
    result.qualification = "unqualified" if profile is None else ("live" if profile.live else "protocol_only")
    enabled = bool(result.installed and profile and profile.live and result.authentication == "authenticated")
    for name in ("generation", "browsing", "streaming", "cancellation", "approvals"):
        setattr(result, name, bool(enabled and getattr(profile, name)))
    if profile is None:
        result.reason = "This exact runtime version is not qualified. Update connection support before starting research."
    elif not profile.live:
        result.reason = "Only the local protocol has been checked for this version. Live research and tool isolation remain unqualified."
    elif result.authentication != "authenticated":
        result.reason = "Connect supported subscription authentication before starting research."
    else:
        result.reason = "Qualified subscription capabilities are available; model access and quota are checked per request."
    return result
