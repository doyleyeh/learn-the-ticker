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
    requires_native_identity: bool = False


# Direct inventory and separate live acceptance are reviewed in dated evidence.
# Version detection alone still yields protocol_only. Exact binary identity is
# required here; CodexRPC rechecks model/catalog/policy before production turns.
QUALIFICATIONS = {("codex", "0.158.0-alpha.2.1"): Qualification(
    live=True, generation=True, browsing=True, streaming=True, cancellation=True,
    approvals=True, requires_native_identity=True)}


def apply_qualification(result: RuntimeCapabilities, *, native_identity_verified: bool = False) -> RuntimeCapabilities:
    profile = QUALIFICATIONS.get((result.provider, result.version))
    live = bool(profile and profile.live and (not profile.requires_native_identity or native_identity_verified is True))
    result.qualification = "unqualified" if profile is None else ("live" if live else "protocol_only")
    enabled = bool(result.installed and live and result.authentication == "authenticated")
    for name in ("generation", "browsing", "streaming", "cancellation", "approvals"):
        setattr(result, name, bool(enabled and getattr(profile, name)))
    if profile is None:
        result.reason = "This exact runtime version is not qualified. Update connection support before starting research."
    elif not live:
        result.reason = "This installation has protocol support only. Live research requires the reviewed native Windows Codex binary and model/tool scope."
    elif result.authentication != "authenticated":
        result.reason = "Connect supported subscription authentication before starting research."
    else:
        result.reason = ("Qualified for gpt-6-astra on the reviewed native Windows binary; model/catalog/tool scope and included usage are checked per request."
                         if profile.requires_native_identity else "Qualified subscription capabilities are available; model access and quota are checked per request.")
    return result
