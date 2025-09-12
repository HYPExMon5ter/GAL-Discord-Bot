# core/components_traditional.py
"""
Traditional embed implementation for GAL Bot using discord.py with regular embeds and buttons.
Creates a single embed interface with all sections separated by dividers and buttons at the bottom.
"""

import logging
import discord
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional

from config import (
    embed_from_cfg, get_registered_role, get_checked_in_role,
    get_unified_channel_name, get_sheet_settings, _FULL_CFG
)
from core.persistence import (
    get_event_mode_for_guild, get_persisted_msg, set_persisted_msg, persisted, get_schedule
)
from helpers import RoleManager, SheetOperations
from helpers.embed_helpers import EmbedHelper
from helpers.waitlist_helpers import WaitlistManager
from helpers.schedule_helpers import ScheduleHelper


def get_confirmation_message(key: str, **kwargs) -> str:
    """Get a confirmation message from config with formatting."""
    from config import _FULL_CFG
    confirmations = _FULL_CFG.get("embeds", {}).get("confirmations", {})
    message = confirmations.get(key, f"✅ Action completed: {key}")
    return message.format(**kwargs)


def create_management_embed(user_status: str, status_emoji: str, confirmation_message: str = None, waitlist_warning: str = None, embed_type: str = "registration") -> discord.Embed:
    """Create a consistently formatted management embed."""
    
    # Set title and actions based on embed type
    if embed_type == "checkin":
        embed = discord.Embed(
            title="✅ Check-In Management",
            color=discord.Color.green()
        )
        # Set check-in specific actions
        if "currently checked in" in user_status.lower():
            actions = "• **Check Out** - Release your tournament spot"
        elif "not checked in yet" in user_status.lower():
            actions = "• **Check In** - Confirm your tournament spot"
        else:
            actions = "• **Register First** - You must register before checking in"
    else:  # registration
        embed = discord.Embed(
            title="🎫 Registration Management",
            color=discord.Color.blurple()
        )
        # Set registration specific actions
        if "registered" in user_status.lower():
            actions = "• **Update Registration** - Modify your information\n• **Unregister** - Remove yourself from the tournament"
        elif "waitlist" in user_status.lower():
            actions = "• **Update Registration** - Update your waitlist information\n• **Leave Waitlist** - Remove yourself from the waitlist"
        else:
            actions = "• **Register** - Join the tournament or waitlist"
    
    # Add blank line after title
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    
    # Current status
    embed.add_field(
        name="Current Status",
        value=f"> {status_emoji} {user_status}",
        inline=False
    )
    
    # Add blank line after status
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    
    embed.add_field(
        name="Available Actions",
        value=actions,
        inline=False
    )
    
    # Add waitlist warning if tournament is full
    if waitlist_warning:
        embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.add_field(
            name="📋 Registration Notice",
            value=waitlist_warning,
            inline=False
        )
    
    # Add confirmation message if provided
    if confirmation_message:
        embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.add_field(
            name="Confirmation",
            value=confirmation_message,
            inline=False
        )
    
    return embed


