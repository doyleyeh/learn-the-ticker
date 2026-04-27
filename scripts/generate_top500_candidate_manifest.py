#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.top500_candidate_manifest import (
    generate_top500_candidate_manifest_from_fixture_paths,
    write_candidate_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic reviewed Top-500 candidate fixtures.")
    parser.add_argument("--candidate-month", required=True, help="Candidate month in YYYY-MM form.")
    parser.add_argument("--rank-limit", type=int, default=10, help="Fixture rank limit to emit.")
    parser.add_argument("--root", default=".", help="Repository root for fixture input and output paths.")
    args = parser.parse_args()

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
    print(candidate_path.relative_to(root))
    print(diff_path.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
