# core/commands.py

import logging
import os
import time
from datetime import timezone, datetime
from typing import Optional, Dict, Any

import discord
import yaml
from discord import app_commands
from discord.ext import commands

from config import (
    embed_from_cfg, get_sheet_settings, _FULL_CFG, get_log_channel_name,
    get_unified_channel_name
)
from core.persistence import (
    get_event_mode_for_guild, set_event_mode_for_guild
)
from core.views import (
    DMActionView, update_unified_channel
)
# Import all helpers
from helpers import (
    RoleManager, Validators,
    ErrorHandler, ConfigManager, EmbedHelper
)
from integrations.sheets import (
    refresh_sheet_cache
)
from utils.utils import (
    send_reminder_dms,
)


class CommandError(Exception):
    """Custom exception for command-related errors."""
    pass


# Create command group with better error handling
gal = app_commands.Group(
    name="gal",
    description="Group of GAL bot commands"
)


@gal.command(name="toggle", description="Toggle registration or check-in status.")
@app_commands.describe(
    system="Which system to toggle (registration or checkin)",
    silent="Toggle silently without announcements (default: False)"
)
@app_commands.choices(system=[
    app_commands.Choice(name="registration", value="registration"),
    app_commands.Choice(name="checkin", value="checkin"),
    app_commands.Choice(name="both", value="both")
])
async def toggle(interaction: discord.Interaction, system: app_commands.Choice[str], silent: bool = False):
    """Toggle registration or check-in status."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        from core.persistence import persisted, save_persisted

        guild_id = str(interaction.guild.id)
        if guild_id not in persisted:
            persisted[guild_id] = {}

        system_value = system.value

        # Get current states
        reg_open = persisted[guild_id].get("registration_open", False)
        ci_open = persisted[guild_id].get("checkin_open", False)

        # Toggle based on selection
        if system_value == "registration":
            reg_open = not reg_open
            persisted[guild_id]["registration_open"] = reg_open
            status = f"Registration is now {'OPEN' if reg_open else 'CLOSED'}"
        elif system_value == "checkin":
            ci_open = not ci_open
            persisted[guild_id]["checkin_open"] = ci_open
            status = f"Check-in is now {'OPEN' if ci_open else 'CLOSED'}"
        else:  # both
            reg_open = not reg_open
            ci_open = not ci_open
            persisted[guild_id]["registration_open"] = reg_open
            persisted[guild_id]["checkin_open"] = ci_open
            status = f"Registration: {'OPEN' if reg_open else 'CLOSED'}\nCheck-in: {'OPEN' if ci_open else 'CLOSED'}"

        save_persisted(persisted)

        # Update unified channel
        await update_unified_channel(interaction.guild)
        
        # Handle ping notifications when systems are opened (not when closed)
        if not silent:
            await handle_toggle_pings(interaction.guild, system_value, reg_open, ci_open)

        # Send feedback
        embed = discord.Embed(
            title="✅ System Toggled",
            description=status,
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed, ephemeral=not silent)

        # Log the change if not silent
        if not silent:
            log_channel = discord.utils.get(interaction.guild.text_channels, name=get_log_channel_name())
            if log_channel:
                log_embed = discord.Embed(
                    title="🔄 System Status Changed",
                    description=f"{status}\n\nChanged by {interaction.user.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc)
                )
                await log_channel.send(embed=log_embed)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Toggle Command")


@gal.command(name="event", description="View or set the event mode for this guild (normal/doubleup).")
@app_commands.describe(mode="Set the event mode (normal/doubleup)")
@app_commands.choices(mode=[
    app_commands.Choice(name="normal", value="normal"),
    app_commands.Choice(name="doubleup", value="doubleup")
])
async def event(interaction: discord.Interaction, mode: Optional[app_commands.Choice[str]] = None):
    """View or set event mode."""
    try:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        guild_id = str(guild.id)

        current_mode = get_event_mode_for_guild(guild_id)

        # If no mode is provided, show current mode
        if mode is None:
            embed = embed_from_cfg(
                "event_mode_current",
                mode=current_mode.capitalize()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Only staff can change mode
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            embed = embed_from_cfg("permission_denied")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        mode_value = mode.value
        set_event_mode_for_guild(guild_id, mode_value)

        await interaction.followup.send(
            embed=embed_from_cfg(
                "event_mode_set",
                mode=mode_value.capitalize()
            ),
            ephemeral=True
        )

        # Update embeds/views after mode change
        await refresh_sheet_cache(bot=interaction.client)
        await update_unified_channel(guild)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Event Command")


@gal.command(name="registeredlist", description="Show all registered users with check-in status.")
async def registeredlist(interaction: discord.Interaction):
    """Display registered users list with check-in status."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        await interaction.response.defer(ephemeral=False)
        guild_id = str(interaction.guild.id)
        mode = get_event_mode_for_guild(guild_id)

        # Get all registered users from cache
        from integrations.sheets import sheet_cache, cache_lock

        async with cache_lock:
            all_registered = [(tag, tpl) for tag, tpl in sheet_cache["users"].items()
                              if str(tpl[2]).upper() == "TRUE"]

        if not all_registered:
            # No registered users
            embed = discord.Embed(
                title="📋 Registered Players List",
                description="*No registered players found.*",
                color=discord.Color.blurple()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return

        # Use the same helper as check-in to build lines
        lines = EmbedHelper.build_checkin_list_lines(all_registered, mode)

        # Calculate statistics
        total_registered = len(all_registered)
        total_checked_in = sum(1 for _, tpl in all_registered
                               if str(tpl[3]).upper() == "TRUE")

        # Build embed
        embed = discord.Embed(
            title="📋 Registered Players List",
            description="\n".join(lines) if lines else "No registered players found.",
            color=discord.Color.blurple()
        )

        # Build footer with correct order: Players, Teams (if doubleup), Checked-In, Percentage
        footer_parts = [f"👤 Players: {total_registered}"]

        if mode == "doubleup":
            # Count teams
            teams = set()
            for _, tpl in all_registered:
                if len(tpl) > 4 and tpl[4]:
                    teams.add(tpl[4])
            if teams:  # Only show if there are teams
                footer_parts.append(f"👥 Teams: {len(teams)}")

        footer_parts.append(f"✅ Checked-In: {total_checked_in}")

        if total_registered > 0:
            percentage = (total_checked_in / total_registered) * 100
            footer_parts.append(f"📊 {percentage:.0f}%")

        embed.set_footer(text=" • ".join(footer_parts))

        # Send with the persistent view that includes reminder button
        await interaction.followup.send(
            embed=embed,
            ephemeral=False  # ,
            # view=PersistentRegisteredListView(interaction.guild)
        )

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Registered List Command")


@gal.command(name="reminder", description="DM all registered users who are not checked in.")
async def reminder(interaction: discord.Interaction):
    """Send reminder DMs to unchecked users."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        await interaction.response.defer(ephemeral=False)

        dm_embed = embed_from_cfg("reminder_dm")
        guild = interaction.guild

        # Use existing helper
        dmmed = await send_reminder_dms(
            client=interaction.client,
            guild=guild,
            dm_embed=dm_embed,
            view_cls=DMActionView
        )

        # Summarize results
        count = len(dmmed)
        users_list = "\n".join(dmmed) if dmmed else "No users could be DM'd."
        public_embed = embed_from_cfg("reminder_public", count=count, users=users_list)

        await interaction.followup.send(embed=public_embed, ephemeral=False)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Reminder Command")


@gal.command(name="cache", description="Forces a manual refresh of the user cache from the Google Sheet.")
async def cache(interaction: discord.Interaction):
    """Refresh sheet cache manually."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        await interaction.response.defer(ephemeral=True)
        start_time = time.perf_counter()

        # Refresh cache (this will also update unified channels automatically)
        updated_users, total_users = await refresh_sheet_cache(bot=interaction.client)
        elapsed = time.perf_counter() - start_time

        # The unified channel is already updated by refresh_sheet_cache, so we don't need to call it again
        embed_success = True

        embed = embed_from_cfg(
            "cache",
            updated=updated_users,
            count=total_users,
            elapsed=elapsed
        )

        # Add embed update info if available
        if embed_success is not None:
            embed.add_field(
                name="Embed Updates",
                value=f"{'✅ Success' if embed_success else '❌ Failed'}",
                inline=True
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Cache Command")


@gal.command(name="config", description="Manage bot configuration")
@app_commands.describe(
    action="Configuration action to perform",
    file="Configuration file to upload (only for 'upload' action)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="edit", value="edit"),
    app_commands.Choice(name="download", value="download"),
    app_commands.Choice(name="upload", value="upload"),
    app_commands.Choice(name="reload", value="reload")
])
async def config_cmd(
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        file: Optional[discord.Attachment] = None
):
    """Manage bot configuration."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        action_value = action.value

        if action_value == "edit":
            # Show configuration menu with buttons
            guild_id = str(interaction.guild.id)
            current_mode = get_event_mode_for_guild(guild_id)
            settings = get_sheet_settings(current_mode)

            # Create info embed
            embed = discord.Embed(
                title="⚙️ Configuration Manager",
                description="Select what you'd like to configure:",
                color=discord.Color.blurple()
            )

            # Add current status info
            is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
            environment = "Production" if is_production else "Development"

            # Get cache refresh from config
            cache_refresh_seconds = _FULL_CFG.get("cache_refresh_seconds", 600)

            embed.add_field(
                name="Current Settings",
                value=f"**Mode:** {current_mode}\n"
                      f"**Environment:** {environment}\n"
                      f"**Max Players:** {settings.get('max_players', 32)}",
                inline=True
            )

            embed.add_field(
                name="Cache Status",
                value=f"**Refresh Rate:** {cache_refresh_seconds}s\n"
                      f"**Last Refresh:** Recently",
                inline=True
            )

            embed.set_footer(text="💡 Tip: All changes create automatic backups")

            # Send with the configuration menu view
            view = ConfigMenuView(current_mode)
            message = await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

            # Store message reference for timeout handling
            if hasattr(message, 'message'):
                view.message = message.message
            else:
                view.message = await interaction.original_response()

        elif action_value == "download":
            # Send current config.yaml as a file
            await interaction.response.defer(ephemeral=True)

            with open("config.yaml", "rb") as f:
                config_file = discord.File(f, filename="config.yaml")

            embed = discord.Embed(
                title="📥 Configuration Download",
                description="Here's your current `config.yaml` file.\n\n"
                            "**Edit this file for:**\n"
                            "• Embed messages\n"
                            "• Advanced settings\n"
                            "• Bulk changes\n\n"
                            "Then use `/gal config upload` to apply changes.",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, file=config_file, ephemeral=True)

        elif action_value == "upload":
            if not file:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ No File Attached",
                        description="Please attach a `config.yaml` file to upload.\n\n"
                                    "Use `/gal config download` to get the current configuration first.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return

            if not file.filename.endswith((".yaml", ".yml")):
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Invalid File Type",
                        description="File must be a YAML file (`.yaml` or `.yml` extension).",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True)

            # Clean up old timestamped backups
            import glob
            try:
                old_backups = glob.glob("config_backup_*.yaml")
                for old_backup in old_backups:
                    if not old_backup.endswith("_latest.yaml"):
                        try:
                            os.remove(old_backup)
                        except:
                            pass
            except:
                pass

            # Create single backup
            from datetime import datetime
            import shutil
            backup_name = "config_backup_latest.yaml"
            shutil.copy("config.yaml", backup_name)

            try:
                # Download and validate the new config
                content = await file.read()
                new_config = yaml.safe_load(content)

                # Validate required sections
                required_sections = ["embeds", "sheet_configuration"]
                for section in required_sections:
                    if section not in new_config:
                        raise ValueError(f"Missing required section: {section}")

                # Save new config
                with open("config.yaml", "wb") as f:
                    f.write(content)

                # Try to reload configuration
                try:
                    from helpers import ConfigManager
                    results = await ConfigManager.reload_and_update_all(interaction.client)

                    embed = discord.Embed(
                        title="✅ Configuration Uploaded",
                        description=f"Configuration has been updated successfully!",
                        color=discord.Color.green()
                    )

                    if results["config_reload"]:
                        embed.add_field(
                            name="✅ Status",
                            value="Configuration reloaded and applied",
                            inline=False
                        )

                    await interaction.followup.send(embed=embed, ephemeral=True)

                    # Log to bot-log channel with revert button
                    log_channel = discord.utils.get(interaction.guild.text_channels, name=get_log_channel_name())
                    if log_channel:
                        # Clear old revert buttons first
                        await clear_old_config_views(log_channel)

                        log_embed = discord.Embed(
                            title="📝 Configuration Uploaded",
                            description=f"Configuration was uploaded by {interaction.user.mention}",
                            color=discord.Color.blue(),
                            timestamp=datetime.now(timezone.utc)
                        )

                        # Add revert view to new message
                        revert_view = ConfigRevertView(backup_name)
                        await log_channel.send(embed=log_embed, view=revert_view)

                except Exception as reload_error:
                    # Reload failed, restore backup
                    shutil.copy(backup_name, "config.yaml")
                    from helpers import ConfigManager
                    await ConfigManager.reload_and_update_all(interaction.client)

                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="❌ Configuration Invalid",
                            description=f"The uploaded configuration caused an error and has been reverted.\n\n"
                                        f"**Error:** `{str(reload_error)[:100]}`",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )

            except yaml.YAMLError as e:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Invalid YAML",
                        description=f"The file contains invalid YAML syntax:\n```{str(e)[:200]}```",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Upload Failed",
                        description=f"Failed to process the uploaded file:\n```{str(e)[:200]}```",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

        elif action_value == "reload":
            # Reload configuration from file
            await interaction.response.defer(ephemeral=True)

            try:
                from helpers import ConfigManager
                results = await ConfigManager.reload_and_update_all(interaction.client)

                # Refresh sheet cache
                from integrations.sheets import refresh_sheet_cache
                await refresh_sheet_cache(bot=interaction.client)

                if results["config_reload"]:
                    embed = discord.Embed(
                        title="✅ Configuration Reloaded",
                        description="All settings have been refreshed from `config.yaml`",
                        color=discord.Color.green()
                    )

                    # Show what was updated
                    if results.get("embeds_updated"):
                        updated_count = sum(
                            sum(1 for v in guild_results.values() if v)
                            for guild_results in results["embeds_updated"].values()
                        )
                        embed.add_field(
                            name="📝 Embeds",
                            value=f"{updated_count} embeds refreshed",
                            inline=True
                        )

                    if results.get("presence_update"):
                        embed.add_field(
                            name="🎮 Bot Status",
                            value="Updated successfully",
                            inline=True
                        )

                    embed.add_field(
                        name="📊 Cache",
                        value="Sheet cache refreshed",
                        inline=True
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Reload Failed",
                        description="Failed to reload configuration. Check the logs for details.",
                        color=discord.Color.red()
                    )

                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Reload Error",
                        description=f"Error reloading configuration:\n```{str(e)[:200]}```",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Config Command")


class ConfigMenuView(discord.ui.View):
    """Configuration menu with buttons for different config options."""

    def __init__(self, current_mode: str):
        super().__init__(timeout=300)  # 5 minute timeout
        self.current_mode = current_mode

    async def on_timeout(self):
        """Disable all buttons when the view times out."""
        for item in self.children:
            item.disabled = True

        # Try to edit the message to show buttons as disabled
        try:
            # We need to store the message reference when sending
            if hasattr(self, 'message'):
                await self.message.edit(view=self)
        except:
            pass  # Message might be deleted or we don't have permissions

    @discord.ui.button(label="⚙️ General Settings", style=discord.ButtonStyle.primary, row=0)
    async def general_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit general bot settings."""
        modal = GeneralConfigModal(self.current_mode)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📊 Column Mappings", style=discord.ButtonStyle.primary, row=0)
    async def column_mappings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit sheet column mappings."""
        modal = ColumnConfigModal(self.current_mode)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📄 Sheet URLs", style=discord.ButtonStyle.primary, row=0)
    async def sheet_urls(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit Google Sheet URLs."""
        modal = SheetConfigModal(self.current_mode)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📥 Download Config", style=discord.ButtonStyle.secondary, row=1)
    async def download_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download current configuration file."""
        with open("config.yaml", "rb") as f:
            config_file = discord.File(f, filename="config.yaml")

        embed = discord.Embed(
            title="📥 Configuration Download",
            description="Here's your current `config.yaml` file.\n\n"
                        "**Edit this file for:**\n"
                        "• Embed messages\n"
                        "• Advanced settings\n"
                        "• Bulk changes\n\n"
                        "Then use `/gal config upload` to apply changes.",
            color=discord.Color.blue()
        )

        await interaction.response.send_message(
            embed=embed,
            file=config_file,
            ephemeral=True
        )

    @discord.ui.button(label="🔄 Reload Config", style=discord.ButtonStyle.secondary, row=1)
    async def reload_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reload configuration from file."""
        await interaction.response.defer(ephemeral=True)

        try:
            from helpers import ConfigManager
            results = await ConfigManager.reload_and_update_all(interaction.client)

            # Refresh sheet cache
            from integrations.sheets import refresh_sheet_cache
            await refresh_sheet_cache(bot=interaction.client)

            if results["config_reload"]:
                embed = discord.Embed(
                    title="✅ Configuration Reloaded",
                    description="All settings have been refreshed from `config.yaml`",
                    color=discord.Color.green()
                )

                # Show what was updated
                if results.get("embeds_updated"):
                    updated_count = sum(
                        sum(1 for v in guild_results.values() if v)
                        for guild_results in results["embeds_updated"].values()
                    )
                    embed.add_field(
                        name="📝 Embeds",
                        value=f"{updated_count} embeds refreshed",
                        inline=True
                    )

                if results.get("presence_update"):
                    embed.add_field(
                        name="🎮 Bot Status",
                        value="Updated successfully",
                        inline=True
                    )

                embed.add_field(
                    name="📊 Cache",
                    value="Sheet cache refreshed",
                    inline=True
                )
            else:
                embed = discord.Embed(
                    title="❌ Reload Failed",
                    description="Failed to reload configuration. Check the logs for details.",
                    color=discord.Color.red()
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Reload Error",
                    description=f"Error reloading configuration:\n```{str(e)[:200]}```",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

    @discord.ui.button(label="📋 View Current", style=discord.ButtonStyle.success, row=1)
    async def view_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current configuration details."""
        guild_id = str(interaction.guild.id)
        mode = get_event_mode_for_guild(guild_id)
        settings = get_sheet_settings(mode)

        is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
        environment = "Production" if is_production else "Development"

        presence_cfg = _FULL_CFG.get("rich_presence", {})
        bot_status = presence_cfg.get("message", "Not set")

        # Get cache refresh from config, not constant
        cache_refresh_seconds = _FULL_CFG.get("cache_refresh_seconds", 600)

        # Build detailed view
        embed = discord.Embed(
            title="📋 Current Configuration",
            color=discord.Color.blue()
        )

        # General Settings
        embed.add_field(
            name="⚙️ General",
            value=f"**Mode:** {mode}\n"
                  f"**Max Players:** {settings.get('max_players', 32)}\n"
                  f"**Header Line:** {settings.get('header_line_num', 2)}\n"
                  f"**Cache Refresh:** {cache_refresh_seconds}s",
            inline=True
        )

        # Column Mappings
        cols = f"**Discord:** {settings.get('discord_col', 'B')}\n"
        cols += f"**IGN:** {settings.get('ign_col', 'D')}\n"
        cols += f"**Registered:** {settings.get('registered_col', 'F')}\n"
        cols += f"**Check-In:** {settings.get('checkin_col', 'G')}"
        if mode == "doubleup":
            cols += f"\n**Team:** {settings.get('team_col', 'I')}"

        embed.add_field(
            name="📊 Columns",
            value=cols,
            inline=True
        )

        # Environment Info
        embed.add_field(
            name="🌍 Environment",
            value=f"**Type:** {environment}\n"
                  f"**Bot Status:** {bot_status}\n"
                  f"**Using:** {environment} sheets",
            inline=True
        )

        # Sheet URLs (truncated for display)
        from config import get_sheet_url_for_environment
        try:
            current_url = get_sheet_url_for_environment(mode)
            if current_url:
                # Extract sheet ID for cleaner display
                if "/d/" in current_url:
                    sheet_id = current_url.split("/d/")[1].split("/")[0]
                    embed.add_field(
                        name="📄 Active Sheet",
                        value=f"ID: `{sheet_id}...`" if len(sheet_id) > 20 else f"ID: `{sheet_id}`",
                        inline=False
                    )
        except:
            pass

        embed.set_footer(text=f"Mode: {mode} | Environment: {environment}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger, row=2)
    async def close_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the configuration menu."""
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="Configuration menu closed.",
            embed=None,
            view=self
        )


class GeneralConfigModal(discord.ui.Modal):
    """Modal for editing general bot settings."""

    def __init__(self, current_mode: str = "normal"):
        super().__init__(title="Edit General Settings")
        self.current_mode = current_mode

        # Get current settings
        settings = get_sheet_settings(current_mode)
        presence_cfg = _FULL_CFG.get("rich_presence", {})

        # Get cache refresh from root config, not from constants
        current_cache_refresh = _FULL_CFG.get("cache_refresh_seconds", 600)

        # Event Mode
        self.mode_input = discord.ui.TextInput(
            label="Event Mode",
            placeholder="Enter 'normal' or 'doubleup'",
            default=current_mode,
            required=True,
            min_length=6,
            max_length=10
        )
        self.add_item(self.mode_input)

        # Max Players
        self.max_players_input = discord.ui.TextInput(
            label="Maximum Players",
            placeholder="Maximum number of players (e.g., 32)",
            default=str(settings.get("max_players", 32)),
            required=True,
            max_length=4
        )
        self.add_item(self.max_players_input)

        # Header Line
        self.header_line_input = discord.ui.TextInput(
            label="Sheet Header Line Number",
            placeholder="Row number where data starts (e.g., 2)",
            default=str(settings.get("header_line_num", 2)),
            required=True,
            max_length=3
        )
        self.add_item(self.header_line_input)

        # Cache Refresh - now reading from actual config
        self.cache_refresh_input = discord.ui.TextInput(
            label="Cache Refresh Interval (seconds)",
            placeholder="Seconds between cache refreshes (e.g., 600)",
            default=str(current_cache_refresh),
            required=True,
            max_length=5
        )
        self.add_item(self.cache_refresh_input)

        # Bot Status
        self.bot_status_input = discord.ui.TextInput(
            label="Bot Status Message",
            placeholder="Message shown in bot's Discord status",
            default=presence_cfg.get("message", "🛡️ TFT"),
            required=False,
            max_length=128
        )
        self.add_item(self.bot_status_input)

    async def on_submit(self, interaction: discord.Interaction):
        await handle_config_update(
            interaction,
            self,
            update_type="general",
            updates={
                "mode": self.mode_input.value.strip().lower(),
                "max_players": self.max_players_input.value,
                "header_line": self.header_line_input.value,
                "cache_refresh": self.cache_refresh_input.value,
                "bot_status": self.bot_status_input.value.strip()
            }
        )


class ColumnConfigModal(discord.ui.Modal):
    """Modal for editing column mappings."""

    def __init__(self, current_mode: str = "normal"):
        super().__init__(title=f"Edit Column Mappings ({current_mode})")
        self.mode = current_mode

        # Get current settings
        settings = get_sheet_settings(current_mode)

        # Discord Column
        self.discord_col_input = discord.ui.TextInput(
            label="Discord Username Column",
            placeholder="Column letter (e.g., B)",
            default=settings.get("discord_col", "B"),
            required=True,
            max_length=3
        )
        self.add_item(self.discord_col_input)

        # IGN Column
        self.ign_col_input = discord.ui.TextInput(
            label="In-Game Name Column",
            placeholder="Column letter (e.g., D)",
            default=settings.get("ign_col", "D"),
            required=True,
            max_length=3
        )
        self.add_item(self.ign_col_input)

        # Registered Column
        self.registered_col_input = discord.ui.TextInput(
            label="Registered Status Column",
            placeholder="Column letter (e.g., F)",
            default=settings.get("registered_col", "F"),
            required=True,
            max_length=3
        )
        self.add_item(self.registered_col_input)

        # Check-In Column
        self.checkin_col_input = discord.ui.TextInput(
            label="Check-In Status Column",
            placeholder="Column letter (e.g., G)",
            default=settings.get("checkin_col", "G"),
            required=True,
            max_length=3
        )
        self.add_item(self.checkin_col_input)

        # Team Column (only for doubleup)
        if current_mode == "doubleup":
            self.team_col_input = discord.ui.TextInput(
                label="Team Name Column",
                placeholder="Column letter (e.g., I)",
                default=settings.get("team_col", "I"),
                required=True,
                max_length=3
            )
            self.add_item(self.team_col_input)

    async def on_submit(self, interaction: discord.Interaction):
        columns = {
            "discord_col": self.discord_col_input.value.strip().upper(),
            "ign_col": self.ign_col_input.value.strip().upper(),
            "registered_col": self.registered_col_input.value.strip().upper(),
            "checkin_col": self.checkin_col_input.value.strip().upper()
        }

        if self.mode == "doubleup":
            columns["team_col"] = self.team_col_input.value.strip().upper()

        await handle_config_update(
            interaction,
            self,
            update_type="columns",
            updates=columns
        )


class SheetConfigModal(discord.ui.Modal):
    """Modal for editing sheet URLs."""

    def __init__(self, current_mode: str = "normal"):
        super().__init__(title=f"Edit Sheet URLs ({current_mode})")
        self.mode = current_mode

        # Get current settings
        settings = get_sheet_settings(current_mode)

        # Mode selector (to edit URLs for different modes)
        self.mode_select = discord.ui.TextInput(
            label="Mode to Edit",
            placeholder="'normal' or 'doubleup'",
            default=current_mode,
            required=True,
            min_length=6,
            max_length=10
        )
        self.add_item(self.mode_select)

        # Production URL
        prod_url = settings.get("sheet_url_prod", settings.get("sheet_url", ""))
        self.prod_url_input = discord.ui.TextInput(
            label="Production Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/.../edit",
            default=prod_url,
            required=True,
            style=discord.TextStyle.long
        )
        self.add_item(self.prod_url_input)

        # Development URL
        dev_url = settings.get("sheet_url_dev", settings.get("sheet_url", ""))
        self.dev_url_input = discord.ui.TextInput(
            label="Development Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/.../edit",
            default=dev_url,
            required=True,
            style=discord.TextStyle.long
        )
        self.add_item(self.dev_url_input)

        # Pronouns Column (bonus field since we have room)
        self.pronouns_col_input = discord.ui.TextInput(
            label="Pronouns Column (optional)",
            placeholder="Column letter (e.g., C)",
            default=settings.get("pronouns_col", "C"),
            required=False,
            max_length=3
        )
        self.add_item(self.pronouns_col_input)

        # Alt IGN Column (bonus field)
        self.alt_ign_col_input = discord.ui.TextInput(
            label="Alternative IGN Column (optional)",
            placeholder="Column letter (e.g., E)",
            default=settings.get("alt_ign_col", "E"),
            required=False,
            max_length=3
        )
        self.add_item(self.alt_ign_col_input)

    async def on_submit(self, interaction: discord.Interaction):
        mode_to_edit = self.mode_select.value.strip().lower()

        updates = {
            "mode": mode_to_edit,
            "sheet_url_prod": self.prod_url_input.value.strip(),
            "sheet_url_dev": self.dev_url_input.value.strip()
        }

        if self.pronouns_col_input.value:
            updates["pronouns_col"] = self.pronouns_col_input.value.strip().upper()

        if self.alt_ign_col_input.value:
            updates["alt_ign_col"] = self.alt_ign_col_input.value.strip().upper()

        await handle_config_update(
            interaction,
            self,
            update_type="sheets",
            updates=updates
        )


class ConfigRevertView(discord.ui.View):
    """View for reverting configuration changes."""

    def __init__(self, backup_name: str = "config_backup_latest.yaml"):
        super().__init__(timeout=None)  # Persistent view
        self.backup_name = backup_name

    @discord.ui.button(label="🔄 Revert to Backup", style=discord.ButtonStyle.danger, custom_id="revert_config")
    async def revert_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Revert configuration to backup."""
        # Check permissions
        from helpers import RoleManager
        if not RoleManager.has_allowed_role_from_interaction(interaction):
            await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            import shutil
            import os

            # Check if backup exists
            if not os.path.exists(self.backup_name):
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Backup Not Found",
                        description=f"No backup file `{self.backup_name}` found.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return

            # Revert the config
            shutil.copy(self.backup_name, "config.yaml")

            # Reload configuration
            from helpers import ConfigManager
            results = await ConfigManager.reload_and_update_all(interaction.client)

            if results["config_reload"]:
                embed = discord.Embed(
                    title="✅ Configuration Reverted",
                    description=f"Configuration has been reverted to the backup.",
                    color=discord.Color.green()
                )

                # Remove the view from this message
                await interaction.message.edit(view=None)

                await interaction.followup.send(embed=embed, ephemeral=True)

                # Log the revert (without a new revert button)
                log_embed = discord.Embed(
                    title="🔄 Configuration Reverted",
                    description=f"Configuration was reverted by {interaction.user.mention}",
                    color=discord.Color.orange(),
                    timestamp=datetime.now(timezone.utc)
                )
                await interaction.channel.send(embed=log_embed)

                # Clear any other old config views in the channel
                await clear_old_config_views(interaction.channel)
            else:
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Revert Failed",
                        description="Failed to reload configuration after revert.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Revert Error",
                    description=f"Error reverting configuration:\n```{str(e)[:200]}```",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


async def clear_old_config_views(log_channel: discord.TextChannel):
    """Remove revert buttons from old configuration messages."""
    try:
        # Look through recent messages for config update messages
        async for message in log_channel.history(limit=50):
            if message.author.bot and message.embeds:
                embed = message.embeds[0]
                # Check if it's a config update/upload message
                if embed.title and ("Configuration Updated" in embed.title or
                                    "Configuration Uploaded" in embed.title or
                                    "Configuration Reverted" in embed.title):
                    # If message has components (buttons), remove them
                    if message.components:
                        try:
                            await message.edit(view=None)
                            logging.debug(f"Removed view from old config message {message.id}")
                        except discord.HTTPException as e:
                            logging.debug(f"Could not edit message {message.id}: {e}")
    except Exception as e:
        logging.warning(f"Error clearing old config views: {e}")


async def handle_config_update(interaction: discord.Interaction, modal, update_type: str, updates: dict):
    """Shared handler for all config modal updates with backup/restore."""
    from datetime import datetime, timezone
    import shutil
    import os
    import glob

    # Use ruamel.yaml for round-trip preservation
    try:
        from ruamel.yaml import YAML
        yaml_handler = YAML()
        yaml_handler.preserve_quotes = True
        yaml_handler.width = 4096  # Prevent line wrapping
    except ImportError:
        # Fallback to regular yaml if ruamel not available
        import yaml as yaml_fallback
        yaml_handler = None

    # Clean up old timestamped backups first (one-time cleanup)
    try:
        old_backups = glob.glob("config_backup_*.yaml")
        for old_backup in old_backups:
            if not old_backup.endswith("_latest.yaml"):
                try:
                    os.remove(old_backup)
                    logging.debug(f"Removed old backup: {old_backup}")
                except:
                    pass
    except:
        pass

    # Use a single latest backup file
    backup_name = "config_backup_latest.yaml"

    try:
        shutil.copy("config.yaml", backup_name)
        logging.debug(f"Created backup: {backup_name}")
    except Exception as e:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Backup Failed",
                description=f"Could not create backup: {str(e)}",
                color=discord.Color.red()
            ),
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        # Load current config preserving formatting
        if yaml_handler:
            with open("config.yaml", "r", encoding="utf-8") as f:
                full_config = yaml_handler.load(f)
        else:
            with open("config.yaml", "r", encoding="utf-8") as f:
                full_config = yaml_fallback.safe_load(f)

        guild_id = str(interaction.guild.id)
        current_mode = get_event_mode_for_guild(guild_id)
        changes = []

        if update_type == "general":
            # Validate and update general settings
            new_mode = updates["mode"]
            if new_mode not in ["normal", "doubleup"]:
                raise ValueError(f"Invalid mode: {new_mode}")

            max_players = int(updates["max_players"])
            header_line = int(updates["header_line"])
            cache_refresh = int(updates["cache_refresh"])

            if not (1 <= max_players <= 9999):
                raise ValueError("Max players must be between 1 and 9999")
            if header_line < 1:
                raise ValueError("Header line must be at least 1")
            if not (60 <= cache_refresh <= 86400):
                raise ValueError("Cache refresh must be between 60 and 86400 seconds")

            # Update config
            config_section = full_config["sheet_configuration"][new_mode]
            config_section["max_players"] = max_players
            config_section["header_line_num"] = header_line

            # Update cache refresh at root level
            full_config["cache_refresh_seconds"] = cache_refresh

            # Update bot status
            if updates["bot_status"]:
                if "rich_presence" not in full_config:
                    full_config["rich_presence"] = {}
                full_config["rich_presence"]["message"] = updates["bot_status"]

            # Update mode if changed
            if new_mode != current_mode:
                set_event_mode_for_guild(guild_id, new_mode)
                changes.append(f"Mode: {current_mode} → {new_mode}")

            changes.extend([
                f"Max Players: {max_players}",
                f"Header Line: {header_line}",
                f"Cache Refresh: {cache_refresh}s"
            ])

            if updates["bot_status"]:
                changes.append(f"Bot Status: {updates['bot_status']}")

            # Update in-memory config
            from config import SHEET_CONFIG, _FULL_CFG
            SHEET_CONFIG[new_mode]["max_players"] = max_players
            SHEET_CONFIG[new_mode]["header_line_num"] = header_line
            _FULL_CFG["cache_refresh_seconds"] = cache_refresh

        elif update_type == "columns":
            # Validate and update column mappings
            mode = getattr(modal, 'mode', current_mode)

            for col_name, col_value in updates.items():
                if not col_value or not all(c.isalpha() for c in col_value):
                    raise ValueError(f"Invalid column {col_name}: '{col_value}' - must be letters only")

            # Update config
            config_section = full_config["sheet_configuration"][mode]
            for col_name, col_value in updates.items():
                config_section[col_name] = col_value
                from config import SHEET_CONFIG
                SHEET_CONFIG[mode][col_name] = col_value

            changes.append(f"Updated {mode} mode columns:")
            for col_name, col_value in updates.items():
                readable_name = col_name.replace("_", " ").title()
                changes.append(f"  • {readable_name}: {col_value}")

        elif update_type == "sheets":
            # Validate and update sheet URLs
            mode_to_edit = updates.get("mode", current_mode)
            if mode_to_edit not in ["normal", "doubleup"]:
                raise ValueError(f"Invalid mode: {mode_to_edit}")

            # Validate URLs
            for url in [updates["sheet_url_prod"], updates["sheet_url_dev"]]:
                if not url.startswith("https://docs.google.com/spreadsheets/"):
                    raise ValueError("Invalid Google Sheets URL format")

            # Update config
            config_section = full_config["sheet_configuration"][mode_to_edit]
            config_section["sheet_url_prod"] = updates["sheet_url_prod"]
            config_section["sheet_url_dev"] = updates["sheet_url_dev"]

            if "pronouns_col" in updates:
                config_section["pronouns_col"] = updates["pronouns_col"]
            if "alt_ign_col" in updates:
                config_section["alt_ign_col"] = updates["alt_ign_col"]

            # Update in-memory
            from config import SHEET_CONFIG
            SHEET_CONFIG[mode_to_edit]["sheet_url_prod"] = updates["sheet_url_prod"]
            SHEET_CONFIG[mode_to_edit]["sheet_url_dev"] = updates["sheet_url_dev"]

            if "pronouns_col" in updates:
                SHEET_CONFIG[mode_to_edit]["pronouns_col"] = updates["pronouns_col"]
            if "alt_ign_col" in updates:
                SHEET_CONFIG[mode_to_edit]["alt_ign_col"] = updates["alt_ign_col"]

            changes.append(f"Updated {mode_to_edit} mode sheet URLs")
            if "pronouns_col" in updates:
                changes.append(f"Pronouns Column: {updates['pronouns_col']}")
            if "alt_ign_col" in updates:
                changes.append(f"Alt IGN Column: {updates['alt_ign_col']}")

        # Save updated config with formatting preserved
        if yaml_handler:
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml_handler.dump(full_config, f)
        else:
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml_fallback.dump(full_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Try to reload
        try:
            from helpers import ConfigManager
            results = await ConfigManager.reload_and_update_all(interaction.client)

            # Refresh cache if columns or sheets changed
            if update_type in ["columns", "sheets"]:
                from integrations.sheets import refresh_sheet_cache
                await refresh_sheet_cache(bot=interaction.client)

            # Success message
            embed = discord.Embed(
                title="✅ Configuration Updated",
                description=f"Settings have been updated successfully!",
                color=discord.Color.green()
            )

            embed.add_field(
                name="Changes Applied",
                value="\n".join(changes) if changes else "No changes detected",
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

            # Log changes with revert button
            from config import LOG_CHANNEL_NAME
            log_channel = discord.utils.get(interaction.guild.text_channels, name=LOG_CHANNEL_NAME)
            if log_channel:
                # Clear old revert buttons first
                await clear_old_config_views(log_channel)

                log_embed = discord.Embed(
                    title=f"⚙️ Configuration Updated ({update_type.title()})",
                    description=f"Updated by {interaction.user.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc)
                )

                # Add revert view to new message
                revert_view = ConfigRevertView(backup_name)
                await log_channel.send(embed=log_embed, view=revert_view)

        except Exception as reload_error:
            # Restore backup
            shutil.copy(backup_name, "config.yaml")
            from helpers import ConfigManager
            await ConfigManager.reload_and_update_all(interaction.client)
            raise ValueError(f"Invalid configuration, reverted: {str(reload_error)}")

    except Exception as e:
        # Restore from backup on any error
        try:
            import shutil
            shutil.copy(backup_name, "config.yaml")
            from helpers import ConfigManager
            await ConfigManager.reload_and_update_all(interaction.client)
            error_msg = f"❌ Error: {str(e)[:200]}\n\n✅ Configuration restored from backup"
        except:
            error_msg = f"❌ Error: {str(e)[:200]}\n\n📁 Manual restore needed from backup"

        await interaction.followup.send(
            embed=discord.Embed(
                title="⚠️ Configuration Reverted",
                description=error_msg,
                color=discord.Color.orange()
            ),
            ephemeral=True
        )


@gal.command(name="help", description="Shows this help message.")
async def help_cmd(interaction: discord.Interaction):
    """Display help information."""
    try:
        from config import EMBEDS_CFG, GAL_COMMAND_IDS

        cfg = EMBEDS_CFG.get("help", {})
        help_embed = discord.Embed(
            title=cfg.get("title", "GAL Bot Help"),
            description=cfg.get("description", "Here are all the available commands:"),
            color=discord.Color.blurple()
        )

        cmd_descs = ConfigManager.get_command_help()
        for cmd_name, cmd_id in GAL_COMMAND_IDS.items():
            desc = cmd_descs.get(cmd_name, "No description available")
            clickable = f"</gal {cmd_name}:{cmd_id}>"
            help_embed.add_field(
                name=clickable,
                value=desc,
                inline=False
            )

        # Add footer with additional info
        help_embed.set_footer(
            text="All commands are restricted to staff members."
        )

        await interaction.response.send_message(embed=help_embed, ephemeral=True)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Help Command")


# Error handlers for the command group
@toggle.error
@event.error
@registeredlist.error
@reminder.error
@cache.error
@config_cmd.error
@help_cmd.error
async def command_error_handler(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for all GAL commands."""
    try:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )
        else:
            # Let the ErrorHandler deal with other errors
            await ErrorHandler.handle_command_error(interaction, error)

    except Exception as handler_error:
        logging.error(f"Error in command error handler: {handler_error}")
        # Fallback error message
        try:
            fallback_embed = discord.Embed(
                title="❌ Command Error",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red()
            )

            if interaction.response.is_done():
                await interaction.followup.send(embed=fallback_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=fallback_embed, ephemeral=True)
        except:
            pass  # Give up if we can't even send a fallback


