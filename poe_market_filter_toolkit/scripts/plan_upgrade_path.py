#!/usr/bin/env python3
"""
plan_upgrade_path.py

Build-aware upgrade planner for the active target build.

It reads the current player items/stats, target build files and upgrade rules,
searches the official Path of Exile trade API through the existing profiles, and
tests 1-item, 2-item and 3-item purchase plans inside the user budget.

The output is intentionally conservative: when the budget is too small, the
market has too few offers, or a combo would break defensive floors, the report
says so instead of pretending there are ten good options.
"""

from __future__ import annotations

import argparse
import html
import itertools
import json
import math
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import find_upgrade_deals as trade


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.time_utils import utc_now_iso

DEFAULT_CONFIG = ROOT / "config" / "market_config.json"
BUILDS_DIR = ROOT / "builds"
PLAYER_ITEMS = BUILDS_DIR / "player_items.json"
PLAYER_STATS = BUILDS_DIR / "player_stats.json"
TARGET_ITEMS = BUILDS_DIR / "target_build_items.json"
TARGET_STATS = BUILDS_DIR / "target_build_stats.json"
UPGRADE_RULES = BUILDS_DIR / "upgrade_rules.json"
ACTIVE_BUILD = BUILDS_DIR / "active_build.json"
REPORT_FILE = ROOT / "market" / "reports" / "upgrade_plan.md"
REPORT_HTML = ROOT / "market" / "reports" / "upgrade_plan.html"
REPORT_JSON = ROOT / "market" / "reports" / "upgrade_plan.json"
NO_BUDGET_SEARCH_LIMIT_CHAOS = math.inf


@dataclass(frozen=True)
class Candidate:
    profile: str
    profile_label: str
    slot: str
    name: str
    type_line: str
    price_chaos: float
    price_text: str
    score: float
    value_score: float
    effects: dict[str, float]
    gains: list[str]
    warnings: list[str]
    seller: str
    trade_url: str
    trade_item_url: str
    trade_search_url: str
    trade_fetch_url: str
    result_id: str
    query_id: str
    whisper: str
    item_mods: list[str]


@dataclass(frozen=True)
class Plan:
    candidates: tuple[Candidate, ...]
    price_chaos: float
    score: float
    value_score: float
    final_stats: dict[str, float]
    gains: list[str]
    warnings: list[str]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def active_build_slug(path: Path = ACTIVE_BUILD) -> str:
    if not path.exists():
        return ""
    return str(load_json(path).get("active_slug") or "")


