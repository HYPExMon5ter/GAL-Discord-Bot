# helpers/async_helpers.py

import asyncio
import functools
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any, Callable, Union, Awaitable, TypeVar

import discord

from .logging_helper import BotLogger

T = TypeVar('T')


class AsyncOperationError(Exception):
    """Custom exception for async operation failures."""

    def __init__(self, operation: str, original_error: Exception = None):
        self.operation = operation
        self.original_error = original_error
        message = f"Async operation '{operation}' failed"
        if original_error:
            message += f": {original_error}"
        super().__init__(message)


class PerformanceMonitor:
    """Performance monitoring system for async operations."""

    def __init__(self):
        self.operation_stats = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "errors": 0,
            "min_time": float('inf'),
            "max_time": 0.0,
            "last_execution": None
        })

    def record_operation(self, operation_name: str, duration: float, success: bool = True):
        """Record performance data for an operation."""
        stats = self.operation_stats[operation_name]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)
        stats["last_execution"] = datetime.now(timezone.utc).isoformat()

        if not success:
            stats["errors"] += 1

    def get_stats(self, operation_name: str = None) -> Dict[str, Any]:
        """Get performance statistics for operations."""
        if operation_name:
            return self.operation_stats.get(operation_name, {})
        return dict(self.operation_stats)

    def reset_stats(self):
        """Reset all performance statistics."""
        self.operation_stats.clear()


