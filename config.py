# gal_discord_bot/config.py

import os

import aiohttp
import discord
import yaml
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN     = os.getenv("DISCORD_TOKEN")
RIOT_API_KEY      = os.getenv("RIOT_API_KEY")
DATABASE_URL      = os.getenv("DATABASE_URL")

# Bot‐specific constants (unchanged)
ALLOWED_ROLES         = ["Admin", "Moderator", "GAL Helper"]
CHECK_IN_CHANNEL      = "✔check-in"
REGISTRATION_CHANNEL  = "🎫registration"
CHECKED_IN_ROLE       = "Checked In"
REGISTERED_ROLE       = "Registered"
ANGEL_ROLE            = "Angels"
LOG_CHANNEL_NAME      = "bot-log"
PING_USER            = "<@162359821100646401>"

CACHE_REFRESH_SECONDS = 1800  # 30 minutes

# ————— Load entire config.yaml ————————————————————————————————
with open("config.yaml", "r", encoding="utf-8") as f:
    _FULL_CFG = yaml.safe_load(f)

# — Embeds mapping —————————————————————————————————————————————
EMBEDS_CFG = _FULL_CFG.get("embeds", {})

def hex_to_color(s: str) -> discord.Color:
    return discord.Color(int(s.lstrip("#"), 16))

def embed_from_cfg(key: str, **kwargs) -> discord.Embed:
    """
    Fetch an embed template from the merged config.yaml (EMBEDS_CFG),
    format it with provided kwargs, and return a discord.Embed.
    Supports special '_toggled' embeds with description_visible/hidden and color_visible/hidden.
    """
    import discord
    import logging

    # Lookup the raw embed data
    data = EMBEDS_CFG.get(key, {})

    # 1) Handle toggled embeds (endswith "_toggled" and has 'visible' kwarg)
    if key.endswith("_toggled") and "visible" in kwargs:
        visible = kwargs.pop("visible")
        # Choose the appropriate description & color fields
        desc_key = "description_visible" if visible else "description_hidden"
        color_key = "color_visible" if visible else "color_hidden"

        desc = data.get(desc_key) or "\u200b"
        color = hex_to_color(data.get(color_key, "#000000"))

        title = data.get("title", "")
        return discord.Embed(title=title, description=desc, color=color)

    # 2) Normal embeds
    # Format the title
    raw_title = data.get("title", "")
    title = raw_title.format(**kwargs)

    # Format the description, with graceful fallback for missing keys
    raw_desc = data.get("description", "")
    try:
        description = raw_desc.format(**kwargs)
    except KeyError as ex:
        missing = str(ex).strip("'")
        logging.warning(f"embed_from_cfg: Missing key '{missing}' for embed '{key}'. Kwargs: {kwargs}")
        description = raw_desc

    if not description:
        description = "\u200b"

    # Parse the color hex
    color = hex_to_color(data.get("color", "#3498db"))

    # Build and return
    return discord.Embed(title=title, description=description, color=color)

# — Sheet configuration ————————————————————————————————————————
SHEET_CONFIG = _FULL_CFG.get("sheet_configuration", {})

def get_sheet_settings(mode: str) -> dict:
    """
    Return the dict for mode "normal" or "doubleup" (falls back to normal).
    """
    return SHEET_CONFIG.get(mode, SHEET_CONFIG["normal"])

def col_to_index(col: str) -> int:
    """
    Convert column letter(s) to 1-based index: A→1, B→2, ..., Z→26, AA→27, etc.
    """
    col = col.upper()
    idx = 0
    for ch in col:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx

GAL_COMMAND_IDS = {}

async def fetch_guild_commands(bot, guild_id):
    url = f"https://discord.com/api/v10/applications/{bot.user.id}/guilds/{guild_id}/commands"
    headers = {
        "Authorization": f"Bot {os.environ.get('DISCORD_TOKEN') or bot.http.token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return []
            return await resp.json()

async def update_gal_command_ids(bot):
    """Populates GAL_COMMAND_IDS for all /gal subcommands in all guilds via REST API."""
    GAL_COMMAND_IDS.clear()
    for guild in bot.guilds:
        cmds = await fetch_guild_commands(bot, guild.id)
        for cmd in cmds:
            if cmd["name"] == "gal" and cmd["type"] == 1:
                gal_id = cmd["id"]
                for option in cmd.get("options", []):
                    if option["type"] == 1:
                        GAL_COMMAND_IDS[option["name"]] = gal_id
        for cmd in cmds:
            if cmd["name"].startswith("gal ") and cmd["type"] == 1:
                GAL_COMMAND_IDS[cmd["name"].split(" ", 1)[1]] = cmd["id"]

def get_cmd_id(name):
    return GAL_COMMAND_IDS.get(name, 0)