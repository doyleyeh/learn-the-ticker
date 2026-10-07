"""Backend-only data-provider credentials in the native Windows vault."""
from __future__ import annotations

import hmac
import json
import re
import sys
from dataclasses import dataclass, field

SERVICE = "LearnTheTicker.DataSources"
PROVIDERS = {
    "eodhd": "EODHD_API_KEY",
    "tiingo": "TIINGO_API_KEY",
    "fmp": "FMP_API_KEY",
    "alpha-vantage": "ALPHA_VANTAGE_API_KEY",
    "finnhub": "FINNHUB_API_KEY",
    "marketaux": "MARKETAUX_API_KEY",
    "guardian": "GUARDIAN_API_KEY",
    "gnews": "GNEWS_API_KEY",
    "mediastack": "MEDIASTACK_API_KEY",
    "newsapi": "NEWSAPI_API_KEY",
}


class DataCredentialError(RuntimeError):
    """Fixed messages only: native errors can include secret material."""


@dataclass(frozen=True)
class DataCredential:
    api_key: str = field(repr=False)
    plan: str = "unknown"


def provider_name(provider: str) -> str:
    if provider not in PROVIDERS:
        raise DataCredentialError("Unsupported data provider.")
    return provider


def validate_credential(api_key: str, plan: str = "unknown") -> DataCredential:
    if (not isinstance(api_key, str) or not re.fullmatch(r"[A-Za-z0-9._~+/=-]{1,1024}", api_key)
            or any(api_key.startswith(name + "=") for name in PROVIDERS.values())):
        raise DataCredentialError("Paste only the key value, without quotes, a variable name or line breaks.")
    if not isinstance(plan, str) or not 1 <= len(plan) <= 100 or any(ord(char) < 32 or ord(char) > 126 for char in plan):
        raise DataCredentialError("Use a short plain-text plan label, or leave it unknown.")
    return DataCredential(api_key, plan)


def windows_vault():
    if sys.platform != "win32":
        raise DataCredentialError("Run this setup in native Windows PowerShell, not WSL.")
    try:
        from keyring.backends.Windows import WinVaultKeyring
        return WinVaultKeyring()
    except Exception:
        raise DataCredentialError("Windows Credential Manager is unavailable.") from None


class DataCredentialStore:
    def __init__(self, *, _vault=None, _service=SERVICE):
        self._vault = windows_vault() if _vault is None else _vault
        self._service = _service

    def load(self, provider: str) -> DataCredential | None:
        account = provider_name(provider)
        try:
            value = self._vault.get_password(self._service, account)
            if value is None:
                return None
            if not isinstance(value, str) or len(value) > 8192:
                raise ValueError
            data = json.loads(value)
            if not isinstance(data, dict) or set(data) != {"api_key", "plan"}:
                raise ValueError
            return validate_credential(data["api_key"], data["plan"])
        except Exception:
            raise DataCredentialError("Could not read this data credential from Windows Credential Manager.") from None

    def save(self, provider: str, api_key: str, plan: str = "unknown") -> None:
        account = provider_name(provider)
        value = validate_credential(api_key, plan)
        encoded = json.dumps({"api_key": value.api_key, "plan": value.plan}, separators=(",", ":"))
        try:
            self._vault.set_password(self._service, account, encoded)
            stored = self.load(account)
            if stored is None or not hmac.compare_digest(stored.api_key, value.api_key) or stored.plan != value.plan:
                raise ValueError
        except Exception:
            raise DataCredentialError("Could not verify the saved data credential. It may have been saved; check setup again.") from None

    def configured(self, provider: str) -> bool:
        return self.load(provider) is not None
