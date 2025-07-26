# gal_discord_bot/commands.py

import time
from itertools import groupby
from typing import Optional

import discord
from discord import app_commands

from config import (
    embed_from_cfg, CHECK_IN_CHANNEL, REGISTRATION_CHANNEL,
    REGISTERED_ROLE, ANGEL_ROLE, col_to_index
)
from logging_utils import log_error
from persistence import (
    get_event_mode_for_guild, set_event_mode_for_guild
)
from riot_api import tactics_tools_get_latest_placement
from sheets import (
    sheet_cache, cache_lock, refresh_sheet_cache, ordinal_suffix, retry_until_successful, get_sheet_for_guild
)
from utils import (
    has_allowed_role_from_interaction,
    toggle_persisted_channel, send_reminder_dms,
)
from views import (
    update_live_embeds, PersistentRegisteredListView, DMActionView
)

gal = app_commands.Group(
    name="gal",
    description="Group of GAL bot commands"
)

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
        await interaction.response.send_message("Invalid channel type! Use `registration` or `checkin`.", ephemeral=True)

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
        return await interaction.response.send_message(
            embed=embed_from_cfg("permission_denied"), ephemeral=True
        )

    await interaction.response.defer(ephemeral=False)

    dm_embed = embed_from_cfg("reminder_dm")
    guild    = interaction.guild

    # <-- NEW: single call to helper -->
    dmmed = await send_reminder_dms(
        client=interaction.client,
        guild=guild,
        dm_embed=dm_embed,
        view_cls=DMActionView
    )

    # Summarize
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

