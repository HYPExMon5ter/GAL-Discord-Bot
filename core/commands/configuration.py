"""Configuration management commands."""

from __future__ import annotations

import glob
import os
import shutil
from typing import Optional

import discord
from discord import app_commands

from config import (
    _FULL_CFG,
    SHEET_CONFIG,
    embed_from_cfg,
    get_log_channel_name,
    get_sheet_settings,
    get_unified_channel_name,
)
from core.config_ui import ColumnMappingView, SettingsView
from core.persistence import get_event_mode_for_guild
from helpers.environment_helpers import EnvironmentHelper

from .common import command_tracer, ensure_staff, handle_command_exception, logger


def register(gal: app_commands.Group) -> None:

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
    @command_tracer("gal.config")
    async def config_cmd(
            interaction: discord.Interaction,
            action: app_commands.Choice[str],
            file: Optional[discord.Attachment] = None
    ):
        """Manage bot configuration."""
        if not await ensure_staff(interaction, context="Config Command"):
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
                is_production = EnvironmentHelper.is_production()
                environment = EnvironmentHelper.get_environment_type()
    
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
    
                # Send with the new configuration menu view
                view = NewConfigMenuView(current_mode, guild_id)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
                # Store message reference for timeout handling
                try:
                    view.message = await interaction.original_response()
                except (discord.NotFound, discord.HTTPException):
                    pass  # If we can't get the message reference, timeout handling will just fail gracefully
    
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
                                timestamp=discord.utils.utcnow()
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
                            description=f"The file contains invalid YAML syntax:\n```{str(e)[:150]}```",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                except Exception as e:
                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="❌ Upload Failed",
                            description=f"Failed to process the uploaded file:\n```{str(e)[:150]}```",
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
                    await refresh_sheet_cache(bot=interaction.client, force=True)
    
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
                            description=f"Error reloading configuration:\n```{str(e)[:150]}```",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
    
        except Exception as e:
            await handle_command_exception(interaction, e, "Config Command")
    
    

