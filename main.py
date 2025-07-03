import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import yaml
import json
import asyncio
import random
import time
import traceback
from datetime import datetime, UTC, timezone
from zoneinfo import ZoneInfo
import requests

# --- Embed Configuration Loader ---
def hex_to_color(hex_str):
    return discord.Color(int(hex_str.replace("#", ""), 16))

def load_embeds_cfg():
    with open("embeds.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

EMBEDS_CFG = load_embeds_cfg()

def embed_from_cfg(key, **kwargs):
    cfg = EMBEDS_CFG.get(key, {})
    title = cfg.get("title", "").format(**kwargs)
    desc = cfg.get("description", "").format(**kwargs)
    if not desc:
        desc = "\u200b"  # Zero-width space, keeps Discord happy for "empty" desc
    color = hex_to_color(cfg.get("color", "#3498db"))
    return discord.Embed(title=title, description=desc, color=color)

# --- Configuration ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Y_NBCYSJvYs3j_xD8IivMU5EdAbTMNAtsU40g7bCQzg/edit"
SHEET_KEY = SHEET_URL.split("/d/")[1].split("/")[0]
SHEETS_BASE_DELAY = 1.0
MAX_DELAY = 90
FULL_BACKOFF = 60

CACHE_REFRESH_SECONDS = 600  # 10 min
PERSIST_FILE = "persisted_views.json"
ALLOWED_ROLES = ["Admin", "Moderator", "GAL Helper"]
CHECK_IN_CHANNEL = "✔check-in"
REGISTRATION_CHANNEL = "🎫registration"
CHECKED_IN_ROLE = "Checked In"
REGISTERED_ROLE = "Registered"
ANGEL_ROLE = "Angels"
LOG_CHANNEL_NAME = "bot-log"
PING_USER = "<@162359821100646401>"

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if os.path.exists("google-creds.json"):
    # Local file exists, use it
    creds = ServiceAccountCredentials.from_json_keyfile_name("google-creds.json", scope)
else:
    # Use Railway environment variable
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise RuntimeError("Missing google-creds.json file AND GOOGLE_CREDS_JSON environment variable!")
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_KEY).worksheet("GAL Database")

# --- Bot Setup ---
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logging.basicConfig(level=logging.INFO, handlers=[handler])
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=None, intents=intents)
tree = bot.tree

RIOT_API_KEY = os.environ.get("RIOT_API_KEY")

def ordinal_suffix(n):
    n = int(n)
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

# --- Persistent State (for message IDs) ---
def load_persisted():
    try:
        with open(PERSIST_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_persisted(data):
    with open(PERSIST_FILE, "w") as f:
        json.dump(data, f, indent=2)

persisted = load_persisted()
def set_persisted_msg(guild_id, key, msg_id):
    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}
    persisted[gid][key] = msg_id
    save_persisted(persisted)
def get_persisted_msg(guild_id, key):
    return persisted.get(str(guild_id), {}).get(key)

def get_schedule(guild_id, key):
    data = persisted.get(str(guild_id), {})
    return data.get(f"{key}_schedule")

def set_schedule(guild_id, key, dtstr):
    gid = str(guild_id)
    if gid not in persisted:
        persisted[gid] = {}
    persisted[gid][f"{key}_schedule"] = dtstr
    save_persisted(persisted)

async def schedule_channel_open(guild, channel_name, role_name, open_time):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    wait_seconds = (open_time - now).total_seconds()
    print(
        f"[Schedule] Now (UTC): {now.isoformat()} | Scheduled (UTC): {open_time.isoformat()} | Wait: {wait_seconds:.2f}s"
    )
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
    else:
        print("[Schedule] Warning: Scheduled time is in the past or now! Channel will open immediately.")

    channel = discord.utils.get(guild.text_channels, name=channel_name)
    role = discord.utils.get(guild.roles, name=role_name)
    if channel and role:
        overwrites = channel.overwrites_for(role)
        overwrites.view_channel = True
        await channel.set_permissions(role, overwrite=overwrites)
        print(f"[Schedule] Channel '{channel_name}' opened for role '{role_name}'.")
        await update_live_embeds(guild)

        # --- CLEAR THE SCHEDULE ---
        key = "registration" if channel_name == REGISTRATION_CHANNEL else "checkin"
        set_schedule(guild.id, key, None)

# --- Permissions ---
def has_allowed_role(member):
    return any(role.name in ALLOWED_ROLES for role in getattr(member, "roles", []))
def has_allowed_role_from_interaction(interaction: discord.Interaction):
    member = getattr(interaction, "user", getattr(interaction, "author", None))
    return hasattr(member, "roles") and has_allowed_role(member)

# --- Logging ---
async def log_error(bot, guild, message, level="Error"):
    log_channel = None
    if guild:
        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    embed = embed_from_cfg("error")
    embed.description = message
    embed.timestamp = datetime.now(UTC)
    embed.set_footer(text="GAL Bot")
    if log_channel:
        await log_channel.send(content=PING_USER if level == "Error" else None, embed=embed)
    else:
        logging.error(message)

# --- Pin Message Cleanup ---
async def delete_recent_pin_message(channel):
    async for msg in channel.history(limit=4):
        if msg.type == discord.MessageType.pins_add:
            try:
                await msg.delete()
            except Exception:
                pass
            break

