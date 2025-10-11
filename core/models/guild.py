"""
Guild data models.

Defines Discord guild (server) related entities and their configurations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .base_model import BaseModel


@dataclass
class GuildConfiguration(BaseModel):
    """Configuration settings for a Discord guild."""
    
    guild_id: str
    name: str
    prefix: str = "!"
    timezone: str = "UTC"
    locale: str = "en-US"
    admin_roles: List[str] = field(default_factory=list)
    moderator_roles: List[str] = field(default_factory=list)
    member_roles: List[str] = field(default_factory=list)
    welcome_message: Optional[str] = None
    welcome_channel_id: Optional[str] = None
    rules_channel_id: Optional[str] = None
    announcements_channel_id: Optional[str] = None
    tournament_channels: List[str] = field(default_factory=list)
    logging_channel_id: Optional[str] = None
    auto_roles_enabled: bool = False
    auto_role_ids: List[str] = field(default_factory=list)
    moderation_enabled: bool = True
    welcome_enabled: bool = False
    level_system_enabled: bool = False
    custom_commands: Dict[str, str] = field(default_factory=dict)
    embed_color: str = "#0099ff"  # Default Discord blue
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate guild configuration data."""
        if not self.guild_id:
            raise ValueError("Guild ID is required")
        if not self.name:
            raise ValueError("Guild name is required")
        if not self.prefix:
            raise ValueError("Command prefix cannot be empty")
        if len(self.prefix) > 5:
            raise ValueError("Command prefix too long (max 5 characters)")
    
    def is_admin_role(self, role_id: str) -> bool:
        """Check if a role ID is in the admin roles list."""
        return role_id in self.admin_roles
    
    def is_moderator_role(self, role_id: str) -> bool:
        """Check if a role ID is in the moderator roles list."""
        return role_id in self.moderator_roles
    
    def add_admin_role(self, role_id: str) -> None:
        """Add an admin role."""
        if role_id not in self.admin_roles:
            self.admin_roles.append(role_id)
            self.update_timestamp()
    
    def remove_admin_role(self, role_id: str) -> None:
        """Remove an admin role."""
        if role_id in self.admin_roles:
            self.admin_roles.remove(role_id)
            self.update_timestamp()
    
    def add_moderator_role(self, role_id: str) -> None:
        """Add a moderator role."""
        if role_id not in self.moderator_roles:
            self.moderator_roles.append(role_id)
            self.update_timestamp()
    
    def remove_moderator_role(self, role_id: str) -> None:
        """Remove a moderator role."""
        if role_id in self.moderator_roles:
            self.moderator_roles.remove(role_id)
            self.update_timestamp()
    
    def add_tournament_channel(self, channel_id: str) -> None:
        """Add a tournament channel."""
        if channel_id not in self.tournament_channels:
            self.tournament_channels.append(channel_id)
            self.update_timestamp()
    
    def remove_tournament_channel(self, channel_id: str) -> None:
        """Remove a tournament channel."""
        if channel_id in self.tournament_channels:
            self.tournament_channels.remove(channel_id)
            self.update_timestamp()
    
    def set_custom_command(self, name: str, response: str) -> None:
        """Set a custom command."""
        self.custom_commands[name] = response
        self.update_timestamp()
    
    def remove_custom_command(self, name: str) -> None:
        """Remove a custom command."""
        if name in self.custom_commands:
            del self.custom_commands[name]
            self.update_timestamp()


