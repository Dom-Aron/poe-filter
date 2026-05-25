#!/usr/bin/env python3
"""
update_market.py

Fetches Path of Exile 1 market prices from poe.ninja and saves:
- market/latest_market.json
- market/snapshots/market_YYYY-MM-DD_HHMMSS.json

Usage:
    python scripts/update_market.py
    python scripts/update_market.py --league Mirage
    python scripts/update_market.py --config config/market_config.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.time_utils import utc_now_iso

DEFAULT_CONFIG = ROOT / "config" / "market_config.json"
SNAPSHOT_DIR = ROOT / "market" / "snapshots"
LATEST_FILE = ROOT / "market" / "latest_market.json"


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_exchange_url(league: str, category: str) -> str:
    query = urlencode({"league": league, "type": category})
    return f"https://poe.ninja/poe1/api/economy/exchange/current/overview?{query}"


def build_stash_url(league: str, category: str) -> str:
    query = urlencode({"league": league, "type": category})
    return f"https://poe.ninja/poe1/api/economy/stash/current/item/overview?{query}"


def fetch_json(url: str, user_agent: str, timeout: int, retries: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        request = Request(url, headers={"User-Agent": user_agent})

        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))

        except HTTPError as exc:
            last_error = exc
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 10 * attempt
                print(f"[rate limit] waiting {wait_seconds}s before retrying...")
                time.sleep(wait_seconds)
                continue
            raise

        except (URLError, TimeoutError) as exc:
            last_error = exc
            wait_seconds = 3 * attempt
            print(f"[network] attempt {attempt}/{retries} failed: {exc}. Retrying in {wait_seconds}s.")
            time.sleep(wait_seconds)

    raise RuntimeError(f"Failed to fetch URL after {retries} attempts: {url}") from last_error


def normalize_exchange(category: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    metadata_by_id = {
        str(item.get("id")): item
        for item in data.get("items", [])
        if item.get("id") is not None
    }
    items: list[dict[str, Any]] = []

    for line in data.get("lines", []):
        item_id = str(line.get("id", ""))
        metadata = metadata_by_id.get(item_id, {})
        name = metadata.get("name")
        chaos_value = line.get("primaryValue")

        if not name or chaos_value is None:
            continue

        items.append({
            "name": name,
            "category": metadata.get("category") or category,
            "chaos_value": float(chaos_value),
            "divine_value": None,
            "listing_count": line.get("volumePrimaryValue"),
            "details_id": metadata.get("detailsId") or item_id,
            "source": "poe.ninja",
            "source_endpoint": "exchange",
            "requested_category": category,
            "max_volume_currency": line.get("maxVolumeCurrency"),
            "max_volume_rate": line.get("maxVolumeRate"),
            "change_percent": (line.get("sparkline") or {}).get("totalChange"),
        })

    return items


def normalize_stash(category: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for line in data.get("lines", []):
        name = line.get("name")
        chaos_value = line.get("chaosValue")

        if not name or chaos_value is None:
            continue

        items.append({
            "name": name,
            "category": category,
            "chaos_value": float(chaos_value),
            "divine_value": line.get("divineValue"),
            "listing_count": line.get("listingCount"),
            "details_id": line.get("detailsId"),
            "source": "poe.ninja",
            "source_endpoint": "stash",
            "requested_category": category,
            "base_type": line.get("baseType"),
            "variant": line.get("variant"),
            "change_percent": (line.get("sparkLine") or {}).get("totalChange"),
        })

    return items


def configured_categories(config: dict[str, Any]) -> tuple[list[str], list[str]]:
    categories = config.get("categories", {})
    exchange = categories.get("exchange")
    stash = categories.get("stash")

    if exchange is not None or stash is not None:
        return list(exchange or []), list(stash or [])

    old_currency = categories.get("currency", [])
    old_items = categories.get("items", [])
    stash_types = {"Map", "UniqueMap", "SkillGem", "ClusterJewel", "Invitation", "Memory", "Beast"}

    exchange_categories = list(old_currency)
    stash_categories: list[str] = []

    for category in old_items:
        if category in stash_types:
            stash_categories.append(category)
        else:
            exchange_categories.append(category)

    return exchange_categories, stash_categories


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}

    for item in items:
        key = (
            str(item.get("source_endpoint", "")),
            str(item.get("requested_category", "")),
            str(item.get("category", "")),
            str(item.get("name", "")),
            str(item.get("variant", "")),
            str(item.get("details_id", "")),
        )
        current = by_key.get(key)
        item_value = float(item.get("chaos_value", 0) or 0)
        current_value = float(current.get("chaos_value", 0) or 0) if current else -1

        if current is None or item_value > current_value:
            by_key[key] = item

    return sorted(
        by_key.values(),
        key=lambda item: (-float(item.get("chaos_value", 0) or 0), str(item.get("category", "")), str(item.get("name", ""))),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Update a Path of Exile market snapshot using poe.ninja.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to market_config.json.")
    parser.add_argument("--league", default=None, help="Override the league from the config.")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)

    league = args.league or config.get("league", "Standard")
    delay = float(config.get("request_delay_seconds", 0.7))
    timeout = int(config.get("timeout_seconds", 30))
    user_agent = str(config.get("user_agent", "poe-market-filter-toolkit/1.0"))
    exchange_categories, stash_categories = configured_categories(config)

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    snapshot: dict[str, Any] = {
        "league": league,
        "generated_at": utc_now_iso(),
        "generated_by": "scripts/update_market.py",
        "items": [],
        "errors": [],
    }

    collected_items: list[dict[str, Any]] = []

    print(f"Updating market for league: {league}")

    for category in exchange_categories:
        try:
            print(f"Fetching exchange: {category}")
            data = fetch_json(build_exchange_url(league, category), user_agent, timeout)
            collected_items.extend(normalize_exchange(category, data))
            time.sleep(delay)
        except Exception as exc:
            snapshot["errors"].append({"category": category, "kind": "exchange", "error": str(exc)})

    for category in stash_categories:
        try:
            print(f"Fetching stash: {category}")
            data = fetch_json(build_stash_url(league, category), user_agent, timeout)
            collected_items.extend(normalize_stash(category, data))
            time.sleep(delay)
        except Exception as exc:
            snapshot["errors"].append({"category": category, "kind": "stash", "error": str(exc)})

    snapshot["items"] = dedupe_items(collected_items)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    snapshot_file = SNAPSHOT_DIR / f"market_{timestamp}.json"

    text = json.dumps(snapshot, ensure_ascii=False, indent=2)
    snapshot_file.write_text(text, encoding="utf-8")
    LATEST_FILE.write_text(text, encoding="utf-8")

    print()
    print(f"Snapshot saved to: {snapshot_file.relative_to(ROOT)}")
    print(f"Latest market saved to: {LATEST_FILE.relative_to(ROOT)}")
    print(f"Items collected: {len(snapshot['items'])}")
    print(f"Errors: {len(snapshot['errors'])}")

    if snapshot["errors"]:
        print()
        print("Categories with errors:")
        for error in snapshot["errors"]:
            print(f"- {error['category']} ({error['kind']}): {error['error']}")

    if not snapshot["items"]:
        print()
        print("No items were collected. Check the league name and poe.ninja endpoints.")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
