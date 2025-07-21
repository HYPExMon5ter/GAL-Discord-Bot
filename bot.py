# gal_discord_bot/bot.py

import logging

import discord
from discord.ext import commands

from commands import gal
from config import DISCORD_TOKEN
from events import setup_events

# Logging setup
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logging.basicConfig(level=logging.INFO, handlers=[handler])

# Discord Intents
intents = discord.Intents.default()
intents.guild_scheduled_events = True
intents.messages = True
intents.message_content = True
intents.members = True

# Create the bot
bot = commands.Bot(command_prefix=".", intents=intents)
tree = bot.tree

# Register slash commands group
tree.add_command(gal)

# Setup event listeners
setup_events(bot)

# Run the bot
bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)