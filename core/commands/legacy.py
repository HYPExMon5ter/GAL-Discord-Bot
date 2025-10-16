# core/commands.py

import logging
import os
import time
from typing import Optional, Dict, Any, List

import discord
import yaml
from discord import app_commands
from discord.ext import commands

from config import (
    embed_from_cfg, get_sheet_settings, _FULL_CFG, get_log_channel_name,
    get_unified_channel_name, get_registered_role, get_checked_in_role
)
from core.components_traditional import update_unified_channel
from core.config_ui import (
    ColumnMappingView, SettingsView
)
from core.persistence import (
    get_event_mode_for_guild, set_event_mode_for_guild
)
# Import all helpers
from helpers import (
    RoleManager, Validators,
    ErrorHandler, ConfigManager, EmbedHelper
)
from integrations.sheets import (
    refresh_sheet_cache
)


async def send_reminder_dms(
        client: discord.Client,
        guild: discord.Guild,
        dm_embed: discord.Embed,
        view_cls: type[discord.ui.View],
        skip_member_resolution: bool = False
    ) -> List[str]:
    """
    Send DM reminders to registered but not checked-in users.
    Clears previous DMs before sending new ones.
    """
    if not guild or not dm_embed or not view_cls:
        raise ValueError("Guild, embed, and view class are required")

    try:
        from integrations.sheets import sheet_cache, cache_lock

        dmmed: List[str] = []
        failed_dms = 0

        async with cache_lock:
            cache_snapshot = dict(sheet_cache["users"])

        for discord_tag, user_tuple in cache_snapshot.items():
            # Check if user is registered but not checked in
            if len(user_tuple) < 4:
                continue

            is_reg = str(user_tuple[2]).upper() == "TRUE"
            is_ci = str(user_tuple[3]).upper() == "TRUE"

            if is_reg and not is_ci:
                try:
                    member = await resolve_member(guild, discord_tag)
                    if member:
                        dm = await member.create_dm()
                        await dm.send(embed=dm_embed, view=view_cls)
                        dmmed.append(discord_tag)
                    else:
                        if not skip_member_resolution:
                            failed_dms += 1
                except discord.Forbidden:
                    if not skip_member_resolution:
                        failed_dms += 1
                except Exception as e:
                    if not skip_member_resolution:
                        failed_dms += 1
                    logging.error(f"Failed to DM {discord_tag}: {e}")

        # Send summary message
        if dmmed or failed_dms:
            summary_embed = discord.Embed(
                title="✅ Reminders Sent",
                description=f"Sent {len(dmmed)} reminders ({failed_dms} failed)",
                color=discord.Color.green()
            )
            channel = await get_log_channel_name(guild)
            if channel:
                await channel.send(embed=summary_embed)
            else:
                logging.warning("Could not find log channel for reminder summary")

        return dmmed

    except Exception as e:
        logging.error(f"Error sending reminder DMs: {e}")
        return []


async def clear_user_dms(member: discord.Member, bot_user: discord.User) -> int:
    """Clear all previous DMs sent by the bot to a user."""
    deleted_count = 0

    try:
        dm_channel = await member.create_dm()

        # Delete all bot messages in the DM channel
        async for message in dm_channel.history(limit=100):
            if message.author.id == bot_user.id:
                try:
                    await message.delete()
                    deleted_count += 1
                except discord.Forbidden:
                    # Can't delete this message, skip it
                    pass
                except discord.NotFound:
                    # Message already deleted
                    pass
                except Exception as e:
                    logging.warning(f"Failed to delete DM message: {e}")

    except discord.Forbidden:
        logging.debug(f"Cannot access DM channel for {member}")
    except Exception as e:
        logging.error(f"Error clearing DMs for {member}: {e}")

    return deleted_count


class CommandError(Exception):
    """Custom exception for command-related errors."""
    pass
    """Custom exception for command-related errors."""
    pass

