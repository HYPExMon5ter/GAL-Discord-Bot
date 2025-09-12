# utils/utils.py

import asyncio
import logging
import re
import urllib.parse
from typing import List, Optional, Callable

import aiohttp
import discord

from config import (
    embed_from_cfg, get_sheet_settings, get_checked_in_role
)
from core.persistence import get_event_mode_for_guild
from integrations.sheets import (
    get_sheet_for_guild, retry_until_successful
)


class UtilsError(Exception):
    """Custom exception for utils-related errors."""
    pass


class MemberNotFoundError(UtilsError):
    """Exception for when a Discord member cannot be found."""
    pass


# Backward compatibility functions
def has_allowed_role(member: discord.Member) -> bool:
    """Check if a member has any of the staff roles."""
    from helpers import RoleManager
    return RoleManager.has_any_allowed_role(member)


def has_allowed_role_from_interaction(interaction: discord.Interaction) -> bool:
    """Check interaction.user's roles for permission."""
    from helpers import RoleManager
    return RoleManager.has_allowed_role_from_interaction(interaction)


def resolve_member(guild: discord.Guild, discord_tag: str) -> Optional[discord.Member]:
    """
    Find a Member in guild by tag, name, or display name.
    """
    if not guild or not discord_tag:
        return None

    discord_tag = discord_tag.strip()

    # Try exact tag match first (most reliable)
    if "#" in discord_tag:
        name, discrim = discord_tag.rsplit("#", 1)
        member = discord.utils.get(guild.members, name=name, discriminator=discrim)
        if member:
            return member

    # Try exact name matches
    member = discord.utils.get(guild.members, name=discord_tag)
    if member:
        return member

    # Try exact display name matches
    member = discord.utils.get(guild.members, display_name=discord_tag)
    if member:
        return member

    # Try case-insensitive matches
    for member in guild.members:
        if (member.name.lower() == discord_tag.lower() or
                member.display_name.lower() == discord_tag.lower()):
            return member

    logging.debug(f"Could not resolve member: {discord_tag} in guild {guild.name}")
    return None


async def clear_user_dms(member: discord.Member, bot_user: discord.User) -> int:
    """
    Clear all previous DMs sent by the bot to a user.
    """
    deleted_count = 0

    try:
        dm_channel = await member.create_dm()

        # Delete all bot messages in the DM channel
        async for message in dm_channel.history(limit=100):
            if message.author.id == bot_user.id:
                try:
                    await message.delete()
                    deleted_count += 1
                except discord.Forbidden:
                    # Can't delete this message, skip it
                    pass
                except discord.NotFound:
                    # Message already deleted
                    pass
                except Exception as e:
                    logging.warning(f"Failed to delete DM message: {e}")

    except discord.Forbidden:
        logging.debug(f"Cannot access DM channel for {member}")
    except Exception as e:
        logging.error(f"Error clearing DMs for {member}: {e}")

    return deleted_count


async def send_reminder_dms(
        client: discord.Client,
        guild: discord.Guild,
        dm_embed: discord.Embed,
        view_cls: type[discord.ui.View],
        skip_member_resolution: bool = False
) -> List[str]:
    """
    Send DM reminders to registered but not checked-in users.
    Clears previous DMs before sending new ones.
    """
    if not guild or not dm_embed or not view_cls:
        raise ValueError("Guild, embed, and view class are required")

    try:
        from integrations.sheets import sheet_cache, cache_lock

        dmmed: List[str] = []
        failed_dms = 0

        async with cache_lock:
            cache_snapshot = dict(sheet_cache["users"])

        for discord_tag, user_tuple in cache_snapshot.items():
            try:
                # Check if user is registered but not checked in
                if len(user_tuple) < 4:
                    continue

                is_reg = str(user_tuple[2]).upper() == "TRUE"
                is_ci = str(user_tuple[3]).upper() == "TRUE"

                if not (is_reg and not is_ci):
                    continue

                # FIXED: Skip member resolution if requested (during channel toggles)
                if skip_member_resolution:
                    continue

                # Try to get member - if they're not in server, skip silently
                member = resolve_member(guild, discord_tag)
                if not member:
                    # User not in server anymore, skip without logging
                    continue

                try:
                    # Clear previous DMs
                    deleted = await clear_user_dms(member, client.user)
                    if deleted > 0:
                        logging.debug(f"Cleared {deleted} previous DMs for {discord_tag}")

                    # Send new DM
                    view = view_cls(guild, member)
                    await member.send(embed=dm_embed, view=view)
                    dmmed.append(f"{member} (`{discord_tag}`)")

                except discord.Forbidden:
                    logging.debug(f"Cannot DM {discord_tag} - DMs disabled or blocked")
                    failed_dms += 1
                except discord.HTTPException as e:
                    logging.warning(f"Failed to DM {discord_tag}: {e}")
                    failed_dms += 1
                except Exception as e:
                    logging.error(f"Unexpected error DMing {discord_tag}: {e}")
                    failed_dms += 1

            except Exception as e:
                logging.error(f"Error processing reminder for {discord_tag}: {e}")
                continue

        logging.info(f"Sent {len(dmmed)} reminder DMs, {failed_dms} failed")
        return dmmed

    except Exception as e:
        raise UtilsError(f"Failed to send reminder DMs: {e}")


