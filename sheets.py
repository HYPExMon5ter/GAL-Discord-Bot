# gal_discord_bot/sheets.py

import asyncio
import json
import os
import random
import time
import re
from gspread import Cell
import aiohttp
from urllib.parse import quote

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import (
    SHEET_KEY,
    DOUBLEUP_SHEET_KEY,
    CACHE_REFRESH_SECONDS,
    REGISTERED_ROLE,
    CHECKED_IN_ROLE,
    ANGEL_ROLE,
)
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


def get_sheet_for_guild(guild_id, worksheet=None):
    mode = get_event_mode_for_guild(guild_id)
    key = DOUBLEUP_SHEET_KEY if mode == "doubleup" else SHEET_KEY
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


async def refresh_sheet_cache(bot=None):
    """
    Pulls columns B, Ign (D), Alt-IGNs (E), Team (F, doubleup only),
    Registered (J for doubleup, F for normal), CheckedIn (K for doubleup, G for normal),
    builds in-memory map: discord_tag -> (row, ign, reg_flag, ci_flag, team, alt_igns).
    Detects adds/removes/updates, updates sheet_cache, returns (num_changes, total_users).
    """
    global sheet_cache
    async with cache_lock:
        old_data = dict(sheet_cache["users"])

        # 1) Pick which guild/sheet to use
        active_guild_id = None
        if bot and hasattr(bot, "guilds") and bot.guilds:
            active_guild_id = bot.guilds[0].id
        gid = str(active_guild_id or SHEET_KEY)

        mode = get_event_mode_for_guild(gid)
        sheet = get_sheet_for_guild(gid, "GAL Database")

        # 2) Fetch all needed columns
        discord_vals = await retry_until_successful(sheet.col_values, 2)
        ign_vals = await retry_until_successful(sheet.col_values, 4)
        alt_vals = await retry_until_successful(sheet.col_values, 5)
        team_vals = []
        if mode == "doubleup":
            try:
                team_vals = await retry_until_successful(sheet.col_values, 6)
            except:
                team_vals = []
        # **Registered / Checked-In columns**
        reg_idx = 10 if mode == "doubleup" else 6  # J vs F
        ci_idx = 11 if mode == "doubleup" else 7   # K vs G
        reg_vals = await retry_until_successful(sheet.col_values, reg_idx)
        ci_vals = await retry_until_successful(sheet.col_values, ci_idx)

        # 3) Trim headers
        discord_col = discord_vals[2:]
        ign_col = ign_vals[2:]
        alt_col = alt_vals[2:]
        team_col = team_vals[2:] if mode == "doubleup" else []
        reg_col = reg_vals[2:]
        ci_col = ci_vals[2:]

        # 4) Build new map
        new_map: dict[str, tuple[int, str, str, str, str, str]] = {}
        for i, tag in enumerate(discord_col, start=3):
            tag = tag.strip()
            if not tag:
                continue
            ign = ign_col[i - 3].strip() if i - 3 < len(ign_col) else ""
            alt = alt_col[i - 3].strip() if i - 3 < len(alt_col) else ""
            team = team_col[i - 3].strip() if mode == "doubleup" and i - 3 < len(team_col) else ""
            reg_flag = reg_col[i - 3].strip() if i - 3 < len(reg_col) else ""
            ci_flag = ci_col[i - 3].strip() if i - 3 < len(ci_col) else ""
            new_map[tag] = (i, ign, reg_flag, ci_flag, team, alt)

        # 5) Change detection
        old_tags = set(old_data.keys())
        new_tags = set(new_map.keys())
        added = new_tags - old_tags
        removed = old_tags - new_tags
        updated = {t for t in new_tags & old_tags if new_map[t] != old_data[t]}

        # 6) Store & return
        sheet_cache["users"] = new_map
        sheet_cache["last_refresh"] = time.time()
        total_changes = len(added) + len(removed) + len(updated)
        return total_changes, len(new_map)


async def cache_refresh_loop(bot):
    while True:
        try:
            await refresh_sheet_cache(bot=bot)
        except:
            pass
        await asyncio.sleep(CACHE_REFRESH_SECONDS)


