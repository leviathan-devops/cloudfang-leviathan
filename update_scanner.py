#!/usr/bin/env python3
"""
OpenFang Update Scanner Bot v1.0
================================
Monitors GitHub releases for RightNow-AI/openfang and notifies Discord.
NEVER auto-updates — notification only.

Runs as a background daemon alongside OpenFang.
Health endpoint on port 4202.

Author: Leviathan DevOps (External Claude)
Date: 2026-03-01
"""

import os
import sys
import logging
import time
import threading
import json
import re
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
CURRENT_VERSION = os.environ.get("CURRENT_VERSION", "v0.2.3")
GITHUB_API_URL = os.environ.get(
    "GITHUB_API_URL",
    "https://api.github.com/repos/RightNow-AI/openfang/releases/latest",
)
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL_SECONDS", "86400"))  # 24 hours
HEALTH_PORT = int(os.environ.get("SCANNER_HEALTH_PORT", "4202"))
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Discord notification targets
CHANGELOG_CHANNEL = os.environ.get("DISCORD_CHANGELOG_CHANNEL", "1476157102568243353")
DM_CHANNEL = os.environ.get("DISCORD_DM_CHANNEL", "1477514771187109981")

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCANNER] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("update_scanner")


def load_discord_token() -> str:
    """Load Discord bot token from file or env."""
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        try:
            with open("/tmp/DISCORD_BOT_TOKEN", "r") as f:
                token = f.read().strip()
        except FileNotFoundError:
            pass
    return token


def parse_version(version_str: str) -> tuple:
    """Parse version string into comparable tuple. e.g. 'v0.2.3' -> (0, 2, 3)"""
    clean = version_str.lstrip("v").split("-")[0]  # strip v prefix and pre-release
    parts = clean.split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return (0, 0, 0)


def fetch_latest_release() -> dict | None:
    """Fetch latest release from GitHub API. Returns release info or None."""
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "Leviathan-Scanner/1.0"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    for attempt in range(3):
        try:
            req = Request(GITHUB_API_URL, headers=headers)
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return {
                    "tag": data.get("tag_name", ""),
                    "name": data.get("name", ""),
                    "url": data.get("html_url", ""),
                    "published": data.get("published_at", ""),
                    "prerelease": data.get("prerelease", False),
                    "body": (data.get("body", "") or "")[:500],
                }
        except HTTPError as e:
            if e.code == 404:
                log.info("No releases found (404)")
                return None
            if e.code == 403:
                log.warning(f"GitHub rate limited (403). Attempt {attempt+1}/3")
                time.sleep(60 * (attempt + 1))
                continue
            log.error(f"GitHub API error {e.code}: {e.reason}")
        except URLError as e:
            log.error(f"Network error: {e.reason}. Attempt {attempt+1}/3")
        except Exception as e:
            log.error(f"Unexpected error: {e}. Attempt {attempt+1}/3")

        time.sleep(5 * (attempt + 1))  # Backoff

    return None


def send_discord_message(channel_id: str, content: str, token: str) -> bool:
    """Send a message to a Discord channel via REST API."""
    if not token:
        log.warning("No Discord token — cannot send notification")
        return False

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    payload = json.dumps({"content": content}).encode()
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://openfang.dev, 1.0)",
    }

    try:
        req = Request(url, data=payload, headers=headers, method="POST")
        with urlopen(req, timeout=30) as resp:
            if resp.status in (200, 201, 204):
                log.info(f"Notification sent to channel {channel_id}")
                return True
            log.error(f"Discord API returned {resp.status}")
    except Exception as e:
        log.error(f"Discord notification failed: {e}")

    return False


# ──────────────────────────────────────────────
# Scanner State
# ──────────────────────────────────────────────
state = {
    "current_version": CURRENT_VERSION,
    "latest_version": None,
    "last_check": None,
    "last_notification": None,
    "checks": 0,
    "errors": 0,
    "started_at": None,
    "update_available": False,
}


def run_scan():
    """Run a single scan cycle."""
    log.info(f"Scanning for updates (current: {CURRENT_VERSION})...")
    state["checks"] += 1

    release = fetch_latest_release()
    if not release:
        state["errors"] += 1
        log.warning("Failed to fetch latest release")
        return

    latest_tag = release["tag"]
    state["latest_version"] = latest_tag
    state["last_check"] = datetime.now(timezone.utc).isoformat()

    current = parse_version(CURRENT_VERSION)
    latest = parse_version(latest_tag)

    if latest > current:
        state["update_available"] = True
        log.info(f"UPDATE AVAILABLE: {CURRENT_VERSION} → {latest_tag}")

        # Only notify once per version
        if state.get("last_notified_version") != latest_tag:
            token = load_discord_token()
            msg = (
                f"**OpenFang Update Available**\n"
                f"Current: `{CURRENT_VERSION}` → Latest: `{latest_tag}`\n"
                f"{'⚠️ PRE-RELEASE' if release['prerelease'] else '✅ Stable Release'}\n"
                f"Release: {release['url']}\n"
                f"Published: {release['published']}\n"
                f"---\n"
                f"**Action Required**: Review changelog and deploy manually.\n"
                f"**NEVER auto-update** — the Tier 4 Lizard Brain is sacred."
            )

            # Notify #change-log
            send_discord_message(CHANGELOG_CHANNEL, msg, token)
            # DM Owner
            send_discord_message(DM_CHANNEL, f"🔔 OpenFang {latest_tag} available (you're on {CURRENT_VERSION}). Check #change-log.", token)

            state["last_notification"] = datetime.now(timezone.utc).isoformat()
            state["last_notified_version"] = latest_tag
    else:
        state["update_available"] = False
        log.info(f"Up to date: {CURRENT_VERSION} (latest: {latest_tag})")


# ──────────────────────────────────────────────
# Health Endpoint
# ──────────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/health", "/", "/metrics"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "service": "update_scanner",
                "version": "1.0.0",
                **state,
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("OpenFang Update Scanner v1.0 starting")
    log.info(f"  Current version: {CURRENT_VERSION}")
    log.info(f"  Scan interval: {SCAN_INTERVAL}s ({SCAN_INTERVAL // 3600}h)")
    log.info(f"  Health port: {HEALTH_PORT}")
    log.info("=" * 60)

    state["started_at"] = datetime.now(timezone.utc).isoformat()

    # Start health endpoint
    try:
        server = HTTPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
        health_thread = threading.Thread(target=server.serve_forever, daemon=True)
        health_thread.start()
        log.info(f"Health endpoint on port {HEALTH_PORT}")
    except OSError as e:
        log.warning(f"Health endpoint failed: {e}")

    # Initial scan after 60s delay (let OpenFang boot first)
    time.sleep(60)
    run_scan()

    # Main loop
    while True:
        try:
            time.sleep(SCAN_INTERVAL)
            run_scan()
        except KeyboardInterrupt:
            log.info("Shutdown")
            break
        except Exception as e:
            log.error(f"Scan error: {e}", exc_info=True)
            state["errors"] += 1
            time.sleep(300)  # Wait 5 min on error


if __name__ == "__main__":
    main()
