# gal_discord_bot/logging_utils.py

import logging
from datetime import datetime, timezone

from gal_discord_bot.config import embed_from_cfg, LOG_CHANNEL_NAME, PING_USER


async def log_error(bot, guild, message, level="Error"):
    log_channel = None
    if guild:
        log_channel = next(
            (c for c in guild.text_channels if c.name == LOG_CHANNEL_NAME), None
        )
    embed = embed_from_cfg("error")
    embed.description = message
    embed.timestamp = datetime.now(timezone.utc)
    embed.set_footer(text="GAL Bot")
    if log_channel:
        await log_channel.send(content=PING_USER if level == "Error" else None, embed=embed)
    else:
        logging.error(message)