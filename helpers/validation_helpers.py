# helpers/validation_helpers.py

"""
Validation helpers for Discord bot operations.

This module provides comprehensive validation functionality for all bot operations
including permissions, capacity, team management, and data integrity checks.
"""

import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timezone
from enum import Enum

import discord

# Import configuration and utilities
from config import (
    REGISTERED_ROLE,
    CHECKED_IN_ROLE,
    CHECK_IN_CHANNEL,
    REGISTRATION_CHANNEL,
    ANGEL_ROLE,
    get_sheet_settings
)

# Import logging helper
from .logging_helper import BotLogger

# Import necessary utilities
try:
    from utils.utils import (
        get_event_mode_for_guild,
        has_allowed_role
    )
except ImportError:
    BotLogger.warning("Some utilities not available for validation", "VALIDATION")


    def get_event_mode_for_guild(guild_id: str) -> str:
        return "normal"


    def has_allowed_role(member: discord.Member, required_permissions: List[str] = None) -> bool:
        return False


class ValidationErrorType(Enum):
    """Enumeration of validation error types for consistent handling."""

    # Permission errors
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    DM_NOT_ALLOWED = "dm_not_allowed"
    MEMBER_NOT_FOUND = "member_not_found"

    # Capacity errors
    REGISTRATION_FULL = "registration_full"
    TEAM_FULL = "team_full"
    REGISTRATION_CLOSED = "registration_closed"
    CHECKIN_CLOSED = "checkin_closed"

    # Status errors
    ALREADY_REGISTERED = "already_registered"
    NOT_REGISTERED = "not_registered"
    ALREADY_CHECKED_IN = "already_checked_in"
    NOT_CHECKED_IN = "not_checked_in"

    # Channel errors
    CHANNEL_NOT_FOUND = "channel_not_found"
    CHANNEL_NOT_ACCESSIBLE = "channel_not_accessible"

    # Data errors
    INVALID_DATA = "invalid_data"
    SHEETS_UNAVAILABLE = "sheets_unavailable"

    # System errors
    VALIDATION_ERROR = "validation_error"
    CAPACITY_CHECK_FAILED = "capacity_check_failed"
    STATUS_CHECK_FAILED = "status_check_failed"


class ValidationError:
    """
    Structured validation error with context and formatting support.
    """

    def __init__(self, error_type: str, **kwargs):
        """
        Initialize validation error with type and context.

        Args:
            error_type: Type of validation error
            **kwargs: Additional context for error formatting
        """
        self.error_type = error_type
        self.context = kwargs
        self.timestamp = datetime.now(timezone.utc)

        # Generate user-friendly message
        self.message = self._generate_message()

    def _generate_message(self) -> str:
        """Generate user-friendly error message based on type and context."""
        messages = {
            "insufficient_permissions": "You don't have permission to use this command.",
            "dm_not_allowed": "This command cannot be used in DMs.",
            "member_not_found": "Member not found in this server.",
            "registration_full": "Registration is full ({current}/{max} players).",
            "team_full": "Team '{team}' is full.",
            "registration_closed": "Registration is currently closed.",
            "checkin_closed": "Check-in is currently closed.",
            "already_registered": "{user} is already registered.",
            "not_registered": "{user} is not registered.",
            "already_checked_in": "{user} is already checked in.",
            "not_checked_in": "{user} is not checked in.",
            "channel_not_found": "Channel '{channel}' not found.",
            "channel_not_accessible": "Channel '{channel}' is not accessible.",
            "invalid_data": "Invalid data provided: {reason}",
            "sheets_unavailable": "Google Sheets is currently unavailable.",
            "validation_error": "Validation failed: {reason}",
            "capacity_check_failed": "Failed to check capacity.",
            "status_check_failed": "Failed to check user status.",
            "invalid_interaction": "Invalid interaction.",
            "invalid_status_registered": "{user} must be registered first.",
            "invalid_status_unregistered": "{user} is already registered.",
            "invalid_status_checked_in": "{user} is already checked in.",
            "invalid_status_checked_out": "{user} must be checked in first."
        }

        template = messages.get(self.error_type, "An error occurred: {error_type}")

        try:
            return template.format(error_type=self.error_type, **self.context)
        except KeyError:
            return f"Validation error: {self.error_type}"

    def __str__(self) -> str:
        return self.message


