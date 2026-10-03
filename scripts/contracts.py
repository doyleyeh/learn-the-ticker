"""Export JSON Schema from Pydantic. TypeScript is generated from this file, never hand-maintained."""
import json
from pathlib import Path
from pydantic.json_schema import models_json_schema
from backend.app.contracts import AssetIdentity, BackupSummary, Claim, Conversation, EvidenceBundle, ProviderLogin, ResearchRequest, ResearchResult, RuntimeCapabilities, RuntimeEvent, SavedResearch, Settings, Source, TermExplanation, TermRequest, TermResult

models = [AssetIdentity, BackupSummary, Claim, Conversation, EvidenceBundle, ProviderLogin, ResearchRequest, ResearchResult, RuntimeCapabilities, RuntimeEvent, SavedResearch, Settings, Source, TermExplanation, TermRequest, TermResult]
_, schema = models_json_schema([(model, "validation") for model in models], title="DesktopContracts")
schema.update({"type": "object", "properties": {model.__name__: {"$ref": "#/$defs/" + model.__name__} for model in models}, "additionalProperties": False})
root = Path(__file__).resolve().parents[1]
(root / "contracts").mkdir(exist_ok=True)
(root / "contracts/desktop.schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
