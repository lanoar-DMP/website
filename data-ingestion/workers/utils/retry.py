"""Retry and circuit-breaker utilities for external API calls.

Provides:

- :func:`retry_with_backoff` — exponential backoff retry (max 3 retries,
  1s/2s/4s delays) with integrated circuit-breaker awareness.
- :func:`is_circuit_open` — check whether a service's circuit breaker
  is currently tripped.
- :func:`record_result` — record a success/failure for circuit-breaker
  tracking.

Circuit breaker logic
---------------------
If >50% of requests to a service fail within a rolling 5-minute window,
the circuit **opens** and all subsequent calls raise
:class:`RuntimeError` for a 15-minute cooldown period.  After the
cooldown the circuit resets automatically on the next call.

Spec: :ref:`ARCHITECTURE.md §4.11 (REL-03)<ARCHITECTURE.md#262-264>`.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

# Circuit state per service
_failure_window: Dict[str, list] = defaultdict(list)
_circuit_open_until: Dict[str, float] = {}

WINDOW_SECONDS = 300  # 5 minutes
ERROR_THRESHOLD = 0.5  # 50%
COOLDOWN_SECONDS = 900  # 15 minutes


def is_circuit_open(service_name: str) -> bool:
    """Check if circuit breaker is open for a service.

    Parameters
    ----------
    service_name : str
        Unique name for the external service (e.g. ``'fred'``,
        ``'yfinance'``, ``'defillama'``).

    Returns
    -------
    bool
        ``True`` if the circuit is open (requests should be blocked).
    """
    if service_name not in _circuit_open_until:
        return False
    if time.monotonic() > _circuit_open_until[service_name]:
        del _circuit_open_until[service_name]
        _failure_window[service_name].clear()
        return False
    return True


def record_result(service_name: str, success: bool) -> None:
    """Record a success/failure for circuit breaker tracking.

    Parameters
    ----------
    service_name : str
        Unique name for the external service.
    success : bool
        ``True`` if the API call succeeded, ``False`` otherwise.
    """
    now = time.monotonic()
    _failure_window[service_name].append((now, success))
    # Prune old entries
    cutoff = now - WINDOW_SECONDS
    _failure_window[service_name] = [
        (t, s) for t, s in _failure_window[service_name] if t > cutoff
    ]
    # Check threshold
    window = _failure_window[service_name]
    if len(window) >= 3:
        failures = sum(1 for _, s in window if not s)
        if failures / len(window) > ERROR_THRESHOLD:
            _circuit_open_until[service_name] = now + COOLDOWN_SECONDS
            logger.warning(
                "Circuit BREAKER OPEN for %s — %.0f%% failure rate over %ds. "
                "Cooling down for %ds.",
                service_name,
                failures / len(window) * 100,
                WINDOW_SECONDS,
                COOLDOWN_SECONDS,
            )


async def retry_with_backoff(
    coro_factory: Callable[[], Any],
    service_name: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """Execute with exponential backoff retry + circuit breaker check.

    Checks the circuit breaker before each attempt.  If the circuit is
    open, raises :class:`RuntimeError` immediately without attempting
    the call.

    Parameters
    ----------
    coro_factory : Callable
        A zero-argument callable that returns an awaitable coroutine.
        The factory pattern ensures a fresh coroutine is created for
        each retry attempt.
    service_name : str
        Unique name for the external service (for circuit breaker
        tracking).
    max_retries : int
        Maximum number of **retries** (total attempts = max_retries + 1).
        Default 3.
    base_delay : float
        Base delay in seconds for exponential backoff.  Actual delay
        is ``base_delay * (2 ** attempt)``.

    Returns
    -------
    Any
        The return value of the successful coroutine call.

    Raises
    ------
    RuntimeError
        If the circuit breaker is open.
    Exception
        The last exception raised, if all retries are exhausted.
    """
    if is_circuit_open(service_name):
        raise RuntimeError(f"Circuit breaker OPEN for {service_name}")

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            result = await coro_factory()
            record_result(service_name, True)
            return result
        except Exception as exc:
            last_exc = exc
            record_result(service_name, False)
            if attempt < max_retries:
                delay = base_delay * (2**attempt)
                logger.warning(
                    "%s attempt %d/%d failed: %s. Retrying in %.1fs …",
                    service_name,
                    attempt + 1,
                    max_retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)

    # All retries exhausted — propagate the last exception
    raise last_exc  # type: ignore[misc]
