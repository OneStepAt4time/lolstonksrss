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


@pytest.mark.asyncio
async def test_scheduler_start(scheduler: NewsScheduler) -> None:
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


@pytest.mark.asyncio
async def test_scheduler_start_already_running(
    scheduler: NewsScheduler, caplog: pytest.LogCaptureFixture
) -> None:
    """Test starting scheduler when already running."""
    import logging

    caplog.set_level(logging.WARNING)

    scheduler.start()
    scheduler.start()  # Try to start again

    assert "already running" in caplog.text
    scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_stop(scheduler: NewsScheduler) -> None:
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
    # Mock the update service (UpdateServiceV2 format)
    mock_stats = {
        "new_articles": 5,
        "total_tasks": 10,
        "successful_tasks": 8,
        "failed_tasks": 2,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "elapsed_seconds": 1.5,
    }

    with patch.object(scheduler.update_service, "update_all", return_value=mock_stats):
        stats = await scheduler.trigger_update_now()
        assert "new_articles" in stats
        assert stats["new_articles"] == 5


@pytest.mark.asyncio
async def test_manual_trigger_with_error(scheduler: NewsScheduler) -> None:
    """Test manual trigger when update fails."""
    # Mock update service to raise an exception
    with patch.object(
        scheduler.update_service,
        "update_all",
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


@pytest.mark.asyncio
async def test_get_status_running(scheduler: NewsScheduler) -> None:
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
        "new_articles": 3,
        "total_tasks": 5,
        "successful_tasks": 5,
        "failed_tasks": 0,
    }

    with patch.object(scheduler.update_service, "update_all", return_value=mock_stats):
        stats = await scheduler._update_job()
        assert stats["new_articles"] == 3
        assert stats["total_tasks"] == 5


@pytest.mark.asyncio
async def test_update_job_error(scheduler: NewsScheduler) -> None:
    """Test the internal update job function with error."""
    with patch.object(
        scheduler.update_service,
        "update_all",
        side_effect=Exception("Database error"),
    ):
        stats = await scheduler._update_job()
        assert "error" in stats
        assert "timestamp" in stats
        assert "Database error" in stats["error"]


@pytest.mark.asyncio
async def test_scheduler_with_custom_interval(mock_repository: AsyncMock) -> None:
    """Test creating scheduler with custom interval."""
    scheduler = NewsScheduler(mock_repository, interval_minutes=60)
    assert scheduler.interval_minutes == 60

    scheduler.start()
    status = scheduler.get_status()
    assert status["interval_minutes"] == 60

    scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_prevents_overlapping_jobs(scheduler: NewsScheduler) -> None:
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
    """Test integration between scheduler and UpdateServiceV2."""
    # Mock the update service to avoid real network calls
    mock_stats = {
        "new_articles": 10,
        "total_tasks": 20,
        "successful_tasks": 15,
        "failed_tasks": 5,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "elapsed_seconds": 2.5,
    }

    with patch.object(scheduler.update_service, "update_all", return_value=mock_stats):
        # Just verify the scheduler can call the update service
        stats = await scheduler.trigger_update_now()

        # Verify update service returns expected stats (UpdateServiceV2 format)
        assert "new_articles" in stats
        assert "total_tasks" in stats or "successful_tasks" in stats or "failed_tasks" in stats


@pytest.mark.asyncio
async def test_scheduler_job_configuration(scheduler: NewsScheduler) -> None:
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
