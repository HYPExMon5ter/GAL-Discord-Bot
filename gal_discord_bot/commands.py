# gal_discord_bot/commands.py

from discord import app_commands
import discord
import asyncio
import time
from zoneinfo import ZoneInfo
from datetime import datetime
from gal_discord_bot.config import (
    embed_from_cfg, EMBEDS_CFG,
    ALLOWED_ROLES, CHECK_IN_CHANNEL, REGISTRATION_CHANNEL,
    REGISTERED_ROLE, ANGEL_ROLE, CHECKED_IN_ROLE
)
from gal_discord_bot.views import (
    RegistrationView, CheckInView,
    update_live_embeds, update_registration_embed, update_checkin_embed,
    PersistentRegisteredListView
)
from gal_discord_bot.sheets import (
    sheet_cache, cache_lock, find_or_register_user, refresh_sheet_cache, retry_until_successful,
    mark_checked_in_async, unmark_checked_in_async, reset_registered_roles_and_sheet, reset_checked_in_roles_and_sheet,
    similar, get_sheet_for_guild
)
from gal_discord_bot.persistence import (
    get_persisted_msg, set_persisted_msg,
    get_event_mode_for_guild, set_event_mode_for_guild,
    get_schedule, set_schedule
)
from gal_discord_bot.riot_api import get_summoner_info, get_latest_tft_placement

TEST_GUILD_ID = 1385739351505240074
PROD_GUILD_ID = 716787949584515102

# Helper: Check allowed roles
def has_allowed_role(member):
    return any(role.name in ALLOWED_ROLES for role in getattr(member, "roles", []))

def has_allowed_role_from_interaction(interaction: discord.Interaction):
    member = getattr(interaction, "user", getattr(interaction, "author", None))
    return hasattr(member, "roles") and has_allowed_role(member)

@app_commands.guilds(discord.Object(id=TEST_GUILD_ID))
class GalGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="gal", description="Group of GAL bot commands")

gal = GalGroup()