async def resolve_member(guild: discord.Guild, discord_tag: str) -> discord.Member | None:
    """Resolve Discord member by tag or display name."""
    try:
        # Try exact display name matches
        member = discord.utils.get(guild.members, display_name=discord_tag)
        if member:
            return member

        # Try case-insensitive matches
        for member in guild.members:
            if (member.name.lower() == discord_tag.lower() or
                    member.display_name.lower() == discord_tag.lower()):
                return member

        logging.debug(f"Could not resolve member: {discord_tag} in guild {guild.name}")
        return None

    except Exception as e:
        logging.error(f"Error resolving member {discord_tag}: {e}")
        return None


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
        # Only ping for manual toggles, not scheduled events (to prevent duplicates)
        if not silent:
            await handle_toggle_pings(interaction.guild, system_value, reg_open, ci_open, is_manual=True)

        # Send feedback
        embed = discord.Embed(
            title="✅ System Toggled",
            description=status,
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Note: Removed log channel logging to reduce spam - ping notifications provide sufficient feedback

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
        await interaction.response.defer(ephemeral=True)
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
            await interaction.followup.send(embed=embed, ephemeral=True)
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
        if RoleManager.has_allowed_role_from_interaction(interaction):
            # Import the view from components_traditional
            from core.components_traditional import PlayerListView
            view = PlayerListView()
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

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
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild.id)

        # Get registered users who aren't checked in (same logic as ReminderButton)
        from helpers.sheet_helpers import SheetOperations
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

        # Send DMs using existing helper
        from core.views import WaitlistRegistrationDMView
        dm_embed = embed_from_cfg("reminder_dm")

        sent_dms = await send_reminder_dms(
            client=interaction.client,
            guild=interaction.guild,
            dm_embed=dm_embed,
            view_cls=WaitlistRegistrationDMView
        )
        sent_count = len(sent_dms)

        # Send single ephemeral confirmation with user mentions
        final_embed = discord.Embed(
            title="✅ Reminder Complete",
            description=f"Successfully sent DMs to **{sent_count}/{len(unchecked_users)}** users.",
            color=discord.Color.green()
        )

        if sent_count > 0:
            # Create list of user mentions for those who received DMs
            reminded_mentions = []
            for dm_info in sent_dms:
                # Extract discord_tag from the format "DisplayName (`discord_tag`)"
                # dm_info looks like "UserDisplayName (`user#1234`)"
                if "(`" in dm_info and "`)" in dm_info:
                    start = dm_info.find("(`") + 2
                    end = dm_info.find("`)")
                    discord_tag = dm_info[start:end]

                    # Find the member by discord tag to get their mention
                    for member in unchecked_users:
                        if str(member) == discord_tag:
                            reminded_mentions.append(member.mention)
                            break

            # Show up to 10 mentions, then summarize the rest
            if len(reminded_mentions) <= 10:
                mention_text = "\n".join(reminded_mentions)
            else:
                mention_text = "\n".join(reminded_mentions[:10])
                mention_text += f"\n... and {len(reminded_mentions) - 10} more"

            final_embed.add_field(
                name="Reminded Users",
                value=mention_text,
                inline=False
            )

        if sent_count < len(unchecked_users):
            final_embed.add_field(
                name="Note",
                value=f"{len(unchecked_users) - sent_count} user(s) could not be reached (DMs disabled)",
                inline=False
            )

        await interaction.followup.send(embed=final_embed, ephemeral=True)

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
                        description=f"Error reloading configuration:\n```{str(e)[:150]}```",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Config Command")


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
                            logging.debug(f"Removed view from old config message {message.id}")
                        except discord.HTTPException as e:
                            logging.debug(f"Could not edit message {message.id}: {e}")
    except Exception as e:
        logging.warning(f"Error clearing old config views: {e}")


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
                    logging.debug(f"Removed old backup: {old_backup}")
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
        logging.debug(f"Created backup: {backup_name}")
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


