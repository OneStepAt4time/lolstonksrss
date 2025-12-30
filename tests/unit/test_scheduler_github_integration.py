"""
Tests for scheduler GitHub Pages integration.

This module tests the scheduler's ability to trigger GitHub Pages
updates when new articles are found.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.models import Article, ArticleSource
from src.services.scheduler import NewsScheduler


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create a mock repository for testing."""
    repo = AsyncMock()
    repo.save = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def scheduler(mock_repository: AsyncMock) -> NewsScheduler:
    """Create a scheduler instance with mock repository."""
    return NewsScheduler(mock_repository, interval_minutes=5)


@pytest.mark.asyncio
async def test_github_pages_sync_disabled_by_default(
    scheduler: NewsScheduler, mock_repository: AsyncMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that GitHub Pages sync is disabled by default."""
    # Ensure env vars don't interfere with test (remove real .env values)
    monkeypatch.delenv("ENABLE_GITHUB_PAGES_SYNC", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    # Mock settings to disable GitHub sync (test default behavior)
    with patch("src.services.scheduler.settings") as mock_settings:
        mock_settings.enable_github_pages_sync = False
        mock_settings.github_token = None
        mock_settings.github_repository = "owner/repo"

        # Mock update service to return new articles
        _mock_articles = [
            Article(
                title="Test Article",
                url="http://test.com/1",
                pub_date=datetime.utcnow(),
                guid="test-1",
                source=ArticleSource.LOL_EN_US,
                description="Test",
                categories=["News"],
            )
        ]

        with patch.object(
            scheduler.update_service, "update_all_sources", new=AsyncMock()
        ) as mock_update:
            mock_update.return_value = {
                "total_new": 1,
                "total_fetched": 1,
                "total_duplicates": 0,
            }

            # No GitHub dispatcher should be called
            with patch("src.services.scheduler.GitHubWorkflowDispatcher") as mock_dispatcher:
                await scheduler._update_job()

                # Verify dispatcher was never instantiated (feature disabled by default)
                mock_dispatcher.assert_not_called()


@pytest.mark.asyncio
async def test_github_pages_sync_enabled_with_new_articles(
    scheduler: NewsScheduler, mock_repository: AsyncMock
) -> None:
    """Test GitHub Pages sync triggers when enabled and new articles found."""
    # Mock settings to enable GitHub sync
    with patch("src.services.scheduler.settings") as mock_settings:
        mock_settings.enable_github_pages_sync = True
        mock_settings.github_token = "ghp_test_token"
        mock_settings.github_repository = "owner/repo"

        # Mock update service
        with patch.object(
            scheduler.update_service, "update_all_sources", new=AsyncMock()
        ) as mock_update:
            mock_update.return_value = {
                "total_new": 3,
                "total_fetched": 5,
                "total_duplicates": 2,
            }

            # Mock GitHub dispatcher
            with patch("src.services.scheduler.GitHubWorkflowDispatcher") as mock_dispatcher_class:
                mock_dispatcher = Mock()
                mock_dispatcher.trigger_workflow = AsyncMock(return_value=True)
                mock_dispatcher_class.return_value = mock_dispatcher

                _stats = await scheduler._update_job()

                # Verify dispatcher was instantiated
                mock_dispatcher_class.assert_called_once_with(
                    token="ghp_test_token", repository="owner/repo"
                )

                # Verify workflow was triggered
                mock_dispatcher.trigger_workflow.assert_called_once_with(
                    workflow_file="publish-news.yml",
                    inputs={
                        "triggered_by": "windows-app",
                        "reason": "new-articles-found-3",
                    },
                )


@pytest.mark.asyncio
async def test_github_pages_sync_not_triggered_without_new_articles(
    scheduler: NewsScheduler, mock_repository: AsyncMock
) -> None:
    """Test GitHub Pages sync doesn't trigger when no new articles."""
    with patch("src.services.scheduler.settings") as mock_settings:
        mock_settings.enable_github_pages_sync = True
        mock_settings.github_token = "ghp_test_token"
        mock_settings.github_repository = "owner/repo"

        with patch.object(
            scheduler.update_service, "update_all_sources", new=AsyncMock()
        ) as mock_update:
            # No new articles
            mock_update.return_value = {
                "total_new": 0,
                "total_fetched": 5,
                "total_duplicates": 5,
            }

            with patch("src.services.scheduler.GitHubWorkflowDispatcher") as mock_dispatcher_class:
                await scheduler._update_job()

                # Dispatcher should not be instantiated if no new articles
                mock_dispatcher_class.assert_not_called()


@pytest.mark.asyncio
async def test_github_pages_sync_warning_when_token_missing(
    scheduler: NewsScheduler, mock_repository: AsyncMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test warning logged when sync enabled but token not configured."""
    import logging

    caplog.set_level(logging.WARNING)

    with patch("src.services.scheduler.settings") as mock_settings:
        mock_settings.enable_github_pages_sync = True
        mock_settings.github_token = None  # Missing token
        mock_settings.github_repository = "owner/repo"

        with patch.object(
            scheduler.update_service, "update_all_sources", new=AsyncMock()
        ) as mock_update:
            mock_update.return_value = {"total_new": 1, "total_fetched": 1}

            await scheduler._update_job()

            # Verify warning logged
            assert "GITHUB_TOKEN not configured" in caplog.text


@pytest.mark.asyncio
async def test_github_pages_sync_error_doesnt_crash_scheduler(
    scheduler: NewsScheduler, mock_repository: AsyncMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that GitHub API errors don't crash the scheduler."""
    import logging

    caplog.set_level(logging.ERROR)

    with patch("src.services.scheduler.settings") as mock_settings:
        mock_settings.enable_github_pages_sync = True
        mock_settings.github_token = "ghp_test_token"
        mock_settings.github_repository = "owner/repo"

        with patch.object(
            scheduler.update_service, "update_all_sources", new=AsyncMock()
        ) as mock_update:
            mock_update.return_value = {"total_new": 1, "total_fetched": 1}

            # Mock dispatcher to raise exception
            with patch("src.services.scheduler.GitHubWorkflowDispatcher") as mock_dispatcher_class:
                mock_dispatcher = Mock()
                mock_dispatcher.trigger_workflow = AsyncMock(
                    side_effect=Exception("GitHub API error")
                )
                mock_dispatcher_class.return_value = mock_dispatcher

                # Should not raise exception
                stats = await scheduler._update_job()

                # Verify error logged
                assert "Failed to trigger GitHub Pages update" in caplog.text

                # Stats should still be returned
                assert stats["total_new"] == 1


@pytest.mark.asyncio
async def test_github_pages_sync_workflow_trigger_failure(
    scheduler: NewsScheduler, mock_repository: AsyncMock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling when workflow trigger returns False."""
    import logging

    caplog.set_level(logging.INFO)

    with patch("src.services.scheduler.settings") as mock_settings:
        mock_settings.enable_github_pages_sync = True
        mock_settings.github_token = "ghp_test_token"
        mock_settings.github_repository = "owner/repo"

        with patch.object(
            scheduler.update_service, "update_all_sources", new=AsyncMock()
        ) as mock_update:
            mock_update.return_value = {"total_new": 2, "total_fetched": 2}

            with patch("src.services.scheduler.GitHubWorkflowDispatcher") as mock_dispatcher_class:
                mock_dispatcher = Mock()
                mock_dispatcher.trigger_workflow = AsyncMock(return_value=False)
                mock_dispatcher_class.return_value = mock_dispatcher

                await scheduler._update_job()

                # Should not log success message
                assert "GitHub Pages update triggered" not in caplog.text
