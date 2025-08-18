# helpers/config_manager.py

from typing import Dict, Any

import discord
import yaml

from config import _FULL_CFG, EMBEDS_CFG, SHEET_CONFIG


class ConfigManager:
    """Manages configuration loading and reloading."""

    @staticmethod
    def reload_config(config_path: str = "config.yaml") -> bool:
        """
        Reload configuration from file.
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                new_cfg = yaml.safe_load(f)

            # Update in-place so all modules see the changes
            _FULL_CFG.clear()
            _FULL_CFG.update(new_cfg)

            EMBEDS_CFG.clear()
            EMBEDS_CFG.update(_FULL_CFG.get("embeds", {}))

            SHEET_CONFIG.clear()
            SHEET_CONFIG.update(_FULL_CFG.get("sheet_configuration", {}))

            return True
        except Exception as e:
            print(f"[CONFIG-RELOAD-ERROR] Failed to reload config: {e}")
            return False

    @staticmethod
    def get_embed_config(key: str) -> Dict[str, Any]:
        """Get embed configuration by key."""
        return EMBEDS_CFG.get(key, {})

    @staticmethod
    def get_sheet_config(mode: str) -> Dict[str, Any]:
        """Get sheet configuration for a specific mode."""
        return SHEET_CONFIG.get(mode, SHEET_CONFIG.get("normal", {}))

    @staticmethod
    def get_rich_presence() -> tuple[discord.ActivityType, str]:
        """
        Get rich presence configuration.
        """
        presence_cfg = _FULL_CFG.get("rich_presence", {})
        pres_type = presence_cfg.get("type", "PLAYING").upper()
        pres_msg = presence_cfg.get("message", "")

        activity_type = {
            "PLAYING": discord.ActivityType.playing,
            "LISTENING": discord.ActivityType.listening,
            "WATCHING": discord.ActivityType.watching,
            "STREAMING": discord.ActivityType.streaming,
            "COMPETING": discord.ActivityType.competing
        }.get(pres_type, discord.ActivityType.playing)

        return activity_type, pres_msg

    @staticmethod
    async def apply_rich_presence(bot: discord.Client) -> None:
        """Apply rich presence configuration to bot."""
        activity_type, message = ConfigManager.get_rich_presence()

        if activity_type == discord.ActivityType.listening:
            activity = discord.Activity(type=activity_type, name=message)
        elif activity_type == discord.ActivityType.watching:
            activity = discord.Activity(type=activity_type, name=message)
        else:
            activity = discord.Game(name=message)

        await bot.change_presence(activity=activity)

    @staticmethod
    def validate_config() -> Dict[str, list[str]]:
        """
        Validate configuration for common issues.
        """
        issues = {
            "embeds": [],
            "sheet_configuration": [],
            "general": []
        }

        # Check required embed keys
        required_embeds = [
            "registration", "registration_closed", "checkin", "checkin_closed",
            "permission_denied", "error", "unregister_success", "unregister_not_registered",
            "checkin_requires_registration", "already_checked_in", "already_checked_out",
            "checked_in", "checked_out"
        ]
        for key in required_embeds:
            if key not in EMBEDS_CFG:
                issues["embeds"].append(f"Missing required embed: {key}")

        # Check sheet configuration
        for mode in ["normal", "doubleup"]:
            if mode not in SHEET_CONFIG:
                issues["sheet_configuration"].append(f"Missing mode: {mode}")
            else:
                mode_cfg = SHEET_CONFIG[mode]
                required_fields = [
                    "sheet_url", "header_line_num", "max_players",
                    "discord_col", "ign_col", "registered_col", "checkin_col"
                ]
                if mode == "doubleup":
                    required_fields.append("team_col")

                for field in required_fields:
                    if field not in mode_cfg:
                        issues["sheet_configuration"].append(
                            f"Missing field '{field}' in {mode} mode"
                        )

        # Remove empty sections
        return {k: v for k, v in issues.items() if v}

    @staticmethod
    def get_command_help() -> Dict[str, str]:
        """Get command help descriptions from config."""
        help_cfg = EMBEDS_CFG.get("help", {})
        return help_cfg.get("commands", {})

    @staticmethod
    def update_embed_template(key: str, **kwargs) -> None:
        """
        Update an embed template in memory (not persisted to file).
        Useful for dynamic embed updates.
        """
        if key not in EMBEDS_CFG:
            EMBEDS_CFG[key] = {}

        for field, value in kwargs.items():
            if field in ["title", "description", "color"]:
                EMBEDS_CFG[key][field] = value

    @staticmethod
    async def reload_and_update_all(bot: discord.Client) -> Dict[str, bool]:
        """
        Reload config and update all necessary components.
        """
        from helpers import EmbedHelper

        results = {
            "config_reload": False,
            "presence_update": False,
            "embeds_updated": {}
        }

        # Reload config
        results["config_reload"] = ConfigManager.reload_config()

        if results["config_reload"]:
            # Update rich presence
            try:
                await ConfigManager.apply_rich_presence(bot)
                results["presence_update"] = True
            except Exception as e:
                print(f"[CONFIG-RELOAD] Failed to update presence: {e}")

            # Update embeds for all guilds
            for guild in bot.guilds:
                guild_results = await EmbedHelper.update_all_guild_embeds(guild)
                results["embeds_updated"][guild.name] = guild_results

        return results