# --- Rate-limited Google Sheets Calls ---
async def retry_until_successful(fn, *args, **kwargs):
    global SHEETS_BASE_DELAY
    delay = SHEETS_BASE_DELAY
    attempts = 0
    while True:
        try:
            result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
            if delay > SHEETS_BASE_DELAY:
                logging.warning(f"Success at delay {delay:.2f}s. Lowering SHEETS_BASE_DELAY to this value.")
                SHEETS_BASE_DELAY = delay
            return result
        except Exception as e:
            err_str = str(e)
            attempts += 1
            if "429" in err_str or "quota" in err_str.lower():
                if delay >= 30 or attempts > 3:
                    logging.warning(f"Still hitting quota (429). Waiting full {FULL_BACKOFF} seconds for quota to reset.")
                    await asyncio.sleep(FULL_BACKOFF + random.uniform(0, 3))
                    delay = FULL_BACKOFF
                else:
                    logging.warning(f"Quota error: {e}. Backing off for {delay:.2f} seconds.")
                    await asyncio.sleep(delay + random.uniform(0, 0.4))
                    delay = min(delay * 2, MAX_DELAY)
            else:
                logging.error(f"Non-quota error in retry_until_successful:\n{traceback.format_exc()}")
                raise

# --- Google Sheets Caching ---
sheet_cache = {"users": {}, "last_refresh": 0}
cache_lock = asyncio.Lock()

async def refresh_sheet_cache():
    global sheet_cache
    async with cache_lock:
        old_user_data = dict(sheet_cache["users"])  # tag -> (row, ign, reg, checkin)
        # Pull columns B (discord tag), D (ign), F (registered), G (checked in)
        discord_col = await retry_until_successful(sheet.col_values, 2)
        ign_col = await retry_until_successful(sheet.col_values, 4)
        registered_col = await retry_until_successful(sheet.col_values, 6)
        checkedin_col = await retry_until_successful(sheet.col_values, 7)
        # Skip headers (first 2 rows)
        discord_col = discord_col[2:]
        ign_col = ign_col[2:]
        registered_col = registered_col[2:]
        checkedin_col = checkedin_col[2:]
        row_map = {}
        for idx, tag in enumerate(discord_col, start=3):
            if tag and tag.strip():
                ign = ign_col[idx-3].strip() if idx-3 < len(ign_col) else ""
                reg = registered_col[idx-3].strip() if idx-3 < len(registered_col) else ""
                checkin = checkedin_col[idx-3].strip() if idx-3 < len(checkedin_col) else ""
                row_map[tag.strip()] = (idx, ign, reg, checkin)
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

async def cache_refresh_loop():
    while True:
        try:
            await refresh_sheet_cache()
        except Exception as e:
            logging.error(f"Error refreshing sheet cache: {e}")
        await asyncio.sleep(CACHE_REFRESH_SECONDS)  # 10 min

# --- Smart Registration Logic: windowed cache with fallback ---
async def find_or_register_user(discord_tag, ign, search_window=5, scan_tail=20):
    async with cache_lock:
        user_tuple = sheet_cache["users"].get(discord_tag)
    if user_tuple:
        row_num = int(user_tuple[0])
        cell = await retry_until_successful(sheet.acell, f"B{row_num}")
        if cell.value and cell.value.strip() == discord_tag:
            await retry_until_successful(sheet.update_acell, f"F{row_num}", True)
            return
        # Search window in case the cache is off by a few lines
        for offset in range(-search_window, search_window + 1):
            check_row = row_num + offset
            if check_row < 3:
                continue
            cell = await retry_until_successful(sheet.acell, f"B{check_row}")
            if cell.value and cell.value.strip() == discord_tag:
                await retry_until_successful(sheet.update_acell, f"F{check_row}", True)
                return
    # Scan the tail of the sheet (in case new user was just added)
    b_col = await retry_until_successful(sheet.col_values, 2)
    start_row = max(3, len(b_col) - scan_tail + 1)
    for i in range(start_row, len(b_col) + 1):
        val = b_col[i - 1] if i - 1 < len(b_col) else ""
        if val.strip() == discord_tag:
            await retry_until_successful(sheet.update_acell, f"F{i}", True)
            return
    # Find the first empty row
    for i in range(3, len(b_col) + 2):
        val = b_col[i - 1] if i - 1 < len(b_col) else ""
        if not val.strip():
            await retry_until_successful(sheet.update_acell, f"B{i}", discord_tag)
            await retry_until_successful(sheet.update_acell, f"D{i}", ign)
            await retry_until_successful(sheet.update_acell, f"F{i}", True)
            asyncio.create_task(refresh_sheet_cache())
            return
    # If somehow all are filled, append at the very end
    i = len(b_col) + 1
    await retry_until_successful(sheet.update_acell, f"B{i}", discord_tag)
    await retry_until_successful(sheet.update_acell, f"D{i}", ign)
    await retry_until_successful(sheet.update_acell, f"F{i}", True)
    asyncio.create_task(refresh_sheet_cache())

def is_registration_open(guild):
    reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
    angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
    if reg_channel and angel_role:
        overwrites = reg_channel.overwrites_for(angel_role)
        return bool(overwrites.view_channel)
    return False

