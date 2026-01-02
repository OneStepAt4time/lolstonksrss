"""
Pydantic schemas for API response models.

This module provides type-safe response models for all API endpoints,
including health checks, diagnostics, and error responses.
"""

from pydantic import BaseModel, Field


class DatabaseStatus(BaseModel):
    """Database health status."""

    status: str = Field(..., description="Database connection status (connected/disconnected)")
    total_articles: int = Field(..., description="Total number of articles in database", ge=0)
    last_write_timestamp: str | None = Field(
        None, description="ISO timestamp of most recent article write"
    )
    locales: list[str] = Field(default_factory=list, description="Available locales in database")
    source_categories: list[str] = Field(
        default_factory=list, description="Available source categories"
    )


class SchedulerStatus(BaseModel):
    """Scheduler health status."""

    running: bool = Field(..., description="Whether scheduler is running")
    interval_minutes: int = Field(..., description="Update interval in minutes", ge=1)
    last_update: str | None = Field(None, description="ISO timestamp of last update")
    next_run: str | None = Field(None, description="ISO timestamp of next scheduled run")
    update_count: int = Field(..., description="Total number of updates performed", ge=0)
    error_count: int = Field(..., description="Total number of errors", ge=0)
    configured_sources: int = Field(..., description="Number of configured sources", ge=0)
    configured_locales: int = Field(..., description="Number of configured locales", ge=0)


class CacheStatus(BaseModel):
    """Cache statistics."""

    status: str = Field(..., description="Cache status (active/inactive)")
    total_entries: int = Field(..., description="Number of entries in cache", ge=0)
    size_bytes_estimate: int = Field(..., description="Estimated cache size in bytes", ge=0)
    ttl_seconds: int = Field(..., description="Default TTL in seconds", ge=0)
    backend: str = Field(..., description="Cache backend type (redis/memory)")
    redis_connected: bool = Field(
        default=False, description="Whether Redis is connected (for redis backend)"
    )


class ScraperSourceStatus(BaseModel):
    """Status of a single scraper source."""

    source_id: str = Field(..., description="Source identifier (e.g., 'lol', 'dexerto')")
    last_success: str | None = Field(None, description="ISO timestamp of last successful fetch")
    status: str = Field(..., description="Source status (active/error/unknown)")


class ScrapersStatus(BaseModel):
    """Aggregate scraper status."""

    total_sources: int = Field(..., description="Total number of sources", ge=0)
    sources: list[ScraperSourceStatus] = Field(
        default_factory=list, description="Per-source status details"
    )


class HealthCheckResponse(BaseModel):
    """Comprehensive health check response."""

    status: str = Field(..., description="Overall health status (healthy/degraded/unhealthy)")
    version: str = Field(..., description="Application version")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="ISO timestamp of health check")
    database: DatabaseStatus = Field(..., description="Database status and statistics")
    scheduler: SchedulerStatus = Field(..., description="Scheduler status and statistics")
    cache: CacheStatus = Field(..., description="Cache statistics")
    scrapers: ScrapersStatus = Field(..., description="Scraper status")


class ReadinessResponse(BaseModel):
    """Kubernetes readiness probe response."""

    ready: bool = Field(..., description="Whether the service is ready to receive traffic")
    timestamp: str = Field(..., description="ISO timestamp of readiness check")
    checks: dict[str, bool] = Field(
        ..., description="Individual check results (database, services, etc.)"
    )
    message: str = Field(..., description="Human-readable readiness message")


class LivenessResponse(BaseModel):
    """Kubernetes liveness probe response."""

    alive: bool = Field(..., description="Whether the service process is alive")
    timestamp: str = Field(..., description="ISO timestamp of liveness check")
    message: str = Field(default="ok", description="Human-readable liveness message")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type/category")
    message: str = Field(..., description="Human-readable error message")
    timestamp: str = Field(..., description="ISO timestamp of error")
