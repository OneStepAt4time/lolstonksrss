"""
FastAPI application for serving LoL Stonks RSS feeds.

This module provides HTTP endpoints for accessing RSS feeds with various filters
including source and category-based filtering.
"""

import logging
import re
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Path, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import get_settings
from src.database import ArticleRepository
from src.models import ArticleSource, SourceCategory
from src.rss.feed_service import FeedService, FeedServiceV2
from src.services.scheduler import NewsScheduler

logger = logging.getLogger(__name__)
settings = get_settings()

# Global state for services
app_state: dict[str, Any] = {}

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """
    Application lifespan manager.

    Initializes repository and services on startup, cleans up on shutdown.

    Args:
        app: FastAPI application instance

    Yields:
        Control to the application
    """
    logger.info("Starting LoL Stonks RSS server...")

    # Initialize database repository
    repository = ArticleRepository(settings.database_path)
    await repository.initialize()

    # Initialize feed service
    feed_service = FeedService(repository=repository, cache_ttl=settings.feed_cache_ttl)

    # Initialize feed service V2 for multi-locale support
    feed_service_v2 = FeedServiceV2(repository=repository, cache_ttl=settings.feed_cache_ttl)

    # Initialize and start scheduler
    scheduler = NewsScheduler(repository, interval_minutes=settings.update_interval_minutes)
    scheduler.start()

    # Note: Not triggering initial update on startup to avoid blocking
    # The scheduler will fetch news according to its interval
    logger.info("Scheduler started, will fetch news on next scheduled interval")

    # Store in app state
    app_state["repository"] = repository
    app_state["feed_service"] = feed_service
    app_state["feed_service_v2"] = feed_service_v2
    app_state["scheduler"] = scheduler

    logger.info("Server initialized successfully")

    yield

    # Cleanup
    scheduler.stop()
    await repository.close()
    logger.info("Server shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="LoL Stonks RSS",
    description="RSS feed aggregator for League of Legends news",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)


def get_feed_service() -> FeedService:
    """
    Get feed service from app state.

    Returns:
        FeedService instance

    Raises:
        HTTPException: If service is not initialized
    """
    service = app_state.get("feed_service")
    if not service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    return cast(FeedService, service)


def get_feed_service_v2() -> FeedServiceV2:
    """
    Get feed service V2 from app state.

    Returns:
        FeedServiceV2 instance

    Raises:
        HTTPException: If service is not initialized
    """
    service = app_state.get("feed_service_v2")
    if not service:
        raise HTTPException(status_code=500, detail="Service V2 not initialized")
    return cast(FeedServiceV2, service)


@app.get("/api/articles", response_model=list[dict[str, Any]])
async def get_articles(limit: int = 50, source: str | None = None) -> list[dict[str, Any]]:
    """
    Get latest articles as JSON for the frontend.

    Args:
        limit: Maximum number of articles
        source: Optional source filter

    Returns:
        List of articles as dictionaries
    """
    repo = app_state.get("repository")
    if not repo:
        raise HTTPException(status_code=500, detail="Repository not initialized")

    articles = await repo.get_latest(limit=limit, source=source)
    return [a.to_dict() for a in articles]


@app.get("/", response_class=FileResponse)
async def root() -> FileResponse:
    """
    Serve the frontend application.

    Returns:
        HTML file response
    """
    return FileResponse("src/api/static/index.html")


@app.get("/feed.xml", response_class=Response)
async def get_main_feed(limit: int = 50) -> Response:
    """
    Get main RSS feed with all articles from all sources.

    Args:
        limit: Maximum number of articles (default: 50, max: 200)

    Returns:
        RSS 2.0 XML feed

    Raises:
        HTTPException: If feed generation fails
    """
    try:
        # Validate limit
        limit = min(limit, 200)

        service = get_feed_service()

        # Generate feed URL (use request URL)
        feed_url = f"{settings.base_url}/feed.xml"

        # Get feed
        feed_xml = await service.get_main_feed(feed_url, limit=limit)

        return Response(
            content=feed_xml,
            media_type="application/rss+xml; charset=utf-8",
            headers={
                "Cache-Control": f"public, max-age={settings.feed_cache_ttl}",
                "Content-Type": "application/rss+xml; charset=utf-8",
            },
        )

    except Exception as e:
        logger.error(f"Error generating main feed: {e}")
        raise HTTPException(status_code=500, detail="Error generating feed") from e


