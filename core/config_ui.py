# core/config_ui.py

import logging
from typing import Optional, Dict, Any, List
import discord
from discord import ui, TextInput, ButtonStyle, SeparatorSpacing
from discord.ext import commands
import gspread.exceptions

from config import embed_from_cfg, get_sheet_settings, _FULL_CFG
from integrations.sheet_detector import (
    detect_sheet_columns, get_column_mapping, save_column_mapping,
    SheetColumnDetector, ColumnMapping
)
from core.persistence import get_guild_data, update_guild_data, get_event_mode_for_guild




class ColumnMappingView(ui.LayoutView):
    """
    Configuration UI for Google Sheet column mappings using containers.
    """

    def __init__(self, guild_id: str):
        super().__init__(timeout=300)  # 5 minute timeout
        self.guild_id = guild_id
        self.detections = {}
        self.current_mapping = None
        self.detector = SheetColumnDetector()

        # Add placeholder items that will be updated after initialization
        self.add_container_items()

    async def initialize(self):
        """
        Initialize the view with current detections and mappings.
        """
        self.detections = await detect_sheet_columns(self.guild_id)
        self.current_mapping = await get_column_mapping(self.guild_id)

        logging.info(f"[CONFIG_UI] Initialized for guild {self.guild_id}")
        logging.info(f"[CONFIG_UI] Detections: {list(self.detections.keys())}")
        if self.current_mapping:
            logging.info(f"[CONFIG_UI] Current mapping: discord={self.current_mapping.discord_column}, ign={self.current_mapping.ign_column}, registered={self.current_mapping.registered_column}")
        else:
            logging.warning("[CONFIG_UI] No current mapping found!")

        # Update button labels with actual column status
        self.update_button_labels()

    def update_button_labels(self):
        """Update button labels with current column status."""
        # Find and update Discord button
        for item in self.children:
            if isinstance(item, ui.ActionRow):
                for button in item.children:
                    if button.custom_id == "update_discord":
                        status = self._get_column_status('discord')
                        button.label = f"Discord: {status}"
                    elif button.custom_id == "update_ign":
                        status = self._get_column_status('ign')
                        button.label = f"IGN: {status}"
                    elif button.custom_id == "update_alt_ign":
                        status = self._get_column_status('alt_ign')
                        button.label = f"Alt IGN: {status}"
                    elif button.custom_id == "update_pronouns":
                        status = self._get_column_status('pronouns')
                        button.label = f"Pronouns: {status}"
                    elif button.custom_id == "update_registered":
                        status = self._get_column_status('registered')
                        button.label = f"Registered: {status}"
                    elif button.custom_id == "update_checkin":
                        status = self._get_column_status('checkin')
                        button.label = f"Checkin: {status}"
                    elif button.custom_id == "update_team":
                        status = self._get_column_status('team')
                        button.label = f"Team: {status}"

    def add_container_items(self):
        """Add individual container items to the view."""
        # Discord container with update/remove buttons (placeholder values)
        self.add_item(ui.ActionRow(
            ui.Button(label="Discord: Loading...", style=discord.ButtonStyle.primary, custom_id="update_discord", emoji="🔄"),
            ui.Button(label="Remove", style=discord.ButtonStyle.danger, custom_id="remove_discord", emoji="🗑️")
        ))

        # IGN container with update/remove buttons (placeholder values)
        self.add_item(ui.ActionRow(
            ui.Button(label="IGN: Loading...", style=discord.ButtonStyle.primary, custom_id="update_ign", emoji="🔄"),
            ui.Button(label="Remove", style=discord.ButtonStyle.danger, custom_id="remove_ign", emoji="🗑️")
        ))

        # Alt IGN container with update/remove buttons (placeholder values)
        self.add_item(ui.ActionRow(
            ui.Button(label="Alt IGN: Loading...", style=discord.ButtonStyle.primary, custom_id="update_alt_ign", emoji="🔄"),
            ui.Button(label="Remove", style=discord.ButtonStyle.danger, custom_id="remove_alt_ign", emoji="🗑️")
        ))

        # Pronouns container with update/remove buttons (placeholder values)
        self.add_item(ui.ActionRow(
            ui.Button(label="Pronouns: Loading...", style=discord.ButtonStyle.primary, custom_id="update_pronouns", emoji="🔄"),
            ui.Button(label="Remove", style=discord.ButtonStyle.danger, custom_id="remove_pronouns", emoji="🗑️")
        ))

        # Registered container with update/remove buttons (placeholder values)
        self.add_item(ui.ActionRow(
            ui.Button(label="Registered: Loading...", style=discord.ButtonStyle.primary, custom_id="update_registered", emoji="🔄"),
            ui.Button(label="Remove", style=discord.ButtonStyle.danger, custom_id="remove_registered", emoji="🗑️")
        ))

        # Checkin container with update/remove buttons (placeholder values)
        self.add_item(ui.ActionRow(
            ui.Button(label="Checkin: Loading...", style=discord.ButtonStyle.primary, custom_id="update_checkin", emoji="🔄"),
            ui.Button(label="Remove", style=discord.ButtonStyle.danger, custom_id="remove_checkin", emoji="🗑️")
        ))

        # Team container (only for doubleup mode) - placeholder
        mode = get_event_mode_for_guild(self.guild_id)
        if mode == "doubleup":
            self.add_item(ui.ActionRow(
                ui.Button(label="Team: Loading...", style=discord.ButtonStyle.primary, custom_id="update_team", emoji="🔄"),
                ui.Button(label="Remove", style=discord.ButtonStyle.danger, custom_id="remove_team", emoji="🗑️")
            ))

        # Action buttons
        self.add_item(ui.ActionRow(
            ui.Button(label="Detect Columns", style=discord.ButtonStyle.secondary, custom_id="detect", emoji="🔍"),
            ui.Button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel", emoji="❌")
        ))

    @ui.button(custom_id="update_discord")
    async def update_discord_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Discord column update."""
        modal = ColumnUpdateModal(self, "discord")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="remove_discord")
    async def remove_discord_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Discord column removal."""
        modal = ColumnRemoveConfirmModal(self, "discord")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="update_ign")
    async def update_ign_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle IGN column update."""
        modal = ColumnUpdateModal(self, "ign")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="remove_ign")
    async def remove_ign_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle IGN column removal."""
        modal = ColumnRemoveConfirmModal(self, "ign")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="update_alt_ign")
    async def update_alt_ign_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Alt IGN column update."""
        modal = ColumnUpdateModal(self, "alt_ign")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="remove_alt_ign")
    async def remove_alt_ign_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Alt IGN column removal."""
        modal = ColumnRemoveConfirmModal(self, "alt_ign")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="update_pronouns")
    async def update_pronouns_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Pronouns column update."""
        modal = ColumnUpdateModal(self, "pronouns")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="remove_pronouns")
    async def remove_pronouns_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Pronouns column removal."""
        modal = ColumnRemoveConfirmModal(self, "pronouns")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="update_registered")
    async def update_registered_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Registered column update."""
        modal = ColumnUpdateModal(self, "registered")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="remove_registered")
    async def remove_registered_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Registered column removal."""
        modal = ColumnRemoveConfirmModal(self, "registered")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="update_checkin")
    async def update_checkin_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Checkin column update."""
        modal = ColumnUpdateModal(self, "checkin")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="remove_checkin")
    async def remove_checkin_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Checkin column removal."""
        modal = ColumnRemoveConfirmModal(self, "checkin")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="update_team")
    async def update_team_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Team column update."""
        modal = ColumnUpdateModal(self, "team")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="remove_team")
    async def remove_team_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Team column removal."""
        modal = ColumnRemoveConfirmModal(self, "team")
        await interaction.response.send_modal(modal)

    @ui.button(custom_id="detect")
    async def detect_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle column detection."""
        await interaction.response.defer(ephemeral=True)
        try:
            # Force refresh detection
            self.detections = await detect_sheet_columns(self.guild_id, force_refresh=True)
            await self.initialize()

            embed = self.create_embed()
            await interaction.followup.send(embed=embed, view=self, ephemeral=True)
        except discord.errors.Forbidden:
            logging.error(f"[CONFIG_UI] Permission denied during column detection")
            await interaction.followup.send(
                content="❌ I don't have permission to access the Google Sheet. Please check sheet permissions.",
                ephemeral=True
            )
        except gspread.exceptions.GSpreadException as gs_error:
            logging.error(f"[CONFIG_UI] Google Sheets API error during detection: {gs_error}")
            await interaction.followup.send(
                content="❌ Google Sheets API error. Please check the sheet URL and permissions.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"[CONFIG_UI] Detection failed: {e}")
            error_message = str(e)
            if "timeout" in error_message.lower():
                await interaction.followup.send(
                    content="❌ Detection timed out. The Google Sheet might be too large or unavailable. Please try again.",
                    ephemeral=True
                )
            elif "not found" in error_message.lower() or "404" in error_message:
                await interaction.followup.send(
                    content="❌ Google Sheet not found. Please check the sheet URL in configuration.",
                    ephemeral=True
                )
            elif "permission" in error_message.lower() or "403" in error_message:
                await interaction.followup.send(
                    content="❌ Permission denied accessing Google Sheet. Please ensure the sheet is shared with the bot's service account.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    content=f"❌ Detection failed: {error_message}",
                    ephemeral=True
                )

    @ui.button(custom_id="cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle cancel."""
        await interaction.response.send_message("❌ Column configuration cancelled.", ephemeral=True)

    def _get_column_status(self, column_type: str) -> str:
        """Get the current status for a column."""
        current_col = getattr(self.current_mapping, f"{column_type}_column", None) if self.current_mapping else None
        detection = self.detections.get(column_type)
        return current_col or (detection.column_letter if detection else "Not set")

    def create_embed(self) -> discord.Embed:
        """
        Create the embed showing column configuration.
        """
        embed = discord.Embed(
            title="📊 Google Sheet Column Assignment",
            color=discord.Colour.green(),
            description="Configure which columns contain your player data using the containers below"
        )

        # Add current status info
        column_configs = [
            ("Discord", "discord", self.current_mapping.discord_column if self.current_mapping else None),
            ("IGN", "ign", self.current_mapping.ign_column if self.current_mapping else None),
            ("Alt IGN", "alt_ign", self.current_mapping.alt_ign_column if self.current_mapping else None),
            ("Pronouns", "pronouns", self.current_mapping.pronouns_column if self.current_mapping else None),
            ("Registered", "registered", self.current_mapping.registered_column if self.current_mapping else None),
            ("Check-in", "checkin", self.current_mapping.checkin_column if self.current_mapping else None),
        ]

        # Only add team section for doubleup mode
        mode = get_event_mode_for_guild(self.guild_id)
        if mode == "doubleup":
            column_configs.append(("Team", "team", self.current_mapping.team_column if self.current_mapping else None))

        # Build field content
        for display_name, column_type, current_col in column_configs:
            detection = self.detections.get(column_type)

            if current_col:
                status = current_col
                confidence = "Manual"
            elif detection:
                status = detection.column_letter
                confidence = f"({detection.confidence_score:.0f}% confidence)"
            else:
                status = "None"
                confidence = "(Not detected)"

            embed.add_field(
                name=f"**{display_name}**",
                value=f"**Column:** `{status}`\n**Status:** {confidence}",
                inline=True
            )

        embed.set_footer(text="Use the buttons below to update column mappings")
        return embed

    
    async def respond_with_ui(self, interaction: discord.Interaction):
        """
        Send the container-based UI response.
        """
        await self.initialize()

        await interaction.response.send_message(view=self, ephemeral=True)

    async def on_timeout(self) -> None:
        """Handle view timeout."""
        logging.info(f"[CONFIG_UI] View timed out for guild {self.guild_id}")

    async def handle_button_callback(self, interaction: discord.Interaction, custom_id: str):
        """
        Handle button callbacks for the view.
        """
        logging.info(f"[CONFIG_UI] Processing button callback: {custom_id}")

        if custom_id.startswith("update_"):
            column_type = custom_id.replace("update_", "")
            logging.info(f"[CONFIG_UI] Opening update modal for column: {column_type}")
            modal = ColumnUpdateModal(self, column_type)
            await interaction.response.send_modal(modal)
        elif custom_id.startswith("remove_"):
            column_type = custom_id.replace("remove_", "")
            logging.info(f"[CONFIG_UI] Opening remove confirmation modal for column: {column_type}")
            modal = ColumnRemoveConfirmModal(self, column_type)
            await interaction.response.send_modal(modal)
        elif custom_id == "detect":
            logging.info(f"[CONFIG_UI] Starting column detection")
            await interaction.response.defer(ephemeral=True)
            try:
                # Force refresh detection
                self.detections = await detect_sheet_columns(self.guild_id, force_refresh=True)
                await self.initialize()

                # Create new view and send it
                new_view = ColumnMappingView(self.guild_id)
                await new_view.initialize()

                embed = new_view.create_embed()
                await interaction.followup.send(embed=embed, view=new_view, ephemeral=True)
            except discord.errors.Forbidden:
                logging.error(f"[CONFIG_UI] Permission denied during column detection")
                await interaction.followup.send(
                    content="❌ I don't have permission to access the Google Sheet. Please check sheet permissions.",
                    ephemeral=True
                )
            except gspread.exceptions.GSpreadException as gs_error:
                logging.error(f"[CONFIG_UI] Google Sheets API error during detection: {gs_error}")
                await interaction.followup.send(
                    content="❌ Google Sheets API error. Please check the sheet URL and permissions.",
                    ephemeral=True
                )
            except Exception as e:
                logging.error(f"[CONFIG_UI] Detection failed: {e}")
                error_message = str(e)
                if "timeout" in error_message.lower():
                    await interaction.followup.send(
                        content="❌ Detection timed out. The Google Sheet might be too large or unavailable. Please try again.",
                        ephemeral=True
                    )
                elif "not found" in error_message.lower() or "404" in error_message:
                    await interaction.followup.send(
                        content="❌ Google Sheet not found. Please check the sheet URL in configuration.",
                        ephemeral=True
                    )
                elif "permission" in error_message.lower() or "403" in error_message:
                    await interaction.followup.send(
                        content="❌ Permission denied accessing Google Sheet. Please ensure the sheet is shared with the bot's service account.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        content=f"❌ Failed to detect columns: {error_message}",
                        ephemeral=True
                    )
        elif custom_id == "cancel":
            logging.info(f"[CONFIG_UI] Canceling configuration")
            await interaction.response.edit_message(
                content="Configuration cancelled.",
                view=None
            )
        else:
            logging.warning(f"[CONFIG_UI] Unknown action: {custom_id}")
            await interaction.response.send_message(
                content=f"Unknown action: {custom_id}",
                ephemeral=True
            )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Handle button interactions for LayoutView.
        """
        custom_id = interaction.data.get("custom_id", "")
        if custom_id:
            await self.handle_button_callback(interaction, custom_id)
            return True
        return False


class ColumnUpdateModal(ui.Modal):
    """
    Modal for updating a column mapping.
    """

    def __init__(self, parent_view: ColumnMappingView, column_type: str):
        column_display_name = column_type.replace('_', ' ').title()
        super().__init__(title=f"Update {column_display_name} Column")
        self.parent_view = parent_view
        self.column_type = column_type

        # Get current value for this column
        current_mapping = parent_view.current_mapping
        current_value = getattr(current_mapping, f"{column_type}_column", "") if current_mapping else ""

        # Get detected value
        detection = parent_view.detections.get(column_type)
        detected_value = detection.column_letter if detection else ""

        self.add_item(ui.TextInput(
            label="Column Letter",
            placeholder="e.g., A, B, C, D",
            default=current_value or detected_value,
            style=discord.TextStyle.short,
            required=True,
            max_length=3
        ))

    async def on_submit(self, interaction: discord.Interaction):
        """
        Handle column update submission with auto-save.
        """
        try:
            column_letter = self.children[0].value.upper().strip()

            # Enhanced validation for column letter format
            if not column_letter or not column_letter[0].isalpha():
                await interaction.response.send_message(
                    "❌ Invalid column letter. Please use a letter like A, B, C, AA, AB, etc.",
                    ephemeral=True
                )
                return

            # Additional validation for column length
            if len(column_letter) > 3:
                await interaction.response.send_message(
                    "❌ Column letter too long. Please use a maximum of 3 letters (e.g., A, AA, AAA).",
                    ephemeral=True
                )
                return

            # Update the mapping with validation
            mapping = self.parent_view.current_mapping
            if not mapping:
                await interaction.response.send_message(
                    "❌ No current mapping found. Please try detecting columns first.",
                    ephemeral=True
                )
                return

            if self.column_type == "discord":
                mapping.discord_column = column_letter
            elif self.column_type == "ign":
                mapping.ign_column = column_letter
            elif self.column_type == "alt_ign":
                mapping.alt_ign_column = column_letter
            elif self.column_type == "pronouns":
                mapping.pronouns_column = column_letter
            elif self.column_type == "registered":
                mapping.registered_column = column_letter
            elif self.column_type == "checkin":
                mapping.checkin_column = column_letter
            elif self.column_type == "team":
                mapping.team_column = column_letter
            else:
                await interaction.response.send_message(
                    f"❌ Unknown column type: {self.column_type}",
                    ephemeral=True
                )
                return

            # Auto-save the mapping with error handling
            try:
                await save_column_mapping(self.parent_view.guild_id, mapping)
                logging.info(f"[CONFIG_UI] Successfully saved column mapping for {self.column_type} = {column_letter}")
            except Exception as save_error:
                logging.error(f"[CONFIG_UI] Failed to save column mapping: {save_error}")
                await interaction.response.send_message(
                    "❌ Failed to save column mapping. The column was updated but may not persist after restart.",
                    ephemeral=True
                )
                return

            column_display_name = self.column_type.replace('_', ' ').title()
            await interaction.response.send_message(
                f"✅ Updated {column_display_name} column to {column_letter} and saved automatically.",
                ephemeral=True
            )

        except discord.errors.InteractionResponded:
            # Interaction already responded to, log and ignore
            logging.warning(f"[CONFIG_UI] Interaction already responded for {self.column_type}")
        except discord.errors.Forbidden:
            logging.error(f"[CONFIG_UI] Permission denied for {self.column_type} update")
            try:
                await interaction.response.send_message(
                    "❌ I don't have permission to perform this action.",
                    ephemeral=True
                )
            except discord.errors.InteractionResponded:
                logging.warning(f"[CONFIG_UI] Could not respond to permission denied error")
        except Exception as e:
            logging.error(f"[CONFIG_UI] Failed to update column {self.column_type}: {e}")
            try:
                await interaction.response.send_message(
                    "❌ Failed to update column. Please try again or contact an admin.",
                    ephemeral=True
                )
            except discord.errors.InteractionResponded:
                logging.warning(f"[CONFIG_UI] Could not respond to user about error for {self.column_type}")
            except Exception as response_error:
                logging.error(f"[CONFIG_UI] Critical error responding to user for {self.column_type}: {response_error}")


class ColumnRemoveConfirmModal(ui.Modal):
    """
    Modal for confirming column removal with button confirmation.
    """

    def __init__(self, parent_view: ColumnMappingView, column_type: str):
        column_display_name = column_type.replace('_', ' ').title()
        super().__init__(title=f"Remove {column_display_name} Column")
        self.parent_view = parent_view
        self.column_type = column_type

        # Get current value for confirmation
        current_mapping = parent_view.current_mapping
        current_value = getattr(current_mapping, f"{column_type}_column", "") if current_mapping else "None"

        self.add_item(ui.TextInput(
            label=f"Are you sure you want to remove {column_display_name} column?",
            placeholder=f"Current value: {current_value or 'None'}",
            style=discord.TextStyle.short,
            required=False,
            default="Type CONFIRM to remove this column mapping"
        ))

    async def on_submit(self, interaction: discord.Interaction):
        """
        Handle column removal confirmation.
        """
        confirmation = self.children[0].value.strip().upper()

        if confirmation != "CONFIRM":
            await interaction.response.send_message(
                "❌ Removal cancelled. You must type 'CONFIRM' to proceed.",
                ephemeral=True
            )
            return

        # Update the mapping to remove the column
        mapping = self.parent_view.current_mapping
        if self.column_type == "discord":
            mapping.discord_column = None
        elif self.column_type == "ign":
            mapping.ign_column = None
        elif self.column_type == "alt_ign":
            mapping.alt_ign_column = None
        elif self.column_type == "pronouns":
            mapping.pronouns_column = None
        elif self.column_type == "registered":
            mapping.registered_column = None
        elif self.column_type == "checkin":
            mapping.checkin_column = None
        elif self.column_type == "team":
            mapping.team_column = None

        # Auto-save the mapping
        await save_column_mapping(self.parent_view.guild_id, mapping)

        column_display_name = self.column_type.replace('_', ' ').title()
        await interaction.response.send_message(
            f"✅ Removed {column_display_name} column mapping and saved automatically.",
            ephemeral=True
        )


class SettingsView(ui.LayoutView):
    """
    Configuration UI for general bot settings using discord.py v2 components.
    """

    def __init__(self, guild_id: str):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """
        Load current settings from config and persistence.
        """
        # Get sheet settings
        mode = get_event_mode_for_guild(self.guild_id)
        sheet_settings = get_sheet_settings(mode)

        # Get guild-specific data
        guild_data = get_guild_data(self.guild_id)

        settings = {
            "header_line_num": sheet_settings.get("header_line_num", 1),
            "max_players": sheet_settings.get("max_players", 24),
            "mode": mode,
            "log_channel": _FULL_CFG.get("channels", {}).get("log_channel", "bot-log"),
            "unified_channel": _FULL_CFG.get("channels", {}).get("unified_channel", "🎫registration"),
        }

        return settings

    def build_sections(self) -> List[ui.Section]:
        """
        Build sections for each setting.
        """
        sections = []

        # Sheet settings
        sheet_settings = [
            ("Header Line Number", "header_line_num", str(self.settings["header_line_num"])),
            ("Max Players", "max_players", str(self.settings["max_players"])),
            ("Event Mode", "mode", self.settings["mode"]),
        ]

        for display_name, key, value in sheet_settings:
            section = ui.Section(
                ui.TextDisplay(content=f"{display_name}: {value}"),
                accessory=ui.Button(
                    style=discord.ButtonStyle.primary,
                    label="Edit",
                    custom_id=f"edit_{key}",
                ),
            )
            sections.append(section)

        # Channel settings
        channel_settings = [
            ("Log Channel", "log_channel", self.settings["log_channel"]),
            ("Unified Channel", "unified_channel", self.settings["unified_channel"]),
        ]

        for display_name, key, value in channel_settings:
            section = ui.Section(
                ui.TextDisplay(content=f"{display_name}: {value}"),
                accessory=ui.Button(
                    style=discord.ButtonStyle.primary,
                    label="Edit",
                    custom_id=f"edit_{key}",
                ),
            )
            sections.append(section)

        return sections

    def build_container(self) -> ui.Container:
        """
        Build the main container for settings.
        """
        sections = self.build_sections()

        container = ui.Container(
            ui.TextDisplay(content="# Bot Configuration"),
            ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            ui.TextDisplay(content="## Sheet Settings"),
            ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            *sections[:3],  # Sheet settings
            ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            ui.TextDisplay(content="## Channel Settings"),
            ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            *sections[3:],  # Channel settings
            accent_colour=discord.Colour(9225410),
        )

        return container

    async def respond_with_ui(self, interaction: discord.Interaction):
        """
        Send the ephemeral UI response.
        """
        container = self.build_container()
        complete_view = ui.View(container)

        await interaction.response.send_message(
            view=complete_view,
            ephemeral=True
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Handle interactions for the SettingsView.
        """
        custom_id = interaction.data.get("custom_id", "")
        if custom_id.startswith("edit_"):
            setting_key = custom_id.replace("edit_", "")
            modal = SettingsEditModal(self, setting_key)
            await interaction.response.send_modal(modal)
        return True