async def find_or_register_user(discord_tag, ign, guild_id=None, team_name=None):
    """
    Finds existing row or appends a new one.
    Updates IGN, Registered flag, Team (if doubleup), and in-memory cache.
    """
    global sheet_cache
    gid = str(guild_id or SHEET_KEY)
    mode = get_event_mode_for_guild(gid)
    sheet = get_sheet_for_guild(gid, "GAL Database")

    user_tuple = sheet_cache["users"].get(discord_tag)
    row = None
    if user_tuple:
        row = user_tuple[0]
    else:
        # scan column B
        bcol = await retry_until_successful(sheet.col_values, 2)
        for i in range(3, len(bcol) + 1):
            if bcol[i - 1].strip() == discord_tag:
                row = i
                break

    # existing
    if row:
        # update IGN if changed
        ign_col = await retry_until_successful(sheet.col_values, 4)
        if ign_col[row - 3] != ign:
            await retry_until_successful(sheet.update_acell, f"D{row}", ign)
        # mark registered
        reg_col = "J" if mode == "doubleup" else "F"
        await retry_until_successful(sheet.update_acell, f"{reg_col}{row}", "TRUE")
        # update team if needed
        if mode == "doubleup" and team_name:
            await retry_until_successful(sheet.update_acell, f"F{row}", team_name)
        # refresh cache (keep alt-IGN untouched)
        _, old_ign, old_reg, old_ci, old_team, old_alt = sheet_cache["users"][discord_tag]
        sheet_cache["users"][discord_tag] = (
            row,
            ign,
            "TRUE",
            old_ci,
            team_name or old_team,
            old_alt,
        )
        return row

    # new
    values = [None] * 11
    values[1] = discord_tag  # B
    values[3] = ign          # D
    # E alt-IGN left blank
    if mode == "doubleup":
        values[5] = team_name or ""  # F
        values[9] = "TRUE"           # J
        values[10] = "FALSE"         # K
    else:
        values[5] = "TRUE"           # F
        values[6] = "FALSE"          # G
    await retry_until_successful(sheet.append_row, values)
    bcol = await retry_until_successful(sheet.col_values, 2)
    new_row = len(bcol)
    sheet_cache["users"][discord_tag] = (new_row, ign, "TRUE", "FALSE", team_name or "", "")
    return new_row


async def unregister_user(discord_tag: str, guild_id: str | None = None) -> bool:
    """
    Unregisters a user in the sheet:
      - Sets Registered → FALSE (col J in doubleup, F otherwise)
      - ALSO sets Checked-In → FALSE (col K in doubleup, G otherwise)
    Updates the in-memory cache to reflect both flags = FALSE.
    """
    global sheet_cache

    # 1) Locate their cache entry
    tup = sheet_cache["users"].get(discord_tag)
    if not tup:
        return False
    row_num, ign, _, ci_flag, team, alt = tup

    # 2) Figure out which sheet & columns to touch
    gid   = str(guild_id or SHEET_KEY)
    mode  = get_event_mode_for_guild(gid)
    sheet = get_sheet_for_guild(gid, "GAL Database")

    reg_col = "J" if mode == "doubleup" else "F"
    ci_col  = "K" if mode == "doubleup" else "G"

    # 3) Double-check we’re on the correct row (by matching column B)
    cell = await retry_until_successful(sheet.acell, f"B{row_num}")
    if cell.value.strip() != discord_tag:
        # fallback scan
        bcol = await retry_until_successful(sheet.col_values, 2)
        for i in range(3, len(bcol) + 1):
            if bcol[i-1].strip() == discord_tag:
                row_num = i
                break
        else:
            return False

    # 4) Write FALSE to both Registered and Checked-In
    await retry_until_successful(sheet.update_acell, f"{reg_col}{row_num}", "FALSE")
    await retry_until_successful(sheet.update_acell, f"{ci_col}{row_num}",  "FALSE")

    # 5) Update the cache so both flags are cleared
    sheet_cache["users"][discord_tag] = (
        row_num,     # row
        ign,         # ign stays the same
        "FALSE",     # registered now false
        "FALSE",     # checked-in now false
        team,        # team unchanged
        alt          # alt-IGN unchanged
    )

    return True