async def build_unified_embed(guild: discord.Guild, user: Optional[discord.Member] = None) -> tuple[discord.Embed, discord.ui.View]:
    """
    Build the main unified embed with traditional embed format and buttons at bottom.
    Returns a tuple of (embed, view).
    """
    guild_id = str(guild.id)
    mode = get_event_mode_for_guild(guild_id)
    cfg = get_sheet_settings(mode)

    reg_open = persisted.get(guild_id, {}).get("registration_open", False)
    ci_open = persisted.get(guild_id, {}).get("checkin_open", False)
    
    # Get all scheduled times using helper
    reg_open_ts, reg_close_ts, ci_open_ts, ci_close_ts = ScheduleHelper.get_all_schedule_times(guild.id)

    max_players = cfg.get("max_players", 32)
    registered = await SheetOperations.count_by_criteria(guild_id, registered=True)
    checked_in = await SheetOperations.count_by_criteria(guild_id, registered=True, checked_in=True)
    spots_remaining = max(0, max_players - registered)
    waitlist = await WaitlistManager.get_waitlist_length(guild_id)

    # Get hub configuration from config
    hub_config = _FULL_CFG.get("embeds", {}).get("hub", {})
    
    # Create the main embed
    embed = discord.Embed(
        title=hub_config.get("title", "🌟 Guardian Angel League Tournament Hub"),
        color=discord.Color.blurple()
    )

    # Tournament Info (if registration or check-in is open, or if there are scheduled events)
    has_scheduled_events = reg_open_ts or reg_close_ts or ci_open_ts or ci_close_ts
    if reg_open or ci_open or has_scheduled_events:
        # Get tournament name from config
        tournament_config = _FULL_CFG.get("tournament", {})
        tournament_name = tournament_config.get("current_name", "K.O. GALISEUM")
        
        if mode == "doubleup":
            teams = await SheetOperations.get_teams_summary(guild_id)
            complete_teams = sum(1 for members in teams.values() if len(members) >= 2)
            
            embed.add_field(
                name=f"🎮 {tournament_name} Tournament Format",
                value=f"**Mode:** Double‑Up Teams\n**Teams:** {complete_teams} complete, {len(teams)} total\n**Max Teams:** {max_players // 2}",
                inline=False
            )
        else:  # normal mode
            embed.add_field(
                name=f"🎮 {tournament_name} Tournament Format",
                value=f"**Mode:** Individual Players\n**Players:** {registered} registered\n**Max Players:** {max_players}",
                inline=False
            )
        embed.add_field(name="\u200b", value="~~────────────────────────────────────────~~", inline=False)

    # Registration Section
    cap_bar = EmbedHelper.create_progress_bar(registered, max_players)
    
    reg_config = hub_config.get("registration", {})
    
    if reg_open:
        reg_text = f"**🎫 Registration OPEN** 🟢\n"
        
        # Add close time right after open status
        if reg_close_ts:
            closes_text = reg_config.get("closes_text", "> 🕒 **Closes at:** <t:{close_ts}:F>")
            reg_text += closes_text.format(close_ts=reg_close_ts) + "\n"
        
        reg_text += f"\n📊 **Capacity:** {cap_bar} {registered}/{max_players}\n"
        reg_text += reg_config.get("spots_available", "**{spots_remaining} spots available!**").format(spots_remaining=spots_remaining) + "\n\n"
        reg_text += reg_config.get("open_text", "✨ Click **Manage Registration** below to register or update your info!")
        
        if user:
            if RoleManager.is_registered(user):
                user_reg_status = reg_config.get("user_registered", "✅ **You are registered!**")
            else:
                user_reg_status = reg_config.get("user_not_registered", "⚠️ **You are not registered yet!**")
            reg_text += f"\n{user_reg_status}"
    else:
        reg_text = f"**🎫 Registration CLOSED** 🔴"
        # Add scheduled open time if available
        if reg_open_ts:
            opens_text = reg_config.get("opens_text", "📅 **Registration opens:** <t:{open_ts}:F>")
            reg_text += f"\n\n{opens_text.format(open_ts=reg_open_ts)}"

    # Check if both are closed for special messaging
    if not reg_open and not ci_open:
        # Check if there are any scheduled open times (only open times for showing sections)
        has_scheduled_open_events = reg_open_ts or ci_open_ts
        
        if has_scheduled_open_events:
            # Show closed sections with scheduled open times
            embed.add_field(name="\u200b", value=reg_text, inline=False)
            embed.add_field(name="\u200b", value="~~────────────────────────────────────────~~", inline=False)
            
            # Generate check-in text (always closed in this branch)
            checkin_config = hub_config.get("checkin", {})
            ci_text = f"**✅ Check‑In CLOSED** 🔴"
            # Add scheduled open time if available
            if ci_open_ts:
                opens_text = checkin_config.get("opens_text", "📅 **Check-in opens:** <t:{open_ts}:F>")
                ci_text += f"\n\n{opens_text.format(open_ts=ci_open_ts)}"
            
            embed.add_field(name="\u200b", value=ci_text, inline=False)
            embed.add_field(name="\u200b", value="~~────────────────────────────────────────~~", inline=False)
            
            # Show waitlist section when there are scheduled events
            show_waitlist = True
        else:
            # No scheduled events - show no event message
            no_event_text = hub_config.get("no_event_message", "🌙 **No active or scheduled event right now**\n> Check back soon for the next tournament!")
            embed.add_field(name="\u200b", value="~~────────────────────────────────────────~~", inline=False)
            embed.add_field(name="\u200b", value=no_event_text, inline=False)
            embed.add_field(name="\u200b", value="~~────────────────────────────────────────~~", inline=False)
            show_waitlist = False
    else:
        # At least one is open - show normally with separators
        embed.add_field(name="\u200b", value=reg_text, inline=False)
        embed.add_field(name="\u200b", value="~~────────────────────────────────────────~~", inline=False)

        # Check-In Section  
        progress_bar = EmbedHelper.create_progress_bar(checked_in, registered)
        
        checkin_config = hub_config.get("checkin", {})
        
        if ci_open:
            ci_text = f"**✅ Check‑In OPEN** 🟢\n"
            
            # Add close time right after open status
            if ci_close_ts:
                closes_text = checkin_config.get("closes_text", "> 🕒 **Closes at:** <t:{close_ts}:t>")
                ci_text += closes_text.format(close_ts=ci_close_ts) + "\n"
            
            pct_checkin = (checked_in / registered * 100) if registered else 0.0
            ci_text += f"\n📊 **Progress:** {progress_bar} {pct_checkin:.0f}%\n"
            ci_text += checkin_config.get("players_ready", "**{checked_in}/{registered} players ready!**").format(checked_in=checked_in, registered=registered) + "\n\n"
            ci_text += checkin_config.get("open_text", "🔒 Click **Manage Check-In** below to check in or out!")
            
            if user and RoleManager.is_registered(user):
                if RoleManager.is_checked_in(user):
                    user_ci_status = checkin_config.get("user_checked_in", "✅ **You are checked in!**")
                else:
                    user_ci_status = checkin_config.get("user_need_checkin", "⚠️ **You need to check in!**")
                ci_text += f"\n{user_ci_status}"
        else:
            ci_text = f"**✅ Check‑In CLOSED** 🔴"
            # Add scheduled open time if available
            if ci_open_ts:
                opens_text = checkin_config.get("opens_text", "📅 **Check-in opens:** <t:{open_ts}:F>")
                ci_text += f"\n\n{opens_text.format(open_ts=ci_open_ts)}"

        embed.add_field(name="\u200b", value=ci_text, inline=False)
        embed.add_field(name="\u200b", value="~~────────────────────────────────────────~~", inline=False)
        show_waitlist = True

    # Waitlisted Players Section
    if show_waitlist:
        waitlist_entries = await WaitlistManager.get_all_waitlist_entries(guild_id)
        if waitlist_entries:
            waitlist_text = f"**📋 Waitlisted Players** ({len(waitlist_entries)} waiting)\n"
            
            if mode == "doubleup":
                # Group by team for doubleup
                waitlist_text += "```css\n"
                for i, entry in enumerate(waitlist_entries, 1):
                    ign = entry.get("ign", "Unknown")
                    team = entry.get("team_name", "No Team")
                    waitlist_text += f"{i}. {entry['discord_tag']} | {ign} | Team: {team}\n"
                waitlist_text += "```"
            else:
                # Simple list for normal mode
                waitlist_text += "```css\n"
                for i, entry in enumerate(waitlist_entries, 1):
                    ign = entry.get("ign", "Unknown")
                    waitlist_text += f"{i}. {entry['discord_tag']} | {ign}\n"
                waitlist_text += "```"
            
            embed.add_field(name="\u200b", value=waitlist_text, inline=False)
            embed.add_field(name="\u200b", value="~~────────────────────────────────────────~~", inline=False)

    # Help Section
    help_text = hub_config.get("help_section", "**❓ Need Help?**\n**Quick Guide:**\n1️⃣ Register when open\n2️⃣ Check in before tournament\n3️⃣ Join lobby when called\n\n**Support:** Ask in chat or DM a @Moderator")
    embed.add_field(name="\u200b", value=help_text, inline=False)

    # Create the view with buttons
    view = UnifiedView(guild, user)

    return embed, view


class UnifiedView(discord.ui.View):
    """Main view with management buttons at the bottom."""
    
    def __init__(self, guild: discord.Guild, user: Optional[discord.Member] = None):
        super().__init__(timeout=None)
        self.guild = guild
        
        # Check if registration/check-in are open
        from core.persistence import persisted
        guild_id = str(guild.id)
        reg_open = persisted.get(guild_id, {}).get("registration_open", False)
        ci_open = persisted.get(guild_id, {}).get("checkin_open", False)
        
        # Primary user buttons (first row) - only show if respective features are open
        if reg_open:
            if user and RoleManager.is_registered(user):
                self.add_item(ManageRegistrationButton(label="Update Registration"))
            else:
                self.add_item(ManageRegistrationButton(label="Manage Registration"))
                
        if ci_open:
            self.add_item(ManageCheckInButton())
        
        # Secondary buttons (second row)  
        self.add_item(ViewListButton())
        self.add_item(AdminPanelButton())


