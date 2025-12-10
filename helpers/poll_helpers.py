"""Poll notification system helpers for mass DM functionality."""

import asyncio
import logging
import re
import time
from datetime import datetime
from typing import List, Dict, Callable, Optional, Tuple

import discord

from config import get_angel_role, get_poll_config


logger = logging.getLogger(__name__)


class PollDMView(discord.ui.View):
    """View with button to go to poll in DM messages."""
    
    def __init__(self, poll_link: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="🗳️ Go to Poll",
            url=poll_link,
            style=discord.ButtonStyle.link
        ))


class PollDMLayoutView(discord.ui.LayoutView):
    """LayoutView for poll DM using Components V2 with markdown support."""
    
    def __init__(self, poll_link: str, config: dict):
        super().__init__(timeout=None)
        self.poll_link = poll_link
        self.config = config
        
        # Build and add container
        container = self.build_container()
        self.add_item(container)
    
    def build_container(self) -> discord.ui.Container:
        """Build the poll DM container with Discord markdown support."""
        dm_config = self.config.get("dm_embed", {})
        
        # Extract config values with proper fallbacks
        title = dm_config.get("title", "# 🌟 Hello Angel!")
        header = dm_config.get("header", "### We need your input! 🗳️")
        body = dm_config.get("body", "")
        how_to_vote = dm_config.get("how_to_vote", {})
        how_to_vote_title = how_to_vote.get("title", "### 🔗 How to vote:")
        how_to_vote_content = how_to_vote.get("content", "Click the **\"Go to Poll\"** button below to access the voting form. It only takes a few seconds! 😊")
        footer = dm_config.get("footer", "-# 💙 Thank you for helping make GAL tournaments even better!")
        button_config = dm_config.get("button", {})
        button_label = button_config.get("label", "🗳️ Go to Poll")
        
        # Get color from config for accent styling
        color_hex = dm_config.get("color", "#f8c8dc")  # Default GAL pink
        
        # Build text content with tighter spacing
        text_content = f"{title}\n\n"
        
        if header:
            text_content += f"{header}\n"
            
        if body:
            text_content += f"{body}\n"
            
        if how_to_vote_title:
            text_content += f"{how_to_vote_title}\n"
            if how_to_vote_content:
                text_content += f"{how_to_vote_content}\n"
        
        if footer:
            text_content += footer
        
        # Build components list
        components = []
        
        # Add text component (supports Discord markdown!)
        components.append(discord.ui.TextDisplay(
            content=text_content
        ))
        
        # Add separator
        components.append(discord.ui.Separator(
            visible=True,
            spacing=discord.SeparatorSpacing.small
        ))
        
        # Add poll button wrapped in ActionRow (required for Components V2)
        poll_button = discord.ui.Button(
            label=button_label,
            url=self.poll_link,
            style=discord.ButtonStyle.link
        )
        components.append(discord.ui.ActionRow(poll_button))
        
        # Return container with accent color from config
        return discord.ui.Container(
            *components,
            accent_colour=discord.Colour.from_str(color_hex)
        )


