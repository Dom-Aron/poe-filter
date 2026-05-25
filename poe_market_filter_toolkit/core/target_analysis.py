"""Generic target-build analysis helpers.

The project should not need to know that a profile is "Cyclone", "Deadeye",
or any other named build to understand what the target asks for.  This module
turns imported PoB data into a compact requirements document that later scripts
can use for gap analysis, scoring, and human-readable reports.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .time_utils import utc_now_iso


ELEMENTAL_RESISTS = ("fire_resistance", "cold_resistance", "lightning_resistance")
RESIST_STATS = (*ELEMENTAL_RESISTS, "chaos_resistance")

STAT_LABELS = {
    "life": "Vida",
    "energy_shield": "Energy Shield",
    "mana": "Mana",
    "ehp": "EHP",
    "total_dps": "DPS total",
    "combined_dps": "DPS combinado",
    "full_dps": "Full DPS",
    "attack_rate": "Velocidade de ataque/conjuração",
    "chance_to_hit": "Chance de acerto",
    "critical_strike_chance": "Chance de crítico",
    "crit_multiplier": "Multiplicador de crítico",
    "accuracy": "Accuracy",
    "armour": "Armadura",
    "evasion": "Evasão",
    "physical_damage_reduction": "Redução física",
    "attack_block": "Bloqueio de ataque",
    "spell_block": "Bloqueio de magia",
    "spell_suppression": "Supressão de magia",
    "fire_resistance": "Resistência a fogo",
    "cold_resistance": "Resistência a frio",
    "lightning_resistance": "Resistência a raio",
    "chaos_resistance": "Resistência a caos",
    "physical_max_hit": "Max hit físico",
    "fire_max_hit": "Max hit fogo",
    "cold_max_hit": "Max hit frio",
    "lightning_max_hit": "Max hit raio",
    "chaos_max_hit": "Max hit caos",
    "movement_speed": "Velocidade de movimento",
    "attack_speed": "Velocidade de ataque",
    "cast_speed": "Velocidade de conjuração",
    "gem_level": "Nível de gemas",
}

BASE_WEIGHTS = {
    "life": 1.0,
    "energy_shield": 0.65,
    "mana": 0.15,
    "ehp": 0.002,
    "total_dps": 0.00006,
    "combined_dps": 0.00006,
    "full_dps": 0.00006,
    "attack_rate": 18.0,
    "chance_to_hit": 2.0,
    "accuracy": 0.03,
    "critical_strike_chance": 2.0,
    "crit_multiplier": 1.6,
    "armour": 0.003,
    "evasion": 0.002,
    "physical_damage_reduction": 1.3,
    "attack_block": 1.4,
    "spell_block": 1.5,
    "spell_suppression": 1.6,
    "fire_resistance": 0.8,
    "cold_resistance": 0.8,
    "lightning_resistance": 0.8,
    "chaos_resistance": 1.4,
    "physical_max_hit": 0.004,
    "fire_max_hit": 0.003,
    "cold_max_hit": 0.003,
    "lightning_max_hit": 0.003,
    "chaos_max_hit": 0.004,
    "movement_speed": 1.2,
    "attack_speed": 2.0,
    "cast_speed": 2.0,
    "gem_level": 35.0,
}

STAT_TAGS = {
    "life": ("defense", "life"),
    "energy_shield": ("defense", "energy_shield"),
    "mana": ("resource", "mana"),
    "accuracy": ("attack", "accuracy"),
    "chance_to_hit": ("attack", "accuracy"),
    "critical_strike_chance": ("damage", "crit"),
    "crit_multiplier": ("damage", "crit"),
    "attack_speed": ("damage", "speed", "attack"),
    "cast_speed": ("damage", "speed", "spell"),
    "movement_speed": ("mobility",),
    "impale_chance": ("damage", "physical", "impale"),
    "physical_damage_to_attacks": ("damage", "physical", "attack"),
    "staff_flat_physical": ("damage", "physical", "staff"),
    "spell_block": ("defense", "block"),
    "attack_block": ("defense", "block"),
    "spell_suppression": ("defense", "suppression"),
    "ailment_avoidance": ("defense", "ailment"),
}


def numeric_stats(stats_doc: dict[str, Any]) -> dict[str, float]:
    raw = stats_doc.get("stats", {}) if isinstance(stats_doc, dict) else {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, bool):
            out[str(key)] = 1.0 if value else 0.0
        elif isinstance(value, (int, float)):
            out[str(key)] = float(value)
    return out


def item_slots(items_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = items_doc.get("items", {}) if isinstance(items_doc, dict) else {}
    if not isinstance(raw, dict):
        return {}
    return {str(slot): item for slot, item in raw.items() if isinstance(item, dict)}


def skill_groups(skills_doc: dict[str, Any]) -> list[dict[str, Any]]:
    raw = skills_doc.get("skill_groups", []) if isinstance(skills_doc, dict) else []
    return [group for group in raw if isinstance(group, dict)]


def infer_minimums(goals: dict[str, float]) -> dict[str, float | int]:
    """Infer survivable floors from target PoB goals.

    Goals say "where the target is"; minimums say "do not break the build while
    upgrading".  A target with 82 fire resistance still has 75 as the safe floor,
    while the extra 7 stays as a goal.
    """

    minimums: dict[str, float | int] = {}
    life = goals.get("life")
    if life:
        minimums["life"] = round(life * 0.85)
    energy_shield = goals.get("energy_shield")
    if energy_shield and not life:
        minimums["energy_shield"] = round(energy_shield * 0.85)

    for key in ELEMENTAL_RESISTS:
        value = goals.get(key)
        if value is not None:
            minimums[key] = 75 if value >= 75 else round(value, 2)

    chaos = goals.get("chaos_resistance")
    if chaos is not None:
        minimums["chaos_resistance"] = 0 if chaos >= 0 else round(chaos, 2)

    hit = goals.get("chance_to_hit")
    if hit is not None:
        minimums["chance_to_hit"] = 90 if hit >= 90 else round(hit, 2)

    for key in ("spell_suppression", "attack_block", "spell_block", "ailment_avoidance"):
        value = goals.get(key)
        if value is not None and value >= 50:
            minimums[key] = round(value * 0.7, 2)

    return minimums


def stat_tags(stat_key: str) -> list[str]:
    tags = set(STAT_TAGS.get(stat_key, ()))
    if stat_key in RESIST_STATS:
        tags.update(("defense", "resistance"))
    if "damage" in stat_key or "dps" in stat_key:
        tags.add("damage")
    if "physical" in stat_key:
        tags.add("physical")
    if "fire" in stat_key:
        tags.add("fire")
    if "cold" in stat_key:
        tags.add("cold")
    if "lightning" in stat_key:
        tags.add("lightning")
    if "chaos" in stat_key:
        tags.add("chaos")
    return sorted(tags)


def tags_from_text(lines: list[str]) -> list[str]:
    text = " ".join(lines).lower()
    tags: set[str] = set()
    rules = {
        "life": ("life",),
        "energy shield": ("energy_shield",),
        "resistance": ("resistance", "defense"),
        "accuracy": ("accuracy", "attack"),
        "critical": ("crit", "damage"),
        "attack": ("attack",),
        "spell": ("spell",),
        "minion": ("minion",),
        "totem": ("totem",),
        "projectile": ("projectile",),
        "physical": ("physical", "damage"),
        "fire": ("fire",),
        "cold": ("cold",),
        "lightning": ("lightning",),
        "chaos": ("chaos",),
        "impale": ("impale", "physical"),
        "aura": ("aura",),
        "reservation": ("reservation",),
        "curse": ("curse",),
        "vulnerability": ("curse", "physical"),
        "bleeding": ("bleed", "physical"),
        "poison": ("poison", "chaos"),
        "brand": ("brand",),
        "strike": ("strike", "attack"),
        "bow": ("bow", "attack"),
        "staff": ("staff",),
    }
    for needle, found_tags in rules.items():
        if needle in text:
            tags.update(found_tags)
    return sorted(tags)


def relevant_item_stats(stats: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in stats.items():
        if isinstance(value, bool):
            out[str(key)] = 1.0 if value else 0.0
        elif isinstance(value, (int, float)) and value != 0:
            out[str(key)] = float(value)
    return out


def slot_requirements(items_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    requirements: dict[str, dict[str, Any]] = {}
    for slot, item in item_slots(items_doc).items():
        mods_raw = [str(line) for line in item.get("mods_raw", []) if str(line).strip()]
        stats = relevant_item_stats(item.get("stats", {}) if isinstance(item.get("stats"), dict) else {})
        tags = set(tags_from_text([str(item.get("base", "")), str(item.get("name", "")), *mods_raw]))
        for stat_key in stats:
            tags.update(stat_tags(stat_key))
        requirements[slot] = {
            "slot": slot,
            "name": item.get("name", ""),
            "base": item.get("base", ""),
            "rarity": item.get("rarity", ""),
            "desired_stats": sorted(stats),
            "stats": stats,
            "tags": sorted(tags),
            "mods_raw": mods_raw,
        }
    return requirements


def skill_requirements(skills_doc: dict[str, Any]) -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    for group in skill_groups(skills_doc):
        gems = [gem for gem in group.get("gems", []) if isinstance(gem, dict) and gem.get("enabled", True)]
        if not gems:
            continue
        tags = set(tags_from_text([str(gem.get("name", "")) for gem in gems]))
        main = str(group.get("main_gem") or gems[0].get("name") or "")
        support_names = [str(gem.get("name")) for gem in gems[1:] if gem.get("name")]
        max_level = max([float(gem.get("level") or 0) for gem in gems] or [0])
        requirements.append(
            {
                "index": group.get("index"),
                "slot": group.get("slot", ""),
                "main_skill": main,
                "supports": support_names,
                "gem_count": len(gems),
                "max_gem_level": int(max_level) if max_level.is_integer() else max_level,
                "include_in_full_dps": bool(group.get("include_in_full_dps")),
                "tags": sorted(tags),
            }
        )
    return requirements


def derive_weights(goals: dict[str, float], slots: dict[str, dict[str, Any]], skills: list[dict[str, Any]]) -> dict[str, float]:
    keys = set(goals)
    for slot in slots.values():
        keys.update(slot.get("desired_stats", []))
    for skill in skills:
        if skill.get("max_gem_level", 0) >= 21:
            keys.add("gem_level")

    weights: dict[str, float] = {}
    for key in sorted(keys):
        if key in BASE_WEIGHTS:
            weights[key] = BASE_WEIGHTS[key]
        elif key in RESIST_STATS:
            weights[key] = 1.0
        elif "damage" in key or "dps" in key:
            weights[key] = 0.5
        elif "speed" in key:
            weights[key] = 1.5
        elif "level" in key:
            weights[key] = 10.0
        else:
            weights[key] = 0.75
    return weights


def top_tags(slots: dict[str, dict[str, Any]], skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for slot in slots.values():
        counter.update(slot.get("tags", []))
    for skill in skills:
        counter.update(skill.get("tags", []))
    return [{"tag": tag, "count": count} for tag, count in counter.most_common(12)]


def suggested_searches(slots: dict[str, dict[str, Any]], tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    searches: list[dict[str, Any]] = []
    for slot, data in slots.items():
        desired = data.get("desired_stats", [])
        if not desired:
            continue
        searches.append(
            {
                "slot": slot,
                "title": f"{slot.replace('_', ' ').title()} parecido com o target",
                "must_keep": [stat for stat in desired if stat in RESIST_STATS or stat in {"life", "accuracy"}],
                "nice_to_have": [stat for stat in desired if stat not in RESIST_STATS and stat not in {"life", "accuracy"}][:6],
                "tags": data.get("tags", [])[:8],
            }
        )

    dominant_tags = [entry["tag"] for entry in tags[:5]]
    if dominant_tags:
        searches.insert(
            0,
            {
                "slot": "generic",
                "title": "Prioridades globais detectadas no target",
                "must_keep": [],
                "nice_to_have": dominant_tags,
                "tags": dominant_tags,
            },
        )
    return searches


def clean_goals(goals: dict[str, float]) -> dict[str, float | int]:
    cleaned: dict[str, float | int] = {}
    for key, value in sorted(goals.items()):
        if abs(value) < 0.0001:
            continue
        rounded = round(value, 4)
        cleaned[key] = int(rounded) if float(rounded).is_integer() else rounded
    return cleaned


def build_target_requirements(stats_doc: dict[str, Any], items_doc: dict[str, Any], skills_doc: dict[str, Any]) -> dict[str, Any]:
    goals = clean_goals(numeric_stats(stats_doc))
    minimums = infer_minimums({key: float(value) for key, value in goals.items() if isinstance(value, (int, float))})
    slots = slot_requirements(items_doc)
    skills = skill_requirements(skills_doc)
    tags = top_tags(slots, skills)
    return {
        "schema_version": 1,
        "source": "path_of_building",
        "updated": utc_now_iso(),
        "minimums": minimums,
        "goals": goals,
        "weights": derive_weights({key: float(value) for key, value in goals.items() if isinstance(value, (int, float))}, slots, skills),
        "dominant_tags": tags,
        "slot_requirements": slots,
        "skill_requirements": skills,
        "suggested_searches": suggested_searches(slots, tags),
        "notes": [
            "Gerado automaticamente a partir do PoB alvo.",
            "Minimums sao pisos de seguranca; goals representam onde a build alvo chega.",
            "Use slot_requirements e dominant_tags para revisar buscas especificas sem prender o projeto a uma build nomeada.",
        ],
    }


def target_stats_from_requirements(requirements: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source": "path_of_building_requirements",
        "updated": requirements.get("updated"),
        "minimums": requirements.get("minimums", {}),
        "goals": requirements.get("goals", {}),
    }


def stat_label(stat_key: str) -> str:
    if stat_key in STAT_LABELS:
        return STAT_LABELS[stat_key]
    return re.sub(r"_+", " ", stat_key).strip().title()
