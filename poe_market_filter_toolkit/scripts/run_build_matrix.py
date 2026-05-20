#!/usr/bin/env python3
"""
run_build_matrix.py

Runs the build-analysis flow for multiple target build profiles and stores the
generated reports under data/generated/builds/<slug>/.

This is useful when tracking gear for more than one player/build at once. The
script activates each selected target build, runs compare/recommend/optional
upgrade planning/dashboard, copies the generated artifacts to a per-build
folder, then creates a multi_build_dashboard.html index with links.
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data" / "generated"
MATRIX_DIR = GENERATED / "builds"
REPORTS = ROOT / "market" / "reports"
PROFILES_DIR = ROOT / "builds" / "profiles"
ACTIVE_BUILD = ROOT / "builds" / "active_build.json"
ACTIVE_CHARACTER = ROOT / "builds" / "active_character.json"


ARTIFACTS = [
    GENERATED / "build_dashboard.html",
    GENERATED / "upgrade_recommendations.html",
    GENERATED / "next_searches.html",
    GENERATED / "market_report.html",
    GENERATED / "upgrade_plan.html",
    GENERATED / "gap_analysis.json",
    GENERATED / "gap_analysis.md",
    GENERATED / "next_searches.md",
    GENERATED / "upgrade_recommendations.md",
    GENERATED / "upgrade_report.json",
    REPORTS / "upgrade_plan.md",
    REPORTS / "upgrade_plan.json",
]

HTML_PAGES = {
    "build_dashboard.html": "Dashboard",
    "upgrade_plan.html": "Plano de compra",
    "upgrade_recommendations.html": "Recomendacoes",
    "next_searches.html": "Proximas buscas",
    "market_report.html": "Mercado",
}

GLOBAL_LINK_REPLACEMENTS = {
    "../../data/generated/build_dashboard.html": "build_dashboard.html",
    "../../data/generated/upgrade_recommendations.html": "upgrade_recommendations.html",
    "../../data/generated/next_searches.html": "next_searches.html",
    "../../data/generated/market_report.html": "market_report.html",
    "../../market/reports/upgrade_plan.html": "upgrade_plan.html",
    "../build_dashboard.html": "build_dashboard.html",
    "../upgrade_recommendations.html": "upgrade_recommendations.html",
    "../next_searches.html": "next_searches.html",
    "../market_report.html": "market_report.html",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_script(script_name: str, *args: str) -> None:
    script_path = ROOT / "scripts" / script_name
    command = [sys.executable, str(script_path), *args]
    print("Running:", " ".join([script_name, *args]), flush=True)
    result = subprocess.run(command, cwd=str(ROOT))
    if result.returncode != 0:
        raise SystemExit(f"Script failed: {script_name} (exit code {result.returncode})")


def known_builds() -> list[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(path.name for path in PROFILES_DIR.iterdir() if path.is_dir())


def copy_artifacts(slug: str) -> dict[str, str]:
    target = MATRIX_DIR / slug
    target.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    for source in ARTIFACTS:
        if not source.exists():
            continue
        destination = target / source.name
        shutil.copy2(source, destination)
        copied[source.name] = str(destination.relative_to(GENERATED)).replace("\\", "/")
    active = read_json(ACTIVE_BUILD)
    (target / "active_build.json").write_text(json.dumps(active, indent=2, ensure_ascii=False), encoding="utf-8")
    copied["active_build.json"] = str((target / "active_build.json").relative_to(GENERATED)).replace("\\", "/")
    if ACTIVE_CHARACTER.exists():
        active_character = read_json(ACTIVE_CHARACTER)
        (target / "active_character.json").write_text(json.dumps(active_character, indent=2, ensure_ascii=False), encoding="utf-8")
        copied["active_character.json"] = str((target / "active_character.json").relative_to(GENERATED)).replace("\\", "/")
    return copied


def run_for_build(slug: str, budget: str | None, profiles: str | None, top: int | None, max_fetch: int | None) -> dict[str, Any]:
    run_script("switch_build.py", "--switch-to", slug)
    active = read_json(ACTIVE_BUILD)
    run_script("compare_current_to_target.py")
    run_script("recommend_next_steps.py")
    planner_args: list[str] = []
    if budget:
        planner_args.extend(["--budget", budget])
    if profiles:
        planner_args.extend(["--profiles", profiles])
    if top is not None:
        planner_args.extend(["--top", str(top)])
    if max_fetch is not None:
        planner_args.extend(["--max-fetch", str(max_fetch)])
    run_script("plan_upgrade_path.py", *planner_args)
    run_script("generate_dashboard.py")
    artifacts = copy_artifacts(slug)
    return {
        "slug": slug,
        "name": active.get("name", slug),
        "pob": active.get("pob", {}),
        "artifacts": artifacts,
    }


def page_path_for_slug(slug: str, page_name: str) -> str:
    return f"../{slug}/{page_name}"


def build_switcher(slug: str, page_name: str, rows: list[dict[str, Any]]) -> str:
    options = []
    for row in rows:
        row_slug = str(row["slug"])
        name = str(row.get("name") or row_slug)
        selected = " selected" if row_slug == slug else ""
        options.append(f"<option value=\"{html.escape(row_slug)}\"{selected}>{html.escape(name)}</option>")

    tabs = []
    for filename, label in HTML_PAGES.items():
        active = " active" if filename == page_name else ""
        tabs.append(f"<a class=\"build-tab{active}\" href=\"{html.escape(filename)}\">{html.escape(label)}</a>")

    return f"""
  <style>
    .multi-build-bar {{
      position: sticky; top: 0; z-index: 9999;
      display: flex; flex-wrap: wrap; align-items: center; gap: 12px;
      padding: 10px 18px; background: rgba(13, 17, 22, .96);
      border-bottom: 1px solid #38424c; box-shadow: 0 6px 20px rgba(0,0,0,.28);
      backdrop-filter: blur(10px);
    }}
    .multi-build-bar label {{ display: flex; align-items: center; gap: 8px; color: #d8c395; font-size: 13px; }}
    .multi-build-bar select {{
      min-width: 240px; max-width: 360px; border: 1px solid #38424c; border-radius: 6px;
      background: #11161a; color: #eee8dc; padding: 7px 9px;
    }}
    .multi-build-tabs {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .multi-build-tabs a {{
      padding: 7px 9px; border: 1px solid #38424c; border-radius: 6px;
      background: #20262c; color: #8fc7ff; text-decoration: none; font-size: 13px;
    }}
    .multi-build-tabs a.active {{ border-color: #d9b36a; color: #f2c66d; background: #2a2418; }}
    @media (max-width: 760px) {{
      .multi-build-bar {{ align-items: stretch; }}
      .multi-build-bar label, .multi-build-bar select, .multi-build-tabs {{ width: 100%; }}
    }}
  </style>
  <nav class="multi-build-bar" aria-label="Navegacao multi-build">
    <label>Build
      <select id="multiBuildSelect" data-page="{html.escape(page_name)}">
        {''.join(options)}
      </select>
    </label>
    <div class="multi-build-tabs">{''.join(tabs)}</div>
  </nav>
  <script>
    (() => {{
      const select = document.getElementById('multiBuildSelect');
      if (!select) return;
      select.addEventListener('change', () => {{
        const page = select.dataset.page || 'build_dashboard.html';
        window.location.href = `../${{select.value}}/${{page}}`;
      }});
    }})();
  </script>
"""


def localize_global_links(content: str) -> str:
    updated = content
    for old, new in GLOBAL_LINK_REPLACEMENTS.items():
        updated = updated.replace(old, new)
    return updated


def inject_build_switcher(content: str, slug: str, page_name: str, rows: list[dict[str, Any]]) -> str:
    content = localize_global_links(content)
    if "multi-build-bar" in content:
        return content
    switcher = build_switcher(slug, page_name, rows)
    if "<body>" in content:
        return content.replace("<body>", f"<body>\n{switcher}", 1)
    return switcher + content


def postprocess_build_pages(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        slug = str(row["slug"])
        build_dir = MATRIX_DIR / slug
        for page_name in HTML_PAGES:
            page = build_dir / page_name
            if not page.exists():
                continue
            content = page.read_text(encoding="utf-8")
            page.write_text(inject_build_switcher(content, slug, page_name, rows), encoding="utf-8")


def write_index(rows: list[dict[str, Any]]) -> Path:
    output = GENERATED / "multi_build_dashboard.html"
    cards = []
    options = []
    for index, row in enumerate(rows):
        slug = str(row["slug"])
        name = str(row.get("name") or slug)
        artifacts = row.get("artifacts", {})
        dashboard = artifacts.get("build_dashboard.html", "")
        plan = artifacts.get("upgrade_plan.html", "")
        recommendations = artifacts.get("upgrade_recommendations.html", "")
        pob = row.get("pob") if isinstance(row.get("pob"), dict) else {}
        pob_value = str(pob.get("value") or "")
        options.append(f"<option value=\"{html.escape(slug)}\">{html.escape(name)}</option>")
        links = []
        if dashboard:
            links.append(f"<a href=\"{html.escape(dashboard)}\">Dashboard</a>")
        if plan:
            links.append(f"<a href=\"{html.escape(plan)}\">Plano de compra</a>")
        if recommendations:
            links.append(f"<a href=\"{html.escape(recommendations)}\">Recomendacoes</a>")
        if pob_value.startswith(("http://", "https://")):
            links.append(f"<a href=\"{html.escape(pob_value)}\" target=\"_blank\" rel=\"noopener\">PoB</a>")
        cards.append(
            f"<article class=\"card\" data-build=\"{html.escape(slug)}\" {'hidden' if index else ''}>"
            f"<h2>{html.escape(name)}</h2>"
            f"<p><code>{html.escape(slug)}</code></p>"
            f"<div class=\"actions\">{''.join(links)}</div>"
            "</article>"
        )

    css = """
    body { margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #101214; color: #eee8dc; }
    header { padding: 28px 34px; background: #1b2025; border-bottom: 1px solid #313943; }
    main { max-width: 1120px; margin: 0 auto; padding: 24px 28px 48px; }
    select { min-width: 280px; border: 1px solid #38424c; border-radius: 6px; background: #11161a; color: #eee8dc; padding: 10px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 18px; }
    .card { border: 1px solid #38424c; border-radius: 8px; padding: 18px; background: #1b1f23; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }
    .actions a { padding: 8px 10px; border: 1px solid #3f596e; border-radius: 6px; background: #202a32; color: #8fc7ff; text-decoration: none; }
    code { background: #262c32; padding: 1px 4px; border-radius: 4px; }
    .muted { color: #b9b1a3; }
    """
    body = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Multi Build Dashboard</title>
  <style>{css}</style>
</head>
<body>
  <header>
    <h1>Multi Build Dashboard</h1>
    <p class="muted">Resultados separados por build alvo. Abra uma pagina da build e use a barra superior para alternar sem misturar relatorios.</p>
    <select id="buildSelect">{''.join(options)}</select>
  </header>
  <main><div class="grid">{''.join(cards)}</div></main>
  <script>
    const select = document.getElementById('buildSelect');
    const cards = Array.from(document.querySelectorAll('[data-build]'));
    select.addEventListener('change', () => {{
      cards.forEach(card => card.hidden = card.dataset.build !== select.value);
    }});
  </script>
</body>
</html>
"""
    output.write_text(body, encoding="utf-8")
    return output


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run build reports for multiple target build profiles.")
    parser.add_argument("--builds", default="active", help="Comma list of build slugs, all, or active.")
    parser.add_argument("--budget", help="Budget passed to plan_upgrade_path.py for each build.")
    parser.add_argument("--profiles", help="Profiles passed to plan_upgrade_path.py.")
    parser.add_argument("--top", type=int)
    parser.add_argument("--max-fetch", type=int)
    return parser.parse_args(argv)


def selected_builds(raw: str) -> list[str]:
    if raw == "all":
        return known_builds()
    if raw == "active":
        active = read_json(ACTIVE_BUILD).get("active_slug")
        return [str(active)] if active else []
    return [slug.strip() for slug in raw.split(",") if slug.strip()]


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    builds = selected_builds(args.builds)
    if not builds:
        raise SystemExit("No builds selected. Use --builds all or create profiles with switch_build.py.")

    rows = []
    for slug in builds:
        print()
        print("=" * 72)
        print(f"Build: {slug}")
        print("=" * 72)
        rows.append(run_for_build(slug, args.budget, args.profiles, args.top, args.max_fetch))

    postprocess_build_pages(rows)
    output = write_index(rows)
    print(f"Multi-build dashboard saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
