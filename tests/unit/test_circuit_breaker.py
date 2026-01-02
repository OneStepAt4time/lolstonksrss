"""
Unit tests for circuit breaker implementation.

Tests the circuit breaker pattern including state transitions,
retry logic, error classification, and metrics reporting.
"""

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from src.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
    CircuitBreakerState,
    get_circuit_breaker_registry,
)


class TestCircuitBreakerState:
    """Test circuit breaker state transitions."""

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self):
        cb = CircuitBreaker("test-source")
        assert cb.is_closed()
        assert not cb.is_open()
        assert not cb.is_half_open()

    @pytest.mark.asyncio
    async def test_opens_after_threshold_reached(self):
        config = CircuitBreakerConfig(failure_threshold=3, retry_attempts=1)
        cb = CircuitBreaker("test-source", config)

        async def failing_func():
            raise httpx.TimeoutException("Timeout")

        # First 2 failures - circuit stays closed
        for _i in range(2):
            with pytest.raises(httpx.TimeoutException):
                await cb.call(failing_func)
            assert cb.is_closed()

        # Third failure - circuit opens
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        assert cb.is_open()

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self):
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=0.1, retry_attempts=1)
        cb = CircuitBreaker("test-source", config)

        async def failing_func():
            raise httpx.TimeoutException("Timeout")

        # Open the circuit with 3 failures
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        assert cb.is_open()

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Verify circuit transitions to HALF_OPEN when attempting reset
        # The circuit should be HALF_OPEN when we check before the call completes
        assert cb._should_attempt_reset()

        # Next call should transition to HALF_OPEN, then fail and reopen
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        # Circuit reopens after failure in HALF_OPEN
        assert cb.is_open()

    @pytest.mark.asyncio
    async def test_closes_after_successful_half_open(self):
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=2,
            retry_attempts=1,
        )
        cb = CircuitBreaker("test-source", config)

        async def failing_func():
            raise httpx.TimeoutException("Timeout")

        async def success_func():
            return "success"

        # Open the circuit
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Successful calls in HALF_OPEN should close circuit
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.is_half_open()  # Still HALF_OPEN after first success

        result = await cb.call(success_func)
        assert result == "success"
        assert cb.is_closed()  # Closed after half_open_max_calls