class NewConfigMenuView(discord.ui.View):
    """New configuration menu with modern UI components."""

    def __init__(self, current_mode: str, guild_id: str):
        super().__init__(timeout=300)  # 5 minute timeout
        self.current_mode = current_mode
        self.guild_id = guild_id

    async def on_timeout(self):
        """Disable all buttons when the view times out."""
        for item in self.children:
            item.disabled = True

        # Try to edit the message to show buttons as disabled
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=self)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass  # Message might be deleted or we don't have permissions

    @discord.ui.button(label="⚙️ General Settings", style=discord.ButtonStyle.primary, row=0)
    async def general_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit general bot settings using new UI."""
        settings_view = SettingsView(self.guild_id)
        await settings_view.respond_with_ui(interaction)

    @discord.ui.button(label="📊 Column Mappings", style=discord.ButtonStyle.primary, row=0)
    async def column_mappings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit sheet column mappings using new UI."""
        column_view = ColumnMappingView(self.guild_id)
        await column_view.respond_with_ui(interaction)

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
            await refresh_sheet_cache(bot=interaction.client, force=True)

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
                    description=f"Error reloading configuration:\n```{str(e)[:150]}```",
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

        is_production = EnvironmentHelper.is_production()
        environment = EnvironmentHelper.get_environment_type()

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

        # Bot Status Message (at the top)
        self.bot_status_input = discord.ui.TextInput(
            label="Bot Status Message",
            placeholder="Message shown in bot's Discord status",
            default=presence_cfg.get("message", "🛡️ TFT"),
            required=False,
            max_length=128
        )
        self.add_item(self.bot_status_input)

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


        # Alt IGN Column
        self.alt_ign_col_input = discord.ui.TextInput(
            label="Alternative IGN Column",
            placeholder="Column letter (e.g., E)",
            default=settings.get("alt_ign_col", "E"),
            required=False,
            max_length=3
        )
        self.add_item(self.alt_ign_col_input)

    async def on_submit(self, interaction: discord.Interaction):
        updates = {
            "bot_status": self.bot_status_input.value.strip(),
            "max_players": self.max_players_input.value,
            "header_line": self.header_line_input.value,
            "cache_refresh": self.cache_refresh_input.value
        }

        if self.alt_ign_col_input.value:
            updates["alt_ign_col"] = self.alt_ign_col_input.value.strip().upper()

        await handle_config_update(
            interaction,
            self,
            update_type="general",
            updates=updates
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

        # Pronouns Column (for both modes now)
        self.pronouns_col_input = discord.ui.TextInput(
            label="Pronouns Column",
            placeholder="Column letter (e.g., C)",
            default=settings.get("pronouns_col", "C"),
            required=False,
            max_length=3
        )
        self.add_item(self.pronouns_col_input)

    async def on_submit(self, interaction: discord.Interaction):
        columns = {
            "discord_col": self.discord_col_input.value.strip().upper(),
            "ign_col": self.ign_col_input.value.strip().upper(),
            "registered_col": self.registered_col_input.value.strip().upper(),
            "checkin_col": self.checkin_col_input.value.strip().upper()
        }

        if self.mode == "doubleup":
            columns["team_col"] = self.team_col_input.value.strip().upper()

        # Add pronouns column for both modes
        if hasattr(self, 'pronouns_col_input') and self.pronouns_col_input.value:
            columns["pronouns_col"] = self.pronouns_col_input.value.strip().upper()

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


        # Get settings for both modes
        from config import SHEET_CONFIG
        normal_settings = SHEET_CONFIG.get("normal", {})
        doubleup_settings = SHEET_CONFIG.get("doubleup", {})

        # Normal Mode - Production URL
        normal_prod_url = normal_settings.get("sheet_url_prod", normal_settings.get("sheet_url", ""))
        self.normal_prod_url_input = discord.ui.TextInput(
            label="Normal Mode - Production Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/.../edit",
            default=normal_prod_url,
            required=True,
            style=discord.TextStyle.long
        )
        self.add_item(self.normal_prod_url_input)

        # Normal Mode - Development URL
        normal_dev_url = normal_settings.get("sheet_url_dev", normal_settings.get("sheet_url", ""))
        self.normal_dev_url_input = discord.ui.TextInput(
            label="Normal Mode - Development Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/.../edit",
            default=normal_dev_url,
            required=True,
            style=discord.TextStyle.long
        )
        self.add_item(self.normal_dev_url_input)

        # Doubleup Mode - Production URL
        doubleup_prod_url = doubleup_settings.get("sheet_url_prod", doubleup_settings.get("sheet_url", ""))
        self.doubleup_prod_url_input = discord.ui.TextInput(
            label="Doubleup Mode - Production Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/.../edit",
            default=doubleup_prod_url,
            required=True,
            style=discord.TextStyle.long
        )
        self.add_item(self.doubleup_prod_url_input)

        # Doubleup Mode - Development URL
        doubleup_dev_url = doubleup_settings.get("sheet_url_dev", doubleup_settings.get("sheet_url", ""))
        self.doubleup_dev_url_input = discord.ui.TextInput(
            label="Doubleup Mode - Development Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/.../edit",
            default=doubleup_dev_url,
            required=True,
            style=discord.TextStyle.long
        )
        self.add_item(self.doubleup_dev_url_input)

    async def on_submit(self, interaction: discord.Interaction):
        updates = {
            "normal_prod_url": self.normal_prod_url_input.value.strip(),
            "normal_dev_url": self.normal_dev_url_input.value.strip(),
            "doubleup_prod_url": self.doubleup_prod_url_input.value.strip(),
            "doubleup_dev_url": self.doubleup_dev_url_input.value.strip()
        }

        await handle_config_update(
            interaction,
            self,
            update_type="sheets",
            updates=updates
        )


class ConfigRevertView(discord.ui.View):
    """View for reverting configuration changes."""

    def __init__(self, backup_name: str = "config_backup_latest.yaml"):
        super().__init__(timeout=3600)  # 1 hour timeout instead of persistent
        self.backup_name = backup_name

    async def on_timeout(self):
        """Disable the revert button when timed out."""
        for item in self.children:
            item.disabled = True

        try:
            # Try to edit the message to show the button as disabled
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=self)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

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
                    timestamp=discord.utils.utcnow()
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
                    description=f"Error reverting configuration:\n```{str(e)[:150]}```",
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
                            logger.debug(f"Removed view from old config message {message.id}")
                        except discord.HTTPException as e:
                            logger.debug(f"Could not edit message {message.id}: {e}")
    except Exception as e:
        logger.warning(f"Error clearing old config views: {e}")


