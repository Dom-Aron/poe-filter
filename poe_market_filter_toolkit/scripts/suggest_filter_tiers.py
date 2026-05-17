#!/usr/bin/env python3
"""
suggest_filter_tiers.py

Compares current poe.ninja prices with the active .filter files and generates
manual review suggestions.

Usage:
    python scripts/suggest_filter_tiers.py
    python scripts/suggest_filter_tiers.py --min-chaos 20
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
CONFIG_FILE = ROOT / "config" / "market_config.json"
MARKET_FILE = ROOT / "market" / "latest_market.json"
FILTER_DIR = ROOT / "filters" / "current"
REPORT_DIR = ROOT / "market" / "reports"
REPORT_FILE = REPORT_DIR / "filter_suggestions.md"

BASE_TYPE_RE = re.compile(r"\bBaseType\s+(.+)", re.IGNORECASE)
QUOTED_RE = re.compile(r'"([^"]+)"')


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def find_filter_files() -> list[Path]:
    paths = list(FILTER_DIR.glob("*.filter")) + list(REPO_ROOT.glob("*.filter"))
    return sorted(set(paths))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path.relative_to(REPO_ROOT))


def extract_base_types_from_filter(path: Path) -> set[str]:
    base_types: set[str] = set()
    text = path.read_text(encoding="utf-8", errors="replace")

    for line in text.splitlines():
        match = BASE_TYPE_RE.search(line)
        if not match:
            continue

        for quoted in QUOTED_RE.findall(match.group(1)):
            base_types.add(quoted.strip())

    return base_types


def tier_for_value(value: float, thresholds: dict[str, float]) -> str:
    ordered = sorted(thresholds.items(), key=lambda kv: kv[1], reverse=True)
    for tier, minimum in ordered:
        if value >= float(minimum):
            return tier
    return "T5_MICRO"


def similar_names(name: str, candidates: set[str], limit: int = 3) -> list[str]:
    return difflib.get_close_matches(name, candidates, n=limit, cutoff=0.72)


def should_include_item(
    name: str,
    category: str,
    requested_category: str,
    value: float,
    config: dict[str, Any],
    min_chaos: float,
) -> bool:
    thresholds = config.get("tier_thresholds_chaos", {})
    priority_categories = set(config.get("priority_categories", []))
    always_watch = set(config.get("always_watch_names", []))

    return (
        value >= min_chaos
        or name in always_watch
        or (
            (category in priority_categories or requested_category in priority_categories)
            and value >= float(thresholds.get("T3_VISIVEL", 5))
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest manual loot-filter tier changes from market data.")
    parser.add_argument("--min-chaos", type=float, default=None, help="Minimum chaos value for an item to appear.")
    args = parser.parse_args()

    config = load_json(CONFIG_FILE)
    market = load_json(MARKET_FILE)

    thresholds = config.get("tier_thresholds_chaos", {})
    min_chaos = args.min_chaos
    if min_chaos is None:
        min_chaos = float(thresholds.get("T2_ALTO", 20))

    filter_files = find_filter_files()
    all_base_types: set[str] = set()

    for filter_file in filter_files:
        all_base_types.update(extract_base_types_from_filter(filter_file))

    market_items = []
    for item in market.get("items", []):
        name = str(item.get("name", "")).strip()
        category = str(item.get("category", "")).strip()
        requested_category = str(item.get("requested_category", "")).strip()
        value = float(item.get("chaos_value", 0) or 0)

        if not name:
            continue

        if should_include_item(name, category, requested_category, value, config, min_chaos):
            market_items.append({
                "name": name,
                "category": category,
                "requested_category": requested_category,
                "chaos_value": value,
                "tier": tier_for_value(value, thresholds),
                "listing_count": item.get("listing_count"),
                "present_in_filter": name in all_base_types,
                "similar_in_filter": similar_names(name, all_base_types),
            })

    market_items.sort(key=lambda item: (-item["chaos_value"], item["category"], item["name"]))

    missing = [item for item in market_items if not item["present_in_filter"]]
    present = [item for item in market_items if item["present_in_filter"]]

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Sugestoes para o filtro com base no mercado")
    lines.append("")
    lines.append(f"- Liga: `{market.get('league', 'desconhecida')}`")
    lines.append(f"- Mercado gerado em: `{market.get('generated_at', 'desconhecido')}`")
    lines.append(f"- Filtros analisados: `{len(filter_files)}`")
    lines.append(f"- BaseTypes unicos encontrados no filtro: `{len(all_base_types)}`")
    lines.append(f"- Preco minimo principal: `{min_chaos:.2f} chaos`")
    lines.append("")
    lines.append("## Arquivos de filtro analisados")
    lines.append("")
    if filter_files:
        for filter_file in filter_files:
            lines.append(f"- `{display_path(filter_file)}`")
    else:
        lines.append("_Nenhum arquivo `.filter` encontrado em `filters/current/` ou na raiz do repositorio._")
    lines.append("")

    lines.append("## Itens caros ausentes no filtro")
    lines.append("")
    if missing:
        lines.append("| Item | Categoria | Fonte | Tier | Chaos | Liquidez/Volume | Nome parecido no filtro |")
        lines.append("|---|---:|---:|---:|---:|---:|---|")
        for item in missing[:200]:
            similar = ", ".join(item["similar_in_filter"])
            listings = "" if item["listing_count"] is None else item["listing_count"]
            lines.append(
                f"| {item['name']} | {item['category']} | {item['requested_category']} | {item['tier']} | "
                f"{item['chaos_value']:.2f} | {listings} | {similar} |"
            )
        if len(missing) > 200:
            lines.append(f"| ... | ... | ... | ... | +{len(missing) - 200} itens omitidos |  |  |")
    else:
        lines.append("_Nenhum item caro ausente encontrado._")
    lines.append("")

    lines.append("## Itens caros presentes no filtro")
    lines.append("")
    if present:
        lines.append("| Item | Categoria | Fonte | Tier | Chaos | Liquidez/Volume |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for item in present[:200]:
            listings = "" if item["listing_count"] is None else item["listing_count"]
            lines.append(
                f"| {item['name']} | {item['category']} | {item['requested_category']} | {item['tier']} | "
                f"{item['chaos_value']:.2f} | {listings} |"
            )
        if len(present) > 200:
            lines.append(f"| ... | ... | ... | ... | +{len(present) - 200} itens omitidos |  |")
    else:
        lines.append("_Nenhum item caro presente no filtro foi identificado._")
    lines.append("")

    lines.append("## Como usar este relatorio")
    lines.append("")
    lines.append("1. Priorize itens `T0_JACKPOT`, `T1_MUITO_ALTO` e `T2_ALTO` ausentes.")
    lines.append("2. Confirme o nome exato antes de criar `BaseType` no filtro.")
    lines.append("3. Itens com baixa liquidez/listagens devem ser revisados manualmente.")
    lines.append("4. O script nao edita o filtro automaticamente.")
    lines.append("")

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Sugestoes salvas em: {REPORT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