async def handle_toggle_pings(guild: discord.Guild, system_value: str, reg_open: bool, ci_open: bool):
    """
    Handle ping notifications when registration or check-in is opened.
    
    Args:
        guild: The Discord guild
        system_value: The system being toggled ("registration", "checkin", or "both")
        reg_open: Whether registration is currently open
        ci_open: Whether check-in is currently open
    """
    try:
        # Get the unified channel
        channel_name = get_unified_channel_name()
        unified_channel = discord.utils.get(guild.text_channels, name=channel_name)
        
        if not unified_channel:
            logging.warning(f"Unified channel '{channel_name}' not found in guild {guild.name}")
            return
        
        # Get role names from config
        from config import _FULL_CFG
        roles_config = _FULL_CFG.get("roles", {})
        angel_role_name = roles_config.get("angel_role", "Angels")
        registered_role_name = roles_config.get("registered_role", "Registered")
        
        messages_to_delete = []
        
        # Handle registration ping (ping Angels when registration opens)
        if (system_value in ["registration", "both"]) and reg_open:
            angel_role = discord.utils.get(guild.roles, name=angel_role_name)
            if angel_role:
                ping_msg = await unified_channel.send(f"🎫 **Registration is now OPEN!** {angel_role.mention}")
                messages_to_delete.append(ping_msg)
            else:
                logging.warning(f"Angel role '{angel_role_name}' not found in guild {guild.name}")
        
        # Handle check-in ping (ping Registered role when check-in opens)
        if (system_value in ["checkin", "both"]) and ci_open:
            registered_role = discord.utils.get(guild.roles, name=registered_role_name)
            if registered_role:
                ping_msg = await unified_channel.send(f"✅ **Check-in is now OPEN!** {registered_role.mention}")
                messages_to_delete.append(ping_msg)
            else:
                logging.warning(f"Registered role '{registered_role_name}' not found in guild {guild.name}")
        
        # Delete ping messages after 5 seconds
        if messages_to_delete:
            import asyncio
            await asyncio.sleep(5)
            for msg in messages_to_delete:
                try:
                    await msg.delete()
                except discord.NotFound:
                    pass  # Message already deleted
                except discord.Forbidden:
                    logging.warning(f"Missing permissions to delete ping message in {guild.name}")
                except Exception as e:
                    logging.error(f"Error deleting ping message: {e}")
                    
    except Exception as e:
        logging.error(f"Error handling toggle pings for guild {guild.name}: {e}")


# Setup function for the commands module
async def setup(bot: commands.Bot):
    """Setup function to add the command group to the bot."""
    try:
        bot.tree.add_command(gal)
        logging.info("GAL command group added to bot tree")
    except Exception as e:
        logging.error(f"Failed to setup GAL commands: {e}")
        raise


# Health check function
def validate_commands_setup() -> Dict[str, Any]:
    """Validate that commands are properly configured."""
    issues = []

    # Check that all commands have descriptions
    for command in gal.commands:
        if not command.description:
            issues.append(f"Command '{command.name}' missing description")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "total_commands": len(gal.commands)
    }


# Validate setup
try:
    validation = validate_commands_setup()
    if validation["valid"]:
        logging.info(f"Commands setup validated: {validation['total_commands']} commands configured")
    else:
        logging.warning(f"Command setup issues: {validation['issues']}")
except Exception as e:
    logging.error(f"Failed to validate commands setup: {e}")

# Export the command group
__all__ = ['gal', 'setup', 'CommandError']