class ManageRegistrationButton(discord.ui.Button):
    """Button to manage registration - opens ephemeral interface."""
    
    def __init__(self, label: str = "Manage Registration"):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary,
            custom_id="manage_registration",
            emoji="🎫"
        )

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        reg_open = persisted.get(guild_id, {}).get("registration_open", False)

        if not reg_open:
            await interaction.response.send_message(
                embed=embed_from_cfg("registration_closed"),
                ephemeral=True
            )
            return

        # Defer immediately since we'll do database lookups
        await interaction.response.defer(ephemeral=True)

        # Create ephemeral registration management interface
        from helpers.waitlist_helpers import WaitlistManager
        from helpers.validation_helpers import Validators
        
        is_registered = RoleManager.is_registered(interaction.user)
        waitlist_warning = None
        
        # Check if user is on waitlist
        waitlist_pos = await WaitlistManager.get_waitlist_position(guild_id, str(interaction.user))
        
        if is_registered:
            user_status = "You are currently registered for this tournament"
            status_emoji = "✅"
        elif waitlist_pos:
            # Show different status for waitlist users
            user_status = f"You are currently on the waitlist (position #{waitlist_pos})"
            status_emoji = "⏳"
        else:
            user_status = "You are not registered for this tournament"
            status_emoji = "❌"
            
            # Check if registration is full to show waitlist notice
            try:
                capacity_error = await Validators.validate_registration_capacity(guild_id, None)
                if capacity_error and capacity_error.embed_key in ["registration_full", "max_teams_reached"]:
                    waitlist_warning = "⚠️ The tournament is currently full. If you register, you will be added to the waitlist and notified if a spot becomes available."
            except:
                pass  # Don't break if validation fails

        embed = create_management_embed(
            user_status=user_status,
            status_emoji=status_emoji,
            waitlist_warning=waitlist_warning
        )

        # Create appropriate view based on registration/waitlist status
        view = RegistrationManagementView(interaction.user, is_registered, bool(waitlist_pos))
        message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        # Store the message reference for editing later
        view.original_message = message


class ManageCheckInButton(discord.ui.Button):
    """Button to manage check-in - opens ephemeral interface."""
    
    def __init__(self):
        super().__init__(
            label="Manage Check-In",
            style=discord.ButtonStyle.success,
            custom_id="manage_checkin",
            emoji="✅"
        )

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        ci_open = persisted.get(guild_id, {}).get("checkin_open", False)

        if not ci_open:
            try:
                embed = embed_from_cfg("checkin_closed")
            except:
                # Fallback if checkin_closed config doesn't exist
                embed = discord.Embed(
                    title="❌ Check-In Closed",
                    description="Check-in is currently closed.",
                    color=discord.Color.red()
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Defer early since we'll be doing role checks
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create ephemeral check-in management interface using check-in specific format
            if not RoleManager.is_registered(interaction.user):
                embed = create_management_embed(
                    user_status="You must be registered before you can check in",
                    status_emoji="⚠️",
                    confirmation_message="Please register first using the **Manage Registration** button.",
                    embed_type="checkin"
                )
                # Create an empty view instead of None
                view = discord.ui.View(timeout=60)
            else:
                is_checked_in = RoleManager.is_checked_in(interaction.user)
                
                if is_checked_in:
                    embed = create_management_embed(
                        user_status="You are currently checked in for this tournament",
                        status_emoji="✅",
                        embed_type="checkin"
                    )
                else:
                    embed = create_management_embed(
                        user_status="You are registered but not checked in yet",
                        status_emoji="⏳",
                        embed_type="checkin"
                    )
                
                view = CheckInManagementView(interaction.user, is_checked_in)

            message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
            # Store the message reference for timeout handling
            if hasattr(view, 'original_message'):
                view.original_message = message
                
        except Exception as e:
            # Log the error for debugging
            import logging
            logging.error(f"ManageCheckInButton error: {e}", exc_info=True)
            
            # If something goes wrong, send an error message
            try:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Error",
                        description="An error occurred while opening the check-in interface. Please try again.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            except:
                pass  # If even this fails, there's nothing more we can do


class ViewListButton(discord.ui.Button):
    """Button to view full player list."""
    
    def __init__(self):
        super().__init__(
            label="View All Players",
            style=discord.ButtonStyle.secondary,
            custom_id="view_list",
            emoji="📋"
        )

    async def callback(self, interaction: discord.Interaction):
        # Defer early since we'll be doing cache operations
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        mode = get_event_mode_for_guild(guild_id)

        # Get all registered users from cache
        from integrations.sheets import sheet_cache, cache_lock

        async with cache_lock:
            all_registered = [(tag, tpl) for tag, tpl in sheet_cache["users"].items()
                              if str(tpl[2]).upper() == "TRUE"]

        if not all_registered:
            await interaction.followup.send(
                "No registered players yet.",
                ephemeral=True
            )
            return

        # Use the same helper as registeredlist command
        from helpers import EmbedHelper
        lines = EmbedHelper.build_checkin_list_lines(all_registered, mode)

        # Calculate statistics
        total_registered = len(all_registered)
        total_checked_in = sum(1 for _, tpl in all_registered
                               if str(tpl[3]).upper() == "TRUE")

        # Build embed
        embed = discord.Embed(
            title=f"📋 Registered Players ({total_registered})",
            description="\n".join(lines) if lines else "No registered players found.",
            color=discord.Color.blurple()
        )

        # Build footer with statistics
        footer_parts = [f"👤 Players: {total_registered}"]

        if mode == "doubleup":
            # Count teams
            teams = set()
            for _, user_data in all_registered:
                # Cache format: (row, ign, reg_status, ci_status, team, alt_ign, pronouns)
                team_name = user_data[4] if len(user_data) > 4 and user_data[4] else "No Team"
                teams.add(team_name)
            footer_parts.append(f"👥 Teams: {len(teams)}")

        footer_parts.append(f"✅ Checked-In: {total_checked_in}")
        
        if total_registered > 0:
            percentage = (total_checked_in / total_registered) * 100
            footer_parts.append(f"📊 {percentage:.0f}%")

        embed.set_footer(text=" | ".join(footer_parts))

        # Create view with reminder button if user has allowed roles
        if RoleManager.has_allowed_role_from_interaction(interaction):
            view = PlayerListView()
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)


