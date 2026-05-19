#!/usr/bin/env python3
"""
generate_dashboard.py

Builds a single beginner-friendly HTML dashboard from the generated build-agent
files and existing market reports. The dashboard is intentionally static: it can
be opened directly in a browser without a server.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "data" / "generated"
REPORTS = ROOT / "market" / "reports"
DEFAULT_GAP = GENERATED / "gap_analysis.json"
DEFAULT_UPGRADE_REPORT = GENERATED / "upgrade_report.json"
DEFAULT_NEXT_SEARCHES = GENERATED / "next_searches.md"
DEFAULT_RECOMMENDATIONS = GENERATED / "upgrade_recommendations.md"
DEFAULT_UPGRADE_PLAN = REPORTS / "upgrade_plan.md"
DEFAULT_OUTPUT = GENERATED / "build_dashboard.html"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def md_to_html(markdown: str) -> str:
    """Small Markdown subset renderer for generated reports."""
    lines = markdown.splitlines()
    out: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for line in lines:
        raw = line.rstrip()
        if raw.startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
            continue
        if in_code:
            code_lines.append(raw)
            continue
        if not raw:
            close_list()
            continue
        if raw.startswith("# "):
            close_list()
            out.append(f"<h2>{inline_md(raw[2:])}</h2>")
        elif raw.startswith("## "):
            close_list()
            out.append(f"<h3>{inline_md(raw[3:])}</h3>")
        elif raw.startswith("### "):
            close_list()
            out.append(f"<h4>{inline_md(raw[4:])}</h4>")
        elif raw.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline_md(raw[2:])}</li>")
        else:
            close_list()
            out.append(f"<p>{inline_md(raw)}</p>")

    close_list()
    if in_code:
        out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(out)


def inline_md(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def status_class(status: str) -> str:
    if status == "solved":
        return "ok"
    if status == "below_minimum":
        return "bad"
    if status in {"needs_improvement", "unknown"}:
        return "warn"
    return "neutral"


def gap_cards(gap: dict[str, Any]) -> str:
    comparison = gap.get("comparison", {})
    if not comparison:
        return "<p class=\"muted\">Nenhuma analise de gaps disponivel. Rode compare_current_to_target.py.</p>"
    cards: list[str] = []
    for key, entry in sorted(comparison.items()):
        status = str(entry.get("status", "unknown"))
        current = entry.get("current")
        goal = entry.get("goal")
        minimum = entry.get("minimum")
        cards.append(
            "<div class=\"metric {cls}\">"
            "<span>{name}</span>"
            "<strong>{current}</strong>"
            "<small>min {minimum} | meta {goal} | {status}</small>"
            "</div>".format(
                cls=status_class(status),
                name=html.escape(key),
                current=html.escape(str(current)),
                minimum=html.escape(str(minimum)),
                goal=html.escape(str(goal)),
                status=html.escape(status),
            )
        )
    return "<div class=\"metrics\">" + "".join(cards) + "</div>"


def protected_slots(gap: dict[str, Any]) -> str:
    slots = gap.get("protected_slots", {})
    if not slots:
        return "<p class=\"muted\">Nenhum slot protegido registrado.</p>"
    items = "".join(f"<li><code>{html.escape(slot)}</code>: {html.escape(reason)}</li>" for slot, reason in slots.items())
    return f"<ul>{items}</ul>"


def recommended_search_cards(report: dict[str, Any]) -> str:
    searches = report.get("recommended_searches", [])
    if not searches:
        return "<p class=\"muted\">Nenhuma busca recomendada gerada ainda.</p>"
    cards: list[str] = []
    for index, entry in enumerate(searches[:8], start=1):
        terms = "".join(f"<li>{html.escape(term)}</li>" for term in entry.get("trade_terms", [])[:5])
        profiles = ", ".join(f"`{profile}`" for profile in entry.get("profiles", [])) or "busca manual"
        cards.append(
            "<article class=\"search-card\">"
            f"<span class=\"rank\">#{index}</span>"
            f"<h4>{html.escape(entry.get('title', 'Busca'))}</h4>"
            f"<p>{html.escape(entry.get('reason', ''))}</p>"
            f"<ul>{terms}</ul>"
            f"<small>Perfis: {html.escape(profiles)}</small>"
            "</article>"
        )
    return "<div class=\"search-grid\">" + "".join(cards) + "</div>"


def file_link(path: Path, label: str) -> str:
    if not path.exists():
        return f"<span class=\"missing\">{html.escape(label)} nao gerado</span>"
    rel = path.relative_to(ROOT).as_posix()
    return f"<a href=\"../{html.escape(rel)}\">{html.escape(label)}</a>"


def render_dashboard(
    gap: dict[str, Any],
    upgrade_report: dict[str, Any],
    next_searches_md: str,
    recommendations_md: str,
    upgrade_plan_md: str,
    output: Path,
) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PoE Build Agent Dashboard</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #101214; color: #eee8dc; }}
    header {{ padding: 26px 34px; background: #1b2025; border-bottom: 1px solid #313943; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 24px 28px 48px; }}
    h1, h2, h3, h4 {{ margin: 0 0 12px; }}
    section {{ margin-bottom: 28px; }}
    .muted, small {{ color: #b9b1a3; }}
    .quick-links {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .quick-links a, .missing {{ padding: 8px 10px; border: 1px solid #38424c; border-radius: 6px; background: #20262c; }}
    a {{ color: #8fc7ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #37404a; border-radius: 8px; padding: 14px; background: #1b1f23; display: grid; gap: 6px; }}
    .metric span {{ color: #d8c395; }}
    .metric strong {{ font-size: 24px; }}
    .metric.ok {{ border-color: #2f7d4a; }}
    .metric.warn {{ border-color: #a47f2d; }}
    .metric.bad {{ border-color: #a54646; }}
    .search-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    .search-card {{ position: relative; border: 1px solid #38424c; border-radius: 8px; padding: 16px; background: #1b1f23; }}
    .rank {{ color: #d9b36a; font-weight: 700; }}
    .columns {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .panel {{ border: 1px solid #38424c; border-radius: 8px; padding: 18px; background: #1b1f23; overflow: auto; }}
    code {{ background: #262c32; padding: 1px 4px; border-radius: 4px; }}
    pre {{ background: #0c0f12; padding: 12px; border-radius: 6px; overflow: auto; }}
    li {{ margin-bottom: 6px; }}
    @media (max-width: 900px) {{ .columns {{ grid-template-columns: 1fr; }} main, header {{ padding-left: 16px; padding-right: 16px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>PoE Build Agent Dashboard</h1>
    <p class="muted">Gerado em {html.escape(generated)}. Painel estatico para ler gaps, proximas buscas e plano de upgrade sem abrir varios arquivos.</p>
    <div class="quick-links">
      {file_link(DEFAULT_RECOMMENDATIONS, "Recomendacoes MD")}
      {file_link(DEFAULT_NEXT_SEARCHES, "Proximas buscas MD")}
      {file_link(DEFAULT_UPGRADE_PLAN, "Plano de compra MD")}
      {file_link(REPORTS / "upgrade_plan.html", "Plano de compra HTML")}
      {file_link(REPORTS / "market_report.md", "Mercado")}
      {file_link(REPORTS / "filter_audit.md", "Auditoria")}
    </div>
  </header>
  <main>
    <section>
      <h2>Gaps Da Build</h2>
      {gap_cards(gap)}
    </section>
    <section>
      <h2>Slots Protegidos</h2>
      {protected_slots(gap)}
    </section>
    <section>
      <h2>Proximas Buscas</h2>
      {recommended_search_cards(upgrade_report)}
    </section>
    <section class="columns">
      <div class="panel">
        <h2>Recomendacoes</h2>
        {md_to_html(recommendations_md) if recommendations_md else '<p class="muted">Rode recommend_next_steps.py.</p>'}
      </div>
      <div class="panel">
        <h2>Plano De Compra</h2>
        {md_to_html(upgrade_plan_md) if upgrade_plan_md else '<p class="muted">Rode plan_upgrade_path.py.</p>'}
      </div>
    </section>
    <section class="panel">
      <h2>Arquivo De Buscas</h2>
      {md_to_html(next_searches_md) if next_searches_md else '<p class="muted">Rode recommend_next_steps.py.</p>'}
    </section>
  </main>
</body>
</html>
"""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a static HTML dashboard for the build agent.")
    parser.add_argument("--gap", type=Path, default=DEFAULT_GAP)
    parser.add_argument("--upgrade-report", type=Path, default=DEFAULT_UPGRADE_REPORT)
    parser.add_argument("--next-searches", type=Path, default=DEFAULT_NEXT_SEARCHES)
    parser.add_argument("--recommendations", type=Path, default=DEFAULT_RECOMMENDATIONS)
    parser.add_argument("--upgrade-plan", type=Path, default=DEFAULT_UPGRADE_PLAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    content = render_dashboard(
        gap=read_json(args.gap),
        upgrade_report=read_json(args.upgrade_report),
        next_searches_md=read_text(args.next_searches),
        recommendations_md=read_text(args.recommendations),
        upgrade_plan_md=read_text(args.upgrade_plan),
        output=args.output,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Dashboard saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
