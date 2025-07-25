# gal_discord_bot/riot_api.py

import json
import os
import re
import urllib.parse
from typing import Optional, Union

import aiohttp

from persistence import get_event_mode_for_guild

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
    (normal vs double-up) by pulling the Next.js JSON and inspecting
    all 'placement' arrays, then filtering by mode.
    """
    mode = get_event_mode_for_guild(guild_id).lower()  # "normal" or "doubleup"
    url  = build_tactics_tools_url(ign)
    print(f"[get_latest_placement] mode={mode!r}, GET {url}")

    session = await _get_session()
    # — Step 1: fetch initial HTML & __NEXT_DATA__ —
    async with session.get(url) as resp:
        if resp.status != 200:
            print(f"[get_latest_placement] HTTP {resp.status}")
            return None
        html = await resp.text()

    m = re.search(r'<script\s+id="__NEXT_DATA__"[^>]*>(?P<json>.+?)</script>',
                  html, flags=re.DOTALL)
    if not m:
        print("[get_latest_placement] no __NEXT_DATA__")
        return None

    try:
        bootstrap = json.loads(m.group("json"))
    except json.JSONDecodeError as e:
        print("[get_latest_placement] JSON parse error:", e)
        return None

    # — Step 2: derive and fetch the data JSON —
    build_id = bootstrap.get("buildId")
    if not build_id:
        print("[get_latest_placement] no buildId in bootstrap")
        return None

    path = urllib.parse.urlparse(url).path  # e.g. "/player/na/Echoes/TFT1"
    data_url = f"https://tactics.tools/_next/data/{build_id}{path}.json"
    async with session.get(data_url) as resp2:
        if resp2.status != 200:
            print(f"[get_latest_placement] data JSON HTTP {resp2.status}")
            return None
        page_json = await resp2.json()

    page_props = page_json.get("pageProps", {}) or page_json.get("props", {}).get("pageProps", {})
    if not page_props:
        print("[get_latest_placement] no pageProps")
        return None

    # — Step 3: collect all lists of matches —
    match_items = []
    for v in page_props.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and "placement" in v[0]:
            match_items.extend(v)

    if not match_items:
        print("[get_latest_placement] no match arrays found")
        return None

    # — Step 4: filter by mode —
    if mode == "doubleup":
        filtered = [
            m for m in match_items
            if any("double" in str(x).lower() for x in m.values())
        ]
    else:
        filtered = [
            m for m in match_items
            if not any("double" in str(x).lower() for x in m.values())
        ]

    chosen = filtered[0] if filtered else match_items[0]
    placement = chosen.get("placement")
    print(f"[get_latest_placement] chosen placement={placement!r}")
    return placement if isinstance(placement, int) else None

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