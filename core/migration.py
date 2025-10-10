# core/migration.py

import logging
import os
from typing import Dict, Any, Optional, Tuple
import yaml

from config import _FULL_CFG, SHEET_CONFIG, load_config
from integrations.sheet_detector import get_column_mapping, save_column_mapping, ColumnMapping
from core.persistence import get_guild_data, update_guild_data, get_event_mode_for_guild, set_event_mode_for_guild


class ConfigMigrationError(Exception):
    """Exception for migration-related errors."""
    pass


class ConfigMigrator:
    """
    Handles migration from config.yaml column assignments to persistence system.
    """

    def __init__(self):
        self.migration_log = []

    def log(self, message: str):
        """Add a message to the migration log."""
        self.migration_log.append(message)
        logging.info(f"Migration: {message}")

    async def migrate_all_guilds(self) -> Dict[str, Any]:
        """
        Migrate all guild configurations from config.yaml to persistence.
        """
        results = {
            "migrated_guilds": [],
            "failed_guilds": [],
            "validation_errors": [],
            "config_cleaned": False
        }

        try:
            # Get all guilds that have data in persistence
            # For now, we'll migrate based on available sheet configurations
            await self._migrate_sheet_configurations(results)

            # Clean up config.yaml after successful migration
            if results["migrated_guilds"]:
                success = await self._cleanup_config_yaml()
                results["config_cleaned"] = success

            self.log(f"Migration completed. Migrated: {len(results['migrated_guilds'])}, Failed: {len(results['failed_guilds'])}")

            return results

        except Exception as e:
            error_msg = f"Migration failed: {e}"
            self.log(error_msg)
            raise ConfigMigrationError(error_msg)

    async def _migrate_sheet_configurations(self, results: Dict[str, Any]):
        """
        Migrate sheet configurations for both normal and doubleup modes.
        """
        modes = ["normal", "doubleup"]

        for mode in modes:
            if mode not in SHEET_CONFIG:
                self.log(f"Skipping {mode} mode - not found in config")
                continue

            mode_config = SHEET_CONFIG[mode]
            self.log(f"Processing {mode} mode configuration")

            # Create column mapping from config
            mapping = self._create_mapping_from_config(mode_config)

            if not self._validate_mapping(mapping, mode):
                self.log(f"Validation failed for {mode} mode configuration")
                results["validation_errors"].append(f"Invalid mapping for {mode} mode")
                continue

            # For migration purposes, we'll store this as a default mapping
            # Guilds will inherit these unless they have their own
            await self._store_default_mapping(mapping, mode, results)

    def _create_mapping_from_config(self, config: Dict[str, Any]) -> ColumnMapping:
        """
        Create a ColumnMapping object from config dictionary.
        """
        mapping = ColumnMapping()

        # Map config keys to mapping attributes
        column_mapping = {
            "discord_col": "discord_column",
            "ign_col": "ign_column",
            "alt_ign_col": "alt_ign_column",
            "pronouns_col": "pronouns_column",
            "registered_col": "registered_column",
            "checkin_col": "checkin_column",
            "team_col": "team_column"
        }

        for config_key, mapping_attr in column_mapping.items():
            if config_key in config:
                setattr(mapping, mapping_attr, config[config_key])

        return mapping

    def _validate_mapping(self, mapping: ColumnMapping, mode: str) -> bool:
        """
        Validate that a column mapping is complete and correct.
        """
        required_columns = ["discord_column", "ign_column", "registered_column", "checkin_column"]

        if mode == "doubleup":
            required_columns.append("team_column")

        # Check that all required columns are present
        for column in required_columns:
            value = getattr(mapping, column)
            if not value:
                self.log(f"Missing required column: {column}")
                return False

            # Validate column letter format
            if not value or not value[0].isalpha() or len(value) > 3:
                self.log(f"Invalid column format for {column}: {value}")
                return False

        return True

    async def _store_default_mapping(self, mapping: ColumnMapping, mode: str, results: Dict[str, Any]):
        """
        Store the mapping as a default for the mode.
        """
        try:
            # Store as a special default mapping that can be inherited
            default_data = {
                f"default_column_mapping_{mode}": {
                    "discord_column": mapping.discord_column,
                    "ign_column": mapping.ign_column,
                    "alt_ign_column": mapping.alt_ign_column,
                    "pronouns_column": mapping.pronouns_column,
                    "registered_column": mapping.registered_column,
                    "checkin_column": mapping.checkin_column,
                    "team_column": mapping.team_column,
                    "custom_columns": mapping.custom_columns
                }
            }

            # Store in a special "default" guild slot
            update_guild_data("default", default_data)

            self.log(f"Stored default {mode} mode column mapping")
            results["migrated_guilds"].append(f"default_{mode}")

        except Exception as e:
            error_msg = f"Failed to store default {mode} mapping: {e}"
            self.log(error_msg)
            results["failed_guilds"].append(error_msg)

    async def _cleanup_config_yaml(self) -> bool:
        """
        Remove column assignments from config.yaml after successful migration.
        """
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

            # Load current config
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # Backup the original config
            backup_path = config_path.replace(".yaml", "_pre_migration_backup.yaml")
            with open(backup_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            self.log(f"Created config backup: {backup_path}")

            # Remove column assignments from sheet configuration
            modified = False
            modes = ["normal", "doubleup"]

            for mode in modes:
                if mode in config_data.get("sheet_configuration", {}):
                    mode_config = config_data["sheet_configuration"][mode]

                    # List of column keys to remove
                    column_keys = [
                        "discord_col", "ign_col", "alt_ign_col", "pronouns_col",
                        "registered_col", "checkin_col", "team_col"
                    ]

                    for key in column_keys:
                        if key in mode_config:
                            del mode_config[key]
                            modified = True
                            self.log(f"Removed {key} from {mode} configuration")

            # Save modified config
            if modified:
                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

                self.log("Config.yaml cleaned up successfully")
                return True
            else:
                self.log("No column assignments found to clean up")
                return True

        except Exception as e:
            error_msg = f"Failed to cleanup config.yaml: {e}"
            self.log(error_msg)
            return False

    async def migrate_guild_specific(self, guild_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Migrate a specific guild's configuration.
        """
        results = {
            "guild_id": guild_id,
            "mapping_created": False,
            "validation_passed": False,
            "error": None
        }

        try:
            # Check if guild already has a mapping
            if not force_refresh:
                existing_mapping = await get_column_mapping(guild_id)
                if existing_mapping and (existing_mapping.discord_column or existing_mapping.ign_column):
                    self.log(f"Guild {guild_id} already has column mapping")
                    results["mapping_created"] = True
                    results["validation_passed"] = True
                    return results

            # Get guild's event mode
            mode = get_event_mode_for_guild(guild_id)

            # Get default mapping for this mode
            guild_data = get_guild_data("default")
            default_key = f"default_column_mapping_{mode}"
            default_mapping_data = guild_data.get(default_key, {})

            if not default_mapping_data:
                # Try to create from current config
                mode_config = SHEET_CONFIG.get(mode, {})
                mapping = self._create_mapping_from_config(mode_config)
            else:
                mapping = ColumnMapping(**default_mapping_data)

            # Validate the mapping
            if not self._validate_mapping(mapping, mode):
                results["error"] = f"Invalid column mapping for {mode} mode"
                return results

            # Save the mapping for this guild
            await save_column_mapping(guild_id, mapping)

            results["mapping_created"] = True
            results["validation_passed"] = True

            self.log(f"Successfully migrated guild {guild_id} to {mode} mode")

            return results

        except Exception as e:
            error_msg = f"Failed to migrate guild {guild_id}: {e}"
            self.log(error_msg)
            results["error"] = error_msg
            return results

    def get_migration_log(self) -> list:
        """
        Get the migration log.
        """
        return self.migration_log.copy()


# Global migrator instance
migrator = ConfigMigrator()


async def run_migration() -> Dict[str, Any]:
    """
    Run the complete migration process.
    """
    return await migrator.migrate_all_guilds()


async def migrate_guild(guild_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Migrate a specific guild.
    """
    return await migrator.migrate_guild_specific(guild_id, force_refresh)


def get_migration_status() -> Dict[str, Any]:
    """
    Get the current migration status.
    """
    return {
        "log": migrator.get_migration_log(),
        "has_default_mappings": bool(
            get_guild_data("default").get("default_column_mapping_normal") or
            get_guild_data("default").get("default_column_mapping_doubleup")
        )
    }


async def ensure_guild_migration(guild_id: str) -> bool:
    """
    Ensure a guild has been migrated, migrating if necessary.
    """
    # Check if guild already has mapping
    existing_mapping = await get_column_mapping(guild_id)
    if existing_mapping and (existing_mapping.discord_column or existing_mapping.ign_column):
        return True

    # Migrate the guild
    result = await migrate_guild(guild_id)
    return result.get("validation_passed", False)