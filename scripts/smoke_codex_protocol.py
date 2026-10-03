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
        profile = Path(directory) / "profile"
        rpc = CodexRPC(profile, Path(directory) / "workspace", allow_browsing=False)
        try:
            await rpc.open()
            account = await rpc.request("account/read", {"refreshToken": False})
            if account.get("account") is not None:
                raise RuntimeError("The new dedicated profile unexpectedly inherited authentication")
            print("Codex initialize/account-read passed with browsing disabled; dedicated profile has no inherited account. No login or inference requested.")
        finally:
            await rpc.close()
        capabilities = await CodexRuntime(profile).check()
        assert capabilities.installed and capabilities.authentication == "required"
        assert capabilities.qualification == "protocol_only"
        assert not capabilities.generation and not capabilities.browsing and not capabilities.approvals
        print(f"Exact version {capabilities.version}: protocol-only; unauthenticated capabilities remain disabled.")


if __name__ == "__main__":
    asyncio.run(main())