@gal.command(name="register", description="Register for the event.")
@app_commands.describe(ign="Your in-game name", team_name="Team name (required for doubleup event)")
async def register(interaction: discord.Interaction, ign: str, team_name: str = None):
    guild = interaction.guild
    user = interaction.user
    guild_id = str(guild.id)
    discord_tag = str(user)
    mode = get_event_mode_for_guild(guild_id)
    reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
    if not reg_channel or interaction.channel.id != reg_channel.id:
        await interaction.response.send_message("You must use this command in the registration channel.", ephemeral=True)
        return

    angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
    if reg_channel and angel_role:
        overwrites = reg_channel.overwrites_for(angel_role)
        if not overwrites.view_channel:
            embed = embed_from_cfg("registration_closed")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    try:
        await interaction.response.defer(thinking=False)
        async for msg in reg_channel.history(limit=100):
            if (
                msg.author == guild.me
                and msg.embeds
                and (user.mention in msg.embeds[0].description or user.mention in msg.embeds[0].title)
            ):
                try:
                    await msg.delete()
                except Exception:
                    pass
        name = user.mention
        if mode == "normal":
            row_num = await find_or_register_user(discord_tag, ign, guild_id=guild_id)
            reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
            if reg_role and reg_role not in user.roles:
                await user.add_roles(reg_role)
            embed = embed_from_cfg("register_success_normal", ign=ign, name=name)
            await interaction.followup.send(embed=embed)

        elif mode == "doubleup":
            if not team_name or len(team_name.strip()) < 2:
                await interaction.followup.send("You must specify a team name for double up!", ephemeral=True)
                return
            team_name = team_name.strip()
            row_num = await find_or_register_user(discord_tag, ign, guild_id=guild_id, team_name=team_name)
            reg_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
            if reg_role and reg_role not in user.roles:
                await user.add_roles(reg_role)
            embed = embed_from_cfg("register_success_doubleup", ign=ign, team_name=team_name, name=name)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Event mode is not set for this server. Please contact staff.", ephemeral=True)
            return
    except Exception as e:
        import logging
        logging.exception(f"[REGISTER-ERROR] {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("Error registering! Please contact staff.", ephemeral=True)
        else:
            await interaction.followup.send("Error registering! Please contact staff.", ephemeral=True)

@gal.command(name="toggle", description="Toggles the registration or check-in channel for the respective role and updates the embed/view.")
@app_commands.describe(channel="Which channel to toggle (registration or checkin)")
async def toggle(interaction: discord.Interaction, channel: str):
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    guild = interaction.guild
    channel_type = channel.lower().strip()

    if channel_type == "registration":
        reg_channel = discord.utils.get(guild.text_channels, name=REGISTRATION_CHANNEL)
        angel_role = discord.utils.get(guild.roles, name=ANGEL_ROLE)
        overwrites = reg_channel.overwrites_for(angel_role)
        overwrites.view_channel = not overwrites.view_channel
        await reg_channel.set_permissions(angel_role, overwrite=overwrites)
        reg_msg_id = get_persisted_msg(guild.id, "registration")
        if reg_msg_id:
            await update_registration_embed(reg_channel, reg_msg_id, guild)
        embed = embed_from_cfg("registration_channel_toggled", visible=overwrites.view_channel)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    elif channel_type == "checkin":
        checkin_channel = discord.utils.get(guild.text_channels, name=CHECK_IN_CHANNEL)
        registered_role = discord.utils.get(guild.roles, name=REGISTERED_ROLE)
        overwrites = checkin_channel.overwrites_for(registered_role)
        overwrites.view_channel = not overwrites.view_channel
        await checkin_channel.set_permissions(registered_role, overwrite=overwrites)
        checkin_msg_id = get_persisted_msg(guild.id, "checkin")
        if checkin_msg_id:
            await update_checkin_embed(checkin_channel, checkin_msg_id, guild)
        embed = embed_from_cfg("checkin_channel_toggled", visible=overwrites.view_channel)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(
            "Invalid channel type! Use either `registration` or `checkin`.",
            ephemeral=True
        )

@gal.command(name="event", description="View or set the event mode for this guild (normal/doubleup).")
@app_commands.describe(mode="Set the event mode (normal/doubleup)")
async def event(interaction: discord.Interaction, mode: str = None):
    from gal_discord_bot.sheets import refresh_sheet_cache
    guild_id = str(interaction.guild.id)
    ALLOWED_MODES = ["normal", "doubleup"]

    if mode and not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    current_mode = get_event_mode_for_guild(guild_id)

    if mode:
        mode = mode.lower()
        if mode not in ALLOWED_MODES:
            await interaction.response.send_message(
                f"Invalid mode! Must be one of: {', '.join(ALLOWED_MODES)}",
                ephemeral=True
            )
            return
        set_event_mode_for_guild(guild_id, mode)
        # Immediately refresh the cache for the new mode
        try:
            await refresh_sheet_cache(bot=interaction.client)
            refresh_note = "\n\nUser cache was refreshed for the new mode."
        except Exception as e:
            refresh_note = f"\n\nUser cache refresh failed: {e}"
        await interaction.response.send_message(
            f"✅ Event mode set to **{mode.capitalize()}** for this guild.{refresh_note}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"Current event mode: **{current_mode.capitalize()}**\nTo change: `/gal event <normal|doubleup>`",
            ephemeral=True
        )

@gal.command(name="registeredlist", description="Show all registered users and who is checked in.")
async def registeredlist(interaction: discord.Interaction):
    from gal_discord_bot.views import PersistentRegisteredListView
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)
    mode = get_event_mode_for_guild(str(interaction.guild.id))
    async with cache_lock:
        user_data = list(sheet_cache["users"].items())

    if mode == "normal":
        lines = []
        for discord_tag, user_tuple in user_data:
            ign = user_tuple[1]
            registered_flag = user_tuple[2]
            checked_in_flag = user_tuple[3]
            status = "✅" if str(checked_in_flag).strip().upper() == "TRUE" else "❌"
            if str(registered_flag).strip().upper() == "TRUE":
                lines.append(f"`{discord_tag}` (`{ign}`) — {status}")

        count = len(lines)
        embed = discord.Embed(
            title=f"Registered Players: {count}",
            description="No registered users found." if not lines else "\n".join(lines),
            color=discord.Color.blurple()
        )
        await interaction.followup.send(embed=embed, ephemeral=False, view=PersistentRegisteredListView(interaction.guild))

    elif mode == "doubleup":
        players = []
        for discord_tag, user_tuple in user_data:
            ign = user_tuple[1]
            registered_flag = user_tuple[2]
            checked_in_flag = user_tuple[3]
            team_name = user_tuple[4] if len(user_tuple) > 4 else ""
            if str(registered_flag).strip().upper() == "TRUE":
                players.append({
                    "discord_tag": discord_tag,
                    "ign": ign,
                    "checked_in_flag": checked_in_flag,
                    "team_name": team_name or "No Team"
                })

        # Group and sort players by team
        from itertools import groupby
        # First, sort by team name, then by discord tag (for stable grouping)
        players.sort(key=lambda x: (x["team_name"].lower(), x["discord_tag"].lower()))

        lines = []
        unique_teams = set()
        for team, group in groupby(players, key=lambda x: x["team_name"].lower()):
            team_members = list(group)
            unique_teams.add(team)
            for player in team_members:
                team_name = player["team_name"]
                status = "✅" if str(player["checked_in_flag"]).strip().upper() == "TRUE" else "❌"
                lines.append(f"{team_name} | `{player['discord_tag']}` (`{player['ign']}`) — {status}")
            lines.append("")  # Blank line between teams

        # Remove trailing blank line if any
        if lines and lines[-1] == "":
            lines.pop()

        embed = discord.Embed(
            title=f"Registered Players: {len(players)} | Teams: {len(unique_teams)}",
            description="No registered users found." if not lines else "\n".join(lines),
            color=discord.Color.blurple()
        )
        await interaction.followup.send(embed=embed, ephemeral=False, view=PersistentRegisteredListView(interaction.guild))

    else:
        embed = embed_from_cfg("error")
        embed.description = "Event mode is not set for this server."
        await interaction.followup.send(embed=embed, ephemeral=True)