class SettingsEditModal(ui.Modal):
    """
    Modal for editing a specific setting.
    """

    def __init__(self, parent_view: SettingsView, setting_key: str):
        super().__init__(title=f"Edit {setting_key.replace('_', ' ').title()}")
        self.parent_view = parent_view
        self.setting_key = setting_key

        # Configure the text input based on setting type
        current_value = str(parent_view.settings[setting_key])

        if setting_key in ["header_line_num", "max_players"]:
            label = setting_key.replace('_', ' ').title()
            placeholder = "Enter a number"
        elif setting_key == "mode":
            label = "Event Mode"
            placeholder = "normal or doubleup"
        else:
            label = setting_key.replace('_', ' ').title()
            placeholder = "Enter new value"

        self.add_item(ui.TextInput(
            label=label,
            placeholder=placeholder,
            default=current_value,
            style=discord.TextStyle.short,
            required=True
        ))

    async def on_submit(self, interaction: discord.Interaction):
        """
        Handle setting edit submission.
        """
        new_value = self.children[0].value.strip()

        # Validate based on setting type
        if self.setting_key in ["header_line_num", "max_players"]:
            try:
                new_value = int(new_value)
                if new_value < 1:
                    raise ValueError("Value must be positive")
            except ValueError:
                await interaction.response.send_message(
                    "❌ Please enter a valid positive number",
                    ephemeral=True
                )
                return
        elif self.setting_key == "mode":
            if new_value not in ["normal", "doubleup"]:
                await interaction.response.send_message(
                    "❌ Mode must be 'normal' or 'doubleup'",
                    ephemeral=True
                )
                return

        # Save the setting
        if self.setting_key == "mode":
            # Save to persistence for event mode
            from core.persistence import set_event_mode_for_guild
            set_event_mode_for_guild(self.parent_view.guild_id, new_value)
        else:
            # Save to guild data for other settings
            guild_data = get_guild_data(self.parent_view.guild_id)
            guild_data[f"setting_{self.setting_key}"] = new_value
            update_guild_data(self.parent_view.guild_id, guild_data)

        await interaction.response.send_message(
            f"✅ Updated {self.setting_key.replace('_', ' ').title()} to {new_value}",
            ephemeral=True
        )