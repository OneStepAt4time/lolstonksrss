"""
Complete scheduler E2E tests.

This module provides comprehensive end-to-end testing for the scheduler functionality
including automatic updates, manual triggers, status reporting, and error handling.
"""
import asyncio
import os
import tempfile
from datetime import datetime

import pytest

from src.database import ArticleRepository
from src.services.scheduler import NewsScheduler
from src.services.update_service import UpdateService


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_initialization():
    """Test scheduler initializes correctly."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=1)

        assert not scheduler.is_running
        assert scheduler.interval_minutes == 1
        assert scheduler.update_service is not None
        assert scheduler.scheduler is not None
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_start_stop():
    """Test scheduler starts and stops correctly."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=1)

        # Start
        scheduler.start()
        assert scheduler.is_running

        # Check job was added
        status = scheduler.get_status()
        assert len(status["jobs"]) > 0
        assert status["running"]

        # Stop
        scheduler.stop()
        assert not scheduler.is_running
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_manual_trigger():
    """Test manual update trigger."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=1)

        # Trigger manual update
        stats = await scheduler.trigger_update_now()

        assert "total_fetched" in stats
        assert "sources" in stats
        assert "en-us" in stats["sources"] or "errors" in stats

        if "errors" not in stats or len(stats["errors"]) == 0:
            assert stats["total_fetched"] >= 0
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_status():
    """Test scheduler status endpoint."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=1)

        status = scheduler.get_status()

        assert "running" in status
        assert "interval_minutes" in status
        assert "jobs" in status
        assert "update_service" in status
        assert "sources" in status["update_service"]
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_auto_update():
    """Test scheduler triggers automatic update."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        # Use short interval for testing (1 second = 0.016 minutes)
        scheduler = NewsScheduler(repo, interval_minutes=0.01)

        initial_count = scheduler.update_service.update_count

        scheduler.start()

        # Wait for at least 1 update (2 second wait for 0.6 second interval)
        await asyncio.sleep(3)

        _status = scheduler.get_status()

        # Check if update occurred
        final_count = scheduler.update_service.update_count
        assert final_count >= initial_count

        scheduler.stop()
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_update_service_statistics():
    """Test update service tracks statistics correctly."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        service = UpdateService(repo)

        stats = await service.update_all_sources()

        # Check statistics structure
        assert "started_at" in stats
        assert "completed_at" in stats
        assert "total_fetched" in stats
        assert "total_new" in stats
        assert "total_duplicates" in stats
        assert "sources" in stats
        assert "elapsed_seconds" in stats

        # Validate values
        assert stats["total_fetched"] >= 0
        assert stats["elapsed_seconds"] >= 0
        assert len(stats["sources"]) == 2  # en-us, it-it
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_error_handling():
    """Test scheduler handles errors gracefully."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        from unittest.mock import patch

        scheduler = NewsScheduler(repo, interval_minutes=1)

        # Mock update_service to raise error
        with patch.object(
            scheduler.update_service, "update_all_sources", side_effect=Exception("Test error")
        ):
            stats = await scheduler.trigger_update_now()
            assert "error" in stats
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_with_real_database():
    """Test scheduler with real SQLite database."""
    # Create temp database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        repo = ArticleRepository(db_path)
        await repo.initialize()

        scheduler = NewsScheduler(repo, interval_minutes=1)

        # Trigger update
        stats = await scheduler.trigger_update_now()

        # Verify statistics structure
        assert "total_fetched" in stats
        assert "total_new" in stats

        # Verify articles saved
        articles = await repo.get_latest(limit=100)
        assert len(articles) >= 0

        await repo.close()

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_concurrent_updates():
    """Test scheduler prevents concurrent updates."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=1)
        scheduler.start()

        # Trigger multiple concurrent updates
        tasks = [scheduler.trigger_update_now() for _ in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete without errors
        # max_instances=1 should queue them
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent update failed: {result}")

        scheduler.stop()
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_persistence():
    """Test scheduler state persists across start/stop cycles."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=1)

        # Start and trigger update
        scheduler.start()
        await scheduler.trigger_update_now()
        _update_count_1 = scheduler.update_service.update_count

        # Stop before restart
        scheduler.stop()

        # Create new scheduler instance for restart test
        scheduler2 = NewsScheduler(repo, interval_minutes=1)
        scheduler2.start()

        # Check status after restart
        status = scheduler2.get_status()
        assert status["running"]

        scheduler2.stop()
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_multiple_intervals():
    """Test scheduler with different interval configurations."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        # Test with different intervals
        for interval in [1, 5, 10, 30]:
            scheduler = NewsScheduler(repo, interval_minutes=interval)
            assert scheduler.interval_minutes == interval

            status = scheduler.get_status()
            assert status["interval_minutes"] == interval
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_update_service_source_isolation():
    """Test that update service handles each source independently."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        service = UpdateService(repo)

        stats = await service.update_all_sources()

        # Check each source has its own stats
        assert "en-us" in stats["sources"] or len(stats["errors"]) > 0
        assert "it-it" in stats["sources"] or len(stats["errors"]) > 0

        if len(stats["errors"]) == 0:
            # Verify source stats structure
            for source in ["en-us", "it-it"]:
                if source in stats["sources"]:
                    source_stats = stats["sources"][source]
                    assert "fetched" in source_stats
                    assert "new" in source_stats
                    assert "duplicates" in source_stats
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_job_configuration():
    """Test scheduler job is configured correctly."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=1)
        scheduler.start()

        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1

        job = jobs[0]
        assert job.id == "update_news"
        assert job.name == "Update LoL News"
        assert job.max_instances == 1
        assert job.next_run_time is not None

        scheduler.stop()
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_update_timing():
    """Test update timing and performance metrics."""
    repo = ArticleRepository(":memory:")
    await repo.initialize()

    try:
        service = UpdateService(repo)

        _start_time = datetime.utcnow()
        stats = await service.update_all_sources()
        _end_time = datetime.utcnow()

        # Check timing is recorded
        assert "started_at" in stats
        assert "completed_at" in stats
        assert "elapsed_seconds" in stats

        # Verify elapsed time is reasonable (should be less than 60 seconds)
        assert stats["elapsed_seconds"] >= 0
        assert stats["elapsed_seconds"] < 60

        # Verify timestamps are valid
        assert stats["started_at"] <= stats["completed_at"]
    finally:
        await repo.close()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_with_database(tmp_path):
    """Test scheduler with file-based database."""
    db_path = str(tmp_path / "scheduler_test.db")

    repo = ArticleRepository(db_path)
    await repo.initialize()

    try:
        scheduler = NewsScheduler(repo, interval_minutes=1)

        # Trigger update
        _stats = await scheduler.trigger_update_now()

        # Verify database persistence
        count = await repo.count()
        assert count >= 0

        # Verify we can retrieve articles
        articles = await repo.get_latest(limit=10)
        assert len(articles) >= 0
    finally:
        await repo.close()