@gal.command(name="reminder", description="DM all registered users who are not checked in.")
async def reminder(interaction: discord.Interaction):
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)
    reminder_cfg = EMBEDS_CFG.get("reminder_dm", {})
    reminder_msg = reminder_cfg.get("description", "Reminder: Please check in for the tournament!")
    dmmed = []
    async with cache_lock:
        for discord_tag, user_tuple in sheet_cache["users"].items():
            registered_flag = user_tuple[2]
            checked_in_flag = user_tuple[3]
            if str(registered_flag).strip().upper() == "TRUE" and str(checked_in_flag).strip().upper() != "TRUE":
                member = None
                if "#" in discord_tag:
                    name, discrim = discord_tag.rsplit("#", 1)
                    member = discord.utils.get(interaction.guild.members, name=name, discriminator=discrim)
                if not member:
                    for m in interaction.guild.members:
                        if m.display_name == discord_tag or m.name == discord_tag:
                            member = m
                            break
                if member:
                    try:
                        await member.send(reminder_msg)
                        dmmed.append(f"{member} (`{discord_tag}`)")
                    except Exception:
                        pass
    num_dmmed = len(dmmed)
    users_list = "\n".join(dmmed) if dmmed else "No users could be DM'd (not found or DMs disabled)."
    embed = embed_from_cfg(
        "reminder_public",
        count=num_dmmed,
        users=users_list
    )
    await interaction.followup.send(embed=embed, ephemeral=False)

@gal.command(name="cache", description="Forces a manual refresh of the user cache from the Google Sheet.")
async def cache(interaction: discord.Interaction):
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    try:
        await interaction.response.defer(ephemeral=True)
        start_time = time.perf_counter()
        # Pass the guild id to refresh_sheet_cache so it can select correct sheet for the mode
        updated_users, total_users = await refresh_sheet_cache(bot=interaction.client)
        elapsed = time.perf_counter() - start_time
        embed = embed_from_cfg(
                "cache",
                updated=updated_users,
                count=total_users,
                elapsed=elapsed
            )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        import logging
        logging.error(f"Cache command error: {e}")
        embed = embed_from_cfg("error")
        embed.description = f"An error occurred while refreshing the cache: {e}"
        try:
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception:
            pass

