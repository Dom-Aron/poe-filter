#!/usr/bin/env python3
"""
run_character.py

Orchestrates the full build-agent flow for one saved character profile.

The character is the unit of work: its current files and associated target
build are read directly from their profile folders, while generated reports,
upgrade plans and HTML pages are written to
data/generated/characters/<character_slug>/ so different characters do not
share final artifacts.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLKIT_ROOT))

from core import paths
from core.io import copy_if_exists, read_json, write_json
from core.profiles import PLAYER_FILES, TARGET_FILES, build_file, load_build_profile, load_character_profile, character_file, write_active_metadata


def run_script(script_name: str, *args: str, keep_going: bool = False) -> bool:
    command = [sys.executable, str(paths.SCRIPTS / script_name), *args]
    print()
    print("=" * 72)
    print("Running:", " ".join([script_name, *args]))
    print("=" * 72, flush=True)
    result = subprocess.run(command, cwd=str(paths.ROOT))
    if result.returncode != 0:
        if keep_going:
            print(f"[warning] Script failed but flow continues: {script_name} (exit code {result.returncode})")
            return False
        raise SystemExit(f"Script failed: {script_name} (exit code {result.returncode})")
    return True

def update_character_from_api(character_slug: str, character_name: str | None, realm: str | None) -> None:
    raw = paths.character_dir(character_slug) / "raw" / "character_api_raw.json"
    args: list[str] = ["--output", str(raw)]
    if character_name:
        args.extend(["--character-name", character_name])
    if realm:
        args.extend(["--realm", realm])
    run_script("fetch_character.py", *args)


def parse_character_into_profile(character_slug: str, keep_manual_stats: bool) -> None:
    profile_dir = paths.character_dir(character_slug)
    raw = profile_dir / "raw" / "character_api_raw.json"
    parsed = profile_dir / "parsed"
    run_script("parse_character.py", "--input", str(raw), "--output-dir", str(parsed))
    copy_if_exists(parsed / "player_items.json", profile_dir / "player_items.json")
    parsed_stats = parsed / "player_stats.json"
    target_stats = profile_dir / "player_stats.json"
    if keep_manual_stats and target_stats.exists():
        print("Keeping existing player_stats.json because API-derived stats are incomplete.")
    else:
        copy_if_exists(parsed_stats, target_stats)
    for extra in ("player_passives.json", "player_skills.json"):
        copy_if_exists(parsed / extra, profile_dir / extra)

def copy_character_inputs(character_slug: str, build_slug: str) -> None:
    destination = paths.character_output_dir(character_slug)
    destination.mkdir(parents=True, exist_ok=True)

    char_dir = paths.character_dir(character_slug)
    for filename in ("character_profile.json", *PLAYER_FILES, "player_passives.json", "player_skills.json"):
        copy_if_exists(char_dir / filename, destination / "character" / filename)

    profile_dir = paths.build_dir(build_slug)
    for filename in ("build_profile.json", *TARGET_FILES):
        copy_if_exists(profile_dir / filename, destination / "build" / filename)


def remove_stale_outputs(character_slug: str, names: tuple[str, ...]) -> None:
    destination = paths.character_output_dir(character_slug)
    for name in names:
        path = destination / name
        if path.exists():
            path.unlink()


def copy_reports(character_slug: str, include_filter_reports: bool) -> None:
    destination = paths.character_output_dir(character_slug)
    files = [
        paths.REPORTS / "market_report.md",
        paths.REPORTS / "market_report.csv",
        paths.MARKET / "latest_market.json",
    ]
    if include_filter_reports:
        files.extend([paths.REPORTS / "filter_suggestions.md", paths.REPORTS / "filter_audit.md"])
    else:
        remove_stale_outputs(character_slug, ("filter_suggestions.md", "filter_audit.md"))
    for source in files:
        copy_if_exists(source, destination / source.name)


def render_character_pages(character_slug: str) -> None:
    destination = paths.character_output_dir(character_slug)
    run_script(
        "generate_dashboard.py",
        "--validation-report",
        str(destination / "validation_report.json"),
        "--gap",
        str(destination / "gap_analysis.json"),
        "--upgrade-report",
        str(destination / "upgrade_report.json"),
        "--next-searches",
        str(destination / "next_searches.md"),
        "--recommendations",
        str(destination / "upgrade_recommendations.md"),
        "--upgrade-plan",
        str(destination / "upgrade_plan.md"),
        "--upgrade-plan-json",
        str(destination / "upgrade_plan.json"),
        "--market-report",
        str(destination / "market_report.md"),
        "--market-json",
        str(destination / "latest_market.json"),
        "--active-build",
        str(destination / "active_build.json"),
        "--active-character",
        str(destination / "active_character.json"),
        "--output",
        str(destination / "build_dashboard.html"),
    )


def open_dashboard(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def write_run_summary(character_slug: str, budget: str | None, steps: list[str]) -> None:
    destination = paths.character_output_dir(character_slug)
    summary = {
        "schema_version": 1,
        "character_slug": character_slug,
        "active_character": read_json(destination / "active_character.json"),
        "active_build": read_json(destination / "active_build.json"),
        "budget": budget or "no budget",
        "steps": steps,
        "dashboard": str((destination / "build_dashboard.html").relative_to(paths.ROOT)).replace("\\", "/"),
    }
    write_json(destination / "run_summary.json", summary)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full isolated flow for one character.")
    parser.add_argument("--character", required=True, help="Saved character slug.")
    parser.add_argument("--character-name", help="Official API character name when fetching current data.")
    parser.add_argument("--realm", help="Official API realm, usually pc.")
    parser.add_argument("--fetch-character", action="store_true", help="Fetch current character data from the official API into the character profile.")
    parser.add_argument("--parse-character", action="store_true", help="Parse fetched raw API data into the character profile.")
    parser.add_argument("--overwrite-manual-stats", action="store_true", help="Allow API parsing to replace player_stats.json even though derived stats are incomplete.")
    parser.add_argument("--skip-market-update", action="store_true", help="Use existing market/latest_market.json instead of updating market data.")
    parser.add_argument("--skip-market-report", action="store_true", help="Use existing market/reports/market_report.* instead of rebuilding the report.")
    parser.add_argument("--skip-filter-reports", action="store_true", help="Do not run filter-oriented reports.")
    parser.add_argument("--skip-upgrade-plan", action="store_true", help="Skip trade searches and only refresh gaps/recommendations/dashboard.")
    parser.add_argument("--skip-validation", action="store_true", help="Skip local character/build validation before running.")
    parser.add_argument("--strict-validation", action="store_true", help="Treat validation warnings as failures.")
    parser.add_argument("--budget", help="Budget per upgrade plan, e.g. 1000c or 2d.")
    parser.add_argument("--profiles", default="all", help="Trade profiles passed to plan_upgrade_path.py.")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--max-fetch", type=int, default=30)
    parser.add_argument("--max-combo-size", type=int)
    parser.add_argument("--request-delay", type=float, help="Seconds to wait between trade API requests.")
    parser.add_argument(
        "--best-any-budget-mode",
        choices=("reuse", "extra", "off"),
        default="reuse",
        help="Use 'reuse' to avoid extra trade API calls, 'extra' to force no-budget searches, or 'off'.",
    )
    parser.add_argument("--open", action="store_true", help="Open the generated character dashboard in the browser.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    character_slug = args.character
    character_profile = load_character_profile(character_slug)
    build_slug = str(character_profile["build_slug"])
    build_profile = load_build_profile(build_slug)

    steps: list[str] = []
    paths.character_output_dir(character_slug).mkdir(parents=True, exist_ok=True)
    write_active_metadata(character_slug, character_profile, build_slug, build_profile)
    steps.append("load_character_and_associated_build")

    if args.fetch_character:
        update_character_from_api(character_slug, args.character_name, args.realm)
        steps.append("fetch_character_api")
    if args.parse_character or args.fetch_character:
        parse_character_into_profile(character_slug, keep_manual_stats=not args.overwrite_manual_stats)
        steps.append("parse_character_into_profile")

    if not args.skip_validation:
        validation_args = [
            "--character",
            character_slug,
            "--output",
            str(paths.character_output_dir(character_slug) / "validation_report.json"),
        ]
        if args.strict_validation:
            validation_args.append("--strict")
        run_script("validate_character.py", *validation_args)
        steps.append("validate_character")

    if not args.skip_market_update:
        run_script("update_market.py")
        steps.append("update_market")

    if not args.skip_market_report:
        run_script("market_report.py")
        steps.append("market_report")
    else:
        steps.append("reuse_market_report")

    if not args.skip_filter_reports:
        run_script("suggest_filter_tiers.py")
        run_script("filter_audit.py")
        steps.append("filter_reports")

    destination = paths.character_output_dir(character_slug)
    player_items = character_file(character_slug, "player_items.json")
    player_stats = character_file(character_slug, "player_stats.json")
    target_items = build_file(build_slug, "target_build_items.json")
    target_stats = build_file(build_slug, "target_build_stats.json")
    upgrade_rules = build_file(build_slug, "upgrade_rules.json")
    active_build = destination / "active_build.json"
    active_character = destination / "active_character.json"

    run_script(
        "compare_current_to_target.py",
        "--player-items",
        str(player_items),
        "--player-stats",
        str(player_stats),
        "--target-stats",
        str(target_stats),
        "--rules",
        str(upgrade_rules),
        "--output-json",
        str(destination / "gap_analysis.json"),
        "--output-md",
        str(destination / "gap_analysis.md"),
    )
    run_script(
        "recommend_next_steps.py",
        "--gap",
        str(destination / "gap_analysis.json"),
        "--rules",
        str(upgrade_rules),
        "--next-searches",
        str(destination / "next_searches.md"),
        "--recommendations",
        str(destination / "upgrade_recommendations.md"),
        "--report-json",
        str(destination / "upgrade_report.json"),
        "--active-build",
        str(active_build),
        "--active-character",
        str(active_character),
    )
    steps.append("gap_and_recommendations")

    if not args.skip_upgrade_plan:
        plan_args: list[str] = [
            "--top",
            str(args.top),
            "--max-fetch",
            str(args.max_fetch),
            "--player-items",
            str(player_items),
            "--player-stats",
            str(player_stats),
            "--target-items",
            str(target_items),
            "--target-stats",
            str(target_stats),
            "--rules",
            str(upgrade_rules),
            "--active-build",
            str(active_build),
            "--output-md",
            str(destination / "upgrade_plan.md"),
            "--output-html",
            str(destination / "upgrade_plan.html"),
            "--output-json",
            str(destination / "upgrade_plan.json"),
        ]
        if args.budget:
            plan_args.extend(["--budget", args.budget])
        if args.profiles:
            plan_args.extend(["--profiles", args.profiles])
        if args.max_combo_size is not None:
            plan_args.extend(["--max-combo-size", str(args.max_combo_size)])
        if args.request_delay is not None:
            plan_args.extend(["--request-delay", str(args.request_delay)])
        if args.best_any_budget_mode:
            plan_args.extend(["--best-any-budget-mode", args.best_any_budget_mode])
        run_script("plan_upgrade_path.py", *plan_args)
        steps.append("trade_upgrade_plan")
    else:
        remove_stale_outputs(character_slug, ("upgrade_plan.md", "upgrade_plan.json", "upgrade_plan.html"))

    copy_character_inputs(character_slug, build_slug)
    copy_reports(character_slug, include_filter_reports=not args.skip_filter_reports)
    render_character_pages(character_slug)
    write_run_summary(character_slug, args.budget, steps)

    dashboard = paths.character_output_dir(character_slug) / "build_dashboard.html"
    print()
    print("Character flow complete.")
    print(f"Character: {character_slug}")
    print(f"Build: {build_slug}")
    print(f"Dashboard: {dashboard}")
    if args.open:
        open_dashboard(dashboard)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
