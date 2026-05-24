"""Small JSON and file helpers shared by toolkit scripts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return {} if default is None else dict(default)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else ({} if default is None else dict(default))


def read_json_checked(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"arquivo ausente: {path}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"JSON invalido em {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"JSON raiz precisa ser objeto: {path}")
        return {}
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def required_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise SystemExit(f"Missing {label}: {path}")
    return path
