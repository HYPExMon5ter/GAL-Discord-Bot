# core/onboard.py

import logging
from typing import Optional

import discord
from discord import app_commands

from config import (
    onboard_embed_from_cfg, get_onboard_main_channel,
    get_onboard_review_channel, get_onboard_approval_role,
    get_onboard_denial_role, get_log_channel_name
)
from helpers.onboard_helpers import (
    OnboardManager, ensure_onboard_channels,
    rebuild_pending_submissions_from_history
)
from helpers.role_helpers import RoleManager
from helpers.embed_helpers import log_error


class OnboardView(discord.ui.View):
    """View with Start Onboarding button for the main channel."""

    def __init__(self, guild_id: int = None):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.add_item(StartOnboardingButton(guild_id))

    @classmethod
    def create_persistent(cls, guild: discord.Guild) -> 'OnboardView':
        """Create a persistent version for registration with the client."""
        return cls(guild_id=guild.id)


class StartOnboardingButton(discord.ui.Button):
    """Button to start the onboarding process."""

    def __init__(self, guild_id: int = None):
        # Create unique custom_id for persistence
        custom_id = f"start_onboarding_{guild_id}" if guild_id else "start_onboarding"
        super().__init__(
            label="Start Onboarding",
            style=discord.ButtonStyle.primary,
            emoji="🌸",
            custom_id=custom_id
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle button click to start onboarding."""
        try:
            member = interaction.user
            if not isinstance(member, discord.Member):
                await interaction.response.send_message(
                    "This feature is only available in servers.",
                    ephemeral=True
                )
                return

            # Check eligibility
            is_eligible, reason = OnboardManager.is_eligible_for_onboarding(member)

            if not is_eligible:
                # Send appropriate response based on reason
                embed = onboard_embed_from_cfg(reason)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Show onboarding modal
            modal = OnboardModal()
            await interaction.response.send_modal(modal)

        except Exception as e:
            logging.error(f"Error in start onboarding button: {e}")
            await log_error(interaction.client, interaction.guild,
                          f"Error in start onboarding button: {e}")

            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while starting onboarding. Please try again later.",
                        ephemeral=True
                    )
            except Exception:
                pass


class OnboardModal(discord.ui.Modal):
    """Modal for collecting onboarding information."""

    def __init__(self):
        super().__init__(title="Guardian Angel League Onboarding")

        # Add input fields
        self.name_input = discord.ui.TextInput(
            label="Name",
            placeholder="What should we call you?",
            required=True,
            max_length=50
        )
        self.add_item(self.name_input)

        self.pronouns_input = discord.ui.TextInput(
            label="Pronouns",
            placeholder="e.g. she/her, he/him, they/them",
            required=True,
            max_length=20
        )
        self.add_item(self.pronouns_input)

        self.socials_input = discord.ui.TextInput(
            label="Socials",
            placeholder="Social media handles, streaming accounts, etc.",
            required=True,
            max_length=200,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.socials_input)

        self.how_heard_input = discord.ui.TextInput(
            label="How did you hear about us?",
            placeholder="Optional: How did you discover Guardian Angel League?",
            required=False,
            max_length=500,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.how_heard_input)

        self.about_input = discord.ui.TextInput(
            label="About You",
            placeholder="Optional: Tell us a bit about yourself",
            required=False,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.about_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission."""
        try:
            member = interaction.user
            if not isinstance(member, discord.Member):
                await interaction.response.send_message(
                    "This feature is only available in servers.",
                    ephemeral=True
                )
                return

            # Double-check eligibility (in case status changed)
            is_eligible, reason = OnboardManager.is_eligible_for_onboarding(member)
            if not is_eligible:
                embed = onboard_embed_from_cfg(reason)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Collect submission data
            submission_data = {
                'name': self.name_input.value.strip(),
                'pronouns': self.pronouns_input.value.strip(),
                'socials': self.socials_input.value.strip(),
                'how_heard': self.how_heard_input.value.strip() if self.how_heard_input.value else None,
                'about': self.about_input.value.strip() if self.about_input.value else None,
                'discord_tag': f"{member.name}#{member.discriminator}" if member.discriminator != "0" else member.name,
                'discord_id': member.id,
                'guild_id': interaction.guild.id
            }

            # Add to pending submissions
            OnboardManager.add_pending_submission(member.id, submission_data)

            # Send to review channel
            await self._send_review_embed(interaction, submission_data)

            # Confirm submission to user
            embed = onboard_embed_from_cfg("pending_review")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            logging.info(f"Onboard submission received from {member} ({member.id})")

        except Exception as e:
            logging.error(f"Error handling onboard submission: {e}")
            await log_error(interaction.client, interaction.guild,
                          f"Error handling onboard submission from {member}: {e}")

            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while processing your submission. Please try again later.",
                        ephemeral=True
                    )
            except Exception:
                pass

    async def _send_review_embed(self, interaction: discord.Interaction, submission_data: dict):
        """Send review embed to staff channel."""
        try:
            # Get review channel
            review_channel_name = get_onboard_review_channel()
            review_channel = discord.utils.get(
                interaction.guild.text_channels,
                name=review_channel_name
            )

            if not review_channel:
                logging.error(f"Review channel '{review_channel_name}' not found")
                return

            # Create review embed
            embed = onboard_embed_from_cfg("review")

            # Add fields with submission data
            embed.add_field(
                name="👤 Name",
                value=submission_data['name'],
                inline=True
            )
            embed.add_field(
                name="🔤 Pronouns",
                value=submission_data['pronouns'],
                inline=True
            )
            embed.add_field(
                name="📱 Socials",
                value=submission_data['socials'],
                inline=False
            )

            if submission_data['how_heard']:
                embed.add_field(
                    name="📢 How they heard about us",
                    value=submission_data['how_heard'],
                    inline=False
                )

            if submission_data['about']:
                embed.add_field(
                    name="📝 About them",
                    value=submission_data['about'],
                    inline=False
                )

            # Set footer with user info
            embed.set_footer(
                text=f"User: {submission_data['discord_tag']} ({submission_data['discord_id']})"
            )

            # Add timestamp
            embed.timestamp = discord.utils.utcnow()

            # Create review view with approve/deny buttons
            view = ReviewView(submission_data['discord_id'], submission_data['guild_id'])

            # Send to review channel
            message = await review_channel.send(embed=embed, view=view)

            # Update submission data with message info
            submission_data['review_message_id'] = message.id
            submission_data['review_channel_id'] = review_channel.id

            logging.info(f"Sent onboard review embed for {submission_data['discord_tag']}")

        except Exception as e:
            logging.error(f"Error sending review embed: {e}")
            raise


