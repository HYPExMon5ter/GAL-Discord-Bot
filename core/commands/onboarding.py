"""Onboarding management commands."""

from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands

from config import (
    get_onboard_approval_role,
    get_onboard_review_channel,
)
from helpers import ErrorHandler

from .common import (
    command_tracer,
    ensure_staff,
    handle_command_exception,
)


def register(gal: app_commands.Group) -> None:
    """Register onboarding commands with the GAL command group."""

    @gal.command(
        name="onboard",
        description="Manage the onboarding system.",
    )
    @app_commands.describe(action="Action to perform (setup, stats, refresh)")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="setup", value="setup"),
            app_commands.Choice(name="stats", value="stats"),
            app_commands.Choice(name="refresh", value="refresh"),
        ]
    )
    @command_tracer("gal.onboard")
    async def onboard_cmd(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
    ):
        """Manage the onboarding system."""
        if not await ensure_staff(interaction, context="Onboard Command"):
            return

        try:
            action_value = action.value

            if action_value == "setup":
                from core.onboard import setup_onboard_channel

                await interaction.response.defer(ephemeral=True)

                success = await setup_onboard_channel(
                    interaction.guild,
                    interaction.client,
                )

                title = "✅ Onboard System Setup" if success else "⚠️ Setup Failed"
                description = (
                    "Onboard channels and embed have been set up successfully!"
                    if success
                    else "Failed to set up onboard system. Check bot permissions and logs."
                )
                color = discord.Color.green() if success else discord.Color.red()

                await interaction.followup.send(
                    embed=discord.Embed(
                        title=title,
                        description=description,
                        color=color,
                        timestamp=discord.utils.utcnow(),
                    ),
                    ephemeral=True,
                )

            elif action_value == "stats":
                from helpers.onboard_helpers import OnboardManager

                pending_submissions = OnboardManager.get_pending_submissions()
                pending_count = len(pending_submissions)

                approval_role = discord.utils.get(
                    interaction.guild.roles,
                    name=get_onboard_approval_role(),
                )
                approved_count = len(approval_role.members) if approval_role else 0

                embed = discord.Embed(
                    title="📊 Onboarding Statistics",
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow(),
                )
                embed.add_field(
                    name="📝 Pending Submissions",
                    value=str(pending_count),
                    inline=True,
                )
                embed.add_field(
                    name="✅ Approved Members",
                    value=str(approved_count),
                    inline=True,
                )

                if pending_count > 0:
                    pending_list = []
                    for user_id in list(pending_submissions.keys())[:5]:
                        member: Optional[discord.Member] = interaction.guild.get_member(
                            user_id
                        )
                        if member:
                            pending_list.append(f"• {member.mention}")
                        else:
                            pending_list.append(f"• <@{user_id}> (left server)")

                    if pending_count > 5:
                        pending_list.append(f"• … and {pending_count - 5} more")

                    embed.add_field(
                        name="Recent Pending",
                        value="\n".join(pending_list),
                        inline=False,
                    )

                await interaction.response.send_message(embed=embed, ephemeral=True)

            elif action_value == "refresh":
                from core.onboard import setup_onboard_channel
                from helpers.onboard_helpers import (
                    rebuild_pending_submissions_from_history,
                )

                await interaction.response.defer(ephemeral=True)

                review_channel = discord.utils.get(
                    interaction.guild.text_channels,
                    name=get_onboard_review_channel(),
                )

                if review_channel:
                    await rebuild_pending_submissions_from_history(review_channel)

                success = await setup_onboard_channel(
                    interaction.guild,
                    interaction.client,
                )

                await interaction.followup.send(
                    embed=discord.Embed(
                        title="🔄 Onboard System Refreshed",
                        description=(
                            "Onboard system has been refreshed and state rebuilt "
                            "from message history."
                        ),
                        color=discord.Color.green()
                        if success
                        else discord.Color.orange(),
                        timestamp=discord.utils.utcnow(),
                    ),
                    ephemeral=True,
                )

        except Exception as exc:
            await handle_command_exception(
                interaction,
                exc,
                "Onboard Command",
            )


__all__ = ["register"]
