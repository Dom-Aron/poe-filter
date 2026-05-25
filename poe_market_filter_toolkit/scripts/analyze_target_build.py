#!/usr/bin/env python3
"""
analyze_target_build.py

Derives generic target requirements from a saved build profile.

Use this when a profile already has target_build_items.json/target_build_stats.json
and you want to refresh target_requirements.json without re-importing a PoB file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import target_analysis


PROFILES_DIR = ROOT / "builds" / "profiles"


def read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return fallback or {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def stats_doc_from_target_stats(target_stats: dict[str, Any]) -> dict[str, Any]:
    goals = target_stats.get("goals", {}) if isinstance(target_stats.get("goals"), dict) else {}
    return {
        "schema_version": 1,
        "source": target_stats.get("source", "target_build_stats"),
        "updated": target_stats.get("updated"),
        "stats": goals,
    }


def explicit_minimums(target_stats: dict[str, Any]) -> dict[str, Any]:
    minimums = target_stats.get("minimums", {}) if isinstance(target_stats.get("minimums"), dict) else {}
    return {str(key): value for key, value in minimums.items() if isinstance(value, (int, float))}


def analyze_build(build_slug: str, update_stats: bool = False) -> dict[str, Any]:
    profile_dir = PROFILES_DIR / build_slug
    if not profile_dir.exists():
        raise SystemExit(f"Build profile not found: {profile_dir}")

    target_stats = read_json(profile_dir / "target_build_stats.json")
    target_items = read_json(profile_dir / "target_build_items.json", {"items": {}})
    target_skills = read_json(profile_dir / "target_build_skills.json", {"skill_groups": []})

    requirements = target_analysis.build_target_requirements(
        stats_doc_from_target_stats(target_stats),
        target_items,
        target_skills,
    )
    requirements["source"] = "saved_build_profile"
    requirements["build_slug"] = build_slug
    requirements["minimums"] = {
        **requirements.get("minimums", {}),
        **explicit_minimums(target_stats),
    }
    write_json(profile_dir / "target_requirements.json", requirements)

    if update_stats:
        write_json(profile_dir / "target_build_stats.json", target_analysis.target_stats_from_requirements(requirements))

    return requirements


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate target_requirements.json for a saved build profile.")
    parser.add_argument("--build", required=True, help="Build profile slug.")
    parser.add_argument("--update-stats", action="store_true", help="Also rewrite target_build_stats.json using inferred safe minimums.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    requirements = analyze_build(args.build, update_stats=args.update_stats)
    print(f"Target requirements saved for: {args.build}")
    print(f"- goals: {len(requirements.get('goals', {}))}")
    print(f"- slots: {len(requirements.get('slot_requirements', {}))}")
    print(f"- skills: {len(requirements.get('skill_requirements', []))}")
    print(f"- output: {PROFILES_DIR / args.build / 'target_requirements.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