class ValidationResult:
    """
    Result of a validation operation with status and context.
    """

    def __init__(
            self,
            is_valid: bool,
            error: Optional[ValidationError] = None,
            context: Optional[Dict[str, Any]] = None,
            warnings: Optional[List[str]] = None
    ):
        """
        Initialize validation result.

        Args:
            is_valid: Whether validation passed
            error: Validation error if failed
            context: Additional context data
            warnings: Non-critical warnings
        """
        self.is_valid = is_valid
        self.error = error
        self.context = context or {}
        self.warnings = warnings or []

        # Add metadata
        self.validation_time = discord.utils.utcnow()

        if not is_valid and error:
            BotLogger.debug(f"Validation failed: {error}", "VALIDATION")

    def __bool__(self) -> bool:
        """Allow boolean evaluation of validation result."""
        return self.is_valid


class Validators:
    """
    Comprehensive validation system for Discord bot operations.

    This class provides static methods for all types of validation including
    permissions, capacity, team management, and data integrity checks.
    All methods return ValidationResult objects for consistent handling.
    """

    @staticmethod
    def validate_member_permissions(
            interaction: discord.Interaction,
            required_permissions: List[str] = None
    ) -> ValidationResult:
        """
        Validate that a member has the required permissions to perform an action.
        """
        try:
            # Check if interaction is valid
            if not interaction or not interaction.user:
                return ValidationResult(
                    False,
                    ValidationError("invalid_interaction"),
                    {"reason": "No user in interaction"}
                )

            # Handle DM interactions (usually not allowed for admin commands)
            if not interaction.guild:
                return ValidationResult(
                    False,
                    ValidationError("dm_not_allowed"),
                    {"reason": "Command not available in DMs"}
                )

            # Get member object
            member = None
            if isinstance(interaction.user, discord.Member):
                member = interaction.user
            else:
                member = interaction.guild.get_member(interaction.user.id)

            if not member:
                return ValidationResult(
                    False,
                    ValidationError("member_not_found"),
                    {"user_id": interaction.user.id, "guild_id": interaction.guild.id}
                )

            # Check for required permissions (using utils function)
            from utils.utils import has_allowed_role

            if not has_allowed_role(member, required_permissions):
                return ValidationResult(
                    False,
                    ValidationError("insufficient_permissions", member=member.display_name),
                    {"member_id": member.id, "required_permissions": required_permissions}
                )

            return ValidationResult(
                True,
                context={
                    "member_id": member.id,
                    "member_name": member.display_name,
                    "guild_id": interaction.guild.id
                }
            )

        except Exception as e:
            BotLogger.error(f"Error validating member permissions: {e}", "VALIDATION")
            return ValidationResult(
                False,
                ValidationError("validation_error"),
                {"error": str(e)}
            )

    @staticmethod
    async def validate_registration_capacity(
            guild: discord.Guild,
            operation: str = "register"
    ) -> ValidationResult:
        """
        Validate that registration capacity allows for the requested operation.
        """
        try:
            # Get current registration data
            from helpers.sheet_helpers import SheetOperations

            if not SheetOperations:
                return ValidationResult(
                    False,
                    ValidationError("sheets_unavailable"),
                    {"reason": "Sheet operations not available"}
                )

            # Get registered users count
            registered_users = await SheetOperations.get_all_registered_users(str(guild.id))
            current_count = len(registered_users)

            # Get capacity settings
            sheet_settings = get_sheet_settings()
            max_capacity = sheet_settings.get("max_registration_capacity", 100)

            # Check if registration is open
            event_mode = get_event_mode_for_guild(str(guild.id))
            if event_mode != "registration" and operation == "register":
                return ValidationResult(
                    False,
                    ValidationError("registration_closed"),
                    {"current_mode": event_mode}
                )

            # Check capacity for new registrations
            if operation == "register" and current_count >= max_capacity:
                return ValidationResult(
                    False,
                    ValidationError("registration_full", current=current_count, max=max_capacity),
                    {"current_count": current_count, "max_capacity": max_capacity}
                )

            return ValidationResult(
                True,
                context={
                    "current_count": current_count,
                    "max_capacity": max_capacity,
                    "event_mode": event_mode,
                    "available_spots": max_capacity - current_count
                }
            )

        except Exception as e:
            BotLogger.error(f"Error validating registration capacity: {e}", "VALIDATION")
            return ValidationResult(
                False,
                ValidationError("capacity_check_failed"),
                {"error": str(e)}
            )

    @staticmethod
    async def validate_user_registration_status(
            guild: discord.Guild,
            user: discord.User,
            expected_status: str = "any"
    ) -> ValidationResult:
        """
        Validate user's current registration status.

        Args:
            guild: Discord guild
            user: Discord user to validate
            expected_status: Expected status ("any", "registered", "unregistered", "checked_in", "checked_out")

        Returns:
            ValidationResult with status information
        """
        try:
            # Get user's current status from sheets
            from helpers.sheet_helpers import SheetOperations

            if not SheetOperations:
                return ValidationResult(
                    False,
                    ValidationError("sheets_unavailable"),
                    {"reason": "Sheet operations not available"}
                )

            user_data = await SheetOperations.get_user_data(str(guild.id), f"{user.name}#{user.discriminator}")

            # Determine current status
            is_registered = user_data and len(user_data) >= 3 and SheetOperations._is_true(user_data[2])
            is_checked_in = user_data and len(user_data) >= 4 and SheetOperations._is_true(user_data[3])

            current_status = "unregistered"
            if is_registered and is_checked_in:
                current_status = "checked_in"
            elif is_registered:
                current_status = "registered"

            # Validate against expected status
            status_valid = True
            if expected_status != "any":
                if expected_status == "registered" and not is_registered:
                    status_valid = False
                elif expected_status == "unregistered" and is_registered:
                    status_valid = False
                elif expected_status == "checked_in" and not is_checked_in:
                    status_valid = False
                elif expected_status == "checked_out" and is_checked_in:
                    status_valid = False

            if not status_valid:
                return ValidationResult(
                    False,
                    ValidationError(
                        f"invalid_status_{expected_status}",
                        user=user.display_name,
                        current_status=current_status,
                        expected=expected_status
                    ),
                    {
                        "user_id": user.id,
                        "current_status": current_status,
                        "expected_status": expected_status
                    }
                )

            return ValidationResult(
                True,
                context={
                    "user_id": user.id,
                    "current_status": current_status,
                    "is_registered": is_registered,
                    "is_checked_in": is_checked_in,
                    "user_data": user_data
                }
            )

        except Exception as e:
            BotLogger.error(f"Error validating user registration status: {e}", "VALIDATION")
            return ValidationResult(
                False,
                ValidationError("status_check_failed", user=user.display_name),
                {"error": str(e)}
            )

    @staticmethod
    def validate_registration_status(member: discord.Member, require_registered: bool = False) -> bool:
        """
        Simple validation for registration status using Discord roles.

        This is a convenience method that checks Discord roles for quick validation.
        For comprehensive validation with sheet data, use validate_user_registration_status.

        Args:
            member: Discord member to check
            require_registered: If True, validates that user IS registered; if False, validates they are NOT registered

        Returns:
            True if validation passes, False otherwise
        """
        try:
            reg_role = discord.utils.get(member.guild.roles, name=REGISTERED_ROLE)
            if not reg_role:
                BotLogger.warning(f"Registered role not found in guild {member.guild.name}", "VALIDATION")
                return not require_registered  # If role doesn't exist, consider unregistered

            is_registered = reg_role in member.roles

            if require_registered:
                # User should be registered
                return is_registered
            else:
                # User should NOT be registered
                return not is_registered

        except Exception as e:
            BotLogger.error(f"Error in validate_registration_status: {e}", "VALIDATION")
            return False

    @staticmethod
    def validate_checkin_status(member: discord.Member, require_not_checked_in: bool = False) -> bool:
        """
        Simple validation for check-in status using Discord roles.

        This is a convenience method that checks Discord roles for quick validation.

        Args:
            member: Discord member to check
            require_not_checked_in: If True, validates user is NOT checked in; if False, validates they ARE checked in

        Returns:
            True if validation passes, False otherwise
        """
        try:
            ci_role = discord.utils.get(member.guild.roles, name=CHECKED_IN_ROLE)
            if not ci_role:
                BotLogger.warning(f"Checked-in role not found in guild {member.guild.name}", "VALIDATION")
                return require_not_checked_in  # If role doesn't exist, consider not checked in

            is_checked_in = ci_role in member.roles

            if require_not_checked_in:
                # User should NOT be checked in
                return not is_checked_in
            else:
                # User should be checked in
                return is_checked_in

        except Exception as e:
            BotLogger.error(f"Error in validate_checkin_status: {e}", "VALIDATION")
            return False

    @staticmethod
    async def validate_and_respond(interaction: discord.Interaction, *validations: bool) -> bool:
        """
        Validate multiple conditions and respond with appropriate error if any fail.

        This is a convenience method for simple boolean validations.

        Args:
            interaction: Discord interaction for response
            *validations: Boolean validation results

        Returns:
            True if all validations pass, False otherwise
        """
        try:
            # Check if all validations passed
            if all(validations):
                return True

            # Find which validation failed (for logging)
            for i, validation in enumerate(validations):
                if not validation:
                    BotLogger.debug(f"Validation {i + 1} failed", "VALIDATION")
                    break

            # Send generic error response
            from config import embed_from_cfg
            embed = embed_from_cfg("validation_failed")

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

            return False

        except Exception as e:
            BotLogger.error(f"Error in validate_and_respond: {e}", "VALIDATION")
            return False

    @staticmethod
    def validate_channel_state(
            guild: discord.Guild,
            channel_name: str,
            required_state: str = "exists"
    ) -> ValidationResult:
        """
        Validate channel state and accessibility.

        Args:
            guild: Discord guild
            channel_name: Name of channel to validate
            required_state: Required state ("exists", "open", "closed")

        Returns:
            ValidationResult with channel state information
        """
        try:
            # Find channel
            channel = discord.utils.get(guild.text_channels, name=channel_name)

            if not channel:
                return ValidationResult(
                    False,
                    ValidationError("channel_not_found", channel=channel_name),
                    {"channel_name": channel_name}
                )

            # Check channel state
            if required_state == "exists":
                # Just needs to exist
                return ValidationResult(
                    True,
                    context={"channel_id": channel.id, "channel_name": channel.name}
                )

            # Check if channel is open/closed (based on role permissions)
            role_name = REGISTERED_ROLE if channel_name == CHECK_IN_CHANNEL else ANGEL_ROLE
            role = discord.utils.get(guild.roles, name=role_name)

            if not role:
                return ValidationResult(
                    False,
                    ValidationError("validation_error", reason=f"Role {role_name} not found"),
                    {"role_name": role_name}
                )

            overwrites = channel.overwrites_for(role)
            is_open = overwrites.view_channel

            if required_state == "open" and not is_open:
                return ValidationResult(
                    False,
                    ValidationError("channel_not_accessible", channel=channel_name),
                    {"channel_name": channel_name, "is_open": is_open}
                )
            elif required_state == "closed" and is_open:
                return ValidationResult(
                    False,
                    ValidationError("validation_error", reason=f"Channel {channel_name} is open"),
                    {"channel_name": channel_name, "is_open": is_open}
                )

            return ValidationResult(
                True,
                context={
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "is_open": is_open
                }
            )

        except Exception as e:
            BotLogger.error(f"Error validating channel state: {e}", "VALIDATION")
            return ValidationResult(
                False,
                ValidationError("validation_error"),
                {"error": str(e)}
            )

    @staticmethod
    async def validate_and_respond_batch(
            interaction: discord.Interaction,
            validations: List[ValidationResult]
    ) -> bool:
        """
        Process multiple ValidationResult objects and respond appropriately.

        Args:
            interaction: Discord interaction for response
            validations: List of ValidationResult objects

        Returns:
            True if all validations passed, False otherwise
        """
        try:
            # Check if all validations passed
            all_valid = all(v.is_valid for v in validations)

            if all_valid:
                return True

            # Find first error
            first_error = None
            for validation in validations:
                if not validation.is_valid and validation.error:
                    first_error = validation.error
                    break

            # Send error response
            from config import embed_from_cfg

            if first_error:
                # Try to use specific error embed
                embed_key = first_error.error_type
                try:
                    embed = embed_from_cfg(embed_key, **first_error.context)
                except:
                    # Fall back to generic error
                    embed = embed_from_cfg("error", message=str(first_error))
            else:
                embed = embed_from_cfg("validation_failed")

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)

            return False

        except Exception as e:
            BotLogger.error(f"Error in validate_and_respond_batch: {e}", "VALIDATION")
            return False


