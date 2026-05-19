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
import os
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
DEFAULT_UPGRADE_PLAN_JSON = REPORTS / "upgrade_plan.json"
DEFAULT_MARKET_REPORT = REPORTS / "market_report.md"
DEFAULT_MARKET_JSON = ROOT / "market" / "latest_market.json"
DEFAULT_OUTPUT = GENERATED / "build_dashboard.html"
RECOMMENDATIONS_HTML = GENERATED / "upgrade_recommendations.html"
NEXT_SEARCHES_HTML = GENERATED / "next_searches.html"
MARKET_REPORT_HTML = GENERATED / "market_report.html"


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

    index = 0
    while index < len(lines):
        line = lines[index]
        raw = line.rstrip()
        if raw.startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(raw)
            index += 1
            continue
        if raw.startswith("|") and raw.endswith("|"):
            close_list()
            table_lines: list[str] = []
            while index < len(lines):
                table_raw = lines[index].rstrip()
                if not (table_raw.startswith("|") and table_raw.endswith("|")):
                    break
                table_lines.append(table_raw)
                index += 1
            out.append(markdown_table_to_html(table_lines))
            continue
        if not raw:
            close_list()
            index += 1
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
        index += 1

    close_list()
    if in_code:
        out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(out)


def markdown_table_to_html(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    if len(rows) >= 2 and all(set(cell) <= {"-", ":", " "} for cell in rows[1]):
        header = rows[0]
        body = rows[2:]
    else:
        header = []
        body = rows
    parts = ["<table>"]
    if header:
        parts.append("<thead><tr>" + "".join(f"<th>{inline_md(cell)}</th>" for cell in header) + "</tr></thead>")
    parts.append("<tbody>")
    for row in body:
        parts.append("<tr>" + "".join(f"<td>{inline_md(cell)}</td>" for cell in row) + "</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


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


def guarded_slots(gap: dict[str, Any]) -> str:
    slots = gap.get("guarded_slots") or gap.get("protected_slots", {})
    if not slots:
        return "<p class=\"muted\">Nenhum slot sensivel registrado.</p>"
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


def relative_link(path: Path, output: Path) -> str:
    return os.path.relpath(path, output.parent).replace(os.sep, "/")


def file_link(path: Path, label: str, output: Path) -> str:
    if path.resolve() != output.resolve() and not path.exists():
        return f"<span class=\"missing\">{html.escape(label)} nao gerado</span>"
    return f"<a href=\"{html.escape(relative_link(path, output))}\">{html.escape(label)}</a>"


def dashboard_summary(gap: dict[str, Any], upgrade_report: dict[str, Any], upgrade_plan: dict[str, Any]) -> str:
    comparison = gap.get("comparison", {})
    solved = sum(1 for entry in comparison.values() if entry.get("status") == "solved")
    risks = sum(1 for entry in comparison.values() if entry.get("status") != "solved")
    searches = len(upgrade_report.get("recommended_searches", []))
    plans = len(upgrade_plan.get("plans", []))
    cards = [
        ("Gaps resolvidos", solved),
        ("Gaps pendentes", risks),
        ("Buscas sugeridas", searches),
        ("Planos de compra", plans),
    ]
    return "<div class=\"summary-grid\">" + "".join(
        f"<div class=\"summary-card\"><span>{html.escape(label)}</span><strong>{value}</strong></div>" for label, value in cards
    ) + "</div>"


def workflow_overview() -> str:
    return """
    <div class="search-grid">
      <article class="search-card">
        <h4>Mercado para a build</h4>
        <p>Usa os dados do personagem, metas da build e ofertas do trade para sugerir compras que aproximam o personagem da build alvo.</p>
        <small>Saidas: recomendacoes, proximas buscas e plano de compra.</small>
      </article>
      <article class="search-card">
        <h4>Mercado para o filtro</h4>
        <p>Usa nomes, base types, currencies e precos para ajudar a manter o filtro correto e destacar o que vale pegar no chao.</p>
        <small>Saidas tecnicas: sugestoes e auditoria do filtro em Markdown.</small>
      </article>
    </div>
    """


def trade_actions(candidate: dict[str, Any]) -> str:
    links: list[str] = []
    search_url = str(candidate.get("trade_search_url") or candidate.get("trade_url") or "")
    fetch_url = str(candidate.get("trade_fetch_url") or "")
    if search_url:
        links.append(f"<a href=\"{html.escape(search_url)}\" target=\"_blank\" rel=\"noopener\">Busca no trade</a>")
    if fetch_url:
        links.append(f"<a href=\"{html.escape(fetch_url)}\" target=\"_blank\" rel=\"noopener\" title=\"Abre o JSON tecnico da listagem retornada pela API oficial\">JSON tecnico</a>")
    if not links:
        return "<span class=\"muted\">Sem link disponivel</span>"
    return "<div class=\"actions\">" + "".join(links) + "</div>"


def whisper_box(candidate: dict[str, Any]) -> str:
    whisper = str(candidate.get("whisper") or "")
    if not whisper:
        return ""
    return f"<label class=\"whisper\">Whisper<textarea readonly>{html.escape(whisper)}</textarea></label>"


def item_mods_details(candidate: dict[str, Any]) -> str:
    mods = [str(mod) for mod in candidate.get("item_mods", []) if str(mod).strip()]
    if not mods:
        return ""
    items = "".join(f"<li>{html.escape(mod)}</li>" for mod in mods[:12])
    return f"<details class=\"mods\"><summary>Mods lidos</summary><ul>{items}</ul></details>"


def upgrade_plan_cards(upgrade_plan: dict[str, Any], fallback_md: str) -> str:
    plans = upgrade_plan.get("plans", [])
    if not plans:
        if fallback_md:
            return md_to_html(fallback_md)
        return "<p class=\"muted\">Rode plan_upgrade_path.py para gerar planos de compra.</p>"

    cards: list[str] = []
    for plan in plans[:10]:
        candidate_blocks: list[str] = []
        for candidate in plan.get("candidates", []):
            gains = "".join(f"<li>{html.escape(str(gain))}</li>" for gain in candidate.get("gains", [])[:6])
            candidate_blocks.append(
                "<article class=\"deal-item\">"
                f"<h4>{html.escape(str(candidate.get('name', 'Item')))}</h4>"
                f"<p><code>{html.escape(str(candidate.get('slot', 'slot')))}</code> | {html.escape(str(candidate.get('price_text', 'n/d')))} | vendedor: {html.escape(str(candidate.get('seller') or 'n/d'))}</p>"
                f"{trade_actions(candidate)}"
                f"{item_mods_details(candidate)}"
                f"{whisper_box(candidate)}"
                f"<ul>{gains}</ul>"
                "</article>"
            )

        warnings = "".join(f"<li>{html.escape(str(warning))}</li>" for warning in plan.get("warnings", [])[:6])
        gains = "".join(f"<li>{html.escape(str(gain))}</li>" for gain in plan.get("gains", [])[:8])
        cards.append(
            "<section class=\"deal-card\">"
            f"<div class=\"deal-head\"><span class=\"rank\">#{html.escape(str(plan.get('rank', '?')))}</span>"
            f"<h3>{html.escape(str(plan.get('title', 'Plano')))}</h3>"
            f"<strong>{float(plan.get('price_chaos', 0.0)):.1f}c</strong></div>"
            f"<p class=\"muted\">Score {float(plan.get('score', 0.0)):.1f} | Valor {float(plan.get('value_score', 0.0)):.2f}</p>"
            f"<div class=\"deal-grid\">{''.join(candidate_blocks)}</div>"
            f"<div class=\"columns compact\"><div><h4>Melhoras</h4><ul>{gains}</ul></div><div><h4>Alertas</h4><ul>{warnings or '<li>Sem alerta automatico.</li>'}</ul></div></div>"
            "</section>"
        )
    notes = "".join(f"<li>{html.escape(str(note))}</li>" for note in upgrade_plan.get("notes", []))
    notes_html = f"<div class=\"panel small\"><h3>Como interpretar os links</h3><ul>{notes}</ul></div>" if notes else ""
    best = upgrade_plan.get("best_any_budget", [])
    best_html = ""
    if best:
        best_cards = []
        for plan in best[:3]:
            candidate = (plan.get("candidates") or [{}])[0]
            gains = "".join(f"<li>{html.escape(str(gain))}</li>" for gain in plan.get("gains", [])[:6])
            best_cards.append(
                "<article class=\"deal-item\">"
                f"<h4>{html.escape(str(candidate.get('name', 'Item')))}</h4>"
                f"<p><strong>{float(plan.get('price_chaos', 0.0)):.1f}c</strong> | Score {float(plan.get('score', 0.0)):.1f} | Valor {float(plan.get('value_score', 0.0)):.2f}</p>"
                f"{trade_actions(candidate)}"
                f"{item_mods_details(candidate)}"
                f"<ul>{gains}</ul>"
                "</article>"
            )
        best_html = (
            "<section class=\"deal-card\">"
            "<h3>Melhor compra barata sem usar o budget como limite</h3>"
            "<p class=\"muted\">O objetivo aqui e achar custo-beneficio real, mesmo quando o budget informado permitiria gastar mais.</p>"
            f"<div class=\"deal-grid\">{''.join(best_cards)}</div>"
            "</section>"
        )
    return notes_html + best_html + "".join(cards)


def common_css() -> str:
    return """
    :root { color-scheme: dark; }
    body { margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #101214; color: #eee8dc; }
    header { padding: 26px 34px; background: #1b2025; border-bottom: 1px solid #313943; }
    main { max-width: 1240px; margin: 0 auto; padding: 24px 28px 48px; }
    h1, h2, h3, h4 { margin: 0 0 12px; }
    section { margin-bottom: 28px; }
    .muted, small { color: #b9b1a3; }
    .quick-links { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
    .quick-links a, .missing { padding: 8px 10px; border: 1px solid #38424c; border-radius: 6px; background: #20262c; }
    a { color: #8fc7ff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
    .summary-card { border: 1px solid #38424c; border-radius: 8px; padding: 14px; background: #1b1f23; display: grid; gap: 6px; }
    .summary-card span { color: #b9b1a3; }
    .summary-card strong { font-size: 26px; color: #f2c66d; }
    .metric { border: 1px solid #37404a; border-radius: 8px; padding: 14px; background: #1b1f23; display: grid; gap: 6px; }
    .metric span { color: #d8c395; }
    .metric strong { font-size: 24px; }
    .metric.ok { border-color: #2f7d4a; }
    .metric.warn { border-color: #a47f2d; }
    .metric.bad { border-color: #a54646; }
    .search-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
    .search-card { position: relative; border: 1px solid #38424c; border-radius: 8px; padding: 16px; background: #1b1f23; }
    .search-card, .summary-card, .metric, .deal-card, .panel { animation: fadeUp .24s ease both; }
    .rank { color: #d9b36a; font-weight: 700; }
    .columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
    .compact { margin-top: 14px; }
    .panel { border: 1px solid #38424c; border-radius: 8px; padding: 18px; background: #1b1f23; overflow: auto; }
    .panel.small { margin-bottom: 14px; }
    .deal-card { border: 1px solid #44505c; border-radius: 8px; padding: 18px; background: #1b1f23; }
    .deal-head { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
    .deal-head h3 { flex: 1; min-width: 220px; }
    .deal-head strong { color: #f2c66d; font-size: 22px; }
    .deal-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-top: 12px; }
    .deal-item { border: 1px solid #38424c; border-radius: 8px; padding: 14px; background: #15191d; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
    .actions a { padding: 7px 9px; border: 1px solid #3f596e; border-radius: 6px; background: #202a32; }
    details.mods { margin: 10px 0; border: 1px solid #303842; border-radius: 6px; padding: 8px; background: #11161a; }
    details.mods summary { cursor: pointer; color: #d9b36a; }
    .whisper { display: grid; gap: 4px; color: #b9b1a3; margin: 8px 0; }
    textarea { min-height: 54px; resize: vertical; border: 1px solid #38424c; border-radius: 6px; background: #0c0f12; color: #eee8dc; padding: 8px; font: 12px Consolas, monospace; }
    code { background: #262c32; padding: 1px 4px; border-radius: 4px; }
    pre { background: #0c0f12; padding: 12px; border-radius: 6px; overflow: auto; border: 1px solid #303842; }
    li { margin-bottom: 6px; }
    table { width: 100%; border-collapse: collapse; background: #1b1f23; border: 1px solid #38424c; margin: 14px 0 22px; }
    th, td { padding: 10px 12px; border-bottom: 1px solid #303842; text-align: left; vertical-align: top; }
    th { color: #d9b36a; background: #20262c; position: sticky; top: 0; z-index: 1; }
    tr:hover td { background: #20252a; }
    .toolbar { display: grid; grid-template-columns: minmax(220px, 1fr) repeat(3, minmax(140px, 180px)); gap: 10px; margin: 18px 0; }
    input, select { width: 100%; box-sizing: border-box; border: 1px solid #38424c; border-radius: 6px; background: #11161a; color: #eee8dc; padding: 9px 10px; }
    .pill { display: inline-flex; align-items: center; gap: 6px; border: 1px solid #38424c; border-radius: 999px; padding: 5px 9px; margin: 0 6px 6px 0; background: #171c21; color: #d8c395; font-size: 12px; }
    .value-high { color: #f2c66d; font-weight: 700; }
    .value-mid { color: #8fc7ff; }
    .change-up { color: #61e981; }
    .change-down { color: #ff6b6b; }
    .empty-state { border: 1px dashed #46515d; border-radius: 8px; padding: 18px; color: #b9b1a3; }
    @keyframes fadeUp { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    @media (max-width: 900px) { .columns { grid-template-columns: 1fr; } main, header { padding-left: 16px; padding-right: 16px; } }
    @media (max-width: 760px) { .toolbar { grid-template-columns: 1fr; } }
    """


def page_shell(title: str, subtitle: str, body: str, output: Path) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{common_css()}</style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <p class="muted">{html.escape(subtitle)}</p>
    <div class="quick-links">
      {file_link(DEFAULT_OUTPUT, "Dashboard", output)}
      {file_link(RECOMMENDATIONS_HTML, "Recomendacoes", output)}
      {file_link(NEXT_SEARCHES_HTML, "Proximas buscas", output)}
      {file_link(MARKET_REPORT_HTML, "Mercado", output)}
      {file_link(REPORTS / "upgrade_plan.html", "Plano de compra", output)}
    </div>
  </header>
  <main>
    <section class="panel">{body}</section>
  </main>
</body>
</html>
"""


def write_markdown_page(title: str, subtitle: str, markdown: str, output: Path) -> None:
    if not markdown:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page_shell(title, subtitle, md_to_html(markdown), output), encoding="utf-8")


def recommendation_cards(report: dict[str, Any]) -> str:
    searches = report.get("recommended_searches", [])
    if not searches:
        return "<div class=\"empty-state\">Nenhuma recomendacao gerada ainda.</div>"
    cards: list[str] = []
    for index, entry in enumerate(searches, start=1):
        terms = "".join(f"<li>{html.escape(str(term))}</li>" for term in entry.get("trade_terms", [])[:8])
        profiles = "".join(f"<span class=\"pill\">{html.escape(str(profile))}</span>" for profile in entry.get("profiles", []))
        profiles_html = profiles or "<span class=\"muted\">busca manual</span>"
        priority = entry.get("priority_pt") or entry.get("priority") or "n/d"
        cards.append(
            "<article class=\"deal-card\">"
            f"<div class=\"deal-head\"><span class=\"rank\">#{index}</span><h3>{html.escape(str(entry.get('title', 'Recomendacao')))}</h3><strong>{html.escape(str(priority))}</strong></div>"
            f"<p>{html.escape(str(entry.get('reason', '')))}</p>"
            "<div class=\"columns compact\">"
            f"<div><h4>Buscar</h4><ul>{terms}</ul></div>"
            f"<div><h4>Preco alvo</h4><p class=\"muted\">{html.escape(str(entry.get('price_hint', 'n/d')))}</p><h4>Perfis</h4><div>{profiles_html}</div></div>"
            "</div>"
            "</article>"
        )
    return "".join(cards)


def write_recommendations_page(report: dict[str, Any], output: Path) -> None:
    body = (
        "<section><h2>Recomendacoes De Upgrade</h2>"
        "<p class=\"muted\">Leitura priorizada dos gargalos atuais. Ela nao compra automaticamente e nao substitui PoB.</p>"
        f"{recommendation_cards(report)}</section>"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page_shell("Recomendacoes", "Prioridades de compra para aproximar o personagem da build alvo.", body, output), encoding="utf-8")


def write_next_searches_page(report: dict[str, Any], output: Path) -> None:
    searches = report.get("recommended_searches", [])
    cards: list[str] = []
    for entry in searches:
        terms = "".join(f"<span class=\"pill\">{html.escape(str(term))}</span>" for term in entry.get("trade_terms", [])[:8])
        cards.append(
            "<article class=\"search-card\">"
            f"<h4>{html.escape(str(entry.get('title', 'Busca')))}</h4>"
            f"<p>{html.escape(str(entry.get('reason', '')))}</p>"
            f"<div>{terms}</div>"
            "</article>"
        )
    cards_html = "".join(cards) if cards else "<div class=\"empty-state\">Nenhuma busca gerada ainda.</div>"
    body = (
        "<section><h2>Proximas Buscas</h2>"
        "<p class=\"muted\">Use estes termos para montar buscas manuais ou escolher perfis do script.</p>"
        f"<div class=\"search-grid\">{cards_html}</div></section>"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page_shell("Proximas Buscas", "Termos prontos para procurar upgrades com menos ruido.", body, output), encoding="utf-8")


def as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def compact_number(value: float | int | None) -> str:
    if value is None:
        return "n/d"
    number = float(value)
    abs_number = abs(number)
    if abs_number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if abs_number >= 1_000:
        return f"{number / 1_000:.1f}k"
    if abs_number >= 100:
        return f"{number:.0f}"
    if abs_number >= 10:
        return f"{number:.1f}"
    return f"{number:.2f}"


def market_category_summary(items: list[dict[str, Any]]) -> list[tuple[str, int, float]]:
    categories: dict[str, dict[str, float]] = {}
    for item in items:
        category = str(item.get("category") or "Outros")
        entry = categories.setdefault(category, {"count": 0, "max": 0.0})
        entry["count"] += 1
        entry["max"] = max(entry["max"], as_float(item.get("chaos_value")))
    return sorted(
        ((category, int(data["count"]), data["max"]) for category, data in categories.items()),
        key=lambda row: (row[1], row[2]),
        reverse=True,
    )


def market_card_list(title: str, items: list[dict[str, Any]], metric: str) -> str:
    if not items:
        return f"<article class=\"search-card\"><h4>{html.escape(title)}</h4><p class=\"muted\">Sem dados.</p></article>"
    rows = []
    for item in items[:6]:
        chaos = compact_number(item.get("chaos_value"))
        change = as_float(item.get("change_percent"))
        change_class = "change-up" if change > 0 else "change-down" if change < 0 else "muted"
        extra = compact_number(item.get("listing_count")) if metric == "liquidez" else f"{change:+.1f}%"
        rows.append(
            "<li>"
            f"<strong>{html.escape(str(item.get('name', 'Item')))}</strong> "
            f"<span class=\"muted\">{html.escape(str(item.get('category', '')))}</span> "
            f"<span class=\"value-high\">{chaos}c</span> "
            f"<span class=\"{change_class}\">{html.escape(extra)}</span>"
            "</li>"
        )
    return f"<article class=\"search-card\"><h4>{html.escape(title)}</h4><ul>{''.join(rows)}</ul></article>"


def market_page(market: dict[str, Any], output: Path) -> str:
    items = [item for item in market.get("items", []) if isinstance(item, dict)]
    items.sort(key=lambda item: as_float(item.get("chaos_value")), reverse=True)
    categories = market_category_summary(items)
    category_options = "".join(
        f"<option value=\"{html.escape(category)}\">{html.escape(category)} ({count})</option>"
        for category, count, _ in categories
    )
    category_pills = "".join(
        f"<span class=\"pill\">{html.escape(category)} <strong>{count}</strong> <small>top {compact_number(top)}c</small></span>"
        for category, count, top in categories[:14]
    )
    top_value = items[:6]
    top_liquid = sorted(items, key=lambda item: as_float(item.get("listing_count")), reverse=True)[:6]
    top_movers = sorted(items, key=lambda item: as_float(item.get("change_percent")), reverse=True)[:6]
    falling = sorted(items, key=lambda item: as_float(item.get("change_percent")))[:6]
    payload = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    generated = str(market.get("generated_at") or "n/d")
    league = str(market.get("league") or "n/d")
    body = f"""
    <section>
      <h2>Resumo Do Mercado</h2>
      <p class="muted">Esta pagina e um mapa de precos da liga. Ela ajuda a decidir o que vale destacar no filtro e a entender o ambiente economico antes de procurar upgrades.</p>
      <div class="summary-grid">
        <div class="summary-card"><span>Liga</span><strong>{html.escape(league)}</strong></div>
        <div class="summary-card"><span>Itens coletados</span><strong>{len(items)}</strong></div>
        <div class="summary-card"><span>Categorias</span><strong>{len(categories)}</strong></div>
        <div class="summary-card"><span>Gerado em</span><strong>{html.escape(generated[:10])}</strong></div>
      </div>
    </section>
    <section>
      <h2>Categorias</h2>
      <div>{category_pills}</div>
    </section>
    <section class="search-grid">
      {market_card_list("Mais caros", top_value, "valor")}
      {market_card_list("Mais liquidos", top_liquid, "liquidez")}
      {market_card_list("Subindo mais", top_movers, "variacao")}
      {market_card_list("Caindo mais", falling, "variacao")}
    </section>
    <section class="panel">
      <h2>Tabela Interativa</h2>
      <div class="toolbar">
        <input id="marketSearch" type="search" placeholder="Buscar item, categoria, base type...">
        <select id="marketCategory"><option value="">Todas categorias</option>{category_options}</select>
        <input id="marketMinChaos" type="number" min="0" step="1" placeholder="Min chaos">
        <select id="marketSort">
          <option value="chaos_desc">Maior valor</option>
          <option value="chaos_asc">Menor valor</option>
          <option value="liquidity_desc">Maior liquidez</option>
          <option value="change_desc">Maior alta</option>
          <option value="change_asc">Maior queda</option>
          <option value="name_asc">Nome A-Z</option>
        </select>
      </div>
      <p id="marketCount" class="muted"></p>
      <table>
        <thead>
          <tr><th>Item</th><th>Categoria</th><th>Chaos</th><th>Divine</th><th>Liquidez</th><th>Variacao</th><th>Uso</th></tr>
        </thead>
        <tbody id="marketRows"></tbody>
      </table>
      <div id="marketEmpty" class="empty-state" hidden>Nenhum item bateu com os filtros atuais.</div>
    </section>
    <script>
      const MARKET_ITEMS = {payload};
      const rowsEl = document.getElementById('marketRows');
      const emptyEl = document.getElementById('marketEmpty');
      const countEl = document.getElementById('marketCount');
      const searchEl = document.getElementById('marketSearch');
      const categoryEl = document.getElementById('marketCategory');
      const minChaosEl = document.getElementById('marketMinChaos');
      const sortEl = document.getElementById('marketSort');
      function n(value) {{ return Number.isFinite(Number(value)) ? Number(value) : 0; }}
      function fmt(value) {{
        const num = Number(value);
        if (!Number.isFinite(num)) return 'n/d';
        if (Math.abs(num) >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (Math.abs(num) >= 1000) return (num / 1000).toFixed(1) + 'k';
        if (Math.abs(num) >= 100) return num.toFixed(0);
        if (Math.abs(num) >= 10) return num.toFixed(1);
        return num.toFixed(2);
      }}
      function escapeHtml(value) {{
        return String(value ?? '').replace(/[&<>"']/g, char => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[char]));
      }}
      function tierLabel(item) {{
        const chaos = n(item.chaos_value);
        if (chaos >= 100) return 'Filtro: destaque maximo';
        if (chaos >= 50) return 'Filtro: muito alto';
        if (chaos >= 20) return 'Filtro: alto';
        if (chaos >= 5) return 'Filtro: visivel';
        if (chaos >= 1) return 'Filtro: baixo';
        return 'Filtro: micro/oculto';
      }}
      function render() {{
        const query = searchEl.value.trim().toLowerCase();
        const category = categoryEl.value;
        const minChaos = Number(minChaosEl.value || 0);
        let filtered = MARKET_ITEMS.filter(item => {{
          const haystack = [item.name, item.category, item.base_type, item.variant, item.requested_category].join(' ').toLowerCase();
          return (!query || haystack.includes(query)) &&
            (!category || item.category === category) &&
            n(item.chaos_value) >= minChaos;
        }});
        const sort = sortEl.value;
        filtered.sort((a, b) => {{
          if (sort === 'chaos_asc') return n(a.chaos_value) - n(b.chaos_value);
          if (sort === 'liquidity_desc') return n(b.listing_count) - n(a.listing_count);
          if (sort === 'change_desc') return n(b.change_percent) - n(a.change_percent);
          if (sort === 'change_asc') return n(a.change_percent) - n(b.change_percent);
          if (sort === 'name_asc') return String(a.name || '').localeCompare(String(b.name || ''));
          return n(b.chaos_value) - n(a.chaos_value);
        }});
        const visible = filtered.slice(0, 250);
        rowsEl.innerHTML = visible.map(item => {{
          const change = n(item.change_percent);
          const changeClass = change > 0 ? 'change-up' : change < 0 ? 'change-down' : 'muted';
          const valueClass = n(item.chaos_value) >= 50 ? 'value-high' : n(item.chaos_value) >= 5 ? 'value-mid' : '';
          return `<tr>
            <td><strong>${{escapeHtml(item.name)}}</strong><br><small>${{escapeHtml(item.base_type || item.variant || item.details_id || '')}}</small></td>
            <td>${{escapeHtml(item.category || '')}}</td>
            <td class="${{valueClass}}">${{fmt(item.chaos_value)}}c</td>
            <td>${{item.divine_value == null ? '' : fmt(item.divine_value)}}</td>
            <td>${{fmt(item.listing_count)}}</td>
            <td class="${{changeClass}}">${{change.toFixed(1)}}%</td>
            <td><span class="pill">${{tierLabel(item)}}</span></td>
          </tr>`;
        }}).join('');
        countEl.textContent = `${{filtered.length}} itens encontrados. Mostrando ${{visible.length}} para manter a pagina leve.`;
        emptyEl.hidden = filtered.length !== 0;
      }}
      [searchEl, categoryEl, minChaosEl, sortEl].forEach(el => el.addEventListener('input', render));
      render();
    </script>
    """
    return page_shell("Mercado", "Precos da liga organizados para leitura humana e manutencao do filtro.", body, output)


def write_market_page(market: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(market_page(market, output), encoding="utf-8")


def render_dashboard(
    gap: dict[str, Any],
    upgrade_report: dict[str, Any],
    next_searches_md: str,
    recommendations_md: str,
    upgrade_plan_md: str,
    upgrade_plan_json: dict[str, Any],
    output: Path,
) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PoE Build Agent Dashboard</title>
  <style>{common_css()}</style>
</head>
<body>
  <header>
    <h1>PoE Build Agent Dashboard</h1>
    <p class="muted">Gerado em {html.escape(generated)}. Painel estatico para ler gaps, proximas buscas e plano de upgrade sem abrir varios arquivos.</p>
    <div class="quick-links">
      {file_link(RECOMMENDATIONS_HTML, "Recomendacoes", output)}
      {file_link(NEXT_SEARCHES_HTML, "Proximas buscas", output)}
      {file_link(REPORTS / "upgrade_plan.html", "Plano de compra", output)}
      {file_link(MARKET_REPORT_HTML, "Mercado", output)}
    </div>
  </header>
  <main>
    <section>
      <h2>Resumo</h2>
      {dashboard_summary(gap, upgrade_report, upgrade_plan_json)}
    </section>
    <section>
      <h2>Como Este Repositorio Se Divide</h2>
      {workflow_overview()}
    </section>
    <section>
      <h2>Gaps Da Build</h2>
      {gap_cards(gap)}
    </section>
    <section>
      <h2>Slots Sensíveis</h2>
      <p class="muted">Estes itens podem ser trocados, mas a troca precisa preservar os pisos da build e passar o ganho minimo configurado.</p>
      {guarded_slots(gap)}
    </section>
    <section>
      <h2>Plano De Compra</h2>
      {upgrade_plan_cards(upgrade_plan_json, upgrade_plan_md)}
    </section>
    <section class="columns">
      <div class="panel">
        <h2>Recomendacoes</h2>
        {md_to_html(recommendations_md) if recommendations_md else '<p class="muted">Rode recommend_next_steps.py.</p>'}
      </div>
      <div class="panel">
        <h2>Proximas Buscas</h2>
        {recommended_search_cards(upgrade_report)}
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
    parser.add_argument("--upgrade-plan-json", type=Path, default=DEFAULT_UPGRADE_PLAN_JSON)
    parser.add_argument("--market-report", type=Path, default=DEFAULT_MARKET_REPORT)
    parser.add_argument("--market-json", type=Path, default=DEFAULT_MARKET_JSON)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    next_searches_md = read_text(args.next_searches)
    recommendations_md = read_text(args.recommendations)
    market_json = read_json(args.market_json)
    upgrade_report = read_json(args.upgrade_report)
    content = render_dashboard(
        gap=read_json(args.gap),
        upgrade_report=upgrade_report,
        next_searches_md=next_searches_md,
        recommendations_md=recommendations_md,
        upgrade_plan_md=read_text(args.upgrade_plan),
        upgrade_plan_json=read_json(args.upgrade_plan_json),
        output=args.output,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    if upgrade_report:
        write_recommendations_page(upgrade_report, RECOMMENDATIONS_HTML)
        write_next_searches_page(upgrade_report, NEXT_SEARCHES_HTML)
    else:
        write_markdown_page("Recomendacoes", "Leitura guiada dos proximos passos da build.", recommendations_md, RECOMMENDATIONS_HTML)
        write_markdown_page("Proximas Buscas", "Termos e perfis para procurar upgrades com mais seguranca.", next_searches_md, NEXT_SEARCHES_HTML)
    if market_json:
        write_market_page(market_json, MARKET_REPORT_HTML)
    else:
        write_markdown_page("Mercado", "Snapshot formatado dos precos coletados para a liga atual.", read_text(args.market_report), MARKET_REPORT_HTML)
    print(f"Dashboard saved: {args.output}")
    print(f"HTML pages saved: {GENERATED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
