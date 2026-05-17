#!/usr/bin/env python3
"""
run_all.py

Runs the full toolkit flow:
1. update_market.py
2. market_report.py
3. suggest_filter_tiers.py
4. filter_audit.py

Usage:
    python scripts/run_all.py
    python scripts/run_all.py --skip-update
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_script(script_name: str) -> None:
    script_path = ROOT / "scripts" / script_name
    print()
    print("=" * 72)
    print(f"Running: {script_path.relative_to(ROOT)}")
    print("=" * 72, flush=True)

    result = subprocess.run([sys.executable, str(script_path)], cwd=str(ROOT))

    if result.returncode != 0:
        raise SystemExit(f"Script failed: {script_name} (exit code {result.returncode})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all PoE market toolkit scripts.")
    parser.add_argument("--skip-update", action="store_true", help="Do not fetch the market; use market/latest_market.json.")
    args = parser.parse_args()

    if not args.skip_update:
        run_script("update_market.py")

    run_script("market_report.py")
    run_script("suggest_filter_tiers.py")
    run_script("filter_audit.py")

    print()
    print("Flow complete.")
    print("Main reports:")
    print("- market/reports/market_report.md")
    print("- market/reports/filter_suggestions.md")
    print("- market/reports/filter_audit.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
