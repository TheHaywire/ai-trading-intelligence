"""Time-boxed operation utilities."""

import time
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional, TypeVar

T = TypeVar("T")


class TimeoutError(Exception):
    """Raised when an operation exceeds its deadline."""

    pass


@contextmanager
def deadline(seconds: float, operation: str = "operation") -> Generator[None, None, None]:
    """
    Context manager that enforces a time limit on operations.

    Args:
        seconds: Maximum allowed time in seconds
        operation: Description of the operation for error messages

    Raises:
        TimeoutError: If the operation exceeds the deadline

    Example:
        with deadline(5.0, "broker connection"):
            connect_to_broker()
    """
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    if elapsed > seconds:
        raise TimeoutError(
            f"{operation} exceeded deadline: {elapsed:.2f}s > {seconds:.2f}s"
        )


def with_timeout(
    func: Callable[..., T],
    timeout_seconds: float,
    *args: Any,
    **kwargs: Any,
) -> Optional[T]:
    """
    Execute a function with a timeout.

    Args:
        func: Function to execute
        timeout_seconds: Maximum allowed time
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Function result or None if timeout exceeded
    """
    start = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        if elapsed > timeout_seconds:
            return None
        return result
    except Exception:
        return None


def retry_with_backoff(
    func: Callable[..., T],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to execute
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each failure
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Function result

    Raises:
        Exception: Last exception if all attempts fail
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                time.sleep(delay)
                delay *= backoff_factor

    raise last_exception  # type: ignore