def is_checkin_open(guild):
    checkin_channel = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
    registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
    if checkin_channel and registered_role:
        overwrites = checkin_channel.overwrites_for(registered_role)
        return bool(overwrites.view_channel)
    return False

async def mark_checked_in_async(discord_tag):
    user_tuple = sheet_cache["users"].get(discord_tag)
    if not user_tuple:
        raise Exception("User not found in cache.")
    row_num = user_tuple[0]  # row number as integer or string (should be int or cast to int)
    await retry_until_successful(sheet.update_acell, f"G{row_num}", "TRUE")
    # And update your cache too if needed:
    async with cache_lock:
        sheet_cache["users"][discord_tag] = (
            row_num,
            user_tuple[1],  # ign
            user_tuple[2],  # registered
            "TRUE",         # checked_in now TRUE
        )

async def unmark_checked_in_async(discord_tag):
    async with cache_lock:
        user_tuple = sheet_cache["users"].get(discord_tag)
    if user_tuple:
        row_num = user_tuple[0]
        # Confirm cell B at row_num matches discord_tag
        cell = await retry_until_successful(sheet.acell, f"B{row_num}")
        if cell.value and cell.value.strip() == discord_tag:
            await retry_until_successful(sheet.update_acell, f"G{row_num}", "FALSE")
            # Also update cache
            async with cache_lock:
                sheet_cache["users"][discord_tag] = (
                    row_num,
                    user_tuple[1],      # IGN
                    user_tuple[2],      # Registered
                    "FALSE",            # Checked in now FALSE
                )
        else:
            await log_error(bot, None, f"Discord tag {discord_tag} not found at cached row {row_num}, skipping uncheck-in (tag changed/removed).")
    else:
        await log_error(bot, None, f"Discord tag {discord_tag} not found in cache, skipping uncheck-in.")

# --- Registration/Check-in reset logic (efficient: only update checked users) ---
async def reset_registered_roles_and_sheet(guild, channel):
    registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
    angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
    cleared = 0

    # Remove Registered role from all members
    if registered_role:
        for member in guild.members:
            if registered_role in member.roles:
                cleared += 1
                await member.remove_roles(registered_role)

    # Hide registration channel from Angels
    if angel_role:
        overwrites = channel.overwrites_for(angel_role)
        overwrites.view_channel = False
        await channel.set_permissions(angel_role, overwrite=overwrites)

    # Full column reset: set every entry (except header) to boolean False (preserves checkboxes)
    f_values = await retry_until_successful(sheet.col_values, 6)  # Column F
    new_f_values = []
    for idx, val in enumerate(f_values):
        if idx < 2:
            new_f_values.append(val)  # header
        else:
            new_f_values.append(False)  # <--- Set as boolean False

    cell_range = f"F1:F{len(new_f_values)}"
    cell_list = sheet.range(cell_range)
    for cell, new_val in zip(cell_list, new_f_values):
        cell.value = new_val
    await retry_until_successful(sheet.update_cells, cell_list)

    await refresh_sheet_cache()
    return cleared

async def reset_checked_in_roles_and_sheet(guild, channel):
    checked_in_role = discord.utils.get(guild.roles, name=CHECKED_IN_ROLE)
    registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
    cleared = 0

    # Remove Checked-In role from all members
    if checked_in_role:
        for member in guild.members:
            if checked_in_role in member.roles:
                cleared += 1
                await member.remove_roles(checked_in_role)

    # Hide check-in channel from Registered users
    if registered_role:
        overwrites = channel.overwrites_for(registered_role)
        overwrites.view_channel = False
        await channel.set_permissions(registered_role, overwrite=overwrites)

    # Full column reset: set every entry (except header) to boolean False (preserves checkboxes)
    g_values = await retry_until_successful(sheet.col_values, 7)
    new_g_values = []
    for idx, val in enumerate(g_values):
        if idx < 2:
            new_g_values.append(val)
        else:
            new_g_values.append(False)  # <--- This is the key!

    cell_range = f"G1:G{len(new_g_values)}"
    cell_list = sheet.range(cell_range)
    for cell, new_val in zip(cell_list, new_g_values):
        cell.value = new_val
    await retry_until_successful(sheet.update_cells, cell_list)

    await refresh_sheet_cache()
    return cleared

# --- TFT API: Get PUUID by summoner name (no #tag) ---
def get_tft_puuid_from_summoner_name(api_key, ign, region="na1"):
    name_enc = ign.replace(" ", "%20")
    url = f"https://{region}.api.riotgames.com/tft/summoner/v1/summoners/by-name/{name_enc}"
    headers = {"X-Riot-Token": api_key}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()["puuid"]
    else:
        return None

# --- TFT API: Get latest placement by PUUID ---
def get_tft_latest_placement(api_key, puuid, region="americas"):
    url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count=1"
    headers = {"X-Riot-Token": api_key}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        match_ids = resp.json()
        if not match_ids:
            return "No Recent Games"
        match_id = match_ids[0]
        url2 = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        resp2 = requests.get(url2, headers=headers)
        if resp2.status_code == 200:
            match = resp2.json()
            for participant in match["info"]["participants"]:
                if participant["puuid"] == puuid:
                    return f"{participant['placement']}{ordinal_suffix(participant['placement'])}"
            return "Not Found"
        else:
            return f"Error: {resp2.status_code}"
    else:
        return f"Error: {resp.status_code}"

