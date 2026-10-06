"""Export JSON Schema from Pydantic. TypeScript is generated from this file, never hand-maintained."""
import json
import argparse
from pathlib import Path
from pydantic.json_schema import models_json_schema
from backend.app.import_previews import ImportPreview
from backend.app.import_storage import RetainedImportSummary, RetainedImportView
from backend.app.import_learning import ImportExplanation, ImportLearningRequest, ImportLearningScope
from backend.app.source_review import SourceReviewDecision, SourceReviewRequest
from backend.app.freshness import BundleFreshness
from backend.app.contracts import ApprovalDecision, ApprovalRequest, AssetIdentity, BackupSummary, Claim, Conversation, EvidenceBundle, ProviderLogin, ResearchJobSummary, ResearchRequest, ResearchResult, RuntimeCapabilities, RuntimeEvent, RuntimeModel, RuntimeModelCatalog, SavedResearch, Settings, Source, TermExplanation, TermRequest, TermResult

def generated_schema() -> str:
    from backend.app.comparisons import ComparisonRequest, ComparisonResult
    from backend.app.reports import ReportRequest, ResearchReport
    models = [ApprovalDecision, ApprovalRequest, AssetIdentity, BackupSummary, Claim, Conversation, EvidenceBundle, ImportPreview, RetainedImportSummary, RetainedImportView, ImportExplanation, ImportLearningRequest, ImportLearningScope, ProviderLogin, ResearchJobSummary, ResearchRequest, ResearchResult, RuntimeCapabilities, RuntimeEvent, RuntimeModel, RuntimeModelCatalog, SavedResearch, Settings, Source, TermExplanation, TermRequest, TermResult]
    models.extend([SourceReviewDecision, SourceReviewRequest, BundleFreshness, ComparisonRequest, ComparisonResult, ReportRequest, ResearchReport])
    _, schema = models_json_schema([(model, "validation") for model in models], title="DesktopContracts")
    schema.update({"type": "object", "properties": {model.__name__: {"$ref": "#/$defs/" + model.__name__} for model in models}, "additionalProperties": False})
    return json.dumps(schema, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare without changing tracked files")
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / "contracts/desktop.schema.json"
    output = generated_schema()
    if args.check:
        if not target.is_file() or target.read_text(encoding="utf-8") != output:
            raise SystemExit("JSON Schema drift: run python -m scripts.contracts and regenerate TypeScript.")
        print("JSON Schema matches Pydantic contracts.")
    else:
        target.parent.mkdir(exist_ok=True)
        target.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
