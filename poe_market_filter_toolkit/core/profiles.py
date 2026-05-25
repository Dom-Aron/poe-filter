"""Character/build profile helpers."""

from __future__ import annotations

from typing import Any

from . import paths
from .io import read_json, required_file, write_json
from .time_utils import utc_now_iso


PLAYER_FILES = ("player_items.json", "player_stats.json")
TARGET_FILES = ("target_build_items.json", "target_build_stats.json", "upgrade_rules.json")


def profile_path(character_slug: str):
    return paths.character_dir(character_slug) / "character_profile.json"


def load_character_profile(character_slug: str) -> dict[str, Any]:
    path = profile_path(character_slug)
    if not path.exists():
        raise SystemExit(f"Character profile not found: {character_slug}. Expected: {path}")
    profile = read_json(path)
    build_slug = str(profile.get("build_slug") or "")
    if not build_slug:
        raise SystemExit(f"Character profile has no build_slug: {path}")
    return profile


def load_build_profile(build_slug: str) -> dict[str, Any]:
    path = paths.build_dir(build_slug) / "build_profile.json"
    if not path.exists():
        raise SystemExit(f"Build profile not found: {build_slug}. Expected: {path}")
    return read_json(path)


def character_file(character_slug: str, filename: str):
    return required_file(paths.character_dir(character_slug) / filename, f"character {filename}")


def build_file(build_slug: str, filename: str):
    return required_file(paths.build_dir(build_slug) / filename, f"build {filename}")


def character_payload(character_slug: str, profile: dict[str, Any], build_slug: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "active_slug": character_slug,
        "slug": character_slug,
        "name": profile.get("name", character_slug),
        "build_slug": build_slug,
        "notes": profile.get("notes", ""),
        "active_character_dir": paths.rel(paths.character_dir(character_slug)),
        "activated_at": utc_now_iso(),
        "source": "run_character.py",
    }


def build_payload(build_slug: str, profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "active_slug": build_slug,
        "slug": build_slug,
        "name": profile.get("name", build_slug),
        "pob": profile.get("pob", {}),
        "notes": profile.get("notes", ""),
        "active_profile_dir": paths.rel(paths.build_dir(build_slug)),
        "activated_at": utc_now_iso(),
        "source": "run_character.py",
    }


def write_active_metadata(character_slug: str, character_profile: dict[str, Any], build_slug: str, build_profile: dict[str, Any]) -> None:
    destination = paths.character_output_dir(character_slug)
    write_json(destination / "active_character.json", character_payload(character_slug, character_profile, build_slug))
    write_json(destination / "active_build.json", build_payload(build_slug, build_profile))
