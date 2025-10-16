# integrations/sheet_utils.py

import asyncio
import logging
import random
import time
from typing import Any, Callable

from utils.metrics import increment_counter, record_duration


def _operation_name(callable_obj: Callable[..., Any]) -> str:
    """Return a readable name for the wrapped callable."""
    name = getattr(callable_obj, "__name__", None)
    if name:
        return name
    return callable_obj.__class__.__name__

# Rate limiting configuration (more conservative to avoid rate limiting)
SHEETS_BASE_DELAY = 2.0  # Start with longer delay
MAX_DELAY = 120
FULL_BACKOFF = 90  # Longer backoff for quota exceeded
MAX_RETRIES = 3  # Fewer retries to avoid spamming the API


async def retry_until_successful(fn, *args, **kwargs):
    """
    Retry function with exponential backoff and comprehensive error handling.
    """
    operation = _operation_name(fn)
    global SHEETS_BASE_DELAY
    delay = SHEETS_BASE_DELAY
    attempts = 0
    last_error = None
    start_time = time.perf_counter()

    while attempts < MAX_RETRIES:
        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(*args, **kwargs)
            else:
                result = fn(*args, **kwargs)

            # Successful call - adjust base delay if it was increased
            if delay > SHEETS_BASE_DELAY:
                SHEETS_BASE_DELAY = min(SHEETS_BASE_DELAY * 0.9, delay)

            elapsed = time.perf_counter() - start_time
            record_duration(
                "sheets.operation.duration",
                elapsed,
                operation=operation,
                attempts=str(attempts + 1),
                status="success",
            )
            return result

        except Exception as e:
            last_error = e
            attempts += 1
            err_str = str(e).lower()
            increment_counter(
                "sheets.operation.retry",
                operation=operation,
                attempt=str(attempts),
            )

            # Check for quota/rate limit errors
            if "429" in str(e) or any(keyword in err_str for keyword in ["quota", "rate", "limit"]):
                if delay >= 30 or attempts > 3:
                    wait_time = FULL_BACKOFF + random.uniform(0, 5)
                    logging.warning(
                        f"Quota exceeded, waiting {wait_time:.1f}s (attempt {attempts})"
                    )
                    await asyncio.sleep(wait_time)
                    delay = FULL_BACKOFF
                else:
                    wait_time = delay + random.uniform(0, 0.5)
                    logging.warning(f"Rate limited, waiting {wait_time:.1f}s (attempt {attempts})")
                    await asyncio.sleep(wait_time)
                    delay = min(delay * 2, MAX_DELAY)

            # Check for authentication errors
            elif "401" in str(e) or "unauthorized" in err_str:
                from integrations.sheet_base import AuthenticationError
                raise AuthenticationError(f"Authentication failed: {e}") from e

            # Check for other HTTP errors
            elif any(code in str(e) for code in ["400", "403", "404", "500", "502", "503"]):
                if attempts >= MAX_RETRIES - 1:
                    from integrations.sheet_base import SheetsError
                    raise SheetsError(f"HTTP error after {attempts} attempts: {e}") from e
                logging.warning(f"HTTP error, retrying (attempt {attempts}): {e}")
                await asyncio.sleep(delay)

            # For other errors, fail immediately on critical ones
            elif "connection" in err_str or "timeout" in err_str:
                if attempts >= MAX_RETRIES - 1:
                    from integrations.sheet_base import SheetsError
                    raise SheetsError(f"Connection error after {attempts} attempts: {e}") from e
                logging.warning(f"Connection error, retrying (attempt {attempts}): {e}")
                await asyncio.sleep(delay)
            else:
                # Unknown error, don't retry
                from integrations.sheet_base import SheetsError
                record_duration(
                    "sheets.operation.duration",
                    time.perf_counter() - start_time,
                    operation=operation,
                    attempts=str(attempts),
                    status="error",
                )
                raise SheetsError(f"Unexpected error: {e}") from e

    # All retries exhausted
    from integrations.sheet_base import SheetsError
    record_duration(
        "sheets.operation.duration",
        time.perf_counter() - start_time,
        operation=operation,
        attempts=str(attempts),
        status="error",
    )
    message = f"All {MAX_RETRIES} retries exhausted. Last error: {last_error}"
    if isinstance(last_error, Exception):
        raise SheetsError(message) from last_error
    raise SheetsError(message)


def index_to_column(index: int) -> str:
    """
    Convert column index to letter (1=A, 2=B, etc.).
    """
    result = ""
    while index > 0:
        index -= 1
        result = chr(ord('A') + (index % 26)) + result
        index //= 26
    return result
