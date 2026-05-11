#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.analysis_pack_producer import (
    build_analysis_pack_bundle,
    build_analysis_pack_producer_summary,
    build_macro_cache_artifact,
    build_technical_data_artifact,
    default_analysis_pack_tickers,
    default_live_analysis_pack_tickers,
    load_analysis_pack_bundle,
)
from backend.analysis_packs import validate_analysis_pack_import_bundle


def main() -> int:
    args = _build_parser().parse_args()

    if args.validate_only:
        bundle = load_analysis_pack_bundle(str(args.input))
        reason_codes = validate_analysis_pack_import_bundle(bundle, now=args.now or bundle.generated_at)
        summary = build_analysis_pack_producer_summary(
            bundle,
            requested_tickers=sorted(bundle.ticker_packs),
            skipped_tickers=list(bundle.validation_metadata.get("skipped_tickers", [])),
            validation_reason_codes=reason_codes,
        )
        _write_json(args.summary_output, summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if not reason_codes else 1

    tickers = args.ticker or list(default_live_analysis_pack_tickers() if args.live else default_analysis_pack_tickers())
    bundle, summary = build_analysis_pack_bundle(
        tickers=tickers,
        bundle_id=args.bundle_id,
        generated_at=args.generated_at,
        freshness_expires_at=args.freshness_expires_at,
        expires_days=args.expires_days,
        fail_on_skipped=args.fail_on_skipped,
        live=args.live,
    )

    if args.output is None:
        raise SystemExit("--output is required unless --validate-only is set.")

    _write_json(args.output, bundle.model_dump(mode="json"))
    _write_json(args.summary_output, summary)
    if args.technical_output is not None:
        _write_json(args.technical_output, build_technical_data_artifact(bundle))
    if args.macro_output is not None:
        _write_json(args.macro_output, build_macro_cache_artifact(bundle))

    if args.print_summary:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["validation_status"] == "passed" else 1


def _write_json(path: Path | None, payload: object) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and validate a structured Codex-assisted analysis pack import bundle."
    )
    parser.add_argument("--ticker", action="append", help="High-demand ticker to include. Repeat for multiple tickers.")
    parser.add_argument("--bundle-id", help="Optional import bundle ID.")
    parser.add_argument("--generated-at", help="ISO timestamp for generated_at. Defaults to current UTC time.")
    parser.add_argument("--freshness-expires-at", help="ISO timestamp for freshness_expires_at.")
    parser.add_argument("--expires-days", type=int, default=7, help="Freshness TTL in days when freshness_expires_at is omitted.")
    parser.add_argument("--output", type=Path, help="Path for analysis-pack-import-bundle-v1 JSON.")
    parser.add_argument("--summary-output", type=Path, help="Optional path for producer summary JSON.")
    parser.add_argument("--technical-output", type=Path, help="Optional path for technical_data.json-style artifact.")
    parser.add_argument("--macro-output", type=Path, help="Optional path for macro_cache.json-style artifact.")
    parser.add_argument("--print-summary", action="store_true", help="Print producer summary to stdout.")
    parser.add_argument("--fail-on-skipped", action="store_true", help="Fail if any requested ticker is skipped.")
    parser.add_argument("--live", action="store_true", help="Use operator-approved live market/news/economic/technical adapters.")
    parser.add_argument("--validate-only", action="store_true", help="Validate an existing bundle instead of building one.")
    parser.add_argument("--input", type=Path, help="Existing bundle path for --validate-only.")
    parser.add_argument("--now", help="Validation timestamp for --validate-only. Defaults to bundle generated_at.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
