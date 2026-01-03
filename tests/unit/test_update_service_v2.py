"""
Tests for UpdateServiceV2 - Priority queue orchestration service.

Tests the priority-based concurrent update service including:
- Priority queue management
- Concurrent updates with semaphore limits
- Rate limiting per domain
- Multi-locale support
- Error handling and recovery
- Circuit breaker integration
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.models import Article, ArticleSource, SourceCategory
from src.services.update_service import (
    UpdatePriority,
    UpdateServiceV2,
    UpdateTask,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create a mock repository for testing."""
    repo = AsyncMock()
    repo.save = AsyncMock(return_value=True)
    repo.find_by_guid = AsyncMock(return_value=None)  # No duplicates by default
    return repo


@pytest.fixture
def update_service_v2(mock_repository: AsyncMock) -> UpdateServiceV2:
    """Create an UpdateServiceV2 instance with mock repository."""
    return UpdateServiceV2(repository=mock_repository, max_concurrent=5)


@pytest.fixture
def sample_articles() -> list[Article]:
    """Create sample articles for testing."""
    return [
        Article(
            title="Test Article 1",
            url="https://example.com/1",
            pub_date=datetime.utcnow(),
            guid="test-1",
            source=ArticleSource.create("lol", "en-us"),
            description="Test description 1",
            categories=["News"],
        ),
        Article(
            title="Test Article 2",
            url="https://example.com/2",
            pub_date=datetime.utcnow(),
            guid="test-2",
            source=ArticleSource.create("lol", "en-us"),
            description="Test description 2",
            categories=["Patches"],
        ),
    ]


# =============================================================================
# UpdateTask Tests
# =============================================================================


class TestUpdateTask:
    """Tests for UpdateTask dataclass."""

    def test_update_task_creation(self) -> None:
        """Test creating UpdateTask."""
        task = UpdateTask(
            priority=UpdatePriority.CRITICAL,
            source_id="lol",
            locale="en-us",
            category=SourceCategory.OFFICIAL_RIOT,
        )
        assert task.priority == UpdatePriority.CRITICAL
        assert task.source_id == "lol"
        assert task.locale == "en-us"
        assert task.category == SourceCategory.OFFICIAL_RIOT

    def test_update_task_ordering(self) -> None:
        """Test that UpdateTask is orderable by priority."""
        critical_task = UpdateTask(
            priority=UpdatePriority.CRITICAL,
            source_id="lol",
            locale="en-us",
            category=SourceCategory.OFFICIAL_RIOT,
        )
        low_task = UpdateTask(
            priority=UpdatePriority.LOW,
            source_id="reddit",
            locale="en-us",
            category=SourceCategory.SOCIAL,
        )
        assert critical_task < low_task

    def test_update_task_hashable(self) -> None:
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
        # Same source_id and locale should hash the same and be equal
        assert hash(task1) == hash(task2)
        assert task1 == task2
        # Can use in sets
        task_set = {task1, task2}
        assert len(task_set) == 1

    def test_update_task_not_equal_different_priority(self) -> None:
        """Test that tasks with different priorities are not equal."""
        task1 = UpdateTask(
            priority=UpdatePriority.CRITICAL,
            source_id="lol",
            locale="en-us",
            category=SourceCategory.OFFICIAL_RIOT,
        )
        task2 = UpdateTask(
            priority=UpdatePriority.HIGH,
            source_id="lol",
            locale="en-us",
            category=SourceCategory.OFFICIAL_RIOT,
        )
        # Different priorities mean different tasks (dataclass equality)
        assert task1 != task2


# =============================================================================
# UpdateServiceV2 Initialization Tests
# =============================================================================


class TestUpdateServiceV2Init:
    """Tests for UpdateServiceV2 initialization."""

    def test_initialization(self, update_service_v2: UpdateServiceV2) -> None:
        """Test UpdateServiceV2 initializes correctly."""
        assert update_service_v2.repository is not None
        assert update_service_v2.max_concurrent == 5
        assert update_service_v2.lol_client is not None
        assert update_service_v2.last_update is None
        assert update_service_v2.update_count == 0
        assert update_service_v2.error_count == 0
        assert len(update_service_v2.domain_rate_limits) > 0

    def test_domain_rate_limits_initialized(self, update_service_v2: UpdateServiceV2) -> None:
        """Test that domain rate limits are initialized."""
        assert "leagueoflegends.com" in update_service_v2.domain_rate_limits
        assert "riotgames.com" in update_service_v2.domain_rate_limits
        assert "dexerto.com" in update_service_v2.domain_rate_limits


# =============================================================================
# Get Priority Tests
# =============================================================================


