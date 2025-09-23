# helpers/onboard_helpers.py

import logging
from typing import Dict, Optional, Set
from datetime import datetime

import discord

from config import (
    get_onboard_main_channel, get_onboard_review_channel,
    get_onboard_approval_role, get_allowed_roles
)
from helpers.role_helpers import RoleManager


class OnboardManager:
    """Manages onboarding submissions and state tracking."""

    # Track pending submissions: {user_id: submission_data}
    _pending_submissions: Dict[int, Dict] = {}

    @classmethod
    def add_pending_submission(cls, user_id: int, submission_data: Dict) -> None:
        """Add a user to pending submissions."""
        cls._pending_submissions[user_id] = {
            **submission_data,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id
        }
        logging.info(f"Added pending onboard submission for user {user_id}")

    @classmethod
    def remove_pending_submission(cls, user_id: int) -> Optional[Dict]:
        """Remove and return a user's pending submission."""
        submission = cls._pending_submissions.pop(user_id, None)
        if submission:
            logging.info(f"Removed pending onboard submission for user {user_id}")
        return submission

    @classmethod
    def has_pending_submission(cls, user_id: int) -> bool:
        """Check if user has a pending submission."""
        return user_id in cls._pending_submissions

    @classmethod
    def get_pending_submissions(cls) -> Dict[int, Dict]:
        """Get all pending submissions."""
        return cls._pending_submissions.copy()

    @classmethod
    def clear_pending_submissions(cls) -> None:
        """Clear all pending submissions (useful for bot restart)."""
        cls._pending_submissions.clear()
        logging.info("Cleared all pending onboard submissions")

    @classmethod
    def is_eligible_for_onboarding(cls, member: discord.Member) -> tuple[bool, str]:
        """
        Check if a member is eligible for onboarding.

        Returns:
            tuple: (is_eligible, reason_if_not)
        """
        # Check if user already has the approval role
        approval_role = get_onboard_approval_role()
        if RoleManager.has_role(member, approval_role):
            return False, "already_approved"

        # Check if user has a pending submission
        if cls.has_pending_submission(member.id):
            return False, "pending_review"

        return True, ""


async def ensure_onboard_channels(guild: discord.Guild) -> tuple[Optional[discord.TextChannel], Optional[discord.TextChannel]]:
    """
    Ensure onboard channels exist with proper permissions.

    Returns:
        tuple: (main_channel, review_channel)
    """
    main_channel_name = get_onboard_main_channel()
    review_channel_name = get_onboard_review_channel()
    approval_role_name = get_onboard_approval_role()
    allowed_role_names = get_allowed_roles()

    logging.info(f"Ensuring onboard channels: main='{main_channel_name}', review='{review_channel_name}'")

    # Get existing channels
    main_channel = discord.utils.get(guild.text_channels, name=main_channel_name)
    review_channel = discord.utils.get(guild.text_channels, name=review_channel_name)

    logging.info(f"Found existing channels: main={main_channel.name if main_channel else None}, review={review_channel.name if review_channel else None}")

    # Get roles
    approval_role = discord.utils.get(guild.roles, name=approval_role_name)
    everyone_role = guild.default_role

    # Get staff roles
    staff_roles = []
    for role_name in allowed_role_names:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            staff_roles.append(role)

    try:
        # Create main channel if it doesn't exist
        if not main_channel:
            logging.info(f"Creating onboard main channel: {main_channel_name}")

            # Set up permissions for main channel
            overwrites = {
                everyone_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    read_message_history=True
                )
            }

            # Allow staff to manage the channel
            for staff_role in staff_roles:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    read_message_history=True
                )

            # Hide from approved users (they don't need to see onboarding)
            if approval_role:
                overwrites[approval_role] = discord.PermissionOverwrite(
                    read_messages=False
                )

            main_channel = await guild.create_text_channel(
                main_channel_name,
                overwrites=overwrites,
                topic="Welcome to Guardian Angel League! Complete onboarding to access the server.",
                reason="Auto-created onboard main channel"
            )
            logging.info(f"Created onboard main channel: {main_channel.mention}")

        # Create review channel if it doesn't exist
        if not review_channel:
            logging.info(f"Creating onboard review channel: {review_channel_name}")

            # Set up permissions for review channel (staff only)
            overwrites = {
                everyone_role: discord.PermissionOverwrite(
                    read_messages=False
                )
            }

            # Allow staff access
            for staff_role in staff_roles:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    read_message_history=True
                )

            review_channel = await guild.create_text_channel(
                review_channel_name,
                overwrites=overwrites,
                topic="Staff review channel for onboarding submissions.",
                reason="Auto-created onboard review channel"
            )
            logging.info(f"Created onboard review channel: {review_channel.mention}")

        return main_channel, review_channel

    except discord.Forbidden:
        logging.error(f"Missing permissions to create onboard channels in {guild.name}")
        return None, None
    except discord.HTTPException as e:
        logging.error(f"Failed to create onboard channels in {guild.name}: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error creating onboard channels in {guild.name}: {e}")
        return None, None


