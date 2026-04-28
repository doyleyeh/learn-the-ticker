#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.source_policy import SourcePolicyAction, validate_source_handoff


SCHEMA_VERSION = "source-handoff-manifest-v1"
FINALIZABLE_MANIFEST_STATUSES = {"draft", "finalized"}
EVIDENCE_ACTIONS = (
    SourcePolicyAction.generated_claim_support,
    SourcePolicyAction.cacheable_generated_output,
    SourcePolicyAction.markdown_json_section_export,
)


class SourceHandoffManifestError(ValueError):
    pass


def inspect_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    _validate_manifest_shape(manifest)
    sources = manifest.get("sources") or []
    inspected_sources = [_inspect_source(source, index=index) for index, source in enumerate(sources)]
    finalizable = bool(inspected_sources) and all(source["finalizable"] for source in inspected_sources)
    blocking_source_count = sum(1 for source in inspected_sources if not source["finalizable"])
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_id": manifest.get("manifest_id"),
        "manifest_status": manifest.get("manifest_status"),
        "source_count": len(inspected_sources),
        "blocking_source_count": blocking_source_count,
        "finalizable": finalizable,
        "sources": inspected_sources,
    }


def finalized_manifest(
    manifest: dict[str, Any],
    *,
    finalized_at: str | None = None,
) -> dict[str, Any]:
    inspection = inspect_manifest(manifest)
    if manifest.get("manifest_status") not in FINALIZABLE_MANIFEST_STATUSES:
        raise SourceHandoffManifestError("Only draft or finalized source-handoff manifests can be finalized.")
    if not inspection["finalizable"]:
        blockers = _blocking_summary(inspection)
        raise SourceHandoffManifestError(f"Source-handoff manifest is blocked from finalization: {blockers}")

    output = dict(manifest)
    output["schema_version"] = SCHEMA_VERSION
    output["manifest_status"] = "finalized"
    output["finalized_at"] = finalized_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output["inspection"] = {
        "source_count": inspection["source_count"],
        "blocking_source_count": inspection["blocking_source_count"],
        "finalizable": inspection["finalizable"],
        "validated_actions": [action.value for action in EVIDENCE_ACTIONS],
    }
    return output


def _inspect_source(source: dict[str, Any], *, index: int) -> dict[str, Any]:
    source_id = source.get("source_id") or source.get("source_document_id") or f"source[{index}]"
    action_results = {}
    reason_codes: list[str] = []
    for action in EVIDENCE_ACTIONS:
        result = validate_source_handoff(source, action=action)
        action_results[action.value] = {
            "allowed": result.allowed,
            "reason_codes": list(result.reason_codes),
        }
        reason_codes.extend(result.reason_codes)

    unique_reasons = list(dict.fromkeys(reason_codes))
    return {
        "source_id": source_id,
        "source_identity": source.get("source_identity") or source.get("url") or source.get("source_document_id"),
        "source_type": source.get("source_type"),
        "review_status": source.get("review_status"),
        "parser_status": source.get("parser_status"),
        "freshness_state": source.get("freshness_state"),
        "source_use_policy": source.get("source_use_policy"),
        "storage_rights": source.get("storage_rights"),
        "export_rights": source.get("export_rights"),
        "finalizable": not unique_reasons,
        "reason_codes": unique_reasons,
        "actions": action_results,
    }


def _validate_manifest_shape(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise SourceHandoffManifestError(f"Expected schema_version {SCHEMA_VERSION}.")
    if not manifest.get("manifest_id"):
        raise SourceHandoffManifestError("Source-handoff manifest must include manifest_id.")
    if manifest.get("manifest_status") not in {"draft", "finalized", "pending_review", "rejected"}:
        raise SourceHandoffManifestError("manifest_status must be draft, finalized, pending_review, or rejected.")
    if not isinstance(manifest.get("sources"), list):
        raise SourceHandoffManifestError("Source-handoff manifest must include a sources list.")


def _blocking_summary(inspection: dict[str, Any]) -> str:
    blocked = []
    for source in inspection["sources"]:
        if not source["finalizable"]:
            reasons = ",".join(source["reason_codes"]) or "blocked"
            blocked.append(f"{source['source_id']}[{reasons}]")
    return "; ".join(blocked)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or finalize governed source-handoff manifest packets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect source-handoff manifest packets.")
    inspect_parser.add_argument("manifest", type=Path)
    inspect_parser.add_argument("--strict", action="store_true", help="Exit non-zero when any packet is blocked.")

    finalize_parser = subparsers.add_parser("finalize", help="Finalize only fully approved source-handoff manifests.")
    finalize_parser.add_argument("manifest", type=Path)
    finalize_parser.add_argument("--output", type=Path, required=True)
    finalize_parser.add_argument("--finalized-at", help="Deterministic UTC timestamp to write into finalized_at.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        manifest = _read_json(args.manifest)
        if args.command == "inspect":
            inspection = inspect_manifest(manifest)
            print(json.dumps(inspection, indent=2, sort_keys=True))
            return 0 if inspection["finalizable"] or not args.strict else 1
        finalized = finalized_manifest(manifest, finalized_at=args.finalized_at)
        _write_json(args.output, finalized)
        print(json.dumps(finalized["inspection"], indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, SourceHandoffManifestError) as exc:
        print(f"source-handoff manifest error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
