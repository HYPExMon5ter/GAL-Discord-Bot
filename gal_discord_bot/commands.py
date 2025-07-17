# gal_discord_bot/commands.py

import time

import discord
from discord import app_commands

from gal_discord_bot.config import (
    embed_from_cfg, CHECK_IN_CHANNEL, REGISTRATION_CHANNEL,
    REGISTERED_ROLE, ANGEL_ROLE, load_embeds_cfg
)
from gal_discord_bot.logging_utils import log_error
from gal_discord_bot.persistence import (
    get_event_mode_for_guild, set_event_mode_for_guild
)
from gal_discord_bot.riot_api import get_summoner_info, get_latest_tft_placement
from gal_discord_bot.sheets import (
    sheet_cache, cache_lock, refresh_sheet_cache
)
from gal_discord_bot.utils import (
    has_allowed_role_from_interaction,
    toggle_persisted_channel,
)
from gal_discord_bot.views import (
    update_live_embeds, PersistentRegisteredListView, CheckInButton
)

TEST_GUILD_ID = 1385739351505240074
PROD_GUILD_ID = 716787949584515102

@app_commands.guilds(discord.Object(id=TEST_GUILD_ID))
class GalGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="gal", description="Group of GAL bot commands")

gal = GalGroup()

@gal.command(name="toggle", description="Toggles the registration or check-in channel.")
@app_commands.describe(channel="Which channel to toggle (registration or checkin)")
async def toggle(interaction: discord.Interaction, channel: str):
    # permission check
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    chan = channel.lower().strip()
    if chan == "registration":
        await toggle_persisted_channel(
            interaction,
            persist_key="registration",
            channel_name=REGISTRATION_CHANNEL,
            role_name=ANGEL_ROLE,
            ping_role=True,
        )
    elif chan == "checkin":
        await toggle_persisted_channel(
            interaction,
            persist_key="checkin",
            channel_name=CHECK_IN_CHANNEL,
            role_name=REGISTERED_ROLE,
            ping_role=True,
        )
    else:
        await interaction.response.send_message(
            "Invalid channel type! Use `registration` or `checkin`.",
            ephemeral=True
        )

@gal.command(name="event", description="View or set the event mode for this guild (normal/doubleup).")
@app_commands.describe(mode="Set the event mode (normal/doubleup)")
async def event(interaction: discord.Interaction, mode: str = None):
    try:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        guild_id = str(guild.id)

        current_mode = get_event_mode_for_guild(guild_id)

        # If no mode is provided, just show current mode
        if mode is None:
            embed = embed_from_cfg(
                "event_mode_current",
                mode=current_mode.capitalize()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Only staff (or allowed role) can change
        if not has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Validate and set new mode
        mode = mode.lower()
        if mode not in ["normal", "doubleup"]:
            embed = embed_from_cfg(
                "event_mode_invalid",
                allowed="normal or doubleup"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        set_event_mode_for_guild(guild_id, mode)
        await interaction.followup.send(
            embed=embed_from_cfg(
                "event_mode_set",
                mode=mode.capitalize()
            ),
            ephemeral=True
        )

        # Optionally, update embeds/views after mode change
        await refresh_sheet_cache(bot=interaction.client)
        await update_live_embeds(guild)

    except Exception as e:
        await log_error(interaction.client, interaction.guild, f"[EVENT-COMMAND-ERROR] {e}")

@gal.command(name="registeredlist", description="Show all registered users and who is checked in.")
async def registeredlist(interaction: discord.Interaction):
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
        await log_error(interaction.client, interaction.guild, f"Event mode is not set for {interaction.guild}")

@gal.command(name="reminder", description="DM all registered users who are not checked in.")
async def reminder(interaction: discord.Interaction):
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    await interaction.response.defer(ephemeral=False)

    # Prepare DM embed + view
    dm_embed = embed_from_cfg("reminder_dm")
    dmmed = []

    async with cache_lock:
        for discord_tag, user_tuple in sheet_cache["users"].items():
            registered = str(user_tuple[2]).upper() == "TRUE"
            checked_in  = str(user_tuple[3]).upper() == "TRUE"
            if registered and not checked_in:
                # locate the member
                member = None
                if "#" in discord_tag:
                    name, discrim = discord_tag.rsplit("#", 1)
                    member = discord.utils.get(interaction.guild.members, name=name, discriminator=discrim)
                if not member:
                    for m in interaction.guild.members:
                        if m.name == discord_tag or m.display_name == discord_tag:
                            member = m
                            break

                if member:
                    try:
                        view = discord.ui.View(timeout=None)
                        view.add_item(CheckInButton(guild_id=interaction.guild.id))
                        await member.send(embed=dm_embed, view=view)
                        dmmed.append(f"{member} (`{discord_tag}`)")
                    except:
                        pass

    # Summarize DMs sent
    count = len(dmmed)
    users_list = "\n".join(dmmed) if dmmed else "No users could be DM'd."
    public = embed_from_cfg("reminder_public", count=count, users=users_list)
    await interaction.followup.send(embed=public, ephemeral=False)

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
        await log_error(interaction.client, interaction.guild, f"Cache command error: {e}")

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

@gal.command(
    name="reload",
    description="Reloads embeds config, updates live messages, and refreshes presence."
)
async def reload_cmd(interaction: discord.Interaction):
    # 1) Permission check
    if not has_allowed_role_from_interaction(interaction):
        embed = embed_from_cfg("permission_denied")
        return await interaction.response.send_message(embed=embed, ephemeral=True)

    # 2) Reload embeds & live views
    global EMBEDS_CFG
    EMBEDS_CFG = load_embeds_cfg()
    for guild in interaction.client.guilds:
        await update_live_embeds(guild)

    # 3) Refresh Rich Presence from embeds.yaml
    presence_cfg = EMBEDS_CFG.get("rich_presence", {})
    pres_type = presence_cfg.get("type", "PLAYING").upper()
    pres_msg  = presence_cfg.get("message", "")

    if pres_type == "LISTENING":
        activity = discord.Activity(type=discord.ActivityType.listening, name=pres_msg)
    elif pres_type == "WATCHING":
        activity = discord.Activity(type=discord.ActivityType.watching,  name=pres_msg)
    else:
        activity = discord.Game(name=pres_msg)

    await interaction.client.change_presence(activity=activity)

    # 4) Confirm
    confirm = discord.Embed(
        title="✅ Config & Presence Reloaded",
        description="Embeds, live views, and rich presence have all been updated!",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=confirm, ephemeral=True)

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