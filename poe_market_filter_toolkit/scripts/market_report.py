#!/usr/bin/env python3
"""
market_report.py

Generates Markdown and CSV reports from market/latest_market.json.

Usage:
    python scripts/market_report.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / "config" / "market_config.json"
MARKET_FILE = ROOT / "market" / "latest_market.json"
REPORT_DIR = ROOT / "market" / "reports"
REPORT_MD = REPORT_DIR / "market_report.md"
REPORT_CSV = REPORT_DIR / "market_report.csv"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def tier_for_value(value: float, thresholds: dict[str, float]) -> str:
    ordered = sorted(thresholds.items(), key=lambda kv: kv[1], reverse=True)
    for tier, minimum in ordered:
        if value >= float(minimum):
            return tier
    return "T5_MICRO"


def sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            str(item.get("tier", "")),
            -float(item.get("chaos_value", 0)),
            str(item.get("category", "")),
            str(item.get("name", "")),
        ),
    )


def normalize_market_items(market: dict[str, Any], thresholds: dict[str, float]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for item in market.get("items", []):
        value = float(item.get("chaos_value", 0) or 0)
        normalized.append({
            "tier": tier_for_value(value, thresholds),
            "name": item.get("name", ""),
            "category": item.get("category", ""),
            "requested_category": item.get("requested_category", ""),
            "chaos_value": value,
            "divine_value": item.get("divine_value"),
            "listing_count": item.get("listing_count"),
            "change_percent": item.get("change_percent"),
            "source_endpoint": item.get("source_endpoint", ""),
            "source": item.get("source", ""),
        })

    return sort_items(normalized)


def main() -> int:
    config = load_json(CONFIG_FILE)
    market = load_json(MARKET_FILE)

    thresholds = config.get("tier_thresholds_chaos", {})
    normalized = normalize_market_items(market, thresholds)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with REPORT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tier",
                "name",
                "category",
                "requested_category",
                "chaos_value",
                "divine_value",
                "listing_count",
                "change_percent",
                "source_endpoint",
                "source",
            ],
        )
        writer.writeheader()
        writer.writerows(normalized)

    by_tier: dict[str, list[dict[str, Any]]] = {}
    for item in normalized:
        by_tier.setdefault(item["tier"], []).append(item)

    tier_order = ["T0_JACKPOT", "T1_MUITO_ALTO", "T2_ALTO", "T3_VISIVEL", "T4_BAIXO", "T5_MICRO"]

    lines: list[str] = []
    lines.append("# Relatorio de mercado - Path of Exile")
    lines.append("")
    lines.append(f"- Liga: `{market.get('league', 'desconhecida')}`")
    lines.append(f"- Gerado em: `{market.get('generated_at', 'desconhecido')}`")
    lines.append(f"- Total de itens: `{len(normalized)}`")
    lines.append(f"- Erros na coleta: `{len(market.get('errors', []))}`")
    lines.append("")
    lines.append("## Tiers usados")
    lines.append("")
    for tier, minimum in sorted(thresholds.items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"- `{tier}`: >= {minimum} chaos")
    lines.append("- `T5_MICRO`: abaixo do menor limite configurado")
    lines.append("")

    for tier in tier_order:
        tier_items = by_tier.get(tier, [])
        lines.append(f"## {tier} - {len(tier_items)} itens")
        lines.append("")
        if not tier_items:
            lines.append("_Nenhum item._")
            lines.append("")
            continue

        lines.append("| Item | Categoria | Chaos | Divine | Liquidez/Volume | Variacao |")
        lines.append("|---|---:|---:|---:|---:|---:|")

        display_items = tier_items if tier != "T5_MICRO" else tier_items[:100]

        for item in display_items:
            divine = item["divine_value"]
            listings = item["listing_count"]
            change = item["change_percent"]
            lines.append(
                f"| {item['name']} | {item['category']} | {item['chaos_value']:.2f} | "
                f"{'' if divine is None else divine} | {'' if listings is None else listings} | "
                f"{'' if change is None else f'{float(change):.2f}%'} |"
            )

        if tier == "T5_MICRO" and len(tier_items) > len(display_items):
            lines.append(f"| ... | ... | +{len(tier_items) - len(display_items)} itens omitidos |  |  |  |")

        lines.append("")

    if market.get("errors"):
        lines.append("## Erros de coleta")
        lines.append("")
        for error in market["errors"]:
            lines.append(f"- `{error.get('category')}` ({error.get('kind')}): {error.get('error')}")
        lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Relatorio Markdown salvo em: {REPORT_MD.relative_to(ROOT)}")
    print(f"Relatorio CSV salvo em: {REPORT_CSV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