@gal.command(name="onboard", description="Manage the onboarding system.")
@app_commands.describe(
    action="Action to perform (setup, stats, refresh)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="setup", value="setup"),
    app_commands.Choice(name="stats", value="stats"),
    app_commands.Choice(name="refresh", value="refresh")
])
async def onboard_cmd(interaction: discord.Interaction, action: app_commands.Choice[str]):
    """Manage the onboarding system."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        action_value = action.value

        if action_value == "setup":
            # Set up onboard channels and embed
            from core.onboard import setup_onboard_channel

            await interaction.response.defer(ephemeral=True)

            success = await setup_onboard_channel(interaction.guild, interaction.client)

            if success:
                embed = discord.Embed(
                    title="✅ Onboard System Setup",
                    description="Onboard channels and embed have been set up successfully!",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
            else:
                embed = discord.Embed(
                    title="❌ Setup Failed",
                    description="Failed to set up onboard system. Check bot permissions and logs.",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        elif action_value == "stats":
            # Show onboarding statistics
            from helpers.onboard_helpers import OnboardManager
            from config import get_onboard_approval_role

            pending_submissions = OnboardManager.get_pending_submissions()
            pending_count = len(pending_submissions)

            # Count approved members (those with Angels role)
            approval_role_name = get_onboard_approval_role()
            approval_role = discord.utils.get(interaction.guild.roles, name=approval_role_name)
            approved_count = len(approval_role.members) if approval_role else 0

            embed = discord.Embed(
                title="📊 Onboarding Statistics",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="⏳ Pending Submissions",
                value=str(pending_count),
                inline=True
            )

            embed.add_field(
                name="✅ Approved Members",
                value=str(approved_count),
                inline=True
            )

            if pending_count > 0:
                pending_list = []
                for user_id, data in list(pending_submissions.items())[:5]:  # Show max 5
                    member = interaction.guild.get_member(user_id)
                    if member:
                        pending_list.append(f"• {member.mention}")
                    else:
                        pending_list.append(f"• <@{user_id}> (left server)")

                if len(pending_submissions) > 5:
                    pending_list.append(f"• ... and {len(pending_submissions) - 5} more")

                embed.add_field(
                    name="Recent Pending",
                    value="\n".join(pending_list) if pending_list else "None",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action_value == "refresh":
            # Refresh onboard embed and rebuild state
            from core.onboard import setup_onboard_channel
            from helpers.onboard_helpers import rebuild_pending_submissions_from_history
            from config import get_onboard_review_channel

            await interaction.response.defer(ephemeral=True)

            # Rebuild state from review channel
            review_channel_name = get_onboard_review_channel()
            review_channel = discord.utils.get(interaction.guild.text_channels, name=review_channel_name)

            if review_channel:
                await rebuild_pending_submissions_from_history(review_channel)

            # Refresh the setup
            success = await setup_onboard_channel(interaction.guild, interaction.client)

            embed = discord.Embed(
                title="🔄 Onboard System Refreshed",
                description="Onboard system has been refreshed and state rebuilt from message history.",
                color=discord.Color.green() if success else discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Onboard Command")


@gal.command(name="test", description="Test the new Discord components layout.")
async def test_cmd(interaction: discord.Interaction):
    """Test the new Discord components layout."""
    if not await Validators.validate_and_respond(
            interaction,
            Validators.validate_staff_permission(interaction)
    ):
        return

    try:
        from core.test_components import TestComponents

        view = TestComponents()
        await interaction.response.send_message(view=view, ephemeral=True)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Test Command")


@gal.command(name="placement", description="Get the latest TFT placement for a player.")
@app_commands.describe(
    riot_id="Riot ID to look up (format: GameName#TAG or just GameName)",
    region="Region (default: na)"
)
@app_commands.choices(region=[
    app_commands.Choice(name="North America (NA)", value="na"),
    app_commands.Choice(name="Europe West (EUW)", value="euw"),
    app_commands.Choice(name="Europe Nordic & East (EUNE)", value="eune"),
    app_commands.Choice(name="Korea (KR)", value="kr"),
    app_commands.Choice(name="Japan (JP)", value="jp"),
    app_commands.Choice(name="Oceania (OCE)", value="oce"),
    app_commands.Choice(name="Brazil (BR)", value="br"),
    app_commands.Choice(name="Latin America North (LAN)", value="lan"),
    app_commands.Choice(name="Latin America South (LAS)", value="las"),
    app_commands.Choice(name="Russia (RU)", value="ru"),
    app_commands.Choice(name="Turkey (TR)", value="tr")
])
async def placement_cmd(interaction: discord.Interaction, riot_id: str, region: Optional[app_commands.Choice[str]] = None):
    """Get latest TFT placement for a player using Riot ID."""
    try:
        await interaction.response.defer()

        # Default to NA if no region specified
        region_value = region.value if region else "na"

        # Import and use Riot API
        from integrations.riot_api import RiotAPI

        async with RiotAPI() as riot_api:
            result = await riot_api.get_latest_placement(region_value, riot_id)

        if result["success"]:
            # Create success embed
            embed = discord.Embed(
                title="🎮 TFT Latest Placement",
                color=discord.Color.gold() if result["placement"] <= 4 else discord.Color.blue()
            )

            # Add placement with emoji
            placement_emojis = {
                1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣",
                5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣"
            }
            placement_emoji = placement_emojis.get(result["placement"], f"{result['placement']}️⃣")

            embed.add_field(
                name="📊 Placement",
                value=f"{placement_emoji} **{result['placement']}** out of {result['total_players']} players",
                inline=False
            )

            embed.add_field(
                name="👤 Player",
                value=f"**{result['riot_id']}** (Level {result['level']})",
                inline=True
            )

            embed.add_field(
                name="🌍 Region",
                value=result["region"],
                inline=True
            )

            # Format game length (seconds to minutes:seconds)
            game_length_minutes = result["game_length"] // 60
            game_length_seconds = result["game_length"] % 60

            embed.add_field(
                name="⏱️ Game Length",
                value=f"{game_length_minutes}m {game_length_seconds}s",
                inline=True
            )

            # Add game version and match ID in footer
            embed.set_footer(
                text=f"Game Version: {result['game_version']} | Match ID: {result['match_id'][:8]}..."
            )

            # Add timestamp
            import datetime
            game_time = datetime.datetime.fromtimestamp(result["game_datetime"] / 1000, tz=datetime.timezone.utc)
            embed.timestamp = game_time

        else:
            # Create error embed
            embed = discord.Embed(
                title="❌ TFT Placement Lookup Failed",
                description=f"Could not retrieve placement data for **{result['riot_id']}** in **{result['region']}**",
                color=discord.Color.red()
            )

            embed.add_field(
                name="Error Details",
                value=result["error"],
                inline=False
            )

            # Add helpful tips based on error type
            if "not found" in result["error"].lower():
                embed.add_field(
                    name="💡 Tips",
                    value="• Check the Riot ID format (GameName#TAG)\n• Verify the region is correct\n• Ensure the player has recent TFT matches\n• Try including the full tag (e.g., Player#NA1)",
                    inline=False
                )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await ErrorHandler.handle_interaction_error(interaction, e, "Placement Command")



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


# Enhanced error handlers using Discord.py v2 features
@toggle.error
@event.error
@registeredlist.error
@reminder.error
@cache.error
@config_cmd.error
@onboard_cmd.error
@test_cmd.error
@placement_cmd.error
@help_cmd.error
async def command_error_handler(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Enhanced global error handler for all GAL commands using Discord.py v2 features."""
    try:
        # Handle specific Discord.py v2 error types
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=embed_from_cfg("permission_denied"),
                ephemeral=True
            )
        elif isinstance(error, app_commands.CommandSignatureMismatch):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Command Signature Error",
                    description="There was an issue with the command parameters. Please try again.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
        elif isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Parameter Error",
                    description=f"Invalid parameter: {str(error)}",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="⏰ Command Cooldown",
                    description=f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                    color=discord.Color.orange()
                ),
                ephemeral=True
            )
        else:
            # Let the ErrorHandler deal with other errors
            await ErrorHandler.handle_command_error(interaction, error)

    except Exception as handler_error:
        logging.error(f"Error in command error handler: {handler_error}")
        # Enhanced fallback error message
        try:
            fallback_embed = discord.Embed(
                title="❌ Unexpected Error",
                description="An unexpected error occurred. Please try again later or contact support.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            fallback_embed.set_footer(text="Error ID available in logs")

            if interaction.response.is_done():
                await interaction.followup.send(embed=fallback_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=fallback_embed, ephemeral=True)
        except:
            pass  # Give up if we can't even send a fallback


async def handle_toggle_pings(guild: discord.Guild, system_value: str, reg_open: bool, ci_open: bool,
                              is_manual: bool = False):
    """
    Handle ping notifications when registration or check-in is opened.

    Args:
        guild: The Discord guild
        system_value: The system being toggled ("registration", "checkin", or "both")
        reg_open: Whether registration is currently open
        ci_open: Whether check-in is currently open
        is_manual: Whether this is a manual toggle (vs scheduled event)
    """
    try:
        # Import the recent_pings tracker from events.py to prevent duplicates
        from core.events import recent_pings

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

        # Check spam prevention (same as in events.py)
        now_timestamp = discord.utils.utcnow().timestamp()
        last_ping = recent_pings.get(guild.id, 0)
        if now_timestamp - last_ping < 30:
            logging.info(f"Skipping ping for {system_value} in {guild.name} - recently pinged (within 30s)")
            return

        messages_to_delete = []
        ping_sent = False

        # Handle registration ping (ping Angels when registration opens)
        if (system_value in ["registration", "both"]) and reg_open:
            if roles_config.get("ping_on_registration_open", True):
                angel_role = discord.utils.get(guild.roles, name=angel_role_name)
                if angel_role:
                    ping_msg = await unified_channel.send(f"🎫 **Registration is now OPEN!** {angel_role.mention}")
                    messages_to_delete.append(ping_msg)
                    ping_sent = True
                else:
                    logging.warning(f"Angel role '{angel_role_name}' not found in guild {guild.name}")

        # Handle check-in ping (ping Registered role when check-in opens)
        if (system_value in ["checkin", "both"]) and ci_open:
            if roles_config.get("ping_on_checkin_open", True):
                registered_role = discord.utils.get(guild.roles, name=registered_role_name)
                if registered_role:
                    ping_msg = await unified_channel.send(f"✅ **Check-in is now OPEN!** {registered_role.mention}")
                    messages_to_delete.append(ping_msg)
                    ping_sent = True
                else:
                    logging.warning(f"Registered role '{registered_role_name}' not found in guild {guild.name}")

        # Update last ping time if we sent a ping
        if ping_sent:
            recent_pings[guild.id] = now_timestamp

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
        # Check if command already exists to prevent duplicates
        existing_commands = [cmd.name for cmd in bot.tree.get_commands()]
        if "gal" in existing_commands:
            logging.warning("GAL command already exists in tree - skipping add")
            return

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
