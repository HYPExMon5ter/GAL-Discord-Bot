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

    # Try to find the user in cache
    user_tuple = sheet_cache["users"].get(discord_tag)
    if user_tuple:
        row_num = user_tuple[0]
    else:
        # Find the row in the sheet by discord_tag (B col)
        b_col = await retry_until_successful(sheet.col_values, 2)
        row_num = None
        for i in range(3, len(b_col) + 1):
            if b_col[i - 1].strip() == discord_tag:
                row_num = i
                break

    if user_tuple and row_num:
        # Update IGN if needed
        ign_col = await retry_until_successful(sheet.col_values, 4)
        if ign_col[row_num - 3] != ign:
            await retry_until_successful(sheet.update_acell, f"D{row_num}", ign)
        # Set registered to TRUE
        reg_col = "G" if mode == "doubleup" else "F"
        await retry_until_successful(sheet.update_acell, f"{reg_col}{row_num}", "TRUE")
        # Update team if in doubleup
        if mode == "doubleup" and team_name:
            await retry_until_successful(sheet.update_acell, f"E{row_num}", team_name)
        # Update cache directly
        reg_val = "TRUE"
        checkin_val = user_tuple[3] if len(user_tuple) > 3 else "FALSE"
        team_val = team_name if mode == "doubleup" else ""
        sheet_cache["users"][discord_tag] = (
            row_num, ign, reg_val, checkin_val, team_val
        )
        return row_num
    else:
        # Register new user (append row)
        values = [None] * 9  # Pad to last col
        values[1] = discord_tag  # B
        values[3] = ign  # D
        if mode == "doubleup":
            values[4] = team_name or ""  # E
            values[6] = "TRUE"  # G: Registered
            values[7] = "FALSE"  # H: Checked in
        else:
            values[5] = "TRUE"  # F: Registered
            values[6] = "FALSE"  # G: Checked in
        row = await retry_until_successful(sheet.append_row, values)
        # Find new row number
        b_col = await retry_until_successful(sheet.col_values, 2)
        row_num = len(b_col)
        reg_val = "TRUE"
        checkin_val = "FALSE"
        team_val = team_name if mode == "doubleup" else ""
        sheet_cache["users"][discord_tag] = (
            row_num, ign, reg_val, checkin_val, team_val
        )
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