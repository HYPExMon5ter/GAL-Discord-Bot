# helpers/schedule_helpers.py

import logging
from datetime import datetime
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from core.persistence import get_schedule


class ScheduleHelper:
    """Helper class for managing scheduled times for registration and check-in."""

    @staticmethod
    def parse_schedule_time(time_iso: Optional[str], system_name: str) -> Optional[int]:
        """
        Parse an ISO format datetime string and return a Unix timestamp.
        
        Args:
            time_iso: ISO format datetime string
            system_name: Name for logging (e.g., "registration open", "checkin close")
        
        Returns:
            Unix timestamp as integer, or None if parsing fails
        """
        if not time_iso:
            return None

        try:
            parsed_time = datetime.fromisoformat(time_iso)
            # Ensure timezone awareness
            if parsed_time.tzinfo is None:
                parsed_time = parsed_time.replace(tzinfo=ZoneInfo("UTC"))
            return int(parsed_time.timestamp())
        except Exception as e:
            logging.warning(f"Failed to parse {system_name} time '{time_iso}': {e}")
            return None

    @staticmethod
    def get_all_schedule_times(guild_id: int) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
        """
        Get all scheduled times for a guild.
        
        Returns:
            Tuple of (reg_open_ts, reg_close_ts, ci_open_ts, ci_close_ts)
        """
        # Get scheduled times from persistence
        reg_open_iso = get_schedule(guild_id, "registration_open")
        reg_close_iso = get_schedule(guild_id, "registration_close")
        ci_open_iso = get_schedule(guild_id, "checkin_open")
        ci_close_iso = get_schedule(guild_id, "checkin_close")

        # Parse all times
        reg_open_ts = ScheduleHelper.parse_schedule_time(reg_open_iso, "registration open")
        reg_close_ts = ScheduleHelper.parse_schedule_time(reg_close_iso, "registration close")
        ci_open_ts = ScheduleHelper.parse_schedule_time(ci_open_iso, "checkin open")
        ci_close_ts = ScheduleHelper.parse_schedule_time(ci_close_iso, "checkin close")

        return reg_open_ts, reg_close_ts, ci_open_ts, ci_close_ts

    @staticmethod
    def validate_schedule_times(reg_open_ts: Optional[int], reg_close_ts: Optional[int],
                                ci_open_ts: Optional[int], ci_close_ts: Optional[int]) -> dict:
        """
        Validate scheduled times for logical consistency.
        
        Returns:
            Dictionary with validation results and warnings
        """
        warnings = []

        # Check if registration close is before registration open
        if reg_open_ts and reg_close_ts and reg_close_ts <= reg_open_ts:
            warnings.append("Registration close time is before or same as open time")

        # Check if checkin open is before registration close (common pattern)
        if reg_close_ts and ci_open_ts and ci_open_ts < reg_close_ts:
            warnings.append("Check-in opens before registration closes - users may not be able to register first")

        # Check if checkin close is before checkin open
        if ci_open_ts and ci_close_ts and ci_close_ts <= ci_open_ts:
            warnings.append("Check-in close time is before or same as open time")

        # Check for times in the past (but only warn if they're more than 5 minutes past to avoid spam)
        now = datetime.now(ZoneInfo("UTC")).timestamp()
        grace_period = 300  # 5 minutes

        if reg_open_ts and reg_open_ts < (now - grace_period):
            warnings.append("Registration open time is significantly in the past")
        if reg_close_ts and reg_close_ts < (now - grace_period):
            warnings.append("Registration close time is significantly in the past")
        if ci_open_ts and ci_open_ts < (now - grace_period):
            warnings.append("Check-in open time is significantly in the past")
        if ci_close_ts and ci_close_ts < (now - grace_period):
            warnings.append("Check-in close time is significantly in the past")

        return {
            "is_valid": len(warnings) == 0,
            "warnings": warnings
        }
