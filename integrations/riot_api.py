# integrations/riot_api.py

import json
import os
import re
import urllib.parse
from typing import Optional

import aiohttp

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
    Fetch the player's most recent TFT placement from metatft.com
    """

    # Clean and format IGN for metatft URL
    def clean_ign(s: str) -> str:
        return re.sub(r'[\u2066-\u2069]', '', s).strip()

    ign_clean = clean_ign(ign)
    name, _, tag = ign_clean.partition("#")

    # metatft uses lowercase and hyphen between name and tag
    formatted_name = f"{name.strip()}-{tag.strip()}" if tag else name.strip()
    formatted_name = formatted_name.lower()

    url = f"https://www.metatft.com/player/na/{formatted_name}"
    print(f"[get_latest_placement] GET {url}")

    session = await _get_session()

    try:
        async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
            if resp.status != 200:
                print(f"[get_latest_placement] HTTP {resp.status}")
                return None
            html = await resp.text()

        # Debug: Save HTML for inspection
        with open(f"metatft_debug_{ign.replace('#', '_')}.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[get_latest_placement] Saved HTML to metatft_debug_{ign.replace('#', '_')}.html")

        # Look for placement patterns in metatft HTML
        # Common patterns for placement display
        placement_patterns = [
            # Look for placement in match history
            r'placement["\s:]+(\d+)',
            r'#(\d+)</span>',  # Often placements are shown as #1, #2, etc
            r'rank["\s:]+(\d+)',
            r'"place"["\s:]+(\d+)',
            r'position["\s:]+(\d+)',
            # MetaTFT specific patterns
            r'<div[^>]*class="[^"]*place[^"]*"[^>]*>.*?(\d+)',
            r'<span[^>]*class="[^"]*rank[^"]*"[^>]*>.*?(\d+)',
            # Look in data attributes
            r'data-placement="(\d+)"',
            r'data-rank="(\d+)"',
            r'data-position="(\d+)"',
        ]

        for pattern in placement_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                # Get the first valid placement (most recent)
                for match in matches:
                    try:
                        placement = int(match)
                        if 1 <= placement <= 8:  # Valid TFT placement
                            print(f"[get_latest_placement] Found placement: {placement}")
                            return placement
                    except ValueError:
                        continue

        # Look for JSON data in script tags
        json_patterns = [
            r'<script[^>]*>window\.__INITIAL_STATE__\s*=\s*({.*?})</script>',
            r'<script[^>]*type="application/json"[^>]*>({.*?})</script>',
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>({.*?})</script>',
        ]

        for json_pattern in json_patterns:
            json_matches = re.findall(json_pattern, html, re.DOTALL)

            for json_str in json_matches:
                try:
                    data = json.loads(json_str)

                    # Navigate through possible data structures
                    # Try to find match/game data
                    def find_placement(obj, depth=0):
                        if depth > 10:  # Prevent infinite recursion
                            return None

                        if isinstance(obj, dict):
                            # Direct placement field
                            if "placement" in obj:
                                try:
                                    return int(obj["placement"])
                                except:
                                    pass

                            # Check common keys for match data
                            for key in ["matches", "games", "matchHistory", "recentGames", "data", "props"]:
                                if key in obj:
                                    result = find_placement(obj[key], depth + 1)
                                    if result:
                                        return result

                        elif isinstance(obj, list) and obj:
                            # Check first item if it's recent match
                            for item in obj[:5]:  # Check first 5 items
                                result = find_placement(item, depth + 1)
                                if result:
                                    return result

                        return None

                    placement = find_placement(data)
                    if placement and 1 <= placement <= 8:
                        print(f"[get_latest_placement] Found placement in JSON: {placement}")
                        return placement

                except Exception as e:
                    print(f"[get_latest_placement] Error parsing JSON: {e}")
                    continue

        # If we still haven't found anything, look for match result text
        # MetaTFT might show results like "1st", "2nd", etc.
        ordinal_pattern = r'(\d+)(?:st|nd|rd|th)\s*(?:place)?'
        ordinal_matches = re.findall(ordinal_pattern, html, re.IGNORECASE)

        for match in ordinal_matches:
            try:
                placement = int(match)
                if 1 <= placement <= 8:
                    print(f"[get_latest_placement] Found ordinal placement: {placement}")
                    return placement
            except ValueError:
                continue

        print("[get_latest_placement] No placement found in HTML")
        return None

    except Exception as e:
        print(f"[get_latest_placement] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# Cleanup function for bot shutdown
async def cleanup_sessions():
    """Close any open sessions on bot shutdown."""
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None
