"""
Central event bus for the Guardian Angel League Discord Bot.

Manages event emission, handling, and subscription with support for
prioritization, retry logic, and event filtering.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import weakref
import json
from collections import defaultdict

from .event_types import Event, EventType, EventPriority, EventCategory


class EventHandler(ABC):
    """Abstract base class for event handlers."""
    
    def __init__(self, name: str):
        """
        Initialize event handler.
        
        Args:
            name: Handler name for identification
        """
        self.name = name
        self.logger = logging.getLogger(f"EventHandler.{name}")
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """
        Handle an event.
        
        Args:
            event: Event to handle
        """
        pass
    
    async def can_handle(self, event: Event) -> bool:
        """
        Check if this handler can handle the event.
        
        Args:
            event: Event to check
            
        Returns:
            True if handler can process the event
        """
        return True
    
    def __str__(self) -> str:
        return f"EventHandler({self.name})"


class EventSubscriber(ABC):
    """Abstract base class for event subscribers."""
    
    def __init__(self, name: str):
        """
        Initialize event subscriber.
        
        Args:
            name: Subscriber name for identification
        """
        self.name = name
        self.logger = logging.getLogger(f"EventSubscriber.{name}")
    
    @abstractmethod
    async def on_event(self, event: Event) -> None:
        """
        Called when an event is received.
        
        Args:
            event: Event that occurred
        """
        pass
    
    def __str__(self) -> str:
        return f"EventSubscriber({self.name})"


@dataclass
class EventSubscription:
    """Represents an event subscription."""
    
    event_types: Set[EventType]
    handler: Union[EventHandler, EventSubscriber, Callable]
    priority: EventPriority = EventPriority.NORMAL
    filter_func: Optional[Callable[[Event], bool]] = None
    async_handler: bool = True
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def can_handle(self, event: Event) -> bool:
        """Check if this subscription can handle the event."""
        if not self.enabled:
            return False
        
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        if self.filter_func and not self.filter_func(event):
            return False
        
        return True


@dataclass
class EventMetrics:
    """Event bus metrics."""
    
    events_emitted: int = 0
    events_processed: int = 0
    events_failed: int = 0
    events_retrying: int = 0
    handlers_executed: int = 0
    average_processing_time: float = 0.0
    queue_size: int = 0
    last_event_time: Optional[datetime] = None
    
    def record_emission(self) -> None:
        """Record an event emission."""
        self.events_emitted += 1
        self.last_event_time = datetime.utcnow()
    
    def record_processing(self, processing_time: float) -> None:
        """Record event processing."""
        self.events_processed += 1
        self.handlers_executed += 1
        
        # Update average processing time
        if self.events_processed == 1:
            self.average_processing_time = processing_time
        else:
            total_time = self.average_processing_time * (self.events_processed - 1) + processing_time
            self.average_processing_time = total_time / self.events_processed
    
    def record_failure(self) -> None:
        """Record an event failure."""
        self.events_failed += 1
    
    def record_retry(self) -> None:
        """Record an event retry."""
        self.events_retrying += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "events_emitted": self.events_emitted,
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "events_retrying": self.events_retrying,
            "handlers_executed": self.handlers_executed,
            "average_processing_time_ms": self.average_processing_time * 1000,
            "queue_size": self.queue_size,
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None,
            "success_rate": self.events_processed / max(self.events_emitted, 1)
        }


class EventBus:
    """
    Central event bus for managing events.
    
    Provides event emission, subscription, and handling with support
    for prioritization, retry logic, and performance monitoring.
    """
    
    def __init__(self, max_queue_size: int = 10000):
        """
        Initialize event bus.
        
        Args:
            max_queue_size: Maximum number of events in queue
        """
        self.logger = logging.getLogger("EventBus")
        self.max_queue_size = max_queue_size
        
        # Event storage and processing
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._subscriptions: List[EventSubscription] = []
        self._processing = False
        self._shutdown = False
        
        # Metrics
        self._metrics = EventMetrics()
        
        # Background task
        self._processor_task: Optional[asyncio.Task] = None
        self._retry_task: Optional[asyncio.Task] = None
        self._retry_queue: asyncio.Queue = asyncio.Queue()
        
        # Event history for debugging
        self._event_history: List[Event] = []
        self._max_history_size = 1000
    
    def subscribe(self, 
                  handler: Union[EventHandler, EventSubscriber, Callable],
                  event_types: Optional[List[EventType]] = None,
                  priority: EventPriority = EventPriority.NORMAL,
                  filter_func: Optional[Callable[[Event], bool]] = None) -> None:
        """
        Subscribe to events.
        
        Args:
            handler: Event handler, subscriber, or callable
            event_types: List of event types to handle (None = all)
            priority: Handler priority
            filter_func: Optional filter function
        """
        subscription = EventSubscription(
            event_types=set(event_types) if event_types else None,
            handler=handler,
            priority=priority,
            filter_func=filter_func,
            async_handler=hasattr(handler, 'handle') or hasattr(handler, 'on_event') or asyncio.iscoroutinefunction(handler)
        )
        
        self._subscriptions.append(subscription)
        
        # Sort subscriptions by priority
        self._subscriptions.sort(key=lambda s: s.priority.value, reverse=True)
        
        self.logger.info(f"Subscribed {handler} to events: {event_types or 'all'}")
    
    def unsubscribe(self, handler: Union[EventHandler, EventSubscriber, Callable]) -> None:
        """
        Unsubscribe from events.
        
        Args:
            handler: Handler to unsubscribe
        """
        original_count = len(self._subscriptions)
        self._subscriptions = [
            sub for sub in self._subscriptions 
            if sub.handler != handler
        ]
        
        if len(self._subscriptions) < original_count:
            self.logger.info(f"Unsubscribed {handler}")
    
    async def emit(self, event: Event) -> None:
        """
        Emit an event to the bus.
        
        Args:
            event: Event to emit
        """
        if self._shutdown:
            self.logger.warning("Event bus is shutdown, ignoring event")
            return
        
        try:
            self._metrics.record_emission()
            
            # Add to history
            self._add_to_history(event)
            
            # Add to processing queue
            await self._event_queue.put(event)
            
            # Ensure processor is running
            self._ensure_processor_running()
            
        except asyncio.QueueFull:
            self.logger.error(f"Event queue is full, dropping event: {event.event_id}")
            self._metrics.record_failure()
    
    async def emit_sync(self, event: Event) -> None:
        """
        Emit an event and wait for it to be processed.
        
        Args:
            event: Event to emit
        """
        if self._shutdown:
            self.logger.warning("Event bus is shutdown, ignoring event")
            return
        
        # Process event immediately
        await self._process_event(event)
    
    def _add_to_history(self, event: Event) -> None:
        """Add event to history buffer."""
        self._event_history.append(event)
        
        # Trim history if needed
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
    
    def _ensure_processor_running(self) -> None:
        """Ensure the event processor task is running."""
        if self._processor_task is None or self._processor_task.done():
            self._processor_task = asyncio.create_task(self._process_events())
        
        if self._retry_task is None or self._retry_task.done():
            self._retry_task = asyncio.create_task(self._process_retries())
    
    async def _process_events(self) -> None:
        """Background task to process events from the queue."""
        self._processing = True
        self.logger.info("Event processor started")
        
        while not self._shutdown:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(
                    self._event_queue.get(), 
                    timeout=1.0
                )
                
                await self._process_event(event)
                
            except asyncio.TimeoutError:
                # No events to process, continue
                continue
            except Exception as e:
                self.logger.error(f"Error in event processor: {e}")
                await asyncio.sleep(1)  # Brief pause before continuing
        
        self._processing = False
        self.logger.info("Event processor stopped")
    
    async def _process_event(self, event: Event) -> None:
        """Process a single event."""
        start_time = datetime.utcnow()
        processed_count = 0
        
        try:
            # Find matching subscriptions
            matching_subs = [
                sub for sub in self._subscriptions
                if sub.can_handle(event)
            ]
            
            # Execute handlers
            for subscription in matching_subs:
                try:
                    await self._execute_handler(subscription, event)
                    processed_count += 1
                except Exception as e:
                    self.logger.error(f"Handler {subscription.handler} failed for event {event.event_id}: {e}")
                    self._metrics.record_failure()
            
            # Update metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self._metrics.record_processing(processing_time)
            
            self.logger.debug(f"Processed event {event.event_id} with {processed_count} handlers")
            
        except Exception as e:
            self.logger.error(f"Failed to process event {event.event_id}: {e}")
            self._metrics.record_failure()
    
    async def _execute_handler(self, subscription: EventSubscription, event: Event) -> None:
        """Execute a single event handler."""
        handler = subscription.handler
        
        if isinstance(handler, EventHandler):
            if await handler.can_handle(event):
                await handler.handle(event)
        elif isinstance(handler, EventSubscriber):
            await handler.on_event(event)
        elif callable(handler):
            if subscription.async_handler:
                await handler(event)
            else:
                # Run sync handler in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler, event)
    
    async def _process_retries(self) -> None:
        """Background task to process event retries."""
        self.logger.info("Event retry processor started")
        
        while not self._shutdown:
            try:
                # Wait for retry event with timeout
                event = await asyncio.wait_for(
                    self._retry_queue.get(),
                    timeout=5.0
                )
                
                if event.can_retry():
                    event.increment_retry()
                    
                    # Add delay before retry (exponential backoff)
                    delay = min(2 ** event.retry_count, 30)  # Max 30 seconds
                    await asyncio.sleep(delay)
                    
                    # Retry processing
                    await self._process_event(event)
                    
                else:
                    self.logger.error(f"Event {event.event_id} exceeded max retries")
                    self._metrics.record_failure()
                
            except asyncio.TimeoutError:
                # No retries to process, continue
                continue
            except Exception as e:
                self.logger.error(f"Error in retry processor: {e}")
                await asyncio.sleep(1)
        
        self.logger.info("Event retry processor stopped")
    
    def _schedule_retry(self, event: Event) -> None:
        """Schedule an event for retry."""
        try:
            self._retry_queue.put_nowait(event)
            self._metrics.record_retry()
        except asyncio.QueueFull:
            self.logger.error(f"Retry queue is full, dropping event: {event.event_id}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get event bus metrics."""
        return {
            "metrics": self._metrics.to_dict(),
            "subscriptions": len(self._subscriptions),
            "processing": self._processing,
            "queue_size": self._event_queue.qsize(),
            "retry_queue_size": self._retry_queue.qsize(),
            "history_size": len(self._event_history)
        }
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events from history."""
        recent_events = self._event_history[-limit:]
        return [event.to_dict() for event in recent_events]
    
    def get_subscriptions_info(self) -> List[Dict[str, Any]]:
        """Get information about active subscriptions."""
        return [
            {
                "handler": str(sub.handler),
                "event_types": [et.value for et in sub.event_types] if sub.event_types else ["all"],
                "priority": sub.priority.value,
                "enabled": sub.enabled,
                "created_at": sub.created_at.isoformat()
            }
            for sub in self._subscriptions
        ]
    
    async def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
        self.logger.info("Event history cleared")
    
    async def start(self) -> None:
        """Start the event bus."""
        self._shutdown = False
        self._ensure_processor_running()
        self.logger.info("Event bus started")
    
    async def stop(self) -> None:
        """Stop the event bus."""
        self.logger.info("Stopping event bus...")
        self._shutdown = True
        
        # Wait for current events to finish processing
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        
        # Process any remaining events in queue
        while not self._event_queue.empty():
            try:
                event = self._event_queue.get_nowait()
                self.logger.warning(f"Event {event.event_id} not processed due to shutdown")
            except asyncio.QueueEmpty:
                break
        
        self.logger.info("Event bus stopped")
    
    def __del__(self):
        """Cleanup when event bus is destroyed."""
        if not self._shutdown:
            self.logger.warning("Event bus was not properly stopped")


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def emit_event(event: Event) -> None:
    """Emit an event using the global event bus."""
    event_bus = get_event_bus()
    await event_bus.emit(event)


async def emit_event_sync(event: Event) -> None:
    """Emit an event and wait for processing using the global event bus."""
    event_bus = get_event_bus()
    await event_bus.emit_sync(event)


def subscribe_to_events(handler: Union[EventHandler, EventSubscriber, Callable],
                       event_types: Optional[List[EventType]] = None,
                       priority: EventPriority = EventPriority.NORMAL,
                       filter_func: Optional[Callable[[Event], bool]] = None) -> None:
    """Subscribe to events using the global event bus."""
    event_bus = get_event_bus()
    event_bus.subscribe(handler, event_types, priority, filter_func)


def unsubscribe_from_events(handler: Union[EventHandler, EventSubscriber, Callable]) -> None:
    """Unsubscribe from events using the global event bus."""
    event_bus = get_event_bus()
    event_bus.unsubscribe(handler)
