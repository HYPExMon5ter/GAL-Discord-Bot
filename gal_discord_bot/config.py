# gal_discord_bot/config.py

import os
from dotenv import load_dotenv
import yaml
import aiohttp

# --- Load environment variables ---
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Channel and Role Names ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Y_NBCYSJvYs3j_xD8IivMU5EdAbTMNAtsU40g7bCQzg/edit"
SHEET_KEY = SHEET_URL.split("/d/")[1].split("/")[0]
DOUBLEUP_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Mr-wr0AhiaFdW3Lu_l9U9eaEL-Qn_crMD-iQHiW8oWI/edit"
DOUBLEUP_SHEET_KEY = DOUBLEUP_SHEET_URL.split("/d/")[1].split("/")[0]

ALLOWED_ROLES = ["Admin", "Moderator", "GAL Helper"]
CHECK_IN_CHANNEL = "✔check-in"
REGISTRATION_CHANNEL = "🎫registration"
CHECKED_IN_ROLE = "Checked In"
REGISTERED_ROLE = "Registered"
ANGEL_ROLE = "Angels"
LOG_CHANNEL_NAME = "bot-log"
PING_USER = "<@162359821100646401>"

CACHE_REFRESH_SECONDS = 600  # 10 min

# --- Embeds Loader ---
def hex_to_color(hex_str):
    import discord
    return discord.Color(int(hex_str.replace("#", ""), 16))

def load_embeds_cfg():
    with open("embeds.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

EMBEDS_CFG = load_embeds_cfg()

def embed_from_cfg(key, **kwargs):
    import discord
    cfg = EMBEDS_CFG.get(key, {})
    if key.endswith("_toggled") and "visible" in kwargs:
        visible = kwargs["visible"]
        desc = cfg.get("description_visible") if visible else cfg.get("description_hidden")
        color = hex_to_color(cfg.get("color_visible")) if visible else hex_to_color(cfg.get("color_hidden"))
        if not desc:
            desc = "\u200b"
        return discord.Embed(
            title=cfg.get("title", ""),
            description=desc,
            color=color
        )
    title = cfg.get("title", "").format(**kwargs)
    desc_template = cfg.get("description", "")
    try:
        desc = desc_template.format(**kwargs)
    except KeyError as ex:
        # Fallback for missing keys
        missing = str(ex).strip("'")
        import logging
        logging.warning(f"embed_from_cfg: Missing key '{missing}' for embed '{key}'. Kwargs: {kwargs}")
        desc = desc_template
    if not desc:
        desc = "\u200b"
    color = hex_to_color(cfg.get("color", "#3498db"))
    return discord.Embed(title=title, description=desc, color=color)

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