class PlayerListView(discord.ui.View):
    """View for player list with reminder button for staff."""
    
    def __init__(self):
        super().__init__(timeout=300)  # 5 minutes
        self.add_item(ReminderButton())


class AdminPanelButton(discord.ui.Button):
    """Button to open admin panel - only visible to staff."""
    
    def __init__(self):
        super().__init__(
            label="Admin Panel",
            style=discord.ButtonStyle.danger,
            custom_id="admin_panel",
            emoji="🔧"
        )

    async def callback(self, interaction: discord.Interaction):
        # Check permissions first - if no permission, respond immediately
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )
            return

        # Defer since we'll be creating complex views
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild.id)
        mode = get_event_mode_for_guild(guild_id)
        reg_open = persisted.get(guild_id, {}).get("registration_open", False)
        ci_open = persisted.get(guild_id, {}).get("checkin_open", False)

        # Create admin panel embed
        embed = discord.Embed(
            title="🔧 Admin Panel",
            description="Manage tournament settings and controls",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="Current Status",
            value=f"• **Mode:** {mode.capitalize()}\n"
                  f"• **Registration:** {'OPEN 🟢' if reg_open else 'CLOSED 🔴'}\n"
                  f"• **Check-In:** {'OPEN 🟢' if ci_open else 'CLOSED 🔴'}",
            inline=False
        )
        
        embed.add_field(
            name="Available Actions",
            value="• **Mode Toggle** - Switch between normal/double up mode\n"
                  "• **Toggle Registration** - Open/Close registration\n"
                  "• **Toggle Check-In** - Open/Close check-in\n"
                  "• **Reset Registration** - Close registration and clear all data\n"
                  "• **Reset Check-In** - Close check-in and uncheck all players",
            inline=False
        )

        view = AdminPanelView(interaction.guild)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class ReminderButton(discord.ui.Button):
    """Button to send reminder to users who haven't checked in."""
    
    def __init__(self):
        super().__init__(
            label="Send Reminder",
            style=discord.ButtonStyle.secondary,
            custom_id="send_reminder",
            emoji="🔔"
        )

    async def callback(self, interaction: discord.Interaction):
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )
            return

        # Defer immediately since this will do slow operations
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild.id)
        
        # Get registered users who aren't checked in
        try:
            registered_users = await SheetOperations.get_all_registered_users(guild_id)
            unchecked_users = []
            
            reg_role = discord.utils.get(interaction.guild.roles, name=get_registered_role())
            ci_role = discord.utils.get(interaction.guild.roles, name=get_checked_in_role())
            
            if reg_role and ci_role:
                for member in reg_role.members:
                    if ci_role not in member.roles:
                        unchecked_users.append(member)
            
            if not unchecked_users:
                embed = discord.Embed(
                    title="✅ All Checked In",
                    description="All registered users are already checked in!",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Send reminder embed
            embed = discord.Embed(
                title="🔔 Check-In Reminder Sent",
                description=f"Sending reminders to **{len(unchecked_users)}** registered users who haven't checked in yet...",
                color=discord.Color.blue()
            )
            
            # List some users (max 10)
            user_list = [user.display_name for user in unchecked_users[:10]]
            if len(unchecked_users) > 10:
                user_list.append(f"... and {len(unchecked_users) - 10} more")
            
            embed.add_field(
                name="Target Users",
                value="\n".join(f"• {name}" for name in user_list),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Send DMs to unchecked users using config.yaml message
            reminder_embed = embed_from_cfg("reminder_dm")
            
            # Create view with button to go to tournament channel
            from config import get_unified_channel_name
            channel_name = get_unified_channel_name()
            tournament_channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
            
            reminder_view = None
            if tournament_channel:
                reminder_view = discord.ui.View(timeout=None)
                go_to_channel_button = discord.ui.Button(
                    label="Go to Tournament Channel",
                    style=discord.ButtonStyle.primary,
                    url=f"https://discord.com/channels/{interaction.guild.id}/{tournament_channel.id}",
                    emoji="🎫"
                )
                reminder_view.add_item(go_to_channel_button)
            
            sent_count = 0
            for user in unchecked_users:
                try:
                    if reminder_view:
                        await user.send(embed=reminder_embed, view=reminder_view)
                    else:
                        await user.send(embed=reminder_embed)
                    sent_count += 1
                except Exception:
                    # User has DMs disabled or other error
                    pass
                    
            # Send follow-up with final results
            final_embed = discord.Embed(
                title="✅ Reminder Complete",
                description=f"Successfully sent DMs to **{sent_count}/{len(unchecked_users)}** users.",
                color=discord.Color.green()
            )
            
            if sent_count < len(unchecked_users):
                final_embed.add_field(
                    name="Note",
                    value=f"{len(unchecked_users) - sent_count} user(s) could not be reached (DMs disabled)",
                    inline=False
                )
                
            await interaction.followup.send(embed=final_embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description="Failed to send reminders. Please try again.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


# Management Views for Ephemeral Interfaces
class RegistrationManagementView(discord.ui.View):
    """View for managing registration in ephemeral message."""
    
    def __init__(self, user: discord.Member, is_registered: bool, is_waitlist: bool = False):
        super().__init__(timeout=900)  # 15 minutes instead of 5
        self.user = user
        self.is_registered = is_registered
        self.is_waitlist = is_waitlist
        self.original_message = None  # Store reference to the original message
        
        if is_registered:
            # Fully registered user
            update_btn = UpdateRegistrationButton()
            update_btn.management_view = self
            unregister_btn = UnregisterButton()
            unregister_btn.management_view = self
            self.add_item(update_btn)
            self.add_item(unregister_btn)
        elif is_waitlist:
            # Waitlist user - can update info or unregister from waitlist
            update_btn = UpdateRegistrationButton()
            update_btn.management_view = self
            unregister_btn = UnregisterButton()
            unregister_btn.label = "Remove from Waitlist"
            unregister_btn.management_view = self
            self.add_item(update_btn)
            self.add_item(unregister_btn)
        else:
            # Not registered at all
            register_btn = RegisterButton()
            register_btn.management_view = self
            self.add_item(register_btn)
        
        # Add staff controls if user has permissions
        if RoleManager.has_any_allowed_role(user):
            self.add_item(ToggleRegistrationButton())
            self.add_item(ResetRegistrationButton())

    async def on_timeout(self):
        """Handle view timeout by showing timeout notice and disabling buttons."""
        for item in self.children:
            item.disabled = True
            
        if self.original_message:
            try:
                # Get timeout message from config
                from config import _FULL_CFG
                timeout_notice = _FULL_CFG.get("embeds", {}).get("confirmations", {}).get("timeout_notice", 
                    "⏰ This interface has expired. Click **Manage Registration** or **Manage Check-In** in the main channel to continue.")
                
                # Update current embed to add timeout notice
                current_embed = self.original_message.embeds[0] if self.original_message.embeds else discord.Embed(title="🎫 Registration Management")
                
                # Add timeout notice as a new field
                current_embed.add_field(name="\u200b", value="\u200b", inline=False)  # Blank line
                current_embed.add_field(
                    name="Session Expired",
                    value=timeout_notice,
                    inline=False
                )
                current_embed.color = discord.Color.orange()
                
                await self.original_message.edit(embed=current_embed, view=self)
            except Exception:
                pass  # Don't fail if we can't update the message


class CheckInManagementView(discord.ui.View):
    """View for managing check-in in ephemeral message."""
    
    def __init__(self, user: discord.Member, is_checked_in: bool):
        super().__init__(timeout=900)  # 15 minutes instead of 5
        self.user = user
        self.is_checked_in = is_checked_in
        self.original_message = None
        
        if is_checked_in:
            self.add_item(CheckOutButton())
        else:
            self.add_item(CheckInButton())
        
        # Add staff controls if user has permissions
        if RoleManager.has_any_allowed_role(user):
            self.add_item(ToggleCheckInButton())
            self.add_item(ResetCheckInButton())

    async def on_timeout(self):
        """Handle view timeout by showing timeout notice and disabling buttons."""
        for item in self.children:
            item.disabled = True
            
        if self.original_message:
            try:
                # Get timeout message from config
                from config import _FULL_CFG
                timeout_notice = _FULL_CFG.get("embeds", {}).get("confirmations", {}).get("timeout_notice", 
                    "⏰ This interface has expired. Click **Manage Registration** or **Manage Check-In** in the main channel to continue.")
                
                # Update current embed to add timeout notice
                current_embed = self.original_message.embeds[0] if self.original_message.embeds else discord.Embed(title="✅ Check-In Management")
                
                # Add timeout notice as a new field
                current_embed.add_field(name="\u200b", value="\u200b", inline=False)  # Blank line
                current_embed.add_field(
                    name="Session Expired",
                    value=timeout_notice,
                    inline=False
                )
                current_embed.color = discord.Color.orange()
                
                await self.original_message.edit(embed=current_embed, view=self)
            except Exception:
                pass  # Don't fail if we can't update the message


class ModeToggleButton(discord.ui.Button):
    """Toggle between normal and double up mode."""
    
    def __init__(self):
        super().__init__(
            label="Mode Toggle",
            style=discord.ButtonStyle.primary,
            custom_id="admin_mode_toggle",
            emoji="🔄"
        )

    async def callback(self, interaction: discord.Interaction):
        from core.persistence import get_event_mode_for_guild, set_event_mode_for_guild
        
        # Defer the interaction immediately
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        current_mode = get_event_mode_for_guild(guild_id)
        new_mode = "doubleup" if current_mode == "normal" else "normal"
        set_event_mode_for_guild(guild_id, new_mode)

        await update_unified_channel(interaction.guild)
        
        # Update the admin panel embed with new mode info
        from core.persistence import persisted
        reg_open = persisted.get(guild_id, {}).get("registration_open", False)
        ci_open = persisted.get(guild_id, {}).get("checkin_open", False)
        
        updated_embed = discord.Embed(
            title="🔧 Admin Panel",
            description="Manage tournament settings and controls",
            color=discord.Color.red()
        )
        
        updated_embed.add_field(
            name="Current Status",
            value=f"• **Mode:** {new_mode.capitalize()}\n"
                  f"• **Registration:** {'OPEN 🟢' if reg_open else 'CLOSED 🔴'}\n"
                  f"• **Check-In:** {'OPEN 🟢' if ci_open else 'CLOSED 🔴'}",
            inline=False
        )
        
        updated_embed.add_field(
            name="Available Actions",
            value="• **Mode Toggle** - Switch between normal/double up mode\n"
                  "• **Toggle Registration** - Open/Close registration\n"
                  "• **Toggle Check-In** - Open/Close check-in\n"
                  "• **Reset Registration** - Close registration and clear all data\n"
                  "• **Reset Check-In** - Close check-in and uncheck all players",
            inline=False
        )
        # Add blank line
        updated_embed.add_field(name="\u200b", value="\u200b", inline=False)
        updated_embed.add_field(
            name="✅ Mode Toggle Successful",
            value=f"Tournament mode has been changed to **{new_mode.capitalize()}**.",
            inline=False
        )
        
        updated_view = AdminPanelView(interaction.guild)
        await interaction.edit_original_response(embed=updated_embed, view=updated_view)


class AdminPanelView(discord.ui.View):
    """View for admin panel controls."""
    
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=300)
        self.guild = guild
        
        self.add_item(ModeToggleButton())
        self.add_item(ToggleRegistrationButton())
        self.add_item(ToggleCheckInButton())
        self.add_item(ResetRegistrationButton())
        self.add_item(ResetCheckInButton())
        self.add_item(ReminderButton())

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# Individual Action Buttons for Management Views
class RegisterButton(discord.ui.Button):
    """Register button for registration management."""
    
    def __init__(self):
        super().__init__(
            label="Register",
            style=discord.ButtonStyle.success,
            custom_id="reg_register"
        )

    async def callback(self, interaction: discord.Interaction):
        from core.views import RegistrationModal
        from helpers import SheetOperations
        from helpers.waitlist_helpers import WaitlistManager

        guild_id = str(interaction.guild.id)
        mode = get_event_mode_for_guild(guild_id)
        discord_tag = str(interaction.user)

        # Try to get existing data quickly from cache first
        modal = None
        try:
            # Check cache quickly (should be fast since it's in memory)
            from integrations.sheets import sheet_cache, cache_lock
            
            user_data = None
            waitlist_data = None
            
            # Quick cache check for existing user data
            async with cache_lock:
                if discord_tag in sheet_cache.get("users", {}):
                    raw_data = sheet_cache["users"][discord_tag]
                    if len(raw_data) >= 4:  # Has required fields
                        user_data = {
                            "ign": raw_data[1],
                            "alt_ign": raw_data[3] if len(raw_data) > 3 else "",
                            "team": raw_data[4] if len(raw_data) > 4 and mode == "doubleup" else "",
                            "pronouns": raw_data[0]
                        }
            
            # If not in sheet cache, check waitlist quickly
            if not user_data:
                waitlist_data = await WaitlistManager.get_waitlist_entry(guild_id, discord_tag)

            # Create modal with prefilled data if available
            if user_data:
                modal = RegistrationModal(
                    team_field=(mode == "doubleup"),
                    default_ign=user_data["ign"],
                    default_alt_igns=user_data["alt_ign"],
                    default_team=user_data.get("team", ""),
                    default_pronouns=user_data["pronouns"],
                    update_management_interface=True
                )
            elif waitlist_data:
                modal = RegistrationModal(
                    team_field=(mode == "doubleup"),
                    default_ign=waitlist_data["ign"],
                    default_alt_igns=waitlist_data.get("alt_igns", ""),
                    default_team=waitlist_data.get("team_name", ""),
                    default_pronouns=waitlist_data.get("pronouns", ""),
                    update_management_interface=True
                )
        except Exception as e:
            # If data lookup fails, continue with empty modal
            logging.debug(f"Failed to prefill registration modal: {e}")
        
        # Create empty modal if prefill failed
        if not modal:
            modal = RegistrationModal(
                team_field=(mode == "doubleup"),
                update_management_interface=True
            )
        
        # Set modal properties
        modal.guild = interaction.guild
        modal.member = interaction.user
        modal.management_view = self.management_view

        # Respond with modal (should be fast since we use cache)
        await interaction.response.send_modal(modal)


class UpdateRegistrationButton(discord.ui.Button):
    """Update registration button."""
    
    def __init__(self):
        super().__init__(
            label="Update Registration",
            style=discord.ButtonStyle.success,
            custom_id="reg_update",
            emoji="✏️"
        )

    async def callback(self, interaction: discord.Interaction):
        # Same logic as RegisterButton but store original message info
        from core.views import RegistrationModal
        from integrations.sheets import sheet_cache, cache_lock
        from helpers.waitlist_helpers import WaitlistManager

        guild_id = str(interaction.guild.id)
        mode = get_event_mode_for_guild(guild_id)
        discord_tag = str(interaction.user)

        # Check cache for existing user data (fast, no API calls)
        user_data = None
        waitlist_data = None
        
        try:
            # Check waitlist first - if user is on waitlist, prioritize waitlist data
            waitlist_data = await WaitlistManager.get_waitlist_entry(guild_id, discord_tag)
            
            # If not on waitlist, check sheet cache
            if not waitlist_data:
                async with cache_lock:
                    cached_user = sheet_cache["users"].get(discord_tag)
                    if cached_user:
                        # cached_user format: (row, ign, reg_status, checked_in, team, alt_igns, pronouns)
                        _, ign, _, _, team, alt_igns, pronouns = cached_user
                        user_data = {
                            "ign": ign or "",
                            "team": team or "",
                            "alt_ign": alt_igns or "",
                            "pronouns": pronouns or ""
                        }
        except:
            # If cache fails, proceed with empty modal
            pass

        # Build modal with prefilled data - prioritize waitlist data
        if waitlist_data:
            modal = RegistrationModal(
                team_field=(mode == "doubleup"),
                default_ign=waitlist_data.get("ign", ""),
                default_alt_igns=waitlist_data.get("alt_igns", ""),
                default_team=waitlist_data.get("team_name", ""),
                default_pronouns=waitlist_data.get("pronouns", ""),
                update_management_interface=True
            )
        elif user_data:
            modal = RegistrationModal(
                team_field=(mode == "doubleup"),
                default_ign=user_data["ign"],
                default_alt_igns=user_data["alt_ign"],
                default_team=user_data["team"],
                default_pronouns=user_data["pronouns"],
                update_management_interface=True
            )
        else:
            modal = RegistrationModal(
                team_field=(mode == "doubleup"),
                update_management_interface=True
            )
        
        modal.guild = interaction.guild
        modal.member = interaction.user
        # Store reference to the management view for updating the message
        modal.management_view = self.management_view
        
        # Respond with modal (should be fast since we used cache)
        await interaction.response.send_modal(modal)


class UnregisterButton(discord.ui.Button):
    """Unregister button with updated interaction."""
    
    def __init__(self):
        super().__init__(
            label="Unregister",
            style=discord.ButtonStyle.danger,
            custom_id="reg_unregister"
        )

    async def callback(self, interaction: discord.Interaction):
        from integrations.sheets import unregister_user
        from helpers.waitlist_helpers import WaitlistManager

        # Dismiss this button interaction immediately
        await interaction.response.defer(ephemeral=True, thinking=False)
        
        discord_tag = str(interaction.user)
        guild_id = str(interaction.guild.id)

        # Check waitlist first
        waitlist_pos = await WaitlistManager.get_waitlist_position(guild_id, discord_tag)

        if waitlist_pos:
            await WaitlistManager.remove_from_waitlist(guild_id, discord_tag)
            success = True
        else:
            success = await unregister_user(discord_tag, guild_id)
            if success:
                await RoleManager.remove_roles(
                    interaction.user,
                    [get_registered_role(), get_checked_in_role()]
                )
                await WaitlistManager.process_waitlist(interaction.guild)

        if success:
            confirmation = get_confirmation_message("unregistered")
            new_embed = create_management_embed(
                user_status="You are not registered for this tournament",
                status_emoji="❌",
                confirmation_message=confirmation
            )
            new_view = RegistrationManagementView(interaction.user, False, False)
            
            # Use the button's response to show updated management interface
            await interaction.edit_original_response(embed=new_embed, view=new_view)
        else:
            # Show error in button interaction
            await interaction.edit_original_response(
                embed=embed_from_cfg("registration_required"),
                view=None
            )

        await update_unified_channel(interaction.guild)


class CheckInButton(discord.ui.Button):
    """Check in button with updated interaction."""
    
    def __init__(self):
        super().__init__(
            label="Check In",
            style=discord.ButtonStyle.success,
            custom_id="ci_checkin"
        )

    async def callback(self, interaction: discord.Interaction):
        from integrations.sheets import mark_checked_in_async

        if not RoleManager.is_registered(interaction.user):
            await interaction.response.send_message(
                embed=embed_from_cfg("registration_required"),
                ephemeral=True
            )
            return

        if RoleManager.is_checked_in(interaction.user):
            await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_in"),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        discord_tag = str(interaction.user)
        guild_id = str(interaction.guild.id)
        
        success = await mark_checked_in_async(discord_tag, guild_id)
        if success:
            await RoleManager.add_role(interaction.user, get_checked_in_role())
            
            # Send success message with updated management interface using consistent format
            confirmation = get_confirmation_message("checked_in")
            mgmt_embed = create_management_embed(
                user_status="You are currently checked in for this tournament",
                status_emoji="✅",
                confirmation_message=confirmation,
                embed_type="checkin"
            )
            mgmt_view = CheckInManagementView(interaction.user, True)
            try:
                await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)
            except discord.NotFound:
                await interaction.followup.send(embed=mgmt_embed, view=mgmt_view, ephemeral=True)
        else:
            # Check if user is actually in the cache/sheet
            from integrations.sheets import sheet_cache, cache_lock
            async with cache_lock:
                user_in_cache = discord_tag in sheet_cache.get("users", {})
            
            if not user_in_cache:
                # User has registered role but isn't in cache/sheet - remove role and show error
                await RoleManager.remove_roles(interaction.user, [get_registered_role(), get_checked_in_role()])
                
                error_embed = discord.Embed(
                    title="❌ Registration Data Not Found",
                    description="It looks like your registration data was not found in our system, but you had the registered role.\n\n"
                               "**Your roles have been reset.** Please re-register for the tournament.",
                    color=discord.Color.red()
                )
                error_embed.add_field(
                    name="What to do next",
                    value="1. Click **Register** below to re-register\n"
                          "2. Or go back to the main tournament channel\n" 
                          "3. Use **Manage Registration** to register again",
                    inline=False
                )
                
                # Create a new management view for unregistered state
                new_view = RegistrationManagementView(interaction.user, False, False)
                try:
                    await interaction.edit_original_response(embed=error_embed, view=new_view)
                except discord.NotFound:
                    await interaction.followup.send(embed=error_embed, view=new_view, ephemeral=True)
            else:
                await interaction.followup.send(
                    embed=embed_from_cfg("error"),
                    ephemeral=True
                )

        await update_unified_channel(interaction.guild)


class CheckOutButton(discord.ui.Button):
    """Check out button with updated interaction."""
    
    def __init__(self):
        super().__init__(
            label="Check Out",
            style=discord.ButtonStyle.danger,
            custom_id="ci_checkout"
        )

    async def callback(self, interaction: discord.Interaction):
        from integrations.sheets import unmark_checked_in_async

        if not RoleManager.is_checked_in(interaction.user):
            await interaction.response.send_message(
                embed=embed_from_cfg("already_checked_out"),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        discord_tag = str(interaction.user)
        guild_id = str(interaction.guild.id)
        
        success = await unmark_checked_in_async(discord_tag, guild_id)
        if success:
            await RoleManager.remove_role(interaction.user, get_checked_in_role())
            
            # Send success message with updated management interface using consistent format
            confirmation = get_confirmation_message("checked_out")
            mgmt_embed = create_management_embed(
                user_status="You are registered but not checked in yet",
                status_emoji="⏳",
                confirmation_message=confirmation,
                embed_type="checkin"
            )
            mgmt_view = CheckInManagementView(interaction.user, False)
            try:
                await interaction.edit_original_response(embed=mgmt_embed, view=mgmt_view)
            except discord.NotFound:
                await interaction.followup.send(embed=mgmt_embed, view=mgmt_view, ephemeral=True)
        else:
            await interaction.followup.send(
                embed=embed_from_cfg("error"),
                ephemeral=True
            )

        await update_unified_channel(interaction.guild)


# Admin Panel Action Buttons
class ToggleRegistrationButton(discord.ui.Button):
    """Toggle registration status."""
    
    def __init__(self):
        super().__init__(
            label="Toggle Registration",
            style=discord.ButtonStyle.secondary,
            custom_id="admin_toggle_reg",
            emoji="👁️"
        )

    async def callback(self, interaction: discord.Interaction):
        from core.persistence import persisted, save_persisted
        
        # Defer the interaction immediately
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        if guild_id not in persisted:
            persisted[guild_id] = {}
        
        current_status = persisted[guild_id].get("registration_open", False)
        new_status = not current_status
        persisted[guild_id]["registration_open"] = new_status
        save_persisted(persisted)

        await update_unified_channel(interaction.guild)
        
        # Update the admin panel embed with new status
        guild_id = str(interaction.guild.id)
        reg_open = persisted[guild_id].get("registration_open", False)
        ci_open = persisted[guild_id].get("checkin_open", False)
        
        updated_embed = discord.Embed(
            title="🔧 Admin Panel",
            description="Manage tournament settings and controls",
            color=discord.Color.red()
        )
        
        updated_embed.add_field(
            name="Current Status",
            value=f"• **Registration:** {'OPEN 🟢' if reg_open else 'CLOSED 🔴'}\n"
                  f"• **Check-In:** {'OPEN 🟢' if ci_open else 'CLOSED 🔴'}",
            inline=False
        )
        
        updated_embed.add_field(
            name="Available Actions",
            value="• **Toggle Registration** - Open/Close registration\n"
                  "• **Toggle Check-In** - Open/Close check-in\n"
                  "• **Reset Registration** - Close registration and clear all data\n"
                  "• **Reset Check-In** - Close check-in and uncheck all players",
            inline=False
        )
        # Add blank line
        updated_embed.add_field(name="\u200b", value="\u200b", inline=False)
        updated_embed.add_field(
            name="✅ Registration Toggle Successful",
            value=f"Registration has been **{'opened' if reg_open else 'closed'}**.",
            inline=False
        )
        
        updated_view = AdminPanelView(interaction.guild)
        await interaction.edit_original_response(embed=updated_embed, view=updated_view)


class ToggleCheckInButton(discord.ui.Button):
    """Toggle check-in status."""
    
    def __init__(self):
        super().__init__(
            label="Toggle Check-In",
            style=discord.ButtonStyle.secondary,
            custom_id="admin_toggle_ci",
            emoji="👁️"
        )

    async def callback(self, interaction: discord.Interaction):
        from core.persistence import persisted, save_persisted
        
        # Defer the interaction immediately
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        if guild_id not in persisted:
            persisted[guild_id] = {}
        
        current_status = persisted[guild_id].get("checkin_open", False)
        new_status = not current_status
        persisted[guild_id]["checkin_open"] = new_status
        save_persisted(persisted)

        await update_unified_channel(interaction.guild)
        
        # Update the admin panel embed with new status
        guild_id = str(interaction.guild.id)
        reg_open = persisted[guild_id].get("registration_open", False)
        ci_open = persisted[guild_id].get("checkin_open", False)
        
        updated_embed = discord.Embed(
            title="🔧 Admin Panel",
            description="Manage tournament settings and controls",
            color=discord.Color.red()
        )
        
        updated_embed.add_field(
            name="Current Status",
            value=f"• **Registration:** {'OPEN 🟢' if reg_open else 'CLOSED 🔴'}\n"
                  f"• **Check-In:** {'OPEN 🟢' if ci_open else 'CLOSED 🔴'}",
            inline=False
        )
        
        updated_embed.add_field(
            name="Available Actions",
            value="• **Toggle Registration** - Open/Close registration\n"
                  "• **Toggle Check-In** - Open/Close check-in\n"
                  "• **Reset Registration** - Close registration and clear all data\n"
                  "• **Reset Check-In** - Close check-in and uncheck all players",
            inline=False
        )
        # Add blank line
        updated_embed.add_field(name="\u200b", value="\u200b", inline=False)
        updated_embed.add_field(
            name="✅ Check-In Toggle Successful",
            value=f"Check-In has been **{'opened' if ci_open else 'closed'}**.",
            inline=False
        )
        
        updated_view = AdminPanelView(interaction.guild)
        await interaction.edit_original_response(embed=updated_embed, view=updated_view)


class ResetRegistrationButton(discord.ui.Button):
    """Reset registration system."""
    
    def __init__(self):
        super().__init__(
            label="Reset Registration",
            style=discord.ButtonStyle.danger,
            custom_id="admin_reset_reg",
            emoji="🔄"
        )

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚠️ Reset Registration",
            description="This will **close registration** and **clear all registration data**. This action cannot be undone!\n\nAre you sure you want to proceed?",
            color=discord.Color.orange()
        )
        
        view = ResetConfirmationView("registration", interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ResetCheckInButton(discord.ui.Button):
    """Reset check-in system."""
    
    def __init__(self):
        super().__init__(
            label="Reset Check-In",
            style=discord.ButtonStyle.danger,
            custom_id="admin_reset_ci",
            emoji="🔄"
        )

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚠️ Reset Check-In",
            description="This will **close check-in** and **uncheck all players**. Registration data will remain intact.\n\nAre you sure you want to proceed?",
            color=discord.Color.orange()
        )
        
        view = ResetConfirmationView("checkin", interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ResetConfirmationView(discord.ui.View):
    """Confirmation view for reset operations."""
    
    def __init__(self, reset_type: str, guild: discord.Guild):
        super().__init__(timeout=30)
        self.reset_type = reset_type
        self.guild = guild

    @discord.ui.button(label="Yes, Reset", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        from core.persistence import persisted, save_persisted
        
        guild_id = str(self.guild.id)
        if guild_id not in persisted:
            persisted[guild_id] = {}
        
        try:
            if self.reset_type == "registration":
                # Close registration and reset all data using existing function
                persisted[guild_id]["registration_open"] = False
                save_persisted(persisted)
                
                from integrations.sheets import reset_registered_roles_and_sheet
                cleared_count = await reset_registered_roles_and_sheet(self.guild, None)
                
                embed = discord.Embed(
                    title="✅ Registration Reset Complete",
                    description=f"Registration has been closed and all registration data has been cleared.\n\n**{cleared_count}** rows reset and all registration roles removed.",
                    color=discord.Color.red()
                )
            else:  # checkin
                # Close check-in and reset check-in data using existing function
                persisted[guild_id]["checkin_open"] = False
                save_persisted(persisted)
                
                from integrations.sheets import reset_checked_in_roles_and_sheet
                cleared_count = await reset_checked_in_roles_and_sheet(self.guild, None)
                
                embed = discord.Embed(
                    title="✅ Check-In Reset Complete", 
                    description=f"Check-in has been closed and all players have been unchecked.\n\n**{cleared_count}** rows reset and all check-in roles removed.",
                    color=discord.Color.red()
                )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Reset Failed",
                description=f"An error occurred during reset: {str(e)}",
                color=discord.Color.red()
            )
        
        await update_unified_channel(self.guild)
        
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Reset Cancelled",
            description="The reset operation has been cancelled.",
            color=discord.Color.green()
        )
        
        for item in self.children:
            item.disabled = True
            
        await interaction.response.edit_message(embed=embed, view=self)


# Channel Management Functions
async def setup_unified_channel(guild: discord.Guild) -> bool:
    """Setup the unified channel with traditional embed."""
    try:
        channel_name = get_unified_channel_name()
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel:
            logging.error(f"Channel '{channel_name}' not found")
            return False

        chan_id, msg_id = get_persisted_msg(guild.id, "unified")
        if chan_id and msg_id and chan_id == channel.id:
            try:
                existing_msg = await channel.fetch_message(msg_id)
                # Try to update the existing message, if it fails due to Components V2, we'll recreate
                return await update_unified_channel(guild)
            except discord.NotFound:
                pass

        embed, view = await build_unified_embed(guild)
        msg = await channel.send(embed=embed, view=view)
        set_persisted_msg(guild.id, "unified", channel.id, msg.id)

        try:
            await msg.pin()
            async for m in channel.history(limit=5):
                if m.type == discord.MessageType.pins_add:
                    await m.delete()
                    break
        except Exception:
            pass

        logging.info(f"Setup unified traditional embed in {guild.name}")
        return True
    except Exception as e:
        logging.error(f"Failed to setup unified channel: {e}", exc_info=True)
        return False


async def update_unified_channel(guild: discord.Guild) -> bool:
    """Update the unified channel with fresh data."""
    try:
        chan_id, msg_id = get_persisted_msg(guild.id, "unified")
        if not chan_id or not msg_id:
            return await setup_unified_channel(guild)

        channel = guild.get_channel(chan_id)
        if not channel:
            return False

        try:
            msg = await channel.fetch_message(msg_id)
            embed, view = await build_unified_embed(guild)
            await msg.edit(embed=embed, view=view)
            return True
        except discord.NotFound:
            return await setup_unified_channel(guild)
        except discord.HTTPException as e:
            # If we get a Components V2 error, delete and recreate
            if "MessageFlags.IS_COMPONENTS_V2" in str(e) or "IS_COMPONENTS_V2" in str(e):
                logging.info(f"Detected Components V2 message, recreating as traditional embed")
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.delete()
                except Exception:
                    pass
                return await setup_unified_channel(guild)
            else:
                raise
    except Exception as e:
        logging.error(f"Failed to update unified channel: {e}", exc_info=True)
        return False