"""Explicit synthetic UI preview; never imported by the production application."""
from pathlib import Path
import asyncio
import json
import sys
import uvicorn
from backend.app.api import create_app
from backend.app.contracts import AssetIdentity, Claim, EvidenceBundle, RuntimeCapabilities, RuntimeEvent, RuntimeModel, RuntimeModelCatalog, Source, SourcePolicy
from backend.app.db import Database
from backend.app.backup import make_backup


class PreviewLoginRPC:
    """Synthetic sign-in for UI validation; no provider is launched or contacted."""
    async def open(self):
        pass

    async def request(self, method, params, **kwargs):
        if method == "account/read":
            return {"account": None}
        if method == "account/login/start":
            return {"type": "chatgptDeviceCode", "loginId": "synthetic", "verificationUrl": "https://auth.openai.com/codex/device", "userCode": "TEST-ONLY"}
        return {}

    async def event(self):
        await asyncio.Future()

    async def close(self):
        pass


class PreviewTermRuntime:
    async def check(self):
        return RuntimeCapabilities(provider="codex", reason="Synthetic UI test runtime only")

    async def models(self):
        return RuntimeModelCatalog(provider="codex", status="available", models=[
            RuntimeModel(id="synthetic-default", name="Synthetic default model", is_default=True),
            RuntimeModel(id="synthetic-alternate", name="Synthetic alternate model")],
            message="Synthetic catalog for interface tests only. No subscription or inference is contacted.")

    async def stream(self, prompt, run_id, workspace, model=None, *, allow_browsing=True):
        await asyncio.sleep(.1)
        text = "營收指扣除成本前的銷售收入。此頁為介面測試用的虛構公司，沒有已驗證的營收數據。" if "in zh-TW" in prompt else "Revenue means sales before costs. This fictional example has no verified revenue figures."
        yield RuntimeEvent(run_id=run_id, kind="message.delta", text=json.dumps({"explanation": text, "basis": "snapshot", "source_ids": ["synthetic-source"]}))

if __name__ == "__main__":
    db = Database("sqlite://", testing=True)
    asset = AssetIdentity(id="XTEST:SYNTH", name="Synthetic Research Example", symbol="SYNTH", asset_type="stock", exchange="XTEST")
    source = Source(id="synthetic-source", asset_id=asset.id, url="https://example.com/synthetic", title="Synthetic evidence for UI testing", publisher="Test fixture", policy=SourcePolicy.summary, provenance="user_import", excerpt="Synthetic Research Example is a fictional company used for interface tests.", verified=True)
    bundle = EvidenceBundle(asset=asset, sources=[source], claims=[Claim(asset_id=asset.id, kind="fact", text=source.excerpt, source_ids=[source.id])], notes=[Claim(asset_id=asset.id, text="This unverified example must never appear in a chart or canonical evidence.", source_ids=[source.id])])
    value = bundle.model_dump(mode="json")
    db.put("asset:" + asset.id, "asset", value)
    db.put("bundle:" + bundle.id, "bundle", value, asset.id)
    if "--restore-demo" in sys.argv:
        archive = Path(".local/restore-demo.lttbackup")
        archive.parent.mkdir(exist_ok=True)
        archive.write_bytes(make_backup(db))
        db = Database("sqlite://", testing=True)
    if "--models-demo" in sys.argv:
        db.put("settings", "settings", {"model": "synthetic-removed"})
    app = create_app(db, "synthetic-preview-credential-not-for-production", Path(".local/preview"), adapters={"codex": PreviewTermRuntime()} if "--terms-demo" in sys.argv or "--models-demo" in sys.argv else None)
    if "--login-demo" in sys.argv:
        app.state.codex_login.rpc_factory = lambda *_: PreviewLoginRPC()
    uvicorn.run(app, host="127.0.0.1", port=18764, access_log=False)