class TestGetPriority:
    """Tests for _get_priority method."""

    def test_get_priority_official_riot(self, update_service_v2: UpdateServiceV2) -> None:
        """Test priority for official Riot sources."""
        priority = update_service_v2._get_priority(SourceCategory.OFFICIAL_RIOT)
        assert priority == UpdatePriority.CRITICAL

    def test_get_priority_community_hub(self, update_service_v2: UpdateServiceV2) -> None:
        """Test priority for community hub sources."""
        priority = update_service_v2._get_priority(SourceCategory.COMMUNITY_HUB)
        assert priority == UpdatePriority.HIGH

    def test_get_priority_esports(self, update_service_v2: UpdateServiceV2) -> None:
        """Test priority for esports sources."""
        priority = update_service_v2._get_priority(SourceCategory.ESPORTS)
        assert priority == UpdatePriority.HIGH

    def test_get_priority_analytics(self, update_service_v2: UpdateServiceV2) -> None:
        """Test priority for analytics sources."""
        priority = update_service_v2._get_priority(SourceCategory.ANALYTICS)
        assert priority == UpdatePriority.MEDIUM

    def test_get_priority_social(self, update_service_v2: UpdateServiceV2) -> None:
        """Test priority for social sources."""
        priority = update_service_v2._get_priority(SourceCategory.SOCIAL)
        assert priority == UpdatePriority.LOW


# =============================================================================
# Extract Domain Tests
# =============================================================================


class TestExtractDomain:
    """Tests for _extract_domain method."""

    def test_extract_domain_lol(self, update_service_v2: UpdateServiceV2) -> None:
        """Test extracting domain for lol source."""
        domain = update_service_v2._extract_domain("lol")
        assert domain == "leagueoflegends.com"

    def test_extract_domain_dexerto(self, update_service_v2: UpdateServiceV2) -> None:
        """Test extracting domain for dexerto source."""
        domain = update_service_v2._extract_domain("dexerto")
        assert domain == "dexerto.com"

    def test_extract_domain_unknown(self, update_service_v2: UpdateServiceV2) -> None:
        """Test extracting domain for unknown source returns source_id."""
        domain = update_service_v2._extract_domain("unknown-source")
        assert domain == "unknown-source"


# =============================================================================
# Respect Rate Limit Tests
# =============================================================================


class TestRespectRateLimit:
    """Tests for _respect_rate_limit method."""

    @pytest.mark.asyncio
    async def test_respect_rate_limit_known_domain(
        self, update_service_v2: UpdateServiceV2
    ) -> None:
        """Test rate limiting for known domain."""
        start_time = asyncio.get_event_loop().time()
        await update_service_v2._respect_rate_limit("lol")
        elapsed = asyncio.get_event_loop().time() - start_time
        # Should have waited approximately 2 seconds
        assert elapsed >= 1.9  # Small tolerance

    @pytest.mark.asyncio
    async def test_respect_rate_limit_unknown_domain(
        self, update_service_v2: UpdateServiceV2
    ) -> None:
        """Test rate limiting for unknown domain uses base rate."""
        start_time = asyncio.get_event_loop().time()
        await update_service_v2._respect_rate_limit("unknown-source")
        elapsed = asyncio.get_event_loop().time() - start_time
        # Should have waited approximately BASE_RATE_LIMIT (2.0s)
        assert elapsed >= 1.9

    @pytest.mark.asyncio
    async def test_respect_rate_limit_concurrent(self, update_service_v2: UpdateServiceV2) -> None:
        """Test that concurrent requests to same domain are serialized."""
        tasks = [update_service_v2._respect_rate_limit("lol") for _ in range(3)]
        start_time = asyncio.get_event_loop().time()
        await asyncio.gather(*tasks)
        elapsed = asyncio.get_event_loop().time() - start_time
        # 3 requests at 2s each = ~6s (minus some for concurrency)
        assert elapsed >= 4.0


# =============================================================================
# Fetch LoL News Tests
# =============================================================================


class TestFetchLoLNews:
    """Tests for _fetch_lol_news method."""

    @pytest.mark.asyncio
    async def test_fetch_lol_news(
        self, update_service_v2: UpdateServiceV2, sample_articles: list[Article]
    ) -> None:
        """Test fetching LoL news from API."""
        update_service_v2.lol_client.fetch_news = AsyncMock(return_value=sample_articles)

        articles = await update_service_v2._fetch_lol_news("en-us")

        assert len(articles) == 2
        assert articles[0].title == "Test Article 1"
        update_service_v2.lol_client.fetch_news.assert_called_once_with("en-us")


# =============================================================================
# Update Source Tests
# =============================================================================


