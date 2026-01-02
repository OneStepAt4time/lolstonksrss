import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

import httpx

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 900.0
    half_open_max_calls: int = 3
    retry_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    retry_jitter: float = 0.1


@dataclass
class CircuitBreakerStats:
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    total_failure_count: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    opened_at: datetime | None = None
    total_calls: int = 0
    total_retries: int = 0


class CircuitBreakerOpenError(Exception):
    def __init__(self, source: str, message: str) -> None:
        self.source = source
        super().__init__(message)


class CircuitBreaker:
    def __init__(self, source: str, config: "CircuitBreakerConfig | None" = None) -> None:
        self.source = source
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    def is_open(self) -> bool:
        return self.stats.state == CircuitBreakerState.OPEN

    def is_closed(self) -> bool:
        return self.stats.state == CircuitBreakerState.CLOSED

    def is_half_open(self) -> bool:
        return self.stats.state == CircuitBreakerState.HALF_OPEN

    async def call(self, func: "Callable[..., Awaitable[T]]", *args: Any, **kwargs: Any) -> T:
        async with self._lock:
            if self.stats.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"[CB:{self.source}] Recovery timeout, HALF_OPEN")
                    self.stats.state = CircuitBreakerState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    self.stats.total_calls += 1
                    logger.warning(f"[CB:{self.source}] Circuit OPEN, rejecting")
                    raise CircuitBreakerOpenError(
                        self.source, f"Circuit breaker is OPEN for source {self.source!r}"
                    )
        try:
            result = await self._call_with_retry(func, *args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    async def _call_with_retry(
        self, func: "Callable[..., Awaitable[T]]", *args: Any, **kwargs: Any
    ) -> T:
        last_exception: Exception | None = None
        for attempt in range(self.config.retry_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                self.stats.total_retries += 1
                if attempt == self.config.retry_attempts - 1:
                    break
                delay = self._calculate_retry_delay(attempt)
                logger.info(
                    f"[CB:{self.source}] Retry {attempt + 1}/{self.config.retry_attempts} after {delay:.2f}s"
                )
                await asyncio.sleep(delay)
        assert last_exception is not None
        raise last_exception

    def _calculate_retry_delay(self, attempt: int) -> float:
        exponential_delay = self.config.retry_base_delay * (2**attempt)
        jitter_range = exponential_delay * self.config.retry_jitter
        jitter = random.uniform(-jitter_range, jitter_range)
        return float(max(0.1, min(exponential_delay + jitter, self.config.retry_max_delay)))

    def _should_attempt_reset(self) -> bool:
        if self.stats.opened_at is None:
            return False
        elapsed = (datetime.utcnow() - self.stats.opened_at).total_seconds()
        return elapsed >= self.config.recovery_timeout

    async def _on_success(self) -> None:
        async with self._lock:
            self.stats.total_calls += 1
            self.stats.success_count += 1
            self.stats.last_success_time = datetime.utcnow()
            self.stats.failure_count = 0
            if self.stats.state == CircuitBreakerState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.config.half_open_max_calls:
                    logger.info(f"[CB:{self.source}] Recovery successful, closing circuit")
                    self.stats.state = CircuitBreakerState.CLOSED
                    self.stats.opened_at = None
                    self._half_open_calls = 0

    async def _on_failure(self, error: Exception) -> None:
        async with self._lock:
            self.stats.total_calls += 1
            self.stats.total_failure_count += 1
            self.stats.failure_count += 1
            self.stats.last_failure_time = datetime.utcnow()
            is_retriable = self._is_retriable_error(error)
            if is_retriable:
                if self.stats.state == CircuitBreakerState.HALF_OPEN:
                    logger.warning(f"[CB:{self.source}] Failure in HALF_OPEN, reopening")
                    self.stats.state = CircuitBreakerState.OPEN
                    self.stats.opened_at = datetime.utcnow()
                    self._half_open_calls = 0
                elif self.stats.failure_count >= self.config.failure_threshold:
                    logger.warning(f"[CB:{self.source}] Threshold reached, opening circuit")
                    self.stats.state = CircuitBreakerState.OPEN
                    self.stats.opened_at = datetime.utcnow()

    def _is_retriable_error(self, error: Exception) -> bool:
        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
            return status >= 500 or status == 429
        if isinstance(
            error, (httpx.TimeoutException, httpx.NetworkError, ConnectionError, OSError)
        ):
            return True
        return False

    def reset(self) -> None:
        logger.info(f"[CB:{self.source}] Manual reset to CLOSED")
        self.stats = CircuitBreakerStats()
        self._half_open_calls = 0

    def get_metrics(self) -> dict[str, Any]:
        return {
            "circuit_breaker_state": 1 if self.is_closed() else 0,
            f"circuit_breaker_state_{self.stats.state.value}": 1,
            "circuit_breaker_failures_total": self.stats.total_failure_count,
            "circuit_breaker_successes_total": self.stats.success_count,
            "circuit_breaker_calls_total": self.stats.total_calls,
            "circuit_breaker_retries_total": self.stats.total_retries,
            "circuit_breaker_failure_count": self.stats.failure_count,
            "circuit_breaker_open_seconds": (
                (datetime.utcnow() - self.stats.opened_at).total_seconds()
                if self.stats.opened_at
                else 0
            ),
        }

    def __repr__(self) -> str:
        return f"CircuitBreaker({self.source!r}, state={self.stats.state.value}, failures={self.stats.failure_count})"


class CircuitBreakerRegistry:
    def __init__(self) -> None:
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    def get(self, source: str, config: "CircuitBreakerConfig | None" = None) -> CircuitBreaker:
        if source not in self._circuit_breakers:
            logger.info(f"Registry: Creating circuit breaker for {source}")
            self._circuit_breakers[source] = CircuitBreaker(source, config)
        return self._circuit_breakers[source]

    def get_all(self) -> dict[str, CircuitBreaker]:
        return self._circuit_breakers.copy()

    def reset_all(self) -> None:
        for cb in self._circuit_breakers.values():
            cb.reset()
        logger.info("Registry: All circuit breakers reset")

    def get_metrics(self) -> dict[str, dict[str, Any]]:
        return {source: cb.get_metrics() for source, cb in self._circuit_breakers.items()}


_global_registry = CircuitBreakerRegistry()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    return _global_registry