class ReviewView(discord.ui.View):
    """View with approve/deny buttons for staff review."""

    def __init__(self, user_id: int, guild_id: int = None):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.guild_id = guild_id
        self.add_item(ApproveButton(user_id, guild_id))
        self.add_item(DenyButton(user_id, guild_id))

    @classmethod
    def create_persistent(cls, user_id: int, guild_id: int) -> 'ReviewView':
        """Create a persistent version for registration with the client."""
        return cls(user_id=user_id, guild_id=guild_id)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        """Handle errors in review buttons."""
        logging.error(f"Error in review view: {error}")
        await log_error(interaction.client, interaction.guild,
                      f"Error in onboard review view: {error}")


class ApproveButton(discord.ui.Button):
    """Button to approve onboarding submission."""

    def __init__(self, user_id: int, guild_id: int = None):
        # Create unique custom_id for persistence
        custom_id = f"approve_onboard_{user_id}_{guild_id}" if guild_id else f"approve_onboard_{user_id}"
        super().__init__(
            label="Approve",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=custom_id
        )
        self.target_user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        """Handle approval."""
        try:
            # Check staff permissions
            if not RoleManager.has_any_allowed_role(interaction.user):
                await interaction.response.send_message(
                    "You don't have permission to review onboarding submissions.",
                    ephemeral=True
                )
                return

            # Get the user ID from the view
            view = self.view
            if not isinstance(view, ReviewView):
                await interaction.response.send_message(
                    "Error: Could not determine user ID.",
                    ephemeral=True
                )
                return

            user_id = view.user_id

            # Get the member
            member = interaction.guild.get_member(user_id)
            if not member:
                await interaction.response.send_message(
                    "Error: User is no longer in the server.",
                    ephemeral=True
                )
                return

            # Remove from pending submissions
            submission_data = OnboardManager.remove_pending_submission(user_id)

            # Assign approval role
            approval_role = get_onboard_approval_role()
            success = await RoleManager.add_role(member, approval_role)

            if success:
                # Update embed to show approved
                embed = interaction.message.embeds[0]
                embed.color = discord.Color.green()
                embed.add_field(
                    name="✅ Status",
                    value=f"Approved by {interaction.user.mention}",
                    inline=False
                )

                # Disable buttons
                for item in view.children:
                    item.disabled = True

                await interaction.response.edit_message(embed=embed, view=view)

                # Send DM to user
                try:
                    dm_embed = onboard_embed_from_cfg("approved")
                    await member.send(embed=dm_embed)
                except discord.Forbidden:
                    logging.warning(f"Could not DM approval to {member}")

                # Log to bot log
                log_channel = discord.utils.get(
                    interaction.guild.text_channels,
                    name=get_log_channel_name()
                )
                if log_channel:
                    log_embed = discord.Embed(
                        title="✅ Onboarding Approved",
                        description=f"{member.mention} was approved for onboarding by {interaction.user.mention}",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    await log_channel.send(embed=log_embed)

                logging.info(f"Approved onboarding for {member} by {interaction.user}")

            else:
                await interaction.response.send_message(
                    f"Error: Could not assign '{approval_role}' role to {member.mention}.",
                    ephemeral=True
                )

        except Exception as e:
            logging.error(f"Error approving onboard submission: {e}")
            await log_error(interaction.client, interaction.guild,
                          f"Error approving onboard submission: {e}")

            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while approving the submission.",
                        ephemeral=True
                    )
            except Exception:
                pass


