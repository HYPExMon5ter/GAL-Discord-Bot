# helpers/embed_helpers.py
"""
Centralized helper functions for updating embeds across the bot.
"""

import discord
import logging
from typing import Optional, Callable, Dict, List
from datetime import datetime, timezone
from core.persistence import get_persisted_msg
from config import embed_from_cfg, LOG_CHANNEL_NAME, PING_USER

async def log_error(bot, guild, message, level="Error"):
    """Log error to bot-log channel or console."""
    log_channel = None
    if guild:
        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)

    embed = embed_from_cfg("error")
    embed.description = message
    embed.timestamp = datetime.now(timezone.utc)
    embed.set_footer(text="GAL Bot")

    if log_channel:
        try:
            await log_channel.send(
                content=PING_USER if level == "Error" else None,
                embed=embed
            )
        except Exception as e:
            logging.error(f"Failed to log to channel: {e}")
            logging.error(message)
    else:
        logging.error(message)

class EmbedHelper:
    """Helper class for managing Discord embeds."""

    @staticmethod
    async def update_persisted_embed(
            guild: discord.Guild,
            persist_key: str,
            update_func: Callable,
            error_context: str = "embed update"
    ) -> bool:
        """
        Generic helper to update any persisted embed.

        Args:
            guild: Discord guild
            persist_key: Key for persisted message (e.g., "registration", "checkin")
            update_func: Async function that takes (channel, msg_id, guild) as params
            error_context: Context string for error logging

        Returns:
            True if update was successful, False otherwise
        """
        chan_id, msg_id = get_persisted_msg(guild.id, persist_key)

        if not chan_id or not msg_id:
            return False

        channel = guild.get_channel(chan_id)
        if not channel:
            return False

        try:
            await update_func(channel, msg_id, guild)
            return True
        except Exception as e:
            await log_error(None, guild, f"[{error_context.upper()}] Failed to update {persist_key} embed: {e}")
            return False

    @staticmethod
    async def update_all_guild_embeds(guild: discord.Guild) -> Dict[str, bool]:
        """
        Update all live embeds for a guild.

        Returns:
            Dict mapping embed names to success status
        """
        # Import here to avoid circular imports
        from core.views import update_registration_embed, update_checkin_embed

        results = {}

        # Update registration embed
        results['registration'] = await EmbedHelper.update_persisted_embed(
            guild,
            "registration",
            update_registration_embed,
            "registration update"
        )

        # Update check-in embed
        results['checkin'] = await EmbedHelper.update_persisted_embed(
            guild,
            "checkin",
            update_checkin_embed,
            "checkin update"
        )

        return results

    @staticmethod
    async def create_persisted_embed(
            guild: discord.Guild,
            channel: discord.TextChannel,
            embed: discord.Embed,
            view: discord.ui.View,
            persist_key: str,
            pin: bool = True,
            announce_pin: bool = True
    ) -> Optional[discord.Message]:
        """
        Create and persist an embed message.

        Args:
            guild: Discord guild
            channel: Channel to send embed to
            embed: Embed to send
            view: View to attach to the message
            persist_key: Key to persist the message under
            pin: Whether to pin the message
            announce_pin: Whether to announce the pin

        Returns:
            The created message or None if failed
        """
        from core.persistence import set_persisted_msg

        try:
            msg = await channel.send(embed=embed, view=view)
            set_persisted_msg(guild.id, persist_key, channel.id, msg.id)

            if pin:
                await msg.pin()
                if announce_pin:
                    # Delete the "pinned a message" system message
                    async for m in channel.history(limit=5):
                        if m.type == discord.MessageType.pins_add:
                            try:
                                await m.delete()
                                break
                            except:
                                pass

            return msg
        except Exception as e:
            await log_error(None, guild, f"[CREATE-EMBED-ERROR] Failed to create {persist_key} embed: {e}")
            return None

    @staticmethod
    async def refresh_dm_views_for_users(
            guild: discord.Guild,
            discord_tags: Optional[List[str]] = None
    ) -> int:
        """
        Refresh DM action views for specified users or all cached users.

        Args:
            guild: Discord guild
            discord_tags: Optional list of specific discord tags to update.
                         If None, updates all users in cache.

        Returns:
            Number of successfully updated DMs
        """
        from integrations.sheets import sheet_cache, cache_lock
        from core.views import DMActionView
        from config import embed_from_cfg

        if discord_tags is None:
            async with cache_lock:
                discord_tags = list(sheet_cache["users"].keys())

        updated = 0
        rem_embed = embed_from_cfg("reminder_dm")
        rem_title = rem_embed.title

        for discord_tag in discord_tags:
            # Import resolve_member locally to avoid circular import
            from utils.utils import resolve_member

            member = resolve_member(guild, discord_tag)
            if not member:
                # User not in server, skip
                continue

            try:
                dm = await member.create_dm()
                async for msg in dm.history(limit=50):
                    if msg.author == guild.me and msg.embeds:
                        e = msg.embeds[0]
                        if e.title == rem_title:
                            await msg.edit(view=DMActionView(guild, member))
                            updated += 1
                            break
            except Exception:
                # Silently continue - user may have DMs disabled
                pass

        return updated

    @staticmethod
    def build_registration_list_lines(
            users: List[tuple],
            mode: str
    ) -> List[str]:
        """
        Build formatted lines for registration list display.

        Args:
            users: List of (discord_tag, ign, team_name) tuples
            mode: Event mode ("normal" or "doubleup")

        Returns:
            List of formatted lines
        """
        from itertools import groupby

        lines = []

        if mode == "doubleup":
            # Sort by team name
            users.sort(key=lambda x: (x[2] or "No Team").lower())

            for team, grp in groupby(users, key=lambda x: x[2] or "No Team"):
                members = list(grp)
                lines.append(f"👥 **{team}** ({len(members)})")
                for tag, ign, _ in members:
                    lines.append(f"> 👤 {tag}  |  {ign}")
                lines.append("")  # blank line between teams

            # Remove trailing blank line
            if lines and not lines[-1].strip():
                lines.pop()
        else:
            # Normal mode - flat list
            for tag, ign, _ in users:
                lines.append(f"👤 {tag}  |  {ign}")

        return lines

    @staticmethod
    def build_checkin_list_lines(
            checked_in_users: List[tuple],
            mode: str
    ) -> List[str]:
        """
        Build formatted lines for check-in list display.

        Args:
            checked_in_users: List of (discord_tag, (row, ign, reg, ci, team, alt)) tuples
            mode: Event mode ("normal" or "doubleup")

        Returns:
            List of formatted lines
        """
        from itertools import groupby

        lines = []

        if mode == "doubleup" and checked_in_users:
            # Sort by team name
            checked_in_users.sort(key=lambda item: (item[1][4] or "").lower())

            for team, grp in groupby(checked_in_users, key=lambda item: item[1][4] or "<No Team>"):
                members = list(grp)
                lines.append(f"👥 **{team}** ({len(members)})")
                for tag, tpl in members:
                    ign = tpl[1]
                    lines.append(f"> 👤 {tag}  |  {ign}")
                lines.append("")  # blank line between teams

            # Remove trailing blank line
            if lines and not lines[-1].strip():
                lines.pop()
        elif checked_in_users:
            # Normal mode - flat list
            for tag, tpl in checked_in_users:
                ign = tpl[1]
                lines.append(f"👤 {tag}  |  {ign}")

        return lines