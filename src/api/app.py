"""
FastAPI application for serving LoL Stonks RSS feeds.

This module provides HTTP endpoints for accessing RSS feeds with various filters
including source and category-based filtering.
"""

import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Path, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.schemas import (
    CacheStatus,
    DatabaseStatus,
    HealthCheckResponse,
    LivenessResponse,
    ReadinessResponse,
    SchedulerStatus,
    ScraperSourceStatus,
    ScrapersStatus,
)
from src.config import get_settings
from src.database import ArticleRepository
from src.models import ArticleSource, SourceCategory
from src.rss.feed_service import FeedService, FeedServiceV2
from src.services.scheduler import NewsScheduler
from src.utils.logging import RequestIdMiddleware, configure_structlog, get_logger
from src.utils.metrics import auto_init_metrics, get_metrics_text

logger = get_logger(__name__)
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
    # Configure structured logging
    configure_structlog(
        json_logging=settings.json_logging,
        log_level=settings.log_level,
    )

    # Initialize Prometheus metrics
    auto_init_metrics()

    logger.info(
        "Starting LoL Stonks RSS server",
        extra={
            "version": "1.0.0",
            "json_logging": settings.json_logging,
            "log_level": settings.log_level,
            "database_path": settings.database_path,
        },
    )

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
    logger.info(
        "Scheduler started, will fetch news on next scheduled interval",
        extra={"interval_minutes": settings.update_interval_minutes},
    )

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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)