class DenyButton(discord.ui.Button):
    """Button to deny onboarding submission."""

    def __init__(self, user_id: int, guild_id: int = None):
        # Create unique custom_id for persistence
        custom_id = f"deny_onboard_{user_id}_{guild_id}" if guild_id else f"deny_onboard_{user_id}"
        super().__init__(
            label="Deny",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            custom_id=custom_id
        )
        self.target_user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        """Handle denial."""
        try:
            # Check staff permissions
            if not RoleManager.has_any_allowed_role(interaction.user):
                await interaction.response.send_message(
                    "You don't have permission to review onboarding submissions.",
                    ephemeral=True
                )
                return

            # Get the user ID from the view
            view = self.view
            if not isinstance(view, ReviewView):
                await interaction.response.send_message(
                    "Error: Could not determine user ID.",
                    ephemeral=True
                )
                return

            user_id = view.user_id

            # Get the member
            member = interaction.guild.get_member(user_id)
            if not member:
                await interaction.response.send_message(
                    "Error: User is no longer in the server.",
                    ephemeral=True
                )
                return

            # Remove from pending submissions
            submission_data = OnboardManager.remove_pending_submission(user_id)

            # Assign denial role (Supporter)
            denial_role = get_onboard_denial_role()
            success = await RoleManager.add_role(member, denial_role)

            if success:
                # Update embed to show denied
                embed = interaction.message.embeds[0]
                embed.color = discord.Color.red()
                embed.add_field(
                    name="❌ Status",
                    value=f"Denied by {interaction.user.mention}",
                    inline=False
                )

                # Disable buttons
                for item in view.children:
                    item.disabled = True

                await interaction.response.edit_message(embed=embed, view=view)

                # Send DM to user with customizable embed
                try:
                    dm_embed = onboard_embed_from_cfg("denied")
                    await member.send(embed=dm_embed)
                    logging.info(f"Sent denial DM to {member}")
                except discord.Forbidden:
                    logging.warning(f"Could not DM denial to {member}")

                # Log to bot log
                log_channel = discord.utils.get(
                    interaction.guild.text_channels,
                    name=get_log_channel_name()
                )
                if log_channel:
                    log_embed = discord.Embed(
                        title="❌ Onboarding Denied",
                        description=f"{member.mention} was denied onboarding by {interaction.user.mention}",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    await log_channel.send(embed=log_embed)

                logging.info(f"Denied onboarding for {member} by {interaction.user}")

            else:
                await interaction.response.send_message(
                    f"Error: Could not assign '{denial_role}' role to {member.mention}.",
                    ephemeral=True
                )

        except Exception as e:
            logging.error(f"Error denying onboard submission: {e}")
            await log_error(interaction.client, interaction.guild,
                          f"Error denying onboard submission: {e}")

            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while denying the submission.",
                        ephemeral=True
                    )
            except Exception:
                pass


