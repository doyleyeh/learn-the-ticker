#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.etf_universe import (
    RECOGNITION_ETF_UNIVERSE_MANIFEST_PATH,
    SUPPORTED_ETF_UNIVERSE_MANIFEST_PATH,
    build_etf_launch_review_packet,
    load_etf_universe_manifest_from_path,
)
from backend.models import Top500CandidateDiffReport, Top500CandidateManifest
from backend.top500_candidate_manifest import (
    TOP500_DIFF_OUTPUT_TEMPLATE,
    build_top500_operator_review_summary,
    generate_top500_candidate_manifest_from_fixture_paths,
    inspect_top500_candidate_review_packet,
    write_candidate_outputs,
    write_top500_review_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or inspect deterministic review-only launch manifest packets."
    )
    subparsers = parser.add_subparsers(dest="scope", required=True)

    top500 = subparsers.add_parser("top500", help="Top-500 stock candidate review packet commands.")
    top500_subparsers = top500.add_subparsers(dest="command", required=True)
    top500_generate = top500_subparsers.add_parser("generate", help="Generate candidate, diff, and review summary.")
    top500_generate.add_argument("--candidate-month", required=True, help="Candidate month in YYYY-MM form.")
    top500_generate.add_argument("--rank-limit", type=int, default=10, help="Fixture rank limit to emit.")
    top500_generate.add_argument("--root", default=".", help="Repository root for fixture input and output paths.")

    top500_inspect = top500_subparsers.add_parser("inspect", help="Inspect an existing candidate and diff packet.")
    top500_inspect.add_argument("--candidate-path", required=True, help="Candidate manifest path.")
    top500_inspect.add_argument("--diff-path", required=True, help="Candidate diff report path.")
    top500_inspect.add_argument("--root", default=".", help="Repository root used to resolve relative paths.")
    top500_inspect.add_argument(
        "--write-review-summary",
        action="store_true",
        help="Write the review summary artifact next to the candidate and diff naming family.",
    )

    etf = subparsers.add_parser("etf", help="ETF supported/recognition manifest review packet commands.")
    etf_subparsers = etf.add_subparsers(dest="command", required=True)
    etf_inspect = etf_subparsers.add_parser("inspect", help="Inspect supported and recognition ETF manifests.")
    etf_inspect.add_argument("--root", default=".", help="Repository root used to resolve default paths.")
    etf_inspect.add_argument(
        "--supported-path",
        default=str(SUPPORTED_ETF_UNIVERSE_MANIFEST_PATH.relative_to(ROOT)),
        help="Supported ETF manifest path.",
    )
    etf_inspect.add_argument(
        "--recognition-path",
        default=str(RECOGNITION_ETF_UNIVERSE_MANIFEST_PATH.relative_to(ROOT)),
        help="ETF/ETP recognition manifest path.",
    )

    args = parser.parse_args()
    if args.scope == "top500" and args.command == "generate":
        summary = _generate_top500(args)
    elif args.scope == "top500" and args.command == "inspect":
        summary = _inspect_top500(args)
    elif args.scope == "etf" and args.command == "inspect":
        summary = _inspect_etf(args)
    else:
        parser.error("Unsupported command.")

    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0


def _generate_top500(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.root).resolve()
    fixture_dir = root / "tests" / "fixtures" / "top500_refresh"
    result = generate_top500_candidate_manifest_from_fixture_paths(
        primary_fixture_path=fixture_dir / "official_iwb_holdings.json",
        fallback_fixture_paths=[
            fixture_dir / "official_spy_holdings.json",
            fixture_dir / "official_ivv_holdings.json",
            fixture_dir / "official_voo_holdings.json",
        ],
        sec_company_fixture_path=fixture_dir / "sec_company_tickers_exchange.json",
        nasdaq_symbol_fixture_path=fixture_dir / "nasdaq_symbol_directory.json",
        candidate_month=args.candidate_month,
        rank_limit=args.rank_limit,
    )
    candidate_path, diff_path = write_candidate_outputs(result, root=root)
    summary = build_top500_operator_review_summary(result)
    review_path = write_top500_review_summary(summary, root=root)
    return {
        **summary,
        "written_artifacts": [
            str(candidate_path.relative_to(root)),
            str(diff_path.relative_to(root)),
            str(review_path.relative_to(root)),
        ],
    }


def _inspect_top500(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.root).resolve()
    candidate_path = _resolve(root, args.candidate_path)
    diff_path = _resolve(root, args.diff_path)
    candidate = Top500CandidateManifest.model_validate(_load_json(candidate_path))
    diff = Top500CandidateDiffReport.model_validate(_load_json(diff_path))
    summary = inspect_top500_candidate_review_packet(candidate_manifest=candidate, diff_report=diff)
    if args.write_review_summary:
        review_path = write_top500_review_summary(summary, root=root)
        return {**summary, "written_artifacts": [str(review_path.relative_to(root))]}
    return summary


def _inspect_etf(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.root).resolve()
    supported = load_etf_universe_manifest_from_path(_resolve(root, args.supported_path))
    recognition = load_etf_universe_manifest_from_path(_resolve(root, args.recognition_path))
    return build_etf_launch_review_packet(supported_manifest=supported, recognition_manifest=recognition)


def _resolve(root: Path, path: str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def _load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    raise SystemExit(main())
