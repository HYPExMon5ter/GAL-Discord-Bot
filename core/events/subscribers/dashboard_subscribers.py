"""
Dashboard event subscribers.

Handles events that require dashboard integration like
real-time updates, WebSocket notifications, and data synchronization.
"""

import logging

from ..event_bus import EventSubscriber
from ..event_types import Event, EventType


class DashboardEventSubscriber(EventSubscriber):
    """Subscriber for dashboard-related events."""
    
    def __init__(self, websocket_manager=None):
        """
        Initialize dashboard event subscriber.
        
        Args:
            websocket_manager: WebSocket manager for real-time updates
        """
        super().__init__("dashboard_subscriber")
        self.websocket_manager = websocket_manager
        self.logger.info("Dashboard event subscriber initialized")
    
    async def on_event(self, event: Event) -> None:
        """
        Handle event for dashboard integration.
        
        Args:
            event: Event to handle
        """
        try:
            # Send real-time updates via WebSocket if available
            if self.websocket_manager:
                await self._send_websocket_update(event)
            
            # Route to specific handlers based on event type
            handlers = {
                EventType.TOURNAMENT_UPDATED: self._handle_tournament_update,
                EventType.USER_REGISTERED: self._handle_user_registration,
                EventType.MATCH_COMPLETED: self._handle_match_completion,
            }
            
            handler = handlers.get(event.event_type)
            if handler:
                await handler(event)
                
        except Exception as e:
            self.logger.error(f"Error in dashboard subscriber for event {event.event_id}: {e}")
    
    async def _send_websocket_update(self, event: Event) -> None:
        """Send real-time update via WebSocket."""
        try:
            # Prepare event data for WebSocket transmission
            update_data = {
                "type": "event_update",
                "event": event.to_dict(),
                "timestamp": event.timestamp.isoformat()
            }
            
            # Broadcast to connected clients
            await self.websocket_manager.broadcast(update_data)
            
        except Exception as e:
            self.logger.error(f"Failed to send WebSocket update: {e}")
    
    async def _handle_tournament_update(self, event: Event) -> None:
        """Handle tournament update for dashboard."""
        self.logger.info(f"Handling tournament update for dashboard: {event.event_id}")
        # TODO: Update dashboard data, refresh UI components
    
    async def _handle_user_registration(self, event: Event) -> None:
        """Handle user registration for dashboard."""
        self.logger.info(f"Handling user registration for dashboard: {event.event_id}")
        # TODO: Update registration lists, refresh participant counts
    
    async def _handle_match_completion(self, event: Event) -> None:
        """Handle match completion for dashboard."""
        self.logger.info(f"Handling match completion for dashboard: {event.event_id}")
        # TODO: Update brackets, refresh match displays