async def setup_channel_permissions(channel: discord.TextChannel, channel_type: str) -> bool:
    """
    Set up proper permissions for onboard channels.

    Args:
        channel: The channel to set permissions for
        channel_type: Either "main" or "review"

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        approval_role_name = get_onboard_approval_role()
        allowed_role_names = get_allowed_roles()

        approval_role = discord.utils.get(channel.guild.roles, name=approval_role_name)
        everyone_role = channel.guild.default_role

        # Get staff roles
        staff_roles = []
        for role_name in allowed_role_names:
            role = discord.utils.get(channel.guild.roles, name=role_name)
            if role:
                staff_roles.append(role)

        if channel_type == "main":
            # Main channel: visible to everyone without approval role, read-only for non-staff
            overwrites = {
                everyone_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    read_message_history=True
                )
            }

            # Staff can manage
            for staff_role in staff_roles:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    read_message_history=True
                )

            # Hide from approved users
            if approval_role:
                overwrites[approval_role] = discord.PermissionOverwrite(
                    read_messages=False
                )

        elif channel_type == "review":
            # Review channel: staff only
            overwrites = {
                everyone_role: discord.PermissionOverwrite(
                    read_messages=False
                )
            }

            # Staff access
            for staff_role in staff_roles:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    read_message_history=True
                )

        else:
            logging.error(f"Unknown channel type: {channel_type}")
            return False

        # Apply overwrites
        for target, overwrite in overwrites.items():
            await channel.set_permissions(target, overwrite=overwrite)

        logging.debug(f"Set up permissions for {channel_type} channel: {channel.name}")
        return True

    except discord.Forbidden:
        logging.error(f"Missing permissions to set up channel permissions for {channel.name}")
        return False
    except discord.HTTPException as e:
        logging.error(f"Failed to set up channel permissions for {channel.name}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error setting up channel permissions for {channel.name}: {e}")
        return False


async def rebuild_pending_submissions_from_history(review_channel: discord.TextChannel) -> None:
    """
    Rebuild pending submissions state from review channel message history.
    This is useful when the bot restarts and loses in-memory state.
    """
    try:
        logging.info("Rebuilding pending onboard submissions from channel history...")

        # Clear existing state
        OnboardManager.clear_pending_submissions()

        # Look through recent messages in review channel
        async for message in review_channel.history(limit=100):
            # Skip non-bot messages
            if not message.author.bot:
                continue

            # Skip messages without embeds
            if not message.embeds:
                continue

            embed = message.embeds[0]

            # Check if this is a review embed with components
            if (embed.title and "Onboarding Submission" in embed.title and
                message.components):

                # Extract user ID from embed footer or description
                user_id = None
                if embed.footer and embed.footer.text:
                    # Look for user ID in footer (format: "User: username (123456789)")
                    import re
                    match = re.search(r'\((\d+)\)', embed.footer.text)
                    if match:
                        user_id = int(match.group(1))

                if user_id:
                    # Check if buttons are still active (not disabled)
                    has_active_buttons = False
                    for component in message.components:
                        if hasattr(component, 'children'):
                            for button in component.children:
                                if hasattr(button, 'disabled') and not button.disabled:
                                    has_active_buttons = True
                                    break

                    if has_active_buttons:
                        # This is still a pending submission
                        submission_data = {
                            'message_id': message.id,
                            'channel_id': message.channel.id,
                            'timestamp': message.created_at.isoformat()
                        }
                        OnboardManager.add_pending_submission(user_id, submission_data)

        pending_count = len(OnboardManager.get_pending_submissions())
        logging.info(f"Rebuilt {pending_count} pending onboard submissions from history")

    except Exception as e:
        logging.error(f"Failed to rebuild pending submissions from history: {e}")