# integrations/riot_api.py

import json
import logging
import os
import re
import urllib.parse
from typing import Optional

import aiohttp

from core.persistence import get_event_mode_for_guild

# === Constants ===
RIOT_API_REGION = "na1"
TFT_REGION = "americas"
TRACKER_API_KEY = os.getenv("TRACKER_API_KEY")
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}

_session: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"})
    return _session


def _remove_bidi_control_chars(s: str) -> str:
    """Strip Unicode isolate controls U+2066–U+2069."""
    return re.sub(r"[\u2066-\u2069]", "", s)


def build_tactics_tools_url(ign: str) -> str:
    clean = _remove_bidi_control_chars(ign)
    name, _, tag = clean.partition("#")
    name_enc = urllib.parse.quote(name.strip())
    path = f"/player/na/{name_enc}"
    if tag:
        path += f"/{urllib.parse.quote(tag.strip())}"
    return f"https://tactics.tools{path}"


async def tactics_tools_get_latest_placement(
        ign: str,
        guild_id: str
) -> Optional[int]:
    """
    Fetch the player's most recent TFT placement from any game mode
    in the latest set by scraping tactics.tools website.
    """
    url = build_tactics_tools_url(ign)
    print(f"[get_latest_placement] GET {url}")

    session = await _get_session()

    try:
        # Step 1: Fetch the page
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"[get_latest_placement] HTTP {resp.status}")
                return None
            html = await resp.text()

        # Step 2: Look for __NEXT_DATA__ JSON
        m = re.search(r'<script\s+id="__NEXT_DATA__"[^>]*>(?P<json>.+?)</script>',
                      html, flags=re.DOTALL)
        if not m:
            print("[get_latest_placement] no __NEXT_DATA__")
            return None

        try:
            data = json.loads(m.group("json"))
        except json.JSONDecodeError as e:
            print("[get_latest_placement] JSON parse error:", e)
            return None

        # Step 3: Navigate through the data structure
        try:
            page_props = data.get("props", {}).get("pageProps", {})
            if not page_props:
                print("[get_latest_placement] No pageProps found")
                return None

            # Get matches from initialData
            initial_data = page_props.get("initialData", {})
            matches = initial_data.get("matches", [])

            if not matches:
                print("[get_latest_placement] No matches found in initialData")
                return None

            # Filter for latest set only
            # Set 15 started around November 2024
            # We can check the game version or timestamp
            latest_set_matches = []

            for match in matches:
                info = match.get("info", {})
                game_version = info.get("gameVersion", "")

                # TFT Set 15 versions start with "Version 14.23" or higher
                # Format is usually "Version 14.23.xxx.xxxx"
                if game_version:
                    try:
                        # Extract major and minor version
                        version_parts = game_version.replace("Version ", "").split(".")
                        if len(version_parts) >= 2:
                            major = int(version_parts[0])
                            minor = int(version_parts[1])

                            # Set 15 started with patch 14.23
                            if major > 14 or (major == 14 and minor >= 23):
                                latest_set_matches.append(match)

                    except (ValueError, IndexError):
                        # If we can't parse version, check by timestamp
                        # Set 15 started around November 20, 2024
                        game_timestamp = match.get("gameCreation", 0)
                        if game_timestamp > 1732060800000:  # Nov 20, 2024 in milliseconds
                            latest_set_matches.append(match)

            if not latest_set_matches:
                print("[get_latest_placement] No Set 15 matches found")
                return None

            # Get the most recent Set 15 match
            for match in latest_set_matches:
                info = match.get("info", {})
                placement = info.get("placement")

                if placement and isinstance(placement, (int, str)):
                    try:
                        placement_int = int(placement)

                        # Log details for debugging
                        queue_id = match.get("queueId")
                        game_version = info.get("gameVersion", "unknown")
                        queue_type = "unknown"
                        if queue_id == 1100:
                            queue_type = "ranked"
                        elif queue_id == 1160:
                            queue_type = "double-up"
                        elif queue_id == 1090:
                            queue_type = "normal"
                        elif queue_id == 1130:
                            queue_type = "hyper roll"

                        print(
                            f"[get_latest_placement] Found Set 15 placement: {placement_int} from {queue_type} game (version: {game_version})")
                        return placement_int
                    except ValueError:
                        continue

            print(f"[get_latest_placement] No valid placements found in Set 15 matches")
            return None

        except Exception as e:
            print(f"[get_latest_placement] Error parsing match data: {e}")
            return None

    except Exception as e:
        print(f"[get_latest_placement] Error fetching data: {e}")
        return None


# Cleanup function for bot shutdown
async def cleanup_sessions():
    """Close any open sessions on bot shutdown."""
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None