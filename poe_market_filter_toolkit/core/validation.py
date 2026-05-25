"""Validation for local no-OAuth character/build profiles."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import paths
from .io import read_json_checked


REQUIRED_CHARACTER_FILES = ("character_profile.json", "player_items.json", "player_stats.json")
REQUIRED_BUILD_FILES = ("build_profile.json", "target_build_items.json", "target_build_stats.json", "upgrade_rules.json")
LEGACY_STAT_ALIASES = {
    "crit_chance": "critical_strike_chance",
    "critical_multiplier": "crit_multiplier",
}
PLANNER_EFFECT_KEYS = {
    "vulnerability_on_hit",
    "physical_damage_to_attacks",
    "mana_cost_channeling",
    "staff_flat_physical",
    "onslaught",
    "blind",
    "maximum_life_percent",
    "staff_physical_damage_percent",
    "staff_attack_speed_percent",
    "eight_passives",
    "large_cluster_good_base",
    "not_corrupted",
    "spell_block_during_effect",
    "attack_block_during_effect",
    "gem_level",
    "plan_penalty",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def numeric_stats(data: dict[str, Any]) -> dict[str, float]:
    raw = data.get("stats", {})
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, bool):
            out[str(key)] = 1.0 if value else 0.0
        elif isinstance(value, (int, float)):
            out[str(key)] = float(value)
    return out


def item_slots(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = data.get("items", {})
    if not isinstance(items, dict):
        return {}
    return {str(slot): item for slot, item in items.items() if isinstance(item, dict)}


def item_stat_keys(data: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for item in item_slots(data).values():
        stats = item.get("stats", {})
        if isinstance(stats, dict):
            keys.update(str(key) for key in stats)
    return keys


def target_stat_keys(target_stats: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for group in ("minimums", "goals"):
        raw = target_stats.get(group, {})
        if isinstance(raw, dict):
            keys.update(str(key) for key in raw)
    return keys


def list_names(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def rule_stat_references(rules: dict[str, Any], include_weights: bool = True) -> set[str]:
    refs: set[str] = set()
    groups = ("weights", "penalties") if include_weights else ("penalties",)
    for group in groups:
        raw = rules.get(group, {})
        if isinstance(raw, dict):
            refs.update(str(key) for key in raw)
    refs.update(list_names(rules.get("soft_minimum_stats")))
    refs.update(list_names(rules.get("derived_goal_stats")))
    search_library = rules.get("search_library", {})
    if isinstance(search_library, dict):
        refs.update(str(key) for key in search_library)
    return refs


def trade_profiles(rules: dict[str, Any]) -> dict[str, Any]:
    raw = rules.get("trade_profiles", {})
    return raw if isinstance(raw, dict) else {}


def validate_files(base: Path, names: tuple[str, ...], errors: list[str]) -> None:
    for name in names:
        if not (base / name).exists():
            errors.append(f"arquivo obrigatorio ausente: {paths.rel(base / name)}")


def make_report(character_slug: str, build_slug: str, errors: list[str], warnings: list[str], suggestions: list[str], strict: bool) -> dict[str, Any]:
    status = "ok"
    if errors or (strict and warnings):
        status = "failed"
    elif warnings:
        status = "warning"
    return {
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "character_slug": character_slug,
        "build_slug": build_slug,
        "status": status,
        "strict": strict,
        "errors": list(dict.fromkeys(errors)),
        "warnings": list(dict.fromkeys(warnings)),
        "suggestions": list(dict.fromkeys(suggestions)),
    }


def validate_character(character_slug: str, strict: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []
    char_dir = paths.character_dir(character_slug)
    if not char_dir.exists():
        errors.append(f"personagem nao encontrado: {character_slug}")
        return make_report(character_slug, "", errors, warnings, suggestions, strict)

    validate_files(char_dir, REQUIRED_CHARACTER_FILES, errors)
    profile = read_json_checked(char_dir / "character_profile.json", errors)
    player_items = read_json_checked(char_dir / "player_items.json", errors)
    player_stats = read_json_checked(char_dir / "player_stats.json", errors)

    build_slug = str(profile.get("build_slug") or "")
    if not build_slug:
        errors.append(f"character_profile.json sem build_slug: {paths.rel(char_dir / 'character_profile.json')}")
        return make_report(character_slug, "", errors, warnings, suggestions, strict)

    profile_dir = paths.build_dir(build_slug)
    if not profile_dir.exists():
        errors.append(f"build associada nao encontrada: {build_slug}")
        return make_report(character_slug, build_slug, errors, warnings, suggestions, strict)

    validate_files(profile_dir, REQUIRED_BUILD_FILES, errors)
    build_profile = read_json_checked(profile_dir / "build_profile.json", errors)
    target_items = read_json_checked(profile_dir / "target_build_items.json", errors)
    target_stats = read_json_checked(profile_dir / "target_build_stats.json", errors)
    rules = read_json_checked(profile_dir / "upgrade_rules.json", errors)

    slots = item_slots(player_items)
    target_slots = item_slots(target_items)
    current_stats = numeric_stats(player_stats)
    if not slots:
        errors.append("player_items.json nao contem items com slots equipados")
    if not current_stats:
        warnings.append("player_stats.json nao contem stats numericos; comparacao ficara pobre")
    if not target_stat_keys(target_stats):
        errors.append("target_build_stats.json nao contem minimums/goals")

    for old_key, new_key in LEGACY_STAT_ALIASES.items():
        found = (
            old_key in current_stats
            or old_key in item_stat_keys(player_items)
            or old_key in target_stat_keys(target_stats)
            or old_key in rule_stat_references(rules)
        )
        if found:
            warnings.append(f"stat legado encontrado: {old_key}; prefira {new_key}")

    known_stats = current_stats.keys() | item_stat_keys(player_items) | target_stat_keys(target_stats) | PLANNER_EFFECT_KEYS
    weights = rules.get("weights", {})
    if isinstance(weights, dict):
        unknown_weight_keys = [key for key in weights if key not in known_stats and key not in rule_stat_references(rules, include_weights=False)]
        if unknown_weight_keys:
            warnings.append("weights sem stat conhecido nos arquivos atuais/alvo: " + ", ".join(sorted(unknown_weight_keys)))

    guarded_slots = rules.get("guarded_slots", rules.get("locked_slots", {}))
    if isinstance(guarded_slots, dict):
        missing_guarded = [slot for slot in guarded_slots if slot not in slots]
        if missing_guarded:
            warnings.append("guarded_slots nao existem no personagem atual: " + ", ".join(sorted(missing_guarded)))

    for profile_key, trade_profile in trade_profiles(rules).items():
        if not isinstance(trade_profile, dict):
            errors.append(f"trade_profile invalido: {profile_key}")
            continue
        replacement_slots = list_names(trade_profile.get("replacement_slots"))
        if not replacement_slots:
            warnings.append(f"trade_profile sem replacement_slots: {profile_key}")
        missing_slots = [slot for slot in replacement_slots if slot not in slots]
        if missing_slots:
            warnings.append(f"trade_profile {profile_key} mira slots ausentes: {', '.join(missing_slots)}")

    target_keys = target_stat_keys(target_stats)
    if build_profile.get("target_files_source") == "cloned_from_current":
        warnings.append("build alvo parece clonada de outra build; revise target_build_items/stats e upgrade_rules")
    if len(target_slots) < 3 and len(target_keys) < 5:
        suggestions.append("preencha mais slots ou metas em target_build_items/target_build_stats para comparacoes melhores")
    if len(current_stats) < 5:
        suggestions.append("preencha stats agregados do personagem em player_stats.json, idealmente vindos do PoB")
    if not trade_profiles(rules) and not rules.get("allow_legacy_trade_profiles"):
        suggestions.append("adicione trade_profiles em upgrade_rules.json para busca automatica especifica da build")

    return make_report(character_slug, build_slug, errors, warnings, suggestions, strict)
