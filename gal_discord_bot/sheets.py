# gal_discord_bot/sheets.py

import os
import json
import asyncio
import time
import random
import traceback
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import gspread

from gal_discord_bot.config import (
    SHEET_KEY, DOUBLEUP_SHEET_KEY,
    CACHE_REFRESH_SECONDS, REGISTERED_ROLE, CHECKED_IN_ROLE, ANGEL_ROLE,
    ALLOWED_ROLES
)
from gal_discord_bot.persistence import (
    get_event_mode_for_guild, set_event_mode_for_guild,
    get_schedule, set_schedule
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

def similar(a, b):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def ordinal_suffix(n):
    n = int(n)
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

async def refresh_sheet_cache(bot=None):
    global sheet_cache
    async with cache_lock:
        old_user_data = dict(sheet_cache["users"])

        # Choose correct guild for mode
        active_guild_id = None
        if bot and hasattr(bot, "guilds") and bot.guilds:
            active_guild_id = bot.guilds[0].id
        # For multi-guild support, you can loop over all bot.guilds and merge results

        mode = get_event_mode_for_guild(str(active_guild_id or SHEET_KEY))
        sheet = get_sheet_for_guild(active_guild_id or SHEET_KEY, "GAL Database")
        discord_col = await retry_until_successful(sheet.col_values, 2)
        ign_col = await retry_until_successful(sheet.col_values, 4)

        team_col = []
        if mode == "doubleup":
            try:
                team_col = await retry_until_successful(sheet.col_values, 5)
                team_col = team_col[2:]  # skip headers
            except Exception:
                team_col = []
        else:
            team_col = []

        registered_col_num = 7 if mode == "doubleup" else 6
        checkedin_col_num = 8 if mode == "doubleup" else 7
        registered_col = await retry_until_successful(sheet.col_values, registered_col_num)
        checkedin_col = await retry_until_successful(sheet.col_values, checkedin_col_num)
        discord_col = discord_col[2:]  # skip headers
        ign_col = ign_col[2:]
        registered_col = registered_col[2:]
        checkedin_col = checkedin_col[2:]

        row_map = {}
        for idx, tag in enumerate(discord_col, start=3):
            if tag and tag.strip():
                ign = ign_col[idx - 3].strip() if idx - 3 < len(ign_col) else ""
                reg = registered_col[idx - 3].strip() if idx - 3 < len(registered_col) else ""
                checkin = checkedin_col[idx - 3].strip() if idx - 3 < len(checkedin_col) else ""
                if mode == "doubleup":
                    team = team_col[idx - 3].strip() if idx - 3 < len(team_col) else ""
                else:
                    team = ""
                row_map[tag.strip()] = (idx, ign, reg, checkin, team)

        # Detect changes
        old_tags = set(old_user_data.keys())
        new_tags = set(row_map.keys())
        added = new_tags - old_tags
        removed = old_tags - new_tags
        updated = set()
        for tag in (new_tags & old_tags):
            if row_map[tag] != old_user_data[tag]:
                updated.add(tag)

        # Store new cache
        sheet_cache["users"] = row_map
        sheet_cache["last_refresh"] = time.time()
        total_changes = len(added) + len(removed) + len(updated)
    return total_changes, len(row_map)

async def cache_refresh_loop(bot):
    while True:
        try:
            await refresh_sheet_cache(bot=bot)
        except Exception:
            pass
        await asyncio.sleep(CACHE_REFRESH_SECONDS)

async def find_or_register_user(discord_tag, ign, guild_id=None, team_name=None):
    global sheet_cache
    if not guild_id:
        guild_id = str(SHEET_KEY)
    mode = get_event_mode_for_guild(guild_id)
    sheet = get_sheet_for_guild(guild_id, "GAL Database")
    b_col = await retry_until_successful(sheet.col_values, 2)
    row_num = None
    # 1. Check if user exists
    for i in range(3, len(b_col) + 1):
        val = b_col[i - 1] if i - 1 < len(b_col) else ""
        if val.strip() == discord_tag:
            row_num = i
            break
    # 2. If not, find first empty row
    if not row_num:
        for i in range(3, len(b_col) + 2):
            val = b_col[i - 1] if i - 1 < len(b_col) else ""
            if not val.strip():
                row_num = i
                break
    if not row_num:
        row_num = len(b_col) + 1

    # Update cells
    await retry_until_successful(sheet.update_acell, f"B{row_num}", discord_tag)
    await retry_until_successful(sheet.update_acell, f"D{row_num}", ign)
    if mode == "doubleup" and team_name:
        await retry_until_successful(sheet.update_acell, f"E{row_num}", team_name)
    reg_col = "G" if mode == "doubleup" else "F"
    await retry_until_successful(sheet.update_acell, f"{reg_col}{row_num}", "TRUE")

    # Update cache: (row, ign, reg, checkin, team)
    team = team_name if (mode == "doubleup" and team_name) else ""
    sheet_cache["users"][discord_tag] = (row_num, ign, "TRUE", "FALSE", team)
    return row_num

async def unregister_user(discord_tag, guild_id=None):
    global sheet_cache
    user_tuple = sheet_cache["users"].get(discord_tag)
    if not user_tuple:
        return False
    row_num = user_tuple[0]
    if not guild_id:
        guild_id = str(SHEET_KEY)
    mode = get_event_mode_for_guild(guild_id)
    reg_col = "G" if mode == "doubleup" else "F"
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
    # Update cache
    user_tuple = list(user_tuple)
    user_tuple[0] = row_num
    user_tuple[2] = "FALSE"
    user_tuple[3] = "FALSE"
    sheet_cache["users"][discord_tag] = tuple(user_tuple)
    return True

async def mark_checked_in_async(discord_tag, guild_id=None):
    global sheet_cache
    user_tuple = sheet_cache["users"].get(discord_tag)
    if not user_tuple:
        raise Exception("User not found in cache.")
    row_num = user_tuple[0]
    if not guild_id:
        guild_id = str(SHEET_KEY)
    mode = get_event_mode_for_guild(guild_id)
    checkin_col = "H" if mode == "doubleup" else "G"
    sheet = get_sheet_for_guild(guild_id, "GAL Database")
    cell = await retry_until_successful(sheet.acell, f"B{row_num}")
    if not cell.value or cell.value.strip() != discord_tag:
        b_col = await retry_until_successful(sheet.col_values, 2)
        for i in range(3, len(b_col) + 1):
            if b_col[i - 1].strip() == discord_tag:
                row_num = i
                break
        else:
            raise Exception("User not found in sheet after re-scan.")

    await retry_until_successful(sheet.update_acell, f"{checkin_col}{row_num}", "TRUE")
    # Update cache
    user_tuple = list(user_tuple)
    user_tuple[0] = row_num
    user_tuple[3] = "TRUE"
    sheet_cache["users"][discord_tag] = tuple(user_tuple)

async def unmark_checked_in_async(discord_tag, guild_id=None):
    global sheet_cache
    user_tuple = sheet_cache["users"].get(discord_tag)
    if user_tuple:
        row_num = user_tuple[0]
        if not guild_id:
            guild_id = str(SHEET_KEY)
        mode = get_event_mode_for_guild(guild_id)
        checkin_col = "H" if mode == "doubleup" else "G"
        sheet = get_sheet_for_guild(guild_id, "GAL Database")
        cell = await retry_until_successful(sheet.acell, f"B{row_num}")
        if not cell.value or cell.value.strip() != discord_tag:
            b_col = await retry_until_successful(sheet.col_values, 2)
            for i in range(3, len(b_col) + 1):
                if b_col[i - 1].strip() == discord_tag:
                    row_num = i
                    break
            else:
                return
        await retry_until_successful(sheet.update_acell, f"{checkin_col}{row_num}", "FALSE")
        # Update cache
        user_tuple = list(user_tuple)
        user_tuple[0] = row_num
        user_tuple[3] = "FALSE"
        sheet_cache["users"][discord_tag] = tuple(user_tuple)

async def reset_registered_roles_and_sheet(guild, channel):
    from gal_discord_bot.config import REGISTERED_ROLE, ANGEL_ROLE
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
    reg_col_num = 7 if mode == "doubleup" else 6
    reg_col_letter = "G" if mode == "doubleup" else "F"
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
    from gal_discord_bot.config import CHECKED_IN_ROLE, REGISTERED_ROLE
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
    checkin_col_num = 8 if mode == "doubleup" else 7
    checkin_col_letter = "H" if mode == "doubleup" else "G"
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

def find_team_row_in_checkin(sheet, team_name, threshold=0.90):
    team_names = sheet.col_values(2)[2:]
    for idx, existing in enumerate(team_names, start=3):
        if existing and similar(existing, team_name) >= threshold:
            return idx
    return None

async def sync_teams_with_checkin(guild):
    sheet = get_sheet_for_guild(guild.id, "GAL Database")
    checkin_sheet = get_sheet_for_guild(guild.id, "Check-In")
    data = sheet.get_all_values()
    teams = {}
    for row in data[2:]:
        discord_tag = row[1] if len(row) > 1 else ""
        ign = row[3] if len(row) > 3 else ""
        team_name = row[4] if len(row) > 4 else ""
        reg = row[6] if len(row) > 6 else ""
        checkin = row[7] if len(row) > 7 else ""
        if team_name.strip() and reg.strip().upper() == "TRUE":
            norm_team = team_name.lower().strip()
            if norm_team not in teams:
                teams[norm_team] = []
            teams[norm_team].append((ign, discord_tag, checkin))
    checkin_sheet.batch_clear(['B3:J20'])
    idx = 3
    for team, members in teams.items():
        if len(members) < 2:
            continue
        row_vals = [""] * 10
        row_vals[1] = team
        if len(members) > 0:
            row_vals[2] = members[0][0]
            row_vals[4] = members[0][1]
            row_vals[5] = members[0][2]
        if len(members) > 1:
            row_vals[6] = members[1][0]
            row_vals[8] = members[1][1]
            row_vals[9] = members[1][2]
        checkin_sheet.update(f"B{idx}:J{idx}", [row_vals[1:]])
        idx += 1