@gal.command(name="validate", description="Validate checked-in IGNs with Riot API.")
async def validate(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    valid = []
    invalid = []
    async with cache_lock:
        for discord_tag, user_tuple in sheet_cache["users"].items():
            ign = user_tuple[1]
            checked_in_flag = user_tuple[3]
            if str(checked_in_flag).strip().upper() != "TRUE":
                continue
            summ_info = get_summoner_info(ign)
            if summ_info:
                valid.append(f"`{discord_tag}` — `{ign}`")
            else:
                invalid.append(f"`{discord_tag}` — `{ign}`")
    description = ""
    if valid:
        description += "**✅ Valid IGNs:**\n" + "\n".join(valid) + "\n"
    if invalid:
        description += "\n**❌ Invalid IGNs:**\n" + "\n".join(invalid)
    if not valid and not invalid:
        description = "No checked-in users to validate."
    embed = discord.Embed(
        title="IGN Validation Results",
        description=description,
        color=discord.Color.green() if valid and not invalid else discord.Color.orange() if valid else discord.Color.red(),
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

@gal.command(name="placements", description="Show latest TFT placements for checked-in users.")
async def placements(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    results = []
    async with cache_lock:
        for discord_tag, user_tuple in sheet_cache["users"].items():
            ign = user_tuple[1]
            checked_in_flag = user_tuple[3]
            if str(checked_in_flag).strip().upper() != "TRUE":
                continue
            summ_info = get_summoner_info(ign)
            if not summ_info:
                results.append(f"`{discord_tag}` — `{ign}`: **IGN not found**")
                continue
            puuid = summ_info.get("puuid")
            placement = get_latest_tft_placement(puuid)
            if placement:
                results.append(f"`{discord_tag}` — `{ign}`: **{placement}th place**")
            else:
                results.append(f"`{discord_tag}` — `{ign}`: **No recent matches found**")
    description = "\n".join(results) if results else "No checked-in users to show placements for."
    embed = discord.Embed(
        title="Checked-In Player Latest Placements",
        description=description,
        color=discord.Color.blue()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

@gal.command(name="reload", description="Reloads the embeds config and updates live messages.")
async def reload_cmd(interaction: discord.Interaction):
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    from gal_discord_bot.config import load_embeds_cfg
    global EMBEDS_CFG
    EMBEDS_CFG = load_embeds_cfg()
    for guild in interaction.client.guilds:
        await update_live_embeds(guild)
    embed = discord.Embed(
        title="Config Reloaded",
        description="Embed configuration reloaded and live embeds updated!",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

class ScheduleGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="schedule", description="Schedule registration/check-in opening times")

    @app_commands.command(name="reg", description="Set/view the scheduled open time for registration (MM-DD-YY HH:MM AM/PM PST)")
    @app_commands.describe(time="Open time in MM-DD-YY HH:MM AM/PM format, PST (leave blank to view)")
    async def reg(self, interaction: discord.Interaction, time: str = None):
        await _schedule_logic(interaction, "registration", REGISTRATION_CHANNEL, ANGEL_ROLE, time)

    @app_commands.command(name="checkin", description="Set/view the scheduled open time for check-in (MM-DD-YY HH:MM AM/PM PST)")
    @app_commands.describe(time="Open time in MM-DD-YY HH:MM AM/PM format, PST (leave blank to view)")
    async def checkin(self, interaction: discord.Interaction, time: str = None):
        await _schedule_logic(interaction, "checkin", CHECK_IN_CHANNEL, REGISTERED_ROLE, time)

    @app_commands.command(name="cancelreg", description="Cancel the scheduled registration open")
    async def cancelreg(self, interaction: discord.Interaction):
        await _cancel_schedule_logic(interaction, "registration")

    @app_commands.command(name="cancelcheckin", description="Cancel the scheduled check-in open")
    async def cancelcheckin(self, interaction: discord.Interaction):
        await _cancel_schedule_logic(interaction, "checkin")

gal.add_command(ScheduleGroup())

async def _schedule_logic(interaction, key, channel_name, role_name, time):
    await interaction.response.defer(ephemeral=True)
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    guild = interaction.guild
    PST = ZoneInfo("America/Los_Angeles")
    time_format = "%m-%d-%y %I:%M %p"
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
        asyncio.create_task(schedule_channel_open(guild, channel_name, role_name, scheduled_utc))
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

async def schedule_channel_open(guild, channel_name, role_name, open_time):
    now = datetime.now(ZoneInfo("UTC"))
    wait_seconds = (open_time - now).total_seconds()
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    role = discord.utils.get(guild.roles, name=role_name)
    if channel and role:
        overwrites = channel.overwrites_for(role)
        overwrites.view_channel = True
        await channel.set_permissions(role, overwrite=overwrites)
        await update_live_embeds(guild)
        key = "registration" if channel_name == REGISTRATION_CHANNEL else "checkin"
        set_schedule(guild.id, key, None)

@gal.command(name="help", description="Shows this help message.")
async def help_cmd(interaction: discord.Interaction):
    cfg = EMBEDS_CFG.get("help", {})
    help_embed = discord.Embed(
        title=cfg.get("title", "GAL Bot Help"),
        description=cfg.get("description", ""),
        color=discord.Color.blurple()
    )
    from gal_discord_bot.config import GAL_COMMAND_IDS
    cmd_descs = cfg.get("commands", {})
    for cmd_name, cmd_id in GAL_COMMAND_IDS.items():
        desc = cmd_descs.get(cmd_name, "")
        clickable = f"</gal {cmd_name}:{cmd_id}>"
        help_embed.add_field(
            name=clickable,
            value=desc,
            inline=False
        )
    await interaction.response.send_message(embed=help_embed, ephemeral=True)