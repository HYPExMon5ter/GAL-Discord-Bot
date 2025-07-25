# gal_discord_bot/sheets.py

import asyncio
import json
import os
import random
import re
import time
from urllib.parse import quote

import aiohttp
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import get_sheet_settings, col_to_index, CACHE_REFRESH_SECONDS
from persistence import get_event_mode_for_guild

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
if os.path.exists("google-creds.json"):
    creds = ServiceAccountCredentials.from_json_keyfile_name("google-creds.json", scope)
else:
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise RuntimeError(
            "Missing google-creds.json file AND GOOGLE_CREDS_JSON environment variable!"
        )
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)


def get_sheet_for_guild(guild_id: str, worksheet: str | None = None):
    """
    Open the correct Google Sheet by extracting its key from config.yaml.
    """
    mode = get_event_mode_for_guild(guild_id)
    cfg  = get_sheet_settings(mode)
    # config.yaml stores full sheet_url; extract the /d/<key>/ portion
    key = cfg["sheet_url"].split("/d/")[1].split("/")[0]
    return client.open_by_key(key).worksheet(worksheet or "GAL Database")


SHEETS_BASE_DELAY = 1.0
MAX_DELAY = 90
FULL_BACKOFF = 60


async def retry_until_successful(fn, *args, **kwargs):
    global SHEETS_BASE_DELAY
    delay = SHEETS_BASE_DELAY
    attempts = 0
    while True:
        try:
            result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
            if delay > SHEETS_BASE_DELAY:
                SHEETS_BASE_DELAY = delay
            return result
        except Exception as e:
            err_str = str(e)
            attempts += 1
            if "429" in err_str or "quota" in err_str.lower():
                if delay >= 30 or attempts > 3:
                    await asyncio.sleep(FULL_BACKOFF + random.uniform(0, 3))
                    delay = FULL_BACKOFF
                else:
                    await asyncio.sleep(delay + random.uniform(0, 0.4))
                    delay = min(delay * 2, MAX_DELAY)
            else:
                raise


sheet_cache = {"users": {}, "last_refresh": 0}
cache_lock = asyncio.Lock()


def ordinal_suffix(n):
    n = int(n)
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

async def refresh_sheet_cache(bot=None) -> tuple[int, int]:
    """
    Pulls rows [header_line_num+1 … header_line_num+max_players] into:
      discord_tag → (row, ign, registered, checked_in, team, alt_igns)
    Returns: (num_changes, total_users)
    """
    async with cache_lock:
        guild = getattr(bot, "guilds", [None])[0]
        gid   = str(guild.id) if guild else None
        mode  = get_event_mode_for_guild(gid)
        cfg   = get_sheet_settings(mode)
        maxp  = cfg.get("max_players", 9999)
        sheet = get_sheet_for_guild(gid, "GAL Database")

        # column indexes
        hline = cfg["header_line_num"]
        dc = col_to_index(cfg["discord_col"])
        ic = col_to_index(cfg["ign_col"])
        ac = col_to_index(cfg["alt_ign_col"])
        rc = col_to_index(cfg["registered_col"])
        cc = col_to_index(cfg["checkin_col"])
        tc = col_to_index(cfg["team_col"]) if mode == "doubleup" else None

        # fetch all
        discord_vals = await retry_until_successful(sheet.col_values, dc)
        ign_vals     = await retry_until_successful(sheet.col_values, ic)
        alt_vals     = await retry_until_successful(sheet.col_values, ac)
        reg_vals     = await retry_until_successful(sheet.col_values, rc)
        ci_vals      = await retry_until_successful(sheet.col_values, cc)
        team_vals    = await retry_until_successful(sheet.col_values, tc) if tc else []

        # slice to max_players
        start = hline
        end   = hline + maxp
        discord_col = discord_vals[start:end]
        ign_col     = ign_vals[start:end]
        alt_col     = alt_vals[start:end]
        reg_col     = reg_vals[start:end]
        ci_col      = ci_vals[start:end]
        team_col    = team_vals[start:end] if tc else []

        new_map = {}
        for idx, tag in enumerate(discord_col, start=start+1):
            off = idx - (start+1)
            tag = tag.strip()
            if not tag:
                continue
            ign  = ign_col[off].strip() if off < len(ign_col) else ""
            alt  = alt_col[off].strip() if off < len(alt_col) else ""
            reg  = reg_col[off].strip() if off < len(reg_col) else ""
            ci   = ci_col[off].strip() if off < len(ci_col) else ""
            team = team_col[off].strip() if (tc and off < len(team_col)) else ""
            new_map[tag] = (idx, ign, reg, ci, team, alt)

        # compute diffs (optional)
        old = sheet_cache["users"]
        added   = set(new_map) - set(old)
        removed = set(old) - set(new_map)
        changed = {t for t in set(new_map)&set(old) if new_map[t] != old[t]}

        # swap in
        sheet_cache["users"]        = new_map
        sheet_cache["last_refresh"] = time.time()
        return len(added) + len(removed) + len(changed), len(new_map)


