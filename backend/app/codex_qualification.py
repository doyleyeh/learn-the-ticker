"""Reviewed native identity scope; never inferred from settings or provider output."""
import hashlib
import json
from pathlib import Path
import sys

from backend.app.codex_policy import policy_config
from backend.app.runtime_base import RuntimeFailure, executable_command


# Evidence: docs/verification/2026-10-04-codex-wire-inventory.md and separate
# subscription acceptance. Changes require new measurement/review, not autofill.
MODEL = "gpt-6-astra"
EXECUTABLE_SHA256 = "8f0554ede25bbc5450921897c468b2e84635aa513c5017457997af0954581f49"
CATALOG_SHA256 = "f63c9c65e5fa7df6b724ab3e91fe704213d8fa9af5968969f7dba61a8e9ddbf7"
POLICY_SHA256 = {
    False: "1093e995d8b38307069bf362657cc135c6369120d658a577b69f2d50d53dec9b",
    True: "9b9696e7ca22b79c90e5607fb275a2a66a80dbefbbf089ba0daa3fbeb6a73372",
}
CAPABILITIES = {"namespaceTools": True, "imageGeneration": True, "webSearch": True}
ERROR = "This Codex binary, platform, model or tool policy is outside the reviewed qualification. No inference or fallback was started."


def native_identity_verified() -> bool:
    if sys.platform != "win32": return False
    try:
        command = executable_command("codex")
        if len(command) != 1 or Path(command[0]).suffix.lower() != ".exe": return False
        with Path(command[0]).open("rb") as file:
            return hashlib.file_digest(file, "sha256").hexdigest() == EXECUTABLE_SHA256
    except (OSError, RuntimeFailure):
        return False


def require_scope(catalog, model, browsing, capabilities):
    if not native_identity_verified(): raise RuntimeFailure(ERROR)
    if (model != MODEL or catalog.model != model or catalog.digest.hex() != CATALOG_SHA256
            or type(browsing) is not bool or not isinstance(capabilities, dict)
            or set(capabilities) != set(CAPABILITIES)
            or any(type(capabilities[k]) is not bool or capabilities[k] != v for k, v in CAPABILITIES.items())):
        raise RuntimeFailure(ERROR)
    catalog.verify()
    # Normalize only the per-operation temporary path; all tool/sandbox flags
    # must still match the policy whose complete declaration was measured.
    raw = json.dumps(policy_config(browsing, Path("QUALIFIED_CATALOG")), sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA256[browsing]: raise RuntimeFailure(ERROR)
