#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.analysis_pack_producer import load_analysis_pack_bundle
from backend.analysis_packs import validate_analysis_pack_import_bundle


DEFAULT_IMPORT_ENDPOINT = "http://127.0.0.1:8000/api/admin/analysis-packs/import"


def main() -> int:
    args = _build_parser().parse_args()
    bundle = load_analysis_pack_bundle(str(args.bundle))
    reason_codes = validate_analysis_pack_import_bundle(bundle, now=args.now or bundle.generated_at)
    if reason_codes:
        print(json.dumps({"uploaded": False, "validation_reason_codes": reason_codes}, indent=2, sort_keys=True))
        return 1

    if args.dry_run:
        print(
            json.dumps(
                {
                    "uploaded": False,
                    "dry_run": True,
                    "bundle_id": bundle.bundle_id,
                    "endpoint": args.endpoint,
                    "validation_reason_codes": [],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    body = json.dumps(bundle.model_dump(mode="json")).encode("utf-8")
    request = urlrequest.Request(
        args.endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=args.timeout_seconds) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        print(exc.read().decode("utf-8") or str(exc))
        return 1
    except URLError as exc:
        print(json.dumps({"uploaded": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1

    print(payload)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and upload an analysis pack bundle to the backend admin import route.")
    parser.add_argument("--bundle", type=Path, required=True, help="Path to analysis-pack-import-bundle-v1 JSON.")
    parser.add_argument("--endpoint", default=DEFAULT_IMPORT_ENDPOINT, help="Admin import endpoint URL.")
    parser.add_argument("--now", help="Optional validation timestamp. Defaults to bundle generated_at.")
    parser.add_argument("--timeout-seconds", type=int, default=30, help="Upload timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Validate locally but do not POST.")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
