"""
Tests for NewsScheduler.

This module tests the scheduler functionality including
periodic updates, manual triggers, and status reporting.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.services.scheduler import NewsScheduler


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create a mock repository for testing."""
    return AsyncMock()


@pytest.fixture
def scheduler(mock_repository: AsyncMock) -> NewsScheduler:
    """Create a NewsScheduler instance with mock repository."""
    return NewsScheduler(mock_repository, interval_minutes=1)


def test_scheduler_initialization(scheduler: NewsScheduler) -> None:
    """Test that NewsScheduler initializes correctly."""
    assert scheduler.interval_minutes == 1
    assert not scheduler.is_running
    assert scheduler.repository is not None
    assert scheduler.update_service is not None
    assert scheduler.scheduler is not None


def test_scheduler_start(scheduler: NewsScheduler) -> None:
    """Test starting the scheduler."""
    scheduler.start()
    assert scheduler.is_running
    assert len(scheduler.scheduler.get_jobs()) == 1

    # Verify job properties
    job = scheduler.scheduler.get_jobs()[0]
    assert job.id == "update_news"
    assert job.name == "Update LoL News"

    # Stop scheduler
    scheduler.stop()


def test_scheduler_start_already_running(
    scheduler: NewsScheduler, caplog: pytest.LogCaptureFixture
) -> None:
    """Test starting scheduler when already running."""
    import logging

    caplog.set_level(logging.WARNING)

    scheduler.start()
    scheduler.start()  # Try to start again

    assert "already running" in caplog.text
    scheduler.stop()


def test_scheduler_stop(scheduler: NewsScheduler) -> None:
    """Test stopping the scheduler."""
    scheduler.start()
    assert scheduler.is_running

    scheduler.stop()
    assert not scheduler.is_running


def test_scheduler_stop_not_running(scheduler: NewsScheduler) -> None:
    """Test stopping scheduler when not running."""
    # Should not raise an error
    scheduler.stop()
    assert not scheduler.is_running


@pytest.mark.asyncio
async def test_manual_trigger(scheduler: NewsScheduler) -> None:
    """Test manually triggering an update."""
    # Mock the update service
    mock_stats = {
        "total_new": 5,
        "total_fetched": 10,
        "total_duplicates": 5,
        "errors": [],
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "elapsed_seconds": 1.5,
    }

    with patch.object(scheduler.update_service, "update_all_sources", return_value=mock_stats):
        stats = await scheduler.trigger_update_now()
        assert "total_new" in stats
        assert stats["total_new"] == 5


@pytest.mark.asyncio
async def test_manual_trigger_with_error(scheduler: NewsScheduler) -> None:
    """Test manual trigger when update fails."""
    # Mock update service to raise an exception
    with patch.object(
        scheduler.update_service,
        "update_all_sources",
        side_effect=Exception("Update failed"),
    ):
        stats = await scheduler.trigger_update_now()
        assert "error" in stats
        assert "Update failed" in stats["error"]


def test_get_status_not_running(scheduler: NewsScheduler) -> None:
    """Test getting status when scheduler is not running."""
    status = scheduler.get_status()

    assert "running" in status
    assert "interval_minutes" in status
    assert "jobs" in status
    assert "update_service" in status
    assert status["running"] is False
    assert status["interval_minutes"] == 1
    assert len(status["jobs"]) == 0


def test_get_status_running(scheduler: NewsScheduler) -> None:
    """Test getting status when scheduler is running."""
    scheduler.start()

    status = scheduler.get_status()

    assert status["running"] is True
    assert len(status["jobs"]) == 1

    job_info = status["jobs"][0]
    assert job_info["id"] == "update_news"
    assert job_info["name"] == "Update LoL News"
    assert "next_run" in job_info

    scheduler.stop()


@pytest.mark.asyncio
async def test_update_job_success(scheduler: NewsScheduler) -> None:
    """Test the internal update job function."""
    mock_stats = {
        "total_new": 3,
        "total_fetched": 5,
        "total_duplicates": 2,
    }

    with patch.object(scheduler.update_service, "update_all_sources", return_value=mock_stats):
        stats = await scheduler._update_job()
        assert stats["total_new"] == 3
        assert stats["total_fetched"] == 5


@pytest.mark.asyncio
async def test_update_job_error(scheduler: NewsScheduler) -> None:
    """Test the internal update job function with error."""
    with patch.object(
        scheduler.update_service,
        "update_all_sources",
        side_effect=Exception("Database error"),
    ):
        stats = await scheduler._update_job()
        assert "error" in stats
        assert "timestamp" in stats
        assert "Database error" in stats["error"]


def test_scheduler_with_custom_interval(mock_repository: AsyncMock) -> None:
    """Test creating scheduler with custom interval."""
    scheduler = NewsScheduler(mock_repository, interval_minutes=60)
    assert scheduler.interval_minutes == 60

    scheduler.start()
    status = scheduler.get_status()
    assert status["interval_minutes"] == 60

    scheduler.stop()


def test_scheduler_prevents_overlapping_jobs(scheduler: NewsScheduler) -> None:
    """Test that scheduler is configured to prevent overlapping jobs."""
    scheduler.start()

    job = scheduler.scheduler.get_jobs()[0]
    # APScheduler's max_instances=1 prevents overlapping
    assert job.max_instances == 1

    scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_integration_with_update_service(
    scheduler: NewsScheduler, mock_repository: AsyncMock
) -> None:
    """Test integration between scheduler and update service."""
    # Mock the API clients in the update service
    mock_client = AsyncMock()
    mock_client.fetch_news = AsyncMock(return_value=[])

    for locale in scheduler.update_service.clients:
        scheduler.update_service.clients[locale] = mock_client

    # Trigger update
    stats = await scheduler.trigger_update_now()

    # Verify update service was called
    assert "total_fetched" in stats
    assert "total_new" in stats
    assert "total_duplicates" in stats


def test_scheduler_job_configuration(scheduler: NewsScheduler) -> None:
    """Test that scheduler job is configured correctly."""
    scheduler.start()

    jobs = scheduler.scheduler.get_jobs()
    assert len(jobs) == 1

    job = jobs[0]
    assert job.id == "update_news"
    assert job.name == "Update LoL News"
    assert job.max_instances == 1
    assert job.next_run_time is not None

    scheduler.stop()