class TestCircuitBreakerRetry:
    """Test retry with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        config = CircuitBreakerConfig(
            failure_threshold=5,
            retry_attempts=3,
            retry_base_delay=0.05,
            retry_max_delay=1.0,
        )
        cb = CircuitBreaker("test-source", config)

        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Timeout")
            return "success"

        result = await cb.call(func)
        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded on third try

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        config = CircuitBreakerConfig(
            failure_threshold=5,
            retry_attempts=2,
            retry_base_delay=0.05,
        )
        cb = CircuitBreaker("test-source", config)

        async def failing_func():
            raise httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)

        # With retry_attempts=2: loop runs twice, both fail
        # total_retries is incremented on each exception
        assert cb.stats.total_calls == 1
        assert cb.stats.total_retries == 2  # Both attempts failed


class TestErrorClassification:
    """Test error classification for retriable errors."""

    @pytest.mark.asyncio
    async def test_http_500_is_retriable(self):
        cb = CircuitBreaker("test-source", CircuitBreakerConfig(failure_threshold=2))

        async def func():
            raise httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )

        # First failure
        with pytest.raises(httpx.HTTPStatusError):
            await cb.call(func)
        assert cb.is_closed()  # Still closed after 1 failure

        # Second failure - should open circuit
        with pytest.raises(httpx.HTTPStatusError):
            await cb.call(func)
        assert cb.is_open()

    @pytest.mark.asyncio
    async def test_http_429_is_retriable(self):
        cb = CircuitBreaker("test-source", CircuitBreakerConfig(failure_threshold=2))

        async def func():
            raise httpx.HTTPStatusError(
                "Rate Limited",
                request=MagicMock(),
                response=MagicMock(status_code=429),
            )

        with pytest.raises(httpx.HTTPStatusError):
            await cb.call(func)
        with pytest.raises(httpx.HTTPStatusError):
            await cb.call(func)
        assert cb.is_open()

    @pytest.mark.asyncio
    async def test_http_404_is_not_retriable(self):
        cb = CircuitBreaker("test-source", CircuitBreakerConfig(failure_threshold=2))

        async def func():
            raise httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )

        # 404 errors should NOT open circuit
        with pytest.raises(httpx.HTTPStatusError):
            await cb.call(func)
        with pytest.raises(httpx.HTTPStatusError):
            await cb.call(func)
        assert cb.is_closed()  # Should stay closed for non-retriable errors

    @pytest.mark.asyncio
    async def test_timeout_is_retriable(self):
        cb = CircuitBreaker("test-source", CircuitBreakerConfig(failure_threshold=2))

        async def failing_func():
            raise httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        assert cb.is_open()

    @pytest.mark.asyncio
    async def test_network_error_is_retriable(self):
        cb = CircuitBreaker("test-source", CircuitBreakerConfig(failure_threshold=2))

        async def failing_func():
            raise httpx.NetworkError("Network error")

        with pytest.raises(httpx.NetworkError):
            await cb.call(failing_func)
        with pytest.raises(httpx.NetworkError):
            await cb.call(failing_func)
        assert cb.is_open()


class TestCircuitBreakerOpenError:
    """Test CircuitBreakerOpenError is raised when circuit is open."""

    @pytest.mark.asyncio
    async def test_open_circuit_raises_error(self):
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60, retry_attempts=1)
        cb = CircuitBreaker("test-source", config)

        async def failing_func():
            raise httpx.TimeoutException("Timeout")

        # Open the circuit
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)

        assert cb.is_open()

        # Next call should raise CircuitBreakerOpenError immediately
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(failing_func)

        assert exc_info.value.source == "test-source"
        assert "OPEN" in str(exc_info.value)


class TestMetrics:
    """Test metrics reporting."""

    @pytest.mark.asyncio
    async def test_metrics_include_state(self):
        cb = CircuitBreaker("test-source")
        metrics = cb.get_metrics()

        assert "circuit_breaker_state" in metrics
        assert metrics["circuit_breaker_state"] == 1  # CLOSED = 1 (healthy)

    @pytest.mark.asyncio
    async def test_metrics_track_failures(self):
        config = CircuitBreakerConfig(failure_threshold=3, retry_attempts=1)
        cb = CircuitBreaker("test-source", config)

        async def failing_func():
            raise httpx.TimeoutException("Timeout")

        # Two failures
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)

        metrics = cb.get_metrics()
        assert metrics["circuit_breaker_failures_total"] == 2
        assert metrics["circuit_breaker_failure_count"] == 2

    @pytest.mark.asyncio
    async def test_metrics_track_successes(self):
        cb = CircuitBreaker("test-source")

        async def success_func():
            return "success"

        result = await cb.call(success_func)
        assert result == "success"

        metrics = cb.get_metrics()
        assert metrics["circuit_breaker_successes_total"] == 1
        assert metrics["circuit_breaker_failure_count"] == 0

    @pytest.mark.asyncio
    async def test_metrics_track_retries(self):
        config = CircuitBreakerConfig(failure_threshold=5, retry_attempts=3)
        cb = CircuitBreaker("test-source", config)

        async def failing_func():
            raise httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)

        metrics = cb.get_metrics()
        assert metrics["circuit_breaker_retries_total"] >= 1


class TestCircuitBreakerRegistry:
    """Test the circuit breaker registry."""

    def test_registry_returns_same_instance_for_same_source(self):
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("dexerto")
        cb2 = registry.get("dexerto")
        assert cb1 is cb2

    def test_registry_creates_different_instances_for_different_sources(self):
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("dexerto")
        cb2 = registry.get("inven")
        assert cb1 is not cb2

    def test_registry_get_all(self):
        registry = CircuitBreakerRegistry()
        registry.get("dexerto")
        registry.get("inven")
        registry.get("dotesports")

        all_cbs = registry.get_all()
        assert len(all_cbs) == 3
        assert "dexerto" in all_cbs
        assert "inven" in all_cbs
        assert "dotesports" in all_cbs

    def test_registry_reset_all(self):
        registry = CircuitBreakerRegistry()
        cb = registry.get("test", config=CircuitBreakerConfig(failure_threshold=2))
        # Force circuit open by simulating failures
        cb.stats.state = CircuitBreakerState.OPEN
        cb.stats.failure_count = 5

        registry.reset_all()

        # Circuit should be reset to CLOSED
        assert cb.is_closed()
        assert cb.stats.failure_count == 0

    @pytest.mark.asyncio
    async def test_global_registry(self):
        global_registry = get_circuit_breaker_registry()
        cb1 = global_registry.get("test-source")
        cb2 = global_registry.get("test-source")
        assert cb1 is cb2


class TestManualReset:
    """Test manual reset functionality."""

    @pytest.mark.asyncio
    async def test_manual_reset_closes_circuit(self):
        config = CircuitBreakerConfig(failure_threshold=2, retry_attempts=1)
        cb = CircuitBreaker("test-source", config)

        async def failing_func():
            raise httpx.TimeoutException("Timeout")

        # Open the circuit
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_func)

        assert cb.is_open()

        # Manual reset
        cb.reset()

        assert cb.is_closed()
        assert cb.stats.failure_count == 0
