#!/usr/bin/env python3
"""
switch_build.py

Manages target build and character profiles for the build agent.

Each target profile lives in builds/profiles/<slug>/ and each character profile
lives in builds/characters/<slug>/. The official execution flow is
run_character.py, which reads those folders directly and writes isolated output
under data/generated/characters/<character_slug>/.

This script intentionally avoids copying profile JSON files into builds/. It may
write active metadata for CLI convenience, but that metadata is not a source of
truth for the character flow.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
BUILDS_DIR = ROOT / "builds"
PROFILES_DIR = BUILDS_DIR / "profiles"
CHARACTER_PROFILES_DIR = BUILDS_DIR / "characters"
ACTIVE_BUILD = BUILDS_DIR / "active_build.json"
ACTIVE_CHARACTER = BUILDS_DIR / "active_character.json"
TARGET_FILES = ("target_build_items.json", "target_build_stats.json", "upgrade_rules.json")
PLAYER_FILES = ("player_items.json", "player_stats.json")
POB_USER_AGENT = "poe-market-filter-toolkit/1.0 (+personal build profile switcher)"


def now_label() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return cleaned or "build"


def detect_pob_reference(raw: str) -> dict[str, str]:
    value = raw.strip()
    if not value:
        return {"kind": "manual", "value": ""}
    pobb = re.search(r"pobb\.in/([A-Za-z0-9_-]+)", value)
    if pobb:
        return {"kind": "pobb.in", "value": value, "id": pobb.group(1)}
    pastebin = re.search(r"pastebin\.com/(?:raw/)?([A-Za-z0-9]+)", value)
    if pastebin:
        return {"kind": "pastebin", "value": value, "id": pastebin.group(1)}
    if value.startswith("http://") or value.startswith("https://"):
        return {"kind": "url", "value": value}
    return {"kind": "pob_code", "value": value}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def profile_dir(slug: str) -> Path:
    return PROFILES_DIR / slugify(slug)


def existing_profile_slugs() -> list[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(path.name for path in PROFILES_DIR.iterdir() if path.is_dir())


def existing_character_slugs() -> list[str]:
    if not CHARACTER_PROFILES_DIR.exists():
        return []
    return sorted(path.name for path in CHARACTER_PROFILES_DIR.iterdir() if path.is_dir())


def build_profile_payload(name: str, slug: str, pob_url: str = "", notes: str = "") -> dict[str, Any]:
    pob = detect_pob_reference(pob_url)
    return {
        "schema_version": 1,
        "slug": slug,
        "name": name,
        "pob": pob,
        "notes": notes,
        "files": {name: name for name in TARGET_FILES},
        "created_at": now_label(),
        "updated_at": now_label(),
    }


def create_profile(
    name: str,
    pob_url: str,
    notes: str = "",
    fetch_pob: bool = False,
    timeout: int = 30,
) -> Path:
    slug = slugify(name or detect_pob_reference(pob_url).get("id", "build"))
    target = profile_dir(slug)
    target.mkdir(parents=True, exist_ok=True)

    profile_file = target / "build_profile.json"
    if profile_file.exists():
        profile = read_json(profile_file)
        if pob_url:
            profile["pob"] = detect_pob_reference(pob_url)
        if name:
            profile["name"] = name
        if notes:
            profile["notes"] = notes
        profile["updated_at"] = now_label()
    else:
        profile = build_profile_payload(name or slug, slug, pob_url, notes)

    missing = [filename for filename in TARGET_FILES if not (target / filename).exists()]
    if missing:
        profile["target_files_status"] = "incomplete"
        profile["target_files_missing"] = missing
    else:
        profile["target_files_status"] = "ready"
        profile.pop("target_files_missing", None)

    if fetch_pob and pob_url:
        fetch_pob_source(pob_url, target / "pob_source.txt", timeout)

    write_json(profile_file, profile)
    return target


def fetch_pob_source(url: str, output: Path, timeout: int) -> None:
    reference = detect_pob_reference(url)
    value = reference.get("value", url)
    if not value.startswith(("http://", "https://")):
        output.write_text(value, encoding="utf-8")
        return
    request = Request(value, headers={"User-Agent": POB_USER_AGENT, "Accept": "text/plain, text/html, */*"})
    try:
        with urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Failed to fetch PoB URL: HTTP {exc.code}: {detail[:500]}") from exc
    except (URLError, TimeoutError) as exc:
        raise SystemExit(f"Failed to fetch PoB URL: {exc}") from exc
    output.write_text(text, encoding="utf-8")


def activate_profile(slug: str) -> dict[str, Any]:
    slug = slugify(slug)
    source_dir = profile_dir(slug)
    if not source_dir.exists():
        raise SystemExit(f"Build profile not found: {slug}. Use --list to see available profiles.")

    missing = [filename for filename in TARGET_FILES if not (source_dir / filename).exists()]
    if missing:
        raise SystemExit(f"Build profile {slug} is incomplete. Missing: {', '.join(missing)}")

    profile = read_json(source_dir / "build_profile.json")
    active = {
        "schema_version": 1,
        "active_slug": slug,
        "active_profile_dir": str(source_dir.relative_to(ROOT)).replace("\\", "/"),
        "name": profile.get("name", slug),
        "pob": profile.get("pob", {}),
        "activated_at": now_label(),
    }
    write_json(ACTIVE_BUILD, active)
    return active


def remove_directory(path: Path) -> None:
    resolved = path.resolve()
    allowed_roots = [PROFILES_DIR.resolve(), CHARACTER_PROFILES_DIR.resolve()]
    if not any(resolved == root or root in resolved.parents for root in allowed_roots):
        raise SystemExit(f"Refusing to remove path outside managed profile dirs: {path}")
    shutil.rmtree(resolved)


def delete_build_profile(slug: str, force: bool = False) -> Path:
    slug = slugify(slug)
    target = profile_dir(slug)
    if not target.exists():
        raise SystemExit(f"Build profile not found: {slug}")
    active_slug = read_json(ACTIVE_BUILD).get("active_slug")
    if active_slug == slug and not force:
        raise SystemExit(
            f"Build profile is active: {slug}. Switch to another build first or pass --force."
        )
    remove_directory(target)
    if active_slug == slug:
        ACTIVE_BUILD.unlink(missing_ok=True)
    return target


def character_profile_dir(slug: str) -> Path:
    return CHARACTER_PROFILES_DIR / slugify(slug)


def create_character_profile(name: str, notes: str = "") -> Path:
    slug = slugify(name)
    target = character_profile_dir(slug)
    target.mkdir(parents=True, exist_ok=True)
    missing = [filename for filename in PLAYER_FILES if not (target / filename).exists()]
    if missing:
        raise SystemExit(
            "Character profile files are missing: "
            + ", ".join(missing)
            + ". Create/import player_items.json and player_stats.json inside this character profile."
        )
    write_json(
        target / "character_profile.json",
        {
            "schema_version": 1,
            "slug": slug,
            "name": name,
            "notes": notes,
            "build_slug": "",
            "files": {name: name for name in PLAYER_FILES},
            "updated_at": now_label(),
        },
    )
    return target


def activate_character_profile(slug: str) -> Path:
    slug = slugify(slug)
    source_dir = character_profile_dir(slug)
    if not source_dir.exists():
        raise SystemExit(f"Character profile not found: {slug}")
    missing = [filename for filename in PLAYER_FILES if not (source_dir / filename).exists()]
    if missing:
        raise SystemExit(f"Character profile {slug} is incomplete. Missing: {', '.join(missing)}")
    profile = read_json(source_dir / "character_profile.json")
    active = {
        "schema_version": 1,
        "active_slug": slug,
        "active_character_dir": str(source_dir.relative_to(ROOT)).replace("\\", "/"),
        "name": profile.get("name", slug),
        "build_slug": profile.get("build_slug", ""),
        "activated_at": now_label(),
    }
    write_json(ACTIVE_CHARACTER, active)
    return source_dir


def set_character_build(character_slug: str, build_slug: str) -> Path:
    character_slug = slugify(character_slug)
    build_slug = slugify(build_slug)
    if not profile_dir(build_slug).exists():
        raise SystemExit(f"Build profile not found: {build_slug}")
    target = character_profile_dir(character_slug)
    if not target.exists():
        raise SystemExit(f"Character profile not found: {character_slug}")
    profile_file = target / "character_profile.json"
    profile = read_json(profile_file)
    profile["build_slug"] = build_slug
    profile["updated_at"] = now_label()
    write_json(profile_file, profile)
    return target


def delete_character_profile(slug: str) -> Path:
    slug = slugify(slug)
    target = character_profile_dir(slug)
    if not target.exists():
        raise SystemExit(f"Character profile not found: {slug}")
    remove_directory(target)
    return target


def list_profiles() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    active = read_json(ACTIVE_BUILD).get("active_slug")
    for slug in existing_profile_slugs():
        profile = read_json(profile_dir(slug) / "build_profile.json")
        rows.append(
            {
                "slug": slug,
                "name": profile.get("name", slug),
                "pob": profile.get("pob", {}).get("value", ""),
                "active": slug == active,
            }
        )
    return rows


def list_character_profiles() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for slug in existing_character_slugs():
        profile = read_json(character_profile_dir(slug) / "character_profile.json")
        rows.append(
            {
                "slug": slug,
                "name": profile.get("name", slug),
                "build_slug": profile.get("build_slug", ""),
                "notes": profile.get("notes", ""),
            }
        )
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create, list and activate target build profiles.")
    parser.add_argument("--list", action="store_true", help="List available build profiles.")
    parser.add_argument("--list-characters", action="store_true", help="List saved current-character profiles.")
    parser.add_argument("--switch-to", help="Activate an existing profile slug, or create it when --name/--pob-url are provided.")
    parser.add_argument("--delete-build", help="Delete a target build profile by slug.")
    parser.add_argument("--force", action="store_true", help="Allow deleting the active build profile.")
    parser.add_argument("--name", help="Human-readable build name when creating/updating a profile.")
    parser.add_argument("--pob-url", help="Path of Building link/code to store with the profile.")
    parser.add_argument("--activate", action="store_true", help="Activate the created or updated profile.")
    parser.add_argument("--notes", default="", help="Short free-form notes saved in build_profile.json.")
    parser.add_argument("--fetch-pob", action="store_true", help="Save the PoB URL/code content to pob_source.txt when possible.")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--create-character", help="Create/update a saved current-character profile.")
    parser.add_argument("--switch-character", help="Activate a saved current-character profile.")
    parser.add_argument("--character-build", help="Build slug to associate with --create-character or --switch-character.")
    parser.add_argument("--set-character-build", nargs=2, metavar=("CHARACTER", "BUILD"), help="Associate an existing character profile with a build profile.")
    parser.add_argument("--no-switch-character-build", action="store_true", help="When switching character, do not activate its associated build.")
    parser.add_argument("--delete-character", help="Delete a saved current-character profile.")
    return parser.parse_args(argv)


def handle_character_commands(args: argparse.Namespace) -> bool:
    if args.delete_build:
        deleted = delete_build_profile(args.delete_build, force=args.force)
        print(f"Deleted build profile: {deleted}")
        return True

    if args.create_character:
        created = create_character_profile(args.create_character, args.notes)
        if args.character_build:
            set_character_build(args.create_character, args.character_build)
        print(f"Character profile saved: {created}")
        return True

    if args.switch_character:
        activated = activate_character_profile(args.switch_character)
        print(f"Active character files loaded from: {activated}")
        profile = read_json(activated / "character_profile.json")
        build_slug = args.character_build or profile.get("build_slug")
        if build_slug and not args.no_switch_character_build:
            active = activate_profile(str(build_slug))
            print(f"Associated build activated: {active['active_slug']} ({active['name']})")
        return True

    if args.set_character_build:
        character_slug, build_slug = args.set_character_build
        updated = set_character_build(character_slug, build_slug)
        print(f"Character build association saved: {updated}")
        return True

    if args.delete_character:
        deleted = delete_character_profile(args.delete_character)
        print(f"Deleted character profile: {deleted}")
        return True
    return False


def show_requested_lists(args: argparse.Namespace) -> bool:
    if args.list_characters:
        rows = list_character_profiles()
        if not rows:
            print("No character profiles found.")
        for row in rows:
            note = f" | {row['notes']}" if row.get("notes") else ""
            build = f" | build={row['build_slug']}" if row.get("build_slug") else ""
            print(f"  {row['slug']} | {row['name']}{build}{note}")
        if not args.list and not args.switch_to and not args.name and not args.pob_url:
            return True

    if args.list:
        rows = list_profiles()
        if not rows:
            print("No build profiles found.")
        for row in rows:
            marker = "*" if row["active"] else " "
            print(f"{marker} {row['slug']} | {row['name']} | {row['pob']}")
        if not args.switch_to and not args.name and not args.pob_url:
            return True
    return False


def create_or_select_build(args: argparse.Namespace) -> str:
    selected_slug = ""
    if args.name or args.pob_url:
        profile_path = create_profile(
            name=args.name or args.switch_to or "",
            pob_url=args.pob_url or "",
            notes=args.notes,
            fetch_pob=args.fetch_pob,
            timeout=args.timeout,
        )
        selected_slug = profile_path.name
        print(f"Build profile saved: {profile_path}")
        profile = read_json(profile_path / "build_profile.json")
        missing = profile.get("target_files_missing", [])
        if missing:
            print(
                "Note: build profile is registered but incomplete. Missing target files: "
                + ", ".join(str(name) for name in missing)
            )
    if args.switch_to:
        selected_slug = slugify(args.switch_to)
    return selected_slug


def activate_selected_build(args: argparse.Namespace, selected_slug: str) -> bool:
    if args.activate or args.switch_to:
        if not selected_slug:
            raise SystemExit("Use --switch-to or --name/--pob-url with --activate.")
        active = activate_profile(selected_slug)
        print(f"Active build: {active['active_slug']} ({active['name']})")
        print(f"Active metadata: {ACTIVE_BUILD}")
        return True
    return False


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if handle_character_commands(args):
        return 0
    if show_requested_lists(args):
        return 0

    selected_slug = create_or_select_build(args)
    if activate_selected_build(args, selected_slug):
        return 0

    if not args.list and not selected_slug:
        raise SystemExit("Nothing to do. Use --list, --switch-to, or --name/--pob-url.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
