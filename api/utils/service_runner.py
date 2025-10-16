"""
Helpers for executing service layer functions inside FastAPI endpoints.

Ensures consistent translation of domain-level `ServiceError`s into HTTP
responses while supporting both synchronous and asynchronous service calls.
"""

from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, TypeVar

from fastapi import HTTPException

from api.services.errors import ServiceError

ReturnType = TypeVar("ReturnType")
ServiceCallable = Callable[..., ReturnType | Awaitable[ReturnType]]


def _ensure_awaitable(result: ReturnType | Awaitable[ReturnType]) -> Awaitable[ReturnType]:
    if inspect.isawaitable(result):
        return result  # type: ignore[return-value]

    async def _wrapper() -> ReturnType:
        return result

    return _wrapper()


async def execute_service(callable_: ServiceCallable[ReturnType], *args: Any, **kwargs: Any) -> ReturnType:
    """
    Execute a service callable and convert domain exceptions to HTTP errors.

    The callable can be synchronous or asynchronous. Any `ServiceError`
    raised will be converted into an `HTTPException` with the appropriate
    status code and detail message.
    """
    try:
        result = callable_(*args, **kwargs)
        awaited = _ensure_awaitable(result)
        return await awaited
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
