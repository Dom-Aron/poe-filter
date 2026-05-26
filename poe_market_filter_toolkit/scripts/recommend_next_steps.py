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
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.time_utils import utc_now_iso

DEFAULT_GAP = ROOT / "data" / "generated" / "gap_analysis.json"
DEFAULT_NEXT_SEARCHES = ROOT / "data" / "generated" / "next_searches.md"
DEFAULT_RECOMMENDATIONS = ROOT / "data" / "generated" / "upgrade_recommendations.md"
DEFAULT_REPORT_JSON = ROOT / "data" / "generated" / "upgrade_report.json"


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
        current = risk.get("current")
        if stat_name in {"chance_to_hit", "chance_to_hit_evasive"} and isinstance(current, (int, float)) and current >= 94:
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
        f"Generated: {utc_now_iso()}",
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
        f"Generated: {utc_now_iso()}",
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
        "generated_at": utc_now_iso(),
        "active_build_slug": active_build.get("active_slug", ""),
        "active_build_name": active_build.get("name", ""),
        "active_character_slug": active_character.get("active_slug", ""),
        "active_character_name": active_character.get("name", ""),
        "priorities": gap.get("current_priorities", {}),
        "guarded_slots": gap.get("guarded_slots") or gap.get("protected_slots", {}),
        "recommended_searches": entries,
        "guarded_slots_rules": rules.get("guarded_slots", {}),
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
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--next-searches", type=Path, default=DEFAULT_NEXT_SEARCHES)
    parser.add_argument("--recommendations", type=Path, default=DEFAULT_RECOMMENDATIONS)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--active-build", type=Path)
    parser.add_argument("--active-character", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    gap = load_json(args.gap)
    rules = load_json(args.rules)
    active_build = load_json(args.active_build) if args.active_build and args.active_build.exists() else {}
    active_character = load_json(args.active_character) if args.active_character and args.active_character.exists() else {}
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
