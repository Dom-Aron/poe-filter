#!/usr/bin/env python3
"""CLI wrapper for core.validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLKIT_ROOT))

from core.io import write_json
from core.validation import validate_character


def print_report(data: dict) -> None:
    print(f"Validation: {data['status']} | character={data.get('character_slug')} | build={data.get('build_slug') or 'n/d'}")
    for label in ("errors", "warnings", "suggestions"):
        values = data.get(label, [])
        if values:
            print(label + ":")
            for value in values:
                print(f"- {value}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a saved character/build profile for the no-OAuth workflow.")
    parser.add_argument("--character", required=True, help="Saved character slug.")
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    data = validate_character(args.character, strict=args.strict)
    if args.output:
        write_json(args.output, data)
    if not args.quiet:
        print_report(data)
    return 0 if data["status"] != "failed" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
