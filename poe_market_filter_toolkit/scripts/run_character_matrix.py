#!/usr/bin/env python3
"""
run_character_matrix.py

Runs the upgrade-search flow for multiple saved character profiles.

Each character profile owns player_items.json/player_stats.json and points to a
single target build. The script calls run_character.py for each selected
character, so every run reads its own files and linked build profile directly
before storing outputs under data/generated/characters/<character_slug>/.
"""

from __future__ import annotations

import argparse
import html
import subprocess
import sys
from pathlib import Path
from typing import Any

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLKIT_ROOT))

from core import paths
from core.io import read_json


def run_script(name: str, *args: str) -> None:
    command = [sys.executable, str(paths.SCRIPTS / name), *args]
    print("Running:", " ".join([name, *args]), flush=True)
    result = subprocess.run(command, cwd=str(paths.ROOT))
    if result.returncode != 0:
        raise SystemExit(f"Script failed: {name} (exit code {result.returncode})")


def known_characters() -> list[str]:
    if not paths.CHARACTERS.exists():
        return []
    return sorted(path.name for path in paths.CHARACTERS.iterdir() if path.is_dir())


def selected_characters(raw: str) -> list[str]:
    if raw == "all":
        return known_characters()
    if raw == "active":
        raise SystemExit("The per-character architecture has no global active character. Use --characters all or pass explicit character slugs.")
    return [item.strip() for item in raw.split(",") if item.strip()]


def render_character_pages(character_slug: str) -> None:
    target = paths.CHARACTER_OUTPUT / character_slug
    target.mkdir(parents=True, exist_ok=True)
    run_script(
        "generate_dashboard.py",
        "--validation-report",
        str(target / "validation_report.json"),
        "--gap",
        str(target / "gap_analysis.json"),
        "--upgrade-report",
        str(target / "upgrade_report.json"),
        "--next-searches",
        str(target / "next_searches.md"),
        "--recommendations",
        str(target / "upgrade_recommendations.md"),
        "--upgrade-plan",
        str(target / "upgrade_plan.md"),
        "--upgrade-plan-json",
        str(target / "upgrade_plan.json"),
        "--market-report",
        str(target / "market_report.md"),
        "--market-json",
        str(target / "latest_market.json"),
        "--active-build",
        str(target / "active_build.json"),
        "--active-character",
        str(target / "active_character.json"),
        "--output",
        str(target / "build_dashboard.html"),
    )


def run_for_character(
    character_slug: str,
    budget: str,
    top: int,
    max_fetch: int,
    profiles: str,
    request_delay: float | None,
    best_any_budget_mode: str,
) -> dict[str, Any]:
    args = [
        "--character",
        character_slug,
        "--skip-market-update",
        "--skip-market-report",
        "--skip-filter-reports",
        "--budget",
        budget,
        "--top",
        str(top),
        "--max-fetch",
        str(max_fetch),
    ]
    if profiles:
        args.extend(["--profiles", profiles])
    if request_delay is not None:
        args.extend(["--request-delay", str(request_delay)])
    if best_any_budget_mode:
        args.extend(["--best-any-budget-mode", best_any_budget_mode])
    run_script("run_character.py", *args)
    target = paths.CHARACTER_OUTPUT / character_slug
    character = read_json(target / "active_character.json")
    build = read_json(target / "active_build.json")
    artifacts = {
        path.name: str(path.relative_to(paths.GENERATED)).replace("\\", "/")
        for path in target.iterdir()
        if path.is_file()
    }
    return {
        "character_slug": character_slug,
        "character_name": character.get("name", character_slug),
        "build_slug": build.get("active_slug", ""),
        "build_name": build.get("name", ""),
        "artifacts": artifacts,
    }


def gap_sort_key(item: tuple[str, dict[str, Any]]) -> tuple[int, float, str]:
    key, entry = item
    status = str(entry.get("status", "unknown"))
    rank = {"below_minimum": 0, "needs_improvement": 1, "unknown": 2, "solved": 3}.get(status, 4)
    missing = entry.get("missing_to_minimum")
    if not isinstance(missing, (int, float)):
        missing = entry.get("missing_to_goal")
    missing_value = float(missing) if isinstance(missing, (int, float)) else 0.0
    return (rank, -missing_value, key)


def gap_summary_for_character(character_slug: str) -> str:
    gap = read_json(paths.CHARACTER_OUTPUT / character_slug / "gap_analysis.json")
    comparison = gap.get("comparison", {}) if isinstance(gap.get("comparison"), dict) else {}
    if not comparison:
        return "<p class=\"muted\">Sem gap analysis salvo.</p>"
    items = []
    for key, entry in sorted(comparison.items(), key=gap_sort_key)[:5]:
        status = str(entry.get("status", "unknown"))
        current = entry.get("current")
        minimum = entry.get("minimum")
        goal = entry.get("goal")
        missing = entry.get("missing_to_minimum")
        label = "min"
        if not isinstance(missing, (int, float)):
            missing = entry.get("missing_to_goal")
            label = "meta"
        missing_text = f"falta {missing:g} ate {label}" if isinstance(missing, (int, float)) else status
        items.append(
            f"<li class=\"gap {html.escape(status)}\"><code>{html.escape(key)}</code>: "
            f"{html.escape(str(current))} "
            f"<small>min {html.escape(str(minimum))} | meta {html.escape(str(goal))} | {html.escape(missing_text)}</small></li>"
        )
    return "<ul class=\"gaps\">" + "".join(items) + "</ul>"


