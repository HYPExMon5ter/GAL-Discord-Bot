# gal_discord_bot/riot_api.py

import json
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
    Fetch the player's most recent TFT placement for the guild's mode
    (normal vs double-up) by scraping tactics.tools website.
    """
    mode = get_event_mode_for_guild(guild_id).lower()  # "normal" or "doubleup"
    url = build_tactics_tools_url(ign)
    print(f"[get_latest_placement] mode={mode!r}, GET {url}")

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
        # The structure is typically: props -> pageProps -> player -> matches
        try:
            page_props = data.get("props", {}).get("pageProps", {})
            if not page_props:
                # Try alternative structure
                page_props = data.get("pageProps", {})

            # Look for matches in various possible locations
            matches = None

            # Try different paths where matches might be stored
            if "player" in page_props and "matches" in page_props["player"]:
                matches = page_props["player"]["matches"]
            elif "matches" in page_props:
                matches = page_props["matches"]
            elif "data" in page_props and "matches" in page_props["data"]:
                matches = page_props["data"]["matches"]
            elif "matchHistory" in page_props:
                matches = page_props["matchHistory"]

            if not matches:
                print("[get_latest_placement] No matches found in data")
                return None

            # Filter matches based on mode
            for match in matches:
                # Check if it's a double-up match
                is_double_up = False

                # Check various fields that might indicate double-up
                if "game_type" in match:
                    is_double_up = "double" in str(match["game_type"]).lower()
                elif "queueType" in match:
                    is_double_up = "double" in str(match["queueType"]).lower()
                elif "gameMode" in match:
                    is_double_up = "double" in str(match["gameMode"]).lower()
                elif "traits" in match:
                    # Sometimes double-up is indicated by specific traits
                    traits_str = json.dumps(match["traits"]).lower()
                    is_double_up = "double" in traits_str

                # Skip if mode doesn't match
                if mode == "doubleup" and not is_double_up:
                    continue
                elif mode == "normal" and is_double_up:
                    continue

                # Get placement
                placement = match.get("placement")
                if placement and isinstance(placement, (int, str)):
                    try:
                        return int(placement)
                    except ValueError:
                        continue

            print(f"[get_latest_placement] No {mode} matches found")
            return None

        except Exception as e:
            print(f"[get_latest_placement] Error parsing match data: {e}")
            return None

    except Exception as e:
        print(f"[get_latest_placement] Error fetching data: {e}")
        return None