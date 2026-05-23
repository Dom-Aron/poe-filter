#!/usr/bin/env python3
"""
parse_character.py

Normalizes a raw official Path of Exile character API response into JSON files
used by the build agent.

The official API provides raw character state, not full Path of Building style
derived stats. For that reason this parser extracts equipment, gems, passives
and stat hints from item mods, while keeping calculated combat stats marked as
manual/PoB-required.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "character_api_raw.json"
CURRENT_DIR = ROOT / "data" / "current"
BUILDS_DIR = ROOT / "builds"


FRAME_TYPES = {
    0: "Normal",
    1: "Magic",
    2: "Rare",
    3: "Unique",
    4: "Gem",
    5: "Currency",
    6: "Divination Card",
    7: "Quest",
    8: "Prophecy",
    9: "Relic",
}


SLOT_MAP = {
    "Weapon": "weapon",
    "Weapon2": "weapon_swap",
    "Offhand": "offhand",
    "Offhand2": "offhand_swap",
    "Helm": "helmet",
    "BodyArmour": "body_armour",
    "Gloves": "gloves",
    "Boots": "boots",
    "Amulet": "amulet",
    "Ring": "ring_1",
    "Ring2": "ring_2",
    "Belt": "belt",
    "Flask": "flask_1",
    "Flask2": "flask_2",
    "Flask3": "flask_3",
    "Flask4": "flask_4",
    "Flask5": "flask_5",
}


def load_raw(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("data", raw)


def all_mod_lines(item: dict[str, Any]) -> list[str]:
    fields = [
        "implicitMods",
        "explicitMods",
        "craftedMods",
        "fracturedMods",
        "enchantMods",
        "utilityMods",
        "scourgeMods",
    ]
    lines: list[str] = []
    for field in fields:
        value = item.get(field)
        if isinstance(value, list):
            lines.extend(str(line) for line in value)
    return lines


def numbers(text: str) -> list[float]:
    return [abs(float(match.replace(",", "."))) for match in re.findall(r"[-+]?\d+(?:[.,]\d+)?", text)]


def first_number(text: str) -> float:
    vals = numbers(text)
    return vals[0] if vals else 0.0


def add(stats: dict[str, float], key: str, value: float) -> None:
    if value:
        stats[key] = stats.get(key, 0.0) + value


def normalize_mods(lines: list[str]) -> dict[str, float]:
    stats: dict[str, float] = {}
    for line in lines:
        lower = line.lower()
        value = first_number(line)

        if "to maximum life" in lower:
            add(stats, "life", value)
        if "to accuracy rating" in lower:
            add(stats, "accuracy", value)
        if "to fire resistance" in lower:
            add(stats, "fire_resistance", value)
        if "to cold resistance" in lower:
            add(stats, "cold_resistance", value)
        if "to lightning resistance" in lower:
            add(stats, "lightning_resistance", value)
        if "to chaos resistance" in lower:
            add(stats, "chaos_resistance", value)
        if "to all elemental resistances" in lower:
            add(stats, "fire_resistance", value)
            add(stats, "cold_resistance", value)
            add(stats, "lightning_resistance", value)
        if "increased attack speed" in lower:
            add(stats, "attack_speed", value)
        if "global critical strike multiplier" in lower:
            add(stats, "crit_multiplier", value)
        if "chance to impale" in lower:
            add(stats, "impale_chance", value)
        if "physical damage to attacks" in lower:
            stats["physical_damage_to_attacks"] = 1.0
        if "added physical damage with staff attacks" in lower:
            stats["staff_flat_physical"] = 1.0
        if "channelling skills have" in lower and "total mana cost" in lower:
            stats["mana_cost_channeling"] = -value
        if "increased damage while leeching" in lower:
            add(stats, "damage_while_leeching", value)
        if "movement speed" in lower:
            add(stats, "movement_speed", value)
        if "chance to avoid elemental ailments" in lower:
            add(stats, "ailment_avoidance", value)
        if "action speed" in lower:
            add(stats, "action_speed", value)
        if "chance to block attack damage during effect" in lower:
            add(stats, "attack_block_during_effect", value)
        if "chance to block spell damage during effect" in lower:
            add(stats, "spell_block_during_effect", value)
        if "corrupted" == lower.strip():
            stats["corrupted"] = 1.0
    return stats


def normalize_slot(item: dict[str, Any], fallback_index: int) -> str:
    inventory_id = str(item.get("inventoryId") or item.get("inventory_id") or "")
    if inventory_id in SLOT_MAP:
        return SLOT_MAP[inventory_id]
    if inventory_id.startswith("Jewel"):
        return f"jewel_{fallback_index}"
    if inventory_id:
        return inventory_id.lower()
    return f"item_{fallback_index}"


def normalize_item(item: dict[str, Any], slot: str) -> dict[str, Any]:
    lines = all_mod_lines(item)
    socketed = item.get("socketedItems") if isinstance(item.get("socketedItems"), list) else []
    return {
        "slot": slot,
        "name": item.get("name") or "",
        "base": item.get("typeLine") or item.get("baseType") or "",
        "rarity": FRAME_TYPES.get(item.get("frameType"), str(item.get("frameType", "Unknown"))),
        "ilvl": item.get("ilvl"),
        "locked": False,
        "mods_raw": lines,
        "stats": normalize_mods(lines),
        "tags": infer_tags(item, lines),
        "socketed_gems": [
            {
                "name": gem.get("typeLine") or gem.get("baseType") or gem.get("name") or "",
                "level": gem.get("properties", []),
                "mods_raw": all_mod_lines(gem),
            }
            for gem in socketed
        ],
    }


def infer_tags(item: dict[str, Any], lines: list[str]) -> list[str]:
    text = " ".join([str(item.get("typeLine", "")), *lines]).lower()
    tags: set[str] = set()
    if "staff" in text:
        tags.add("staff_build")
    if "physical" in text:
        tags.add("physical")
    if "attack" in text:
        tags.add("attack")
    if "life" in text:
        tags.add("life")
    if "resistance" in text:
        tags.add("resistance")
    if "impale" in text:
        tags.add("impale")
    return sorted(tags)


def extract_equipment(data: dict[str, Any]) -> dict[str, Any]:
    equipment = data.get("equipment") or data.get("items") or []
    if not isinstance(equipment, list):
        equipment = []
    items: dict[str, Any] = {}
    for index, item in enumerate(equipment, start=1):
        if not isinstance(item, dict):
            continue
        slot = normalize_slot(item, index)
        normalized = normalize_item(item, slot)
        items[slot] = normalized
    return {"schema_version": 1, "source": "official_api", "items": items}


def extract_passives(data: dict[str, Any]) -> dict[str, Any]:
    passives = data.get("passives") if isinstance(data.get("passives"), dict) else {}
    return {
        "schema_version": 1,
        "source": "official_api",
        "hashes": passives.get("hashes", []),
        "hashes_ex": passives.get("hashes_ex", []),
        "mastery_effects": passives.get("mastery_effects", {}),
        "bandit_choice": passives.get("bandit_choice"),
        "pantheon_major": passives.get("pantheon_major"),
        "pantheon_minor": passives.get("pantheon_minor"),
        "jewel_data": passives.get("jewel_data", {}),
    }


def extract_skills(player_items: dict[str, Any]) -> dict[str, Any]:
    skills: list[dict[str, Any]] = []
    for slot, item in player_items.get("items", {}).items():
        for gem in item.get("socketed_gems", []):
            if gem.get("name"):
                skills.append({"slot": slot, **gem})
    return {"schema_version": 1, "source": "official_api", "skills": skills}


def extract_stats(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": "official_api_limited",
        "note": "A API oficial entrega dados crus. Stats como DPS, chance_to_hit e EHP precisam de PoB ou entrada manual.",
        "character": {
            "name": data.get("name"),
            "class": data.get("class"),
            "league": data.get("league"),
            "level": data.get("level"),
            "experience": data.get("experience"),
        },
        "stats": {},
        "manual_or_pob_required": [
            "life",
            "chance_to_hit",
            "chance_to_hit_evasive",
            "impale_chance",
            "fire_resistance",
            "cold_resistance",
            "lightning_resistance",
            "chaos_resistance",
            "attack_block",
            "spell_block",
            "ailment_avoidance",
        ],
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def copy_to_builds(source: Path, target: Path, backup: bool = False) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if backup and target.exists():
        backup = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, backup)
    shutil.copy2(source, target)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse raw PoE character API data into normalized build files.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=CURRENT_DIR)
    parser.add_argument("--update-builds", action="store_true", help="Also copy player_items/player_stats into builds/ for the planner.")
    parser.add_argument("--backup-builds", action="store_true", help="Create .bak files before overwriting builds/player_items.json and builds/player_stats.json.")
    parser.add_argument("--allow-legacy-global-state", action="store_true", help="Allow --update-builds to overwrite global builds/player_*.json files.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}. Run fetch_character.py first.")

    data = load_raw(args.input)
    player_items = extract_equipment(data)
    player_passives = extract_passives(data)
    player_skills = extract_skills(player_items)
    player_stats = extract_stats(data)

    write_json(args.output_dir / "player_items.json", player_items)
    write_json(args.output_dir / "player_passives.json", player_passives)
    write_json(args.output_dir / "player_skills.json", player_skills)
    write_json(args.output_dir / "player_stats.json", player_stats)

    if args.update_builds and not args.allow_legacy_global_state:
        raise SystemExit(
            "--update-builds writes global planner inputs and is legacy. "
            "Write directly into builds/characters/<slug>/ instead, or pass "
            "--allow-legacy-global-state intentionally."
        )

    if args.update_builds:
        copy_to_builds(args.output_dir / "player_items.json", BUILDS_DIR / "player_items.json", args.backup_builds)
        copy_to_builds(args.output_dir / "player_stats.json", BUILDS_DIR / "player_stats.json", args.backup_builds)

    print(f"Parsed character files written to: {args.output_dir}")
    if args.update_builds:
        suffix = " with .bak backups." if args.backup_builds else "."
        print(f"Updated planner input files in builds/{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
