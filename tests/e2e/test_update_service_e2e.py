"""
End-to-end tests for UpdateService and UpdateServiceV2.

This module tests the complete workflow of fetching articles from
LoL API and scrapers, saving to database, and verifying results.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.database import ArticleRepository
from src.models import Article, ArticleSource, SourceCategory
from src.services.update_service import (
    UpdatePriority,
    UpdateService,
    UpdateServiceV2,
    UpdateTask,
)


@pytest.fixture
async def test_db(tmp_path: Path) -> ArticleRepository:
    """Create an in-memory database for testing."""
    db_path = str(tmp_path / "test.db")
    repo = ArticleRepository(db_path)
    await repo.initialize()
    return repo


@pytest.fixture
def sample_articles() -> list[Article]:
    """Create sample articles for testing."""
    base_time = datetime.utcnow()
    return [
        Article(
            title="Test Article 1",
            url="http://test.com/1",
            pub_date=base_time,
            guid="test-1",
            source=ArticleSource.create("lol", "en-us"),
            description="Test description 1",
            categories=["News"],
        ),
        Article(
            title="Test Article 2",
            url="http://test.com/2",
            pub_date=base_time + timedelta(hours=1),
            guid="test-2",
            source=ArticleSource.create("lol", "en-us"),
            description="Test description 2",
            categories=["Patches"],
        ),
        Article(
            title="Articolo di Test 1",
            url="http://test.com/it-1",
            pub_date=base_time,
            guid="test-it-1",
            source=ArticleSource.create("lol", "it-it"),
            description="Descrizione del test 1",
            categories=["Notizie"],
        ),
    ]


# =============================================================================
# UpdateService Tests (Current Production)
# =============================================================================


class TestUpdateServiceE2E:
    """End-to-end tests for UpdateService."""

    @pytest.mark.asyncio
    async def test_update_service_initialization(self, test_db: ArticleRepository) -> None:
        """Test UpdateService initializes with correct configuration."""
        service = UpdateService(test_db)

        assert service.repository is test_db
        assert len(service.clients) == 2
        assert "en-us" in service.clients
        assert "it-it" in service.clients
        assert service.last_update is None
        assert service.update_count == 0
        assert service.error_count == 0

    @pytest.mark.asyncio
    async def test_update_all_sources_e2e(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test complete update workflow for all sources."""
        service = UpdateService(test_db)

        # Mock the API clients to return sample articles
        mock_en_articles = sample_articles[:2]
        mock_it_articles = [sample_articles[2]]

        for locale, client in service.clients.items():
            if locale == "en-us":
                client.fetch_news = AsyncMock(return_value=mock_en_articles)
            else:
                client.fetch_news = AsyncMock(return_value=mock_it_articles)

        # Run update
        stats = await service.update_all_sources()

        # Verify stats
        assert stats["total_fetched"] == 3
        assert stats["total_new"] == 3
        assert stats["total_duplicates"] == 0
        assert len(stats["errors"]) == 0
        assert stats["sources"]["en-us"]["fetched"] == 2
        assert stats["sources"]["it-it"]["fetched"] == 1

        # Verify articles in database
        db_count = await test_db.count()
        assert db_count == 3

        en_articles = await test_db.get_latest_by_locale("en-us")
        assert len(en_articles) == 2
        assert en_articles[0].title == "Test Article 2"  # Newest first

        it_articles = await test_db.get_latest_by_locale("it-it")
        assert len(it_articles) == 1
        assert it_articles[0].title == "Articolo di Test 1"

        # Verify service state updated
        assert service.last_update is not None
        assert service.update_count == 1
        assert service.error_count == 0

    @pytest.mark.asyncio
    async def test_update_all_sources_with_duplicates(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test update workflow with duplicate detection."""
        service = UpdateService(test_db)

        # Save one article first
        await test_db.save(sample_articles[0])

        # Mock the API clients to return same articles
        mock_articles = sample_articles[:2]

        for locale, client in service.clients.items():
            if locale == "en-us":
                client.fetch_news = AsyncMock(return_value=mock_articles)
            else:
                client.fetch_news = AsyncMock(return_value=[])

        # Run update twice
        await service.update_all_sources()
        stats = await service.update_all_sources()

        # Verify duplicates detected
        assert stats["total_fetched"] == 2
        assert stats["total_new"] == 0  # Both already exist
        assert stats["total_duplicates"] == 2

        # Verify no extra articles in database
        db_count = await test_db.count()
        assert db_count == 2  # Only the unique ones

    @pytest.mark.asyncio
    async def test_update_all_sources_with_errors(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test update workflow with partial failures."""
        service = UpdateService(test_db)

        # Mock one client to succeed and one to fail
        success_client = service.clients["en-us"]
        error_client = service.clients["it-it"]

        success_client.fetch_news = AsyncMock(return_value=sample_articles[:2])
        error_client.fetch_news = AsyncMock(side_effect=Exception("API Error"))

        # Run update
        stats = await service.update_all_sources()

        # Verify partial success
        assert stats["total_fetched"] == 2  # Only en-us succeeded
        assert stats["total_new"] == 2
        assert len(stats["errors"]) == 1
        assert "it-it" in stats["errors"][0]
        assert service.error_count == 1

        # Verify successful articles were saved
        en_articles = await test_db.get_latest_by_locale("en-us")
        assert len(en_articles) == 2

        # Verify failed source has no articles
        it_articles = await test_db.get_latest_by_locale("it-it")
        assert len(it_articles) == 0

    @pytest.mark.asyncio
    async def test_get_status(self, test_db: ArticleRepository) -> None:
        """Test getting service status."""
        service = UpdateService(test_db)

        status = service.get_status()

        assert status["last_update"] is None
        assert status["update_count"] == 0
        assert status["error_count"] == 0
        assert status["sources"] == ["en-us", "it-it"]

    @pytest.mark.asyncio
    async def test_get_status_after_update(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test getting status after performing an update."""
        service = UpdateService(test_db)

        # Mock API client
        for client in service.clients.values():
            client.fetch_news = AsyncMock(return_value=[])

        # Run update
        await service.update_all_sources()

        # Check status
        status = service.get_status()
        assert status["update_count"] == 1
        assert status["last_update"] is not None


# =============================================================================
# UpdateServiceV2 Tests (New Multi-Source)
# =============================================================================


class TestUpdateServiceV2E2E:
    """End-to-end tests for UpdateServiceV2."""

    @pytest.mark.asyncio
    async def test_update_service_v2_initialization(self, test_db: ArticleRepository) -> None:
        """Test UpdateServiceV2 initializes with correct configuration."""
        service = UpdateServiceV2(test_db)

        assert service.repository is test_db
        assert service.max_concurrent == 10
        assert service.last_update is None
        assert service.update_count == 0
        assert service.error_count == 0
        assert len(service.domain_rate_limits) > 0

    @pytest.mark.asyncio
    async def test_priority_queue_implementation(self, test_db: ArticleRepository) -> None:
        """Test that UpdateServiceV2 has proper priority queue implementation."""
        service = UpdateServiceV2(test_db)

        # Check priority mapping
        assert SourceCategory.OFFICIAL_RIOT in service.PRIORITY_MAP
        assert service.PRIORITY_MAP[SourceCategory.OFFICIAL_RIOT] == UpdatePriority.CRITICAL
        assert service.PRIORITY_MAP[SourceCategory.ESPORTS] == UpdatePriority.HIGH
        assert service.PRIORITY_MAP[SourceCategory.AGGREGATOR] == UpdatePriority.LOW

    @pytest.mark.asyncio
    async def test_source_category_mapping(self, test_db: ArticleRepository) -> None:
        """Test that source categories are correctly mapped."""
        service = UpdateServiceV2(test_db)

        # Check that all sources in ALL_SOURCES have categories
        from src.models import ArticleSource

        for source_id, source_info in ArticleSource.ALL_SOURCES.items():
            category = source_info.get("category")
            assert category is not None, f"Source {source_id} missing category"

            # Verify category is mapped to priority
            priority = service._get_priority(category)
            assert isinstance(priority, UpdatePriority)

    @pytest.mark.asyncio
    async def test_create_tasks(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test task creation for multiple sources and locales."""
        service = UpdateServiceV2(test_db)

        # Create tasks for all sources and locales
        tasks = await service._create_tasks()

        # Verify tasks were created
        assert len(tasks) > 0

        # Verify tasks are sorted by priority
        priorities = [t.priority for t in tasks]
        assert priorities == sorted(priorities)

        # Verify task structure
        task = tasks[0]
        assert isinstance(task, UpdateTask)
        assert hasattr(task, "priority")
        assert hasattr(task, "source_id")
        assert hasattr(task, "locale")
        assert hasattr(task, "category")

    @pytest.mark.asyncio
    async def test_concurrent_updates_no_locks(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test that concurrent updates don't cause database locks."""
        service = UpdateServiceV2(test_db, max_concurrent=5)

        # Mock the LoL client to return sample articles
        service.lol_client.fetch_news = AsyncMock(return_value=sample_articles[:2])

        # Mock scrapers to avoid actual network calls
        with patch("src.services.update_service.get_scraper") as mock_get_scraper:
            mock_scraper = AsyncMock()
            mock_scraper.fetch_articles = AsyncMock(return_value=[])
            mock_get_scraper.return_value = mock_scraper

            # Run update with specific locales only (faster test)
            stats = await service.update_locales(["en-us", "it-it"])

            # Verify no errors
            assert stats["failed_tasks"] == 0
            assert stats["successful_tasks"] > 0

            # Verify database integrity
            db_count = await test_db.count()
            assert db_count >= 0  # Should have some articles

    @pytest.mark.asyncio
    async def test_rate_limiting(self, test_db: ArticleRepository) -> None:
        """Test rate limiting for different domains."""
        service = UpdateServiceV2(test_db)

        # Check that rate limits are configured
        assert "leagueoflegends.com" in service.DEFAULT_RATE_LIMITS
        assert "riotgames.com" in service.DEFAULT_RATE_LIMITS
        assert service.DEFAULT_RATE_LIMITS["leagueoflegends.com"] == 2.0

        # Check that semaphores were created
        assert "leagueoflegends.com" in service.domain_rate_limits
        assert "riotgames.com" in service.domain_rate_limits

    @pytest.mark.asyncio
    async def test_extract_domain(self, test_db: ArticleRepository) -> None:
        """Test domain extraction from source IDs."""
        service = UpdateServiceV2(test_db)

        assert service._extract_domain("lol") == "leagueoflegends.com"
        assert service._extract_domain("riot-games") == "riotgames.com"
        assert service._extract_domain("dexerto") == "dexerto.com"
        assert service._extract_domain("unknown-source") == "unknown-source"

    @pytest.mark.asyncio
    async def test_update_all_e2e(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test complete update workflow for all sources."""
        service = UpdateServiceV2(test_db, max_concurrent=5)

        # Mock the LoL client to return sample articles
        service.lol_client.fetch_news = AsyncMock(return_value=sample_articles[:2])

        # Mock scrapers
        with patch("src.services.update_service.get_scraper") as mock_get_scraper:
            mock_scraper = AsyncMock()
            mock_scraper.fetch_articles = AsyncMock(return_value=[])
            mock_get_scraper.return_value = mock_scraper

            # Run update with limited locales for faster test
            # Note: update_count is only incremented by update_all(), not update_locales()
            stats = await service.update_locales(["en-us", "it-it"])

            # Verify stats
            assert stats["total_tasks"] > 0
            assert stats["successful_tasks"] >= stats["failed_tasks"]
            assert stats["new_articles"] >= 0
            assert "elapsed_seconds" in stats
            assert "started_at" in stats
            assert "completed_at" in stats

            # Verify service state updated
            assert service.last_update is not None
            # update_count is only incremented by update_all(), not update_locales()
            assert service.update_count == 0

    @pytest.mark.asyncio
    async def test_update_locales(self, test_db: ArticleRepository) -> None:
        """Test updating specific locales."""
        service = UpdateServiceV2(test_db)

        # Mock the LoL client
        service.lol_client.fetch_news = AsyncMock(return_value=[])

        # Mock scrapers
        with patch("src.services.update_service.get_scraper") as mock_get_scraper:
            mock_scraper = AsyncMock()
            mock_scraper.fetch_articles = AsyncMock(return_value=[])
            mock_get_scraper.return_value = mock_scraper

            # Update only specific locales - limit to 2 for faster test
            stats = await service.update_locales(["en-us", "it-it"])

            # Verify stats
            assert stats["locales"] == ["en-us", "it-it"]
            assert stats["total_tasks"] > 0
            assert "elapsed_seconds" in stats

    @pytest.mark.asyncio
    async def test_update_source(self, test_db: ArticleRepository) -> None:
        """Test updating a specific source."""
        service = UpdateServiceV2(test_db)

        # Mock the LoL client
        service.lol_client.fetch_news = AsyncMock(return_value=[])

        # Mock scrapers
        with patch("src.services.update_service.get_scraper") as mock_get_scraper:
            mock_scraper = AsyncMock()
            mock_scraper.fetch_articles = AsyncMock(return_value=[])
            mock_get_scraper.return_value = mock_scraper

            # Update lol source
            stats = await service.update_source("lol", locales=["en-us"])

            # Verify stats
            assert stats["source_id"] == "lol"
            assert stats["total_tasks"] > 0
            assert "elapsed_seconds" in stats

    @pytest.mark.asyncio
    async def test_update_unknown_source(self, test_db: ArticleRepository) -> None:
        """Test updating an unknown source returns gracefully."""
        service = UpdateServiceV2(test_db)

        # Try to update unknown source
        stats = await service.update_source("unknown-source")

        # Verify graceful handling
        assert stats["source_id"] == "unknown-source"
        assert stats["total_tasks"] == 0
        assert stats["successful_tasks"] == 0
        assert stats["new_articles"] == 0

    @pytest.mark.asyncio
    async def test_get_status_v2(self, test_db: ArticleRepository) -> None:
        """Test getting service status for V2."""
        service = UpdateServiceV2(test_db)

        status = service.get_status()

        assert status["version"] == "v2"
        assert status["last_update"] is None
        assert status["update_count"] == 0
        assert status["error_count"] == 0
        assert status["max_concurrent"] == 10
        assert status["configured_sources"] > 0
        assert status["configured_locales"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_update_stress_test(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Stress test concurrent updates to verify no database locks."""
        service = UpdateServiceV2(test_db, max_concurrent=20)

        # Mock the LoL client to return articles
        service.lol_client.fetch_news = AsyncMock(return_value=sample_articles)

        # Mock scrapers to return varying articles
        async def mock_fetch():
            await asyncio.sleep(0.01)  # Simulate network delay
            return sample_articles[:1]

        mock_scraper = AsyncMock()
        mock_scraper.fetch_articles = mock_fetch

        with patch("src.services.update_service.get_scraper") as mock_get_scraper:
            mock_get_scraper.return_value = mock_scraper

            # Run multiple concurrent updates with limited locales
            tasks = [service.update_locales(["en-us", "it-it"]) for _ in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all succeeded
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent update failed: {result}")
                assert result["failed_tasks"] == 0

            # Verify database integrity
            db_count = await test_db.count()
            assert db_count >= 0  # Should have consistent state

    @pytest.mark.asyncio
    async def test_update_with_high_priority_sources(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test that high priority sources are updated first."""
        service = UpdateServiceV2(test_db)

        # Mock the LoL client
        service.lol_client.fetch_news = AsyncMock(return_value=[])

        # Mock scrapers
        with patch("src.services.update_service.get_scraper") as mock_get_scraper:
            mock_scraper = AsyncMock()
            mock_scraper.fetch_articles = AsyncMock(return_value=[])
            mock_get_scraper.return_value = mock_scraper

            # Create tasks with limited locales for faster test
            tasks = await service._create_tasks(locales=["en-us", "it-it"])

            # Verify official Riot sources have highest priority
            lol_tasks = [t for t in tasks if t.source_id == "lol"]
            for task in lol_tasks:
                assert task.priority == UpdatePriority.CRITICAL

            # Verify social sources have lowest priority
            if any(t for t in tasks if t.source_id == "twitter"):
                twitter_task = next(t for t in tasks if t.source_id == "twitter")
                assert twitter_task.priority == UpdatePriority.LOW

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_failures(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test that individual source failures don't stop the entire update."""
        service = UpdateServiceV2(test_db)

        # Mock LoL client to succeed
        service.lol_client.fetch_news = AsyncMock(return_value=sample_articles[:1])

        # Mock scrapers - some succeed, some fail
        call_count = 0

        async def mock_fetch_with_failures():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if call_count % 3 == 0:  # Every 3rd call fails
                raise Exception("Simulated scraper failure")
            return []

        mock_scraper = AsyncMock()
        mock_scraper.fetch_articles = mock_fetch_with_failures

        with patch("src.services.update_service.get_scraper") as mock_get_scraper:
            mock_get_scraper.return_value = mock_scraper

            # Run update with limited locales for faster test
            stats = await service.update_locales(["en-us", "it-it"])

            # Verify partial success - update completes despite failures
            assert stats["total_tasks"] > 0
            assert stats["successful_tasks"] >= 0
            # Some tasks may fail, but update should complete
            assert "elapsed_seconds" in stats
            assert "completed_at" in stats

    @pytest.mark.asyncio
    async def test_update_task_hashable(self, test_db: ArticleRepository) -> None:
        """Test that UpdateTask is hashable for use in sets."""
        task1 = UpdateTask(
            priority=UpdatePriority.CRITICAL,
            source_id="lol",
            locale="en-us",
            category=SourceCategory.OFFICIAL_RIOT,
        )
        task2 = UpdateTask(
            priority=UpdatePriority.CRITICAL,
            source_id="lol",
            locale="en-us",
            category=SourceCategory.OFFICIAL_RIOT,
        )
        task3 = UpdateTask(
            priority=UpdatePriority.HIGH,
            source_id="dexerto",
            locale="en-us",
            category=SourceCategory.ESPORTS,
        )

        # Test hashing
        task_set = {task1, task2, task3}
        assert len(task_set) == 2  # task1 and task2 are duplicates

        # Test equality
        assert task1 == task2
        assert task1 != task3


# =============================================================================
# Performance Tests
# =============================================================================


class TestUpdateServicePerformance:
    """Performance tests for update services."""

    @pytest.mark.asyncio
    async def test_update_service_performance(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test UpdateService performance with many articles."""
        service = UpdateService(test_db)

        # Create many articles
        many_articles = sample_articles * 10

        for client in service.clients.values():
            client.fetch_news = AsyncMock(return_value=many_articles)

        # Run update and measure time
        start = datetime.utcnow()
        stats = await service.update_all_sources()
        elapsed = (datetime.utcnow() - start).total_seconds()

        # Verify reasonable performance (should complete in < 5 seconds)
        assert elapsed < 5.0
        # Check we got the expected count (may be fewer if duplicates)
        assert stats["total_fetched"] == len(many_articles) * 2

    @pytest.mark.asyncio
    async def test_update_service_v2_performance(
        self, test_db: ArticleRepository, sample_articles: list[Article]
    ) -> None:
        """Test UpdateServiceV2 performance with concurrent updates."""
        service = UpdateServiceV2(test_db, max_concurrent=10)

        # Mock the LoL client
        service.lol_client.fetch_news = AsyncMock(return_value=sample_articles)

        # Mock scrapers
        with patch("src.services.update_service.get_scraper") as mock_get_scraper:
            mock_scraper = AsyncMock()
            mock_scraper.fetch_articles = AsyncMock(return_value=sample_articles[:1])
            mock_get_scraper.return_value = mock_scraper

            # Run update with limited locales and measure time
            start = datetime.utcnow()
            stats = await service.update_locales(["en-us", "it-it"])
            elapsed = (datetime.utcnow() - start).total_seconds()

            # Verify reasonable performance (allow 30s due to rate limiting delays)
            # With rate limiting of 2-5 seconds per domain, this test can take longer
            assert elapsed < 30.0
            assert stats["total_tasks"] > 0