async def cache_refresh_loop(bot):
    while True:
        try:
            await refresh_sheet_cache(bot=bot)
        except:
            pass
        await asyncio.sleep(CACHE_REFRESH_SECONDS)


async def find_or_register_user(
    discord_tag: str,
    ign: str,
    guild_id: str | None = None,
    team_name: str | None = None
) -> int:
    """
    Ensure a row exists for `discord_tag`. If it does, update IGN,
    Registered=TRUE, and Team (for doubleup) as needed. Otherwise,
    append a new row setting Registered=TRUE, Checked-In=FALSE,
    and Team if applicable. Returns the sheet row number.
    """
    # 1) Grab the current cache snapshot
    async with cache_lock:
        cache = sheet_cache["users"]

    # 2) Resolve config & worksheet
    gid   = str(guild_id)
    mode  = get_event_mode_for_guild(gid)
    cfg   = get_sheet_settings(mode)
    sheet = get_sheet_for_guild(gid, "GAL Database")

    # 3) Try to find an existing row in cache
    tup = cache.get(discord_tag)
    row = tup[0] if tup else None

    # 4) If not in cache, scan the Discord‐tag column manually
    if not row:
        dc   = col_to_index(cfg["discord_col"])
        vals = await retry_until_successful(sheet.col_values, dc)
        for i, v in enumerate(vals, start=1):
            if v.strip() == discord_tag:
                row = i
                break

    # 5) Update the existing row
    if row:
        # unpack the cached tuple
        _, old_ign, old_reg, old_ci, old_team, old_alt = cache[discord_tag]

        # 5a) IGN changed?
        if old_ign != ign:
            await retry_until_successful(
                sheet.update_acell,
                f"{cfg['ign_col']}{row}",
                ign
            )

        # 5b) Registered flag toggle
        if old_reg.upper() != "TRUE":
            await retry_until_successful(
                sheet.update_acell,
                f"{cfg['registered_col']}{row}",
                "TRUE"
            )

        # 5c) Team name (doubleup) changed?
        if mode == "doubleup" and team_name and old_team != team_name:
            await retry_until_successful(
                sheet.update_acell,
                f"{cfg['team_col']}{row}",
                team_name
            )

        # 5d) Update in-memory cache (6-tuple)
        sheet_cache["users"][discord_tag] = (
            row,
            ign,
            "TRUE",
            old_ci,
            team_name or old_team,
            old_alt
        )
        return row

    # 6) Append a brand-new row
    # 6a) Determine how many columns we need
    max_col = max(
        col_to_index(col)
        for col in cfg.values()
        if isinstance(col, str)
    )
    # build a blank row
    vals = [""] * max_col
    vals[col_to_index(cfg["discord_col"]) - 1]   = discord_tag
    vals[col_to_index(cfg["ign_col"])        - 1] = ign
    vals[col_to_index(cfg["registered_col"]) - 1] = "TRUE"
    vals[col_to_index(cfg["checkin_col"])    - 1] = "FALSE"
    if mode == "doubleup":
        vals[col_to_index(cfg["team_col"])    - 1] = team_name or ""

    # 6b) Append and recompute row number
    await retry_until_successful(sheet.append_row, vals)
    dc_vals = await retry_until_successful(
        sheet.col_values,
        col_to_index(cfg["discord_col"])
    )
    new_row = len(dc_vals)

    # 6c) Insert into cache
    sheet_cache["users"][discord_tag] = (
        new_row,
        ign,
        "TRUE",
        "FALSE",
        team_name or "",
        ""
    )
    return new_row