@gal.command(
    name="validate",
    description="Validate checked-in IGNs by verifying they’ve a recent TFT placement."
)
async def validate(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    valid, invalid = [], []
    async with cache_lock:
        for discord_tag, user_row in sheet_cache["users"].items():
            ign, checked = user_row[1], user_row[3]
            if str(checked).strip().upper() != "TRUE":
                continue

            try:
                placement = await tactics_tools_get_latest_placement(ign, str(interaction.guild.id))
            except Exception as e:
                await log_error(
                    interaction.client, interaction.guild,
                    f"[VALIDATE] Error scraping `{ign}`: {e}"
                )
                invalid.append(f"`{discord_tag}` — `{ign}`: **Error**")
                continue

            # real player if we got an integer back
            if isinstance(placement, int):
                valid.append(f"`{discord_tag}` — `{ign}`")
            else:
                invalid.append(f"`{discord_tag}` — `{ign}`: **IGN not found or no recent matches**")

    # Build embed description & color
    if not (valid or invalid):
        description = "No checked-in users to validate."
        color = discord.Color.light_grey()
    else:
        parts = []
        if valid:
            parts.append("**✅ Valid (played recently):**")
            parts.extend(valid)
        if invalid:
            parts.append("\n**❌ Invalid or no recent matches:**")
            parts.extend(invalid)
        description = "\n".join(parts)
        color = (
            discord.Color.green() if valid and not invalid else
            discord.Color.orange() if valid else
            discord.Color.red()
        )

    embed = discord.Embed(
        title="IGN Validation Results",
        description=description,
        color=color
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

@gal.command(
    name="placements",
    description="Show latest TFT placements for checked-in players."
)
@app_commands.describe(
    round="(Optional) Double-up round number (1–4)."
)
async def placements(
    interaction: discord.Interaction,
    round: Optional[int] = None
):
    # 1) Defer
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    gid   = str(guild.id)
    mode  = get_event_mode_for_guild(gid)

    # 2) DOUBLE-UP MODE
    if mode == "doubleup":
        # If a round was given, update that column in the "Lobbies" tab
        if round in (1,2,3,4):
            lobby_sheet = get_sheet_for_guild(gid, "Lobbies")
            # Map rounds → (IGN col, Placement col)
            cols = {
                1: ("C", "D"),
                2: ("G", "H"),
                3: ("K", "L"),
                4: ("O", "P"),
            }
            ign_col_letter, place_col_letter = cols[round]
            ign_idx   = col_to_index(ign_col_letter)
            place_idx = col_to_index(place_col_letter)

            # Fetch all IGN values once
            igns = await retry_until_successful(lobby_sheet.col_values, ign_idx)

            # For each IGN cell (skip header at row 1–2), scrape and write
            for row_num, ign in enumerate(igns, start=1):
                if row_num <= 2:
                    continue
                ign = ign.strip()
                if not ign:
                    continue
                try:
                    mode = get_event_mode_for_guild(gid)
                    placement = await tactics_tools_get_latest_placement(ign, str(guild.id))
                    val = str(placement) if isinstance(placement, int) else ""
                    await retry_until_successful(
                        lobby_sheet.update_acell,
                        f"{place_col_letter}{row_num}",
                        val
                    )
                except Exception:
                    # skip errors silently
                    continue

        # Now build the embed, grouping by team
        async with cache_lock:
            players = [
                {"team": tpl[4] or "No Team",
                 "discord_tag": tag,
                 "ign": tpl[1],
                 "placement": await tactics_tools_get_latest_placement(tpl[1], str(guild.id))}
                for tag, tpl in sheet_cache["users"].items()
                if tpl[3].upper() == "TRUE"
            ]

        # Sort & group by team
        players.sort(key=lambda p: (p["team"].lower(), p["discord_tag"].lower()))
        embed = discord.Embed(
            title="🗺️ Double-Up Placements",
            color=discord.Color.blue()
        )
        for team, group in groupby(players, key=lambda p: p["team"]):
            lines = []
            for p in group:
                pl = p["placement"]
                if isinstance(pl, int):
                    suffix = ordinal_suffix(pl)
                    pl_str = f"{pl}{suffix}"
                else:
                    pl_str = "N/A"
                lines.append(f"`{p['discord_tag']}` (`{p['ign']}`): **{pl_str}**")
            embed.add_field(name=team, value="\n".join(lines), inline=False)

        return await interaction.followup.send(embed=embed, ephemeral=True)

    # 3) NORMAL MODE (or no round arg)
    # Existing behavior: list all checked-in players with their latest normal placement
    lines = []
    async with cache_lock:
        for discord_tag, tpl in sheet_cache["users"].items():
            ign, checked = tpl[1], tpl[3]
            if checked.upper() != "TRUE":
                continue
            try:
                placement = await tactics_tools_get_latest_placement(ign, str(guild.id))
            except Exception:
                lines.append(f"`{discord_tag}` — `{ign}`: **Error**")
                continue
            if isinstance(placement, int):
                suffix = ordinal_suffix(placement)
                lines.append(f"`{discord_tag}` — `{ign}`: **{placement}{suffix} place**")
            else:
                lines.append(f"`{discord_tag}` — `{ign}`: **No recent matches**")

    desc = "\n".join(lines) or "No checked-in players to show placements for."
    embed = discord.Embed(
        title="📈 Checked-In Players Latest TFT Placements",
        description=desc,
        color=discord.Color.blue()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

@gal.command(name="reload", description="Reloads config, updates live embeds, and refreshes rich presence.")
async def reload_cmd(interaction: discord.Interaction):
    # 1) Permission guard
    if not has_allowed_role_from_interaction(interaction):
        return await interaction.response.send_message(
            embed=embed_from_cfg("permission_denied"),
            ephemeral=True
        )

    # 2) Re-read the entire config.yaml into memory
    import yaml
    from config import _FULL_CFG, EMBEDS_CFG, SHEET_CONFIG

    with open("config.yaml", "r", encoding="utf-8") as f:
        new_cfg = yaml.safe_load(f)

    # Overwrite in-place so all modules see the update
    _FULL_CFG.clear()
    _FULL_CFG.update(new_cfg)

    EMBEDS_CFG.clear()
    EMBEDS_CFG.update(_FULL_CFG.get("embeds", {}))

    SHEET_CONFIG.clear()
    SHEET_CONFIG.update(_FULL_CFG.get("sheet_configuration", {}))

    # 3) Update all persisted/live embeds in every guild
    for guild in interaction.client.guilds:
        await update_live_embeds(guild)

    # 4) Refresh rich presence from config.yaml → top‐level "rich_presence" key
    presence_cfg = _FULL_CFG.get("rich_presence", {})
    pres_type = presence_cfg.get("type", "PLAYING").upper()
    pres_msg  = presence_cfg.get("message", "")

    if pres_type == "LISTENING":
        activity = discord.Activity(
            type=discord.ActivityType.listening, name=pres_msg
        )
    elif pres_type == "WATCHING":
        activity = discord.Activity(
            type=discord.ActivityType.watching, name=pres_msg
        )
    else:
        activity = discord.Game(name=pres_msg)

    await interaction.client.change_presence(activity=activity)

    # 5) Confirm back to the invoker
    confirm = discord.Embed(
        title="✅ Configuration Reloaded",
        description="All embeds, live views, and rich presence have been updated!",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=confirm, ephemeral=True)

@gal.command(name="help", description="Shows this help message.")
async def help_cmd(interaction: discord.Interaction):
    from config import EMBEDS_CFG
    cfg = EMBEDS_CFG.get("help", {})
    help_embed = discord.Embed(
        title=cfg.get("title", "GAL Bot Help"),
        description=cfg.get("description", ""),
        color=discord.Color.blurple()
    )
    from config import GAL_COMMAND_IDS
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

from discord.ext import commands
async def setup(bot: commands.Bot):
    bot.tree.add_command(gal)