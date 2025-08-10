# helpers/embed_helpers.py

"""
Centralized helper functions for updating embeds across the bot.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, List

import discord

from config import embed_from_cfg, LOG_CHANNEL_NAME, PING_USER
from core.persistence import get_persisted_msg


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
    def build_registration_list_lines(users: List[tuple], mode: str) -> List[str]:
        """
        Build formatted lines for registration list display with team completeness sorting.
        Full teams (2+ members) are shown first, then partial teams, then unassigned players.
        """
        import random

        lines = []

        if mode == "doubleup":
            # Group users by team
            teams_data = {}
            for tag, ign, team in users:
                team_key = team or "No Team"
                if team_key not in teams_data:
                    teams_data[team_key] = []
                teams_data[team_key].append((tag, ign))

            # Separate teams into categories
            full_teams = []  # Teams with 2+ members
            partial_teams = []  # Teams with 1 member
            no_team = None  # The "No Team" group

            for team_name, members in teams_data.items():
                if team_name == "No Team":
                    no_team = (team_name, members)
                elif len(members) >= 2:
                    full_teams.append((team_name, members))
                else:
                    partial_teams.append((team_name, members))

            # Sort each category by team name
            full_teams.sort(key=lambda x: x[0].lower())
            partial_teams.sort(key=lambda x: x[0].lower())

            # Combine in order: full teams first, then partial teams, then no team
            sorted_teams = full_teams + partial_teams
            if no_team:
                sorted_teams.append(no_team)

            # Emoji management for visual distinction
            team_emojis = ["🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "⚪", "⚫", "🟤",
                           "💙", "💚", "💛", "💜", "🧡", "❤️", "🤍", "🖤", "🤎"]
            used_emojis = []
            team_emoji_map = {}

            # Build the display lines
            for i, (team, members) in enumerate(sorted_teams):
                # Assign emoji for this team
                if team not in team_emoji_map:
                    # If we've used all emojis, start recycling intelligently
                    if len(used_emojis) >= len(team_emojis):
                        # Get the emoji used by previous team to avoid
                        avoid_emojis = []

                        # Check previous team's emoji
                        if i > 0:
                            prev_team = sorted_teams[i - 1][0]
                            if prev_team in team_emoji_map:
                                avoid_emojis.append(team_emoji_map[prev_team])

                        # Also avoid the next few recently used
                        avoid_emojis.extend(used_emojis[-3:])

                        # Pick a random emoji that's not in the avoid list
                        available = [e for e in team_emojis if e not in avoid_emojis]
                        if not available:  # Fallback if somehow all are to be avoided
                            available = team_emojis

                        emoji = random.choice(available)
                    else:
                        # First time through, use emojis in order
                        emoji = team_emojis[len(used_emojis)]

                    team_emoji_map[team] = emoji
                    used_emojis.append(emoji)

                emoji = team_emoji_map[team]

                # Format team header
                lines.append(f"{emoji} **{team}**")

                # Add team members
                lines.append("```css")
                for tag, ign in members:
                    lines.append(f"{tag} | {ign}")
                lines.append("```")

        else:
            # Normal mode - simple list
            lines.append("```css")
            lines.append("# Registered Players")
            lines.append("=" * 40)

            for i, (tag, ign, _) in enumerate(users, 1):
                lines.append(f"{i:2d}. {tag} | {ign}")

            lines.append("```")

        return lines

    @staticmethod
    def build_checkin_list_lines(checked_in_users: List[tuple], mode: str) -> List[str]:
        """
        Build formatted lines showing ALL registered users with check-in status.
        Shows ready teams first, then non-ready teams, all in a single list format.
        """

        lines = []

        def is_true(v):
            return str(v).upper() == "TRUE"

        if mode == "doubleup":
            # Group by team
            teams = {}
            for tag, user_data in checked_in_users:
                # user_data is the full tuple (row, ign, reg, ci, team, alt)
                team_name = user_data[4] if len(user_data) > 4 else "No Team"
                if not team_name:
                    team_name = "No Team"

                if team_name not in teams:
                    teams[team_name] = []
                teams[team_name].append((tag, user_data))

            # Separate teams into ready and not ready
            ready_teams = []
            not_ready_teams = []

            for team_name, members in teams.items():
                # Check if team has 2+ members AND all are checked in
                has_enough_members = len(members) >= 2
                all_checked_in = all(is_true(member[1][3]) for member in members)
                is_ready = has_enough_members and all_checked_in

                if is_ready:
                    ready_teams.append((team_name, members))
                else:
                    not_ready_teams.append((team_name, members))

            # Sort each group by team name
            ready_teams.sort(key=lambda x: x[0].lower())
            not_ready_teams.sort(key=lambda x: x[0].lower())

            # Combine ready teams first, then not ready teams
            all_teams = ready_teams + not_ready_teams

            # Display all teams in order (ready first, then not ready)
            for team_name, members in all_teams:
                # Check if team is ready for the checkmark
                has_enough_members = len(members) >= 2
                all_checked_in = all(is_true(member[1][3]) for member in members)
                is_ready = has_enough_members and all_checked_in

                team_check = "✅ " if is_ready else ""

                if team_name == "No Team":
                    team_display = f"{team_check}**Unassigned Players**"
                else:
                    team_display = f"{team_check}**{team_name}**"

                lines.append(f"{team_display}")
                lines.append("```css")

                for tag, tpl in members:
                    ign = tpl[1]
                    is_checked_in = is_true(tpl[3])
                    status = "🟢" if is_checked_in else "🔴"
                    lines.append(f"{status} {tag} | {ign}")

                lines.append("```")

        else:
            # Normal mode - show all registered users with check-in status
            lines.append("**📋 Player Check-In Status**")
            lines.append("```css")

            for i, (tag, tpl) in enumerate(checked_in_users, 1):
                ign = tpl[1]
                is_checked_in = is_true(tpl[3])
                status = "🟢" if is_checked_in else "🔴"
                lines.append(f"{status} [{i:02d}] {tag} | {ign}")

            lines.append("```")

        return lines