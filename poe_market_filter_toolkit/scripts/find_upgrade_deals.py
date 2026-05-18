#!/usr/bin/env python3
"""
find_upgrade_deals.py

Searches the official Path of Exile trade API for budget upgrades for the
Ronarray Shockwave Cyclone / General's Cry Slayer setup documented in this repo.

Usage:
    python poe_market_filter_toolkit/scripts/find_upgrade_deals.py --budget 251c
    python poe_market_filter_toolkit/scripts/find_upgrade_deals.py --budget 1d --profiles ring_vulnerability,jewel_damage
    python poe_market_filter_toolkit/scripts/find_upgrade_deals.py --budget 250c --top 8

Notes:
    - Uses the public trade endpoints used by the official trade site.
    - Keeps searches small and slow to respect rate limits.
    - Scores are heuristics. Always inspect the item in trade/PoE Overlay before buying.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
DEFAULT_CONFIG = ROOT / "config" / "market_config.json"
LATEST_MARKET = ROOT / "market" / "latest_market.json"
REPORT_FILE = ROOT / "market" / "reports" / "upgrade_deals.md"
STATS_CACHE = ROOT / "market" / "trade_stats_cache.json"

TRADE_BASE = "https://www.pathofexile.com"


@dataclass(frozen=True)
class Weight:
    contains: str
    points: float = 0.0
    per_value: float = 0.0
    cap: float | None = None


@dataclass(frozen=True)
class Profile:
    key: str
    label: str
    why: str
    query: dict[str, Any]
    required_stat_texts: tuple[str, ...]
    weights: tuple[Weight, ...]
    count_stat_texts: tuple[str, ...] = ()
    count_min: int = 0
    base_score: float = 0.0
    min_score: float = 0.0


def load_config(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "league": "Mirage",
        "request_delay_seconds": 0.9,
        "timeout_seconds": 30,
        "user_agent": "poe-market-filter-toolkit/1.0 (+personal loot filter project)",
    }


def request_json(
    url: str,
    user_agent: str,
    timeout: int,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    retries: int = 3,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            last_error = exc
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 8 * attempt
                print(f"[rate limit] waiting {wait_seconds}s before retrying {url}")
                time.sleep(wait_seconds)
                continue
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} for {url}: {detail[:800]}") from exc
        except (URLError, TimeoutError) as exc:
            last_error = exc
            wait_seconds = 3 * attempt
            print(f"[network] attempt {attempt}/{retries} failed: {exc}. Retrying in {wait_seconds}s.")
            time.sleep(wait_seconds)

    raise RuntimeError(f"Failed to request {url}") from last_error


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def get_trade_stats(user_agent: str, timeout: int, max_age_hours: int = 24) -> list[dict[str, str]]:
    if STATS_CACHE.exists():
        age_seconds = time.time() - STATS_CACHE.stat().st_mtime
        if age_seconds < max_age_hours * 3600:
            return json.loads(STATS_CACHE.read_text(encoding="utf-8"))

    data = request_json(f"{TRADE_BASE}/api/trade/data/stats", user_agent, timeout)
    stats: list[dict[str, str]] = []
    for section in data.get("result", []):
        for entry in section.get("entries", []):
            if entry.get("id") and entry.get("text"):
                stats.append(
                    {
                        "id": entry["id"],
                        "text": entry["text"],
                        "type": entry.get("type", ""),
                    }
                )

    STATS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    STATS_CACHE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


def stat_ids_for_text(stats: list[dict[str, str]], text: str) -> list[str]:
    target = normalize_text(text)
    exact = [entry["id"] for entry in stats if normalize_text(entry["text"]) == target]
    if exact:
        return exact
    loose = [entry["id"] for entry in stats if target in normalize_text(entry["text"])]
    return loose


def preferred_stat_id(stats: list[dict[str, str]], ids: list[str]) -> str:
    by_id = {entry["id"]: entry for entry in stats}
    for stat_type in ("explicit", "implicit", "pseudo", "enchant"):
        for stat_id in ids:
            if by_id.get(stat_id, {}).get("type") == stat_type:
                return stat_id
    return ids[0]


def parse_budget(raw: str, divine_price_chaos: float) -> float:
    value = raw.strip().lower().replace(" ", "")
    match = re.fullmatch(r"([0-9]+(?:[.,][0-9]+)?)(c|chaos|d|div|divine|divines)?", value)
    if not match:
        raise ValueError("Budget must look like 250c, 1d, 1.5div or 250.")

    amount = float(match.group(1).replace(",", "."))
    unit = match.group(2) or "chaos"
    if unit in {"c", "chaos"}:
        return amount
    if unit in {"d", "div", "divine", "divines"}:
        return amount * divine_price_chaos
    raise ValueError(f"Unsupported budget unit: {unit}")


def load_divine_price_chaos(default: float = 490.0) -> float:
    if not LATEST_MARKET.exists():
        return default
    data = json.loads(LATEST_MARKET.read_text(encoding="utf-8"))
    for item in data.get("items", []):
        if item.get("name") == "Divine Orb" and item.get("chaos_value"):
            return float(item["chaos_value"])
    return default


def price_to_chaos(price: dict[str, Any] | None, divine_price: float) -> float | None:
    if not price:
        return None
    amount = price.get("amount")
    currency = str(price.get("currency", "")).lower()
    if amount is None:
        return None
    amount = float(amount)
    conversions = {
        "chaos": 1.0,
        "divine": divine_price,
        "exalted": 3.2,
    }
    return amount * conversions.get(currency, math.inf)


def make_price_filter(max_chaos: float) -> dict[str, Any]:
    return {
        "trade_filters": {
            "filters": {
                "price": {"max": round(max_chaos, 2), "option": "chaos"},
                "sale_type": {"option": "priced"},
            }
        }
    }


def merge_filters(*groups: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for group in groups:
        for section, section_value in group.items():
            target = merged.setdefault(section, {"filters": {}})
            target["filters"].update(section_value.get("filters", {}))
    return merged


def with_required_stats(
    query: dict[str, Any],
    stats: list[dict[str, str]],
    required_texts: tuple[str, ...],
    count_texts: tuple[str, ...],
    count_min: int,
) -> dict[str, Any]:
    query = json.loads(json.dumps(query))
    stat_groups = query.setdefault("stats", [])
    for text in required_texts:
        ids = stat_ids_for_text(stats, text)
        if not ids:
            raise RuntimeError(f"No trade stat id found for: {text}")
        stat_groups.append({"type": "and", "filters": [{"id": preferred_stat_id(stats, ids)}]})
    if count_texts and count_min:
        filters = []
        for text in count_texts:
            ids = stat_ids_for_text(stats, text)
            if ids:
                filters.append({"id": preferred_stat_id(stats, ids)})
        if filters:
            stat_groups.append({"type": "count", "value": {"min": count_min}, "filters": filters})
    return query


def make_profiles() -> dict[str, Profile]:
    return {
        "ring_vulnerability": Profile(
            key="ring_vulnerability",
            label="Anel com Vulnerability on Hit",
            why="Maior chance de upgrade ofensivo real se mantiver vida/resistência/mana.",
            required_stat_texts=("Curse Enemies with Vulnerability on Hit",),
            query={
                "status": {"option": "online"},
                "filters": {
                    "type_filters": {
                        "filters": {
                            "category": {"option": "accessory.ring"},
                            "rarity": {"option": "rare"},
                        }
                    }
                },
            },
            weights=(
                Weight("Curse Enemies with Vulnerability on Hit", points=100),
                Weight("to maximum Life", per_value=0.45, cap=55),
                Weight("to Accuracy Rating", per_value=0.05, cap=35),
                Weight("Adds", points=12),
                Weight("Physical Damage to Attacks", points=22),
                Weight("increased Attack Speed", per_value=2.5, cap=35),
                Weight("to all Elemental Resistances", per_value=1.5, cap=35),
                Weight("to Fire Resistance", per_value=0.7, cap=25),
                Weight("to Cold Resistance", per_value=0.7, cap=25),
                Weight("to Lightning Resistance", per_value=0.5, cap=18),
                Weight("to Chaos Resistance", per_value=1.0, cap=25),
                Weight("Total Mana Cost", points=35),
            ),
            base_score=10,
            min_score=90,
        ),
        "jewel_damage": Profile(
            key="jewel_damage",
            label="Jewel raro para dano/vida/accuracy",
            why="Upgrade barato costuma ser melhor que trocar luvas boas por sidegrade.",
            required_stat_texts=(),
            count_stat_texts=(
                "#% increased maximum Life",
                "#% increased Attack Speed with Staves",
                "#% increased Physical Damage with Staves",
                "+#% to Global Critical Strike Multiplier",
                "+# to Accuracy Rating",
                "+#% to Chaos Resistance",
            ),
            count_min=2,
            query={
                "status": {"option": "online"},
                "filters": {
                    "type_filters": {
                        "filters": {
                            "category": {"option": "jewel.base"},
                            "rarity": {"option": "rare"},
                        }
                    }
                },
            },
            weights=(
                Weight("increased maximum Life", per_value=5.0, cap=40),
                Weight("Physical Damage with Staves", per_value=3.0, cap=36),
                Weight("Attack Speed with Staves", per_value=4.0, cap=40),
                Weight("Global Critical Strike Multiplier", per_value=2.5, cap=40),
                Weight("to Accuracy Rating", per_value=0.05, cap=30),
                Weight("increased Attack Speed", per_value=2.0, cap=30),
                Weight("to all Elemental Resistances", per_value=1.0, cap=25),
                Weight("to Chaos Resistance", per_value=1.0, cap=25),
            ),
            base_score=5,
            min_score=45,
        ),
        "abyss_jewel": Profile(
            key="abyss_jewel",
            label="Abyss jewel para Stygian Vise",
            why="Pode melhorar a jewel atual com vida, flat phys e utilidade sem mexer no resto do gear.",
            required_stat_texts=(),
            count_stat_texts=(
                "+# to maximum Life",
                "# to # Added Physical Damage with Staff Attacks",
                "#% increased Attack Speed if you've Killed Recently",
                "+# to Accuracy Rating",
                "+#% to Chaos Resistance",
            ),
            count_min=2,
            query={
                "status": {"option": "online"},
                "filters": {
                    "type_filters": {
                        "filters": {
                            "category": {"option": "jewel.abyss"},
                            "rarity": {"option": "rare"},
                        }
                    }
                },
            },
            weights=(
                Weight("to maximum Life", per_value=1.0, cap=45),
                Weight("Added Physical Damage with Staff Attacks", points=40),
                Weight("increased Attack Speed if you've Killed Recently", per_value=5.0, cap=40),
                Weight("to Accuracy Rating", per_value=0.05, cap=30),
                Weight("to Dexterity", per_value=0.5, cap=18),
                Weight("to Chaos Resistance", per_value=1.0, cap=25),
                Weight("Chance to Blind", points=25),
                Weight("Onslaught", points=30),
            ),
            base_score=5,
            min_score=45,
        ),
        "large_cluster": Profile(
            key="large_cluster",
            label="Large Cluster Jewel fisico/staff",
            why="Bom caminho para escalar dano fisico, Impale ou staff sem trocar bons rares.",
            required_stat_texts=(),
            query={
                "status": {"option": "online"},
                "type": "Large Cluster Jewel",
                "filters": {
                    "type_filters": {
                        "filters": {
                            "category": {"option": "jewel.cluster"},
                        }
                    }
                },
            },
            weights=(
                Weight("12% increased Physical Damage", points=45),
                Weight("12% increased Damage with Two Handed Weapons", points=35),
                Weight("Staff Attacks deal 12% increased Damage", points=55),
                Weight("8 Passive Skills", points=50),
                Weight("Impale", points=35),
                Weight("Fuel the Fight", points=30),
                Weight("Martial Prowess", points=28),
                Weight("Master the Fundamentals", points=25),
                Weight("Fire Damage", points=-40),
                Weight("Cold Damage", points=-30),
                Weight("Lightning Damage", points=-30),
                Weight("Minion", points=-35),
                Weight("Bow", points=-25),
            ),
            base_score=10,
            min_score=70,
        ),
        "rumi_uncorrupted": Profile(
            key="rumi_uncorrupted",
            label="Rumi's Concoction nao corrompido",
            why="Permite enchant/craft automatico de flask no futuro.",
            required_stat_texts=(),
            query={
                "status": {"option": "online"},
                "name": "Rumi's Concoction",
                "type": "Granite Flask",
                "filters": {
                    "type_filters": {
                        "filters": {
                            "rarity": {"option": "unique"},
                        }
                    },
                    "misc_filters": {
                        "filters": {
                            "corrupted": {"option": "false"},
                        }
                    },
                },
            },
            weights=(
                Weight("Chance to Block Attack Damage during Effect", per_value=4.0, cap=60),
                Weight("Chance to Block Spell Damage during Effect", per_value=7.0, cap=45),
                Weight("Quality", points=10),
            ),
            base_score=20,
            min_score=60,
        ),
    }


def extract_number_near(text: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text.replace(",", "."))
    if not match:
        return None
    return abs(float(match.group(0)))


def item_texts(item: dict[str, Any]) -> list[str]:
    fields = [
        "implicitMods",
        "explicitMods",
        "craftedMods",
        "fracturedMods",
        "enchantMods",
        "utilityMods",
        "scourgeMods",
    ]
    texts: list[str] = []
    for field in fields:
        value = item.get(field)
        if isinstance(value, list):
            texts.extend(str(line) for line in value)
    if item.get("name"):
        texts.append(str(item["name"]))
    if item.get("typeLine"):
        texts.append(str(item["typeLine"]))
    if item.get("baseType"):
        texts.append(str(item["baseType"]))
    return texts


def score_item(profile: Profile, item: dict[str, Any]) -> tuple[float, list[str]]:
    texts = item_texts(item)
    score = profile.base_score
    reasons: list[str] = []

    for weight in profile.weights:
        needle = weight.contains.lower()
        for text in texts:
            if needle in text.lower():
                gained = weight.points
                value = extract_number_near(text)
                if weight.per_value and value is not None:
                    gained += value * weight.per_value
                if weight.cap is not None:
                    gained = min(gained, weight.cap)
                if gained != 0:
                    score += gained
                if gained > 0:
                    reasons.append(text)
                break

    return score, reasons[:8]


def search_profile(
    profile: Profile,
    league: str,
    budget_chaos: float,
    stats: list[dict[str, str]],
    user_agent: str,
    timeout: int,
    max_fetch: int,
) -> tuple[str | None, list[str]]:
    query = with_required_stats(
        profile.query,
        stats,
        profile.required_stat_texts,
        profile.count_stat_texts,
        profile.count_min,
    )
    query["filters"] = merge_filters(query.get("filters", {}), make_price_filter(budget_chaos))
    payload = {"query": query, "sort": {"price": "asc"}}

    url = f"{TRADE_BASE}/api/trade/search/{league}"
    data = request_json(url, user_agent, timeout, method="POST", payload=payload)
    return data.get("id"), list(data.get("result", []))[:max_fetch]


def fetch_results(
    ids: list[str],
    query_id: str,
    user_agent: str,
    timeout: int,
    delay: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for start in range(0, len(ids), 10):
        chunk = ids[start : start + 10]
        if not chunk:
            continue
        query = urlencode({"query": query_id})
        url = f"{TRADE_BASE}/api/trade/fetch/{','.join(chunk)}?{query}"
        data = request_json(url, user_agent, timeout)
        results.extend(data.get("result", []))
        time.sleep(delay)
    return results


def evaluate_profile(
    profile: Profile,
    league: str,
    budget_chaos: float,
    divine_price: float,
    stats: list[dict[str, str]],
    user_agent: str,
    timeout: int,
    delay: float,
    max_fetch: int,
) -> list[dict[str, Any]]:
    query_id, ids = search_profile(profile, league, budget_chaos, stats, user_agent, timeout, max_fetch)
    if not query_id or not ids:
        return []
    time.sleep(delay)

    fetched = fetch_results(ids, query_id, user_agent, timeout, delay)
    evaluated: list[dict[str, Any]] = []
    trade_url = f"{TRADE_BASE}/trade/search/{league}/{query_id}"

    for entry in fetched:
        item = entry.get("item", {})
        listing = entry.get("listing", {})
        price = listing.get("price")
        price_chaos = price_to_chaos(price, divine_price)
        if price_chaos is None or not math.isfinite(price_chaos) or price_chaos > budget_chaos:
            continue

        score, reasons = score_item(profile, item)
        if score < profile.min_score:
            continue
        value_score = score / max(price_chaos, 1.0)
        evaluated.append(
            {
                "profile": profile.key,
                "profile_label": profile.label,
                "why": profile.why,
                "item_name": item.get("name") or "",
                "type_line": item.get("typeLine") or item.get("baseType") or "",
                "ilvl": item.get("ilvl"),
                "price": price,
                "price_chaos": price_chaos,
                "score": score,
                "value_score": value_score,
                "reasons": reasons,
                "seller": listing.get("account", {}).get("name", ""),
                "trade_url": trade_url,
                "whisper": listing.get("whisper", ""),
            }
        )

    evaluated.sort(key=lambda item: (item["value_score"], item["score"]), reverse=True)
    return evaluated


def format_price(price: dict[str, Any] | None, price_chaos: float) -> str:
    if not price:
        return f"{price_chaos:.1f}c"
    amount = price.get("amount")
    currency = price.get("currency")
    return f"{amount:g} {currency} (~{price_chaos:.1f}c)"


def write_report(
    profiles: list[Profile],
    rows_by_profile: dict[str, list[dict[str, Any]]],
    budget_chaos: float,
    league: str,
    top: int,
) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Upgrade Deals",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"League: `{league}`",
        f"Budget: `{budget_chaos:.1f} chaos`",
        "",
        "Heuristic score only. Confirm every item manually in trade/PoE Overlay before buying.",
        "",
    ]

    for profile in profiles:
        rows = rows_by_profile.get(profile.key, [])
        if rows:
            label = rows[0]["profile_label"]
            why = rows[0]["why"]
        else:
            label = profile.label
            why = profile.why
        lines.extend([f"## {label}", "", why, ""])
        if not rows:
            lines.extend(["No matching priced online listings within budget.", ""])
            continue
        lines.append("| Rank | Item | Price | Score | Value | Seller | Reasons |")
        lines.append("| ---: | --- | ---: | ---: | ---: | --- | --- |")
        for rank, row in enumerate(rows[:top], start=1):
            name = f"{row['item_name']} {row['type_line']}".strip()
            reasons = "<br>".join(row["reasons"]) if row["reasons"] else "base/profile match"
            lines.append(
                "| {rank} | [{name}]({url}) | {price} | {score:.1f} | {value:.2f} | {seller} | {reasons} |".format(
                    rank=rank,
                    name=name.replace("|", "\\|"),
                    url=row["trade_url"],
                    price=format_price(row["price"], row["price_chaos"]),
                    score=row["score"],
                    value=row["value_score"],
                    seller=str(row["seller"]).replace("|", "\\|"),
                    reasons=reasons.replace("|", "\\|"),
                )
            )
        lines.append("")

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


def print_summary(profiles: list[Profile], rows_by_profile: dict[str, list[dict[str, Any]]], top: int) -> None:
    for profile in profiles:
        rows = rows_by_profile.get(profile.key, [])
        print(f"\n== {rows[0]['profile_label'] if rows else profile.label} ==")
        if not rows:
            print("No matches.")
            continue
        for rank, row in enumerate(rows[:top], start=1):
            name = f"{row['item_name']} {row['type_line']}".strip()
            print(
                f"{rank}. {name} | {format_price(row['price'], row['price_chaos'])} "
                f"| score {row['score']:.1f} | value {row['value_score']:.2f}"
            )
            if row["reasons"]:
                print(f"   {', '.join(row['reasons'][:3])}")
            print(f"   {row['trade_url']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find budget upgrade deals on official Path of Exile trade.")
    parser.add_argument("--budget", required=True, help="Available budget, e.g. 251c, 1d, 1.5div.")
    parser.add_argument("--league", help="League name. Defaults to config/market_config.json.")
    parser.add_argument("--profiles", default="all", help="Comma list or all. Available: ring_vulnerability,jewel_damage,abyss_jewel,large_cluster,rumi_uncorrupted")
    parser.add_argument("--top", type=int, default=5, help="Rows per profile to print/save.")
    parser.add_argument("--max-fetch", type=int, default=25, help="Max listings fetched per profile.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    league = args.league or config.get("league", "Mirage")
    user_agent = config.get("user_agent", "poe-market-filter-toolkit/1.0 (+personal loot filter project)")
    timeout = int(config.get("timeout_seconds", 30))
    delay = float(config.get("request_delay_seconds", 0.9))
    divine_price = load_divine_price_chaos()
    budget_chaos = parse_budget(args.budget, divine_price)

    profiles = make_profiles()
    if args.profiles == "all":
        selected = list(profiles.values())
    else:
        keys = [key.strip() for key in args.profiles.split(",") if key.strip()]
        unknown = [key for key in keys if key not in profiles]
        if unknown:
            raise SystemExit(f"Unknown profiles: {', '.join(unknown)}")
        selected = [profiles[key] for key in keys]

    print(f"League: {league}")
    print(f"Budget: {budget_chaos:.1f} chaos (Divine ~= {divine_price:.1f}c)")
    print("Fetching trade stat metadata...")
    stats = get_trade_stats(user_agent, timeout)

    rows_by_profile: dict[str, list[dict[str, Any]]] = {}
    for profile in selected:
        print(f"\nSearching: {profile.label}")
        try:
            rows = evaluate_profile(
                profile=profile,
                league=league,
                budget_chaos=budget_chaos,
                divine_price=divine_price,
                stats=stats,
                user_agent=user_agent,
                timeout=timeout,
                delay=delay,
                max_fetch=args.max_fetch,
            )
        except Exception as exc:
            print(f"[warning] profile failed: {profile.key}: {exc}")
            rows = []
        rows_by_profile[profile.key] = rows
        time.sleep(delay)

    print_summary(selected, rows_by_profile, args.top)
    write_report(selected, rows_by_profile, budget_chaos, league, args.top)
    print(f"\nReport saved: {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
