#!/usr/bin/env python3
"""
recommend_next_steps.py

Generates practical next searches and upgrade recommendations from the current
gap analysis. This is a deterministic MVP for the future local AI agent: it
does not invent mechanics, does not call a model, and keeps recommendations
grounded in gap_analysis.json plus the build rules.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAP = ROOT / "data" / "generated" / "gap_analysis.json"
DEFAULT_RULES = ROOT / "builds" / "upgrade_rules.json"
DEFAULT_ACTIVE_BUILD = ROOT / "builds" / "active_build.json"
DEFAULT_ACTIVE_CHARACTER = ROOT / "builds" / "active_character.json"
DEFAULT_NEXT_SEARCHES = ROOT / "data" / "generated" / "next_searches.md"
DEFAULT_RECOMMENDATIONS = ROOT / "data" / "generated" / "upgrade_recommendations.md"
DEFAULT_REPORT_JSON = ROOT / "data" / "generated" / "upgrade_report.json"


LEGACY_SEARCH_LIBRARY: dict[str, dict[str, Any]] = {
    "life": {
        "title": "Jewel com maximum life",
        "priority": "alta",
        "reason": "Vida esta abaixo da meta e jewels permitem melhorar sem mexer em slots sensiveis.",
        "trade_terms": [
            "6-7% increased maximum Life",
            "Attack Speed with Staves ou Two Handed Melee Weapons",
            "Global Critical Strike Multiplier",
            "Physical Damage with Staves",
            "Chaos Resistance se possivel",
        ],
        "price_hint": "Ate 30c: bom; 30-80c: comprar se tiver vida + 2 mods uteis; acima disso, comparar no PoB.",
        "profiles": ["jewel_damage", "abyss_jewel"],
    },
    "chaos_resistance": {
        "title": "Jewel/anel/cinto com Chaos Resistance",
        "priority": "alta",
        "reason": "Chaos Resistance esta positiva, mas abaixo da meta confortavel.",
        "trade_terms": [
            "+#% to Chaos Resistance",
            "+# to maximum Life",
            "mods de dano fisico/attack speed/crit se for jewel",
            "nao perder resistencias elementais capadas",
        ],
        "price_hint": "Barato em jewels simples; em anel com Vulnerability fica mais caro.",
        "profiles": ["jewel_damage", "abyss_jewel", "ring_vulnerability"],
    },
    "impale_chance": {
        "title": "Cluster/jewel com Impale ou dano fisico",
        "priority": "alta",
        "reason": "Chance de Impale esta longe da meta da build fisica.",
        "trade_terms": [
            "Large Cluster Jewel com 8 passivas",
            "Physical Damage / Staff Attacks / Two Handed Weapons",
            "notables uteis como Fuel the Fight, Martial Prowess ou equivalentes",
            "evitar bases elemental, minion, bow ou spell",
        ],
        "price_hint": "Cluster bom depende dos notables; nao comprar sem abrir o item no trade.",
        "profiles": ["large_cluster"],
    },
    "spell_block": {
        "title": "Rumi's nao corrompido ou fontes de spell block",
        "priority": "media",
        "reason": "Spell Block ainda esta abaixo da meta defensiva.",
        "trade_terms": [
            "Rumi's Concoction nao corrompido",
            "pelo menos 12% attack block durante efeito",
            "pelo menos 4% spell block durante efeito",
            "idealmente permitir enchant automatico depois",
        ],
        "price_hint": "Compra de qualidade de vida; nao pagar caro se o atual 12/4 ainda funciona.",
        "profiles": ["rumi_uncorrupted"],
    },
    "ailment_avoidance": {
        "title": "Ailment avoidance sem quebrar gear atual",
        "priority": "media",
        "reason": "Avoidance esta baixo, mas pode ser resolvido por arvore, flask ou crafts depois.",
        "trade_terms": [
            "chance to Avoid Elemental Ailments",
            "flask suffixes uteis",
            "boots/crafts apenas se nao perder vida/resists",
        ],
        "price_hint": "Tratar como defesa futura; so vale trocar botas se o ganho total compensar vida, resists e velocidade.",
        "profiles": [],
    },
    "chance_to_hit": {
        "title": "Accuracy apenas se vier junto de outros mods",
        "priority": "baixa",
        "reason": "Chance to hit esta acima do minimo; accuracy extra nao deve dominar o score.",
        "trade_terms": [
            "+# to Accuracy Rating",
            "comprar apenas se vier com life/dano/chaos res",
        ],
        "price_hint": "Nao gastar budget alto so para accuracy.",
        "profiles": ["jewel_damage"],
    },
    "chance_to_hit_evasive": {
        "title": "Accuracy contra evasivos como bonus",
        "priority": "baixa",
        "reason": "Contra evasivos ainda ha espaco, mas nao e gargalo principal como antes.",
        "trade_terms": [
            "Accuracy Rating como mod secundario",
            "preferir jewel com life + dano + accuracy",
        ],
        "price_hint": "Bonus, nao prioridade de compra isolada.",
        "profiles": ["jewel_damage"],
    },
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}. Run compare_current_to_target.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def priority_rank(priority: str) -> int:
    return {
        "very_high": 0,
        "muito_alta": 0,
        "high": 1,
        "alta": 1,
        "medium": 2,
        "media": 2,
        "low": 4,
        "baixa": 4,
        "needs_data": 5,
    }.get(priority, 3)


def active_search_library(rules: dict[str, Any]) -> dict[str, dict[str, Any]]:
    configured = rules.get("search_library")
    if isinstance(configured, dict) and configured:
        return {str(key): value for key, value in configured.items() if isinstance(value, dict)}
    if rules.get("allow_legacy_search_library"):
        return LEGACY_SEARCH_LIBRARY
    return {}


def search_entries(gap: dict[str, Any], rules: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    library = active_search_library(rules or {})
    priorities = gap.get("current_priorities", {})
    risks = gap.get("risks", {})
    entries: list[dict[str, Any]] = []
    for stat_name, risk in risks.items():
        template = library.get(stat_name)
        if not template:
            continue
        priority = priorities.get(stat_name, "high")
        entry = {
            "stat": stat_name,
            "status": risk.get("status"),
            "current": risk.get("current"),
            "minimum": risk.get("minimum"),
            "goal": risk.get("goal"),
            "missing_to_minimum": risk.get("missing_to_minimum"),
            "missing_to_goal": risk.get("missing_to_goal"),
            "priority": priority,
            **template,
        }
        if stat_name in {"chance_to_hit", "chance_to_hit_evasive"} and risk.get("current", 0) >= 94:
            entry["priority"] = "low"
            entry["priority_pt"] = "baixa"
        entries.append(entry)

    entries.sort(key=lambda item: (priority_rank(str(item["priority"])), -(item.get("missing_to_goal") or 0)))
    return entries


def gap_context(entry: dict[str, Any]) -> str:
    status = str(entry.get("status") or "unknown")
    current = entry.get("current")
    minimum = entry.get("minimum")
    goal = entry.get("goal")
    missing = entry.get("missing_to_minimum")
    label = "minimo"
    if not isinstance(missing, (int, float)):
        missing = entry.get("missing_to_goal")
        label = "meta"
    missing_text = f"; falta {missing:g} ate {label}" if isinstance(missing, (int, float)) else ""
    return f"status={status}; atual={current}; minimo={minimum}; meta={goal}{missing_text}"


def write_next_searches(path: Path, entries: list[dict[str, Any]]) -> None:
    lines = [
        "# Proximas buscas recomendadas",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    if not entries:
        lines.append("Nenhuma busca recomendada com os dados atuais.")
        lines.append("")
        lines.append("Possiveis motivos:")
        lines.append("- A build nao tem `search_library` configurado em `upgrade_rules.json`.")
        lines.append("- Os gaps atuais nao combinam com nenhuma busca declarada para esta build.")
        lines.append("- A build/personagem ja esta perto o bastante dos alvos configurados.")
    for index, entry in enumerate(entries, start=1):
        lines.extend(
            [
                f"## {index}. {entry['title']}",
                "",
                f"Prioridade: {entry.get('priority_pt') or entry['priority']}",
                "",
                f"Gap: {gap_context(entry)}",
                "",
                f"Motivo: {entry['reason']}",
                "",
                "Buscar:",
            ]
        )
        for term in entry["trade_terms"]:
            lines.append(f"- {term}")
        lines.extend(["", f"Preco alvo: {entry['price_hint']}", ""])
        if entry.get("profiles"):
            lines.append("Perfis do script relacionados:")
            for profile in entry["profiles"]:
                lines.append(f"- `{profile}`")
            lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_recommendations(path: Path, gap: dict[str, Any], entries: list[dict[str, Any]]) -> None:
    solved = gap.get("solved", {})
    risks = gap.get("risks", {})
    guarded = gap.get("guarded_slots") or gap.get("protected_slots", {})
    lines = [
        "# Recomendacoes de upgrade",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Estado atual resumido",
        "",
    ]
    for key, entry in gap.get("comparison", {}).items():
        if entry.get("current") is not None:
            lines.append(f"- {key}: {entry.get('current')}")

    lines.extend(["", "## O que ja esta resolvido", ""])
    if solved:
        for key, entry in solved.items():
            lines.append(f"- `{key}` esta resolvido ou acima do minimo com valor {entry.get('current')}.")
    else:
        lines.append("- Nada marcado como resolvido nos dados atuais.")

    lines.extend(["", "## Gargalos", ""])
    if risks:
        for key, entry in risks.items():
            lines.append(f"- `{key}`: {entry.get('status')} (atual={entry.get('current')}, meta={entry.get('goal')}).")
    else:
        lines.append("- Nenhum gargalo detectado.")

    lines.extend(["", "## Slots sensiveis", ""])
    if guarded:
        lines.append("Estes slots podem ser trocados, mas so quando a troca preserva os pisos da build e entrega ganho claro.")
        lines.append("")
    for slot, reason in guarded.items():
        lines.append(f"- `{slot}`: {reason}")

    lines.extend(["", "## Compras recomendadas", ""])
    if entries:
        for index, entry in enumerate(entries[:5], start=1):
            lines.extend(
                [
                    f"### {index}. {entry['title']}",
                    "",
                    f"Prioridade: {entry.get('priority_pt') or entry['priority']}",
                    "",
                    f"Gap: {gap_context(entry)}",
                    "",
                    f"Motivo: {entry['reason']}",
                    "",
                    f"Perfis relacionados: {', '.join(entry.get('profiles') or ['busca manual'])}",
                    "",
                ]
            )
    else:
        lines.append("Nenhuma compra recomendada com os dados atuais.")
        lines.append("")
        lines.append("Se isso parecer estranho, confira se `upgrade_rules.json` da build tem `search_library` e `trade_profiles`.")

    lines.extend(
        [
            "## Regras de seguranca",
            "",
            "- Itens importantes podem ser trocados se a melhora for clara e nao quebrar pisos da build.",
            "- Evitar sidegrades: gastar pouco para melhorar quase nada geralmente nao compensa.",
            "- Usar o score minimo configurado antes de considerar uma compra.",
            "- Nao comprar item acima do budget como compra imediata; tratar como monitorar depois.",
            "- Confirmar qualquer compra no trade, PoE Overlay e PoB.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report_json(
    path: Path,
    gap: dict[str, Any],
    entries: list[dict[str, Any]],
    rules: dict[str, Any],
    active_build: dict[str, Any],
    active_character: dict[str, Any],
) -> None:
    report = {
        "schema_version": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active_build_slug": active_build.get("active_slug", ""),
        "active_build_name": active_build.get("name", ""),
        "active_character_slug": active_character.get("active_slug", ""),
        "active_character_name": active_character.get("name", ""),
        "priorities": gap.get("current_priorities", {}),
        "guarded_slots": gap.get("guarded_slots") or gap.get("protected_slots", {}),
        "recommended_searches": entries,
        "guarded_slots_rules": rules.get("guarded_slots", rules.get("locked_slots", {})),
        "minimum_plan_score": rules.get("minimum_plan_score", 0),
        "notes": [
            "Deterministic recommendation MVP; future run_agent.py can use this as compact context.",
            "No recommendation here is an automatic purchase order.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate next searches and upgrade recommendations from gap analysis.")
    parser.add_argument("--gap", type=Path, default=DEFAULT_GAP)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--next-searches", type=Path, default=DEFAULT_NEXT_SEARCHES)
    parser.add_argument("--recommendations", type=Path, default=DEFAULT_RECOMMENDATIONS)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--active-build", type=Path, default=DEFAULT_ACTIVE_BUILD)
    parser.add_argument("--active-character", type=Path, default=DEFAULT_ACTIVE_CHARACTER)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    gap = load_json(args.gap)
    rules = load_json(args.rules)
    active_build = load_json(args.active_build) if args.active_build.exists() else {}
    active_character = load_json(args.active_character) if args.active_character.exists() else {}
    entries = search_entries(gap, rules)
    write_next_searches(args.next_searches, entries)
    write_recommendations(args.recommendations, gap, entries)
    write_report_json(args.report_json, gap, entries, rules, active_build, active_character)
    print(f"Next searches saved: {args.next_searches}")
    print(f"Recommendations saved: {args.recommendations}")
    print(f"Upgrade report JSON saved: {args.report_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