async def mark_checked_in_async(discord_tag, guild_id=None):
    """
    Sets CheckedIn=True (K or G) in sheet & cache.
    """
    global sheet_cache
    tup = sheet_cache["users"].get(discord_tag)
    if not tup:
        return False
    row = tup[0]
    gid = str(guild_id or SHEET_KEY)
    mode = get_event_mode_for_guild(gid)
    ci_col = "K" if mode == "doubleup" else "G"
    sheet = get_sheet_for_guild(gid, "GAL Database")
    cell = await retry_until_successful(sheet.acell, f"B{row}")
    if cell.value.strip() != discord_tag:
        bcol = await retry_until_successful(sheet.col_values, 2)
        for i in range(3, len(bcol) + 1):
            if bcol[i - 1].strip() == discord_tag:
                row = i
                break
        else:
            return False
    await retry_until_successful(sheet.update_acell, f"{ci_col}{row}", "TRUE")
    # cache
    row_idx, ign, reg, _, team, alt = tup
    sheet_cache["users"][discord_tag] = (row, ign, reg, "TRUE", team, alt)
    return True


async def unmark_checked_in_async(discord_tag, guild_id=None):
    """
    Sets CheckedIn=False (K or G) in sheet & cache.
    """
    global sheet_cache
    tup = sheet_cache["users"].get(discord_tag)
    if not tup:
        return False
    row = tup[0]
    gid = str(guild_id or SHEET_KEY)
    mode = get_event_mode_for_guild(gid)
    ci_col = "K" if mode == "doubleup" else "G"
    sheet = get_sheet_for_guild(gid, "GAL Database")
    cell = await retry_until_successful(sheet.acell, f"B{row}")
    if cell.value.strip() != discord_tag:
        bcol = await retry_until_successful(sheet.col_values, 2)
        for i in range(3, len(bcol) + 1):
            if bcol[i - 1].strip() == discord_tag:
                row = i
                break
        else:
            return False
    await retry_until_successful(sheet.update_acell, f"{ci_col}{row}", "FALSE")
    # cache
    row_idx, ign, reg, _, team, alt = tup
    sheet_cache["users"][discord_tag] = (row, ign, reg, "FALSE", team, alt)
    return True


async def reset_registered_roles_and_sheet(guild, channel):
    """
    Clears all Registered roles on Discord and hides channel, then resets sheet column.
    """
    registered_role = next((r for r in guild.roles if r.name == REGISTERED_ROLE), None)
    angel_role = next((r for r in guild.roles if r.name == ANGEL_ROLE), None)
    cleared = 0
    if registered_role:
        for m in guild.members:
            if registered_role in m.roles:
                cleared += 1
                await m.remove_roles(registered_role)

    if angel_role:
        overwrites = channel.overwrites_for(angel_role)
        overwrites.view_channel = False
        await channel.set_permissions(angel_role, overwrite=overwrites)

    gid = str(guild.id)
    mode = get_event_mode_for_guild(gid)
    reg_col_num = 10 if mode == "doubleup" else 6
    reg_col_letter = "J" if mode == "doubleup" else "F"
    sheet = get_sheet_for_guild(gid, "GAL Database")
    f_values = await retry_until_successful(sheet.col_values, reg_col_num)
    # prepare new values array
    new_vals = [None] * len(f_values)
    for i in range(2, len(new_vals)):
        new_vals[i] = "FALSE"
    # update entire column range
    cell_range = f"{reg_col_letter}1:{reg_col_letter}{len(new_vals)}"
    cell_list = await retry_until_successful(sheet.range, cell_range)
    for cell, val in zip(cell_list, new_vals):
        cell.value = val
    await retry_until_successful(sheet.update_cells, cell_list)
    await refresh_sheet_cache()
    return cleared