def write_index(rows: list[dict[str, Any]], budget: str) -> Path:
    output = paths.GENERATED / "character_matrix_dashboard.html"
    cards = []
    for row in rows:
        artifacts = row.get("artifacts", {})
        plan = artifacts.get("upgrade_plan.html") or artifacts.get("upgrade_plan.md", "")
        dashboard = artifacts.get("build_dashboard.html", "")
        recommendations = artifacts.get("upgrade_recommendations.html", "")
        links = []
        if dashboard:
            links.append(f"<a href=\"{html.escape(dashboard)}\">Dashboard</a>")
        if plan:
            links.append(f"<a href=\"{html.escape(plan)}\">Plano 1000c</a>")
        if recommendations:
            links.append(f"<a href=\"{html.escape(recommendations)}\">Recomendacoes</a>")
        gaps = gap_summary_for_character(str(row["character_slug"]))
        cards.append(
            "<article>"
            f"<h2>{html.escape(str(row['character_name']))}</h2>"
            f"<p><strong>Personagem:</strong> <code>{html.escape(str(row['character_slug']))}</code></p>"
            f"<p><strong>Build:</strong> {html.escape(str(row['build_name']))} "
            f"<code>{html.escape(str(row['build_slug']))}</code></p>"
            "<h3>Principais gaps</h3>"
            f"{gaps}"
            f"<div class=\"actions\">{''.join(links)}</div>"
            "</article>"
        )

    body = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Simulacao por Personagem</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #101214; color: #eee8dc; }}
    header {{ padding: 28px 34px; background: #1b2025; border-bottom: 1px solid #313943; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px 28px 48px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    article {{ border: 1px solid #38424c; border-radius: 8px; padding: 18px; background: #1b1f23; }}
    article h3 {{ margin: 14px 0 8px; color: #d9b36a; font-size: 15px; }}
    .gaps {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 7px; }}
    .gap {{ border: 1px solid #38424c; border-radius: 6px; padding: 8px; background: #15191d; display: grid; gap: 3px; }}
    .gap.below_minimum {{ border-color: #a54646; }}
    .gap.needs_improvement, .gap.unknown {{ border-color: #a47f2d; }}
    .gap.solved {{ border-color: #2f7d4a; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .actions a {{ padding: 8px 10px; border: 1px solid #3f596e; border-radius: 6px; background: #202a32; color: #8fc7ff; text-decoration: none; }}
    code {{ background: #262c32; padding: 1px 4px; border-radius: 4px; }}
    .muted {{ color: #b9b1a3; }}
  </style>
</head>
<body>
  <header>
    <h1>Simulacao por Personagem</h1>
    <p class="muted">Busca de mercado rodada para cada personagem com budget de {html.escape(budget)} por plano de upgrade.</p>
  </header>
  <main><div class="grid">{''.join(cards)}</div></main>
</body>
</html>
"""
    output.write_text(body, encoding="utf-8")
    return output


def rows_from_existing_outputs(characters: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for character_slug in characters:
        target = paths.CHARACTER_OUTPUT / character_slug
        if not target.exists():
            continue
        render_character_pages(character_slug)
        character = read_json(target / "active_character.json")
        build = read_json(target / "active_build.json")
        artifacts = {
            path.name: str(path.relative_to(paths.GENERATED)).replace("\\", "/")
            for path in target.iterdir()
            if path.is_file()
        }
        rows.append(
            {
                "character_slug": character_slug,
                "character_name": character.get("name", character_slug),
                "build_slug": build.get("active_slug", character.get("build_slug", "")),
                "build_name": build.get("name", character.get("build_slug", "")),
                "artifacts": artifacts,
            }
        )
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run upgrade searches for saved characters.")
    parser.add_argument("--characters", default="all", help="Comma list or all.")
    parser.add_argument("--budget", default="1000c")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--max-fetch", type=int, default=30)
    parser.add_argument("--profiles", default="all")
    parser.add_argument("--request-delay", type=float)
    parser.add_argument("--best-any-budget-mode", choices=("reuse", "extra", "off"), default="reuse")
    parser.add_argument("--index-only", action="store_true", help="Rebuild the HTML index from existing per-character outputs.")
    parser.add_argument("--skip-market-report", action="store_true", help="Use existing market report instead of rebuilding it once before the matrix.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    characters = selected_characters(args.characters)
    if not characters:
        raise SystemExit("No characters selected. Create them with switch_build.py --create-character.")
    if args.index_only:
        rows = rows_from_existing_outputs(characters)
        output = write_index(rows, args.budget)
        print(f"Character matrix dashboard saved: {output}")
        return 0
    if not args.skip_market_report:
        run_script("market_report.py")
    rows = []
    for character_slug in characters:
        print()
        print("=" * 72)
        print(f"Character: {character_slug}")
        print("=" * 72)
        rows.append(
            run_for_character(
                character_slug,
                args.budget,
                args.top,
                args.max_fetch,
                args.profiles,
                args.request_delay,
                args.best_any_budget_mode,
            )
        )
    output = write_index(rows, args.budget)
    print(f"Character matrix dashboard saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