async def handle_config_update(interaction: discord.Interaction, modal, update_type: str, updates: dict):
    """Shared handler for all config modal updates with backup/restore."""
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
                    logger.debug(f"Removed old backup: {old_backup}")
                except:
                    pass
    except:
        pass

    # Use a single latest backup file
    backup_name = "config_backup_latest.yaml"

    try:
        if not os.path.exists("config.yaml"):
            raise FileNotFoundError("config.yaml not found")
        shutil.copy("config.yaml", backup_name)
        logger.debug(f"Created backup: {backup_name}")
    except Exception as e:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Backup Failed",
                description=f"Could not create backup: {str(e)[:150]}",
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
            try:
                max_players = int(updates["max_players"])
            except ValueError:
                raise ValueError(f"Max players must be a number, got: '{updates['max_players']}'")

            try:
                header_line = int(updates["header_line"])
            except ValueError:
                raise ValueError(f"Header line must be a number, got: '{updates['header_line']}'")

            try:
                cache_refresh = int(updates["cache_refresh"])
            except ValueError:
                raise ValueError(f"Cache refresh must be a number, got: '{updates['cache_refresh']}'")

            if not (1 <= max_players <= 9999):
                raise ValueError("Max players must be between 1 and 9999")
            if header_line < 1:
                raise ValueError("Header line must be at least 1")
            if not (60 <= cache_refresh <= 86400):
                raise ValueError("Cache refresh must be between 60 and 86400 seconds")

            # Update config for current mode
            config_section = full_config["sheet_configuration"][current_mode]
            config_section["max_players"] = max_players
            config_section["header_line_num"] = header_line

            # Update cache refresh at root level
            full_config["cache_refresh_seconds"] = cache_refresh

            # Update bot status
            if updates["bot_status"]:
                if "rich_presence" not in full_config:
                    full_config["rich_presence"] = {}
                full_config["rich_presence"]["message"] = updates["bot_status"]

            # Handle optional column fields
            if "alt_ign_col" in updates:
                config_section["alt_ign_col"] = updates["alt_ign_col"]

            changes.extend([
                f"Max Players: {max_players}",
                f"Header Line: {header_line}",
                f"Cache Refresh: {cache_refresh}s"
            ])

            if updates["bot_status"]:
                changes.append(f"Bot Status: {updates['bot_status']}")

            if "alt_ign_col" in updates:
                changes.append(f"Alt IGN Column: {updates['alt_ign_col']}")

            # Update in-memory config
            from config import SHEET_CONFIG, _FULL_CFG
            SHEET_CONFIG[current_mode]["max_players"] = max_players
            SHEET_CONFIG[current_mode]["header_line_num"] = header_line
            _FULL_CFG["cache_refresh_seconds"] = cache_refresh

            if "alt_ign_col" in updates:
                SHEET_CONFIG[current_mode]["alt_ign_col"] = updates["alt_ign_col"]

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
            # Validate and update sheet URLs for all modes/environments
            # Validate URLs
            for url_key, url in updates.items():
                if not url.startswith("https://docs.google.com/spreadsheets/"):
                    raise ValueError(f"Invalid Google Sheets URL format for {url_key}")

            # Update config for both modes
            normal_config = full_config["sheet_configuration"]["normal"]
            doubleup_config = full_config["sheet_configuration"]["doubleup"]

            normal_config["sheet_url_prod"] = updates["normal_prod_url"]
            normal_config["sheet_url_dev"] = updates["normal_dev_url"]
            doubleup_config["sheet_url_prod"] = updates["doubleup_prod_url"]
            doubleup_config["sheet_url_dev"] = updates["doubleup_dev_url"]

            # Update in-memory
            from config import SHEET_CONFIG
            SHEET_CONFIG["normal"]["sheet_url_prod"] = updates["normal_prod_url"]
            SHEET_CONFIG["normal"]["sheet_url_dev"] = updates["normal_dev_url"]
            SHEET_CONFIG["doubleup"]["sheet_url_prod"] = updates["doubleup_prod_url"]
            SHEET_CONFIG["doubleup"]["sheet_url_dev"] = updates["doubleup_dev_url"]

            changes.extend([
                "Updated Normal Mode sheet URLs",
                "Updated Doubleup Mode sheet URLs"
            ])

        # Save updated config with formatting preserved (use temp file for atomicity)
        import tempfile
        temp_config_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as temp_f:
                temp_config_path = temp_f.name
                if yaml_handler:
                    yaml_handler.dump(full_config, temp_f)
                else:
                    yaml_fallback.dump(full_config, temp_f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            # Atomically replace the config file
            shutil.move(temp_config_path, "config.yaml")
            temp_config_path = None  # Successfully moved
        except Exception as e:
            # Clean up temp file if something went wrong
            if temp_config_path and os.path.exists(temp_config_path):
                try:
                    os.remove(temp_config_path)
                except:
                    pass
            raise e

        # Try to reload
        try:
            from helpers import ConfigManager
            results = await ConfigManager.reload_and_update_all(interaction.client)

            # Refresh cache if columns or sheets changed
            if update_type in ["columns", "sheets"]:
                from integrations.sheets import refresh_sheet_cache
                await refresh_sheet_cache(bot=interaction.client, force=True)

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
                    timestamp=discord.utils.utcnow()
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
            error_msg = f"❌ Error: {str(e)[:150]}\n\n✅ Configuration restored from backup"
        except:
            error_msg = f"❌ Error: {str(e)[:150]}\n\n📁 Manual restore needed from backup"

        await interaction.followup.send(
            embed=discord.Embed(
                title="⚠️ Configuration Reverted",
                description=error_msg,
                color=discord.Color.orange()
            ),
            ephemeral=True
        )