async def toggle_checkin_for_member(
        interaction: discord.Interaction,
        checkin_fn: Callable,
        success_key: str,
) -> None:
    """
    Toggle check-in status for a member.
    """
    try:
        # Import here to avoid circular import
        from core.views import update_checkin_embed
        from helpers import RoleManager, ErrorHandler, EmbedHelper

        logging.debug(f"Toggle check-in: fn={checkin_fn.__name__} user={interaction.user} guild={interaction.guild.id}")

        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=True)

        guild = interaction.guild
        member = interaction.user

        if not guild or not member:
            raise UtilsError("Guild and member are required")

        # Validate user is registered
        if not RoleManager.is_registered(member):
            await interaction.followup.send(
                embed=embed_from_cfg("registration_required"),
                ephemeral=True
            )
            return

        # Perform sheet operation
        discord_tag = str(member)
        success = await checkin_fn(discord_tag, guild_id=str(guild.id))

        logging.debug(f"Check-in operation result: {success}")

        if success:
            # Update Discord role
            if success_key == "checked_in":
                await RoleManager.add_role(member, get_checked_in_role())
            else:
                await RoleManager.remove_role(member, get_checked_in_role())

        # Send feedback
        embed_key = success_key if success else "error"
        response_embed = embed_from_cfg(embed_key)
        await interaction.followup.send(embed=response_embed, ephemeral=True)

        # Update persisted embed
        if success:
            await EmbedHelper.update_persisted_embed(
                guild,
                "checkin",
                lambda ch, mid, g: update_checkin_embed(ch, mid, g),
                "checkin update"
            )

    except Exception as e:
        from helpers import ErrorHandler
        await ErrorHandler.handle_interaction_error(
            interaction, e, "Check-in Toggle",
            "Failed to update check-in status"
        )


async def update_dm_action_views(guild: discord.Guild) -> None:
    """
    Refresh DM action views for all users.
    """
    try:
        from helpers import EmbedHelper
        # Skip member resolution during channel toggles
        await EmbedHelper.refresh_dm_views_for_users(guild)
    except Exception as e:
        logging.error(f"Failed to update DM action views for guild {guild.id}: {e}")


async def hyperlink_lolchess_profile(discord_tag: str, guild_id: str) -> None:
    """
    Create hyperlink for lolchess profile in sheet.
    """
    if not discord_tag or not guild_id:
        logging.warning("Discord tag and guild ID are required for hyperlinking")
        return

    try:
        from integrations.sheets import sheet_cache

        user_data = sheet_cache["users"].get(discord_tag)
        if not user_data:
            logging.debug(f"No user data found for hyperlinking: {discord_tag}")
            return

        row, ign = user_data[0], user_data[1]
        if not ign:
            logging.debug(f"No IGN found for user: {discord_tag}")
            return

        # Clean IGN of Unicode control characters
        def clean_ign(s: str) -> str:
            return re.sub(r'[\u2066-\u2069]', '', s).strip()

        ign_clean = clean_ign(ign)
        if not ign_clean:
            logging.debug(f"IGN became empty after cleaning: {ign}")
            return

        # Build lolchess URL - correct format: https://lolchess.gg/profile/na/name-tag/
        name, _, tag = ign_clean.partition("#")
        name_encoded = urllib.parse.quote(name.strip(), safe="-")
        
        # Use profile path and format with dash instead of slash
        if tag:
            formatted_name = f"{name_encoded}-{urllib.parse.quote(tag.strip(), safe='-')}"
        else:
            formatted_name = name_encoded
            
        profile_url = f"https://lolchess.gg/profile/na/{formatted_name}/"

        # Verify profile exists
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(profile_url, allow_redirects=True, timeout=10) as resp:
                    if resp.url.path.startswith("/search"):
                        logging.debug(f"Profile not found for IGN: {ign_clean}")
                        return
            except asyncio.TimeoutError:
                logging.warning(f"Timeout checking profile for: {ign_clean}")
                return
            except Exception as e:
                logging.warning(f"Error checking profile for {ign_clean}: {e}")
                return

        # Update sheet with hyperlink
        mode = get_event_mode_for_guild(guild_id)
        settings = get_sheet_settings(mode)
        sheet = await get_sheet_for_guild(guild_id, "GAL Database")

        formula = f'=HYPERLINK("{profile_url}","{ign_clean}")'

        await retry_until_successful(
            sheet.update_acell,
            f"{settings['ign_col']}{row}",
            formula
        )

        logging.info(f"Successfully hyperlinked profile for {discord_tag}: {ign_clean}")

    except Exception as e:
        logging.error(f"Failed to hyperlink profile for {discord_tag}: {e}")