def stat(data: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = data.get(key, default)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return default


def item_stats(player_items: dict[str, Any], slot: str) -> dict[str, float]:
    item = player_items.get("items", {}).get(slot, {})
    return {key: float(value) for key, value in item.get("stats", {}).items() if isinstance(value, (int, float))}


def safe_name(row: dict[str, Any]) -> str:
    name = f"{row.get('item_name', '')} {row.get('type_line', '')}".strip()
    return name or row.get("type_line") or "Item sem nome"


def add_effect(effects: dict[str, float], key: str, value: float) -> None:
    if value:
        effects[key] = effects.get(key, 0.0) + value


def numeric_mod_value_exact(texts: list[str], include: str, exclude: tuple[str, ...] = ()) -> float:
    include_lower = include.lower()
    exclude_lower = tuple(item.lower() for item in exclude)
    for text in texts:
        lower = text.lower()
        if include_lower in lower and not any(blocked in lower for blocked in exclude_lower):
            values = trade.all_numbers(text)
            return values[0] if values else 0.0
    return 0.0


def candidate_effects(profile: str, item: dict[str, Any]) -> dict[str, float]:
    texts = trade.item_texts(item)
    effects: dict[str, float] = {}

    life = trade.numeric_mod_value(texts, "to maximum Life")
    add_effect(effects, "life", life)
    add_effect(effects, "accuracy", trade.numeric_mod_value(texts, "to Accuracy Rating"))
    add_effect(effects, "attack_speed", trade.numeric_mod_value(texts, "increased Attack Speed"))
    add_effect(effects, "fire_resistance", trade.numeric_mod_value(texts, "to Fire Resistance"))
    add_effect(effects, "cold_resistance", trade.numeric_mod_value(texts, "to Cold Resistance"))
    add_effect(effects, "lightning_resistance", trade.numeric_mod_value(texts, "to Lightning Resistance"))
    add_effect(effects, "chaos_resistance", trade.numeric_mod_value(texts, "to Chaos Resistance"))
    all_res = trade.numeric_mod_value(texts, "to all Elemental Resistances")
    add_effect(effects, "fire_resistance", all_res)
    add_effect(effects, "cold_resistance", all_res)
    add_effect(effects, "lightning_resistance", all_res)
    add_effect(effects, "crit_multiplier", trade.numeric_mod_value(texts, "Global Critical Strike Multiplier"))
    add_effect(effects, "critical_strike_chance", trade.numeric_mod_value(texts, "increased Critical Strike Chance"))
    add_effect(effects, "elemental_damage_with_attacks", trade.numeric_mod_value(texts, "increased Elemental Damage with Attack Skills"))
    add_effect(effects, "elemental_damage", numeric_mod_value_exact(texts, "increased Elemental Damage", ("with Attack Skills",)))
    add_effect(effects, "projectile_damage", trade.numeric_mod_value(texts, "increased Projectile Damage"))
    add_effect(effects, "spell_damage", trade.numeric_mod_value(texts, "increased Spell Damage"))
    add_effect(effects, "lightning_damage", trade.numeric_mod_value(texts, "increased Lightning Damage"))
    add_effect(effects, "cast_speed", trade.numeric_mod_value(texts, "increased Cast Speed"))
    add_effect(effects, "totem_damage", trade.numeric_mod_value(texts, "increased Totem Damage"))

    if trade.has_text(texts, "Curse Enemies with Vulnerability on Hit"):
        effects["vulnerability_on_hit"] = 1.0
    if trade.has_text(texts, "Physical Damage to Attacks"):
        effects["physical_damage_to_attacks"] = 1.0
    if trade.has_text(texts, "Total Mana Cost"):
        effects["mana_cost_channeling"] = -3.0
    if trade.has_text(texts, "Level of all Lightning Spell Skill Gems"):
        effects["gem_level"] = 1.0

    if profile == "abyss_jewel":
        if trade.has_text(texts, "Added Physical Damage with Staff Attacks"):
            effects["staff_flat_physical"] = 1.0
        if trade.has_text(texts, "Onslaught"):
            effects["onslaught"] = 1.0
        if trade.has_text(texts, "Blind"):
            effects["blind"] = 1.0

    if profile == "jewel_damage":
        add_effect(effects, "maximum_life_percent", trade.numeric_mod_value(texts, "increased maximum Life"))
        add_effect(effects, "staff_physical_damage_percent", trade.numeric_mod_value(texts, "Physical Damage with Staves"))
        add_effect(effects, "staff_attack_speed_percent", trade.numeric_mod_value(texts, "Attack Speed with Staves"))

    if profile == "large_cluster":
        if trade.has_text(texts, "8 Passive Skills"):
            effects["eight_passives"] = 1.0
        if trade.has_text(texts, "Physical Damage") or trade.has_text(texts, "Staff Attacks"):
            effects["large_cluster_good_base"] = 1.0
        if trade.has_text(texts, "Impale"):
            effects["impale_chance"] = 8.0

    if profile == "rumi_uncorrupted":
        add_effect(effects, "attack_block_during_effect", trade.numeric_mod_value(texts, "Chance to Block Attack Damage during Effect"))
        add_effect(effects, "spell_block_during_effect", trade.numeric_mod_value(texts, "Chance to Block Spell Damage during Effect"))
        effects["not_corrupted"] = 1.0

    return effects


def candidate_for_slot(
    row: dict[str, Any],
    slot: str,
    player_items: dict[str, Any],
    rules: dict[str, Any],
    profile_rules: dict[str, Any],
) -> Candidate | None:
    item = row.get("raw_item", {})
    effects = candidate_effects(row["profile"], item)
    current = item_stats(player_items, slot)
    delta = dict(effects)
    warnings: list[str] = []

    for key, value in current.items():
        delta[key] = delta.get(key, 0.0) - value

    guarded_slots = rules.get("guarded_slots", rules.get("locked_slots", {}))
    required_keys = required_effects_for_slot(profile_rules, slot)
    for key in required_keys:
        if not preserves_required_effect(effects.get(key), current.get(key)):
            warnings.append(f"bloqueado: trocar {slot} nao preserva {key}")
            penalty_key = f"missing_{key}_when_replacing_{slot}"
            penalty = float(rules.get("penalties", {}).get(penalty_key, rules.get("penalties", {}).get("missing_required_effect", 80)))
            delta["plan_penalty"] = delta.get("plan_penalty", 0.0) - penalty

    if isinstance(guarded_slots, dict) and slot in guarded_slots:
        warnings.append(f"slot sensivel: {guarded_slots[slot]}")

    gains = describe_effects(delta)
    if not gains:
        gains = ["Sem ganho numerico claro; revisar manualmente."]

    return Candidate(
        profile=row["profile"],
        profile_label=row["profile_label"],
        slot=slot,
        name=safe_name(row),
        type_line=row.get("type_line", ""),
        price_chaos=float(row["price_chaos"]),
        price_text=trade.format_price(row.get("price"), float(row["price_chaos"])),
        score=float(row["score"]),
        value_score=float(row["value_score"]),
        effects=delta,
        gains=gains,
        warnings=warnings,
        seller=str(row.get("seller", "")),
        trade_url=str(row.get("trade_url", "")),
        trade_item_url=str(row.get("trade_item_url") or row.get("trade_url", "")),
        trade_search_url=str(row.get("trade_search_url") or row.get("trade_url", "")),
        trade_fetch_url=str(row.get("trade_fetch_url", "")),
        result_id=str(row.get("result_id", "")),
        query_id=str(row.get("query_id", "")),
        whisper=str(row.get("whisper", "")),
        item_mods=[str(mod) for mod in row.get("item_mods", [])],
    )


def required_effects_for_slot(profile_rules: dict[str, Any], slot: str) -> list[str]:
    keys: list[str] = []
    for field in (f"must_keep_if_replacing_{slot}", "must_keep"):
        value = profile_rules.get(field)
        if isinstance(value, list):
            keys.extend(str(item) for item in value)
    if slot == "ring_1":
        legacy = profile_rules.get("must_keep_if_replacing_ring_1")
        if isinstance(legacy, list):
            keys.extend(str(item) for item in legacy)
    return list(dict.fromkeys(keys))


def preserves_required_effect(candidate_value: float | None, current_value: float | None) -> bool:
    if current_value is None:
        return candidate_value is not None
    if current_value < 0:
        return candidate_value is not None and candidate_value <= current_value
    if current_value > 0:
        return candidate_value is not None and candidate_value >= min(current_value, 1.0)
    return candidate_value is not None


def describe_effects(effects: dict[str, float]) -> list[str]:
    labels = {
        "vulnerability_on_hit": "ganha Vulnerability on Hit",
        "life": "vida",
        "accuracy": "accuracy",
        "fire_resistance": "fire res",
        "cold_resistance": "cold res",
        "lightning_resistance": "lightning res",
        "chaos_resistance": "chaos res",
        "attack_speed": "attack speed",
        "critical_strike_chance": "crit chance",
        "crit_multiplier": "crit multi",
        "elemental_damage": "elemental damage",
        "elemental_damage_with_attacks": "elemental damage attacks",
        "projectile_damage": "projectile damage",
        "physical_damage_to_attacks": "flat phys attacks",
        "staff_flat_physical": "flat phys staff",
        "maximum_life_percent": "% life",
        "staff_physical_damage_percent": "% phys staff",
        "staff_attack_speed_percent": "attack speed staff",
        "large_cluster_good_base": "cluster base util",
        "eight_passives": "cluster 8 passivas",
        "not_corrupted": "nao corrompido",
        "spell_block_during_effect": "spell block flask",
        "attack_block_during_effect": "attack block flask",
        "spell_damage": "spell damage",
        "lightning_damage": "lightning damage",
        "cast_speed": "cast speed",
        "totem_damage": "totem damage",
        "gem_level": "+gem level"
    }
    out: list[str] = []
    for key, label in labels.items():
        value = effects.get(key, 0.0)
        if not value:
            continue
        if key in {"vulnerability_on_hit", "physical_damage_to_attacks", "staff_flat_physical", "large_cluster_good_base", "eight_passives", "not_corrupted"}:
            if value > 0:
                out.append(label)
        elif value > 0:
            out.append(f"+{value:g} {label}")
        elif value < 0:
            out.append(f"{value:g} {label}")
    return out[:8]


def final_stats_for_combo(base_stats: dict[str, float], candidates: tuple[Candidate, ...]) -> dict[str, float]:
    final = dict(base_stats)
    for candidate in candidates:
        for key, value in candidate.effects.items():
            if key in {"plan_penalty", "mana_cost_channeling"}:
                continue
            final[key] = final.get(key, 0.0) + value
    return final


def weighted_stat_contribution(
    key: str,
    value: float,
    base_stats: dict[str, float],
    final_stats: dict[str, float],
    target_stats: dict[str, Any],
    weights: dict[str, Any],
) -> float:
    weight = float(weights.get(key, 0.0))
    if not weight or not value:
        return 0.0
    goals = target_stats.get("goals", {}) if isinstance(target_stats.get("goals"), dict) else {}
    minimums = target_stats.get("minimums", {}) if isinstance(target_stats.get("minimums"), dict) else {}

    if isinstance(goals.get(key), (int, float)):
        goal = float(goals[key])
        before_gap = max(goal - base_stats.get(key, 0.0), 0.0)
        after_gap = max(goal - final_stats.get(key, 0.0), 0.0)
        return (before_gap - after_gap) * weight

    if isinstance(minimums.get(key), (int, float)):
        minimum = float(minimums[key])
        before_gap = max(minimum - base_stats.get(key, 0.0), 0.0)
        after_gap = max(minimum - final_stats.get(key, 0.0), 0.0)
        if before_gap or after_gap:
            return (before_gap - after_gap) * weight
        if value < 0:
            return value * weight
        return value * weight * 0.25

    return value * weight


def combo_score(
    candidates: tuple[Candidate, ...],
    base_stats: dict[str, float],
    final_stats: dict[str, float],
    target_stats: dict[str, Any],
    rules: dict[str, Any],
) -> tuple[float, list[str], list[str], bool]:
    weights = rules.get("weights", {})
    minimums = target_stats.get("minimums", {})
    goals = target_stats.get("goals", {})
    soft_minimums = set(rules.get("soft_minimum_stats", [])) if isinstance(rules.get("soft_minimum_stats"), list) else set()
    score = 0.0
    gains: list[str] = []
    warnings: list[str] = []

    for stat_name, minimum in minimums.items():
        value = final_stats.get(stat_name, 0.0)
        if value < float(minimum):
            if stat_name in soft_minimums:
                warnings.append(f"abaixo do minimo derivado: {stat_name} {value:g}/{minimum:g}; validar no PoB")
                continue
            warnings.append(f"rejeitado: {stat_name} ficaria {value:g}, abaixo do minimo {minimum:g}")
            return -math.inf, gains, warnings, False

    seen_profiles: set[str] = set()
    seen_slots: set[str] = set()
    for candidate in candidates:
        if candidate.profile in seen_profiles and candidate.profile not in {"jewel_damage"}:
            score -= float(rules.get("penalties", {}).get("same_profile_duplicate", 35))
        seen_profiles.add(candidate.profile)
        if candidate.slot in seen_slots:
            warnings.append(f"rejeitado: duas compras tentam ocupar o mesmo slot ({candidate.slot})")
            return -math.inf, gains, warnings, False
        seen_slots.add(candidate.slot)

        for key, value in candidate.effects.items():
            if key == "plan_penalty":
                score += value
                continue
            score += weighted_stat_contribution(key, value, base_stats, final_stats, target_stats, weights)
        gains.extend(candidate.gains)
        warnings.extend(candidate.warnings)

    for stat_name, goal in goals.items():
        current = final_stats.get(stat_name, 0.0)
        if current < float(goal):
            gap = float(goal) - current
            warnings.append(f"ainda abaixo da meta: {stat_name} {current:g}/{goal:g}")
        else:
            score += 15

    if score <= 0:
        warnings.append("rejeitado: ganho estimado nao supera perdas/riscos")
        return score, gains, warnings, False

    minimum_plan_score = float(rules.get("minimum_plan_score", 0))
    guarded_slots = rules.get("guarded_slots", rules.get("locked_slots", {}))
    guarded_minimum = float(rules.get("minimum_guarded_slot_score", minimum_plan_score))
    if score < minimum_plan_score:
        warnings.append(f"rejeitado: score {score:.1f} abaixo do ganho minimo {minimum_plan_score:.1f}")
        return score, gains, warnings, False
    if isinstance(guarded_slots, dict) and any(candidate.slot in guarded_slots for candidate in candidates):
        if score < guarded_minimum:
            warnings.append(f"rejeitado: troca em slot sensivel exige score minimo {guarded_minimum:.1f}")
            return score, gains, warnings, False

    return score, gains[:10], warnings[:10], True


def make_plans(
    candidates: list[Candidate],
    budget_chaos: float,
    player_stats: dict[str, Any],
    target_stats: dict[str, Any],
    rules: dict[str, Any],
    max_combo_size: int,
    cheapest_first: bool = False,
) -> tuple[list[Plan], list[str]]:
    base_stats = {key: float(value) for key, value in player_stats.get("stats", {}).items() if isinstance(value, (int, float))}
    plans: list[Plan] = []
    diagnostics: list[str] = []

    for size in range(1, max_combo_size + 1):
        for combo in itertools.combinations(candidates, size):
            total_price = sum(candidate.price_chaos for candidate in combo)
            if math.isfinite(budget_chaos) and total_price > budget_chaos:
                continue
            final_stats = final_stats_for_combo(base_stats, combo)
            score, gains, warnings, ok = combo_score(combo, base_stats, final_stats, target_stats, rules)
            if not ok:
                diagnostics.extend(warnings[:2])
                continue
            plans.append(
                Plan(
                    candidates=combo,
                    price_chaos=total_price,
                    score=score,
                    value_score=score / max(total_price, 1.0),
                    final_stats=final_stats,
                    gains=gains,
                    warnings=warnings,
                )
            )

    if cheapest_first:
        plans.sort(key=lambda plan: (plan.price_chaos, -plan.score, -plan.value_score))
    else:
        plans.sort(key=lambda plan: (plan.score, plan.value_score), reverse=True)
    return plans, diagnostics


def budget_price_windows(budget_chaos: float) -> list[tuple[float | None, float]]:
    """Return price windows used to sample trade listings across the whole budget.

    The trade API result list is sorted by price ascending. If we only fetch the
    first page with a high budget, we mostly see very cheap items. These windows
    keep the budget as a max price per upgrade plan while still sampling listings
    from the middle and upper part of the available budget.
    """
    if not math.isfinite(budget_chaos):
        return [(None, NO_BUDGET_SEARCH_LIMIT_CHAOS)]

    if budget_chaos <= 150:
        upper_bounds = [float(budget_chaos)]
    elif budget_chaos <= 500:
        upper_bounds = [round(budget_chaos * 0.35, 2), float(budget_chaos)]
    else:
        upper_bounds = [round(budget_chaos * 0.2, 2), round(budget_chaos * 0.6, 2), float(budget_chaos)]

    windows: list[tuple[float | None, float]] = []
    previous: float | None = None
    for upper in upper_bounds:
        if previous is not None and upper <= previous:
            continue
        windows.append((previous, upper))
        previous = upper
    return windows


def best_single_purchase_any_budget(
    candidates: list[Candidate],
    player_stats: dict[str, Any],
    target_stats: dict[str, Any],
    rules: dict[str, Any],
) -> list[Plan]:
    plans, _ = make_plans(
        candidates=candidates,
        budget_chaos=NO_BUDGET_SEARCH_LIMIT_CHAOS,
        player_stats=player_stats,
        target_stats=target_stats,
        rules=rules,
        max_combo_size=1,
        cheapest_first=False,
    )
    plans.sort(key=lambda plan: (plan.value_score, plan.score, -plan.price_chaos), reverse=True)
    return plans[:3]


def collect_candidates(
    rows_by_profile: dict[str, list[dict[str, Any]]],
    target_items: dict[str, Any],
    player_items: dict[str, Any],
    rules: dict[str, Any],
) -> list[Candidate]:
    candidates: list[Candidate] = []
    desired = target_items.get("desired_by_profile", {})
    max_per_profile = int(rules.get("max_candidates_per_profile", 8))

    for profile, rows in rows_by_profile.items():
        profile_rules = desired.get(profile, {})
        slots = profile_rules.get("replacement_slots", [])
        for row in rows[:max_per_profile]:
            for slot in slots:
                candidate = candidate_for_slot(row, slot, player_items, rules, profile_rules)
                if candidate:
                    candidates.append(candidate)

    candidates.sort(key=lambda candidate: (candidate.score, candidate.value_score), reverse=True)
    max_per_slot = int(rules.get("max_candidates_per_slot", 6))
    kept: list[Candidate] = []
    counts: dict[str, int] = {}
    for candidate in candidates:
        count = counts.get(candidate.slot, 0)
        if count >= max_per_slot:
            continue
        kept.append(candidate)
        counts[candidate.slot] = count + 1
    max_total = int(rules.get("max_total_candidates", 48))
    return kept[:max_total]


def write_report(
    plans: list[Plan],
    best_any_budget: list[Plan],
    candidates: list[Candidate],
    diagnostics: list[str],
    budget_chaos: float,
    league: str,
    top: int,
    cheapest_first: bool,
    output_md: Path,
    output_html: Path,
    output_json: Path,
    active_slug: str,
) -> None:
    output_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Upgrade Plan",
        "",
        f"Generated: {utc_now_iso()}",
        f"League: `{league}`",
        f"Budget: `{format_budget_label(budget_chaos)}`",
        f"Mode: `{'cheapest safe upgrades' if cheapest_first else 'best value inside budget'}`",
        "",
        "Este relatorio testa compras 1x1, 2x2 e 3x3. O budget e tratado como teto por plano de upgrade, nao como soma de todos os planos exibidos.",
        "Com budget informado, a busca amostra faixas de preco ate o teto para evitar que um budget alto retorne apenas os itens mais baratos.",
        "Ele pode mostrar menos que o top pedido quando o mercado nao tem ofertas suficientes, quando o budget nao cobre bons upgrades, ou quando as ofertas quebram pisos da build.",
        "",
    ]

    if not candidates:
        lines.extend(
            [
                "## Resultado",
                "",
                "Nenhum candidato bruto passou pelas buscas conservadoras dentro do budget.",
                "",
                "Possiveis motivos:",
                "",
                "- budget insuficiente ou nao informado para uma busca mais ampla;",
                "- mercado sem ofertas online para a liga atual;",
                "- build atual ja esta boa nos slots pesquisados;",
                "- filtros conservadores rejeitaram itens que seriam downgrade.",
                "",
            ]
        )
    elif not plans:
        lines.extend(
            [
                "## Resultado",
                "",
                "Foram encontrados candidatos no mercado, mas nenhuma combinacao passou os pisos de seguranca da build.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Melhores Planos",
                "",
                "| Rank | Combo | Custo | Score | O que melhora | Alertas | Whisper |",
                "| ---: | --- | ---: | ---: | --- | --- | --- |",
            ]
        )
        for rank, plan in enumerate(plans[:top], start=1):
            combo = "<br>".join(item_markdown_links(c) + f" -> `{c.slot}`" for c in plan.candidates)
            gains = "; ".join(dict.fromkeys(plan.gains)) or "Ganho estimado positivo."
            warnings = "; ".join(dict.fromkeys(plan.warnings[:5])) or "Sem alerta automatico."
            whispers = "<br>".join(f"`{c.whisper}`" for c in plan.candidates if c.whisper) or "n/d"
            lines.append(
                f"| {rank} | {combo} | {plan.price_chaos:.1f}c | {plan.score:.1f} | {gains} | {warnings} | {whispers} |"
            )

    if best_any_budget:
        lines.extend(
            [
                "",
                "## Melhor compra barata ignorando o budget",
                "",
                "Esta secao procura oportunidade de custo-beneficio mesmo quando voce informou um budget maior.",
                "",
                "| Rank | Item | Custo | Score | Valor | O que melhora |",
                "| ---: | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for rank, plan in enumerate(best_any_budget[:3], start=1):
            candidate = plan.candidates[0]
            gains = "; ".join(dict.fromkeys(plan.gains)) or "Ganho estimado positivo."
            lines.append(
                f"| {rank} | {item_markdown_links(candidate)} -> `{candidate.slot}` | {plan.price_chaos:.1f}c | {plan.score:.1f} | {plan.value_score:.2f} | {gains} |"
            )

    lines.extend(["", "## Candidatos Individuais Considerados", ""])
    if candidates:
        lines.append("| Perfil | Slot | Item | Preco | Ganhos/Perdas |")
        lines.append("| --- | --- | --- | ---: | --- |")
        for candidate in candidates[: max(top * 3, 10)]:
            gains = "; ".join(candidate.gains)
            lines.append(
                f"| {candidate.profile_label} | `{candidate.slot}` | {item_markdown_links(candidate)} | {candidate.price_text} | {gains} |"
            )
    else:
        lines.append("Nenhum candidato individual disponivel.")

    if diagnostics:
        unique = list(dict.fromkeys(diagnostics))[:12]
        lines.extend(["", "## Por Que Algumas Opcoes Foram Rejeitadas", ""])
        for note in unique:
            lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Como Ler",
            "",
            "- `1x1`: uma troca isolada.",
            "- `2x2`: duas compras que se compensam, por exemplo um anel que perde resistencia e outro item que recupera.",
            "- `3x3`: caminho maior dentro do budget.",
            "- O budget e teto de cada plano exibido. Exemplo: 1000c permite um plano de ate 1000c, nao dez planos somando 1000c.",
            "- Se nao houver top 10, isso nao e erro: significa que o mercado/budget/filtros so produziram menos opcoes seguras.",
            "- Sempre valide no trade, PoE Overlay e PoB antes de comprar.",
            "",
        ]
    )

    output_md.write_text("\n".join(lines), encoding="utf-8")
    write_json_report(
        plans,
        best_any_budget,
        candidates,
        diagnostics,
        budget_chaos,
        league,
        top,
        cheapest_first,
        output_json,
        active_slug,
    )
    write_html_report(
        plans,
        best_any_budget,
        candidates,
        diagnostics,
        budget_chaos,
        league,
        top,
        cheapest_first,
        output_html,
    )