class TestUpdateSourceV2:
    """Tests for _update_source method."""

    @pytest.mark.asyncio
    async def test_update_source_lol_success(
        self,
        update_service_v2: UpdateServiceV2,
        mock_repository: AsyncMock,
        sample_articles: list[Article],
    ) -> None:
        """Test updating lol source successfully."""
        task = UpdateTask(
            priority=UpdatePriority.CRITICAL,
            source_id="lol",
            locale="en-us",
            category=SourceCategory.OFFICIAL_RIOT,
        )

        update_service_v2.lol_client.fetch_news = AsyncMock(return_value=sample_articles)

        with patch.object(update_service_v2, "_respect_rate_limit", new_callable=AsyncMock):
            new_count = await update_service_v2._update_source(task)

        assert new_count == 2
        assert mock_repository.save.call_count == 2

    @pytest.mark.asyncio
    async def test_update_source_scraper_success(
        self,
        update_service_v2: UpdateServiceV2,
        mock_repository: AsyncMock,
        sample_articles: list[Article],
    ) -> None:
        """Test updating scraper-based source successfully."""
        task = UpdateTask(
            priority=UpdatePriority.HIGH,
            source_id="dexerto",
            locale="en-us",
            category=SourceCategory.ESPORTS,
        )

        mock_scraper = AsyncMock()
        mock_scraper.fetch_articles = AsyncMock(return_value=sample_articles)

        with patch("src.services.update_service.get_scraper", return_value=mock_scraper):
            with patch.object(update_service_v2, "_respect_rate_limit", new_callable=AsyncMock):
                new_count = await update_service_v2._update_source(task)

        assert new_count == 2
        assert mock_repository.save.call_count == 2

    @pytest.mark.asyncio
    async def test_update_source_unknown_source(self, update_service_v2: UpdateServiceV2) -> None:
        """Test updating unknown source returns 0."""
        task = UpdateTask(
            priority=UpdatePriority.LOW,
            source_id="unknown-source",
            locale="en-us",
            category=SourceCategory.AGGREGATOR,
        )

        with patch.object(update_service_v2, "_respect_rate_limit", new_callable=AsyncMock):
            new_count = await update_service_v2._update_source(task)

        assert new_count == 0

    @pytest.mark.asyncio
    async def test_update_source_with_duplicates(
        self,
        update_service_v2: UpdateServiceV2,
        mock_repository: AsyncMock,
        sample_articles: list[Article],
    ) -> None:
        """Test updating source with duplicate detection."""
        task = UpdateTask(
            priority=UpdatePriority.CRITICAL,
            source_id="lol",
            locale="en-us",
            category=SourceCategory.OFFICIAL_RIOT,
        )

        # Mock save to return True (new), False (duplicate), True (new)
        mock_repository.save = AsyncMock(side_effect=[True, False, True])

        update_service_v2.lol_client.fetch_news = AsyncMock(
            return_value=sample_articles
            + [
                Article(
                    title="Article 3",
                    url="https://example.com/3",
                    pub_date=datetime.utcnow(),
                    guid="test-3",
                    source=ArticleSource.create("lol", "en-us"),
                )
            ]
        )

        with patch.object(update_service_v2, "_respect_rate_limit", new_callable=AsyncMock):
            new_count = await update_service_v2._update_source(task)

        assert new_count == 2  # Only new articles counted


# =============================================================================
# Create Tasks Tests
# =============================================================================


class TestCreateTasks:
    """Tests for _create_tasks method."""

    @pytest.mark.asyncio
    async def test_create_tasks_all_locales(self, update_service_v2: UpdateServiceV2) -> None:
        """Test creating tasks for all locales."""
        with patch("src.services.update_service.RIOT_LOCALES", ["en-us", "ko-kr", "ja-jp"]):
            tasks = await update_service_v2._create_tasks(source_ids=["lol"])

        assert len(tasks) == 3
        # Check all have CRITICAL priority for lol source
        for task in tasks:
            assert task.source_id == "lol"
            assert task.priority == UpdatePriority.CRITICAL
            assert task.locale in ["en-us", "ko-kr", "ja-jp"]

    @pytest.mark.asyncio
    async def test_create_tasks_single_locale(self, update_service_v2: UpdateServiceV2) -> None:
        """Test creating tasks for single locale."""
        tasks = await update_service_v2._create_tasks(source_ids=["lol"], locales=["en-us"])

        assert len(tasks) == 1
        assert tasks[0].source_id == "lol"
        assert tasks[0].locale == "en-us"


# =============================================================================
# Status Tests
# =============================================================================


class TestGetStatusV2:
    """Tests for get_status method."""

    def test_get_status_initial(self, update_service_v2: UpdateServiceV2) -> None:
        """Test getting initial status."""
        status = update_service_v2.get_status()

        assert "last_update" in status
        assert "update_count" in status
        assert "error_count" in status
        assert status["last_update"] is None
        assert status["update_count"] == 0
        assert status["error_count"] == 0

    def test_get_status_after_update(self, update_service_v2: UpdateServiceV2) -> None:
        """Test getting status after update."""
        update_service_v2.last_update = datetime.utcnow()
        update_service_v2.update_count = 5
        update_service_v2.error_count = 1

        status = update_service_v2.get_status()

        assert status["last_update"] is not None
        assert status["update_count"] == 5
        assert status["error_count"] == 1