# Validation utility functions
async def validate_registration_prerequisites(
        interaction: discord.Interaction,
        member: discord.Member = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate all prerequisites for registration.

    Returns:
        Tuple of (success, error_message)
    """
    try:
        member = member or interaction.user
        guild = interaction.guild

        # Check if registration is open
        channel_validation = Validators.validate_channel_state(
            guild,
            REGISTRATION_CHANNEL,
            "open"
        )

        if not channel_validation.is_valid:
            return False, "Registration is currently closed."

        # Check if user is already registered
        if not Validators.validate_registration_status(member, require_registered=False):
            return False, "You are already registered."

        # Check capacity
        capacity_validation = await Validators.validate_registration_capacity(guild)
        if not capacity_validation.is_valid:
            return False, capacity_validation.error.message

        return True, None

    except Exception as e:
        BotLogger.error(f"Error validating registration prerequisites: {e}", "VALIDATION")
        return False, "Failed to validate registration requirements."


async def validate_checkin_prerequisites(
        interaction: discord.Interaction,
        member: discord.Member = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate all prerequisites for check-in.

    Returns:
        Tuple of (success, error_message)
    """
    try:
        member = member or interaction.user
        guild = interaction.guild

        # Check if check-in is open
        channel_validation = Validators.validate_channel_state(
            guild,
            CHECK_IN_CHANNEL,
            "open"
        )

        if not channel_validation.is_valid:
            return False, "Check-in is currently closed."

        # Check if user is registered
        if not Validators.validate_registration_status(member, require_registered=True):
            return False, "You must be registered before checking in."

        # Check if user is already checked in
        if not Validators.validate_checkin_status(member, require_not_checked_in=True):
            return False, "You are already checked in."

        return True, None

    except Exception as e:
        BotLogger.error(f"Error validating check-in prerequisites: {e}", "VALIDATION")
        return False, "Failed to validate check-in requirements."


# Module health check
def validate_validators_health() -> Dict[str, Any]:
    """
    Validate the health of the validators module.

    Returns:
        Dictionary with health status information
    """
    health = {
        "status": True,
        "validators_available": True,
        "error_types": len(ValidationErrorType.__members__),
        "methods": []
    }

    # Check available validator methods
    validator_methods = [
        "validate_member_permissions",
        "validate_registration_capacity",
        "validate_user_registration_status",
        "validate_registration_status",
        "validate_checkin_status",
        "validate_and_respond",
        "validate_channel_state",
        "validate_and_respond_batch"
    ]

    for method in validator_methods:
        if hasattr(Validators, method):
            health["methods"].append(method)

    health["method_count"] = len(health["methods"])

    return health


# Export important classes and functions
__all__ = [
    "Validators",
    "ValidationResult",
    "ValidationError",
    "ValidationErrorType",
    "validate_registration_prerequisites",
    "validate_checkin_prerequisites",
    "validate_validators_health"
]