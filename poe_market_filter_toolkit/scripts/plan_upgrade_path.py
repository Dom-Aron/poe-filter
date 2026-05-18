#!/usr/bin/env python3
"""
plan_upgrade_path.py

Build-aware upgrade planner for the Shockwave Cyclone / General's Cry Slayer.

It reads the current player items/stats, target build files and upgrade rules,
searches the official Path of Exile trade API through the existing profiles, and
tests 1-item, 2-item and 3-item purchase plans inside the user budget.

The output is intentionally conservative: when the budget is too small, the
market has too few offers, or a combo would break defensive floors, the report
says so instead of pretending there are ten good options.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import find_upgrade_deals as trade


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "market_config.json"
BUILDS_DIR = ROOT / "builds"
PLAYER_ITEMS = BUILDS_DIR / "player_items.json"
PLAYER_STATS = BUILDS_DIR / "player_stats.json"
TARGET_ITEMS = BUILDS_DIR / "target_build_items.json"
TARGET_STATS = BUILDS_DIR / "target_build_stats.json"
UPGRADE_RULES = BUILDS_DIR / "upgrade_rules.json"
REPORT_FILE = ROOT / "market" / "reports" / "upgrade_plan.md"


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

    if trade.has_text(texts, "Curse Enemies with Vulnerability on Hit"):
        effects["vulnerability_on_hit"] = 1.0
    if trade.has_text(texts, "Physical Damage to Attacks"):
        effects["physical_damage_to_attacks"] = 1.0
    if trade.has_text(texts, "Total Mana Cost"):
        effects["mana_cost_channeling"] = -3.0

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
) -> Candidate | None:
    item = row.get("raw_item", {})
    effects = candidate_effects(row["profile"], item)
    current = item_stats(player_items, slot)
    delta = dict(effects)
    warnings: list[str] = []

    for key, value in current.items():
        delta[key] = delta.get(key, 0.0) - value

    locked_slots = rules.get("locked_slots", {})
    if slot in locked_slots:
        return None

    if slot == "ring_1" and delta.get("mana_cost_channeling", 0.0) >= 0:
        warnings.append("bloqueado: trocar ring_1 remove o -mana cost do Cyclone")
        penalty = float(rules.get("penalties", {}).get("missing_mana_cost_when_replacing_ring_1", 80))
        delta["plan_penalty"] = delta.get("plan_penalty", 0.0) - penalty

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
    )


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
        "crit_multiplier": "crit multi",
        "physical_damage_to_attacks": "flat phys attacks",
        "staff_flat_physical": "flat phys staff",
        "maximum_life_percent": "% life",
        "staff_physical_damage_percent": "% phys staff",
        "staff_attack_speed_percent": "attack speed staff",
        "large_cluster_good_base": "cluster base util",
        "eight_passives": "cluster 8 passivas",
        "not_corrupted": "nao corrompido",
        "spell_block_during_effect": "spell block flask",
        "attack_block_during_effect": "attack block flask"
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
            if key in final:
                final[key] += value
    return final


def combo_score(
    candidates: tuple[Candidate, ...],
    final_stats: dict[str, float],
    target_stats: dict[str, Any],
    rules: dict[str, Any],
) -> tuple[float, list[str], list[str], bool]:
    weights = rules.get("weights", {})
    minimums = target_stats.get("minimums", {})
    goals = target_stats.get("goals", {})
    score = 0.0
    gains: list[str] = []
    warnings: list[str] = []

    for stat_name, minimum in minimums.items():
        value = final_stats.get(stat_name, 0.0)
        if value < float(minimum):
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
            weight = float(weights.get(key, 0.0))
            score += value * weight
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

    return score, gains[:10], warnings[:10], True


def make_plans(
    candidates: list[Candidate],
    budget_chaos: float,
    player_stats: dict[str, Any],
    target_stats: dict[str, Any],
    rules: dict[str, Any],
    max_combo_size: int,
) -> tuple[list[Plan], list[str]]:
    base_stats = {key: float(value) for key, value in player_stats.get("stats", {}).items() if isinstance(value, (int, float))}
    plans: list[Plan] = []
    diagnostics: list[str] = []

    for size in range(1, max_combo_size + 1):
        for combo in itertools.combinations(candidates, size):
            total_price = sum(candidate.price_chaos for candidate in combo)
            if total_price > budget_chaos:
                continue
            final_stats = final_stats_for_combo(base_stats, combo)
            score, gains, warnings, ok = combo_score(combo, final_stats, target_stats, rules)
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

    plans.sort(key=lambda plan: (plan.score, plan.value_score), reverse=True)
    return plans, diagnostics


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
                candidate = candidate_for_slot(row, slot, player_items, rules)
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
    return kept


def write_report(
    plans: list[Plan],
    candidates: list[Candidate],
    diagnostics: list[str],
    budget_chaos: float,
    league: str,
    top: int,
) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Upgrade Plan",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"League: `{league}`",
        f"Budget: `{budget_chaos:.1f} chaos`",
        "",
        "Este relatorio testa compras 1x1, 2x2 e 3x3. Ele pode mostrar menos que o top pedido quando o mercado nao tem ofertas suficientes ou quando as ofertas quebram pisos da build.",
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
                "- budget insuficiente;",
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
                "| Rank | Combo | Custo | Score | O que melhora | Alertas |",
                "| ---: | --- | ---: | ---: | --- | --- |",
            ]
        )
        for rank, plan in enumerate(plans[:top], start=1):
            combo = "<br>".join(f"[{c.name}]({c.trade_url}) -> `{c.slot}`" for c in plan.candidates)
            gains = "; ".join(dict.fromkeys(plan.gains)) or "Ganho estimado positivo."
            warnings = "; ".join(dict.fromkeys(plan.warnings[:5])) or "Sem alerta automatico."
            lines.append(
                f"| {rank} | {combo} | {plan.price_chaos:.1f}c | {plan.score:.1f} | {gains} | {warnings} |"
            )

    lines.extend(["", "## Candidatos Individuais Considerados", ""])
    if candidates:
        lines.append("| Perfil | Slot | Item | Preco | Ganhos/Perdas |")
        lines.append("| --- | --- | --- | ---: | --- |")
        for candidate in candidates[: max(top * 3, 10)]:
            gains = "; ".join(candidate.gains)
            lines.append(
                f"| {candidate.profile_label} | `{candidate.slot}` | [{candidate.name}]({candidate.trade_url}) | {candidate.price_text} | {gains} |"
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
            "- Se nao houver top 10, isso nao e erro: significa que o mercado/budget/filtros so produziram menos opcoes seguras.",
            "- Sempre valide no trade, PoE Overlay e PoB antes de comprar.",
            "",
        ]
    )

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan 1x1, 2x2 and 3x3 upgrade purchases for the current build.")
    parser.add_argument("--budget", required=True, help="Available budget, e.g. 251c, 1d, 1.5div.")
    parser.add_argument("--league", help="League name. Defaults to config/market_config.json.")
    parser.add_argument("--profiles", default="all", help="Comma list or all.")
    parser.add_argument("--top", type=int, default=10, help="Maximum plans to show.")
    parser.add_argument("--max-fetch", type=int, default=30, help="Max trade listings fetched per profile.")
    parser.add_argument("--max-combo-size", type=int, default=None, help="Override max combo size.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--player-items", type=Path, default=PLAYER_ITEMS)
    parser.add_argument("--player-stats", type=Path, default=PLAYER_STATS)
    parser.add_argument("--target-items", type=Path, default=TARGET_ITEMS)
    parser.add_argument("--target-stats", type=Path, default=TARGET_STATS)
    parser.add_argument("--rules", type=Path, default=UPGRADE_RULES)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = trade.load_config(args.config)
    league = args.league or config.get("league", "Mirage")
    user_agent = config.get("user_agent", "poe-market-filter-toolkit/1.0 (+personal loot filter project)")
    timeout = int(config.get("timeout_seconds", 30))
    delay = float(config.get("request_delay_seconds", 0.9))
    divine_price = trade.load_divine_price_chaos()
    budget_chaos = trade.parse_budget(args.budget, divine_price)

    player_items = load_json(args.player_items)
    player_stats = load_json(args.player_stats)
    target_items = load_json(args.target_items)
    target_stats = load_json(args.target_stats)
    rules = load_json(args.rules)
    max_combo_size = args.max_combo_size or int(rules.get("max_combo_size", 3))
    max_combo_size = max(1, min(3, max_combo_size))

    profiles = trade.make_profiles()
    if args.profiles == "all":
        selected = list(profiles.values())
    else:
        keys = [key.strip() for key in args.profiles.split(",") if key.strip()]
        unknown = [key for key in keys if key not in profiles]
        if unknown:
            raise SystemExit(f"Unknown profiles: {', '.join(unknown)}")
        selected = [profiles[key] for key in keys]

    print(f"League: {league}")
    print(f"Budget: {budget_chaos:.1f} chaos (Divine ~= {divine_price:.1f}c)")
    print("Loading trade stat metadata...")
    stats = trade.get_trade_stats(user_agent, timeout)

    rows_by_profile: dict[str, list[dict[str, Any]]] = {}
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
        time.sleep(delay)

    candidates = collect_candidates(rows_by_profile, target_items, player_items, rules)
    plans, diagnostics = make_plans(candidates, budget_chaos, player_stats, target_stats, rules, max_combo_size)
    write_report(plans, candidates, diagnostics, budget_chaos, league, args.top)

    if not plans:
        print("No safe plan found. See report for reasons.")
    else:
        print(f"Safe plans found: {len(plans)}")
        for rank, plan in enumerate(plans[: args.top], start=1):
            names = " + ".join(candidate.name for candidate in plan.candidates)
            print(f"{rank}. {names} | {plan.price_chaos:.1f}c | score {plan.score:.1f}")
    print(f"Report saved: {REPORT_FILE}")
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
    query_id, ids = trade.search_profile(profile, league, budget_chaos, stats, user_agent, timeout, max_fetch)
    if not query_id or not ids:
        return []
    time.sleep(delay)

    fetched = trade.fetch_results(ids, query_id, user_agent, timeout, delay)
    evaluated: list[dict[str, Any]] = []
    trade_url = f"{trade.TRADE_BASE}/trade/search/{league}/{query_id}"

    for entry in fetched:
        item = entry.get("item", {})
        listing = entry.get("listing", {})
        price = listing.get("price")
        price_chaos = trade.price_to_chaos(price, divine_price)
        if price_chaos is None or not math.isfinite(price_chaos) or price_chaos > budget_chaos:
            continue

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
                "trade_url": trade_url,
                "whisper": listing.get("whisper", ""),
                "raw_item": item,
            }
        )

    evaluated.sort(key=lambda item: (item["score"], item["value_score"]), reverse=True)
    return evaluated


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