async def _schedule_logic(interaction, key, channel_name, role_name, time):
    await interaction.response.defer(ephemeral=True)
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    guild = interaction.guild
    PST = ZoneInfo("America/Los_Angeles")
    time_format = "%m-%d-%y %I:%M %p"  # 07-08-25 05:03 PM

    if time is None:
        scheduled_iso = get_schedule(guild.id, key)
        if scheduled_iso:
            scheduled_dt = datetime.fromisoformat(scheduled_iso).astimezone(PST)
            embed = embed_from_cfg(
                "schedule_status",
                role=key.capitalize() if key != "checkin" else "Check-in",
                time=scheduled_dt.strftime(time_format) + " PST",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = embed_from_cfg("schedule_usage", role=key.capitalize() if key != "checkin" else "Check-in")
            await interaction.followup.send(embed=embed, ephemeral=True)
        return
    try:
        scheduled_pst = datetime.strptime(time, time_format).replace(tzinfo=PST)
        scheduled_utc = scheduled_pst.astimezone(ZoneInfo("UTC"))
        now_utc = datetime.now(ZoneInfo("UTC"))
        if scheduled_utc < now_utc:
            embed = embed_from_cfg("schedule_usage", role=key.capitalize() if key != "checkin" else "Check-in")
            embed.description += "\n\n❌ Cannot schedule a time in the past. Please provide a future time."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        set_schedule(guild.id, key, scheduled_utc.isoformat())
        embed = embed_from_cfg(
            "schedule_set",
            role=key.capitalize() if key != "checkin" else "Check-in",
            time=scheduled_pst.strftime(time_format) + " PST",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        bot.loop.create_task(schedule_channel_open(guild, channel_name, role_name, scheduled_utc))
    except Exception as e:
        embed = embed_from_cfg("schedule_usage", role=key.capitalize() if key != "checkin" else "Check-in")
        embed.description += f"\n\nError: {e}"
        await interaction.followup.send(embed=embed, ephemeral=True)

async def _cancel_schedule_logic(interaction, key):
    await interaction.response.defer(ephemeral=True)
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    guild = interaction.guild
    scheduled_iso = get_schedule(guild.id, key)
    if scheduled_iso:
        set_schedule(guild.id, key, None)
        embed = embed_from_cfg("schedule_cancel", role=key.capitalize() if key != "checkin" else "Check-in")
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        embed = embed_from_cfg("schedule_cancel_none", role=key.capitalize() if key != "checkin" else "Check-in")
        await interaction.followup.send(embed=embed, ephemeral=True)

# --- Embed updating for live messages (config reload support) ---
async def update_live_embeds(guild):
    # --- Registration Embed ---
    reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
    reg_msg_id = get_persisted_msg(guild.id, "registration")
    if reg_channel and reg_msg_id:
        try:
            await update_registration_embed(reg_channel, reg_msg_id, guild)
        except Exception as e:
            await log_error(bot, guild, f"Failed to update registration embed: {e}")

    # --- Check-in Embed ---
    checkin_channel = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
    checkin_msg_id = get_persisted_msg(guild.id, "checkin")
    if checkin_channel and checkin_msg_id:
        try:
            await update_checkin_embed(checkin_channel, checkin_msg_id, guild)
        except Exception as e:
            await log_error(bot, guild, f"Failed to update check-in embed: {e}")

# --- Persistent Views with custom_id! ---
class CheckInButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Check in!",
            style=discord.ButtonStyle.green,
            emoji="✅",
            custom_id="checkin_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        check_in_channel = interaction.channel
        registered_role = discord.utils.get(interaction.guild.roles, name=REGISTERED_ROLE)
        if not registered_role:
            embed = embed_from_cfg("error")
            embed.description = f"Role '{REGISTERED_ROLE}' not found."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        overwrites = check_in_channel.overwrites_for(registered_role)
        if not overwrites.view_channel:
            embed = embed_from_cfg("checkin_disabled")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        member = interaction.user
        discord_tag = str(member)
        async with cache_lock:
            user_exists = discord_tag in sheet_cache["users"]
        if not user_exists:
            embed = embed_from_cfg("checkin_requires_registration")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        role = discord.utils.get(interaction.guild.roles, name=CHECKED_IN_ROLE)
        if not role:
            embed = embed_from_cfg("error")
            embed.description = f"Role '{CHECKED_IN_ROLE}' not found."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # All checks passed
        await interaction.response.defer(ephemeral=True)
        try:
            if role in member.roles:
                await member.remove_roles(role)
                try:
                    await unmark_checked_in_async(discord_tag)
                except Exception as e:
                    await log_error(bot, interaction.guild, f"Uncheck-in button error: {e}")
                embed = embed_from_cfg("checked_out")
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await member.add_roles(role)
                try:
                    await mark_checked_in_async(discord_tag)
                except Exception as e:
                    await log_error(bot, interaction.guild, f"Check-in button error: {e}")
                embed = embed_from_cfg("checked_in")
                await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await log_error(bot, interaction.guild, f"Check-in button error: {e}")
            if not interaction.response.is_done():
                error_embed = embed_from_cfg("error")
                error_embed.description = f"An error occurred during check-in: {e}"
                await interaction.followup.send(embed=error_embed, ephemeral=True)

class ResetCheckInsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Reset",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            custom_id="reset_checkin_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_allowed_role(interaction.user):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        checked_in_role = discord.utils.get(interaction.guild.roles, name=CHECKED_IN_ROLE)
        cleared_count = 0
        if checked_in_role:
            for member in interaction.guild.members:
                if checked_in_role in member.roles:
                    cleared_count += 1
        embed_start = embed_from_cfg("resetting", count=cleared_count, role="checked-in")
        await interaction.followup.send(embed=embed_start, ephemeral=True)
        start_time = time.perf_counter()
        check_in_channel = discord.utils.get(interaction.guild.text_channels, name=CHECK_IN_CHANNEL)
        actual_cleared = await reset_checked_in_roles_and_sheet(interaction.guild, check_in_channel)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        embed_done = embed_from_cfg("reset_complete", role="Check-in", count=actual_cleared, elapsed=elapsed)
        # Update live embed and view after reset
        await update_live_embeds(interaction.guild)
        await interaction.followup.send(embed=embed_done, ephemeral=True)

class CheckInView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        if is_checkin_open(guild):
            self.add_item(CheckInButton())
        self.add_item(ResetCheckInsButton())

async def update_checkin_embed(channel, msg_id, guild):
    is_open = is_checkin_open(guild)
    checkin_msg = await channel.fetch_message(msg_id)
    cfg = EMBEDS_CFG.get("checkin", {})
    closed_cfg = EMBEDS_CFG.get("checkin_closed", {})
    if is_open:
        embed = discord.Embed(
            title=cfg.get("title"),
            color=hex_to_color(cfg.get("color", "#3498db")),
        )
    else:
        embed = discord.Embed(
            title=closed_cfg.get("title", "Check-in Closed"),
            description=closed_cfg.get("description", "Check-in is currently closed."),
            color=hex_to_color(closed_cfg.get("color", "#e67e22")),
        )
    await checkin_msg.edit(embed=embed, view=CheckInView(guild))

class ResetRegistrationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Reset",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            custom_id="reset_registration_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_allowed_role(interaction.user):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        registered_role = discord.utils.get(interaction.guild.roles, name=REGISTERED_ROLE)
        cleared_count = 0
        if registered_role:
            for member in interaction.guild.members:
                if registered_role in member.roles:
                    cleared_count += 1
        embed_start = embed_from_cfg("resetting", count=cleared_count, role="registered")
        await interaction.followup.send(embed=embed_start, ephemeral=True)
        start_time = time.perf_counter()
        registration_channel = discord.utils.get(interaction.guild.text_channels, name=REGISTRATION_CHANNEL)
        actual_cleared = await reset_registered_roles_and_sheet(
            interaction.guild, registration_channel
        )

        # Delete all user messages in registration channel except the persistent embed
        reg_embed_msg_id = get_persisted_msg(interaction.guild.id, "registration")
        if registration_channel is not None:
            async for msg in registration_channel.history(limit=200):
                if (msg.id != reg_embed_msg_id) and (not msg.author.bot):
                    try:
                        await msg.delete()
                    except Exception:
                        pass

        end_time = time.perf_counter()
        elapsed = end_time - start_time
        embed_done = embed_from_cfg("reset_complete", role="Registration", count=actual_cleared, elapsed=elapsed)
        await update_live_embeds(interaction.guild)
        await interaction.followup.send(embed=embed_done, ephemeral=True)

class UnregisterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Unregister",
            style=discord.ButtonStyle.secondary,
            emoji="🚫",
            custom_id="unregister_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
        registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        discord_tag = str(member)

        # Check if user is registered
        async with cache_lock:
            user_tuple = sheet_cache["users"].get(discord_tag)
        if not user_tuple or not (user_tuple[2].upper() == "TRUE"):
            embed = embed_from_cfg("unregister_not_registered")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Remove Registered role
        if registered_role and registered_role in member.roles:
            await member.remove_roles(registered_role)

        # Update sheet: set Registered to FALSE
        row_num = user_tuple[0]
        await retry_until_successful(sheet.update_acell, f"F{row_num}", False)
        # Update cache
        async with cache_lock:
            sheet_cache["users"][discord_tag] = (
                row_num,
                user_tuple[1],   # IGN
                "FALSE",         # Registered now FALSE
                user_tuple[3],   # Checked In
            )

        # Delete user's messages in registration channel
        if reg_channel:
            async for msg in reg_channel.history(limit=200):
                if msg.author.id == member.id and not msg.author.bot:
                    try:
                        await msg.delete()
                    except Exception:
                        pass

        embed = embed_from_cfg("unregister_success")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RegistrationView(discord.ui.View):
    def __init__(self, embed_message_id, guild):
        super().__init__(timeout=None)
        self.embed_message_id = embed_message_id
        if is_registration_open(guild):
            self.add_item(UnregisterButton())
        self.add_item(ResetRegistrationButton())

async def update_registration_embed(channel, msg_id, guild):
    is_open = is_registration_open(guild)
    reg_msg = await channel.fetch_message(msg_id)
    if is_open:
        embed = embed_from_cfg("registration")
    else:
        embed = embed_from_cfg("registration_closed")
    await reg_msg.edit(embed=embed, view=RegistrationView(msg_id, guild))

# --- Slash command group ---
class GalGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="gal", description="Group of GAL bot commands")
gal = GalGroup()
tree.add_command(gal)

@gal.command(name="reg", description="Toggles the registration channel for Angels and updates the registration embed.")
@app_commands.checks.has_any_role(*ALLOWED_ROLES)
async def reg(interaction: discord.Interaction):
    guild = interaction.guild
    registration_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
    angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
    if not registration_channel or not angel_role:
        embed = embed_from_cfg("error")
        embed.description = "Registration channel or Angels role not found."
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    overwrites = registration_channel.overwrites_for(angel_role)
    is_visible = overwrites.view_channel if overwrites.view_channel is not None else False

    # Toggle visibility
    overwrites.view_channel = not is_visible
    await registration_channel.set_permissions(angel_role, overwrite=overwrites)

    # Update the registration embed and view
    reg_msg_id = get_persisted_msg(guild.id, "registration")
    if reg_msg_id:
        await update_registration_embed(registration_channel, reg_msg_id, guild)

    # Confirmation
    status_embed_cfg = EMBEDS_CFG.get("registration_channel_toggled", {})
    if not is_visible:
        # Now open
        embed = discord.Embed(
            title=status_embed_cfg.get("title", "Registration Channel Toggled"),
            description=status_embed_cfg.get("description_visible", "👁️ Registration channel is now visible to Angels."),
            color=hex_to_color(status_embed_cfg.get("color_visible", "#2ecc71"))
        )
    else:
        embed = discord.Embed(
            title=status_embed_cfg.get("title", "Registration Channel Toggled"),
            description=status_embed_cfg.get("description_hidden", "🙈 Registration channel has been hidden from Angels."),
            color=hex_to_color(status_embed_cfg.get("color_hidden", "#e67e22"))
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@gal.command(name="checkin", description="Toggles the check-in channel for Registered role and updates the check-in embed.")
@app_commands.checks.has_any_role(*ALLOWED_ROLES)
async def checkin(interaction: discord.Interaction):
    guild = interaction.guild
    check_in_channel = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
    registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
    if not check_in_channel or not registered_role:
        embed = embed_from_cfg("error")
        embed.description = "Check-in channel or Registered role not found."
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    overwrites = check_in_channel.overwrites_for(registered_role)
    is_visible = overwrites.view_channel if overwrites.view_channel is not None else False

    # Toggle visibility
    overwrites.view_channel = not is_visible
    await check_in_channel.set_permissions(registered_role, overwrite=overwrites)

    # Update the check-in embed and view
    checkin_msg_id = get_persisted_msg(guild.id, "checkin")
    if checkin_msg_id:
        await update_checkin_embed(check_in_channel, checkin_msg_id, guild)

    # Confirmation
    status_embed_cfg = EMBEDS_CFG.get("checkin_channel_toggled", {})
    if not is_visible:
        embed = discord.Embed(
            title=status_embed_cfg.get("title", "Check-in Channel Toggled"),
            description=status_embed_cfg.get("description_visible", "👁️ Check-in channel is now visible to Registered users."),
            color=hex_to_color(status_embed_cfg.get("color_visible", "#2ecc71"))
        )
    else:
        embed = discord.Embed(
            title=status_embed_cfg.get("title", "Check-in Channel Toggled"),
            description=status_embed_cfg.get("description_hidden", "🙈 Check-in channel has been hidden."),
            color=hex_to_color(status_embed_cfg.get("color_hidden", "#e67e22"))
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@gal.command(name="cache", description="Forces a manual refresh of the user cache from the Google Sheet.")
async def cache(interaction: discord.Interaction):
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    start_time = time.perf_counter()
    updated_users, total_users = await refresh_sheet_cache()
    elapsed = time.perf_counter() - start_time
    embed = embed_from_cfg(
        "cache",
        updated=updated_users,
        count=total_users,
        elapsed=elapsed
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Schedule command group for registration and check-in with cancel support ---
class ScheduleGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="schedule", description="Schedule registration/check-in opening times")

    # --- Registration schedule ---
    @app_commands.command(name="reg", description="Set/view the scheduled open time for registration (MM-DD-YY HH:MM AM/PM PST)")
    @app_commands.describe(time="Open time in MM-DD-YY HH:MM AM/PM format, PST (leave blank to view)")
    async def reg(self, interaction: discord.Interaction, time: str = None):
        await _schedule_logic(interaction, "registration", REGISTRATION_CHANNEL, ANGEL_ROLE, time)

    # --- Check-in schedule ---
    @app_commands.command(name="checkin", description="Set/view the scheduled open time for check-in (MM-DD-YY HH:MM AM/PM PST)")
    @app_commands.describe(time="Open time in MM-DD-YY HH:MM AM/PM format, PST (leave blank to view)")
    async def checkin(self, interaction: discord.Interaction, time: str = None):
        await _schedule_logic(interaction, "checkin", CHECK_IN_CHANNEL, REGISTERED_ROLE, time)

    # --- Cancel Registration schedule ---
    @app_commands.command(name="cancelreg", description="Cancel the scheduled registration open")
    async def cancelreg(self, interaction: discord.Interaction):
        await _cancel_schedule_logic(interaction, "registration")

    # --- Cancel Check-in schedule ---
    @app_commands.command(name="cancelcheckin", description="Cancel the scheduled check-in open")
    async def cancelcheckin(self, interaction: discord.Interaction):
        await _cancel_schedule_logic(interaction, "checkin")

# Register this group under /gal (add after tree.add_command(gal))
gal.add_command(ScheduleGroup())

@gal.command(name="help", description="Shows this help message.")
async def help_cmd(interaction: discord.Interaction):
    try:
        if not has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        cfg = EMBEDS_CFG.get("help", {})
        help_embed = discord.Embed(
            title=cfg.get("title", "GAL Bot Help"),
            description=cfg.get("description", ""),
            color=hex_to_color(cfg.get("color", "#7289da"))
        )
        for cmd, desc in cfg.get("commands", {}).items():
            help_embed.add_field(
                name=f"/gal {cmd}",
                value=desc,
                inline=False
            )
        await interaction.response.send_message(embed=help_embed, ephemeral=True)
    except Exception as e:
        if not interaction.response.is_done():
            embed = embed_from_cfg("error")
            embed.description = f"An error occurred in the help command: {e}"
            await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.error(f"/gal help error: {e}")

@gal.command(name="reload", description="Reloads the embeds config and updates live messages.")
async def reload_cmd(interaction: discord.Interaction):
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    global EMBEDS_CFG
    EMBEDS_CFG = load_embeds_cfg()
    for guild in bot.guilds:
        await update_live_embeds(guild)
    embed = discord.Embed(
        title="Config Reloaded",
        description="Embed configuration reloaded and live embeds updated!",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ----------- NEW: Validate IGNs command (TFT API only) --------------
@gal.command(name="validate", description="Validate all checked-in IGNs with Riot TFT API")
async def validate(interaction: discord.Interaction):
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    cfg = EMBEDS_CFG.get("validate", {})
    await interaction.response.defer(thinking=True, ephemeral=True)
    async with cache_lock:
        user_map = dict(sheet_cache["users"])
    g_values = await retry_until_successful(sheet.col_values, 7)
    d_values = await retry_until_successful(sheet.col_values, 4)

    checked_in_igns = []
    for discord_tag, row in user_map.items():
        if row <= len(g_values) and str(g_values[row-1]).lower() == "true":
            ign = d_values[row-1].strip() if row-1 < len(d_values) else None
            if ign:
                checked_in_igns.append(ign)

    if not checked_in_igns:
        embed = discord.Embed(
            title=cfg.get("no_players_title", "No checked-in players found."),
            description=cfg.get("no_players_description", "There are currently no checked-in users to validate."),
            color=hex_to_color(cfg.get("color_invalid", "#e67e22"))
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    valid = []
    invalid = []
    for ign in checked_in_igns:
        summ_name = ign.split("#")[0] if "#" in ign else ign
        puuid = get_tft_puuid_from_summoner_name(RIOT_API_KEY, summ_name)
        if puuid:
            valid.append(ign)
        else:
            invalid.append(f"{ign} (Not found)")

    color = hex_to_color(cfg.get("color_valid", "#2ecc71") if not invalid else cfg.get("color_invalid", "#e67e22"))
    embed = discord.Embed(
        title=cfg.get("title", "IGN Validation Results"),
        color=color
    )
    embed.add_field(
        name=cfg.get("valid_field", "✅ Valid IGNs"),
        value="\n".join(valid) if valid else cfg.get("valid_none", "None"),
        inline=False
    )
    embed.add_field(
        name=cfg.get("invalid_field", "❌ Invalid IGNs"),
        value="\n".join(invalid) if invalid else cfg.get("invalid_none", "None"),
        inline=False
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

# ----------- NEW: Placements command (TFT API only) --------------
@gal.command(name="placements", description="Show latest TFT placements for checked-in users using Riot TFT API.")
async def placements(interaction: discord.Interaction):
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    cfg = EMBEDS_CFG.get("placements", {})
    await interaction.response.defer(thinking=True, ephemeral=True)

    async with cache_lock:
        user_map = dict(sheet_cache["users"])
    g_values = await retry_until_successful(sheet.col_values, 7)
    d_values = await retry_until_successful(sheet.col_values, 4)

    checked_in_igns = []
    for discord_tag, row in user_map.items():
        if row <= len(g_values) and str(g_values[row-1]).lower() == "true":
            ign = d_values[row-1].strip() if row-1 < len(d_values) else None
            if ign:
                checked_in_igns.append(ign)

    if not checked_in_igns:
        embed = discord.Embed(
            title=cfg.get("title", "Checked-In Player Latest Placements"),
            description=cfg.get("no_players_description", "There are currently no checked-in users to report."),
            color=hex_to_color(cfg.get("color", "#3498db"))
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    placements_list = []
    for ign in checked_in_igns:
        summ_name = ign.split("#")[0] if "#" in ign else ign
        tag = "NA1"  # Or parse from IGN if you want to support other regions!
        puuid = get_tft_puuid_from_summoner_name(RIOT_API_KEY, summ_name, region="na1")
        if not puuid:
            placements_list.append((ign, "IGN not found", None))
            continue
        riot_region = "americas"
        placement = get_tft_latest_placement(RIOT_API_KEY, puuid, region=riot_region)
        placements_list.append((ign, placement, puuid))

    embed = discord.Embed(
        title=cfg.get("title", "Checked-In Player Latest Placements"),
        color=hex_to_color(cfg.get("color", "#3498db"))
    )
    for ign, place, puuid in placements_list:
        summ_name = ign.split("#")[0] if "#" in ign else ign
        profile_url = f"https://lolchess.gg/profile/na/{summ_name.replace(' ','')}/set14"
        embed.add_field(
            name=ign,
            value=f"[Lolchess Profile]({profile_url})\n{place}",
            inline=True
        )

    await interaction.followup.send(embed=embed, ephemeral=True)

# --- Update IGN in sheet on message edit (no registered.json logic) ---
@bot.event
async def on_message_edit(before, after):
    # Only react to edits in the registration channel, from non-bots, and non-empty messages
    if (
        after.channel.name != REGISTRATION_CHANNEL
        or after.author.bot
        or not after.content.strip()
    ):
        return

    discord_tag = str(after.author)
    new_ign = after.content.strip()
    msg = await after.channel.fetch_message(after.id)

    try:
        async with cache_lock:
            row_tuple = sheet_cache["users"].get(discord_tag)
        if row_tuple:
            row_num = row_tuple[0]  # The first value in your tuple is the row number!
            await retry_until_successful(sheet.update_acell, f"D{row_num}", new_ign)
            # Update cache with new IGN
            async with cache_lock:
                updated_tuple = (
                    row_tuple[0],
                    new_ign,
                    row_tuple[2],
                    row_tuple[3],
                )
                sheet_cache["users"][discord_tag] = updated_tuple
            await msg.clear_reactions()
            await msg.add_reaction("✅")
        else:
            await msg.clear_reactions()
            await msg.add_reaction("❌")
    except Exception as e:
        await log_error(bot, after.guild, f"Error updating IGN on edit: {e}")
        await msg.clear_reactions()
        await msg.add_reaction("❌")

# --- On ready: restore persistent views and launch cache loop ---
@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")
    bot.loop.create_task(cache_refresh_loop())
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    for guild in bot.guilds:
        # ... (existing embed/view setup for registration/checkin) ...
        await update_live_embeds(guild)

        # --- Restore scheduled opens for registration and checkin ---
        for key, (channel_name, role_name) in [
            ("registration", (REGISTRATION_CHANNEL, ANGEL_ROLE)),
            ("checkin", (CHECK_IN_CHANNEL, REGISTERED_ROLE)),
        ]:
            scheduled_iso = get_schedule(guild.id, key)
            if scheduled_iso:
                scheduled_utc = datetime.fromisoformat(scheduled_iso)
                now_utc = datetime.now(ZoneInfo("UTC"))
                if scheduled_utc > now_utc:
                    print(f"[Schedule] Restoring scheduled open for {channel_name}: {scheduled_utc.isoformat()}")
                    bot.loop.create_task(schedule_channel_open(guild, channel_name, role_name, scheduled_utc))
                elif scheduled_utc <= now_utc:
                    # Optionally, open channel immediately if scheduled time already passed
                    channel = discord.utils.get(guild.text_channels, name=channel_name)
                    role = discord.utils.get(guild.roles, name=role_name)
                    if channel and role:
                        overwrites = channel.overwrites_for(role)
                        if not overwrites.view_channel:
                            overwrites.view_channel = True
                            await channel.set_permissions(role, overwrite=overwrites)
                            print(f"[Schedule] Channel '{channel_name}' opened immediately after restart.")
                        await update_live_embeds(guild)
                        # --- CLEAR THE SCHEDULE ---
                        key = "registration" if channel_name == REGISTRATION_CHANNEL else "checkin"
                        set_schedule(guild.id, key, None)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.name == REGISTRATION_CHANNEL:
        # Only allow registration if Angels can view the channel
        angels_role = discord.utils.get(message.guild.roles, name=ANGEL_ROLE)
        if not angels_role:
            return
        overwrites = message.channel.overwrites_for(angels_role)
        if not overwrites.view_channel:
            try:
                await message.delete()
            except Exception:
                pass
            embed = embed_from_cfg("registration_closed")
            try:
                await message.author.send(embed=embed)
            except Exception:
                pass
            return  # Don't process registration

        role = discord.utils.get(message.guild.roles, name=REGISTERED_ROLE)
        try:
            await message.add_reaction("⏳")
        except:
            pass
        if role and role not in message.author.roles:
            try:
                await message.author.add_roles(role)
            except discord.Forbidden:
                pass
        try:
            discord_tag = str(message.author)
            ign = message.content.strip()
            await find_or_register_user(discord_tag, ign)
            await message.clear_reactions()
            await message.add_reaction("✅")
        except Exception as e:
            await message.clear_reactions()
            await message.add_reaction("❌")
            await log_error(bot, message.guild, f"Registration error: {e}")
    await bot.process_commands(message)

bot.run(token, log_handler=handler, log_level=logging.DEBUG)