class AsyncHelpers:
    """Comprehensive async utilities for Discord bot operations."""

    @staticmethod
    async def safe_send_message(
            channel: discord.abc.Messageable,
            content: str = None,
            embed: discord.Embed = None,
            view: discord.ui.View = None,
            file: discord.File = None,
            files: List[discord.File] = None,
            delete_after: Optional[float] = None,
            max_retries: int = 2
    ) -> Optional[discord.Message]:
        """Send message with comprehensive error handling and retry logic."""
        if not channel:
            BotLogger.error("Cannot send message: channel is None", "ASYNC_HELPERS")
            return None

        for attempt in range(max_retries + 1):
            try:
                # Validate content length
                if content and len(content) > 2000:
                    BotLogger.warning(f"Message content truncated (was {len(content)} chars)", "ASYNC_HELPERS")
                    content = content[:1997] + "..."

                message = await channel.send(
                    content=content,
                    embed=embed,
                    view=view,
                    file=file,
                    files=files,
                    delete_after=delete_after
                )

                BotLogger.debug(f"Message sent successfully to {channel}", "ASYNC_HELPERS")
                return message

            except discord.Forbidden:
                BotLogger.error(f"No permission to send message to {channel}", "ASYNC_HELPERS")
                break
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limit
                    retry_after = getattr(e, 'retry_after', 1)
                    BotLogger.warning(f"Rate limited, waiting {retry_after}s", "ASYNC_HELPERS")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    BotLogger.error(f"HTTP error sending message: {e}", "ASYNC_HELPERS")
                    if attempt == max_retries:
                        break
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                BotLogger.error(f"Unexpected error sending message: {e}", "ASYNC_HELPERS")
                if attempt == max_retries:
                    break
                await asyncio.sleep(1)

        return None

    @staticmethod
    async def safe_edit_message(
            message: discord.Message,
            content: str = None,
            embed: discord.Embed = None,
            view: discord.ui.View = None,
            max_retries: int = 2
    ) -> bool:
        """Edit message with comprehensive error handling."""
        if not message:
            BotLogger.error("Cannot edit message: message is None", "ASYNC_HELPERS")
            return False

        for attempt in range(max_retries + 1):
            try:
                # Validate content length
                if content and len(content) > 2000:
                    BotLogger.warning(f"Edit content truncated (was {len(content)} chars)", "ASYNC_HELPERS")
                    content = content[:1997] + "..."

                await message.edit(content=content, embed=embed, view=view)
                BotLogger.debug(f"Message edited successfully: {message.id}", "ASYNC_HELPERS")
                return True

            except discord.NotFound:
                BotLogger.warning(f"Message not found for edit: {message.id}", "ASYNC_HELPERS")
                break
            except discord.Forbidden:
                BotLogger.error(f"No permission to edit message: {message.id}", "ASYNC_HELPERS")
                break
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limit
                    retry_after = getattr(e, 'retry_after', 1)
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    BotLogger.error(f"HTTP error editing message: {e}", "ASYNC_HELPERS")
                    if attempt == max_retries:
                        break
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                BotLogger.error(f"Unexpected error editing message: {e}", "ASYNC_HELPERS")
                if attempt == max_retries:
                    break
                await asyncio.sleep(1)

        return False

    @staticmethod
    async def safe_delete_message(message: discord.Message, delay: float = 0) -> bool:
        """Delete message with error handling and optional delay."""
        if not message:
            BotLogger.debug("Cannot delete message: message is None", "ASYNC_HELPERS")
            return False

        try:
            if delay > 0:
                await asyncio.sleep(delay)

            await message.delete()
            BotLogger.debug(f"Message deleted successfully: {message.id}", "ASYNC_HELPERS")
            return True

        except discord.NotFound:
            BotLogger.debug(f"Message already deleted: {message.id}", "ASYNC_HELPERS")
            return True  # Consider this success
        except discord.Forbidden:
            BotLogger.warning(f"No permission to delete message: {message.id}", "ASYNC_HELPERS")
            return False
        except Exception as e:
            BotLogger.error(f"Error deleting message {message.id}: {e}", "ASYNC_HELPERS")
            return False

    @staticmethod
    async def safe_add_reaction(message: discord.Message, emoji: Union[str, discord.Emoji]) -> bool:
        """Add reaction to message with error handling."""
        if not message:
            return False

        try:
            await message.add_reaction(emoji)
            return True
        except discord.NotFound:
            BotLogger.debug(f"Message not found for reaction: {message.id}", "ASYNC_HELPERS")
            return False
        except discord.Forbidden:
            BotLogger.debug(f"No permission to add reaction to: {message.id}", "ASYNC_HELPERS")
            return False
        except discord.HTTPException as e:
            BotLogger.warning(f"HTTP error adding reaction: {e}", "ASYNC_HELPERS")
            return False
        except Exception as e:
            BotLogger.error(f"Unexpected error adding reaction: {e}", "ASYNC_HELPERS")
            return False

    @staticmethod
    async def safe_remove_reaction(
            message: discord.Message,
            emoji: Union[str, discord.Emoji],
            member: discord.Member = None
    ) -> bool:
        """Remove reaction from message with error handling."""
        if not message:
            return False

        try:
            if member:
                await message.remove_reaction(emoji, member)
            else:
                await message.clear_reaction(emoji)
            return True
        except discord.NotFound:
            BotLogger.debug(f"Message/reaction not found: {message.id}", "ASYNC_HELPERS")
            return True  # Consider this success
        except discord.Forbidden:
            BotLogger.debug(f"No permission to remove reaction: {message.id}", "ASYNC_HELPERS")
            return False
        except Exception as e:
            BotLogger.error(f"Error removing reaction: {e}", "ASYNC_HELPERS")
            return False

    @staticmethod
    async def run_with_timeout(
            coro: Callable[..., Awaitable[T]],
            timeout: float,
            default_value: T = None,
            operation_name: str = "unknown",
            *args,
            **kwargs
    ) -> T:
        """Execute coroutine with timeout protection."""
        try:
            result = await asyncio.wait_for(coro(*args, **kwargs), timeout=timeout)
            return result
        except asyncio.TimeoutError:
            BotLogger.warning(f"Operation '{operation_name}' timed out after {timeout}s", "ASYNC_HELPERS")
            return default_value
        except Exception as e:
            BotLogger.error(f"Error in timed operation '{operation_name}': {e}", "ASYNC_HELPERS")
            return default_value

    @staticmethod
    async def retry_with_backoff(
            coro: Callable[..., Awaitable[T]],
            max_retries: int = 3,
            base_delay: float = 1.0,
            context: str = "operation",
            *args,
            **kwargs
    ) -> Optional[T]:
        """Execute coroutine with exponential backoff retry logic."""
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                result = await coro(*args, **kwargs)
                if attempt > 0:
                    BotLogger.info(f"Retry successful for {context} on attempt {attempt + 1}", "ASYNC_HELPERS")
                return result

            except Exception as e:
                last_exception = e

                if attempt == max_retries:
                    BotLogger.error(f"All retries failed for {context}: {e}", "ASYNC_HELPERS")
                    break

                if not _should_retry_exception(e):
                    BotLogger.warning(f"Non-retryable error for {context}: {e}", "ASYNC_HELPERS")
                    break

                delay = base_delay * (2 ** attempt)
                BotLogger.debug(f"Retrying {context} in {delay}s (attempt {attempt + 1})", "ASYNC_HELPERS")
                await asyncio.sleep(delay)

        return None

    @staticmethod
    async def batch_execute(
            items: List[Any],
            handler: Callable[[Any], Awaitable[T]],
            batch_size: int = 10,
            delay_between_batches: float = 0.5,
            operation_name: str = "batch_operation"
    ) -> List[T]:
        """Execute operations in batches with rate limiting."""
        results = []
        total_batches = (len(items) + batch_size - 1) // batch_size

        BotLogger.info(f"Starting {operation_name} with {len(items)} items in {total_batches} batches", "ASYNC_HELPERS")

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_num = i // batch_size + 1

            BotLogger.debug(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)", "ASYNC_HELPERS")

            # Execute batch concurrently
            batch_tasks = [handler(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results and handle exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    BotLogger.warning(f"Error in batch item {i + j}: {result}", "ASYNC_HELPERS")
                    results.append(None)
                else:
                    results.append(result)

            # Delay between batches to prevent rate limiting
            if batch_num < total_batches and delay_between_batches > 0:
                await asyncio.sleep(delay_between_batches)

        successful_results = [r for r in results if r is not None]
        BotLogger.info(f"Batch operation completed: {len(successful_results)}/{len(items)} successful", "ASYNC_HELPERS")

        return results

    @staticmethod
    async def safe_dm_user(user: discord.User, content: str = None, embed: discord.Embed = None) -> bool:
        """Send DM to user with comprehensive error handling."""
        if not user:
            return False

        try:
            await user.send(content=content, embed=embed)
            BotLogger.debug(f"DM sent successfully to user {user.id}", "ASYNC_HELPERS")
            return True

        except discord.Forbidden:
            BotLogger.debug(f"Cannot DM user {user.id} (DMs disabled/blocked)", "ASYNC_HELPERS")
            return False
        except discord.HTTPException as e:
            BotLogger.warning(f"HTTP error sending DM to {user.id}: {e}", "ASYNC_HELPERS")
            return False
        except Exception as e:
            BotLogger.error(f"Unexpected error sending DM to {user.id}: {e}", "ASYNC_HELPERS")
            return False

    @staticmethod
    def safe_typing(channel: discord.abc.Messageable, duration: float = 30.0):
        """Create a safe typing indicator context manager."""
        if not channel:
            BotLogger.debug("Cannot start typing: channel is None", "ASYNC_HELPERS")
            return AsyncHelpers._NoOpContext()

        return AsyncHelpers._SafeTypingContext(channel, duration)

    class _SafeTypingContext:
        """Context manager for safe typing indicator management."""

        def __init__(self, channel: discord.abc.Messageable, duration: float):
            self.channel = channel
            self.duration = duration
            self.typing = None
            self.timeout_task = None

        async def __aenter__(self):
            try:
                self.typing = self.channel.typing()
                await self.typing.__aenter__()

                # Set timeout to automatically stop typing
                self.timeout_task = asyncio.create_task(self._timeout_handler())

            except Exception as e:
                BotLogger.debug(f"Failed to start typing indicator: {type(e).__name__}", "ASYNC_HELPERS")
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            try:
                # Cancel timeout task
                if self.timeout_task and not self.timeout_task.done():
                    self.timeout_task.cancel()

                # Stop typing
                if self.typing:
                    await self.typing.__aexit__(exc_type, exc_val, exc_tb)

            except Exception as e:
                BotLogger.debug(f"Error stopping typing indicator: {type(e).__name__}", "ASYNC_HELPERS")

        async def _timeout_handler(self):
            """Automatically stop typing after duration limit."""
            try:
                await asyncio.sleep(self.duration)
                if self.typing:
                    await self.typing.__aexit__(None, None, None)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                BotLogger.debug(f"Error in typing timeout handler: {type(e).__name__}", "ASYNC_HELPERS")

    class _NoOpContext:
        """No-operation context manager for fallback scenarios."""

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass


def _should_retry_exception(exception: Exception) -> bool:
    """Determine if an exception should trigger a retry attempt."""

    # Always retry these types
    retryable_types = (
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
    )

    if isinstance(exception, retryable_types):
        return True

    # Discord-specific retryable errors
    if isinstance(exception, discord.HTTPException):
        # Retry on server errors and rate limits
        if hasattr(exception, 'status') and exception.status in [500, 502, 503, 504, 429]:
            return True

    # Check error message for retryable conditions
    error_msg = str(exception).lower()
    retryable_messages = [
        'timeout', 'connection', 'network', 'temporary', 'rate limit',
        'server error', 'service unavailable', 'gateway timeout'
    ]

    return any(msg in error_msg for msg in retryable_messages)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Global helper instance for easy access (backward compatibility)
async_helpers = AsyncHelpers()


# Utility decorators for common patterns
def with_timeout(timeout: float = 30.0, default_value: Any = None):
    """Decorator to add timeout protection to async functions."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await AsyncHelpers.run_with_timeout(
                func, timeout, default_value, func.__name__, *args, **kwargs
            )

        return wrapper

    return decorator


def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator to add retry logic to async functions."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await AsyncHelpers.retry_with_backoff(
                func, max_retries, base_delay, context=func.__name__, *args, **kwargs
            )

        return wrapper

    return decorator


# Export important classes and functions
__all__ = [
    'AsyncHelpers',
    'AsyncOperationError',
    'PerformanceMonitor',
    'async_helpers',  # Backward compatibility instance
    'performance_monitor',  # Performance monitoring
    'with_timeout',
    'with_retry',
    '_should_retry_exception',
]