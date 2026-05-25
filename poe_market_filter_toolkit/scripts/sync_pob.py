#!/usr/bin/env python3
"""
sync_pob.py

Imports local Path of Building data into the repository JSON files.

Supported inputs:
- Path of Building XML files saved locally.
- Files containing an exported PoB code.
- Raw exported PoB code passed directly with --source.

This script intentionally does not use Path of Exile credentials, cookies, or
OAuth. It treats PoB as the trusted local source for calculated stats.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import zlib
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from xml.etree import ElementTree as ET

from parse_character import normalize_mods


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import target_analysis

BUILDS_DIR = ROOT / "builds"
PROFILES_DIR = BUILDS_DIR / "profiles"
CHARACTERS_DIR = BUILDS_DIR / "characters"
RAW_DIR = ROOT / "data" / "raw"


STAT_MAP = {
    "Life": "life",
    "EnergyShield": "energy_shield",
    "Mana": "mana",
    "TotalEHP": "ehp",
    "TotalDPS": "total_dps",
    "CombinedDPS": "combined_dps",
    "FullDPS": "full_dps",
    "Speed": "attack_rate",
    "HitChance": "chance_to_hit",
    "CritChance": "critical_strike_chance",
    "CritMultiplier": "crit_multiplier",
    "MainHandAccuracy": "accuracy",
    "Armour": "armour",
    "Evasion": "evasion",
    "PhysicalDamageReduction": "physical_damage_reduction",
    "EffectiveBlockChance": "attack_block",
    "EffectiveSpellBlockChance": "spell_block",
    "EffectiveSpellSuppressionChance": "spell_suppression",
    "FireResist": "fire_resistance",
    "ColdResist": "cold_resistance",
    "LightningResist": "lightning_resistance",
    "ChaosResist": "chaos_resistance",
    "FireResistOverCap": "fire_resistance_overcap",
    "ColdResistOverCap": "cold_resistance_overcap",
    "LightningResistOverCap": "lightning_resistance_overcap",
    "ChaosResistOverCap": "chaos_resistance_overcap",
    "PhysicalMaximumHitTaken": "physical_max_hit",
    "FireMaximumHitTaken": "fire_max_hit",
    "ColdMaximumHitTaken": "cold_max_hit",
    "LightningMaximumHitTaken": "lightning_max_hit",
    "ChaosMaximumHitTaken": "chaos_max_hit",
}


SLOT_MAP = {
    "Weapon 1": "weapon",
    "Weapon 2": "offhand",
    "Weapon 1 Swap": "weapon_swap",
    "Weapon 2 Swap": "offhand_swap",
    "Weapon Swap 1": "weapon_swap",
    "Weapon Swap 2": "offhand_swap",
    "Helmet": "helmet",
    "Helm": "helmet",
    "Body Armour": "body_armour",
    "BodyArmour": "body_armour",
    "Gloves": "gloves",
    "Boots": "boots",
    "Belt": "belt",
    "Amulet": "amulet",
    "Ring 1": "ring_1",
    "Ring 2": "ring_2",
    "Flask 1": "flask_1",
    "Flask 2": "flask_2",
    "Flask 3": "flask_3",
    "Flask 4": "flask_4",
    "Flask 5": "flask_5",
    "Belt Abyssal Socket 1": "abyss_jewel_1",
    "Belt Abyssal Socket 2": "abyss_jewel_2",
}


def read_text_source(source: str) -> tuple[str, str]:
    path = Path(source).expanduser()
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace"), str(path)
    return source.strip(), "inline_pob_code"


def save_pob_code(path: Path, code: str) -> Path:
    cleaned = re.sub(r"\s+", "", code.strip())
    if not cleaned:
        raise SystemExit("PoB code is empty.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cleaned + "\n", encoding="utf-8")
    return path


def read_pob_code_from_stdin() -> str:
    print("Cole o codigo exportado do Path of Building abaixo.")
    print("Finalize com uma linha contendo apenas EOF e pressione Enter.")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "EOF":
            break
        lines.append(line)
    return "\n".join(lines)


def decode_pob_code(text: str) -> str:
    code = re.sub(r"\s+", "", text)
    code = code.replace("-", "+").replace("_", "/")
    code += "=" * ((4 - len(code) % 4) % 4)
    try:
        compressed = base64.b64decode(code)
    except Exception as exc:  # noqa: BLE001 - CLI needs the original failure summarized.
        raise SystemExit(f"Source is not XML and could not be base64 decoded: {exc}") from exc

    errors: list[str] = []
    for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
        try:
            return zlib.decompress(compressed, wbits).decode("utf-8", errors="replace")
        except zlib.error as exc:
            errors.append(str(exc))
    raise SystemExit("Source is not XML and could not be decompressed as a PoB export code: " + "; ".join(errors))


def load_pob_xml(source: str) -> tuple[ET.Element, str]:
    text, source_label = read_text_source(source)
    stripped = text.lstrip("\ufeff\r\n\t ")
    xml_text = stripped if stripped.startswith("<") else decode_pob_code(stripped)
    try:
        return ET.fromstring(xml_text), source_label
    except ET.ParseError as exc:
        raise SystemExit(f"Could not parse PoB XML from {source_label}: {exc}") from exc


def to_number(value: Any) -> float | int | None:
    if value is None:
        return None
    try:
        number = float(str(value).replace(",", "."))
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def extract_stats(root: ET.Element) -> dict[str, Any]:
    build = root.find("Build")
    stats: dict[str, Any] = {}
    character: dict[str, Any] = {}
    if build is None:
        return {"schema_version": 1, "source": "path_of_building", "stats": stats}

    for attr, key in (("level", "level"), ("className", "class"), ("ascendClassName", "ascendancy"), ("mainSocketGroup", "main_socket_group")):
        value = build.get(attr)
        if value not in (None, ""):
            character[key] = to_number(value) if attr == "level" else value

    for node in build.iter():
        if node.tag not in {"PlayerStat", "Stat"}:
            continue
        stat_name = node.get("stat") or node.get("name")
        value = to_number(node.get("value"))
        if stat_name in STAT_MAP and value is not None:
            if stat_name == "CritMultiplier" and value <= 10:
                value = round(float(value) * 100, 4)
            stats[STAT_MAP[stat_name]] = value

    return {
        "schema_version": 1,
        "source": "path_of_building",
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "character": character,
        "stats": stats,
    }


def active_item_set(items_node: ET.Element | None) -> ET.Element | None:
    if items_node is None:
        return None
    active_id = items_node.get("activeItemSet") or items_node.get("activeItemSetId")
    item_sets = list(items_node.findall("ItemSet"))
    if active_id:
        for item_set in item_sets:
            if item_set.get("id") == active_id:
                return item_set
    return item_sets[0] if item_sets else None


def item_id_map(items_node: ET.Element | None) -> dict[str, str]:
    if items_node is None:
        return {}
    out: dict[str, str] = {}
    for item in items_node.findall("Item"):
        item_id = item.get("id")
        if item_id:
            out[item_id] = item.text or ""
    return out


def normalize_slot(slot_name: str, index: int) -> str:
    if slot_name in SLOT_MAP:
        return SLOT_MAP[slot_name]
    cleaned = re.sub(r"\s+", " ", slot_name).strip()
    if cleaned.startswith("Jewel"):
        return f"jewel_{index}"
    return re.sub(r"[^a-z0-9]+", "_", cleaned.lower()).strip("_") or f"slot_{index}"


def useful_mod_lines(lines: list[str]) -> list[str]:
    ignored_prefixes = (
        "Rarity:",
        "Item Level:",
        "Quality:",
        "Sockets:",
        "LevelReq:",
        "Implicits:",
        "Variant:",
        "League:",
        "Unique ID:",
        "Armour:",
        "Evasion:",
        "Energy Shield:",
        "ArmourBasePercentile:",
        "EvasionBasePercentile:",
        "EnergyShieldBasePercentile:",
        "HasEaterOfWorldsImplicit:",
        "HasSearingExarchImplicit:",
    )
    out: list[str] = []
    for line in lines:
        line = line.strip()
        if not line or line == "--------":
            continue
        if line.startswith(ignored_prefixes):
            continue
        out.append(line)
    return out


def parse_item_text(text: str, slot: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n") if line.strip()]
    rarity = ""
    name = ""
    base = ""
    if lines and lines[0].startswith("Rarity:"):
        rarity = lines[0].split(":", 1)[1].strip().title()
        rarity_key = rarity.lower()
        header = [
            line
            for line in lines[1:]
            if line != "--------" and not line.startswith(("Unique ID:", "Source:", "League:"))
        ]
        if rarity_key in {"rare", "unique"}:
            name = header[0] if len(header) > 0 else ""
            base = header[1] if len(header) > 1 else name
        elif rarity_key == "magic":
            name = header[0] if header else ""
            base = header[1] if len(header) > 1 and ":" not in header[1] else name
        else:
            base = header[0] if header else ""
            name = ""

    mods_raw = [line for line in useful_mod_lines(lines) if line not in {name, base}]
    return {
        "slot": slot,
        "name": name,
        "base": base,
        "rarity": rarity or "Unknown",
        "locked": False,
        "mods_raw": mods_raw,
        "stats": normalize_mods(mods_raw),
    }


def extract_items(root: ET.Element) -> dict[str, Any]:
    items_node = root.find("Items")
    active_set = active_item_set(items_node)
    by_id = item_id_map(items_node)
    items: dict[str, Any] = {}
    if active_set is None:
        return {"schema_version": 1, "source": "path_of_building", "items": items}

    for index, slot_node in enumerate(active_set.findall("Slot"), start=1):
        item_id = slot_node.get("itemId")
        if not item_id or item_id not in by_id:
            continue
        slot = normalize_slot(slot_node.get("name") or "", index)
        items[slot] = parse_item_text(by_id[item_id], slot)

    return {
        "schema_version": 1,
        "source": "path_of_building",
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items,
    }


def active_skill_set(skills_node: ET.Element | None) -> ET.Element | None:
    if skills_node is None:
        return None
    active_id = skills_node.get("activeSkillSet") or skills_node.get("activeSkillSetId")
    skill_sets = list(skills_node.findall("SkillSet"))
    if active_id:
        for skill_set in skill_sets:
            if skill_set.get("id") == active_id:
                return skill_set
    return skill_sets[0] if skill_sets else None


def extract_skills(root: ET.Element) -> dict[str, Any]:
    skills_node = root.find("Skills")
    skill_set = active_skill_set(skills_node)
    groups: list[dict[str, Any]] = []
    if skill_set is not None:
        for index, skill_node in enumerate(skill_set.findall("Skill"), start=1):
            gems: list[dict[str, Any]] = []
            for gem in skill_node.findall("Gem"):
                gems.append(
                    {
                        "name": gem.get("nameSpec") or gem.get("skillId") or "",
                        "level": to_number(gem.get("level")),
                        "quality": to_number(gem.get("quality")),
                        "enabled": gem.get("enabled", "true") == "true",
                        "skill_id": gem.get("skillId") or "",
                        "gem_id": gem.get("gemId") or "",
                    }
                )
            enabled_gems = [gem for gem in gems if gem.get("enabled")]
            main_gem = enabled_gems[0]["name"] if enabled_gems else (gems[0]["name"] if gems else "")
            groups.append(
                {
                    "index": index,
                    "slot": normalize_slot(skill_node.get("slot") or "", index),
                    "label": skill_node.get("label") or "",
                    "enabled": skill_node.get("enabled", "true") == "true",
                    "include_in_full_dps": skill_node.get("includeInFullDPS", "false") == "true",
                    "main_active_skill": skill_node.get("mainActiveSkill") or "",
                    "main_gem": main_gem,
                    "gems": gems,
                }
            )
    return {
        "schema_version": 1,
        "source": "path_of_building",
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "skill_groups": groups,
        "main_skills": [group["main_gem"] for group in groups if group.get("enabled") and group.get("main_gem")],
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def target_requirements_from_pob(stats_doc: dict[str, Any], items_doc: dict[str, Any], skills_doc: dict[str, Any]) -> dict[str, Any]:
    requirements = target_analysis.build_target_requirements(stats_doc, items_doc, skills_doc)
    requirements["source_path"] = stats_doc.get("source_path")
    return requirements


def target_stats_from_pob(stats_doc: dict[str, Any], items_doc: dict[str, Any] | None = None, skills_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    items_doc = items_doc or {"items": {}}
    skills_doc = skills_doc or {"skill_groups": []}
    requirements = target_requirements_from_pob(stats_doc, items_doc, skills_doc)
    return target_analysis.target_stats_from_requirements(requirements)


def target_items_from_pob(items_doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": "path_of_building",
        "updated": items_doc.get("updated"),
        "items": items_doc.get("items", {}),
        "desired_by_profile": {},
    }


def target_skills_from_pob(skills_doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": "path_of_building",
        "updated": skills_doc.get("updated"),
        "skill_groups": skills_doc.get("skill_groups", []),
        "main_skills": skills_doc.get("main_skills", []),
    }


def local_pob_dirs() -> list[Path]:
    home = Path.home()
    candidates = [
        home / "Documents" / "Path of Building" / "Builds",
        home / "Documents" / "Path of Building Community" / "Builds",
        home / "OneDrive" / "Documents" / "Path of Building" / "Builds",
        home / "OneDrive" / "Documents" / "Path of Building Community" / "Builds",
    ]
    return [path for path in candidates if path.exists()]


def list_local_builds() -> None:
    dirs = local_pob_dirs()
    if not dirs:
        print("No local Path of Building build directories found.")
        return
    for directory in dirs:
        print(f"\n{directory}")
        for path in sorted(directory.glob("*.xml"))[:100]:
            print(f"- {path.name}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import local Path of Building XML/export code into toolkit JSON files.")
    parser.add_argument("--source", help="PoB XML path, file containing exported code, or raw exported code.")
    parser.add_argument("--from-clipboard", action="store_true", help="Read PoB export code from the Windows clipboard.")
    parser.add_argument("--from-stdin", action="store_true", help="Paste PoB export code interactively; finish with EOF on its own line.")
    parser.add_argument("--save-code", type=Path, help="Save the provided PoB export code to this file before importing.")
    parser.add_argument("--character", help="Character slug to update with player_items/player_stats.")
    parser.add_argument("--build", help="Build profile slug to update with target_build_items/target_build_stats.")
    parser.add_argument("--as", dest="mode", choices=["player", "target"], help="Output mode. Defaults to player for --character and target for --build.")
    parser.add_argument("--list-local", action="store_true", help="List likely local Path of Building XML files.")
    parser.add_argument("--stats-only", action="store_true", help="Only write stats JSON.")
    parser.add_argument("--items-only", action="store_true", help="Only write items JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.list_local:
        list_local_builds()
        return 0
    source_count = sum(1 for value in (args.source, args.from_clipboard, args.from_stdin) if value)
    if source_count != 1:
        raise SystemExit("Use exactly one source: --source, --from-clipboard, --from-stdin, or --list-local.")
    if not args.character and not args.build:
        raise SystemExit("Use --character <slug> or --build <slug>.")
    if args.stats_only and args.items_only:
        raise SystemExit("Use either --stats-only or --items-only, not both.")

    source = args.source
    temporary_source: Path | None = None
    if args.from_clipboard:
        try:
            import tkinter as tk
        except ImportError as exc:
            raise SystemExit("--from-clipboard requires tkinter on this Python installation.") from exc
        clipboard = tk.Tk()
        clipboard.withdraw()
        try:
            source = clipboard.clipboard_get()
        finally:
            clipboard.destroy()
    elif args.from_stdin:
        source = read_pob_code_from_stdin()

    if args.save_code:
        source = str(save_pob_code(args.save_code, str(source or "")))
    elif source and not Path(str(source)).expanduser().exists() and not str(source).lstrip().startswith("<"):
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", suffix=".pob.txt", dir=RAW_DIR, delete=False) as tmp:
            tmp.write(str(source).strip())
            temporary_source = Path(tmp.name)
            source = str(temporary_source)

    mode = args.mode or ("player" if args.character else "target")
    root, source_label = load_pob_xml(str(source))
    stats_doc = extract_stats(root)
    items_doc = extract_items(root)
    skills_doc = extract_skills(root)
    stats_doc["source_path"] = source_label
    items_doc["source_path"] = source_label
    skills_doc["source_path"] = source_label
    if temporary_source is not None:
        try:
            temporary_source.unlink()
        except OSError:
            pass

    if mode == "player":
        if not args.character:
            raise SystemExit("--as player requires --character.")
        target_dir = CHARACTERS_DIR / args.character
        if not target_dir.exists():
            raise SystemExit(f"Character profile not found: {target_dir}")
        if not args.items_only:
            write_json(target_dir / "player_stats.json", stats_doc)
        if not args.stats_only:
            write_json(target_dir / "player_items.json", items_doc)
            write_json(target_dir / "player_skills.json", skills_doc)
        print(f"Updated character from PoB: {args.character}")
        print(f"- stats: {target_dir / 'player_stats.json'}")
        print(f"- items: {target_dir / 'player_items.json'}")
        print(f"- skills: {target_dir / 'player_skills.json'}")
        return 0

    if not args.build:
        raise SystemExit("--as target requires --build.")
    target_dir = PROFILES_DIR / args.build
    if not target_dir.exists():
        raise SystemExit(f"Build profile not found: {target_dir}")
    if not args.items_only:
        requirements_doc = target_requirements_from_pob(stats_doc, items_doc, skills_doc)
        write_json(target_dir / "target_build_stats.json", target_analysis.target_stats_from_requirements(requirements_doc))
        write_json(target_dir / "target_requirements.json", requirements_doc)
    if not args.stats_only:
        write_json(target_dir / "target_build_items.json", target_items_from_pob(items_doc))
        write_json(target_dir / "target_build_skills.json", target_skills_from_pob(skills_doc))
    print(f"Updated target build from PoB: {args.build}")
    print(f"- stats: {target_dir / 'target_build_stats.json'}")
    print(f"- items: {target_dir / 'target_build_items.json'}")
    print(f"- skills: {target_dir / 'target_build_skills.json'}")
    if not args.items_only:
        print(f"- requirements: {target_dir / 'target_requirements.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