@dataclass
class Guild(BaseModel):
    """Represents a Discord guild (server)."""
    
    discord_id: str
    name: str
    owner_id: str
    member_count: int = 0
    icon_url: Optional[str] = None
    description: Optional[str] = None
    features: List[str] = field(default_factory=list)
    boosted: bool = False
    boost_level: int = 0
    is_active: bool = True
    joined_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    last_activity: Optional[datetime] = field(default_factory=datetime.utcnow)
    
    # Configuration
    configuration: Optional[GuildConfiguration] = None
    
    # Statistics
    message_count: int = 0
    command_usage: Dict[str, int] = field(default_factory=dict)
    active_users_24h: int = 0
    active_users_7d: int = 0
    
    # Custom fields
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate guild data."""
        if not self.discord_id:
            raise ValueError("Discord ID is required")
        if not self.name:
            raise ValueError("Guild name is required")
        if not self.owner_id:
            raise ValueError("Owner ID is required")
        if self.member_count < 0:
            raise ValueError("Member count cannot be negative")
        if self.boost_level < 0 or self.boost_level > 3:
            raise ValueError("Boost level must be between 0 and 3")
    
    def update_member_count(self, count: int) -> None:
        """Update the member count."""
        if count < 0:
            raise ValueError("Member count cannot be negative")
        self.member_count = count
        self.update_timestamp()
    
    def increment_command_usage(self, command_name: str) -> None:
        """Increment usage count for a command."""
        self.command_usage[command_name] = self.command_usage.get(command_name, 0) + 1
        self.update_timestamp()
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow()
        self.update_timestamp()
    
    def get_command_usage_stats(self) -> Dict[str, int]:
        """Get command usage statistics sorted by usage."""
        return dict(sorted(self.command_usage.items(), key=lambda x: x[1], reverse=True))
    
    def get_top_commands(self, limit: int = 10) -> List[tuple[str, int]]:
        """Get the most used commands."""
        sorted_commands = sorted(self.command_usage.items(), key=lambda x: x[1], reverse=True)
        return sorted_commands[:limit]
    
    def set_configuration(self, config: GuildConfiguration) -> None:
        """Set the guild configuration."""
        self.configuration = config
        self.update_timestamp()
    
    def is_premium(self) -> bool:
        """Check if guild has premium features (based on boost level)."""
        return self.boosted and self.boost_level >= 2
    
    def get_feature_limit(self, feature: str) -> int:
        """Get feature limits based on boost level."""
        limits = {
            "custom_commands": {
                0: 5,
                1: 10,
                2: 25,
                3: 50
            },
            "tournaments": {
                0: 1,
                1: 3,
                2: 10,
                3: float('inf')
            },
            "auto_roles": {
                0: 0,
                1: 3,
                2: 10,
                3: 25
            }
        }
        
        return limits.get(feature, {}).get(self.boost_level, 0)


@dataclass
class GuildMember(BaseModel):
    """Represents a member's status within a specific guild."""
    
    guild_id: str
    user_id: str
    joined_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    roles: List[str] = field(default_factory=list)
    nickname: Optional[str] = None
    is_boosting: bool = False
    boost_since: Optional[datetime] = None
    warnings: int = 0
    strikes: int = 0
    notes: Optional[str] = None
    last_message: Optional[datetime] = None
    message_count: int = 0
    voice_time_minutes: int = 0
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate guild member data."""
        if not self.guild_id:
            raise ValueError("Guild ID is required")
        if not self.user_id:
            raise ValueError("User ID is required")
        if self.warnings < 0:
            raise ValueError("Warnings cannot be negative")
        if self.strikes < 0:
            raise ValueError("Strikes cannot be negative")
        if self.message_count < 0:
            raise ValueError("Message count cannot be negative")
        if self.voice_time_minutes < 0:
            raise ValueError("Voice time cannot be negative")
    
    def add_role(self, role_id: str) -> None:
        """Add a role to the member."""
        if role_id not in self.roles:
            self.roles.append(role_id)
            self.update_timestamp()
    
    def remove_role(self, role_id: str) -> None:
        """Remove a role from the member."""
        if role_id in self.roles:
            self.roles.remove(role_id)
            self.update_timestamp()
    
    def has_role(self, role_id: str) -> bool:
        """Check if member has a specific role."""
        return role_id in self.roles
    
    def add_warning(self) -> None:
        """Add a warning to the member."""
        self.warnings += 1
        self.update_timestamp()
    
    def add_strike(self) -> None:
        """Add a strike to the member."""
        self.strikes += 1
        self.update_timestamp()
    
    def clear_warnings(self) -> None:
        """Clear all warnings."""
        self.warnings = 0
        self.update_timestamp()
    
    def clear_strikes(self) -> None:
        """Clear all strikes."""
        self.strikes = 0
        self.update_timestamp()
    
    def increment_message_count(self) -> None:
        """Increment message count and update last message time."""
        self.message_count += 1
        self.last_message = datetime.utcnow()
        self.update_timestamp()
    
    def add_voice_time(self, minutes: int) -> None:
        """Add voice time."""
        if minutes < 0:
            raise ValueError("Voice time cannot be negative")
        self.voice_time_minutes += minutes
        self.update_timestamp()
