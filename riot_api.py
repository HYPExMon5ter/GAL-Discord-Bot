# gal_discord_bot/riot_api.py

import json
import os
import re
import urllib.parse
from typing import Optional, Union

import aiohttp

from config import RIOT_API_KEY

# === Constants ===
RIOT_API_REGION = "na1"
TFT_REGION = "americas"
TRACKER_API_KEY = os.getenv("TRACKER_API_KEY")
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}

# Shared aiohttp session
_session: Optional[aiohttp.ClientSession] = None

# === Riot API Helpers ===
def riot_headers() -> dict:
    """Headers for Riot API calls."""
    return {"X-Riot-Token": RIOT_API_KEY}

async def _get_session() -> aiohttp.ClientSession:
    """
    Returns a shared aiohttp session with DEFAULT_HEADERS.
    """
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(headers=DEFAULT_HEADERS)
    return _session

# ———————————————————————————————
# 1) Sanitizer to strip U+2066–U+2069
# ———————————————————————————————
def _remove_bidi_control_chars(s: str) -> str:
    """
    Remove Unicode isolate controls (U+2066–U+2069) from the IGN.
    """
    return re.sub(r"[\u2066-\u2069]", "", s)


# ———————————————————————————————
# 2) URL builder (uses sanitizer)
# ———————————————————————————————
def build_tactics_tools_url(ign: str) -> str:
    """
    Build a tactics.tools URL for a TFT profile.
    1) Strip bidi controls
    2) Split on '#'
    3) URL-encode name and tag
    """
    clean = _remove_bidi_control_chars(ign)
    parts = clean.split("#", 1)
    name = parts[0].strip()
    tag  = parts[1].strip() if len(parts) > 1 else ""
    name_enc = urllib.parse.quote(name)
    path = f"/player/na/{name_enc}"
    if tag:
        path += f"/{urllib.parse.quote(tag)}"
    return f"https://tactics.tools{path}"


# ———————————————————————————————
# 3) Placement scraper (now sanitizes IGN)
# ———————————————————————————————
async def tactics_tools_get_latest_placement(ign: str) -> Optional[int]:
    """
    Scrape tactics.tools for the player’s latest TFT placement.
    BIDI controls are stripped from the IGN first.
    """
    # 1) Sanitize and build URL
    clean_ign = _remove_bidi_control_chars(ign)
    url = build_tactics_tools_url(clean_ign)
    print(f"[tactics_tools_get_latest_placement] GET {url} for {clean_ign!r}")

    # 2) Fetch HTML
    session = await _get_session()
    async with session.get(url) as resp:
        print(f"[tactics_tools_get_latest_placement] HTTP {resp.status} for {clean_ign!r}")
        if resp.status != 200:
            return None
        html = await resp.text()

    # 3) Extract the Next.js JSON blob
    m = re.search(
        r'<script\s+id="__NEXT_DATA__"[^>]*>(?P<json>.+?)</script>',
        html,
        flags=re.DOTALL
    )
    if not m:
        print(f"[tactics_tools_get_latest_placement] no JSON for {clean_ign!r}")
        return None

    # 4) Parse JSON and find first 'placement'
    try:
        data = json.loads(m.group("json"))
    except json.JSONDecodeError as e:
        print(f"[tactics_tools_get_latest_placement] JSON error for {clean_ign!r}: {e}")
        return None

    def _extract_first_placement(obj: Union[dict, list]) -> Optional[int]:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower() == "placement" and isinstance(v, int):
                    return v
                got = _extract_first_placement(v)
                if got is not None:
                    return got
        elif isinstance(obj, list):
            for item in obj:
                got = _extract_first_placement(item)
                if got is not None:
                    return got
        return None

    page_props = data.get("props", {}).get("pageProps", {})
    placement = _extract_first_placement(page_props)
    print(f"[tactics_tools_get_latest_placement] placement={placement} for {clean_ign!r}")
    return placement

async def get_tracker_tft_rank(ign: str) -> str | None:
    """
    Fetch live Set 14 rank from Tracker.gg's TFT API using the
    TRN-Api-Key loaded from .env.

    Example .env entry:
      TRACKER_API_KEY=your_key_here
    """
    # Split name/tag
    name, tag = (ign.split("#", 1) + [""])[:2]
    name_enc = urllib.parse.quote(name.strip())
    seg = name_enc + (f"%23{urllib.parse.quote(tag.strip())}" if tag else "")
    url = f"https://api.tracker.gg/api/v2/tft/standard/profile/riot/{seg}?forceCollect=true"
    headers = {
        "TRN-Api-Key": TRACKER_API_KEY,
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            print(f"[DEBUG get_tracker_tft_rank] HTTP {resp.status} for {ign!r}")
            if resp.status != 200:
                print("Tracker API error status:", resp.status)
                return None
            payload = await resp.json()

    # Extract tier/division/LP
    try:
        segment = next(
            seg for seg in payload["data"]["segments"]
            if seg.get("type") == "overview"
        )
        raw = segment["stats"]["rank"]["metadata"]["rankString"]
    except Exception as e:
        print(f"[ERROR get_tracker_tft_rank] parsing error for {ign!r}: {e}")
        return None

    return raw  # e.g. "Silver II 85LP"