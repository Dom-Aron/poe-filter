#!/usr/bin/env python3
"""
run_all.py

Runs the full toolkit flow:
1. update_market.py
2. market_report.py
3. suggest_filter_tiers.py
4. filter_audit.py
5. plan_upgrade_path.py (optional)

Usage:
    python scripts/run_all.py
    python scripts/run_all.py --skip-update
    python scripts/run_all.py --upgrade-plan
    python scripts/run_all.py --upgrade-plan --budget 251c
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_script(script_name: str, *args: str) -> None:
    script_path = ROOT / "scripts" / script_name
    print()
    print("=" * 72)
    command_label = " ".join([str(script_path.relative_to(ROOT)), *args])
    print(f"Running: {command_label}")
    print("=" * 72, flush=True)

    result = subprocess.run([sys.executable, str(script_path), *args], cwd=str(ROOT))

    if result.returncode != 0:
        raise SystemExit(f"Script failed: {script_name} (exit code {result.returncode})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all PoE market toolkit scripts.")
    parser.add_argument("--skip-update", action="store_true", help="Do not fetch the market; use market/latest_market.json.")
    parser.add_argument("--upgrade-plan", action="store_true", help="Also run plan_upgrade_path.py after market/filter reports.")
    parser.add_argument("--budget", help="Budget passed to plan_upgrade_path.py, e.g. 251c or 1d. If omitted, planner shows top 3 cheapest safe upgrades.")
    parser.add_argument("--profiles", help="Profiles passed to plan_upgrade_path.py, e.g. rumi_uncorrupted or ring_vulnerability,jewel_damage.")
    parser.add_argument("--top", type=int, help="Top plans passed to plan_upgrade_path.py.")
    parser.add_argument("--max-fetch", type=int, help="Max trade listings per profile for plan_upgrade_path.py.")
    parser.add_argument("--max-combo-size", type=int, help="Max combo size passed to plan_upgrade_path.py.")
    args = parser.parse_args()

    if not args.skip_update:
        run_script("update_market.py")

    run_script("market_report.py")
    run_script("suggest_filter_tiers.py")
    run_script("filter_audit.py")

    if args.upgrade_plan:
        planner_args: list[str] = []
        if args.budget:
            planner_args.extend(["--budget", args.budget])
        if args.profiles:
            planner_args.extend(["--profiles", args.profiles])
        if args.top is not None:
            planner_args.extend(["--top", str(args.top)])
        if args.max_fetch is not None:
            planner_args.extend(["--max-fetch", str(args.max_fetch)])
        if args.max_combo_size is not None:
            planner_args.extend(["--max-combo-size", str(args.max_combo_size)])
        run_script("plan_upgrade_path.py", *planner_args)

    print()
    print("Flow complete.")
    print("Main reports:")
    print("- market/reports/market_report.md")
    print("- market/reports/filter_suggestions.md")
    print("- market/reports/filter_audit.md")
    if args.upgrade_plan:
        print("- market/reports/upgrade_plan.md")
        print("- market/reports/upgrade_plan.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
