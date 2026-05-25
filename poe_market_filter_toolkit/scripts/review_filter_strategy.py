#!/usr/bin/env python3
"""
review_filter_strategy.py

Build-aware loot-filter review.

This script does not edit the active filter. It combines:
- current character equipment,
- target build requirements,
- current market snapshot,

and writes a concise report plus a conservative `.filter` snippet for manual
review. The goal is to keep loot-filter decisions separate from trade-planner
decisions while letting both use the same facts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import paths


MARKET_FILE = ROOT / "market" / "latest_market.json"
CONFIG_FILE = ROOT / "config" / "market_config.json"
REPORT_FILE = ROOT / "market" / "reports" / "filter_strategy.md"
SNIPPET_FILE = ROOT / "market" / "reports" / "filter_strategy_snippets.filter"

SAFE_BASETYPE_REQUESTED = {
    "Currency",
    "Fragment",
    "Scarab",
    "Fossil",
    "Resonator",
    "Essence",
    "DivinationCard",
    "Oil",
    "DeliriumOrb",
    "Omen",
    "Tattoo",
    "Runegraft",
    "AllflameEmber",
    "Invitation",
    "Memory",
}
BASE_SLOTS = {
    "weapon",
    "offhand",
    "helmet",
    "body_armour",
    "gloves",
    "boots",
    "belt",
    "amulet",
    "ring_1",
    "ring_2",
    "abyss_jewel_1",
    "abyss_jewel_2",
}
IGNORED_BUILD_BASE_SLOTS = {
    "weapon_swap",
    "offhand_swap",
    "flask_1",
    "flask_2",
    "flask_3",
    "flask_4",
    "flask_5",
}
BUILD_GEAR_STATS = {
    "life",
    "energy_shield",
    "accuracy",
    "crit_multiplier",
    "critical_strike_chance",
    "attack_speed",
    "cast_speed",
    "movement_speed",
    "fire_resistance",
    "cold_resistance",
    "lightning_resistance",
    "chaos_resistance",
    "physical_damage_to_attacks",
    "staff_flat_physical",
    "impale_chance",
    "ailment_avoidance",
    "spell_suppression",
    "attack_block",
    "spell_block",
}


def read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return fallback or {}
    return json.loads(path.read_text(encoding="utf-8"))


def active_character_slug() -> str:
    active = read_json(paths.BUILDS / "active_character.json")
    slug = str(active.get("slug") or active.get("character_slug") or "").strip()
    if not slug:
        raise SystemExit("Use --character <slug> or activate a character first.")
    return slug


def character_build_slug(character_slug: str) -> str:
    profile = read_json(paths.character_dir(character_slug) / "character_profile.json")
    build_slug = str(profile.get("build_slug") or "").strip()
    if not build_slug:
        raise SystemExit(f"Character profile has no build_slug: {character_slug}")
    return build_slug


def tier_for_value(value: float, thresholds: dict[str, Any]) -> str:
    ordered = sorted(thresholds.items(), key=lambda kv: float(kv[1]), reverse=True)
    for tier, minimum in ordered:
        if value >= float(minimum):
            return tier
    return "T5_MICRO"


def numeric_stats(data: dict[str, Any]) -> dict[str, float]:
    stats = data.get("stats", {}) if isinstance(data.get("stats"), dict) else {}
    return {str(key): float(value) for key, value in stats.items() if isinstance(value, (int, float))}


def item_slots(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = data.get("items", {}) if isinstance(data.get("items"), dict) else {}
    return {str(slot): item for slot, item in items.items() if isinstance(item, dict)}


def stat_gaps(player_stats: dict[str, Any], requirements: dict[str, Any]) -> list[dict[str, Any]]:
    current = numeric_stats(player_stats)
    goals = requirements.get("goals", {}) if isinstance(requirements.get("goals"), dict) else {}
    gaps: list[dict[str, Any]] = []
    for key, goal in goals.items():
        if not isinstance(goal, (int, float)):
            continue
        value = current.get(str(key))
        if value is None:
            gaps.append({"stat": str(key), "current": None, "goal": goal, "missing": None, "priority": "needs_data"})
        elif value < float(goal):
            missing = round(float(goal) - value, 2)
            priority = "high" if key in {"life", "chance_to_hit", "chaos_resistance", "spell_block"} else "medium"
            gaps.append({"stat": str(key), "current": value, "goal": goal, "missing": missing, "priority": priority})
    gaps.sort(key=lambda row: (row["priority"] != "high", row["stat"]))
    return gaps


def useful_build_bases(player_items: dict[str, Any], target_items: dict[str, Any], requirements: dict[str, Any]) -> list[dict[str, Any]]:
    bases: dict[str, dict[str, Any]] = {}

    def add_base(slot: str, item: dict[str, Any], source: str, desired_stats: list[str] | None = None) -> None:
        if slot in IGNORED_BUILD_BASE_SLOTS:
            return
        base = str(item.get("base") or "").strip()
        if not base:
            return
        stats = item.get("stats", {}) if isinstance(item.get("stats"), dict) else {}
        stat_keys = set(str(key) for key in stats)
        if desired_stats:
            stat_keys.update(desired_stats)
        interesting = sorted(stat_keys & BUILD_GEAR_STATS)
        if slot not in BASE_SLOTS and not interesting:
            return
        row = bases.setdefault(
            base,
            {
                "base": base,
                "slots": set(),
                "sources": set(),
                "stats": set(),
                "example_names": set(),
            },
        )
        row["slots"].add(slot)
        row["sources"].add(source)
        row["stats"].update(interesting)
        if item.get("name"):
            row["example_names"].add(str(item["name"]))

    for slot, item in item_slots(player_items).items():
        add_base(slot, item, "personagem_atual")

    for slot, item in item_slots(target_items).items():
        add_base(slot, item, "build_target")

    slots_req = requirements.get("slot_requirements", {}) if isinstance(requirements.get("slot_requirements"), dict) else {}
    for slot, req in slots_req.items():
        if isinstance(req, dict):
            add_base(slot, req, "target_requirements", list(req.get("desired_stats", [])))

    out: list[dict[str, Any]] = []
    for row in bases.values():
        out.append(
            {
                "base": row["base"],
                "slots": sorted(row["slots"]),
                "sources": sorted(row["sources"]),
                "stats": sorted(row["stats"]),
                "example_names": sorted(row["example_names"]),
            }
        )
    out.sort(key=lambda row: (row["slots"][0] if row["slots"] else "", row["base"]))
    return out


def market_rows(market: dict[str, Any], config: dict[str, Any], min_chaos: float) -> list[dict[str, Any]]:
    thresholds = config.get("tier_thresholds_chaos", {}) if isinstance(config.get("tier_thresholds_chaos"), dict) else {}
    rows: list[dict[str, Any]] = []
    for item in market.get("items", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        value = float(item.get("chaos_value") or 0)
        requested = str(item.get("requested_category") or item.get("category") or "").strip()
        if not name or value < min_chaos:
            continue
        rows.append(
            {
                "name": name,
                "value": value,
                "tier": tier_for_value(value, thresholds),
                "category": str(item.get("category") or ""),
                "requested_category": requested,
                "listing_count": item.get("listing_count"),
                "safe_basetype": requested in SAFE_BASETYPE_REQUESTED,
            }
        )
    rows.sort(key=lambda row: (-row["value"], row["requested_category"], row["name"]))
    return rows


def quote_names(names: list[str]) -> str:
    return " ".join(f'"{name}"' for name in names)


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def snippet_for_build_bases(bases: list[dict[str, Any]]) -> list[str]:
    names = [row["base"] for row in bases if row.get("base")]
    if not names:
        return [
            "# Build bases: nenhum BaseType de equipamento detectado.",
            "# Importe o PoB target para preencher target_requirements.json com slots da build.",
        ]

    lines = [
        "# ---------------------------------------------------------------------",
        "# BUILD - bases candidatas para identificar no chao",
        "# Regras conservadoras: mostram bases raras/fractured/synthesised ligadas",
        "# ao personagem atual ou ao target. Mods explicitos ficam para revisao manual.",
        "# ---------------------------------------------------------------------",
    ]
    for group in chunked(names, 10):
        lines.extend(
            [
                "Show",
                "    Rarity Rare",
                f"    BaseType {quote_names(group)}",
                "    SetTextColor 210 235 255 255",
                "    SetBorderColor 90 180 255 220",
                "    SetBackgroundColor 0 25 55 185",
                "    SetFontSize 37",
                "    MinimapIcon 2 Cyan Circle",
                "",
                "Show",
                "    Rarity Rare",
                "    FracturedItem True",
                f"    BaseType {quote_names(group)}",
                "    SetTextColor 255 255 255 255",
                "    SetBorderColor 120 220 255 255",
                "    SetBackgroundColor 0 45 75 235",
                "    SetFontSize 42",
                "    PlayAlertSound 5 220",
                "    MinimapIcon 1 Cyan Diamond",
                "    PlayEffect Cyan Temp",
                "",
            ]
        )
    return lines


def snippet_for_market(rows: list[dict[str, Any]], max_items: int = 80) -> list[str]:
    safe_names = [row["name"] for row in rows if row["safe_basetype"]][:max_items]
    if not safe_names:
        return ["# Mercado: nenhum item seguro para BaseType acima do corte."]

    lines = [
        "# ---------------------------------------------------------------------",
        "# MERCADO - itens caros seguros para BaseType",
        "# Exclui SkillGem/UniqueMap/ClusterJewel por exigirem regras especificas.",
        "# ---------------------------------------------------------------------",
    ]
    for group in chunked(safe_names, 14):
        lines.extend(
            [
                "Show",
                f"    BaseType {quote_names(group)}",
                "    SetTextColor 255 255 255 255",
                "    SetBorderColor 255 180 0 255",
                "    SetBackgroundColor 75 35 0 240",
                "    SetFontSize 43",
                "    PlayAlertSound 5 250",
                "    MinimapIcon 1 Orange Star",
                "    PlayEffect Orange Temp",
                "",
            ]
        )
    return lines


def write_report(
    character_slug: str,
    build_slug: str,
    market: dict[str, Any],
    gaps: list[dict[str, Any]],
    bases: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    min_chaos: float,
) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Estrategia de filtro por personagem/build")
    lines.append("")
    lines.append(f"- Personagem: `{character_slug}`")
    lines.append(f"- Build: `{build_slug}`")
    lines.append(f"- Liga do mercado: `{market.get('league', 'desconhecida')}`")
    lines.append(f"- Mercado gerado em: `{market.get('generated_at', 'desconhecido')}`")
    lines.append(f"- Corte de mercado usado: `{min_chaos:.2f} chaos`")
    lines.append("")
    lines.append("## Como pensar o filtro")
    lines.append("")
    lines.append("- `Mercado`: destaque itens caros mesmo que nao sirvam para a build.")
    lines.append("- `Build`: destaque bases e tipos que podem virar upgrade depois de identificar.")
    lines.append("- `Uso/farm`: destaque itens ligados ao conteudo que voce roda, como Breach/Delirium.")
    lines.append("- `Trade planner`: continua separado; ele decide compra, nao o que aparece no chao.")
    lines.append("")
    lines.append("## Gaps relevantes para filtro")
    lines.append("")
    if gaps:
        lines.append("| Stat | Atual | Alvo | Falta | Prioridade |")
        lines.append("|---|---:|---:|---:|---|")
        for gap in gaps[:20]:
            current = "?" if gap["current"] is None else f"{gap['current']:.2f}"
            missing = "?" if gap["missing"] is None else f"{gap['missing']:.2f}"
            lines.append(f"| {gap['stat']} | {current} | {gap['goal']} | {missing} | {gap['priority']} |")
    else:
        lines.append("_Nenhum gap numerico detectado com os dados atuais._")
    lines.append("")
    lines.append("## Bases de build para triagem no chao")
    lines.append("")
    if bases:
        lines.append("| BaseType | Slots | Fonte | Stats observados | Exemplo |")
        lines.append("|---|---|---|---|---|")
        for row in bases:
            lines.append(
                f"| {row['base']} | {', '.join(row['slots'])} | {', '.join(row['sources'])} | "
                f"{', '.join(row['stats'])} | {', '.join(row['example_names'])} |"
            )
    else:
        lines.append("_Nenhuma base de equipamento detectada. Importe o PoB target para enriquecer essa secao._")
    lines.append("")
    lines.append("## Mercado que merece regra de filtro")
    lines.append("")
    lines.append("| Item | Chaos | Tier | Categoria | Seguro como BaseType? | Volume |")
    lines.append("|---|---:|---|---|---|---:|")
    for row in rows[:120]:
        volume = "" if row["listing_count"] is None else row["listing_count"]
        safe = "sim" if row["safe_basetype"] else "nao"
        lines.append(
            f"| {row['name']} | {row['value']:.2f} | {row['tier']} | "
            f"{row['requested_category']} | {safe} | {volume} |"
        )
    lines.append("")
    lines.append("## Proximos ajustes manuais sugeridos")
    lines.append("")
    lines.append("1. Copiar apenas blocos revisados de `filter_strategy_snippets.filter` para o filtro ativo.")
    lines.append("2. Manter nomes de SkillGem, UniqueMap e ClusterJewel fora de `BaseType` automatico.")
    lines.append("3. Para rares identificados no chao, preferir triagem por base/fractured/synthesised; `HasExplicitMod` deve ser adicionado so depois de validar o texto exato no parser.")
    lines.append("4. Quando importar um PoB target real, rodar este script de novo para preencher bases e skills da build alvo.")
    lines.append("")
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


def write_snippet(bases: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    lines.append("# Snippets gerados por review_filter_strategy.py")
    lines.append("# Revisar manualmente antes de copiar para o filtro ativo.")
    lines.append("")
    lines.extend(snippet_for_build_bases(bases))
    lines.append("")
    lines.extend(snippet_for_market(rows))
    lines.append("")
    SNIPPET_FILE.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review loot-filter strategy using character, target build and market data.")
    parser.add_argument("--character", help="Character slug. Defaults to builds/active_character.json.")
    parser.add_argument("--min-chaos", type=float, default=None, help="Market cut for the report/snippet.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    character_slug = args.character or active_character_slug()
    build_slug = character_build_slug(character_slug)
    config = read_json(CONFIG_FILE)
    thresholds = config.get("tier_thresholds_chaos", {}) if isinstance(config.get("tier_thresholds_chaos"), dict) else {}
    min_chaos = args.min_chaos if args.min_chaos is not None else float(thresholds.get("T2_ALTO", 20))

    char_dir = paths.character_dir(character_slug)
    build_dir = paths.build_dir(build_slug)
    player_items = read_json(char_dir / "player_items.json")
    player_stats = read_json(char_dir / "player_stats.json")
    target_items = read_json(build_dir / "target_build_items.json", {"items": {}})
    requirements = read_json(build_dir / "target_requirements.json")
    if not requirements:
        target_stats = read_json(build_dir / "target_build_stats.json")
        requirements = {"goals": target_stats.get("goals", {}), "minimums": target_stats.get("minimums", {})}
    market = read_json(MARKET_FILE)

    gaps = stat_gaps(player_stats, requirements)
    bases = useful_build_bases(player_items, target_items, requirements)
    rows = market_rows(market, config, min_chaos)
    write_report(character_slug, build_slug, market, gaps, bases, rows, min_chaos)
    write_snippet(bases, rows)

    print(f"Estrategia do filtro salva em: {REPORT_FILE.relative_to(ROOT)}")
    print(f"Snippets salvos em: {SNIPPET_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
