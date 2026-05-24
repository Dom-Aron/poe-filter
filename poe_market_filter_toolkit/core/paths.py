"""Shared filesystem paths for scripts and core modules."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
BUILDS = ROOT / "builds"
CHARACTERS = BUILDS / "characters"
PROFILES = BUILDS / "profiles"
GENERATED = ROOT / "data" / "generated"
CHARACTER_OUTPUT = GENERATED / "characters"
REPORTS = ROOT / "market" / "reports"
MARKET = ROOT / "market"
SCRIPTS = ROOT / "scripts"


def character_dir(slug: str) -> Path:
    return CHARACTERS / slug


def build_dir(slug: str) -> Path:
    return PROFILES / slug


def character_output_dir(slug: str) -> Path:
    return CHARACTER_OUTPUT / slug


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)
