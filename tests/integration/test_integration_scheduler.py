"""
Integration tests for the scheduler and update service.

This module tests the full integration of scheduler, update service,
database, and API client working together.
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime

from src.database import ArticleRepository
from src.services.scheduler import NewsScheduler
from src.services.update_service import UpdateService


@pytest.fixture
async def test_repository(tmp_path: Path) -> ArticleRepository:
    """Create a test repository with temporary database."""
    db_path = str(tmp_path / "test.db")
    repo = ArticleRepository(db_path)
    await repo.initialize()
    return repo


@pytest.mark.asyncio
async def test_scheduler_full_integration(test_repository: ArticleRepository) -> None:
    """Test full scheduler integration with real components."""
    # Create scheduler with test repository
    scheduler = NewsScheduler(test_repository, interval_minutes=60)

    # Verify initial state
    assert not scheduler.is_running
    assert scheduler.update_service.update_count == 0

    # Start scheduler
    scheduler.start()
    assert scheduler.is_running

    # Check status
    status = scheduler.get_status()
    assert status["running"]
    assert status["interval_minutes"] == 60
    assert len(status["jobs"]) == 1

    # Stop scheduler
    scheduler.stop()
    assert not scheduler.is_running


@pytest.mark.asyncio
async def test_update_service_with_real_repository(
    test_repository: ArticleRepository,
) -> None:
    """Test update service with real repository."""
    # Create update service
    update_service = UpdateService(test_repository)

    # Check initial state
    assert update_service.update_count == 0
    assert update_service.error_count == 0
    assert update_service.last_update is None

    # Note: We don't run actual update to avoid hitting real API
    # Just verify the service is properly initialized
    status = update_service.get_status()
    assert status["update_count"] == 0
    assert status["sources"] == ["en-us", "it-it"]


@pytest.mark.asyncio
async def test_scheduler_lifecycle(test_repository: ArticleRepository) -> None:
    """Test complete scheduler lifecycle."""
    scheduler = NewsScheduler(test_repository, interval_minutes=1)

    # Initial state
    assert not scheduler.is_running

    # Start
    scheduler.start()
    assert scheduler.is_running

    # Multiple start attempts should be safe
    scheduler.start()
    assert scheduler.is_running

    # Stop
    scheduler.stop()
    assert not scheduler.is_running

    # Multiple stop attempts should be safe
    scheduler.stop()
    assert not scheduler.is_running


@pytest.mark.asyncio
async def test_repository_database_operations(test_repository: ArticleRepository) -> None:
    """Test that repository works correctly with scheduler."""
    from src.models import Article, ArticleSource

    # Create test article
    article = Article(
        title="Integration Test Article",
        url="http://test.example.com/article",
        pub_date=datetime.utcnow(),
        guid="integration-test-1",
        source=ArticleSource.LOL_EN_US,
        description="Test article for integration testing",
        categories=["Test"],
    )

    # Save article
    saved = await test_repository.save(article)
    assert saved is True

    # Duplicate should return False
    saved_again = await test_repository.save(article)
    assert saved_again is False

    # Retrieve article
    retrieved = await test_repository.get_by_guid("integration-test-1")
    assert retrieved is not None
    assert retrieved.title == "Integration Test Article"

    # Count articles
    count = await test_repository.count()
    assert count == 1

    # Get latest
    latest = await test_repository.get_latest(limit=10)
    assert len(latest) == 1
    assert latest[0].title == "Integration Test Article"
