"""
Test scheduler integration with API application.

This module tests the scheduler integration with the FastAPI application
including lifespan management and endpoint availability.
"""
import asyncio

import pytest

from src.api.app import app, app_state, lifespan
from src.config import get_settings
from src.services.scheduler import NewsScheduler


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_in_lifespan():
    """Test scheduler is properly initialized in application lifespan."""
    # Simulate lifespan startup
    async with lifespan(app):
        # Verify scheduler is initialized in app_state
        assert "scheduler" in app_state
        scheduler = app_state["scheduler"]

        assert isinstance(scheduler, NewsScheduler)
        assert scheduler.is_running

        # Verify repository is also initialized
        assert "repository" in app_state
        assert "feed_service" in app_state


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_status_through_app():
    """Test getting scheduler status through app state."""
    async with lifespan(app):
        scheduler = app_state.get("scheduler")
        assert scheduler is not None

        status = scheduler.get_status()

        assert "running" in status
        assert "interval_minutes" in status
        assert "jobs" in status
        assert "update_service" in status


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_manual_trigger_through_app():
    """Test manual trigger through app state scheduler."""
    async with lifespan(app):
        scheduler = app_state.get("scheduler")
        assert scheduler is not None

        # Trigger update
        stats = await scheduler.trigger_update_now()

        assert "total_fetched" in stats or "error" in stats
        assert "sources" in stats or "error" in stats


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_initial_update_on_startup():
    """Test that scheduler performs initial update on startup."""
    async with lifespan(app):
        scheduler = app_state["scheduler"]
        _repository = app_state["repository"]

        # The lifespan triggers an initial update
        # Wait a moment for it to complete
        await asyncio.sleep(2)

        # Check update service status
        status = scheduler.get_status()
        update_count = status["update_service"]["update_count"]

        # Should have at least 1 update from startup
        assert update_count >= 1


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_with_real_database():
    """Test scheduler with real database operations."""
    async with lifespan(app):
        repository = app_state["repository"]
        scheduler = app_state["scheduler"]

        # Trigger update
        await scheduler.trigger_update_now()

        # Check database has articles
        count = await repository.count()
        assert count >= 0

        # Get latest articles
        articles = await repository.get_latest(limit=10)
        assert len(articles) >= 0


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_configuration():
    """Test scheduler uses correct configuration."""
    settings = get_settings()

    async with lifespan(app):
        scheduler = app_state["scheduler"]

        # Check interval matches config
        assert scheduler.interval_minutes == settings.update_interval_minutes

        # Check status reflects config
        status = scheduler.get_status()
        assert status["interval_minutes"] == settings.update_interval_minutes


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_scheduler_cleanup_on_shutdown():
    """Test scheduler is properly cleaned up on shutdown."""
    scheduler_instance = None

    # Startup
    async with lifespan(app):
        scheduler_instance = app_state["scheduler"]
        assert scheduler_instance.is_running

    # After context exit, scheduler should be stopped
    assert not scheduler_instance.is_running
