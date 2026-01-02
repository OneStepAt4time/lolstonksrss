"""
Service for updating news articles from LoL API.

This module provides the UpdateService class which handles fetching news
from multiple LoL API locales and saving to the database.

UpdateServiceV2 provides priority-based concurrent updates from multiple
sources with rate limiting and multi-locale support.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from src.api_client import LoLNewsAPIClient
from src.config import RIOT_LOCALES, get_settings
from src.database import ArticleRepository
from src.models import Article, ArticleSource, SourceCategory
from src.scrapers import ALL_SCRAPER_SOURCES, get_scraper
from src.utils.circuit_breaker import CircuitBreakerOpenError, get_circuit_breaker_registry

logger = logging.getLogger(__name__)
settings = get_settings()


class UpdateService:
    """
    Service for updating news articles from LoL API.

    Fetches articles from all supported locales and saves to database.
    Tracks update statistics and handles errors gracefully.
    """

    def __init__(self, repository: ArticleRepository) -> None:
        """
        Initialize update service.

        Args:
            repository: Article repository for database operations
        """
        self.repository = repository
        self.clients = {
            "en-us": LoLNewsAPIClient(),
            "it-it": LoLNewsAPIClient(),
        }
        self.last_update: datetime | None = None
        self.update_count: int = 0
        self.error_count: int = 0

    async def update_all_sources(self) -> dict[str, Any]:
        """
        Fetch and save articles from all sources.

        Returns:
            Dictionary with update statistics including fetched, new,
            duplicate counts, and any errors encountered
        """
        logger.info("Starting update for all sources...")
        start_time = datetime.utcnow()

        stats: dict[str, Any] = {
            "started_at": start_time.isoformat(),
            "sources": {},
            "total_fetched": 0,
            "total_new": 0,
            "total_duplicates": 0,
            "errors": [],
        }

        # Update each source
        for locale, client in self.clients.items():
            try:
                source_stats = await self._update_source(locale, client)
                stats["sources"][locale] = source_stats
                stats["total_fetched"] += source_stats["fetched"]
                stats["total_new"] += source_stats["new"]
                stats["total_duplicates"] += source_stats["duplicates"]

            except Exception as e:
                error_msg = f"Error updating {locale}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
                self.error_count += 1

        # Update stats
        self.last_update = datetime.utcnow()
        self.update_count += 1

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        stats["completed_at"] = self.last_update.isoformat()
        stats["elapsed_seconds"] = round(elapsed, 2)

        logger.info(
            f"Update complete: {stats['total_new']} new articles, "
            f"{stats['total_duplicates']} duplicates, "
            f"{len(stats['errors'])} errors in {elapsed:.2f}s"
        )

        return stats

    async def _update_source(self, locale: str, client: LoLNewsAPIClient) -> dict[str, int]:
        """
        Update articles for a single source.

        Args:
            locale: Locale identifier (e.g., "en-us", "it-it")
            client: API client for this locale

        Returns:
            Statistics dictionary with counts
        """
        logger.info(f"Fetching articles for {locale}...")

        # Fetch articles
        articles: list[Article] = await client.fetch_news(locale)

        stats = {"fetched": len(articles), "new": 0, "duplicates": 0}

        # Save to database
        for article in articles:
            try:
                saved = await self.repository.save(article)
                if saved:
                    stats["new"] += 1
                else:
                    stats["duplicates"] += 1
            except Exception as e:
                logger.error(f"Error saving article {article.guid}: {e}")

        logger.info(
            f"{locale}: {stats['fetched']} fetched, "
            f"{stats['new']} new, {stats['duplicates']} duplicates"
        )

        return stats

    def get_status(self) -> dict[str, Any]:
        """
        Get current service status.

        Returns:
            Status dictionary with update history and configuration
        """
        return {
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "update_count": self.update_count,
            "error_count": self.error_count,
            "sources": list(self.clients.keys()),
        }


# =============================================================================
# UpdateServiceV2 - Priority Queue Orchestration
# =============================================================================


class UpdatePriority(int, Enum):
    """
    Priority levels for update tasks.

    Lower values indicate higher priority (1 = highest).

    Attributes:
        CRITICAL: Official Riot sources - highest priority
        HIGH: Major community hubs and esports
        MEDIUM: Analytics, regional, TFT, PBE sources
        LOW: Social media and aggregators - lowest priority
    """

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass(order=True)
class UpdateTask:
    """
    A task for updating a specific source-locale combination.

    Attributes:
        priority: Update priority (lower = higher priority)
        source_id: Source identifier (e.g., "lol", "dexerto")
        locale: Locale code (e.g., "en-us", "ko-kr")
        category: Source category for filtering
    """

    priority: UpdatePriority
    source_id: str
    locale: str
    category: SourceCategory

    def __hash__(self) -> int:
        """Make UpdateTask hashable for use in sets."""
        return hash((self.source_id, self.locale))


class UpdateServiceV2:
    """
    Priority-based concurrent update service for multi-source, multi-locale news.

    This service orchestrates concurrent updates from multiple news sources
    with priority queue management, rate limiting, and graceful error handling.
    Individual source failures don't stop the entire update process.

    Features:
        - Priority queue for source ordering (Riot sources first)
        - Concurrent updates with configurable semaphore limit
        - Per-domain rate limiting to avoid overwhelming sites
        - Multi-locale support for all sources
        - Graceful degradation on individual failures

    Attributes:
        repository: Database repository for article storage
        max_concurrent: Maximum number of concurrent updates
        lol_client: LoL API client for official Riot sources
        domain_rate_limits: Per-domain semaphores for rate limiting
    """

    # Priority mapping by source category
    PRIORITY_MAP: dict[SourceCategory, UpdatePriority] = {
        SourceCategory.OFFICIAL_RIOT: UpdatePriority.CRITICAL,
        SourceCategory.COMMUNITY_HUB: UpdatePriority.HIGH,
        SourceCategory.ESPORTS: UpdatePriority.HIGH,
        SourceCategory.ANALYTICS: UpdatePriority.MEDIUM,
        SourceCategory.REGIONAL: UpdatePriority.MEDIUM,
        SourceCategory.TFT: UpdatePriority.MEDIUM,
        SourceCategory.PBE: UpdatePriority.MEDIUM,
        SourceCategory.SOCIAL: UpdatePriority.LOW,
        SourceCategory.AGGREGATOR: UpdatePriority.LOW,
    }

    # Default rate limits per domain (seconds between requests)
    DEFAULT_RATE_LIMITS: dict[str, float] = {
        "leagueoflegends.com": 2.0,
        "riotgames.com": 2.0,
        "dexerto.com": 1.5,
        "dotesports.com": 1.5,
        "esports.gg": 2.0,
        "inven.co.kr": 2.5,
        "op.gg": 2.0,
        "twitter.com": 5.0,
        "reddit.com": 5.0,
        "youtube.com": 5.0,
    }

    # Base rate limit for unknown domains
    BASE_RATE_LIMIT: float = 2.0

    def __init__(self, repository: ArticleRepository, max_concurrent: int = 10) -> None:
        """
        Initialize the update service.

        Args:
            repository: Article repository for database operations
            max_concurrent: Maximum number of concurrent update tasks
        """
        self.repository = repository
        self.max_concurrent = max_concurrent
        self.lol_client = LoLNewsAPIClient()
        self.domain_rate_limits: dict[str, asyncio.Semaphore] = {}
        self.last_update: datetime | None = None
        self.update_count: int = 0
        self.error_count: int = 0
        self.cb_registry = get_circuit_breaker_registry()

        # Initialize semaphores for known domains
        for domain in self.DEFAULT_RATE_LIMITS:
            self.domain_rate_limits[domain] = asyncio.Semaphore(1)

    def _get_priority(self, category: SourceCategory) -> UpdatePriority:
        """
        Get update priority for a source category.

        Args:
            category: Source category to prioritize

        Returns:
            Update priority level
        """
        return self.PRIORITY_MAP.get(category, UpdatePriority.LOW)

    def _extract_domain(self, source_id: str) -> str:
        """
        Extract domain from source ID for rate limiting.

        Args:
            source_id: Source identifier

        Returns:
            Domain name for rate limiting (or source_id if unknown)
        """
        # Map known sources to their domains
        domain_map: dict[str, str] = {
            "lol": "leagueoflegends.com",
            "riot-games": "riotgames.com",
            "dexerto": "dexerto.com",
            "dotesports": "dotesports.com",
            "esportsgg": "esports.gg",
            "inven": "inven.co.kr",
            "opgg": "op.gg",
            "twitter": "twitter.com",
            "reddit": "reddit.com",
            "youtube": "youtube.com",
            "lolesports": "lolesports.com",
        }
        return domain_map.get(source_id, source_id)

    async def _respect_rate_limit(self, source_id: str) -> None:
        """
        Apply rate limiting for a specific source domain.

        Uses a semaphore per-domain to ensure only one request to a given
        domain is active at a time, with additional delay based on config.

        Args:
            source_id: Source identifier to rate limit
        """
        domain = self._extract_domain(source_id)

        # Get or create semaphore for this domain
        if domain not in self.domain_rate_limits:
            self.domain_rate_limits[domain] = asyncio.Semaphore(1)

        # Acquire semaphore (wait for any pending requests to this domain)
        async with self.domain_rate_limits[domain]:
            # Get rate limit for this domain
            rate_limit = self.DEFAULT_RATE_LIMITS.get(domain, self.BASE_RATE_LIMIT)
            logger.debug(f"Rate limiting {domain}: {rate_limit}s delay")
            await asyncio.sleep(rate_limit)

    async def _fetch_lol_news(self, locale: str) -> list[Article]:
        """
        Fetch news from official LoL API for a specific locale.

        Args:
            locale: Locale code (e.g., "en-us", "ko-kr")

        Returns:
            List of Article instances
        """
        return await self.lol_client.fetch_news(locale)

    async def _update_source(self, task: UpdateTask) -> int:
        """
        Update articles for a single source-locale combination.

        This is the core worker method that fetches articles from a source
        and saves them to the database. Handles both Riot API sources
        and scraper-based sources.

        Args:
            task: Update task containing source_id, locale, and priority

        Returns:
            Number of new articles saved

        Raises:
            Exception: Propagates exceptions for logging (caught by caller)
        """
        logger.info(f"Updating {task.source_id}:{task.locale} " f"(priority: {task.priority.name})")

        # Respect rate limit before fetching
        await self._respect_rate_limit(task.source_id)

        articles: list[Article] = []

        try:
            # Use LoL API client for official Riot sources
            if task.source_id == "lol":
                articles = await self._fetch_lol_news(task.locale)
            # Use scraper for other sources
            elif task.source_id in ALL_SCRAPER_SOURCES:
                scraper = get_scraper(task.source_id, task.locale)
                articles = await scraper.fetch_articles()
            else:
                logger.warning(f"Unknown source: {task.source_id}")
                return 0

            # Save articles and count new ones
            new_count = 0
            for article in articles:
                try:
                    saved = await self.repository.save(article)
                    if saved:
                        new_count += 1
                except Exception as e:
                    logger.error(f"Error saving article {article.guid}: {e}")

            logger.info(
                f"Updated {task.source_id}:{task.locale}: "
                f"{len(articles)} fetched, {new_count} new"
            )
            return new_count

        except CircuitBreakerOpenError as e:
            # Circuit breaker is open - log warning but don't fail the task
            logger.warning(
                f"Circuit breaker OPEN for {task.source_id}:{task.locale}. Skipping update. {e}"
            )
            return 0
        except Exception as e:
            logger.error(
                f"Error updating {task.source_id}:{task.locale}: {e}",
                exc_info=True,
            )
            raise

    async def _create_tasks(
        self,
        locales: list[str] | None = None,
        source_ids: list[str] | None = None,
        priority: UpdatePriority | None = None,
    ) -> list[UpdateTask]:
        """
        Create update tasks for specified sources and locales.

        Args:
            locales: List of locale codes (None = all configured locales)
            source_ids: List of source IDs (None = all sources)
            priority: Override priority for all tasks

        Returns:
            List of UpdateTask instances sorted by priority
        """
        locales = locales or RIOT_LOCALES
        source_ids = source_ids or list(ArticleSource.ALL_SOURCES.keys())

        tasks: list[UpdateTask] = []

        for source_id in source_ids:
            # Get source category
            source_info = ArticleSource.ALL_SOURCES.get(source_id)
            if not source_info:
                logger.warning(f"Source {source_id} not in ALL_SOURCES, skipping")
                continue

            category = source_info.get("category", SourceCategory.AGGREGATOR)

            # Determine priority
            task_priority = priority or self._get_priority(category)

            # Create task for each locale
            for locale in locales:
                task = UpdateTask(
                    priority=task_priority,
                    source_id=source_id,
                    locale=locale,
                    category=category,
                )
                tasks.append(task)

        # Sort by priority (lower first = higher priority)
        tasks.sort(key=lambda t: t.priority)
        return tasks

    async def _execute_tasks(self, tasks: list[UpdateTask]) -> dict[str, int]:
        """
        Execute update tasks with concurrency control.

        Args:
            tasks: List of UpdateTask instances to execute

        Returns:
            Dictionary with execution statistics
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        stats = {"success": 0, "failed": 0, "total": len(tasks), "new_articles": 0}

        async def worker(task: UpdateTask) -> int:
            """Worker coroutine that processes a single task."""
            async with semaphore:
                try:
                    new_count = await self._update_source(task)
                    stats["success"] += 1
                    stats["new_articles"] += new_count
                    return new_count
                except Exception:
                    stats["failed"] += 1
                    return 0

        # Execute all tasks concurrently with semaphore limiting
        await asyncio.gather(
            *[worker(task) for task in tasks],
            return_exceptions=False,
        )

        return stats

    async def update_all(self) -> dict[str, Any]:
        """
        Update all sources for all locales with priority orchestration.

        Creates tasks for all source-locale combinations, sorts by priority,
        and executes with concurrency control.

        Returns:
            Dictionary with update statistics including success/failed counts
        """
        logger.info("Starting UpdateServiceV2.update_all...")
        start_time = datetime.utcnow()

        # Create tasks for all sources and locales
        tasks = await self._create_tasks()

        logger.info(
            f"Created {len(tasks)} update tasks for "
            f"{len(ArticleSource.ALL_SOURCES)} sources and {len(RIOT_LOCALES)} locales"
        )

        # Execute tasks with concurrency control
        stats = await self._execute_tasks(tasks)

        # Update service state
        self.last_update = datetime.utcnow()
        self.update_count += 1
        self.error_count = stats["failed"]

        elapsed = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "started_at": start_time.isoformat(),
            "completed_at": self.last_update.isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "total_tasks": stats["total"],
            "successful_tasks": stats["success"],
            "failed_tasks": stats["failed"],
            "new_articles": stats["new_articles"],
        }

        logger.info(
            f"UpdateServiceV2.update_all complete: "
            f"{stats['new_articles']} new articles, "
            f"{stats['success']}/{stats['total']} tasks successful "
            f"in {elapsed:.2f}s"
        )

        return result

    async def update_locales(self, locales: list[str]) -> dict[str, Any]:
        """
        Update all sources for specific locales.

        Args:
            locales: List of locale codes to update

        Returns:
            Dictionary with update statistics
        """
        logger.info(f"Updating locales: {locales}")
        start_time = datetime.utcnow()

        # Create tasks for specified locales only
        tasks = await self._create_tasks(locales=locales)

        logger.info(f"Created {len(tasks)} update tasks for {len(locales)} locales")

        # Execute tasks
        stats = await self._execute_tasks(tasks)

        self.last_update = datetime.utcnow()
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "started_at": start_time.isoformat(),
            "completed_at": self.last_update.isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "locales": locales,
            "total_tasks": stats["total"],
            "successful_tasks": stats["success"],
            "failed_tasks": stats["failed"],
            "new_articles": stats["new_articles"],
        }

        logger.info(
            f"Locales update complete: {stats['new_articles']} new articles " f"in {elapsed:.2f}s"
        )

        return result

    async def update_source(
        self, source_id: str, locales: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Update a specific source for all or specified locales.

        Args:
            source_id: Source identifier to update
            locales: Optional list of locales (None = all configured locales)

        Returns:
            Dictionary with update statistics
        """
        logger.info(f"Updating source: {source_id}")
        start_time = datetime.utcnow()

        locales = locales or RIOT_LOCALES

        # Create tasks for this source only
        tasks = await self._create_tasks(source_ids=[source_id], locales=locales)

        if not tasks:
            logger.warning(f"No tasks created for source: {source_id}")
            return {
                "started_at": start_time.isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
                "elapsed_seconds": 0,
                "source_id": source_id,
                "total_tasks": 0,
                "successful_tasks": 0,
                "failed_tasks": 0,
                "new_articles": 0,
            }

        logger.info(f"Created {len(tasks)} update tasks for source {source_id}")

        # Execute tasks
        stats = await self._execute_tasks(tasks)

        self.last_update = datetime.utcnow()
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "started_at": start_time.isoformat(),
            "completed_at": self.last_update.isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "source_id": source_id,
            "total_tasks": stats["total"],
            "successful_tasks": stats["success"],
            "failed_tasks": stats["failed"],
            "new_articles": stats["new_articles"],
        }

        logger.info(
            f"Source {source_id} update complete: {stats['new_articles']} new articles "
            f"in {elapsed:.2f}s"
        )

        return result

    def get_status(self) -> dict[str, Any]:
        """
        Get current service status.

        Returns:
            Status dictionary with configuration and statistics
        """
        # Get circuit breaker status for all sources
        circuit_breaker_status = {}
        for source_id, cb in self.cb_registry.get_all().items():
            circuit_breaker_status[source_id] = {
                "state": cb.stats.state.value,
                "failure_count": cb.stats.failure_count,
                "is_open": cb.is_open(),
            }

        return {
            "version": "v2",
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "update_count": self.update_count,
            "error_count": self.error_count,
            "max_concurrent": self.max_concurrent,
            "configured_sources": len(ArticleSource.ALL_SOURCES),
            "configured_locales": len(RIOT_LOCALES),
            "scraper_sources": len(ALL_SCRAPER_SOURCES),
            "circuit_breakers": circuit_breaker_status,
        }
