"""Registration and roster management commands."""

from __future__ import annotations

import asyncio
from typing import List, Optional, Sequence, Tuple

import discord
from discord import app_commands

from config import (
    _FULL_CFG,
    embed_from_cfg,
    get_checked_in_role,
    get_registered_role,
    get_unified_channel_name,
)
from core.components_traditional import update_unified_channel
from core.persistence import get_event_mode_for_guild, persisted, save_persisted
from helpers import EmbedHelper
from integrations.sheets import refresh_sheet_cache
from utils.utils import send_reminder_dms
from .common import (
    command_tracer,
    ensure_staff,
    handle_command_exception,
    localized_choice,
    logger,
    respond_with_message,
)


def register(gal: app_commands.Group) -> None:
    """Attach registration commands to the GAL command group."""

    @gal.command(name="toggle", description="Toggle registration or check-in status.")
    @app_commands.describe(
        system="Which system to toggle (registration or checkin)",
        silent="Toggle silently without announcements (default: False)",
    )
    @app_commands.choices(
        system=[
            localized_choice("registration", "registration"),
            localized_choice("checkin", "checkin"),
            localized_choice("both", "both"),
        ]
    )
    @command_tracer("gal.toggle")
    async def toggle(
        interaction: discord.Interaction,
        system: app_commands.Choice[str],
        silent: bool = False,
    ):
        """Toggle registration or check-in status."""
        if not await ensure_staff(interaction, context="Toggle Command"):
            return

        try:
            guild_id = str(interaction.guild.id)
            if guild_id not in persisted:
                persisted[guild_id] = {}

            system_value = system.value

            reg_open = persisted[guild_id].get("registration_open", False)
            ci_open = persisted[guild_id].get("checkin_open", False)

            if system_value == "registration":
                reg_open = not reg_open
                persisted[guild_id]["registration_open"] = reg_open
                status = f"Registration is now {'OPEN' if reg_open else 'CLOSED'}"
            elif system_value == "checkin":
                ci_open = not ci_open
                persisted[guild_id]["checkin_open"] = ci_open
                status = f"Check-in is now {'OPEN' if ci_open else 'CLOSED'}"
            else:
                reg_open = not reg_open
                ci_open = not ci_open
                persisted[guild_id]["registration_open"] = reg_open
                persisted[guild_id]["checkin_open"] = ci_open
                status = (
                    f"Registration: {'OPEN' if reg_open else 'CLOSED'}\n"
                    f"Check-in: {'OPEN' if ci_open else 'CLOSED'}"
                )

            save_persisted(persisted)
            await update_unified_channel(interaction.guild)

            if not silent:
                await _handle_toggle_pings(
                    interaction.guild,
                    system_value,
                    reg_open,
                    ci_open,
                    is_manual=True,
                )

            await respond_with_message(
                interaction,
                embed=discord.Embed(
                    title="🔁 System Toggled",
                    description=status,
                    color=discord.Color.green(),
                ),
            )

        except Exception as exc:
            await handle_command_exception(
                interaction,
                exc,
                context="Toggle Command",
            )

    @gal.command(
        name="event",
        description="View or set the event mode for this guild (normal/doubleup).",
    )
    @app_commands.describe(mode="Set the event mode (normal/doubleup)")
    @app_commands.choices(
        mode=[
            localized_choice("normal", "normal"),
            localized_choice("doubleup", "doubleup"),
        ]
    )
    @command_tracer("gal.event")
    async def event(
        interaction: discord.Interaction,
        mode: Optional[app_commands.Choice[str]] = None,
    ):
        """View or set event mode."""
        try:
            await interaction.response.defer(ephemeral=True)
            guild = interaction.guild
            guild_id = str(guild.id)

            current_mode = get_event_mode_for_guild(guild_id)

            if mode is None:
                embed = embed_from_cfg(
                    "event_mode_current",
                    mode=current_mode.capitalize(),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            if not await ensure_staff(interaction, context="Event Mode Command"):
                return

            new_mode = mode.value
            from core.persistence import set_event_mode_for_guild

            set_event_mode_for_guild(guild_id, new_mode)

            embed = embed_from_cfg(
                "event_mode_updated",
                mode=new_mode.capitalize(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as exc:
            await handle_command_exception(interaction, exc, "Event Mode Command")

    @gal.command(
        name="registeredlist",
        description="Show all registered users with check-in status.",
    )
    @command_tracer("gal.registeredlist")
    async def registered_list(interaction: discord.Interaction):
        """Display registered users list with check-in status."""
        if not await ensure_staff(
            interaction,
            context="Registered List Command",
        ):
            return

        try:
            await interaction.response.defer(ephemeral=True)
            guild_id = str(interaction.guild.id)
            mode = get_event_mode_for_guild(guild_id)

            from integrations.sheets import cache_lock, sheet_cache

            async with cache_lock:
                registered_rows = [
                    (tag, data)
                    for tag, data in sheet_cache["users"].items()
                    if str(data[2]).upper() == "TRUE"
                ]

            embed = _build_registered_embed(registered_rows, mode)
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as exc:
            await handle_command_exception(
                interaction,
                exc,
                "Registered List Command",
            )

    @gal.command(
        name="reminder",
        description="DM all registered users who are not checked in.",
    )
    @command_tracer("gal.reminder")
    async def reminder(interaction: discord.Interaction):
        """Send DM reminders to registered but unchecked users."""
        if not await ensure_staff(interaction, context="Reminder Command"):
            return

        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = str(interaction.guild.id)

            from helpers.sheet_helpers import SheetOperations
            from core.views import WaitlistRegistrationDMView

            _ = await SheetOperations.get_all_registered_users(guild_id)

            reg_role = discord.utils.get(
                interaction.guild.roles,
                name=get_registered_role(),
            )
            ci_role = discord.utils.get(
                interaction.guild.roles,
                name=get_checked_in_role(),
            )

            unchecked_users = []
            if reg_role and ci_role:
                unchecked_users = [
                    member
                    for member in reg_role.members
                    if ci_role not in member.roles
                ]

            if not unchecked_users:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="✅ All Checked In",
                        description="All registered users are already checked in!",
                        color=discord.Color.green(),
                    ),
                    ephemeral=True,
                )
                return

            dmmed = await send_reminder_dms(
                client=interaction.client,
                guild=interaction.guild,
                dm_embed=embed_from_cfg("reminder_dm"),
                view_cls=WaitlistRegistrationDMView,
            )

            sent_count = len(dmmed)
            total_unchecked = len(unchecked_users)

            summary_embed = discord.Embed(
                title="📬 Reminder Complete",
                description=(
                    f"Successfully sent DMs to **{sent_count}/{total_unchecked}** users."
                ),
                color=discord.Color.green(),
            )

            if sent_count > 0:
                mentions: List[str] = []
                for dm_info in dmmed:
                    if "(`" in dm_info and "`)" in dm_info:
                        start = dm_info.find("(`") + 2
                        end = dm_info.find("`)")
                        discord_tag = dm_info[start:end]
                        member = next(
                            (m for m in unchecked_users if str(m) == discord_tag),
                            None,
                        )
                        if member:
                            mentions.append(member.mention)

                if mentions:
                    if len(mentions) > 10:
                        overflow = len(mentions) - 10
                        mentions = mentions[:10] + [f"...and {overflow} more"]
                    summary_embed.add_field(
                        name="Reminded Users",
                        value="\n".join(mentions),
                        inline=False,
                    )

            await interaction.followup.send(embed=summary_embed, ephemeral=True)

        except Exception as exc:
            await handle_command_exception(interaction, exc, "Reminder Command")

    @gal.command(
        name="cache", description="Forces a manual refresh of the user cache from the Google Sheet."
    )
    @command_tracer("gal.cache")
    async def cache_refresh(interaction: discord.Interaction):
        """Force a cache refresh from Google Sheets."""
        if not await ensure_staff(interaction, context="Cache Command"):
            return

        try:
            await interaction.response.defer(ephemeral=True)

            await refresh_sheet_cache(force=True)
            await interaction.followup.send(
                "✅ Sheet cache refresh triggered.",
                ephemeral=True,
            )
        except Exception as exc:
            await handle_command_exception(interaction, exc, "Cache Command")


def _build_registered_embed(
    registered_rows: Sequence[Tuple[str, Sequence]],
    mode: str,
) -> discord.Embed:
    """Create the registered players embed view."""
    if not registered_rows:
        return discord.Embed(
            title="🗂️ Registered Players List",
            description="*No registered players found.*",
            color=discord.Color.blurple(),
        )

    lines = EmbedHelper.build_checkin_list_lines(registered_rows, mode)
    total_registered = len(registered_rows)
    total_checked_in = sum(
        1 for _, tpl in registered_rows if str(tpl[3]).upper() == "TRUE"
    )

    footer_parts: List[str] = [f"👥 Players: {total_registered}"]
    if mode == "doubleup":
        teams = {
            tpl[4]
            for _, tpl in registered_rows
            if len(tpl) > 4 and tpl[4]
        }
        if teams:
            footer_parts.append(f"🧪 Teams: {len(teams)}")

    footer_parts.append(f"✅ Checked-In: {total_checked_in}")
    if total_registered:
        footer_parts.append(
            f"📊 {total_checked_in / total_registered * 100:.1f}% checked in"
        )

    embed = discord.Embed(
        title="🗂️ Registered Players List",
        description="\n".join(lines) if lines else "No registered players found.",
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=" | ".join(footer_parts))
    return embed


async def _handle_toggle_pings(
    guild: discord.Guild,
    system_value: str,
    reg_open: bool,
    ci_open: bool,
    *,
    is_manual: bool,
) -> None:
    """
    Handle ping notifications when toggling systems.

    Parameters:
        guild: The guild where the toggle occurred
        system_value: "registration", "checkin", or "both"
        reg_open: Whether registration is currently open
        ci_open: Whether check-in is currently open
        is_manual: Whether this is a manual toggle (vs scheduled event)
    """
    if not is_manual:
        return

    try:
        from core.discord_events import recent_pings

        channel_name = get_unified_channel_name()
        unified_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not unified_channel:
            logger.warning(
                f"Unified channel '{channel_name}' not found in guild {guild.name}"
            )
            return

        roles_config = _FULL_CFG.get("roles", {})
        angel_role_name = roles_config.get("angel_role", "Angels")
        registered_role_name = roles_config.get("registered_role", "Registered")

        now_timestamp = discord.utils.utcnow().timestamp()
        last_ping = recent_pings.get(guild.id, 0)
        if now_timestamp - last_ping < 30:
            logger.info(
                f"Skipping ping for {system_value} in {guild.name} - recently pinged"
            )
            return

        messages_to_delete = []
        ping_sent = False

        if (system_value in ["registration", "both"]) and reg_open:
            if roles_config.get("ping_on_registration_open", True):
                angel_role = discord.utils.get(guild.roles, name=angel_role_name)
                if angel_role:
                    ping_msg = await unified_channel.send(
                        f"🛎️ **Registration is now OPEN!** {angel_role.mention}"
                    )
                    messages_to_delete.append(ping_msg)
                    ping_sent = True
                else:
                    logger.warning(
                        f"Angel role '{angel_role_name}' not found in guild {guild.name}"
                    )

        if (system_value in ["checkin", "both"]) and ci_open:
            if roles_config.get("ping_on_checkin_open", True):
                registered_role = discord.utils.get(
                    guild.roles,
                    name=registered_role_name,
                )
                if registered_role:
                    ping_msg = await unified_channel.send(
                        f"✅ **Check-in is now OPEN!** {registered_role.mention}"
                    )
                    messages_to_delete.append(ping_msg)
                    ping_sent = True
                else:
                    logger.warning(
                        f"Registered role '{registered_role_name}' not found in guild {guild.name}"
                    )

        if ping_sent:
            recent_pings[guild.id] = now_timestamp

        if messages_to_delete:
            await asyncio.sleep(5)
            for msg in messages_to_delete:
                try:
                    await msg.delete()
                except discord.NotFound:
                    continue
                except discord.Forbidden:
                    logger.warning(
                        f"Missing permissions to delete ping message in {guild.name}"
                    )
                except Exception as exc:
                    logger.error(f"Error deleting ping message: {exc}")

    except Exception as exc:
        logger.error(
            f"Error handling toggle pings for guild {guild.name}: {exc}",
            exc_info=True,
        )