def item_markdown_links(candidate: Candidate) -> str:
    links = [f"[{candidate.name}]({candidate.trade_item_url or candidate.trade_url})"]
    if candidate.trade_search_url:
        links.append(f"[busca]({candidate.trade_search_url})")
    if candidate.trade_fetch_url:
        links.append(f"[item/API]({candidate.trade_fetch_url})")
    return " / ".join(links)


def candidate_to_dict(candidate: Candidate) -> dict[str, Any]:
    return {
        "profile": candidate.profile,
        "profile_label": candidate.profile_label,
        "slot": candidate.slot,
        "name": candidate.name,
        "type_line": candidate.type_line,
        "price_chaos": candidate.price_chaos,
        "price_text": candidate.price_text,
        "score": candidate.score,
        "value_score": candidate.value_score,
        "effects": candidate.effects,
        "gains": candidate.gains,
        "warnings": candidate.warnings,
        "seller": candidate.seller,
        "trade_url": candidate.trade_item_url or candidate.trade_url,
        "trade_item_url": candidate.trade_item_url or candidate.trade_url,
        "trade_search_url": candidate.trade_search_url or candidate.trade_url,
        "trade_fetch_url": candidate.trade_fetch_url,
        "result_id": candidate.result_id,
        "query_id": candidate.query_id,
        "whisper": candidate.whisper,
        "item_mods": candidate.item_mods,
    }


