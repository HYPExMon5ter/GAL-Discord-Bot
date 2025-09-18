# helpers/embed_helpers.py

import logging
from datetime import datetime, timezone
from typing import List

import discord

from config import embed_from_cfg, get_log_channel_name, get_ping_user


async def log_error(bot, guild, message, level="Error"):
    """Log error to bot-log channel or console."""
    log_channel = None
    if guild:
        log_channel = discord.utils.get(guild.text_channels, name=get_log_channel_name())

    embed = embed_from_cfg("error")
    embed.description = message
    embed.timestamp = datetime.now(timezone.utc)
    embed.set_footer(text="GAL Bot")

    if log_channel:
        try:
            await log_channel.send(
                content=get_ping_user() if level == "Error" else None,
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
    def create_progress_bar(current: int, maximum: int, length: int = 20) -> str:
        """
        Create a visual progress bar using emoji.
        
        Args:
            current: Current value (e.g., registered players)
            maximum: Maximum value (e.g., max players) 
            length: Length of the progress bar in characters (default: 20)
            
        Returns:
            String with green filled squares and white empty squares
        """
        if maximum == 0:
            return "⬜" * length

        percentage = min(100, (current / maximum) * 100)
        filled_length = int(length * percentage / 100)

        return "🟩" * filled_length + "⬜" * (length - filled_length)

    @staticmethod
    def build_checkin_list_lines(checked_in_users: List[tuple], mode: str) -> List[str]:
        """
        Build formatted lines showing ALL registered users with check-in status.
        Shows ready teams first, then non-ready teams.
        """

        lines = []

        def is_true(v):
            return str(v).upper() == "TRUE"

        if mode == "doubleup":
            # Group by team
            teams = {}
            for tag, user_data in checked_in_users:
                # user_data is the full tuple (row, ign, reg, ci, team, alt, pronouns)
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
