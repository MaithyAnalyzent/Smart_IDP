from __future__ import annotations
import logging
from typing import Callable, Tuple, Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

_log = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator factory that wraps an async function with exponential-backoff retry.

    Usage:
        @with_retry(max_attempts=3, retry_on=(httpx.HTTPError,))
        async def call_external_api(): ...
    """
    def decorator(func: Callable) -> Callable:
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(retry_on),
            before_sleep=before_sleep_log(_log, logging.WARNING),
            reraise=True,
        )(func)
    return decorator