class PollNotifier:
    """Mass poll notification system with progress tracking."""
    
    def __init__(self, guild: discord.Guild, poll_link: str, custom_message: str = None):
        self.guild = guild
        self.poll_link = poll_link
        self.custom_message = custom_message
        
        # Statistics
        self.total_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.failed_users: List[Tuple[discord.Member, str]] = []  # (member, reason)
        
        # Progress tracking
        self.start_time = None
        self.last_progress_update = 0
        
        # Configuration
        self.config = get_poll_config()
        self.batch_size = self.config.get("batch_size", 10)
        self.batch_delay = self.config.get("batch_delay", 1.0)
        self.progress_update_interval = self.config.get("progress_update_interval", 5)
        
        # Get target role
        self.target_role_name = self.config.get("target_role", "Angels")
        
    def validate_discord_link(self, link: str) -> bool:
        """
        Validate Discord message link format.
        
        Expected format: https://discord.com/channels/{guild_id}/{channel_id}/{message_id}
        """
        pattern = r"https://discord\.com/channels/\d+/\d+/\d+"
        return bool(re.match(pattern, link))
    
    def get_angels_members(self) -> List[discord.Member]:
        """Get all members with the Angels role."""
        try:
            # Get role by name
            role = discord.utils.get(self.guild.roles, name=self.target_role_name)
            if not role:
                raise ValueError(f"Role '{self.target_role_name}' not found in this server")
            
            # Get all members with this role
            members = [member for member in self.guild.members if role in member.roles]
            
            # Filter out bots
            members = [member for member in members if not member.bot]
            
            logger.info(f"Found {len(members)} members with '{self.target_role_name}' role")
            return members
            
        except Exception as e:
            logger.error(f"Error getting Angels members: {e}")
            raise
    
    def create_dm_embed(self) -> discord.Embed:
        """Create the DM embed for poll notification."""
        dm_config = self.config.get("dm_embed", {})
        
        # Override with custom message if provided
        if self.custom_message:
            embed = discord.Embed(
                title=dm_config.get("title", "🌟 Hello Angel!"),
                description=self.custom_message,
                color=int(dm_config.get("color", "#f8c8dc").replace("#", ""), 16)
            )
        else:
            embed = discord.Embed(
                title=dm_config.get("title", "🌟 Hello Angel!"),
                color=int(dm_config.get("color", "#f8c8dc").replace("#", ""), 16)
            )
            
            # Add header
            header = dm_config.get("header", "We need your input! 🗳️")
            embed.description = header
            
            # Add body
            body = dm_config.get("body", "")
            if body:
                embed.add_field(
                    name="📋 Poll Details",
                    value=body,
                    inline=False
                )
            
            # Add how to vote section
            how_to_vote = dm_config.get("how_to_vote", {})
            if how_to_vote:
                embed.add_field(
                    name=how_to_vote.get("title", "🔗 How to vote:"),
                    value=how_to_vote.get("content", "Click the **\"Go to Poll\"** button below to access the voting form."),
                    inline=False
                )
        
        # Add footer
        footer = dm_config.get("footer", "💙 Thank you for helping make GAL tournaments even better!")
        embed.set_footer(text=footer)
        
        # Add timestamp
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    def create_progress_embed(self, current: int, total: int, elapsed: float) -> discord.Embed:
        """Create simple progress tracking embed."""
        percentage = (current / total * 100) if total > 0 else 0
        
        # Simple progress bar
        bar_length = 20
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # Calculate time remaining
        if current > 0:
            avg_time = elapsed / current
            remaining = avg_time * (total - current)
            time_str = f"{remaining:.0f}s"
        else:
            time_str = "Calculating..."
        
        embed = discord.Embed(
            title="📨 Sending Poll Notifications",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="⏳ Progress",
            value=f"{current}/{total} ({percentage:.0f}%)\n[{bar}] {percentage:.0f}%",
            inline=False
        )
        
        embed.add_field(
            name="📊 Status",
            value=f"✅ Successful: {self.success_count}\n❌ Failed: {self.failed_count}",
            inline=True
        )
        
        embed.add_field(
            name="⏱️ Time",
            value=f"Elapsed: {elapsed:.0f}s\nRemaining: {time_str}",
            inline=True
        )
        
        return embed
    
    def create_summary_embed(self, total_time: float) -> discord.Embed:
        """Create final summary embed."""
        embed = discord.Embed(
            title="✅ Poll Notifications Sent!",
            color=discord.Color.green()
        )
        
        embed.description = f"📊 Results:\n✅ Successful: {self.success_count}\n❌ Failed: {self.failed_count}"
        
        if self.failed_users:
            # Show first 10 failed users
            failed_list = []
            for member, reason in self.failed_users[:10]:
                failed_list.append(f"• {member.mention} ({reason})")
            
            if len(self.failed_users) > 10:
                failed_list.append(f"... and {len(self.failed_users) - 10} more")
            
            embed.add_field(
                name="❌ Failed users",
                value="\n".join(failed_list),
                inline=False
            )
        
        embed.add_field(
            name="⏱️ Performance",
            value=f"Total time: {total_time:.1f} seconds\nAverage: {total_time/self.total_count:.2f}s per user",
            inline=False
        )
        
        embed.set_footer(text="Note: Users who failed will not receive the notification. Please reach out to them manually if needed.")
        
        return embed
    
    async def send_dm_to_user(self, member: discord.Member, dm_view: discord.ui.LayoutView = None, embed: discord.Embed = None, view: discord.ui.View = None) -> bool:
        """Send DM to a single user using LayoutView. Returns True if successful."""
        try:
            # Prefer LayoutView if provided
            if dm_view:
                await member.send(view=dm_view)
            elif embed and view:
                # Fallback to old embed+view system
                await member.send(embed=embed, view=view)
            else:
                # No content to send
                logger.warning(f"No content provided for DM to {member}")
                return False
            return True
        except discord.Forbidden:
            logger.warning(f"Could not DM {member} (DMs disabled or bot blocked)")
            self.failed_users.append((member, "DMs disabled"))
            return False
        except discord.HTTPException as e:
            logger.warning(f"HTTP error sending DM to {member}: {e}")
            self.failed_users.append((member, f"HTTP error: {str(e)[:50]}"))
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending DM to {member}: {e}")
            self.failed_users.append((member, f"Unexpected error"))
            return False
    
    async def send_to_all_angels(self, progress_callback: Callable[[discord.Embed, int, int, float], None]) -> Tuple[int, int, List[Tuple[discord.Member, str]]]:
        """
        Send DMs to all Angels with progress tracking.
        
        Args:
            progress_callback: Function to call with progress updates
                               (embed, current, total, elapsed_time)
        
        Returns:
            Tuple of (success_count, failed_count, failed_users)
        """
        self.start_time = time.time()
        
        # Get all Angels members
        members = self.get_angels_members()
        self.total_count = len(members)
        
        if self.total_count == 0:
            logger.warning("No members found with Angels role")
            return 0, 0, []
        
        # Create DM LayoutView (Components V2 with markdown support)
        dm_view = PollDMLayoutView(self.poll_link, self.config)
        
        # Process in batches
        current = 0
        
        try:
            for i in range(0, len(members), self.batch_size):
                batch = members[i:i + self.batch_size]
                
                # Send DMs concurrently within batch
                tasks = []
                for member in batch:
                    task = asyncio.create_task(self.send_dm_to_user(member, dm_view=dm_view))
                    tasks.append(task)
                
                # Wait for batch to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count results
                for j, result in enumerate(results):
                    current += 1
                    if isinstance(result, bool) and result:
                        self.success_count += 1
                    else:
                        self.failed_count += 1
                
                # Update progress if needed
                elapsed = time.time() - self.start_time
                if (current % self.progress_update_interval == 0 or 
                    current == self.total_count or 
                    elapsed - self.last_progress_update >= 2.0):
                    
                    progress_embed = self.create_progress_embed(current, self.total_count, elapsed)
                    await progress_callback(progress_embed, current, self.total_count, elapsed)
                    self.last_progress_update = elapsed
                
                # Rate limiting delay
                if i + self.batch_size < len(members):  # Don't delay after last batch
                    await asyncio.sleep(self.batch_delay)
        
        except Exception as e:
            logger.error(f"Error during mass DM process: {e}")
            raise
        
        total_time = time.time() - self.start_time
        logger.info(f"Mass DM completed: {self.success_count} success, {self.failed_count} failed, {total_time:.1f}s total")
        
        return self.success_count, self.failed_count, self.failed_users


def validate_discord_link(link: str) -> bool:
    """
    Validate Discord message link format.
    
    Expected format: https://discord.com/channels/{guild_id}/{channel_id}/{message_id}
    """
    pattern = r"https://discord\.com/channels/\d+/\d+/\d+"
    return bool(re.match(pattern, link))


__all__ = ["PollNotifier", "PollDMView", "PollDMLayoutView", "validate_discord_link"]
