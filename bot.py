# bot.py

import os
import asyncio
import logging

import discord
from discord.ext import commands

from config import DISCORD_TOKEN
from commands import gal
from events import setup_events

logging.basicConfig(level=logging.INFO, handlers=[
    logging.FileHandler("discord.log", encoding="utf-8", mode="w")
])

class GALBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.message_content = True
        intents.guild_scheduled_events = True

        # APPLICATION_ID must be your App’s client ID (not the token)
        application_id = int(os.getenv("APPLICATION_ID", 0))
        super().__init__(
            command_prefix=".",
            intents=intents,
            application_id=application_id
        )

    async def setup_hook(self):
        # 1) Register your /gal group as a global command
        self.tree.add_command(gal)

        # 2) If DEV_GUILD_ID is set, copy all global commands into it then sync;
        #    otherwise sync globally.
        DEV = os.getenv("DEV_GUILD_ID")
        if DEV:
            dev_obj = discord.Object(id=int(DEV))
            # Copy globals into the DEV guild for immediate testing
            self.tree.copy_global_to(guild=dev_obj)
            await self.tree.sync(guild=dev_obj)
            print(f"[setup_hook] • Copied + synced /gal to DEV_GUILD_ID={DEV}")
        else:
            await self.tree.sync()
            print("[setup_hook] • Synced /gal globally")

        # 3) Setup events
        setup_events(self)

async def main():
    bot = GALBot()
    try:
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        await bot.close()
    except asyncio.CancelledError:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())