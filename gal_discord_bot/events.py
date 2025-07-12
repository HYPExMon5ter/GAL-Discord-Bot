# gal_discord_bot/events.py

import discord
import asyncio
from zoneinfo import ZoneInfo
from datetime import datetime

from gal_discord_bot.views import update_live_embeds, PersistentRegisteredListView, create_persisted_embed, RegistrationView, CheckInView
from gal_discord_bot.persistence import get_schedule, set_schedule, migrate_legacy, get_persisted_msg
from gal_discord_bot.config import REGISTRATION_CHANNEL, CHECK_IN_CHANNEL, ANGEL_ROLE, REGISTERED_ROLE, update_gal_command_ids, embed_from_cfg
from gal_discord_bot.sheets import refresh_sheet_cache

def setup_events(bot):
    @bot.event
    async def on_ready():
        print(f"We are ready to go in, {bot.user.name}")
        migrate_legacy()

        # --- Sync all slash commands to all guilds the bot is in ---
        for guild in bot.guilds:
            await bot.tree.sync(guild=guild)
            print(f"Synced commands to guild {guild.id}")

        await update_gal_command_ids(bot)

        await refresh_sheet_cache(bot=bot)
        asyncio.create_task(bot_cache_refresh_loop(bot))

        # --- Ensure registration and check-in embeds exist for all guilds ---
        for guild in bot.guilds:
            # Registration embed creation if missing
            reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
            reg_channel_id, reg_msg_id = get_persisted_msg(guild.id, "registration")
            if reg_channel and not reg_msg_id:
                embed = embed_from_cfg("registration_closed")
                await create_persisted_embed(
                    guild, reg_channel, embed, RegistrationView(None, guild), "registration"
                )

            # Check-in embed creation if missing
            checkin_channel = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
            checkin_channel_id, checkin_msg_id = get_persisted_msg(guild.id, "checkin")
            if checkin_channel and not checkin_msg_id:
                embed = embed_from_cfg("checkin_closed")
                await create_persisted_embed(
                    guild, checkin_channel, embed, CheckInView(guild), "checkin"
                )

            bot.add_view(PersistentRegisteredListView(guild))
            await update_live_embeds(guild)
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
                        asyncio.create_task(schedule_channel_open(bot, guild, channel_name, role_name, scheduled_utc))
                    elif scheduled_utc <= now_utc:
                        channel = discord.utils.get(guild.text_channels, name=channel_name)
                        role = discord.utils.get(guild.roles, name=role_name)
                        if channel and role:
                            overwrites = channel.overwrites_for(role)
                            if not overwrites.view_channel:
                                overwrites.view_channel = True
                                await channel.set_permissions(role, overwrite=overwrites)
                                print(f"[Schedule] Channel '{channel_name}' opened immediately after restart.")
                            await update_live_embeds(guild)
                            set_schedule(guild.id, key, None)

    @bot.event
    async def on_message(message):
        # Ignore bot messages
        if message.author.bot:
            return
        # Registration channel: only allow the /gal register command
        if message.channel.name == REGISTRATION_CHANNEL:
            if not message.content.startswith("/gal register"):
                try:
                    await message.delete()
                except Exception:
                    pass
                try:
                    from gal_discord_bot.config import embed_from_cfg
                    embed = embed_from_cfg("register_channel_only")
                    await message.author.send(embed=embed)
                except Exception:
                    pass
                return
        await bot.process_commands(message)

async def bot_cache_refresh_loop(bot):
    from gal_discord_bot.sheets import cache_refresh_loop
    await cache_refresh_loop(bot)

async def schedule_channel_open(bot, guild, channel_name, role_name, open_time):
    from gal_discord_bot.views import update_live_embeds
    now = datetime.now(ZoneInfo("UTC"))
    wait_seconds = (open_time - now).total_seconds()
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
        key = "registration" if channel_name == REGISTRATION_CHANNEL else "checkin"
        set_schedule(guild.id, key, None)