@app.get("/feed/{source}.xml", response_class=Response)
async def get_source_feed(source: str, limit: int = 50) -> Response:
    """
    Get RSS feed filtered by source.

    Args:
        source: Source identifier (en-us, it-it)
        limit: Maximum number of articles (default: 50, max: 200)

    Returns:
        RSS 2.0 XML feed

    Raises:
        HTTPException: If source is invalid or feed generation fails
    """
    try:
        # Validate source
        source_map = {
            "en-us": ArticleSource.create("lol", "en-us"),
            "it-it": ArticleSource.create("lol", "it-it"),
        }

        if source not in source_map:
            raise HTTPException(
                status_code=404,
                detail=f"Source '{source}' not found. Available: {list(source_map.keys())}",
            )

        # Validate limit
        limit = min(limit, 200)

        service = get_feed_service()

        # Generate feed
        feed_url = f"{settings.base_url}/feed/{source}.xml"
        feed_xml = await service.get_feed_by_source(source_map[source], feed_url, limit=limit)

        return Response(
            content=feed_xml,
            media_type="application/rss+xml; charset=utf-8",
            headers={
                "Cache-Control": f"public, max-age={settings.feed_cache_ttl}",
                "Content-Type": "application/rss+xml; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating source feed for {source}: {e}")
        raise HTTPException(status_code=500, detail="Error generating feed") from e


@app.get("/feed/category/{category}.xml", response_class=Response)
async def get_category_feed(
    category: str = Path(
        ...,
        max_length=50,
        pattern=r"^[a-zA-Z0-9\-_]+$",
        description="Category name (alphanumeric, hyphens, underscores only, max 50 chars)",
    ),
    limit: int = 50,
) -> Response:
    """
    Get RSS feed filtered by category.

    Args:
        category: Category name (e.g., Champions, Patches, Media)
                 Must be alphanumeric with hyphens/underscores, max 50 characters
        limit: Maximum number of articles (default: 50, max: 200)

    Returns:
        RSS 2.0 XML feed

    Raises:
        HTTPException: If feed generation fails or category is invalid
    """
    try:
        # Additional validation for safety (FastAPI validates via Path)
        if not re.match(r"^[a-zA-Z0-9\-_]{1,50}$", category):
            raise HTTPException(
                status_code=400,
                detail="Invalid category format. Use alphanumeric, hyphens, and underscores only (max 50 chars)",
            )

        # Validate limit
        limit = min(limit, 200)

        service = get_feed_service()

        # Generate feed
        feed_url = f"{settings.base_url}/feed/category/{category}.xml"
        feed_xml = await service.get_feed_by_category(category, feed_url, limit=limit)

        return Response(
            content=feed_xml,
            media_type="application/rss+xml; charset=utf-8",
            headers={
                "Cache-Control": f"public, max-age={settings.feed_cache_ttl}",
                "Content-Type": "application/rss+xml; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating category feed for {category}: {e}")
        raise HTTPException(status_code=500, detail="Error generating feed") from e


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint.

    Returns service status and statistics.

    Returns:
        Dictionary with health status information
    """
    try:
        service = app_state.get("feed_service")
        repository = app_state.get("repository")

        if not service or not repository:
            return {"status": "unhealthy", "message": "Services not initialized"}

        # Get article count
        articles = await repository.get_latest(limit=1)

        return {
            "status": "healthy",
            "version": "1.0.0",
            "service": "LoL Stonks RSS",
            "database": "connected",
            "cache": "active",
            "has_articles": len(articles) > 0,
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@app.post("/admin/refresh")
@limiter.limit("5/minute")
async def refresh_feeds(request: Request) -> dict[str, str]:
    """
    Manual feed cache refresh endpoint.

    Rate limited to 5 requests per minute per IP.

    Invalidates all feed caches.

    Returns:
        Dictionary with refresh status

    Raises:
        HTTPException: If refresh fails
    """
    try:
        service = get_feed_service()
        service.invalidate_cache()

        return {"status": "success", "message": "Feed cache invalidated"}

    except Exception as e:
        logger.error(f"Error refreshing feeds: {e}")
        raise HTTPException(status_code=500, detail="Error refreshing feeds") from e


@app.get("/admin/scheduler/status")
async def get_scheduler_status() -> dict[str, Any]:
    """
    Get scheduler status and statistics.

    Returns:
        Dictionary with scheduler status, job information,
        and update service statistics

    Raises:
        HTTPException: If scheduler is not initialized
    """
    scheduler = app_state.get("scheduler")
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")

    return cast(dict[str, Any], scheduler.get_status())


@app.post("/admin/scheduler/trigger")
@limiter.limit("5/minute")
async def trigger_update(request: Request) -> dict[str, Any]:
    """
    Manually trigger news update.

    Rate limited to 5 requests per minute per IP.

    Forces an immediate update of all news sources,
    bypassing the scheduled interval.

    Returns:
        Update statistics dictionary with counts and timing

    Raises:
        HTTPException: If scheduler is not initialized
    """
    scheduler = app_state.get("scheduler")
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")

    stats = await scheduler.trigger_update_now()
    return cast(dict[str, Any], stats)


# =============================================================================
# Multi-Locale RSS Feed Endpoints (V2)
# =============================================================================


@app.get("/rss/{locale}.xml", response_class=Response)
async def get_locale_feed(
    locale: str = Path(
        ...,
        pattern=r"^[a-z]{2}-[a-z]{2}$",
        description="Locale code in format 'xx-xx' (e.g., en-us, it-it)",
    ),
    limit: int = 50,
) -> Response:
    """
    Get RSS feed for a specific locale.

    Provides a localized RSS feed containing articles for the specified locale.
    Uses locale-specific feed titles and descriptions from settings.

    Args:
        locale: Locale code (e.g., "en-us", "it-it", "es-es")
        limit: Maximum number of articles (default: 50, max: 500)

    Returns:
        RSS 2.0 XML feed for the specified locale

    Raises:
        HTTPException: If locale is not supported or feed generation fails
    """
    try:
        # Validate limit
        limit = min(max(1, limit), 500)

        # Validate locale against supported locales
        service = get_feed_service_v2()
        supported_locales = service.get_supported_locales()

        if locale not in supported_locales:
            raise HTTPException(
                status_code=404,
                detail=f"Locale '{locale}' not supported. Available locales: {supported_locales}",
            )

        # Generate feed
        feed_xml = await service.get_feed_by_locale(locale=locale, limit=limit)

        return Response(
            content=feed_xml,
            media_type="application/xml; charset=utf-8",
            headers={
                "Cache-Control": f"public, max-age={settings.feed_cache_ttl}",
                "Content-Type": "application/xml; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating locale feed for {locale}: {e}")
        raise HTTPException(status_code=500, detail="Error generating feed") from e


@app.get("/rss/{locale}/{source}.xml", response_class=Response)
async def get_source_locale_feed(
    locale: str = Path(
        ...,
        pattern=r"^[a-z]{2}-[a-z]{2}$",
        description="Locale code in format 'xx-xx' (e.g., en-us, it-it)",
    ),
    source: str = Path(
        ...,
        max_length=50,
        pattern=r"^[a-z0-9\-_]+$",
        description="Source identifier (e.g., lol, u-gg, dexerto)",
    ),
    limit: int = 50,
) -> Response:
    """
    Get RSS feed for a specific source and locale.

    Filters articles by both source ID and locale, generating a localized
    RSS feed for that specific source.

    Args:
        locale: Locale code (e.g., "en-us", "it-it")
        source: Source identifier (e.g., "lol", "u-gg", "dexerto")
        limit: Maximum number of articles (default: 50, max: 500)

    Returns:
        RSS 2.0 XML feed for the specified source and locale

    Raises:
        HTTPException: If locale is not supported or feed generation fails
    """
    try:
        # Validate limit
        limit = min(max(1, limit), 500)

        # Validate locale against supported locales
        service = get_feed_service_v2()
        supported_locales = service.get_supported_locales()

        if locale not in supported_locales:
            raise HTTPException(
                status_code=404,
                detail=f"Locale '{locale}' not supported. Available locales: {supported_locales}",
            )

        # Generate feed
        feed_xml = await service.get_feed_by_source_and_locale(
            source_id=source, locale=locale, limit=limit
        )

        return Response(
            content=feed_xml,
            media_type="application/xml; charset=utf-8",
            headers={
                "Cache-Control": f"public, max-age={settings.feed_cache_ttl}",
                "Content-Type": "application/xml; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating source locale feed for {source}/{locale}: {e}")
        raise HTTPException(status_code=500, detail="Error generating feed") from e


@app.get("/rss/{locale}/category/{category}.xml", response_class=Response)
async def get_category_locale_feed(
    locale: str = Path(
        ...,
        pattern=r"^[a-z]{2}-[a-z]{2}$",
        description="Locale code in format 'xx-xx' (e.g., en-us, it-it)",
    ),
    category: str = Path(
        ...,
        max_length=50,
        pattern=r"^[a-z0-9\-_]+$",
        description="Category name (e.g., official_riot, analytics)",
    ),
    limit: int = 50,
) -> Response:
    """
    Get RSS feed for a specific category and locale.

    Filters articles by both category and locale, generating a localized
    RSS feed for that specific category.

    Args:
        locale: Locale code (e.g., "en-us", "it-it")
        category: Category name (e.g., "official_riot", "analytics", "community_hub")
        limit: Maximum number of articles (default: 50, max: 500)

    Returns:
        RSS 2.0 XML feed for the specified category and locale

    Raises:
        HTTPException: If locale is not supported or feed generation fails
    """
    try:
        # Validate limit
        limit = min(max(1, limit), 500)

        # Validate locale against supported locales
        service = get_feed_service_v2()
        supported_locales = service.get_supported_locales()

        if locale not in supported_locales:
            raise HTTPException(
                status_code=404,
                detail=f"Locale '{locale}' not supported. Available locales: {supported_locales}",
            )

        # Validate category against SourceCategory enum values
        valid_categories = [c.value for c in SourceCategory]
        if category not in valid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{category}'. Valid categories: {valid_categories}",
            )

        # Generate feed
        feed_xml = await service.get_feed_by_category_and_locale(
            category=category, locale=locale, limit=limit
        )

        return Response(
            content=feed_xml,
            media_type="application/xml; charset=utf-8",
            headers={
                "Cache-Control": f"public, max-age={settings.feed_cache_ttl}",
                "Content-Type": "application/xml; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating category locale feed for {category}/{locale}: {e}")
        raise HTTPException(status_code=500, detail="Error generating feed") from e


@app.get("/feeds")
async def list_available_feeds() -> dict[str, Any]:
    """
    List all available feeds and their endpoints.

    Provides a discovery endpoint listing all supported locales, sources,
    categories, and their corresponding feed URLs.

    Returns:
        Dictionary containing:
            - locales: List of supported locale codes
            - sources: List of available source IDs
            - categories: List of valid category names
            - feeds: List of feed URL specifications

    Raises:
        HTTPException: If service is not initialized
    """
    try:
        service = get_feed_service_v2()
        repo = app_state.get("repository")
        if not repo:
            raise HTTPException(status_code=500, detail="Repository not initialized")

        # Get supported locales
        supported_locales = service.get_supported_locales()

        # Get available locales (with actual articles)
        available_locales = await service.get_available_locales()

        # Get all source IDs
        all_sources = list(ArticleSource.ALL_SOURCES.keys())

        # Get all categories
        all_categories = [c.value for c in SourceCategory]

        # Build feed list
        feeds: list[dict[str, str]] = []

        # Per-locale feeds
        for locale in supported_locales:
            feeds.append({"type": "locale", "locale": locale, "url": f"/rss/{locale}.xml"})

        # Per-source per-locale feeds
        for source in all_sources:
            for locale in supported_locales:
                feeds.append(
                    {
                        "type": "source_locale",
                        "source": source,
                        "locale": locale,
                        "url": f"/rss/{locale}/{source}.xml",
                    }
                )

        # Per-category per-locale feeds
        for category in all_categories:
            for locale in supported_locales:
                feeds.append(
                    {
                        "type": "category_locale",
                        "category": category,
                        "locale": locale,
                        "url": f"/rss/{locale}/category/{category}.xml",
                    }
                )

        return {
            "supported_locales": supported_locales,
            "available_locales": available_locales,
            "sources": all_sources,
            "categories": all_categories,
            "feeds": feeds,
            "base_url": settings.base_url,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing feeds: {e}")
        raise HTTPException(status_code=500, detail="Error listing feeds") from e
