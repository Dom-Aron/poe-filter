#!/usr/bin/env python3
"""
oauth_refresh.py

Refreshes Path of Exile OAuth tokens using the refresh_token grant.

This is meant for the approved OAuth client flow described in
config/oauth_config.json. It never asks for your Path of Exile password.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import oauth_login


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "oauth_config.json"
DEFAULT_TOKEN_FILE = ROOT / "secrets" / "tokens.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def refresh_token(config_path: Path, token_file: Path, timeout: int = 30) -> dict[str, Any]:
    config = load_json(config_path)
    current = load_json(token_file)
    client_id = str(config.get("client_id") or current.get("client_id") or "").strip()
    token_url = str(config.get("token_url") or "https://www.pathofexile.com/oauth/token")
    refresh = str(current.get("refresh_token") or "").strip()
    scope = str(config.get("scope") or current.get("scope_requested") or current.get("scope") or "account:characters")

    if not client_id or client_id.startswith("SEU_CLIENT_ID"):
        raise SystemExit(f"Configure a real client_id in {config_path} first.")
    if not refresh:
        raise SystemExit(f"No refresh_token found in {token_file}. Run oauth_login.py again.")

    payload = urlencode(
        {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        }
    ).encode("utf-8")
    request = Request(
        token_url,
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": oauth_login.user_agent(),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            refreshed = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Token refresh failed: HTTP {exc.code}: {detail[:1000]}") from exc
    except (URLError, TimeoutError) as exc:
        raise SystemExit(f"Token refresh network error: {exc}") from exc

    if "refresh_token" not in refreshed and refresh:
        refreshed["refresh_token"] = refresh
    enriched = oauth_login.enrich_token_metadata(refreshed, client_id, scope)
    save_json(token_file, enriched)
    return enriched


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh Path of Exile OAuth tokens.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    data = refresh_token(args.config, args.token_file, args.timeout)
    expires_at = data.get("expires_at")
    if isinstance(expires_at, (int, float)):
        print(f"Refreshed OAuth token. Expires at unix time: {int(expires_at)}")
    else:
        print("Refreshed OAuth token.")
    print(f"Saved OAuth tokens: {args.token_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
