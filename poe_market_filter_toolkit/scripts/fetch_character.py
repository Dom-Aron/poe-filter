#!/usr/bin/env python3
"""
fetch_character.py

Fetches the authenticated player's character from the official Path of Exile
API and saves the raw response for later parsing.

Authentication:
    - preferred: POE_OAUTH_TOKEN environment variable
    - fallback: secrets/tokens.json with {"access_token": "..."}

Config:
    config/account_config.json, based on config/account_config.example.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACCOUNT_CONFIG = ROOT / "config" / "account_config.json"
DEFAULT_MARKET_CONFIG = ROOT / "config" / "market_config.json"
DEFAULT_OAUTH_CONFIG = ROOT / "config" / "oauth_config.json"
DEFAULT_TOKEN_FILE = ROOT / "secrets" / "tokens.json"
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "character_api_raw.json"
API_BASE = "https://api.pathofexile.com"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_access_token(token_file: Path, oauth_config: Path, refresh_margin_seconds: int) -> str:
    env_token = os.environ.get("POE_OAUTH_TOKEN", "").strip()
    if env_token:
        return env_token
    data = load_json(token_file)
    expires_at = data.get("expires_at")
    if isinstance(expires_at, (int, float)) and data.get("refresh_token"):
        if float(expires_at) <= time.time() + refresh_margin_seconds:
            try:
                import oauth_refresh
            except ImportError as exc:
                raise SystemExit(f"Could not import oauth_refresh.py: {exc}") from exc
            print("OAuth access token is expired or close to expiring; refreshing it.")
            data = oauth_refresh.refresh_token(oauth_config, token_file)
    token = str(data.get("access_token") or data.get("token") or "").strip()
    if token:
        return token
    raise SystemExit(
        "OAuth token not found. Set POE_OAUTH_TOKEN or create "
        f"{token_file} with {{\"access_token\": \"...\"}}."
    )


def user_agent() -> str:
    market_config = load_json(DEFAULT_MARKET_CONFIG)
    return market_config.get("user_agent", "poe-market-filter-toolkit/1.0 (+personal loot filter project)")


def request_json(url: str, token: str, timeout: int) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": user_agent(),
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} while fetching character: {detail[:1000]}") from exc
    except (URLError, TimeoutError) as exc:
        raise SystemExit(f"Network error while fetching character: {exc}") from exc


def character_url(realm: str, name: str) -> str:
    realm = realm.strip().lower()
    encoded_name = quote(name, safe="")
    if realm:
        return f"{API_BASE}/character/{quote(realm, safe='')}/{encoded_name}"
    return f"{API_BASE}/character/{encoded_name}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch the authenticated Path of Exile character.")
    parser.add_argument("--config", type=Path, default=DEFAULT_ACCOUNT_CONFIG)
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--oauth-config", type=Path, default=DEFAULT_OAUTH_CONFIG)
    parser.add_argument("--character-name", help="Override config character_name.")
    parser.add_argument("--realm", help="Override config realm, usually pc.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--refresh-margin-seconds", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = load_json(args.config)
    character_name = args.character_name or config.get("character_name")
    realm = args.realm if args.realm is not None else config.get("realm", "pc")

    if not character_name:
        raise SystemExit(
            "character_name is required. Create config/account_config.json from "
            "config/account_config.example.json or pass --character-name."
        )

    oauth_config_data = load_json(args.oauth_config)
    refresh_margin = args.refresh_margin_seconds
    if refresh_margin is None:
        refresh_margin = int(oauth_config_data.get("token_refresh_margin_seconds", 300))
    token = load_access_token(args.token_file, args.oauth_config, refresh_margin)
    url = character_url(str(realm or ""), str(character_name))
    data = request_json(url, token, args.timeout)

    wrapped = {
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": url,
        "realm": realm,
        "character_name": character_name,
        "data": data,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(wrapped, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved raw character data: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
