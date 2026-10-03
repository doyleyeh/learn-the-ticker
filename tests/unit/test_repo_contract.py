"""Repository boundaries for the desktop architecture, not the retired automation harness."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_authoritative_documents_and_desktop_workspace():
    for name in ("SPEC.md", "PLAN.md", "TASKS.md", "EVALS.md", "STATUS.md", "DECISIONS.md", "TECHNICAL_DESIGN_SPEC.md", "AGENTS.md", "README.md", "CONTRIBUTING.md", "docs/MIGRATION.md"):
        assert (ROOT / name).read_text(encoding="utf-8").strip()
    package = json.loads((ROOT / "package.json").read_text())
    assert package["workspaces"] == ["apps/desktop"]
    for command in ("dev", "test", "typecheck", "build"):
        assert "--workspace apps/desktop" in package["scripts"][command]
    desktop = json.loads((ROOT / "apps/desktop/package.json").read_text())
    assert "next" not in desktop["dependencies"]


def test_production_does_not_mount_fixture_routes_or_universe_gate():
    source = (ROOT / "backend/app/api.py").read_text(encoding="utf-8")
    assert "backend.main" not in source
    assert "top500" not in source and "openrouter" not in source
    assert not (ROOT / "apps/web").exists()


def test_native_frontend_has_no_arbitrary_process_permissions():
    capability = json.loads((ROOT / "apps/desktop/src-tauri/capabilities/main.json").read_text())
    assert capability["permissions"] == ["core:default"]
    client = (ROOT / "apps/desktop/src/client.ts").read_text()
    assert "localStorage" not in client and "sessionStorage" not in client
    assert 'redirect: "error"' in client


def test_generated_schema_matches_backend_contracts():
    from pydantic.json_schema import models_json_schema
    from backend.app.contracts import AssetIdentity, BackupSummary, Claim, Conversation, EvidenceBundle, ProviderLogin, ResearchRequest, ResearchResult, RuntimeCapabilities, RuntimeEvent, RuntimeModel, RuntimeModelCatalog, SavedResearch, Settings, Source, TermExplanation, TermRequest, TermResult
    models = [AssetIdentity, BackupSummary, Claim, Conversation, EvidenceBundle, ProviderLogin, ResearchRequest, ResearchResult, RuntimeCapabilities, RuntimeEvent, RuntimeModel, RuntimeModelCatalog, SavedResearch, Settings, Source, TermExplanation, TermRequest, TermResult]
    _, schema = models_json_schema([(model, "validation") for model in models], title="DesktopContracts")
    stored = json.loads((ROOT / "contracts/desktop.schema.json").read_text())
    assert stored["$defs"] == schema["$defs"]