# Add request ID middleware for tracing
app.add_middleware(RequestIdMiddleware)


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


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Enhanced health check endpoint with detailed diagnostics.

    Returns comprehensive health status including database, scheduler,
    cache, and scraper information. Useful for monitoring and debugging.

    Returns:
        HealthCheckResponse with detailed health information

    Raises:
        HTTPException: If services are not initialized
    """
    try:
        service = app_state.get("feed_service")
        repository = app_state.get("repository")
        scheduler = app_state.get("scheduler")

        if not service or not repository or not scheduler:
            raise HTTPException(
                status_code=503,
                detail="Services not fully initialized",
            )

        # Get database status
        total_articles = await repository.count()
        last_write_ts = await repository.get_last_write_timestamp()
        locales = await repository.get_locales()
        source_categories = await repository.get_source_categories()

        database_status = DatabaseStatus(
            status="connected",
            total_articles=total_articles,
            last_write_timestamp=last_write_ts.isoformat() if last_write_ts else None,
            locales=locales,
            source_categories=source_categories,
        )

        # Get scheduler status
        scheduler_dict = scheduler.get_status()
        jobs = scheduler_dict.get("jobs", [])
        next_run = jobs[0].get("next_run") if jobs else None
        update_service_dict = scheduler_dict.get("update_service", {})

        scheduler_status = SchedulerStatus(
            running=scheduler_dict.get("running", False),
            interval_minutes=scheduler_dict.get("interval_minutes", 0),
            last_update=update_service_dict.get("last_update"),
            next_run=next_run,
            update_count=update_service_dict.get("update_count", 0),
            error_count=update_service_dict.get("error_count", 0),
            configured_sources=update_service_dict.get("configured_sources", 0),
            configured_locales=update_service_dict.get("configured_locales", 0),
        )

        # Get cache statistics
        cache_stats = service.cache.get_stats()

        # Determine backend type and Redis status
        redis_connected = cache_stats.get("redis_connected", False)
        backend = "redis" if redis_connected else "memory"

        cache_status = CacheStatus(
            status="active" if service.cache.is_healthy() else "inactive",
            total_entries=cache_stats["total_entries"],
            size_bytes_estimate=cache_stats["size_bytes_estimate"],
            ttl_seconds=cache_stats["ttl_seconds"],
            backend=backend,
            redis_connected=redis_connected,
        )

        # Get scraper status (from ArticleSource registry)
        source_statuses = []
        for source_id in ArticleSource.ALL_SOURCES:
            # Determine status based on whether we have articles for this source
            source_statuses.append(
                ScraperSourceStatus(
                    source_id=source_id,
                    last_success=None,  # Could be enhanced with tracking
                    status="active",  # All configured sources are considered active
                )
            )

        scrapers_status = ScrapersStatus(
            total_sources=len(ArticleSource.ALL_SOURCES),
            sources=source_statuses,
        )

        # Determine overall status
        overall_status = "healthy"
        if scheduler_status.error_count > 10:
            overall_status = "degraded"
        if total_articles == 0:
            overall_status = "degraded"

        return HealthCheckResponse(
            status=overall_status,
            version="1.0.0",
            service="LoL Stonks RSS",
            timestamp=datetime.utcnow().isoformat(),
            database=database_status,
            scheduler=scheduler_status,
            cache=cache_status,
            scrapers=scrapers_status,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Health check failed: {e}") from e


@app.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """
    Kubernetes readiness probe endpoint.

    Checks if the service is ready to receive traffic by verifying
    that all critical services are initialized and accessible.

    Returns:
        ReadinessResponse with readiness status

    Example:
        Returns 200 if ready, 503 if not ready
    """
    checks: dict[str, bool] = {}
    messages: list[str] = []

    # Check repository
    repository = app_state.get("repository")
    checks["repository"] = repository is not None
    if not repository:
        messages.append("Repository not initialized")

    # Check feed service
    feed_service = app_state.get("feed_service")
    checks["feed_service"] = feed_service is not None
    if not feed_service:
        messages.append("Feed service not initialized")

    # Check feed service V2
    feed_service_v2 = app_state.get("feed_service_v2")
    checks["feed_service_v2"] = feed_service_v2 is not None
    if not feed_service_v2:
        messages.append("Feed service V2 not initialized")

    # Check scheduler
    scheduler = app_state.get("scheduler")
    checks["scheduler"] = scheduler is not None
    if not scheduler:
        messages.append("Scheduler not initialized")

    # Optional: Check if database has articles
    has_articles = False
    if repository:
        try:
            articles = await repository.get_latest(limit=1)
            has_articles = len(articles) > 0
            checks["has_articles"] = has_articles
        except Exception:
            checks["has_articles"] = False
    else:
        checks["has_articles"] = False

    # Determine overall readiness
    # All critical checks must pass, but has_articles is optional
    ready = all(
        checks.get(k, False) for k in ["repository", "feed_service", "feed_service_v2", "scheduler"]
    )

    if ready:
        message = "Service is ready"
    else:
        message = f"Service not ready: {', '.join(messages)}"

    return ReadinessResponse(
        ready=ready,
        timestamp=datetime.utcnow().isoformat(),
        checks=checks,
        message=message,
    )


@app.get("/health/live", response_model=LivenessResponse)
async def liveness_check() -> LivenessResponse:
    """
    Kubernetes liveness probe endpoint.

    Quick check if the service process is alive and responding.
    This endpoint makes minimal checks and should always return
    200 if the application is running.

    Returns:
        LivenessResponse with liveness status

    Example:
        Returns 200 if alive, 503 if process is dead
    """
    # Basic liveness check - just verify app is running
    # No database calls, just check app_state exists
    alive = bool(app_state)

    return LivenessResponse(
        alive=alive,
        timestamp=datetime.utcnow().isoformat(),
        message="ok" if alive else "not alive",
    )


@app.get("/ping")
async def ping() -> dict[str, str]:
    """
    Simple ping endpoint for basic liveness checks.

    Returns a minimal response to indicate the service is running.
    This endpoint makes no database calls and is designed for quick
    liveness probes from orchestrators like Kubernetes.

    Returns:
        Dictionary with status indicator

    Example:
        >>> ping()
        {"status": "ok"}
    """
    return {"status": "ok"}


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


@app.get("/metrics", response_class=Response)
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Exposes Prometheus metrics for monitoring and alerting.
    Metrics include article counts, scraping latency, cache statistics,
    circuit breaker states, and more.

    Returns:
        Prometheus metrics text in plain text format

    Example metrics:
        - articles_fetched_total{source="lol",locale="en-us"} 1523
        - scraping_duration_seconds_bucket{source="lol",locale="en-us",le="0.5"} 423
        - cache_hit_rate{cache_name="feed_cache"} 0.8234
    """
    try:
        metrics_text = get_metrics_text(content_type="text/plain")

        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8",
            headers={
                "Content-Type": "text/plain; version=0.0.4; charset=utf-8",
            },
        )

    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        raise HTTPException(status_code=500, detail="Error generating metrics") from e
