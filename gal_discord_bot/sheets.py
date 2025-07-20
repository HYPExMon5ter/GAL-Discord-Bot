# gal_discord_bot/sheets.py

import asyncio
import json
import os
import random
import time

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from gal_discord_bot.config import (
    SHEET_KEY, DOUBLEUP_SHEET_KEY,
    CACHE_REFRESH_SECONDS, REGISTERED_ROLE, CHECKED_IN_ROLE, ANGEL_ROLE
)
from gal_discord_bot.persistence import (
    get_event_mode_for_guild
)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
if os.path.exists("google-creds.json"):
    creds = ServiceAccountCredentials.from_json_keyfile_name("google-creds.json", scope)
else:
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise RuntimeError("Missing google-creds.json file AND GOOGLE_CREDS_JSON environment variable!")
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)

def get_sheet_for_guild(guild_id, worksheet=None):
    mode = get_event_mode_for_guild(guild_id)
    if mode == "doubleup":
        return client.open_by_key(DOUBLEUP_SHEET_KEY).worksheet(worksheet or "GAL Database")
    else:
        return client.open_by_key(SHEET_KEY).worksheet(worksheet or "GAL Database")

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
    Pulls columns B,Ign,D,Alt-E,Team-F,Registered-H,CheckedIn-I from the sheet,
    builds an in-memory map of discord_tag -> (row, ign, reg_flag, ci_flag, team, alt_igns).
    Detects adds/removes/updates, updates sheet_cache, and returns (num_changes, total_users).
    """
    global sheet_cache
    async with cache_lock:
        old_data = dict(sheet_cache["users"])

        # 1) Pick which guild/sheet to use
        active_guild_id = None
        if bot and hasattr(bot, "guilds") and bot.guilds:
            active_guild_id = bot.guilds[0].id
        gid = str(active_guild_id or SHEET_KEY)

        mode  = get_event_mode_for_guild(gid)
        sheet = get_sheet_for_guild(gid, "GAL Database")

        # 2) Fetch all needed columns (with retry/back-off)
        discord_vals   = await retry_until_successful(sheet.col_values, 2)
        ign_vals       = await retry_until_successful(sheet.col_values, 4)
        alt_vals       = await retry_until_successful(sheet.col_values, 5)
        # team only if doubleup
        team_vals      = []
        if mode == "doubleup":
            try:
                team_raw = await retry_until_successful(sheet.col_values, 6)
                team_vals = team_raw
            except:
                team_vals = []
        reg_idx   = 8 if mode == "doubleup" else 6
        ci_idx    = 9 if mode == "doubleup" else 7
        reg_vals  = await retry_until_successful(sheet.col_values, reg_idx)
        ci_vals   = await retry_until_successful(sheet.col_values, ci_idx)

        # 3) Trim headers off each list
        discord_col   = discord_vals[2:]
        ign_col       = ign_vals[2:]
        alt_col       = alt_vals[2:]
        team_col      = team_vals[2:] if mode == "doubleup" else []
        registered_col= reg_vals[2:]
        checkedin_col = ci_vals[2:]

        # 4) Build new map
        new_map = {}
        for i, tag in enumerate(discord_col, start=3):
            tag = tag.strip()
            if not tag:
                continue
            ign      = ign_col[i-3].strip() if i-3 < len(ign_col) else ""
            alt      = alt_col[i-3].strip() if i-3 < len(alt_col) else ""
            reg_flag = registered_col[i-3].strip() if i-3 < len(registered_col) else ""
            ci_flag  = checkedin_col[i-3].strip() if i-3 < len(checkedin_col) else ""
            team     = team_col[i-3].strip() if mode=="doubleup" and i-3 < len(team_col) else ""
            new_map[tag] = (i, ign, reg_flag, ci_flag, team, alt)

        # 5) Change detection
        old_tags = set(old_data.keys())
        new_tags = set(new_map.keys())
        added   = new_tags - old_tags
        removed = old_tags - new_tags
        updated = {t for t in new_tags & old_tags if new_map[t] != old_data[t]}

        # 6) Store & return
        sheet_cache["users"]       = new_map
        sheet_cache["last_refresh"]= time.time()
        total_changes = len(added) + len(removed) + len(updated)
        return total_changes, len(new_map)

async def cache_refresh_loop(bot):
    while True:
        try:
            await refresh_sheet_cache(bot=bot)
        except Exception:
            pass
        await asyncio.sleep(CACHE_REFRESH_SECONDS)

async def find_or_register_user(discord_tag, ign, guild_id=None, team_name=None):
    global sheet_cache
    gid  = str(guild_id or SHEET_KEY)
    mode = get_event_mode_for_guild(gid)
    sheet= get_sheet_for_guild(gid, "GAL Database")

    user_tuple = sheet_cache["users"].get(discord_tag)
    if user_tuple:
        row_num = user_tuple[0]
    else:
        # scan column B to find row
        bcol = await retry_until_successful(sheet.col_values, 2)
        row_num = next((i for i in range(3, len(bcol)+1) if bcol[i-1].strip()==discord_tag), None)

    if user_tuple and row_num:
        # existing user: update IGN if changed
        ign_col = await retry_until_successful(sheet.col_values, 4)
        if ign_col[row_num-3] != ign:
            await retry_until_successful(sheet.update_acell, f"D{row_num}", ign)

        # mark registered
        reg_col = "H" if mode=="doubleup" else "F"
        await retry_until_successful(sheet.update_acell, f"{reg_col}{row_num}", "TRUE")

        # update team if needed
        if mode=="doubleup" and team_name:
            await retry_until_successful(sheet.update_acell, f"F{row_num}", team_name)

        # refresh in-memory cache (leave alt untouched here)
        _, old_ign, old_reg, old_ci, old_team, old_alt = user_tuple
        sheet_cache["users"][discord_tag] = (
            row_num,
            ign,
            "TRUE",
            old_ci,
            team_name or old_team,
            old_alt
        )
        return row_num

    # --- new user: append ---
    values = [None]*9
    values[1] = discord_tag  # B
    values[3] = ign          # D
    # E left blank for alt-IGN until complete_registration writes it
    if mode=="doubleup":
        values[5] = team_name or ""  # F
        values[7] = "TRUE"           # H
        values[8] = "FALSE"          # I
    else:
        values[5] = "TRUE"           # F
        values[6] = "FALSE"          # G
    await retry_until_successful(sheet.append_row, values)

    # locate & cache the new row
    bcol = await retry_until_successful(sheet.col_values, 2)
    new_row = len(bcol)
    sheet_cache["users"][discord_tag] = (
        new_row, ign,
        "TRUE",
        "FALSE",
        team_name or "",
        ""
    )
    return new_row

async def unregister_user(discord_tag, guild_id=None):
    global sheet_cache
    user_tuple = sheet_cache["users"].get(discord_tag)
    if not user_tuple:
        return False
    row_num = user_tuple[0]
    if not guild_id:
        guild_id = str(SHEET_KEY)
    mode = get_event_mode_for_guild(guild_id)
    reg_col = "H" if mode == "doubleup" else "F"
    sheet = get_sheet_for_guild(guild_id, "GAL Database")
    cell = await retry_until_successful(sheet.acell, f"B{row_num}")
    if not cell.value or cell.value.strip() != discord_tag:
        b_col = await retry_until_successful(sheet.col_values, 2)
        for i in range(3, len(b_col) + 1):
            if b_col[i - 1].strip() == discord_tag:
                row_num = i
                break
        else:
            return False
    await retry_until_successful(sheet.update_acell, f"{reg_col}{row_num}", "FALSE")
    # Update cache directly (unregister)
    user_tuple = list(user_tuple)
    user_tuple[0] = row_num
    user_tuple[2] = "FALSE"  # Registered status
    user_tuple[3] = "FALSE"  # Checked in status
    sheet_cache["users"][discord_tag] = tuple(user_tuple)
    return True

async def mark_checked_in_async(discord_tag, guild_id=None):
    global sheet_cache
    user_tuple = sheet_cache["users"].get(discord_tag)
    if not user_tuple:
        return False
    row_num = user_tuple[0]
    if not guild_id:
        guild_id = str(SHEET_KEY)
    mode = get_event_mode_for_guild(guild_id)
    checkin_col = "I" if mode == "doubleup" else "G"
    sheet = get_sheet_for_guild(guild_id, "GAL Database")
    cell = await retry_until_successful(sheet.acell, f"B{row_num}")
    if not cell.value or cell.value.strip() != discord_tag:
        b_col = await retry_until_successful(sheet.col_values, 2)
        for i in range(3, len(b_col) + 1):
            if b_col[i - 1].strip() == discord_tag:
                row_num = i
                break
        else:
            return False
    await retry_until_successful(sheet.update_acell, f"{checkin_col}{row_num}", "TRUE")
    # Update cache directly
    user_tuple = list(user_tuple)
    user_tuple[0] = row_num
    user_tuple[3] = "TRUE"
    sheet_cache["users"][discord_tag] = tuple(user_tuple)
    return True

async def unmark_checked_in_async(discord_tag, guild_id=None):
    global sheet_cache
    user_tuple = sheet_cache["users"].get(discord_tag)
    if not user_tuple:
        return False
    row_num = user_tuple[0]
    if not guild_id:
        guild_id = str(SHEET_KEY)
    mode = get_event_mode_for_guild(guild_id)
    checkin_col = "I" if mode == "doubleup" else "G"
    sheet = get_sheet_for_guild(guild_id, "GAL Database")
    cell = await retry_until_successful(sheet.acell, f"B{row_num}")
    if not cell.value or cell.value.strip() != discord_tag:
        b_col = await retry_until_successful(sheet.col_values, 2)
        for i in range(3, len(b_col) + 1):
            if b_col[i - 1].strip() == discord_tag:
                row_num = i
                break
        else:
            return False
    await retry_until_successful(sheet.update_acell, f"{checkin_col}{row_num}", "FALSE")
    # Update cache directly
    user_tuple = list(user_tuple)
    user_tuple[0] = row_num
    user_tuple[3] = "FALSE"
    sheet_cache["users"][discord_tag] = tuple(user_tuple)
    return True

async def reset_registered_roles_and_sheet(guild, channel):
    registered_role = next((r for r in guild.roles if r.name == REGISTERED_ROLE), None)
    angel_role = next((r for r in guild.roles if r.name == ANGEL_ROLE), None)
    cleared = 0

    if registered_role:
        for member in guild.members:
            if registered_role in member.roles:
                cleared += 1
                await member.remove_roles(registered_role)

    if angel_role:
        overwrites = channel.overwrites_for(angel_role)
        overwrites.view_channel = False
        await channel.set_permissions(angel_role, overwrite=overwrites)

    guild_id = str(guild.id)
    mode = get_event_mode_for_guild(guild_id)
    reg_col_num    = 8 if mode == "doubleup" else 6
    reg_col_letter = "H" if mode == "doubleup" else "F"
    sheet = get_sheet_for_guild(guild_id, "GAL Database")
    f_values = await retry_until_successful(sheet.col_values, reg_col_num)
    new_f_values = []
    for idx, val in enumerate(f_values):
        if idx < 2:
            new_f_values.append(val)
        else:
            new_f_values.append(False)
    cell_range = f"{reg_col_letter}1:{reg_col_letter}{len(new_f_values)}"
    cell_list = sheet.range(cell_range)
    for cell, new_val in zip(cell_list, new_f_values):
        cell.value = new_val
    await retry_until_successful(sheet.update_cells, cell_list)
    await refresh_sheet_cache()
    return cleared

async def reset_checked_in_roles_and_sheet(guild, channel):
    checked_in_role = next((r for r in guild.roles if r.name == CHECKED_IN_ROLE), None)
    registered_role = next((r for r in guild.roles if r.name == REGISTERED_ROLE), None)
    cleared = 0

    if checked_in_role:
        for member in guild.members:
            if checked_in_role in member.roles:
                cleared += 1
                await member.remove_roles(checked_in_role)

    if registered_role:
        overwrites = channel.overwrites_for(registered_role)
        overwrites.view_channel = False
        await channel.set_permissions(registered_role, overwrite=overwrites)

    guild_id = str(guild.id)
    mode = get_event_mode_for_guild(guild_id)
    checkin_col_num    = 9 if mode == "doubleup" else 7
    checkin_col_letter = "I" if mode == "doubleup" else "G"
    sheet = get_sheet_for_guild(guild_id, "GAL Database")
    g_values = await retry_until_successful(sheet.col_values, checkin_col_num)
    new_g_values = []
    for idx, val in enumerate(g_values):
        if idx < 2:
            new_g_values.append(val)
        else:
            new_g_values.append(False)
    cell_range = f"{checkin_col_letter}1:{checkin_col_letter}{len(new_g_values)}"
    cell_list = sheet.range(cell_range)
    for cell, new_val in zip(cell_list, new_g_values):
        cell.value = new_val
    await retry_until_successful(sheet.update_cells, cell_list)
    await refresh_sheet_cache()
    return cleared

def get_next_empty_row(sheet):
    col_b = sheet.col_values(2)
    for i in range(2, len(col_b)):
        if not col_b[i].strip():
            return i + 1
    return len(col_b) + 1