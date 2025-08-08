# helpers/config_manager.py

import os
import time
import json
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

import discord
import yaml

from config import _FULL_CFG, EMBEDS_CFG, SHEET_CONFIG
from .logging_helper import BotLogger


class ConfigurationError(Exception):
    """
    Exception raised when configuration operations fail.
    """

    def __init__(self, operation: str, section: str, reason: str, **context):
        self.operation = operation
        self.section = section
        self.reason = reason
        self.context = context
        self.timestamp = datetime.now(timezone.utc)

        message = f"Configuration {operation} failed for section '{section}': {reason}"
        super().__init__(message)


class ConfigurationValidationError(ConfigurationError):
    """
    Exception raised when configuration validation fails.
    """

    def __init__(self, section: str, errors: List[str], warnings: List[str] = None):
        self.errors = errors
        self.warnings = warnings or []

        reason = f"{len(errors)} validation error(s) found"
        super().__init__("validation", section, reason, errors=errors, warnings=warnings)


class ConfigManager:
    """
    Configuration management system with validation, hot-reloading, and recovery.
    """

    # Class-level configuration state
    _config_file_path = "config.yaml"
    _backup_directory = "config_backups"
    _last_modified = 0
    _last_validation = None
    _change_callbacks = []

    @classmethod
    def set_config_file(cls, file_path: str) -> None:
        """
        Set the configuration file path.
        """
        if not file_path or not isinstance(file_path, str):
            raise ConfigurationError("set_path", "global", "File path must be a non-empty string")

        cls._config_file_path = file_path
        BotLogger.info(f"Configuration file path set to: {file_path}", "CONFIG_MGR")

    @classmethod
    def register_change_callback(cls, callback: callable) -> None:
        """
        Register a callback to be called when configuration changes.
        """
        if callable(callback):
            cls._change_callbacks.append(callback)
            BotLogger.debug(f"Registered configuration change callback: {callback.__name__}", "CONFIG_MGR")

    @staticmethod
    def reload_config(config_path: str = None, create_backup: bool = True) -> bool:
        """
        Reload configuration from file with comprehensive validation and rollback capability.
        """
        config_path = config_path or ConfigManager._config_file_path

        BotLogger.info(f"Starting configuration reload from: {config_path}", "CONFIG_MGR")

        # Store original configuration for potential rollback
        original_full_cfg = dict(_FULL_CFG)
        original_embeds_cfg = dict(EMBEDS_CFG)
        original_sheet_config = dict(SHEET_CONFIG)

        try:
            # Create backup if requested
            if create_backup:
                backup_path = ConfigManager._create_backup(config_path)
                BotLogger.info(f"Created configuration backup: {backup_path}", "CONFIG_MGR")

            # Load and validate new configuration
            new_config = ConfigManager._load_configuration_file(config_path)
            validation_result = ConfigManager.validate_configuration(new_config)

            if not validation_result['valid']:
                # Validation failed - don't update configuration
                error_details = '; '.join(validation_result['errors'])
                BotLogger.error(f"Configuration validation failed: {error_details}", "CONFIG_MGR")

                if validation_result['warnings']:
                    warning_details = '; '.join(validation_result['warnings'])
                    BotLogger.warning(f"Configuration warnings: {warning_details}", "CONFIG_MGR")

                return False

            # Log any warnings even if validation passed
            if validation_result['warnings']:
                warning_details = '; '.join(validation_result['warnings'])
                BotLogger.warning(f"Configuration warnings: {warning_details}", "CONFIG_MGR")

            # Update configurations atomically
            ConfigManager._update_configurations(new_config)

            # Detect and log changes
            changes = ConfigManager._detect_changes(original_full_cfg, new_config)
            if changes:
                BotLogger.info(f"Configuration changes detected: {changes}", "CONFIG_MGR")

                # Notify registered callbacks
                ConfigManager._notify_change_callbacks(original_full_cfg, new_config)
            else:
                BotLogger.info("No configuration changes detected", "CONFIG_MGR")

            # Update file modification tracking
            ConfigManager._last_modified = ConfigManager._get_file_modification_time(config_path)
            ConfigManager._last_validation = datetime.now(timezone.utc)

            BotLogger.info("Configuration reload completed successfully", "CONFIG_MGR")
            return True

        except Exception as e:
            # Rollback to original configuration
            BotLogger.error(f"Configuration reload failed, performing rollback: {e}", "CONFIG_MGR")

            try:
                _FULL_CFG.clear()
                _FULL_CFG.update(original_full_cfg)

                EMBEDS_CFG.clear()
                EMBEDS_CFG.update(original_embeds_cfg)

                SHEET_CONFIG.clear()
                SHEET_CONFIG.update(original_sheet_config)

                BotLogger.info("Successfully rolled back to previous configuration", "CONFIG_MGR")

            except Exception as rollback_error:
                BotLogger.error(f"Critical error during configuration rollback: {rollback_error}", "CONFIG_MGR")
                raise ConfigurationError(
                    "rollback", "global", f"Rollback failed: {rollback_error}"
                ) from rollback_error

            return False

    @staticmethod
    def _load_configuration_file(config_path: str) -> Dict[str, Any]:
        """
        Load configuration file with support for multiple formats.
        """
        if not os.path.exists(config_path):
            raise ConfigurationError(
                "load", "file", f"Configuration file not found: {config_path}"
            )

        file_extension = Path(config_path).suffix.lower()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if file_extension in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                elif file_extension == '.json':
                    config = json.load(f)
                else:
                    # Default to YAML for unknown extensions
                    BotLogger.warning(
                        f"Unknown config file extension '{file_extension}', assuming YAML",
                        "CONFIG_MGR"
                    )
                    config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise ConfigurationError(
                    "load", "structure", "Configuration file must contain a dictionary/object at root level"
                )

            BotLogger.debug(f"Successfully loaded configuration from {config_path}", "CONFIG_MGR")
            return config

        except yaml.YAMLError as e:
            raise ConfigurationError(
                "load", "yaml", f"YAML parsing error: {e}"
            ) from e
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                "load", "json", f"JSON parsing error: {e}"
            ) from e
        except UnicodeDecodeError as e:
            raise ConfigurationError(
                "load", "encoding", f"File encoding error: {e}"
            ) from e
        except Exception as e:
            raise ConfigurationError(
                "load", "file", f"Unexpected error loading configuration: {e}"
            ) from e

    @staticmethod
    def _update_configurations(new_config: Dict[str, Any]) -> None:
        """
        Update all configuration dictionaries atomically.
        """
        # Update main configuration
        _FULL_CFG.clear()
        _FULL_CFG.update(new_config)

        # Update embeds configuration
        EMBEDS_CFG.clear()
        EMBEDS_CFG.update(new_config.get("embeds", {}))

        # Update sheet configuration
        SHEET_CONFIG.clear()
        SHEET_CONFIG.update(new_config.get("sheet_configuration", {}))

        BotLogger.debug("Configuration dictionaries updated successfully", "CONFIG_MGR")

    @staticmethod
    def _detect_changes(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> List[str]:
        """
        Detect changes between old and new configuration.
        """
        changes = []

        # Check for added/removed top-level sections
        old_sections = set(old_config.keys())
        new_sections = set(new_config.keys())

        added_sections = new_sections - old_sections
        removed_sections = old_sections - new_sections

        for section in added_sections:
            changes.append(f"Added section: {section}")
        for section in removed_sections:
            changes.append(f"Removed section: {section}")

        # Check for changes in existing sections
        common_sections = old_sections & new_sections
        for section in common_sections:
            old_value = old_config[section]
            new_value = new_config[section]

            if old_value != new_value:
                changes.append(f"Modified section: {section}")

        return changes

    @staticmethod
    def _notify_change_callbacks(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """
        Notify registered callbacks about configuration changes.
        """
        for callback in ConfigManager._change_callbacks:
            try:
                callback(old_config, new_config)
                BotLogger.debug(f"Notified callback: {callback.__name__}", "CONFIG_MGR")
            except Exception as e:
                BotLogger.error(f"Error in configuration change callback {callback.__name__}: {e}", "CONFIG_MGR")

    @staticmethod
    def _create_backup(config_path: str) -> str:
        """
        Create a timestamped backup of the configuration file.
        """
        try:
            # Create backup directory if it doesn't exist
            backup_dir = Path(ConfigManager._backup_directory)
            backup_dir.mkdir(exist_ok=True)

            # Generate timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            config_name = Path(config_path).stem
            config_ext = Path(config_path).suffix
            backup_filename = f"{config_name}_backup_{timestamp}{config_ext}"
            backup_path = backup_dir / backup_filename

            # Copy the configuration file
            shutil.copy2(config_path, backup_path)

            # Clean up old backups (keep last 10)
            ConfigManager._cleanup_old_backups(backup_dir, config_name, keep_count=10)

            return str(backup_path)

        except Exception as e:
            raise ConfigurationError(
                "backup", "file", f"Failed to create backup: {e}"
            ) from e

    @staticmethod
    def _cleanup_old_backups(backup_dir: Path, config_name: str, keep_count: int = 10) -> None:
        """
        Clean up old backup files, keeping only the most recent ones.
        """
        try:
            # Find all backup files for this configuration
            pattern = f"{config_name}_backup_*"
            backup_files = list(backup_dir.glob(pattern))

            if len(backup_files) > keep_count:
                # Sort by modification time (newest first)
                backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

                # Remove old backups
                for old_backup in backup_files[keep_count:]:
                    try:
                        old_backup.unlink()
                        BotLogger.debug(f"Removed old backup: {old_backup.name}", "CONFIG_MGR")
                    except Exception as e:
                        BotLogger.warning(f"Failed to remove old backup {old_backup.name}: {e}", "CONFIG_MGR")

        except Exception as e:
            BotLogger.warning(f"Error during backup cleanup: {e}", "CONFIG_MGR")

    @staticmethod
    def _get_file_modification_time(file_path: str) -> float:
        """
        Get file modification time safely.
        """
        try:
            return os.path.getmtime(file_path)
        except (OSError, FileNotFoundError):
            return 0

    @staticmethod
    def get_embed_config(key: str) -> Dict[str, Any]:
        """
        Get embed configuration by key with validation.
        """
        config = EMBEDS_CFG.get(key, {})

        if not config:
            BotLogger.warning(f"Embed configuration not found for key: {key}", "CONFIG_MGR")
            return {}

        # Validate embed configuration structure
        if not isinstance(config, dict):
            BotLogger.error(f"Invalid embed configuration for key '{key}': not a dictionary", "CONFIG_MGR")
            return {}

        return config

    @staticmethod
    def get_sheet_config(mode: str, guild_id: str = None) -> Dict[str, Any]:
        """
        Get sheet configuration for a specific mode with validation.
        """
        if mode not in SHEET_CONFIG:
            # Fall back to normal mode if requested mode doesn't exist
            BotLogger.warning(f"Sheet mode '{mode}' not found, falling back to 'normal'", "CONFIG_MGR")
            mode = "normal"

            if mode not in SHEET_CONFIG:
                raise ConfigurationError(
                    "get_sheet_config", "sheet_configuration",
                    "No valid sheet configuration found"
                )

        config = SHEET_CONFIG[mode].copy()  # Make a copy to avoid modifying original

        # Validate required fields
        required_fields = [
            "header_line_num", "max_players", "discord_col",
            "ign_col", "registered_col", "checkin_col"
        ]

        if mode == "doubleup":
            required_fields.extend(["max_per_team", "team_col"])

        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ConfigurationError(
                "get_sheet_config", f"sheet_configuration.{mode}",
                f"Missing required fields: {missing_fields}"
            )

        # Handle environment-specific sheet URLs
        if guild_id:
            from config import BotConstants
            if guild_id == BotConstants.TEST_GUILD_ID:
                if "test_sheet_url" in config:
                    config["sheet_url"] = config["test_sheet_url"]
                    BotLogger.debug(f"Using test sheet URL for guild {guild_id}", "CONFIG_MGR")
            else:
                if "prod_sheet_url" in config:
                    config["sheet_url"] = config["prod_sheet_url"]

        # Validate that we have a sheet URL
        if "sheet_url" not in config:
            raise ConfigurationError(
                "get_sheet_config", f"sheet_configuration.{mode}",
                "No sheet URL configured (missing sheet_url, prod_sheet_url, or test_sheet_url)"
            )

        return config

    @staticmethod
    def get_rich_presence() -> Tuple[discord.ActivityType, str]:
        """
        Get rich presence configuration with validation and defaults.
        """
        try:
            presence_cfg = _FULL_CFG.get("rich_presence", {})

            # Get and validate presence type
            pres_type = presence_cfg.get("type", "PLAYING").upper().strip()
            pres_msg = presence_cfg.get("message", "🛡️ TFT").strip()

            # Map string types to Discord activity types
            activity_type_mapping = {
                "PLAYING": discord.ActivityType.playing,
                "LISTENING": discord.ActivityType.listening,
                "WATCHING": discord.ActivityType.watching,
                "STREAMING": discord.ActivityType.streaming,
                "COMPETING": discord.ActivityType.competing
            }

            activity_type = activity_type_mapping.get(pres_type, discord.ActivityType.playing)

            # Log warning if type was invalid
            if pres_type not in activity_type_mapping:
                BotLogger.warning(
                    f"Invalid rich presence type '{pres_type}', using PLAYING",
                    "CONFIG_MGR"
                )

            BotLogger.debug(f"Rich presence configured: {pres_type} - {pres_msg}", "CONFIG_MGR")
            return activity_type, pres_msg

        except Exception as e:
            BotLogger.error(f"Error getting rich presence configuration: {e}", "CONFIG_MGR")
            return discord.ActivityType.playing, "🛡️ TFT"

    @staticmethod
    async def apply_rich_presence(bot: discord.Client) -> bool:
        """
        Apply rich presence configuration to bot.
        """
        if not bot or not hasattr(bot, 'change_presence'):
            BotLogger.error("Invalid bot client for rich presence", "CONFIG_MGR")
            return False

        try:
            activity_type, message = ConfigManager.get_rich_presence()

            # Create appropriate activity object based on type
            if activity_type == discord.ActivityType.playing:
                activity = discord.Game(name=message)
            else:
                activity = discord.Activity(type=activity_type, name=message)

            # Apply the presence
            await bot.change_presence(activity=activity)

            BotLogger.info(f"Applied rich presence: {activity_type.name} - {message}", "CONFIG_MGR")
            return True

        except Exception as e:
            BotLogger.error(f"Failed to apply rich presence: {e}", "CONFIG_MGR")
            return False

    @staticmethod
    def validate_configuration(config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform comprehensive validation of configuration data.
        """
        if config is None:
            config = _FULL_CFG

        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'sections': {}
        }

        try:
            # Validate top-level structure
            if not isinstance(config, dict):
                validation_result['valid'] = False
                validation_result['errors'].append("Configuration must be a dictionary")
                return validation_result

            # Validate required sections
            required_sections = ["embeds", "sheet_configuration"]
            for section in required_sections:
                if section not in config:
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Missing required section: {section}")
                else:
                    validation_result['sections'][section] = {'present': True}

            # Validate embeds section
            if "embeds" in config:
                embeds_validation = ConfigManager._validate_embeds_section(config["embeds"])
                validation_result['sections']['embeds'].update(embeds_validation)

                if not embeds_validation['valid']:
                    validation_result['valid'] = False
                    validation_result['errors'].extend(embeds_validation['errors'])

                validation_result['warnings'].extend(embeds_validation.get('warnings', []))

            # Validate sheet configuration section
            if "sheet_configuration" in config:
                sheet_validation = ConfigManager._validate_sheet_configuration(config["sheet_configuration"])
                validation_result['sections']['sheet_configuration'] = sheet_validation

                if not sheet_validation['valid']:
                    validation_result['valid'] = False
                    validation_result['errors'].extend(sheet_validation['errors'])

                validation_result['warnings'].extend(sheet_validation.get('warnings', []))

            # Validate rich presence section (optional)
            if "rich_presence" in config:
                presence_validation = ConfigManager._validate_rich_presence(config["rich_presence"])
                validation_result['sections']['rich_presence'] = presence_validation
                validation_result['warnings'].extend(presence_validation.get('warnings', []))

            BotLogger.debug(
                f"Configuration validation completed: {'PASSED' if validation_result['valid'] else 'FAILED'}",
                "CONFIG_MGR"
            )

        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
            BotLogger.error(f"Error during configuration validation: {e}", "CONFIG_MGR")

        return validation_result

    @staticmethod
    def _validate_embeds_section(embeds_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the embeds configuration section.
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        if not isinstance(embeds_config, dict):
            result['valid'] = False
            result['errors'].append("Embeds section must be a dictionary")
            return result

        # Check for required embed keys
        required_embeds = [
            "registration", "registration_closed", "checkin", "checkin_closed",
            "permission_denied", "error", "checked_in", "checked_out",
            "register_success_normal", "register_success_doubleup",
            "unregister_success", "unregister_not_registered"
        ]

        for embed_key in required_embeds:
            if embed_key not in embeds_config:
                result['errors'].append(f"Missing required embed: {embed_key}")
                result['valid'] = False
            else:
                # Validate embed structure
                embed_config = embeds_config[embed_key]
                if not isinstance(embed_config, dict):
                    result['errors'].append(f"Embed '{embed_key}' must be a dictionary")
                    result['valid'] = False
                else:
                    # Check for recommended fields
                    if 'title' not in embed_config and 'description' not in embed_config:
                        result['warnings'].append(f"Embed '{embed_key}' has no title or description")

        return result

    @staticmethod
    def _validate_sheet_configuration(sheet_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the sheet configuration section.
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        if not isinstance(sheet_config, dict):
            result['valid'] = False
            result['errors'].append("Sheet configuration must be a dictionary")
            return result

        # Validate required modes
        required_modes = ["normal", "doubleup"]
        for mode in required_modes:
            if mode not in sheet_config:
                result['errors'].append(f"Missing sheet configuration for mode: {mode}")
                result['valid'] = False
                continue

            mode_config = sheet_config[mode]
            if not isinstance(mode_config, dict):
                result['errors'].append(f"Sheet configuration for mode '{mode}' must be a dictionary")
                result['valid'] = False
                continue

            # Validate required fields for this mode
            required_fields = [
                "header_line_num", "max_players", "discord_col",
                "ign_col", "registered_col", "checkin_col"
            ]

            if mode == "doubleup":
                required_fields.extend(["max_per_team", "team_col"])

            # Check for missing required fields
            missing_fields = [field for field in required_fields if field not in mode_config]
            if missing_fields:
                result['errors'].append(f"Mode '{mode}' missing required fields: {missing_fields}")
                result['valid'] = False

            # Validate numeric fields
            numeric_fields = ["header_line_num", "max_players"]
            if mode == "doubleup":
                numeric_fields.append("max_per_team")

            for field in numeric_fields:
                if field in mode_config:
                    value = mode_config[field]
                    if not isinstance(value, int) or value <= 0:
                        result['errors'].append(f"Mode '{mode}' field '{field}' must be a positive integer")
                        result['valid'] = False

            # Validate column specifications
            column_fields = [f for f in required_fields if f.endswith("_col")]
            for field in column_fields:
                if field in mode_config:
                    value = mode_config[field]
                    if not isinstance(value, str) or not value.strip():
                        result['errors'].append(f"Mode '{mode}' field '{field}' must be a non-empty string")
                        result['valid'] = False
                    elif not value.isalpha():
                        result['warnings'].append(f"Mode '{mode}' field '{field}' should contain only letters")

            # Validate sheet URL configuration
            has_sheet_url = "sheet_url" in mode_config
            has_prod_url = "prod_sheet_url" in mode_config
            has_test_url = "test_sheet_url" in mode_config

            if not (has_sheet_url or has_prod_url):
                result['errors'].append(
                    f"Mode '{mode}' must have either 'sheet_url' or 'prod_sheet_url'"
                )
                result['valid'] = False

            if not has_test_url:
                result['warnings'].append(f"Mode '{mode}' has no 'test_sheet_url' configured")

        return result

    @staticmethod
    def _validate_rich_presence(presence_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the rich presence configuration section.
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        if not isinstance(presence_config, dict):
            result['warnings'].append("Rich presence configuration should be a dictionary")
            return result

        # Validate presence type
        if "type" in presence_config:
            pres_type = presence_config["type"]
            valid_types = ["PLAYING", "LISTENING", "WATCHING", "STREAMING", "COMPETING"]

            if not isinstance(pres_type, str):
                result['warnings'].append("Rich presence type should be a string")
            elif pres_type.upper() not in valid_types:
                result['warnings'].append(
                    f"Rich presence type '{pres_type}' not recognized. Valid types: {valid_types}"
                )

        # Validate message
        if "message" in presence_config:
            message = presence_config["message"]
            if not isinstance(message, str):
                result['warnings'].append("Rich presence message should be a string")
            elif len(message.strip()) == 0:
                result['warnings'].append("Rich presence message should not be empty")
            elif len(message) > 128:
                result['warnings'].append("Rich presence message should be 128 characters or less")

        return result

    @staticmethod
    def get_command_help() -> Dict[str, str]:
        """
        Get command help descriptions from configuration with validation.
        """
        try:
            help_config = EMBEDS_CFG.get("help", {})
            commands = help_config.get("commands", {})

            if not isinstance(commands, dict):
                BotLogger.warning("Help commands configuration is not a dictionary", "CONFIG_MGR")
                return {}

            # Filter out non-string values
            valid_commands = {
                cmd: desc for cmd, desc in commands.items()
                if isinstance(cmd, str) and isinstance(desc, str)
            }

            if len(valid_commands) != len(commands):
                BotLogger.warning("Some help command entries were invalid and filtered out", "CONFIG_MGR")

            return valid_commands

        except Exception as e:
            BotLogger.error(f"Error getting command help configuration: {e}", "CONFIG_MGR")
            return {}

    @staticmethod
    def update_embed_template(key: str, **kwargs) -> bool:
        """
        Update an embed template in memory with validation.

        This method allows for dynamic embed updates without modifying the
        configuration file. Changes are temporary and will be lost on reload.
        """
        try:
            if key not in EMBEDS_CFG:
                EMBEDS_CFG[key] = {}
                BotLogger.info(f"Created new embed template: {key}", "CONFIG_MGR")

            valid_fields = ["title", "description", "color"]
            updated_fields = []

            for field, value in kwargs.items():
                if field in valid_fields:
                    if isinstance(value, str) or value is None:
                        EMBEDS_CFG[key][field] = value
                        updated_fields.append(field)
                    else:
                        BotLogger.warning(f"Invalid value type for embed field '{field}': {type(value)}", "CONFIG_MGR")
                else:
                    BotLogger.warning(f"Unknown embed field '{field}' ignored", "CONFIG_MGR")

            if updated_fields:
                BotLogger.info(f"Updated embed template '{key}' fields: {updated_fields}", "CONFIG_MGR")
                return True
            else:
                BotLogger.warning(f"No valid fields updated for embed template '{key}'", "CONFIG_MGR")
                return False

        except Exception as e:
            BotLogger.error(f"Error updating embed template '{key}': {e}", "CONFIG_MGR")
            return False

    @staticmethod
    async def reload_and_update_all(bot: discord.Client) -> Dict[str, Any]:
        """
        Reload configuration and update all dependent systems.

        This method performs a complete configuration reload and updates all
        systems that depend on configuration data, including embeds, presence,
        and any registered callbacks.
        """
        results = {
            "config_reload": False,
            "presence_update": False,
            "embeds_updated": {},
            "errors": [],
            "warnings": []
        }

        try:
            # Reload configuration
            BotLogger.info("Starting comprehensive configuration reload and update", "CONFIG_MGR")

            reload_success = ConfigManager.reload_config(create_backup=True)
            results["config_reload"] = reload_success

            if not reload_success:
                results["errors"].append("Configuration reload failed")
                return results

            # Update rich presence
            if bot:
                try:
                    presence_success = await ConfigManager.apply_rich_presence(bot)
                    results["presence_update"] = presence_success

                    if not presence_success:
                        results["warnings"].append("Rich presence update failed")

                except Exception as e:
                    results["errors"].append(f"Rich presence update error: {e}")
                    BotLogger.error(f"Rich presence update failed: {e}", "CONFIG_MGR")
            else:
                results["warnings"].append("No bot client provided for presence update")

            # Update embeds for all guilds
            if bot and hasattr(bot, 'guilds'):
                try:
                    from .embed_helpers import EmbedHelper

                    for guild in bot.guilds:
                        try:
                            guild_results = await EmbedHelper.update_all_guild_embeds(guild)
                            results["embeds_updated"][guild.name] = guild_results
                        except Exception as guild_error:
                            results["errors"].append(f"Embed update failed for guild {guild.name}: {guild_error}")
                            BotLogger.error(f"Embed update failed for guild {guild.name}: {guild_error}", "CONFIG_MGR")

                except ImportError:
                    results["warnings"].append("EmbedHelper not available for embed updates")
                except Exception as e:
                    results["errors"].append(f"Embed update error: {e}")
                    BotLogger.error(f"Embed update failed: {e}", "CONFIG_MGR")

            # Log overall results
            success_count = sum(1 for v in [
                results["config_reload"],
                results["presence_update"],
                bool(results["embeds_updated"])
            ] if v)

            BotLogger.info(
                f"Configuration reload and update completed: {success_count}/3 operations successful",
                "CONFIG_MGR"
            )

            if results["errors"]:
                BotLogger.warning(f"Errors during reload: {results['errors']}", "CONFIG_MGR")
            if results["warnings"]:
                BotLogger.info(f"Warnings during reload: {results['warnings']}", "CONFIG_MGR")

        except Exception as e:
            results["errors"].append(f"Critical error during reload and update: {e}")
            BotLogger.error(f"Critical error during configuration reload and update: {e}", "CONFIG_MGR")

        return results

    @staticmethod
    def get_configuration_info() -> Dict[str, Any]:
        """
        Get comprehensive information about the current configuration state.
        """
        try:
            config_path = ConfigManager._config_file_path

            info = {
                "file_path": config_path,
                "file_exists": os.path.exists(config_path),
                "last_modified": None,
                "last_validation": ConfigManager._last_validation,
                "sections": {},
                "validation_status": None,
                "backup_directory": ConfigManager._backup_directory
            }

            # File information
            if info["file_exists"]:
                info["last_modified"] = datetime.fromtimestamp(
                    ConfigManager._get_file_modification_time(config_path)
                ).isoformat()
                info["file_size"] = os.path.getsize(config_path)

            # Section information
            info["sections"] = {
                "total_sections": len(_FULL_CFG),
                "embeds_count": len(EMBEDS_CFG),
                "sheet_modes": list(SHEET_CONFIG.keys()),
                "has_rich_presence": "rich_presence" in _FULL_CFG
            }

            # Validation status
            validation_result = ConfigManager.validate_configuration()
            info["validation_status"] = {
                "valid": validation_result["valid"],
                "error_count": len(validation_result["errors"]),
                "warning_count": len(validation_result["warnings"])
            }

            # Backup information
            backup_dir = Path(ConfigManager._backup_directory)
            if backup_dir.exists():
                backup_files = list(backup_dir.glob("*_backup_*"))
                info["backup_count"] = len(backup_files)

                if backup_files:
                    latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
                    info["latest_backup"] = {
                        "file": latest_backup.name,
                        "created": datetime.fromtimestamp(latest_backup.stat().st_mtime).isoformat()
                    }
            else:
                info["backup_count"] = 0

            return info

        except Exception as e:
            BotLogger.error(f"Error getting configuration info: {e}", "CONFIG_MGR")
            return {"error": str(e)}

    @staticmethod
    def check_for_file_changes() -> bool:
        """
        Check if the configuration file has been modified since last load.
        """
        try:
            current_mtime = ConfigManager._get_file_modification_time(ConfigManager._config_file_path)
            return current_mtime > ConfigManager._last_modified
        except Exception as e:
            BotLogger.error(f"Error checking for file changes: {e}", "CONFIG_MGR")
            return False

    @staticmethod
    def export_configuration(export_path: str, format: str = "yaml") -> bool:
        """
        Export current configuration to a file.
        """
        try:
            format = format.lower()
            if format not in ["yaml", "json"]:
                raise ValueError(f"Unsupported export format: {format}")

            # Ensure directory exists
            export_dir = Path(export_path).parent
            export_dir.mkdir(parents=True, exist_ok=True)

            with open(export_path, "w", encoding="utf-8") as f:
                if format == "yaml":
                    yaml.dump(_FULL_CFG, f, default_flow_style=False, allow_unicode=True, indent=2)
                elif format == "json":
                    json.dump(_FULL_CFG, f, indent=2, ensure_ascii=False)

            BotLogger.info(f"Configuration exported to {export_path} in {format.upper()} format", "CONFIG_MGR")
            return True

        except Exception as e:
            BotLogger.error(f"Failed to export configuration: {e}", "CONFIG_MGR")
            return False


# Utility functions for backward compatibility and convenience

def reload_config(config_path: str = None) -> bool:
    """
    Convenience function for reloading configuration.
    """
    return ConfigManager.reload_config(config_path)


def get_embed_config(key: str) -> Dict[str, Any]:
    """
    Convenience function for getting embed configuration.
    """
    return ConfigManager.get_embed_config(key)


def get_sheet_config(mode: str, guild_id: str = None) -> Dict[str, Any]:
    """
    Convenience function for getting sheet configuration.
    """
    return ConfigManager.get_sheet_config(mode, guild_id)


# Export important classes and functions
__all__ = [
    # Main class
    'ConfigManager',

    # Exception classes
    'ConfigurationError',
    'ConfigurationValidationError',

    # Convenience functions
    'reload_config',
    'get_embed_config',
    'get_sheet_config'
]