# Main setup functions
async def setup_onboard_channel(guild: discord.Guild, client: discord.Client = None) -> bool:
    """
    Set up the onboard channel with the main embed and persistent view.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logging.info(f"Setting up onboard channel for guild: {guild.name}")

        # Ensure channels exist
        logging.info(f"Ensuring onboard channels exist for {guild.name}...")
        main_channel, review_channel = await ensure_onboard_channels(guild)

        if not main_channel:
            logging.error(f"Failed to create or find main onboard channel in {guild.name}")
            return False

        if not review_channel:
            logging.error(f"Failed to create or find review onboard channel in {guild.name}")
            return False

        logging.info(f"Onboard channels confirmed: main={main_channel.name}, review={review_channel.name}")

        # Check if main embed already exists
        main_embed_exists = False
        logging.info(f"Checking for existing onboard embed in {main_channel.name}...")
        async for message in main_channel.history(limit=50):
            if (message.author.bot and message.embeds and
                any("Welcome to Guardian Angel League" in embed.title for embed in message.embeds)):
                main_embed_exists = True
                logging.info("Main onboard embed already exists")
                break

        # Post main embed if it doesn't exist
        if not main_embed_exists:
            logging.info(f"Creating new onboard embed for {main_channel.name}...")
            embed = onboard_embed_from_cfg("main")
            view = OnboardView(guild.id)

            await main_channel.send(embed=embed, view=view)
            logging.info(f"Posted main onboard embed to {main_channel.mention}")
        else:
            logging.info(f"Onboard embed already exists in {main_channel.name}, skipping creation")

        # Rebuild pending submissions from review channel history
        logging.info(f"Rebuilding pending submissions from {review_channel.name}...")
        await rebuild_pending_submissions_from_history(review_channel)

        # Register persistent views for onboard system
        if client:
            await register_onboard_persistent_views(client, guild)
            await register_pending_review_views(client, guild)

        logging.info(f"Successfully set up onboard system for {guild.name}")
        return True

    except Exception as e:
        logging.error(f"Failed to setup onboard channel for {guild.name}: {e}", exc_info=True)
        return False


async def register_onboard_persistent_views(client: discord.Client, guild: discord.Guild):
    """Register persistent views for onboarding system."""
    try:
        # Create and register persistent onboard view
        onboard_view = OnboardView.create_persistent(guild)
        client.add_view(onboard_view)

        logging.info(f"Registered persistent onboard views for guild: {guild.name}")
    except Exception as e:
        logging.error(f"Failed to register persistent onboard views for {guild.name}: {e}")


async def register_pending_review_views(client: discord.Client, guild: discord.Guild):
    """Register persistent review views for existing pending submissions."""
    try:
        pending_submissions = OnboardManager.get_pending_submissions()

        for user_id, submission_data in pending_submissions.items():
            review_view = ReviewView.create_persistent(user_id, guild.id)
            client.add_view(review_view)

        if pending_submissions:
            logging.info(f"Registered {len(pending_submissions)} persistent review views for guild: {guild.name}")
    except Exception as e:
        logging.error(f"Failed to register persistent review views for {guild.name}: {e}")


async def register_all_onboard_persistent_views(client: discord.Client):
    """Register persistent onboard views for all guilds."""
    for guild in client.guilds:
        await register_onboard_persistent_views(client, guild)
        await register_pending_review_views(client, guild)


# Export main functions
__all__ = [
    'OnboardView', 'OnboardModal', 'ReviewView',
    'setup_onboard_channel', 'register_onboard_persistent_views',
    'register_all_onboard_persistent_views'
]