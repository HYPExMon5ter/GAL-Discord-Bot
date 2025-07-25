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
    If user exists: update IGN, set Registered=True, update Team (doubleup).
    Otherwise: write into first blank slot under header (or append),
    marking Registered=True, Checked-In=False.
    Returns the 1-based row number.
    """
    async with cache_lock:
        existing = sheet_cache["users"].get(discord_tag)

    gid   = str(guild_id)
    mode  = get_event_mode_for_guild(gid)
    cfg   = get_sheet_settings(mode)
    sheet = get_sheet_for_guild(gid, "GAL Database")

    # ── UPDATE EXISTING ───────────────────────────────────────────
    if existing:
        row, old_ign, old_reg, old_ci, old_team, old_alt = existing

        if old_ign != ign:
            await retry_until_successful(
                sheet.update_acell,
                f"{cfg['ign_col']}{row}",
                ign
            )
        if not old_reg:
            await retry_until_successful(
                sheet.update_acell,
                f"{cfg['registered_col']}{row}",
                True
            )
        if mode == "doubleup" and team_name and old_team != team_name:
            await retry_until_successful(
                sheet.update_acell,
                f"{cfg['team_col']}{row}",
                team_name
            )

        # refresh cache
        sheet_cache["users"][discord_tag] = (
            row, ign, True, old_ci, team_name or old_team, old_alt
        )
        return row

    # ── NEW REGISTRATION ──────────────────────────────────────────
    hline  = cfg["header_line_num"]
    maxp   = cfg.get("max_players", 9999)
    dc_idx = col_to_index(cfg["discord_col"])
    discord_vals = await retry_until_successful(sheet.col_values, dc_idx)

    # find first empty slot between hline+1 … hline+maxp
    target_row = None
    for i in range(hline, min(len(discord_vals), hline + maxp)):
        if not discord_vals[i].strip():
            target_row = i + 1
            break

    # prepare column→value map
    writes = {
        cfg["discord_col"]:   discord_tag,
        cfg["ign_col"]:       ign,
        cfg["registered_col"]: True,
        cfg["checkin_col"]:   False
    }
    if mode == "doubleup":
        writes[cfg["team_col"]] = team_name or ""

    if target_row:
        # fill pre-formatted row
        for col, val in writes.items():
            await retry_until_successful(
                sheet.update_acell,
                f"{col}{target_row}",
                val
            )
        row = target_row
    else:
        # fallback: append
        cols_idx = [col_to_index(c) for c in writes]
        max_idx  = max(cols_idx)
        row_vals = [""] * max_idx
        for col, val in writes.items():
            row_vals[col_to_index(col)-1] = val
        await retry_until_successful(sheet.append_row, row_vals)
        dc_vals = await retry_until_successful(sheet.col_values, dc_idx)
        row     = len(dc_vals)

    sheet_cache["users"][discord_tag] = (
        row, ign, True, False,
        team_name or "", ""
    )
    return row


async def unregister_user(
    discord_tag: str,
    guild_id: str | None = None
) -> bool:
    """
    Set Registered=False, Checked-In=False for `discord_tag`.
    """
    async with cache_lock:
        tup = sheet_cache["users"].get(discord_tag)
    if not tup:
        return False

    row, ign, old_reg, old_ci, team, alt = tup
    gid   = str(guild_id)
    mode  = get_event_mode_for_guild(gid)
    cfg   = get_sheet_settings(mode)
    sheet = get_sheet_for_guild(gid, "GAL Database")

    # sanity check
    cell = await retry_until_successful(sheet.acell, f"{cfg['discord_col']}{row}")
    if cell.value.strip() != discord_tag:
        return False

    await retry_until_successful(
        sheet.update_acell,
        f"{cfg['registered_col']}{row}",
        False
    )
    await retry_until_successful(
        sheet.update_acell,
        f"{cfg['checkin_col']}{row}",
        False
    )

    sheet_cache["users"][discord_tag] = (
        row, ign, False, False, team, alt
    )
    return True


async def mark_checked_in_async(
    discord_tag: str,
    guild_id: str | None = None
) -> bool:
    """
    If Registered=True, set Checked-In=True for `discord_tag`.
    """
    async with cache_lock:
        tup = sheet_cache["users"].get(discord_tag)
    if not tup:
        return False

    row, ign, reg, _, team, alt = tup
    if not reg:
        return False

    gid   = str(guild_id)
    mode  = get_event_mode_for_guild(gid)
    cfg   = get_sheet_settings(mode)
    sheet = get_sheet_for_guild(gid, "GAL Database")

    await retry_until_successful(
        sheet.update_acell,
        f"{cfg['checkin_col']}{row}",
        True
    )

    sheet_cache["users"][discord_tag] = (
        row, ign, reg, True, team, alt
    )
    return True


async def unmark_checked_in_async(
    discord_tag: str,
    guild_id: str | None = None
) -> bool:
    """
    If Checked-In=True, set Checked-In=False for `discord_tag`.
    """
    async with cache_lock:
        tup = sheet_cache["users"].get(discord_tag)
    if not tup:
        return False

    row, ign, reg, ci, team, alt = tup
    if not ci:
        return False

    gid   = str(guild_id)
    mode  = get_event_mode_for_guild(gid)
    cfg   = get_sheet_settings(mode)
    sheet = get_sheet_for_guild(gid, "GAL Database")

    await retry_until_successful(
        sheet.update_acell,
        f"{cfg['checkin_col']}{row}",
        False
    )

    sheet_cache["users"][discord_tag] = (
        row, ign, reg, False, team, alt
    )
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