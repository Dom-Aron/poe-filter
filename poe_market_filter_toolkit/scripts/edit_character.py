#!/usr/bin/env python3
"""
edit_character.py

Small no-dependency assistant for maintaining player_items.json and
player_stats.json without editing raw JSON by hand.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLKIT_ROOT))

from core import paths
from core.io import read_json, write_json

DEFAULT_SLOTS = (
    "weapon",
    "helmet",
    "body_armour",
    "gloves",
    "boots",
    "belt",
    "amulet",
    "ring_1",
    "ring_2",
    "quiver",
    "flask_rumi",
    "jewel_1",
    "abyss_jewel_1",
    "large_cluster_1",
)
COMMON_ITEM_STATS = (
    "life",
    "accuracy",
    "fire_resistance",
    "cold_resistance",
    "lightning_resistance",
    "chaos_resistance",
    "attack_speed",
    "cast_speed",
    "crit_multiplier",
    "critical_strike_chance",
    "spell_damage",
    "lightning_damage",
    "elemental_damage",
    "projectile_damage",
    "impale_chance",
    "mana_cost_channeling",
)
COMMON_PLAYER_STATS = (
    "life",
    "energy_shield",
    "accuracy",
    "chance_to_hit",
    "fire_resistance",
    "cold_resistance",
    "lightning_resistance",
    "chaos_resistance",
    "spell_block",
    "attack_block",
    "ailment_avoidance",
    "impale_chance",
    "crit_multiplier",
    "critical_strike_chance",
    "dps_score",
)


def parse_number(raw: str) -> float | int | None:
    text = raw.strip().replace(",", ".")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value if value else default


def ask_bool(prompt: str, default: bool = False) -> bool:
    default_text = "s" if default else "n"
    raw = ask(prompt + " (s/n)", default_text).lower()
    return raw in {"s", "sim", "y", "yes", "1", "true"}


def ask_stats(existing: dict[str, Any], stat_names: tuple[str, ...]) -> dict[str, Any]:
    stats = dict(existing)
    print("Informe valores numericos. Enter preserva o valor atual; '-' remove o stat.")
    for key in stat_names:
        current = "" if key not in stats else str(stats[key])
        raw = ask(f"  {key}", current)
        if raw == "-":
            stats.pop(key, None)
            continue
        parsed = parse_number(raw)
        if parsed is not None:
            stats[key] = parsed
    while ask_bool("Adicionar outro stat?", False):
        key = ask("  nome do stat")
        raw = ask("  valor")
        parsed = parse_number(raw)
        if key and parsed is not None:
            stats[key] = parsed
    return stats


def edit_slot(items: dict[str, Any], slot: str) -> None:
    current = items.setdefault(slot, {})
    if not isinstance(current, dict):
        current = {}
        items[slot] = current
    print()
    print(f"Slot: {slot}")
    current["name"] = ask("Nome do item", str(current.get("name", "")))
    current["base"] = ask("Base type", str(current.get("base", "")))
    current["locked"] = ask_bool("Slot sensivel/evitar troca automatica?", bool(current.get("locked", False)))
    reason = ask("Motivo/observacao", str(current.get("protect_reason", "")))
    if reason:
        current["protect_reason"] = reason
    elif "protect_reason" in current:
        current.pop("protect_reason", None)
    current["stats"] = ask_stats(current.get("stats", {}) if isinstance(current.get("stats"), dict) else {}, COMMON_ITEM_STATS)


def edit_items(character_slug: str, slots: list[str]) -> None:
    path = paths.character_dir(character_slug) / "player_items.json"
    data = read_json(path)
    data.setdefault("schema_version", 1)
    data.setdefault("character", character_slug)
    data["updated"] = date.today().isoformat()
    items = data.setdefault("items", {})
    if not isinstance(items, dict):
        items = {}
        data["items"] = items
    selected = slots or list(items.keys()) or list(DEFAULT_SLOTS)
    for slot in selected:
        if ask_bool(f"Editar {slot}?", slot in items):
            edit_slot(items, slot)
    write_json(path, data)
    print(f"Salvo: {path}")


def edit_stats(character_slug: str) -> None:
    path = paths.character_dir(character_slug) / "player_stats.json"
    data = read_json(path)
    data.setdefault("schema_version", 1)
    data.setdefault("character", character_slug)
    data["updated"] = date.today().isoformat()
    stats = data.get("stats", {}) if isinstance(data.get("stats"), dict) else {}
    data["stats"] = ask_stats(stats, COMMON_PLAYER_STATS)
    write_json(path, data)
    print(f"Salvo: {path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edit local character item/stat JSONs interactively.")
    parser.add_argument("--character", required=True, help="Saved character slug.")
    parser.add_argument("--items", action="store_true", help="Edit player_items.json.")
    parser.add_argument("--stats", action="store_true", help="Edit player_stats.json.")
    parser.add_argument("--slots", help="Comma-separated slots to edit. Defaults to existing/default slots.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not paths.character_dir(args.character).exists():
        raise SystemExit(f"Personagem nao encontrado: {args.character}")
    slots = [slot.strip() for slot in (args.slots or "").split(",") if slot.strip()]
    edit_items_flag = args.items or not args.stats
    edit_stats_flag = args.stats or not args.items
    if edit_items_flag:
        edit_items(args.character, slots)
    if edit_stats_flag:
        edit_stats(args.character)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