async def unregister_user(discord_tag: str, guild_id: str | None = None) -> bool:
    """
    Un-register a user:
      - Sets Registered & Checked-In = FALSE
      - Updates the in-memory cache (6-tuple).
    """
    async with cache_lock:
        tup = sheet_cache["users"].get(discord_tag)
    if not tup:
        return False

    row, ign, _, _, team, alt = tup
    gid    = str(guild_id)
    mode   = get_event_mode_for_guild(gid)
    cfg    = get_sheet_settings(mode)
    sheet  = get_sheet_for_guild(gid, "GAL Database")

    # Sanity-check the Discord tag still matches
    dc_cell = await retry_until_successful(sheet.acell, f"{cfg['discord_col']}{row}")
    if dc_cell.value.strip() != discord_tag:
        return False

    await retry_until_successful(sheet.update_acell, f"{cfg['registered_col']}{row}", "FALSE")
    await retry_until_successful(sheet.update_acell, f"{cfg['checkin_col']}{row}",    "FALSE")

    sheet_cache["users"][discord_tag] = (row, ign, "FALSE", "FALSE", team, alt)
    return True


async def mark_checked_in_async(discord_tag: str, guild_id: str | None = None) -> bool:
    """
    Marks a user as checked-in in both sheet & cache.
    """
    async with cache_lock:
        tup = sheet_cache["users"].get(discord_tag)
    if not tup:
        return False

    row, ign, reg, old_ci, team, alt = tup
    if reg.upper() != "TRUE":
        return False

    gid   = str(guild_id)
    cfg   = get_sheet_settings(get_event_mode_for_guild(gid))
    sheet = get_sheet_for_guild(gid, "GAL Database")

    await retry_until_successful(
        sheet.update_acell,
        f"{cfg['checkin_col']}{row}",
        "TRUE"
    )
    sheet_cache["users"][discord_tag] = (row, ign, reg, "TRUE", team, alt)
    return True


async def unmark_checked_in_async(discord_tag: str, guild_id: str | None = None) -> bool:
    """
    Un-marks a user as checked-in in both sheet & cache.
    """
    async with cache_lock:
        tup = sheet_cache["users"].get(discord_tag)
    if not tup:
        return False

    row, ign, reg, old_ci, team, alt = tup
    if old_ci.upper() != "TRUE":
        return False

    gid   = str(guild_id)
    cfg   = get_sheet_settings(get_event_mode_for_guild(gid))
    sheet = get_sheet_for_guild(gid, "GAL Database")

    await retry_until_successful(
        sheet.update_acell,
        f"{cfg['checkin_col']}{row}",
        "FALSE"
    )
    sheet_cache["users"][discord_tag] = (row, ign, reg, "FALSE", team, alt)
    return True


async def reset_registered_roles_and_sheet(guild, channel) -> int:
    """
    Clears the Registered column in the sheet:
      - Sets every cell in Registered col to FALSE
      - Refreshes the cache
    Returns the number of rows cleared (excluding header).
    """
    gid  = str(guild.id)
    mode = get_event_mode_for_guild(gid)
    cfg  = get_sheet_settings(mode)
    sheet= get_sheet_for_guild(gid, "GAL Database")

    col  = cfg["registered_col"]
    idx  = col_to_index(col)
    vals = await retry_until_successful(sheet.col_values, idx)

    # Build range from header to end
    cell_list = await retry_until_successful(sheet.range, f"{col}1:{col}{len(vals)}")
    for cell in cell_list:
        cell.value = "FALSE"
    await retry_until_successful(sheet.update_cells, cell_list)

    await refresh_sheet_cache()
    # subtract header lines
    return max(0, len(vals) - cfg["header_line_num"])


async def reset_checked_in_roles_and_sheet(guild, channel) -> int:
    """
    Clears the Checked-In column in the sheet:
      - Sets every cell in Checked-In col to FALSE
      - Refreshes the cache
    Returns the number of rows cleared (excluding header).
    """
    gid  = str(guild.id)
    mode = get_event_mode_for_guild(gid)
    cfg  = get_sheet_settings(mode)
    sheet= get_sheet_for_guild(gid, "GAL Database")

    col  = cfg["checkin_col"]
    idx  = col_to_index(col)
    vals = await retry_until_successful(sheet.col_values, idx)

    cell_list = await retry_until_successful(sheet.range, f"{col}1:{col}{len(vals)}")
    for cell in cell_list:
        cell.value = "FALSE"
    await retry_until_successful(sheet.update_cells, cell_list)

    await refresh_sheet_cache()
    return max(0, len(vals) - cfg["header_line_num"])