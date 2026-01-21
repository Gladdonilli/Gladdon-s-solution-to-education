"""Canvas course fetching with rate limit handling."""

import time
from typing import Any

from canvasapi.exceptions import RateLimitExceeded

from canvas_sync.api.auth import get_canvas_client


class RateLimitError(Exception):
    """Raised when rate limit exceeded after max retries."""


def with_backoff(func: callable, max_retries: int = 3) -> Any:
    """Execute function with exponential backoff on rate limit.

    Args:
        func: Callable to execute
        max_retries: Maximum number of retry attempts

    Returns:
        Result of func()

    Raises:
        RateLimitError: When rate limit exceeded after max_retries
    """
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitExceeded:
            if attempt == max_retries - 1:
                raise RateLimitError(
                    f"Rate limit exceeded after {max_retries} retries"
                )
            delay = 2**attempt
            time.sleep(delay)
    raise RateLimitError(f"Rate limit exceeded after {max_retries} retries")


def get_all_courses(vault_path: str | None = None) -> list[Any]:
    """Fetch all active courses for authenticated user.

    Args:
        vault_path: Path to vault for config. Uses default if None.

    Returns:
        List of Canvas course objects

    Raises:
        RateLimitError: When rate limit exceeded after retries
        ConfigError: When no API token configured
    """
    canvas = get_canvas_client(vault_path)
    return list(with_backoff(lambda: canvas.get_courses(enrollment_state="active")))


def get_course_details(course_id: int, vault_path: str | None = None) -> Any:
    """Fetch single course with syllabus and term info.

    Args:
        course_id: Canvas course ID
        vault_path: Path to vault for config. Uses default if None.

    Returns:
        Canvas course object with syllabus_body and term

    Raises:
        RateLimitError: When rate limit exceeded after retries
        ConfigError: When no API token configured
    """
    canvas = get_canvas_client(vault_path)
    return with_backoff(
        lambda: canvas.get_course(course_id, include=["syllabus_body", "term"])
    )
