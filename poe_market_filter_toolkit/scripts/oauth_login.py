#!/usr/bin/env python3
"""
oauth_login.py

Runs the OAuth Authorization Code + PKCE flow for a Path of Exile public
desktop client. It opens the official authorization page, waits for the local
callback, exchanges the code for tokens, and writes secrets/tokens.json.

Prerequisite:
    config/oauth_config.json, copied from config/oauth_config.example.json
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import secrets
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "oauth_config.json"
DEFAULT_TOKEN_FILE = ROOT / "secrets" / "tokens.json"
DEFAULT_MARKET_CONFIG = ROOT / "config" / "market_config.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def make_code_verifier() -> str:
    return base64url(secrets.token_bytes(64))


def make_code_challenge(verifier: str) -> str:
    return base64url(hashlib.sha256(verifier.encode("ascii")).digest())


def user_agent() -> str:
    market_config = load_json(DEFAULT_MARKET_CONFIG)
    return market_config.get("user_agent", "OAuth poe-market-filter-toolkit/1.0 (contact: personal-use)")


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    server_version = "PoEOAuthCallback/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        self.server.auth_result = {key: values[0] for key, values in query.items()}  # type: ignore[attr-defined]
        if "code" in query:
            body = b"Path of Exile OAuth complete. You can close this tab."
            self.send_response(200)
        else:
            body = b"Path of Exile OAuth failed. Check the terminal."
            self.send_response(400)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def wait_for_callback(redirect_uri: str, timeout: int) -> dict[str, str]:
    parsed = urlparse(redirect_uri)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise SystemExit("This helper only supports local redirect URIs like http://127.0.0.1:8080/callback.")
    port = parsed.port or 80
    server = http.server.HTTPServer((parsed.hostname or "127.0.0.1", port), CallbackHandler)
    server.auth_result = {}  # type: ignore[attr-defined]

    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    thread.join(timeout)
    server.server_close()
    result = getattr(server, "auth_result", {})
    if not result:
        raise SystemExit("Timed out waiting for OAuth callback.")
    return result


def exchange_code(
    token_url: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    code: str,
    code_verifier: str,
    timeout: int,
) -> dict[str, Any]:
    payload = urlencode(
        {
            "client_id": client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "code_verifier": code_verifier,
        }
    ).encode("utf-8")
    request = Request(
        token_url,
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": user_agent(),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Token exchange failed: HTTP {exc.code}: {detail[:1000]}") from exc
    except (URLError, TimeoutError) as exc:
        raise SystemExit(f"Token exchange network error: {exc}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Authorize Path of Exile OAuth and save tokens.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--print-url", action="store_true", help="Print URL instead of opening the browser automatically.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = load_json(args.config)
    client_id = str(config.get("client_id") or "").strip()
    redirect_uri = str(config.get("redirect_uri") or "http://127.0.0.1:8080/callback").strip()
    scope = str(config.get("scope") or "account:characters").strip()
    authorization_url = str(config.get("authorization_url") or "https://www.pathofexile.com/oauth/authorize")
    token_url = str(config.get("token_url") or "https://www.pathofexile.com/oauth/token")

    if not client_id or client_id.startswith("SEU_CLIENT_ID"):
        raise SystemExit(f"Configure a real client_id in {args.config} first.")

    state = base64url(secrets.token_bytes(24))
    verifier = make_code_verifier()
    challenge = make_code_challenge(verifier)
    auth_url = authorization_url + "?" + urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )

    print("Open this official Path of Exile authorization URL:")
    print(auth_url)
    if not args.print_url:
        webbrowser.open(auth_url)

    result = wait_for_callback(redirect_uri, args.timeout)
    if result.get("state") != state:
        raise SystemExit("OAuth state mismatch. Refusing to save token.")
    if "error" in result:
        raise SystemExit(f"OAuth authorization failed: {result.get('error')} {result.get('error_description', '')}")
    code = result.get("code")
    if not code:
        raise SystemExit("OAuth callback did not include a code.")

    token_data = exchange_code(token_url, client_id, redirect_uri, scope, code, verifier, args.timeout)
    token_data["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    token_data["client_id"] = client_id
    token_data["scope_requested"] = scope
    save_json(args.token_file, token_data)
    print(f"Saved OAuth tokens: {args.token_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
