#!/usr/bin/env python3
"""
compare_current_to_target.py

Compares current character stats/items with target build stats/rules and writes
a compact gap analysis for the upgrade planner or a future local agent.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAYER_ITEMS = ROOT / "builds" / "player_items.json"
DEFAULT_PLAYER_STATS = ROOT / "builds" / "player_stats.json"
DEFAULT_TARGET_STATS = ROOT / "builds" / "target_build_stats.json"
DEFAULT_RULES = ROOT / "builds" / "upgrade_rules.json"
DEFAULT_OUTPUT_JSON = ROOT / "data" / "generated" / "gap_analysis.json"
DEFAULT_OUTPUT_MD = ROOT / "data" / "generated" / "gap_analysis.md"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def numeric_stats(data: dict[str, Any]) -> dict[str, float]:
    stats = data.get("stats", {})
    if not isinstance(stats, dict):
        return {}
    return {key: float(value) for key, value in stats.items() if isinstance(value, (int, float))}


def compare_stat(current: float | None, minimum: float | None, goal: float | None) -> dict[str, Any]:
    if current is None:
        return {
            "current": None,
            "minimum": minimum,
            "goal": goal,
            "status": "unknown",
            "message": "Sem valor atual; precisa de PoB, API parseada ou entrada manual.",
        }
    if minimum is not None and current < minimum:
        return {
            "current": current,
            "minimum": minimum,
            "goal": goal,
            "status": "below_minimum",
            "missing_to_minimum": minimum - current,
            "missing_to_goal": (goal - current) if goal is not None else None,
        }
    if goal is not None and current < goal:
        return {
            "current": current,
            "minimum": minimum,
            "goal": goal,
            "status": "needs_improvement",
            "missing_to_goal": goal - current,
        }
    return {
        "current": current,
        "minimum": minimum,
        "goal": goal,
        "status": "solved",
    }


def protected_slots(player_items: dict[str, Any], rules: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    rule_slots = rules.get("locked_slots", {}) if isinstance(rules.get("locked_slots"), dict) else {}
    for slot, reason in rule_slots.items():
        item = player_items.get("items", {}).get(slot, {})
        name = item.get("name") or item.get("base") or slot
        out[slot] = f"{name}: {reason}"
    for slot, item in player_items.get("items", {}).items():
        if item.get("locked") and slot not in out:
            name = item.get("name") or item.get("base") or slot
            reason = item.get("protect_reason") or "Slot marcado como locked."
            out[slot] = f"{name}: {reason}"
    return out


def priorities_from_gaps(comparison: dict[str, Any]) -> dict[str, str]:
    priorities: dict[str, str] = {}
    for key, entry in comparison.items():
        status = entry.get("status")
        if status == "below_minimum":
            priorities[key] = "very_high"
        elif status == "needs_improvement":
            priorities[key] = "high"
        elif status == "unknown":
            priorities[key] = "needs_data"
        else:
            priorities[key] = "low"
    return priorities


def build_gap_analysis(
    player_items: dict[str, Any],
    player_stats: dict[str, Any],
    target_stats: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any]:
    current = numeric_stats(player_stats)
    minimums = target_stats.get("minimums", {})
    goals = target_stats.get("goals", {})
    keys = sorted(set(current) | set(minimums) | set(goals))

    comparison: dict[str, Any] = {}
    for key in keys:
        comparison[key] = compare_stat(
            current.get(key),
            float(minimums[key]) if isinstance(minimums.get(key), (int, float)) else None,
            float(goals[key]) if isinstance(goals.get(key), (int, float)) else None,
        )

    solved = {key: value for key, value in comparison.items() if value["status"] == "solved"}
    risks = {key: value for key, value in comparison.items() if value["status"] in {"below_minimum", "needs_improvement", "unknown"}}

    return {
        "schema_version": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "solved": solved,
        "risks": risks,
        "comparison": comparison,
        "protected_slots": protected_slots(player_items, rules),
        "current_priorities": priorities_from_gaps(comparison),
        "notes": [
            "Este arquivo usa os stats numericos disponiveis no player_stats.json.",
            "Stats ausentes devem vir de PoB, da API parseada ou de entrada manual.",
            "The Brass Dome equipado: Strength nao deve ser pontuada como fonte de vida.",
        ],
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown(path: Path, analysis: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Gap Analysis",
        "",
        f"Generated: {analysis['generated_at']}",
        "",
        "## Resolvido",
        "",
    ]
    if analysis["solved"]:
        for key, entry in analysis["solved"].items():
            lines.append(f"- `{key}`: {entry.get('current')} / meta {entry.get('goal')}")
    else:
        lines.append("- Nada marcado como resolvido com os dados atuais.")

    lines.extend(["", "## Riscos / Prioridades", ""])
    if analysis["risks"]:
        for key, entry in analysis["risks"].items():
            status = entry.get("status")
            current = entry.get("current")
            goal = entry.get("goal")
            minimum = entry.get("minimum")
            lines.append(f"- `{key}`: {status}; atual={current}; minimo={minimum}; meta={goal}")
    else:
        lines.append("- Nenhum risco detectado.")

    lines.extend(["", "## Slots Protegidos", ""])
    for slot, reason in analysis["protected_slots"].items():
        lines.append(f"- `{slot}`: {reason}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare current character state with target build goals.")
    parser.add_argument("--player-items", type=Path, default=DEFAULT_PLAYER_ITEMS)
    parser.add_argument("--player-stats", type=Path, default=DEFAULT_PLAYER_STATS)
    parser.add_argument("--target-stats", type=Path, default=DEFAULT_TARGET_STATS)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    analysis = build_gap_analysis(
        player_items=load_json(args.player_items),
        player_stats=load_json(args.player_stats),
        target_stats=load_json(args.target_stats),
        rules=load_json(args.rules),
    )
    write_json(args.output_json, analysis)
    write_markdown(args.output_md, analysis)
    print(f"Gap analysis saved: {args.output_json}")
    print(f"Gap analysis report saved: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
