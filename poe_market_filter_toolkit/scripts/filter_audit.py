#!/usr/bin/env python3
"""
filter_audit.py

Runs a conservative structural audit over .filter files.

It looks for:
- Duplicate BaseType entries.
- Known risky or removed BaseTypes.
- Generic Class rules that may appear before specific BaseType rules.
- BaseType lines without quoted names.

Usage:
    python scripts/filter_audit.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
CONFIG_FILE = ROOT / "config" / "market_config.json"
FILTER_DIR = ROOT / "filters" / "current"
REPORT_DIR = ROOT / "market" / "reports"
REPORT_FILE = REPORT_DIR / "filter_audit.md"

BASE_TYPE_RE = re.compile(r"\bBaseType\s+(.+)", re.IGNORECASE)
CLASS_RE = re.compile(r"\bClass\s+(.+)", re.IGNORECASE)
QUOTED_RE = re.compile(r'"([^"]+)"')


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def find_filter_files() -> list[Path]:
    paths = list(FILTER_DIR.glob("*.filter")) + list(REPO_ROOT.glob("*.filter"))
    return sorted(set(paths))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path.relative_to(REPO_ROOT))


def extract_quoted(line: str) -> list[str]:
    return [x.strip() for x in QUOTED_RE.findall(line)]


def audit_filter(path: Path, config: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    base_locations: dict[str, list[int]] = defaultdict(list)
    class_locations: dict[str, list[int]] = defaultdict(list)

    for idx, line in enumerate(lines, start=1):
        base_match = BASE_TYPE_RE.search(line)
        if base_match:
            for name in extract_quoted(line):
                base_locations[name].append(idx)

        class_match = CLASS_RE.search(line)
        if class_match:
            for name in extract_quoted(line):
                class_locations[name].append(idx)

    duplicate_warnings = []
    for name, locs in sorted(base_locations.items()):
        if len(locs) > 1:
            duplicate_warnings.append(
                f"- `BaseType \"{name}\"` appears {len(locs)} times on lines {', '.join(map(str, locs[:10]))}."
            )

    if duplicate_warnings:
        warnings.append("### Duplicate BaseTypes")
        warnings.append("")
        warnings.append(
            "Some duplicates are intentional in this filter because early jackpot/global rules override later generic rules."
        )
        warnings.extend(duplicate_warnings)
        warnings.append("")

    risky_names = config.get("known_removed_or_risky_base_types", [])
    risky_warnings = []
    for risky in risky_names:
        if risky in base_locations:
            risky_warnings.append(
                f"- Possible removed/risky BaseType: `{risky}` on lines {', '.join(map(str, base_locations[risky]))}."
            )

    if risky_warnings:
        warnings.append("### Risky Names")
        warnings.append("")
        warnings.extend(risky_warnings)
        warnings.append("")

    ordering_warnings = []
    if "Hivebrain Gland" in base_locations and "Map Fragments" in class_locations:
        first_hive = min(base_locations["Hivebrain Gland"])
        first_frag = min(class_locations["Map Fragments"])
        if first_frag < first_hive:
            ordering_warnings.append(
                "- `Class \"Map Fragments\"` appears before `BaseType \"Hivebrain Gland\"`. "
                "The generic rule may catch Hivebrain before the specific rule."
            )

    generic_classes = ["Stackable Currency", "Map Fragments", "Scarabs", "Divination Card", "Divination Cards", "Maps"]
    for generic in generic_classes:
        if generic in class_locations:
            first = min(class_locations[generic])
            if first < 80:
                ordering_warnings.append(
                    f"- Generic `Class \"{generic}\"` appears early on line {first}. "
                    "Check that it does not shadow later specific rules."
                )

    for idx, line in enumerate(lines, start=1):
        if BASE_TYPE_RE.search(line) and '"' not in line:
            ordering_warnings.append(f"- Line {idx}: `BaseType` without quoted names: `{line.strip()}`")

    if ordering_warnings:
        warnings.append("### Ordering / Syntax")
        warnings.append("")
        warnings.extend(ordering_warnings)
        warnings.append("")

    return warnings


def main() -> int:
    config = load_json(CONFIG_FILE)
    filter_files = find_filter_files()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Auditoria do filtro")
    lines.append("")
    lines.append("Este relatorio aponta riscos estruturais. Ele nao substitui o teste dentro do jogo.")
    lines.append("")

    if not filter_files:
        lines.append("_Nenhum arquivo `.filter` encontrado em `filters/current/` ou na raiz do repositorio._")
        REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
        print(f"Auditoria salva em: {REPORT_FILE.relative_to(ROOT)}")
        return 0

    for filter_file in filter_files:
        lines.append(f"## `{display_path(filter_file)}`")
        lines.append("")
        warnings = audit_filter(filter_file, config)

        if warnings:
            lines.extend(warnings)
        else:
            lines.append("_Nenhum risco obvio encontrado._")

        lines.append("")

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Auditoria salva em: {REPORT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
