#!/usr/bin/env python3
"""
run_all.py

Runs the full toolkit flow:
1. fetch_character.py / parse_character.py (optional)
2. update_market.py
3. market_report.py
4. suggest_filter_tiers.py
5. filter_audit.py
6. compare_current_to_target.py (optional)
7. recommend_next_steps.py (optional)
8. plan_upgrade_path.py (optional)
9. generate_dashboard.py (optional)
10. unittest discovery (optional)

Usage:
    python scripts/run_all.py
    python scripts/run_all.py --skip-update
    python scripts/run_all.py --fetch-character --parse-character --compare-build
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
    parser.add_argument("--list-builds", action="store_true", help="List available target build profiles and continue.")
    parser.add_argument("--switch-build", help="Activate a target build profile before running the flow.")
    parser.add_argument("--builds", help="Run multi-build reports for comma-separated build slugs, all, or active.")
    parser.add_argument("--build-name", help="Name used when creating/updating a build profile.")
    parser.add_argument("--pob-url", help="PoB link/code saved with the build profile.")
    parser.add_argument("--build-from-current", action="store_true", help="Create/update the build profile from current builds/ target files.")
    parser.add_argument("--fetch-pob", action="store_true", help="Ask switch_build.py to save the PoB URL/code content when possible.")
    parser.add_argument("--fetch-character", action="store_true", help="Fetch authenticated character from official GGG API.")
    parser.add_argument("--parse-character", action="store_true", help="Parse data/raw/character_api_raw.json into normalized current files.")
    parser.add_argument("--update-builds", action="store_true", help="When parsing character, also copy player_items/player_stats into builds/.")
    parser.add_argument("--backup-builds", action="store_true", help="When parsing character with --update-builds, create .bak files before overwriting planner inputs.")
    parser.add_argument("--compare-build", action="store_true", help="Generate data/generated/gap_analysis from current/build target files.")
    parser.add_argument("--recommend-next", action="store_true", help="Generate next_searches and upgrade_recommendations from gap_analysis.")
    parser.add_argument("--upgrade-plan", action="store_true", help="Also run plan_upgrade_path.py after market/filter reports.")
    parser.add_argument("--dashboard", action="store_true", help="Generate data/generated/build_dashboard.html.")
    parser.add_argument("--run-tests", action="store_true", help="Run toolkit safety tests after the flow.")
    parser.add_argument("--budget", help="Budget passed to plan_upgrade_path.py, e.g. 251c or 1d. If omitted, planner shows top 3 cheapest safe upgrades.")
    parser.add_argument("--profiles", help="Profiles passed to plan_upgrade_path.py, e.g. rumi_uncorrupted or ring_vulnerability,jewel_damage.")
    parser.add_argument("--top", type=int, help="Top plans passed to plan_upgrade_path.py.")
    parser.add_argument("--max-fetch", type=int, help="Max trade listings per profile for plan_upgrade_path.py.")
    parser.add_argument("--max-combo-size", type=int, help="Max combo size passed to plan_upgrade_path.py.")
    args = parser.parse_args()

    if args.list_builds:
        run_script("switch_build.py", "--list")

    if args.switch_build or args.build_name or args.pob_url:
        switch_args: list[str] = []
        if args.switch_build:
            switch_args.extend(["--switch-to", args.switch_build])
        if args.build_name:
            switch_args.extend(["--name", args.build_name])
        if args.pob_url:
            switch_args.extend(["--pob-url", args.pob_url])
        if args.build_from_current:
            switch_args.append("--from-current")
        if args.fetch_pob:
            switch_args.append("--fetch-pob")
        if not args.switch_build:
            switch_args.append("--activate")
        run_script("switch_build.py", *switch_args)

    if args.builds:
        matrix_args = ["--builds", args.builds]
        if args.budget:
            matrix_args.extend(["--budget", args.budget])
        if args.profiles:
            matrix_args.extend(["--profiles", args.profiles])
        if args.top is not None:
            matrix_args.extend(["--top", str(args.top)])
        if args.max_fetch is not None:
            matrix_args.extend(["--max-fetch", str(args.max_fetch)])
        run_script("run_build_matrix.py", *matrix_args)
        print()
        print("Flow complete.")
        print("- data/generated/multi_build_dashboard.html")
        return 0

    if args.fetch_character:
        run_script("fetch_character.py")

    if args.parse_character or args.fetch_character:
        parse_args = ["--update-builds"] if args.update_builds else []
        if args.backup_builds:
            parse_args.append("--backup-builds")
        run_script("parse_character.py", *parse_args)

    if not args.skip_update:
        run_script("update_market.py")

    run_script("market_report.py")
    run_script("suggest_filter_tiers.py")
    run_script("filter_audit.py")

    if args.compare_build:
        run_script("compare_current_to_target.py")

    if args.recommend_next:
        if not args.compare_build:
            print("Note: --recommend-next uses existing data/generated/gap_analysis.json.")
        run_script("recommend_next_steps.py")

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

    if args.dashboard:
        run_script("generate_dashboard.py")

    if args.run_tests:
        print()
        print("=" * 72)
        print("Running: unittest discover")
        print("=" * 72, flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests")],
            cwd=str(ROOT),
        )
        if result.returncode != 0:
            raise SystemExit(f"Tests failed (exit code {result.returncode})")

    print()
    print("Flow complete.")
    print("Main reports:")
    print("- market/reports/market_report.md")
    print("- market/reports/filter_suggestions.md")
    print("- market/reports/filter_audit.md")
    if args.compare_build:
        print("- data/generated/gap_analysis.md")
        print("- data/generated/gap_analysis.json")
    if args.recommend_next:
        print("- data/generated/next_searches.md")
        print("- data/generated/upgrade_recommendations.md")
        print("- data/generated/upgrade_report.json")
    if args.upgrade_plan:
        print("- market/reports/upgrade_plan.md")
        print("- market/reports/upgrade_plan.html")
        print("- market/reports/upgrade_plan.json")
    if args.dashboard:
        print("- data/generated/build_dashboard.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