def plan_to_dict(plan: Plan, rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "title": plan_title(plan),
        "price_chaos": plan.price_chaos,
        "score": plan.score,
        "value_score": plan.value_score,
        "final_stats": plan.final_stats,
        "gains": plan.gains,
        "warnings": plan.warnings,
        "candidates": [candidate_to_dict(candidate) for candidate in plan.candidates],
    }


def diagnostic_summary(diagnostics: list[str]) -> list[dict[str, Any]]:
    counts = Counter(diagnostics)
    return [
        {"reason": reason, "count": count}
        for reason, count in counts.most_common(12)
    ]


def write_json_report(
    plans: list[Plan],
    best_any_budget: list[Plan],
    candidates: list[Candidate],
    diagnostics: list[str],
    budget_chaos: float,
    league: str,
    top: int,
    cheapest_first: bool,
    output_json: Path,
    active_slug: str,
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "active_build_slug": active_slug,
        "league": league,
        "budget_label": format_budget_label(budget_chaos),
        "budget_chaos": None if not math.isfinite(budget_chaos) else budget_chaos,
        "mode": "cheapest safe upgrades" if cheapest_first else "best value inside budget",
        "notes": [
            "trade_item_url tenta abrir a listagem exata usando query_id e result_id.",
            "trade_search_url abre a busca oficial que produziu o resultado.",
            "trade_fetch_url aponta para a listagem especifica retornada pela API oficial.",
            "Se o item tiver sido vendido ou removido, o trade_item_url pode cair na busca ou nao mostrar mais o item; nesse caso, use trade_fetch_url para conferir o snapshot tecnico.",
            "whisper e o texto de contato mais direto para o item exato.",
            "budget_chaos e o teto de cada plano 1x1, 2x2 ou 3x3, nao a soma de todos os planos.",
            "Com budget informado, o script amostra faixas de preco ate o teto para nao limitar a busca aos itens mais baratos.",
        ],
        "plans": [plan_to_dict(plan, rank) for rank, plan in enumerate(plans[:top], start=1)],
        "best_any_budget": [plan_to_dict(plan, rank) for rank, plan in enumerate(best_any_budget[:3], start=1)],
        "candidates": [candidate_to_dict(candidate) for candidate in candidates],
        "diagnostics": list(dict.fromkeys(diagnostics))[:30],
        "diagnostic_summary": diagnostic_summary(diagnostics),
    }
    output_json.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def format_budget_label(budget_chaos: float) -> str:
    if not math.isfinite(budget_chaos):
        return "sem budget informado; mostrando upgrades seguros mais baratos"
    return f"{budget_chaos:.1f} chaos"


