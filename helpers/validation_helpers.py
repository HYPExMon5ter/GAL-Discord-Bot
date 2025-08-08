# helpers/validation_helpers.py

from typing import Optional, List, Dict, Any, Tuple
import discord
from config import embed_from_cfg, get_sheet_settings
from core.persistence import get_event_mode_for_guild
from .logging_helper import BotLogger
from .error_handler import ErrorHandler, ErrorCategory, ErrorContext, ErrorSeverity


class ValidationError:
    """
    Represents a validation error with an associated Discord embed.

    This class encapsulates validation failures and provides a consistent
    way to generate user-friendly error messages.
    """

    def __init__(self, embed_key: str, **kwargs):
        """Initialize validation error with embed configuration."""
        self.embed_key = embed_key
        self.kwargs = kwargs

    def to_embed(self) -> discord.Embed:
        """Convert validation error to Discord embed."""
        try:
            return embed_from_cfg(self.embed_key, **self.kwargs)
        except Exception as e:
            error_context = ErrorContext(
                error=e,
                operation="create_validation_embed",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.MEDIUM,
                additional_context={
                    "embed_key": self.embed_key,
                    "kwargs": self.kwargs
                }
            )
            BotLogger.error(f"Failed to create embed for {self.embed_key}: {e}", "VALIDATION")

            # Fallback embed
            return discord.Embed(
                title="❌ Validation Error",
                description=f"An error occurred during validation (embed key: {self.embed_key})",
                color=discord.Color.red()
            )

    def __str__(self) -> str:
        """String representation for logging."""
        return f"ValidationError({self.embed_key}, {self.kwargs})"


class ValidationResult:
    """
    Enhanced result of validation with context and metadata.

    Provides detailed information about validation outcomes including
    success/failure status, error details, context data, and warnings.
    """

    def __init__(
            self,
            is_valid: bool,
            error: Optional[ValidationError] = None,
            context: Optional[Dict[str, Any]] = None,
            warnings: Optional[List[str]] = None
    ):
        """Initialize validation result."""
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
    def validate_channel_state(
            guild: discord.Guild,
            channel_name: str,
            required_state: str = "exists"
    ) -> ValidationResult:
        """
        Validate channel state and accessibility.
        """
        try:
            # Find the channel
            channel = discord.utils.get(guild.text_channels, name=channel_name)

            if required_state == "exists" and not channel:
                return ValidationResult(
                    False,
                    ValidationError("channel_not_found", channel=channel_name),
                    {"channel_name": channel_name, "guild_id": guild.id}
                )

            if required_state == "not_exists" and channel:
                return ValidationResult(
                    False,
                    ValidationError("channel_already_exists", channel=channel_name),
                    {"channel_name": channel_name, "channel_id": channel.id}
                )

            # Check bot permissions if channel exists
            if channel and guild.me:
                permissions = channel.permissions_for(guild.me)

                missing_permissions = []
                required_perms = {
                    "send_messages": permissions.send_messages,
                    "embed_links": permissions.embed_links,
                    "manage_messages": permissions.manage_messages
                }

                for perm_name, has_perm in required_perms.items():
                    if not has_perm:
                        missing_permissions.append(perm_name)

                if missing_permissions:
                    return ValidationResult(
                        False,
                        ValidationError(
                            "insufficient_channel_permissions",
                            channel=channel_name,
                            permissions=", ".join(missing_permissions)
                        ),
                        {
                            "channel_id": channel.id,
                            "missing_permissions": missing_permissions
                        }
                    )

            return ValidationResult(
                True,
                context={
                    "channel_name": channel_name,
                    "channel_id": channel.id if channel else None,
                    "channel_exists": channel is not None
                }
            )

        except Exception as e:
            BotLogger.error(f"Error validating channel state: {e}", "VALIDATION")
            return ValidationResult(
                False,
                ValidationError("channel_validation_error", channel=channel_name),
                {"error": str(e)}
            )

    @staticmethod
    async def validate_and_respond_batch(
            interaction: discord.Interaction,
            validation_results: List[ValidationResult]
    ) -> bool:
        """
        Validate a batch of results and respond with errors if needed.
        """
        try:
            # Find first failed validation
            failed_validation = None
            for result in validation_results:
                if not result.is_valid:
                    failed_validation = result
                    break

            # If all validations passed
            if not failed_validation:
                return True

            # Send error response
            if failed_validation.error:
                embed = failed_validation.error.to_embed()

                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    else:
                        await interaction.followup.send(embed=embed, ephemeral=True)
                except Exception as e:
                    BotLogger.error(f"Error sending validation error response: {e}", "VALIDATION")

            return False

        except Exception as e:
            BotLogger.error(f"Error in validate_and_respond_batch: {e}", "VALIDATION")

            # Try to send generic error
            try:
                error_embed = discord.Embed(
                    title="❌ Validation Error",
                    description="An error occurred during validation. Please try again.",
                    color=discord.Color.red()
                )

                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            except:
                pass

            return False

    @staticmethod
    def validate_team_capacity(
            guild_id: str,
            team_name: str = None,
            operation: str = "join"
    ) -> ValidationResult:
        """
        Validate team capacity and availability for team-based events.
        """
        try:
            # Get event mode
            event_mode = get_event_mode_for_guild(guild_id)

            # Only validate for team-based modes
            if event_mode not in ["double_up", "team_based"]:
                return ValidationResult(True, context={"event_mode": event_mode})

            # Get team settings
            sheet_settings = get_sheet_settings()
            max_team_size = sheet_settings.get("max_team_size", 2)

            # If no specific team, just return capacity info
            if not team_name:
                return ValidationResult(
                    True,
                    context={
                        "max_team_size": max_team_size,
                        "event_mode": event_mode
                    }
                )

            # For specific team validation, would need to check current team members
            # This would require integration with sheet operations

            return ValidationResult(
                True,
                context={
                    "team_name": team_name,
                    "max_team_size": max_team_size,
                    "event_mode": event_mode
                }
            )

        except Exception as e:
            BotLogger.error(f"Error validating team capacity: {e}", "VALIDATION")
            return ValidationResult(
                False,
                ValidationError("team_validation_error"),
                {"error": str(e)}
            )

    @staticmethod
    def health_check() -> bool:
        """Perform health check on validation system."""
        try:
            # Test basic validation functionality
            test_embed_key = "test_validation"
            test_error = ValidationError(test_embed_key, test="value")

            # Test result creation
            test_result = ValidationResult(True, context={"test": True})

            return True

        except Exception as e:
            BotLogger.error(f"Validation health check failed: {e}", "VALIDATION")
            return False


# Convenience function for single validation
async def validate_and_respond(interaction: discord.Interaction, validation_result: ValidationResult) -> bool:
    """Validate a single result and respond with errors if needed."""
    return await Validators.validate_and_respond_batch(interaction, [validation_result])


# Export all important classes and functions
__all__ = [
    'Validators',
    'ValidationError',
    'ValidationResult',
    'validate_and_respond'
]