async def reset_checked_in_roles_and_sheet(guild, channel):
    """
    Clears all Checked-In roles on Discord and hides channel, then resets sheet column.
    """
    checked_in_role = next((r for r in guild.roles if r.name == CHECKED_IN_ROLE), None)
    registered_role = next((r for r in guild.roles if r.name == REGISTERED_ROLE), None)
    cleared = 0
    if checked_in_role:
        for m in guild.members:
            if checked_in_role in m.roles:
                cleared += 1
                await m.remove_roles(checked_in_role)

    if registered_role:
        overwrites = channel.overwrites_for(registered_role)
        overwrites.view_channel = False
        await channel.set_permissions(registered_role, overwrite=overwrites)

    gid = str(guild.id)
    mode = get_event_mode_for_guild(gid)
    ci_col_num = 11 if mode == "doubleup" else 7
    ci_col_letter = "K" if mode == "doubleup" else "G"
    sheet = get_sheet_for_guild(gid, "GAL Database")
    f_values = await retry_until_successful(sheet.col_values, ci_col_num)
    new_vals = [None] * len(f_values)
    for i in range(2, len(new_vals)):
        new_vals[i] = "FALSE"
    cell_range = f"{ci_col_letter}1:{ci_col_letter}{len(new_vals)}"
    cell_list = await retry_until_successful(sheet.range, cell_range)
    for cell, val in zip(cell_list, new_vals):
        cell.value = val
    await retry_until_successful(sheet.update_cells, cell_list)
    await refresh_sheet_cache()
    return cleared


async def hyperlink_lolchess_profiles(guild_id=None, batch_size: int = 100):
    """
    Batch‐update columns D (main IGN) and E (alt IGNs) with lolchess.gg links,
    but only if the request does *not* end up redirected to /search (which means
    “user not found”). Skips any cell already containing a hyperlink formula.
    """
    sheet = get_sheet_for_guild(str(guild_id or SHEET_KEY), "GAL Database")

    # 1) Map row → (main_ign, alt_igns)
    async with cache_lock:
        row_map = {tup[0]: (tup[1], tup[5].strip()) for tup in sheet_cache["users"].values()}
    if not row_map:
        return

    # 2) Determine last data row
    discord_col = await retry_until_successful(sheet.col_values, 2)
    last_row    = len(discord_col)

    # 3) Bulk‐fetch the D/E ranges
    d_cells = await retry_until_successful(sheet.range, f"D3:D{last_row}")
    e_cells = await retry_until_successful(sheet.range, f"E3:E{last_row}")

    updates: list[Cell] = []

    async with aiohttp.ClientSession(raise_for_status=False) as session:
        # MAIN IGN (col D)
        for cell in d_cells:
            if cell.value.startswith("=HYPERLINK("):
                continue
            data = row_map.get(cell.row)
            if not data or not data[0]:
                continue

            ign  = data[0]
            slug = quote(ign.replace("#", "-"), safe="-")
            url  = f"https://lolchess.gg/profile/na/{slug}/"
            try:
                resp = await session.get(url, allow_redirects=True)
            except:
                continue

            # if we ended up on /search, skip
            if resp.url.path.startswith("/search"):
                continue

            # otherwise it's a valid profile
            cell.value = f'=HYPERLINK("{url}","{ign}")'
            updates.append(cell)

        # ALT IGNs (col E)
        for cell in e_cells:
            if cell.value.startswith("=HYPERLINK("):
                continue
            data = row_map.get(cell.row)
            if not data or not data[1]:
                continue

            parts = [p for p in re.split(r"[,\s]+", data[1]) if p]
            exprs = []
            for name in parts:
                slug = quote(name.replace("#", "-"), safe="-")
                url  = f"https://lolchess.gg/profile/na/{slug}/"
                try:
                    resp = await session.get(url, allow_redirects=True)
                except:
                    continue

                if resp.url.path.startswith("/search"):
                    continue

                exprs.append(f'HYPERLINK("{url}","{name}")')

            if not exprs:
                continue

            cell.value = "=" + ' & ", " & '.join(exprs)
            updates.append(cell)

    # 4) Push all updates back in batches
    for i in range(0, len(updates), batch_size):
        batch = updates[i : i + batch_size]
        await retry_until_successful(
            sheet.update_cells,
            batch,
            value_input_option="USER_ENTERED"
        )