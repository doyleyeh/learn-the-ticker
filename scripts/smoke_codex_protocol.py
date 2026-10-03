"""Explicit, no-inference local App Server handshake with a new isolated profile."""
import asyncio
import tempfile
from pathlib import Path

from backend.app.codex_rpc import CodexRPC
from backend.app.codex_runtime import CodexRuntime


async def main():
    root = Path(__file__).resolve().parents[1] / ".local"
    root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codex-protocol-", dir=root) as directory:
        # A parent project must not contribute tools/instructions to the app workspace.
        inherited = Path(directory) / ".codex"
        inherited.mkdir()
        (inherited / "config.toml").write_text('developer_instructions="UNTRUSTED_PARENT_SENTINEL"\n[mcp_servers.untrusted]\ncommand="must-not-launch"\n', encoding="utf-8")
        profile = Path(directory) / "profile"
        rpc = CodexRPC(profile, Path(directory) / "workspace", allow_browsing=False)
        try:
            await rpc.open()
            account = await rpc.request("account/read", {"refreshToken": False})
            if account.get("account") is not None:
                raise RuntimeError("The new dedicated profile unexpectedly inherited authentication")
            await rpc.start_thread()
            print("Codex effective configuration/features, account-read and isolated thread-start passed with browsing disabled. No inherited account, login or inference requested.")
        finally:
            await rpc.close()
        capabilities = await CodexRuntime(profile).check()
        assert capabilities.installed and capabilities.authentication == "required"
        assert capabilities.qualification == "protocol_only"
        assert not capabilities.generation and not capabilities.browsing and not capabilities.approvals
        print(f"Exact version {capabilities.version}: protocol-only; unauthenticated capabilities remain disabled.")
        catalog = await CodexRuntime(profile).models()
        assert catalog.status == "authentication_required" and not catalog.models
        print("Model discovery requires the dedicated subscription sign-in; no catalog entitlement or inference was assumed.")


if __name__ == "__main__":
    asyncio.run(main())