def plan_title(plan: Plan) -> str:
    return " + ".join(candidate.name for candidate in plan.candidates)


def html_join(items: list[str], empty: str = "Sem alerta automatico.") -> str:
    unique = list(dict.fromkeys(items))
    if not unique:
        return f"<span class=\"muted\">{html.escape(empty)}</span>"
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in unique[:8]) + "</ul>"


def item_mods_html(mods: list[str]) -> str:
    if not mods:
        return ""
    items = "".join(f"<li>{html.escape(mod)}</li>" for mod in mods[:12])
    return f"<details><summary>Mods lidos do item</summary><ul>{items}</ul></details>"


def write_html_report(
    plans: list[Plan],
    best_any_budget: list[Plan],
    candidates: list[Candidate],
    diagnostics: list[str],
    budget_chaos: float,
    league: str,
    top: int,
    cheapest_first: bool,
    output_html: Path,
) -> None:
    output_html.parent.mkdir(parents=True, exist_ok=True)
    generated = utc_now_iso()
    mode = "Top 3 upgrades seguros mais baratos" if cheapest_first else "Melhores planos dentro do budget"

    cards: list[str] = []
    if plans:
        for rank, plan in enumerate(plans[:top], start=1):
            item_links = []
            for candidate in plan.candidates:
                actions = []
                if candidate.trade_item_url:
                    actions.append(
                        f"<a href=\"{html.escape(candidate.trade_item_url)}\" target=\"_blank\" rel=\"noopener\" title=\"Tenta abrir a listagem exata pelo result_id\">Item exato</a>"
                    )
                if candidate.trade_search_url:
                    actions.append(
                        f"<a href=\"{html.escape(candidate.trade_search_url)}\" target=\"_blank\" rel=\"noopener\">Busca original</a>"
                    )
                if candidate.trade_fetch_url:
                    actions.append(
                        f"<a href=\"{html.escape(candidate.trade_fetch_url)}\" target=\"_blank\" rel=\"noopener\">JSON tecnico</a>"
                    )
                whisper = ""
                if candidate.whisper:
                    whisper = (
                        "<label>Whisper"
                        f"<textarea readonly>{html.escape(candidate.whisper)}</textarea>"
                        "</label>"
                    )
                item_links.append(
                    "<div class=\"item-link\">"
                    f"<strong>{html.escape(candidate.name)}</strong>"
                    f"<span>{html.escape(candidate.profile_label)} -> {html.escape(candidate.slot)}</span>"
                    f"<small>{html.escape(candidate.price_text)} | vendedor: {html.escape(candidate.seller or 'n/d')}</small>"
                    f"<div class=\"actions\">{' '.join(actions)}</div>"
                    f"{item_mods_html(candidate.item_mods)}"
                    f"{whisper}"
                    "</div>"
                )
            cards.append(
                "<section class=\"card\">"
                f"<div class=\"rank\">#{rank}</div>"
                f"<h2>{html.escape(plan_title(plan))}</h2>"
                f"<p class=\"price\">{plan.price_chaos:.1f} chaos</p>"
                f"<p class=\"score\">Score {plan.score:.1f} | Valor {plan.value_score:.2f}</p>"
                "<div class=\"grid\">"
                f"<div><h3>Itens</h3>{''.join(item_links)}</div>"
                f"<div><h3>Melhoras</h3>{html_join(plan.gains, 'Ganho estimado positivo.')}</div>"
                f"<div><h3>Alertas</h3>{html_join(plan.warnings)}</div>"
                "</div>"
                "</section>"
            )
    else:
        cards.append(
            "<section class=\"card\">"
            "<h2>Nenhum plano seguro encontrado</h2>"
            "<p>O budget pode ser insuficiente, o mercado pode nao ter ofertas boas agora, ou os filtros rejeitaram downgrades.</p>"
            "</section>"
        )

    best_cards: list[str] = []
    for rank, plan in enumerate(best_any_budget[:3], start=1):
        candidate = plan.candidates[0]
        actions = []
        if candidate.trade_item_url:
            actions.append(
                f"<a href=\"{html.escape(candidate.trade_item_url)}\" target=\"_blank\" rel=\"noopener\" title=\"Tenta abrir a listagem exata pelo result_id\">Item exato</a>"
            )
        if candidate.trade_search_url:
            actions.append(
                f"<a href=\"{html.escape(candidate.trade_search_url)}\" target=\"_blank\" rel=\"noopener\">Busca original</a>"
            )
        if candidate.trade_fetch_url:
            actions.append(
                f"<a href=\"{html.escape(candidate.trade_fetch_url)}\" target=\"_blank\" rel=\"noopener\">JSON tecnico</a>"
            )
        best_cards.append(
            "<section class=\"card\">"
            f"<div class=\"rank\">#{rank}</div>"
            f"<h2>{html.escape(candidate.name)}</h2>"
            f"<p class=\"price\">{plan.price_chaos:.1f} chaos</p>"
            f"<p class=\"score\">Score {plan.score:.1f} | Valor {plan.value_score:.2f}</p>"
            f"<p class=\"muted\">Compra barata de melhor custo-beneficio, calculada sem limitar pelo budget informado.</p>"
            f"<div class=\"actions\">{' '.join(actions)}</div>"
            f"{item_mods_html(candidate.item_mods)}"
            f"{html_join(plan.gains, 'Ganho estimado positivo.')}"
            "</section>"
        )

    candidate_rows = []
    for candidate in candidates[: max(top * 4, 12)]:
        extra_links = []
        if candidate.trade_search_url:
            extra_links.append(f"<a href=\"{html.escape(candidate.trade_search_url)}\" target=\"_blank\" rel=\"noopener\">busca</a>")
        if candidate.trade_fetch_url:
            extra_links.append(f"<a href=\"{html.escape(candidate.trade_fetch_url)}\" target=\"_blank\" rel=\"noopener\">JSON tecnico</a>")
        extra = " | " + " | ".join(extra_links) if extra_links else ""
        item_url = candidate.trade_item_url or candidate.trade_url or candidate.trade_search_url
        candidate_rows.append(
            "<tr>"
            f"<td>{html.escape(candidate.profile_label)}</td>"
            f"<td>{html.escape(candidate.slot)}</td>"
            f"<td><a href=\"{html.escape(item_url)}\" target=\"_blank\" rel=\"noopener\">{html.escape(candidate.name)}</a>{extra}</td>"
            f"<td>{html.escape(candidate.price_text)}</td>"
            f"<td>{html.escape('; '.join(candidate.gains))}</td>"
            "</tr>"
        )

    diagnostics_html = ""
    if diagnostics:
        summary_rows = "".join(
            f"<tr><td>{html.escape(row['reason'])}</td><td>{row['count']}</td></tr>"
            for row in diagnostic_summary(diagnostics)
        )
        sample_items = "".join(f"<li>{html.escape(note)}</li>" for note in list(dict.fromkeys(diagnostics))[:12])
        diagnostics_html = (
            "<h3>Resumo de motivos</h3>"
            "<table><thead><tr><th>Motivo</th><th>Ocorrencias</th></tr></thead>"
            f"<tbody>{summary_rows}</tbody></table>"
            "<h3>Amostra</h3>"
            f"<ul>{sample_items}</ul>"
        )

    content = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PoE Upgrade Plan</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #111315; color: #ece7dc; }}
    header {{ padding: 24px 32px; background: #1c2024; border-bottom: 1px solid #343a40; }}
    main {{ padding: 24px 32px 48px; max-width: 1200px; margin: 0 auto; }}
    h1, h2, h3 {{ margin: 0 0 12px; }}
    .meta {{ color: #b7b0a2; display: flex; gap: 16px; flex-wrap: wrap; }}
    .quick-links {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .quick-links a {{ padding: 8px 10px; border: 1px solid #38424c; border-radius: 6px; background: #20262c; }}
    .card {{ position: relative; background: #1b1e21; border: 1px solid #373d42; border-radius: 8px; padding: 20px; margin-bottom: 18px; }}
    .rank {{ position: absolute; right: 18px; top: 16px; color: #d9b36a; font-weight: 700; }}
    .price {{ font-size: 22px; color: #f2c66d; margin: 6px 0; }}
    .score, .muted {{ color: #b7b0a2; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }}
    .item-link {{ display: grid; gap: 4px; margin-bottom: 12px; }}
    .item-link span, small {{ color: #b7b0a2; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }}
    .actions a {{ padding: 6px 8px; border: 1px solid #3f596e; border-radius: 6px; background: #202a32; }}
    label {{ display: grid; gap: 4px; color: #b7b0a2; margin-top: 6px; }}
    details {{ margin-top: 8px; border: 1px solid #30363b; border-radius: 6px; padding: 8px; background: #15191d; }}
    summary {{ cursor: pointer; color: #d9b36a; }}
    textarea {{ min-height: 48px; resize: vertical; border: 1px solid #373d42; border-radius: 6px; background: #111315; color: #ece7dc; padding: 8px; font: 12px Consolas, monospace; }}
    a {{ color: #8bc5ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin-bottom: 6px; }}
    table {{ width: 100%; border-collapse: collapse; background: #1b1e21; border: 1px solid #373d42; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #30363b; text-align: left; vertical-align: top; }}
    th {{ color: #d9b36a; background: #20252a; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} main, header {{ padding-left: 16px; padding-right: 16px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>PoE Upgrade Plan</h1>
    <div class="meta">
      <span>Gerado: {html.escape(generated)}</span>
      <span>Liga: {html.escape(league)}</span>
      <span>Budget: {html.escape(format_budget_label(budget_chaos))}</span>
      <span>Modo: {html.escape(mode)}</span>
    </div>
    <div class="quick-links">
      <a href="build_dashboard.html">Dashboard</a>
      <a href="upgrade_recommendations.html">Recomendacoes</a>
      <a href="next_searches.html">Proximas buscas</a>
      <a href="market_report.html">Mercado</a>
    </div>
  </header>
  <main>
    <p class="muted">Abra os links em azul para acessar o trade oficial. Sempre confira no PoE Overlay e no PoB antes de comprar.</p>
    {''.join(cards)}
    {'<h2>Melhor compra barata sem usar o budget como limite</h2>' + ''.join(best_cards) if best_cards else ''}
    <h2>Candidatos individuais considerados</h2>
    <table>
      <thead><tr><th>Perfil</th><th>Slot</th><th>Item</th><th>Preco</th><th>Leitura</th></tr></thead>
      <tbody>{''.join(candidate_rows) if candidate_rows else '<tr><td colspan="5">Nenhum candidato individual disponivel.</td></tr>'}</tbody>
    </table>
    {'<h2>Por que algumas opcoes foram rejeitadas</h2>' + diagnostics_html if diagnostics_html else ''}
  </main>
</body>
</html>
"""
    output_html.write_text(content, encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan 1x1, 2x2 and 3x3 upgrade purchases for the current build.")
    parser.add_argument("--budget", help="Budget per upgrade plan, e.g. 251c, 1d, 1.5div. If omitted, shows top 3 cheapest safe upgrades.")
    parser.add_argument("--league", help="League name. Defaults to config/market_config.json.")
    parser.add_argument("--profiles", default="all", help="Comma list or all.")
    parser.add_argument("--top", type=int, default=None, help="Maximum plans to show. Defaults to 3 without budget and 10 with budget.")
    parser.add_argument("--max-fetch", type=int, default=30, help="Max trade listings fetched per profile.")
    parser.add_argument("--max-combo-size", type=int, default=None, help="Override max combo size.")
    parser.add_argument("--request-delay", type=float, default=None, help="Seconds to wait between trade API requests. Defaults to market_config.json.")
    parser.add_argument(
        "--best-any-budget-mode",
        choices=("reuse", "extra", "off"),
        default="reuse",
        help=(
            "How to build the 'best cheap buy ignoring budget' section. "
            "'reuse' uses already fetched rows and avoids extra API calls; "
            "'extra' performs separate no-budget searches; 'off' disables it."
        ),
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--player-items", type=Path, default=PLAYER_ITEMS)
    parser.add_argument("--player-stats", type=Path, default=PLAYER_STATS)
    parser.add_argument("--target-items", type=Path, default=TARGET_ITEMS)
    parser.add_argument("--target-stats", type=Path, default=TARGET_STATS)
    parser.add_argument("--rules", type=Path, default=UPGRADE_RULES)
    parser.add_argument("--active-build", type=Path, default=ACTIVE_BUILD)
    parser.add_argument("--output-md", type=Path, default=REPORT_FILE)
    parser.add_argument("--output-html", type=Path, default=REPORT_HTML)
    parser.add_argument("--output-json", type=Path, default=REPORT_JSON)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = trade.load_config(args.config)
    league = args.league or config.get("league", "Mirage")
    user_agent = config.get("user_agent", "poe-market-filter-toolkit/1.0 (+personal loot filter project)")
    timeout = int(config.get("timeout_seconds", 30))
    delay = float(args.request_delay if args.request_delay is not None else config.get("request_delay_seconds", 0.9))
    divine_price = trade.load_divine_price_chaos()
    cheapest_first = not bool(args.budget)
    budget_chaos = trade.parse_budget(args.budget, divine_price) if args.budget else NO_BUDGET_SEARCH_LIMIT_CHAOS
    top = args.top if args.top is not None else (3 if cheapest_first else 10)

    player_items = load_json(args.player_items)
    player_stats = load_json(args.player_stats)
    target_items = load_json(args.target_items)
    target_stats = load_json(args.target_stats)
    rules = load_json(args.rules)
    max_combo_size = args.max_combo_size or (1 if cheapest_first else int(rules.get("max_combo_size", 3)))
    max_combo_size = max(1, min(3, max_combo_size))

    profiles = trade.make_profiles(args.rules)
    if args.profiles == "all":
        selected = list(profiles.values())
    else:
        keys = [key.strip() for key in args.profiles.split(",") if key.strip()]
        unknown = [key for key in keys if key not in profiles]
        if unknown:
            raise SystemExit(f"Unknown profiles: {', '.join(unknown)}")
        selected = [profiles[key] for key in keys]

    print(f"League: {league}")
    print(f"Budget: {format_budget_label(budget_chaos)} (Divine ~= {divine_price:.1f}c)")
    print("Loading trade stat metadata...")
    stats = trade.get_trade_stats(user_agent, timeout)

    rows_by_profile: dict[str, list[dict[str, Any]]] = {}
    rows_by_profile_any_budget: dict[str, list[dict[str, Any]]] = {}
    for profile in selected:
        print(f"Searching: {profile.label}")
        try:
            rows = evaluate_profile_with_raw_items(
                profile=profile,
                league=league,
                budget_chaos=budget_chaos,
                divine_price=divine_price,
                stats=stats,
                user_agent=user_agent,
                timeout=timeout,
                delay=delay,
                max_fetch=args.max_fetch,
            )
        except Exception as exc:
            print(f"[warning] profile failed: {profile.key}: {exc}")
            rows = []
        rows_by_profile[profile.key] = rows
        print(f"  accepted candidates: {len(rows)}")
        if args.best_any_budget_mode == "off":
            rows_by_profile_any_budget[profile.key] = []
        elif args.best_any_budget_mode == "reuse" or not math.isfinite(budget_chaos):
            rows_by_profile_any_budget[profile.key] = rows
        elif math.isfinite(budget_chaos):
            try:
                rows_any = evaluate_profile_with_raw_items(
                    profile=profile,
                    league=league,
                    budget_chaos=NO_BUDGET_SEARCH_LIMIT_CHAOS,
                    divine_price=divine_price,
                    stats=stats,
                    user_agent=user_agent,
                    timeout=timeout,
                    delay=delay,
                    max_fetch=args.max_fetch,
                )
            except Exception as exc:
                print(f"[warning] profile best-any-budget failed: {profile.key}: {exc}")
                rows_any = []
            rows_by_profile_any_budget[profile.key] = rows_any
        time.sleep(delay)

    candidates = collect_candidates(rows_by_profile, target_items, player_items, rules)
    any_budget_candidates = collect_candidates(rows_by_profile_any_budget, target_items, player_items, rules)
    plans, diagnostics = make_plans(candidates, budget_chaos, player_stats, target_stats, rules, max_combo_size)
    best_any_budget = best_single_purchase_any_budget(any_budget_candidates, player_stats, target_stats, rules)
    if cheapest_first:
        plans = plans[:top]
    write_report(
        plans,
        best_any_budget,
        candidates,
        diagnostics,
        budget_chaos,
        league,
        top,
        cheapest_first,
        args.output_md,
        args.output_html,
        args.output_json,
        active_build_slug(args.active_build),
    )

    if not plans:
        print("No safe plan found. See report for reasons.")
    else:
        print(f"Safe plans found: {len(plans)}")
        for rank, plan in enumerate(plans[:top], start=1):
            names = " + ".join(candidate.name for candidate in plan.candidates)
            print(f"{rank}. {names} | {plan.price_chaos:.1f}c | score {plan.score:.1f}")
    print(f"Report saved: {args.output_md}")
    print(f"HTML report saved: {args.output_html}")
    print(f"JSON report saved: {args.output_json}")
    return 0


def evaluate_profile_with_raw_items(
    profile: trade.Profile,
    league: str,
    budget_chaos: float,
    divine_price: float,
    stats: list[dict[str, str]],
    user_agent: str,
    timeout: int,
    delay: float,
    max_fetch: int,
) -> list[dict[str, Any]]:
    result_sets = search_profile_optional_budget(profile, league, budget_chaos, stats, user_agent, timeout, max_fetch)
    if not result_sets:
        return []
    evaluated: list[dict[str, Any]] = []
    seen_result_ids: set[str] = set()

    for query_id, ids in result_sets:
        ids = [result_id for result_id in ids if result_id not in seen_result_ids]
        if not ids:
            continue
        seen_result_ids.update(ids)
        time.sleep(delay)

        fetched = trade.fetch_results(ids, query_id, user_agent, timeout, delay)
        trade_url = f"{trade.TRADE_BASE}/trade/search/{league}/{query_id}"

        for entry in fetched:
            result_id = str(entry.get("id") or "")
            item = entry.get("item", {})
            listing = entry.get("listing", {})
            price = listing.get("price")
            price_chaos = trade.price_to_chaos(price, divine_price)
            if price_chaos is None or not math.isfinite(price_chaos):
                continue
            if math.isfinite(budget_chaos) and price_chaos > budget_chaos:
                continue
            trade_item_url = f"{trade_url}/{result_id}" if result_id else trade_url

            score, reasons = trade.score_item(profile, item)
            baseline_delta, baseline_notes, passes_baseline = trade.baseline_adjustment(profile, item)
            if not passes_baseline:
                continue
            score += baseline_delta
            reasons.extend(baseline_notes)
            if score < profile.min_score:
                continue
            value_score = score / max(price_chaos, 1.0)
            evaluated.append(
                {
                    "profile": profile.key,
                    "profile_label": profile.label,
                    "why": profile.why,
                    "item_name": item.get("name") or "",
                    "type_line": item.get("typeLine") or item.get("baseType") or "",
                    "ilvl": item.get("ilvl"),
                    "price": price,
                    "price_chaos": price_chaos,
                    "score": score,
                    "value_score": value_score,
                    "reasons": reasons,
                    "seller": listing.get("account", {}).get("name", ""),
                    "trade_url": trade_item_url,
                    "trade_item_url": trade_item_url,
                    "trade_search_url": trade_url,
                    "trade_fetch_url": f"{trade.TRADE_BASE}/api/trade/fetch/{result_id}?query={query_id}" if result_id else "",
                    "result_id": result_id,
                    "query_id": query_id,
                    "whisper": listing.get("whisper", ""),
                    "item_mods": trade.item_texts(item),
                    "raw_item": item,
                }
            )

    evaluated.sort(key=lambda item: (item["score"], item["value_score"]), reverse=True)
    return evaluated


def search_profile_optional_budget(
    profile: trade.Profile,
    league: str,
    budget_chaos: float,
    stats: list[dict[str, str]],
    user_agent: str,
    timeout: int,
    max_fetch: int,
) -> list[tuple[str, list[str]]]:
    if math.isfinite(budget_chaos):
        return search_profile_budget_windows(profile, league, budget_chaos, stats, user_agent, timeout, max_fetch)

    query = trade.with_required_stats(
        profile.query,
        stats,
        profile.required_stat_texts,
        profile.count_stat_texts,
        profile.count_min,
    )
    payload = {"query": query, "sort": {"price": "asc"}}
    data = trade.request_json(f"{trade.TRADE_BASE}/api/trade/search/{league}", user_agent, timeout, method="POST", payload=payload)
    query_id = data.get("id")
    if not query_id:
        return []
    return [(str(query_id), list(data.get("result", []))[:max_fetch])]


def search_profile_budget_windows(
    profile: trade.Profile,
    league: str,
    budget_chaos: float,
    stats: list[dict[str, str]],
    user_agent: str,
    timeout: int,
    max_fetch: int,
) -> list[tuple[str, list[str]]]:
    windows = budget_price_windows(budget_chaos)
    fetch_per_window = max(3, math.ceil(max_fetch / max(len(windows), 1)))
    result_sets: list[tuple[str, list[str]]] = []
    for minimum, maximum in windows:
        query = trade.with_required_stats(
            profile.query,
            stats,
            profile.required_stat_texts,
            profile.count_stat_texts,
            profile.count_min,
        )
        query["filters"] = trade.merge_filters(query.get("filters", {}), trade.make_price_filter(maximum, minimum))
        payload = {"query": query, "sort": {"price": "asc"}}
        data = trade.request_json(f"{trade.TRADE_BASE}/api/trade/search/{league}", user_agent, timeout, method="POST", payload=payload)
        query_id = data.get("id")
        if query_id:
            result_sets.append((str(query_id), list(data.get("result", []))[:fetch_per_window]))
    return result_sets


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
