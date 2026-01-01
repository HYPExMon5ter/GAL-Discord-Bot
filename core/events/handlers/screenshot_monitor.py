"""
Screenshot Monitor - Discord event handler for automatic screenshot detection.

Monitors configured channels for image attachments and triggers batch processing.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
import logging

import discord
from discord.ext import commands

from integrations.batch_processor import get_batch_processor
from config import _FULL_CFG

log = logging.getLogger(__name__)


class ScreenshotMonitor:
    """Monitors Discord channels for screenshot submissions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = _FULL_CFG
        self.settings = self.config.get("standings_screenshots", {})

        self.enabled = self.settings.get("enabled", False)
        self.monitor_channels = self.settings.get("monitor_channels", [])
        # Force bot-log channel (override config to ensure correct behavior)
        self.notification_channel_name = "bot-log"

        # Confirmation settings
        self.confirmation_method = self.settings.get("confirmation_method", "reaction")
        self.confirmation_reaction = self.settings.get("confirmation_reaction", "✅")
        self.confirmation_message = self.settings.get(
            "confirmation_message",
            "📸 Screenshot detected! Processing in {batch_window}s..."
        )

        # Batch processing
        self.batch_window = self.settings.get("batch_window_seconds", 30)
        self.batch_queue: List[Dict] = []
        self.batch_timer = None

        # Notification channel (lazy load)
        self.notification_channel = None

        if self.enabled:
            log.info(
                f"Screenshot Monitor enabled (channels: {self.monitor_channels})"
            )
        else:
            log.info("Screenshot Monitor disabled")

    async def on_message(self, message: discord.Message):
        """
        Handle incoming messages for screenshot detection.

        Called from Discord bot's on_message event.
        """
        # Ignore own messages
        if message.author.bot or message.author.id == self.bot.user.id:
            return

        # Check if feature is enabled
        if not self.enabled:
            return

        # Check if message is in monitored channel
        channel_name = message.channel.name if hasattr(message.channel, 'name') else str(message.channel.id)

        if channel_name not in self.monitor_channels:
            return

        # Check for image attachments
        if not message.attachments:
            return

        # Filter for image types
        image_attachments = [
            att for att in message.attachments
            if att.content_type and att.content_type.startswith("image/")
        ]

        if not image_attachments:
            return

        log.info(
            f"Detected {len(image_attachments)} screenshot(s) "
            f"from {message.author.name} in #{channel_name}"
        )

        # Send confirmation to user
        await self._send_confirmation(message)

        # Add images to batch queue
        for attachment in image_attachments:
            self.batch_queue.append({
                "url": attachment.url,
                "discord_message_id": message.id,
                "discord_channel_id": message.channel.id,
                "discord_author_id": str(message.author.id),
                "channel_name": channel_name,  # Pass channel name for classifier
                "round_name": self._extract_round_name(message),
                "lobby_number": self._extract_lobby_number(message)
            })

        # Notify staff
        await self._send_notification(
            f"📸 Detected {len(image_attachments)} screenshot(s) "
            f"from {message.author.mention} in {message.channel.mention}\n"
            f"Batching {self.batch_window}s window...",
            "screenshot_detected"
        )

        # Start/reset batch timer
        await self._reset_batch_timer(message.guild)

    async def _reset_batch_timer(self, guild: discord.Guild):
        """Reset or start batch processing timer."""
        # Cancel existing timer
        if self.batch_timer:
            self.batch_timer.cancel()

        # Start new timer
        async def process_batch_callback():
            log.info(f"Batch timer expired - processing {len(self.batch_queue)} images")
            await self._process_batch(guild)

        # Create asyncio task for delayed processing
        self.batch_timer = asyncio.create_task(
            asyncio.sleep(self.batch_window)
        )
        self.batch_timer.add_done_callback(
            lambda t: asyncio.create_task(process_batch_callback())
        )

    async def _process_batch(self, guild: discord.Guild):
        """Process queued screenshots as a batch."""
        if not self.batch_queue:
            return

        # Get tournament ID from guild or config
        tournament_id = str(guild.id) if guild else "default"

        # Process batch
        batch_processor = get_batch_processor()

        await self._send_notification(
            f"⏳ Processing {len(self.batch_queue)} screenshots...",
            "batch_processing"
        )

        result = await batch_processor.process_batch(
            images=self.batch_queue,
            tournament_id=tournament_id,
            guild_id=str(guild.id) if guild else "default",
            round_name=self._detect_round_name()
        )

        # Clear queue
        self.batch_queue = []

        # Send notification with results
        if result.get("success", False):
            completed = result.get("completed", 0)
            validated = result.get("validated", 0)
            errors = result.get("errors", 0)
            avg_confidence = result.get("average_confidence", 0)

            status_emoji = "✅" if errors == 0 else "⚠️"

            notification = (
                f"{status_emoji} Batch Processing Complete\n\n"
                f"📊 Results:\n"
                f"  • Processed: {completed}\n"
                f"  • Auto-validated: {validated}\n"
                f"  • Errors: {errors}\n"
                f"  • Avg Confidence: {avg_confidence:.1%}\n\n"
            )

            # Add manual review reminder if needed
            if completed > validated:
                notification += (
                    f"🔔 {completed - validated} screenshots need manual review!\n"
                    f"Check the admin dashboard for details."
                )
            else:
                notification += "✨ All screenshots auto-validated!"

            await self._send_notification(notification, "batch_complete")

        else:
            error_msg = result.get("error", "Unknown error")
            await self._send_notification(
                f"❌ Batch processing failed: {error_msg}",
                "batch_error"
            )

    def _extract_round_name(self, message: discord.Message) -> str:
        """Attempt to extract round name from message content."""
        # Simple pattern matching
        import re
        content = message.content.upper()

        # Look for "Round X" or "Round X.Y" patterns
        match = re.search(r'ROUND\s*(\d+(?:\.\d+)?)', content)
        if match:
            return f"ROUND_{match.group(1)}"

        # Look for "R1", "R2", etc.
        match = re.search(r'\bR(\d+)\b', content)
        if match:
            return f"ROUND_{match.group(1)}"

        return "UNKNOWN"

    def _extract_lobby_number(self, message: discord.Message) -> int:
        """Attempt to extract lobby number from message content."""
        import re
        content = message.content.upper()

        # Look for "Lobby X" or "L1", "L2", etc.
        match = re.search(r'LOBBY\s*(\d+)', content)
        if match:
            return int(match.group(1))

        match = re.search(r'\bL(\d+)\b', content)
        if match:
            return int(match.group(1))

        return 1  # Default to lobby 1

    def _detect_round_name(self) -> str:
        """Detect round name from batch queue."""
        if not self.batch_queue:
            return "UNKNOWN"

        # Use most common round name in batch
        round_names = [img.get("round_name", "UNKNOWN") for img in self.batch_queue]
        # Filter out unknown
        round_names = [r for r in round_names if r != "UNKNOWN"]

        if round_names:
            # Return most common
            from collections import Counter
            return Counter(round_names).most_common(1)[0][0]

        return "UNKNOWN"

    async def _send_notification(
        self,
        message: str,
        notification_type: str
    ):
        """Send notification to staff channel."""
        if not self.notification_channel_name:
            return

        # Lazy load notification channel
        if self.notification_channel is None:
            # Find channel by name
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    if channel.name == self.notification_channel_name:
                        self.notification_channel = channel
                        break
                if self.notification_channel:
                    break

            if self.notification_channel is None:
                log.warning(f"Notification channel '{self.notification_channel_name}' not found")
                return

        try:
            # Create embed for notification
            embed = discord.Embed(
                title="📊 Screenshot Processing",
                description=message,
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            embed.set_footer(text=notification_type)

            await self.notification_channel.send(embed=embed)

        except Exception as e:
            log.error(f"Failed to send notification: {e}")

    async def _send_confirmation(self, message: discord.Message):
        """
        Send confirmation to user that screenshot was detected.
        
        Supports three modes:
        - reaction: Add emoji reaction to message
        - message: Send ephemeral reply (or regular reply if not slash command)
        - both: Both reaction and message
        """
        try:
            # Add reaction confirmation
            if self.confirmation_method in ["reaction", "both"]:
                try:
                    await message.add_reaction(self.confirmation_reaction)
                    log.debug(f"Added {self.confirmation_reaction} reaction to message {message.id}")
                except discord.Forbidden:
                    log.warning("Missing permissions to add reaction")
                except discord.HTTPException as e:
                    log.warning(f"Failed to add reaction: {e}")

            # Send message confirmation
            if self.confirmation_method in ["message", "both"]:
                try:
                    confirmation_text = self.confirmation_message.format(
                        batch_window=self.batch_window
                    )
                    await message.reply(confirmation_text, mention_author=False)
                    log.debug(f"Sent confirmation message to {message.author.name}")
                except discord.Forbidden:
                    log.warning("Missing permissions to send confirmation message")
                except discord.HTTPException as e:
                    log.warning(f"Failed to send confirmation message: {e}")

        except Exception as e:
            log.error(f"Error sending confirmation: {e}")


# Singleton instance
_screenshot_monitor_instance = None

def get_screenshot_monitor(bot: commands.Bot) -> ScreenshotMonitor:
    """Get or create screenshot monitor instance."""
    global _screenshot_monitor_instance
    if _screenshot_monitor_instance is None:
        _screenshot_monitor_instance = ScreenshotMonitor(bot)
    return _screenshot_monitor_instance


# Discord event handler function to be registered with bot
async def on_screenshot_message(message: discord.Message):
    """Discord on_message event handler wrapper."""
    from bot import bot
    monitor = get_screenshot_monitor(bot)
    await monitor.on_message(message)
