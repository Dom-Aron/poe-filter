#!/usr/bin/env python3
"""
run_all.py

Runs either the official per-character flow, or the market/filter report flow.
Build comparison and upgrade planning must go through --character/--characters
so generated files stay isolated per character.

Usage:
    python scripts/run_all.py
    python scripts/run_all.py --skip-update
    python scripts/run_all.py --character aron_shockwave_cyclone_slayer --budget 1000c
    python scripts/run_all.py --characters all --budget 1000c
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all PoE market toolkit scripts.")
    parser.add_argument("--skip-update", action="store_true", help="Do not fetch the market; use market/latest_market.json.")
    parser.add_argument("--character", help="Official flow: run run_character.py for one saved character profile.")
    parser.add_argument("--characters", help="Official flow: run run_character_matrix.py for comma-separated character slugs or all.")
    parser.add_argument("--list-builds", action="store_true", help="List available target build profiles and continue.")
    parser.add_argument("--switch-build", help="Activate a target build profile before running the flow.")
    parser.add_argument("--switch-character", help="Activate a saved character profile before running the flow.")
    parser.add_argument("--no-switch-character-build", action="store_true", help="When switching character, do not activate its associated build.")
    parser.add_argument("--build-name", help="Name used when creating/updating a build profile.")
    parser.add_argument("--pob-url", help="PoB link/code saved with the build profile.")
    parser.add_argument("--fetch-pob", action="store_true", help="Ask switch_build.py to save the PoB URL/code content when possible.")
    parser.add_argument("--fetch-character", action="store_true", help="Fetch authenticated character from official GGG API.")
    parser.add_argument("--parse-character", action="store_true", help="Parse data/raw/character_api_raw.json into normalized current files.")
    parser.add_argument("--compare-build", action="store_true", help="Deprecated. Use --character so comparison is isolated per character.")
    parser.add_argument("--recommend-next", action="store_true", help="Deprecated. Use --character so recommendations are isolated per character.")
    parser.add_argument("--upgrade-plan", action="store_true", help="Deprecated. Use --character so plans are isolated per character.")
    parser.add_argument("--dashboard", action="store_true", help="Deprecated. Use --character so HTML is isolated per character.")
    parser.add_argument("--run-tests", action="store_true", help="Run toolkit safety tests after the flow.")
    parser.add_argument("--open", action="store_true", help="Open the generated dashboard when using --character.")
    parser.add_argument("--budget", help="Budget passed to plan_upgrade_path.py, e.g. 251c or 1d. If omitted, planner shows top 3 cheapest safe upgrades.")
    parser.add_argument("--profiles", help="Profiles passed to plan_upgrade_path.py, e.g. rumi_uncorrupted or ring_vulnerability,jewel_damage.")
    parser.add_argument("--top", type=int, help="Top plans passed to plan_upgrade_path.py.")
    parser.add_argument("--max-fetch", type=int, help="Max trade listings per profile for plan_upgrade_path.py.")
    parser.add_argument("--max-combo-size", type=int, help="Max combo size passed to plan_upgrade_path.py.")
    parser.add_argument("--fail-on-stale-market", action="store_true", help="Forward to run_character.py.")
    parser.add_argument("--max-market-age-minutes", type=float, help="Forward to run_character.py.")
    parser.add_argument("--fail-on-market-errors", action="store_true", help="Forward to run_character.py.")
    return parser.parse_args()


def character_flow_args(args: argparse.Namespace, slug_option: str, slug_value: str) -> list[str]:
    flow_args = [slug_option, slug_value]
    if args.skip_update:
        flow_args.append("--skip-market-update")
    for option_name, flag in (
        ("budget", "--budget"),
        ("profiles", "--profiles"),
        ("top", "--top"),
        ("max_fetch", "--max-fetch"),
        ("max_combo_size", "--max-combo-size"),
        ("max_market_age_minutes", "--max-market-age-minutes"),
    ):
        value = getattr(args, option_name)
        if value is not None:
            flow_args.extend([flag, str(value)])
    for option_name, flag in (
        ("fail_on_stale_market", "--fail-on-stale-market"),
        ("fail_on_market_errors", "--fail-on-market-errors"),
    ):
        if getattr(args, option_name):
            flow_args.append(flag)
    return flow_args


def run_character_flow(args: argparse.Namespace) -> bool:
    if args.character:
        character_args = character_flow_args(args, "--character", args.character)
        if args.open:
            character_args.append("--open")
        run_script("run_character.py", *character_args)
        return True
    if args.characters:
        run_script("run_character_matrix.py", *character_flow_args(args, "--characters", args.characters))
        return True
    return False


def run_switch_flow(args: argparse.Namespace) -> None:
    if args.list_builds:
        run_script("switch_build.py", "--list")

    if args.switch_character:
        character_args = ["--switch-character", args.switch_character]
        if args.no_switch_character_build:
            character_args.append("--no-switch-character-build")
        run_script("switch_build.py", *character_args)

    if args.switch_build or args.build_name or args.pob_url:
        switch_args: list[str] = []
        if args.switch_build:
            switch_args.extend(["--switch-to", args.switch_build])
        if args.build_name:
            switch_args.extend(["--name", args.build_name])
        if args.pob_url:
            switch_args.extend(["--pob-url", args.pob_url])
        if args.fetch_pob:
            switch_args.append("--fetch-pob")
        run_script("switch_build.py", *switch_args)


def run_market_flow(args: argparse.Namespace) -> None:
    if args.fetch_character:
        run_script("fetch_character.py")
    if args.parse_character or args.fetch_character:
        run_script("parse_character.py")
    if not args.skip_update:
        run_script("update_market.py")
    run_script("market_report.py")
    run_script("suggest_filter_tiers.py")
    run_script("filter_audit.py")


def run_tests_if_requested(args: argparse.Namespace) -> None:
    if not args.run_tests:
        return
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


def print_summary() -> None:
    print()
    print("Flow complete.")
    print("Main reports:")
    print("- market/reports/market_report.md")
    print("- market/reports/filter_suggestions.md")
    print("- market/reports/filter_audit.md")


def main() -> int:
    args = parse_args()
    if args.compare_build or args.recommend_next or args.upgrade_plan or args.dashboard:
        raise SystemExit(
            "Global compare/recommend/upgrade/dashboard flags were removed from run_all.py. "
            "Use --character <slug> or --characters all so reports are generated per character."
        )

    if run_character_flow(args):
        return 0

    run_switch_flow(args)
    run_market_flow(args)
    run_tests_if_requested(args)
    print_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
