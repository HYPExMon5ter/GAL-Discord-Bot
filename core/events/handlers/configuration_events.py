"""
Configuration event handlers.

Handles configuration-related events with business logic
for system settings, preferences, and configuration management.
"""

import logging

from ..event_bus import EventHandler
from ..event_types import Event, EventType, ConfigurationEvent


class ConfigurationEventHandler(EventHandler):
    """Handler for configuration-related events."""
    
    def __init__(self):
        """Initialize configuration event handler."""
        super().__init__("configuration_events")
        self.logger.info("Configuration event handler initialized")
    
    async def handle(self, event: Event) -> None:
        """
        Handle configuration event.
        
        Args:
            event: Configuration event to handle
        """
        try:
            if isinstance(event, ConfigurationEvent):
                await self._handle_configuration_event(event)
            else:
                self.logger.warning(f"Received non-configuration event: {event.event_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling configuration event {event.event_id}: {e}")
            raise
    
    async def _handle_configuration_event(self, event: ConfigurationEvent) -> None:
        """Handle configuration-specific event."""
        self.logger.info(f"Handling configuration event: {event.event_type.value} for {event.configuration_key}")
        
        # Route to specific handler based on event type
        handlers = {
            EventType.CONFIGURATION_UPDATED: self._handle_configuration_updated,
            EventType.CONFIGURATION_BACKUP_CREATED: self._handle_configuration_backup_created,
            EventType.CONFIGURATION_RESTORED: self._handle_configuration_restored,
            EventType.SYSTEM_SETTING_CHANGED: self._handle_system_setting_changed,
        }
        
        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)
        else:
            self.logger.warning(f"No handler for configuration event type: {event.event_type.value}")
    
    async def _handle_configuration_updated(self, event: ConfigurationEvent) -> None:
        """Handle configuration update."""
        self.logger.info(f"Configuration updated: {event.configuration_key}")
        # TODO: Implement configuration update logic
    
    async def _handle_configuration_backup_created(self, event: ConfigurationEvent) -> None:
        """Handle configuration backup creation."""
        self.logger.info(f"Configuration backup created: {event.configuration_key}")
        # TODO: Implement backup creation logic
    
    async def _handle_configuration_restored(self, event: ConfigurationEvent) -> None:
        """Handle configuration restoration."""
        self.logger.info(f"Configuration restored: {event.configuration_key}")
        # TODO: Implement restoration logic
    
    async def _handle_system_setting_changed(self, event: ConfigurationEvent) -> None:
        """Handle system setting change."""
        self.logger.info(f"System setting changed: {event.configuration_key}")
        # TODO: Implement system setting change logic
    
    async def can_handle(self, event: Event) -> bool:
        """
        Check if this handler can handle the event.
        
        Args:
            event: Event to check
            
        Returns:
            True if handler can process the event
        """
        return (
            isinstance(event, ConfigurationEvent) or
            event.event_type.value.startswith("configuration") or
            event.event_type.value.startswith("system_setting")
        )
