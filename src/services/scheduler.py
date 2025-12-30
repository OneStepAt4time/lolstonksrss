"""
Scheduler for periodic news updates.

This module provides the NewsScheduler class which uses APScheduler
to trigger news updates at configured intervals.
"""

import logging
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import get_settings
from src.database import ArticleRepository
from src.integrations.github_dispatcher import GitHubWorkflowDispatcher
from src.services.update_service import UpdateService

logger = logging.getLogger(__name__)
settings = get_settings()


class NewsScheduler:
    """
    Scheduler for periodic news updates.

    Uses APScheduler to trigger updates at configured intervals.
    Prevents overlapping updates and provides manual trigger capability.
    """

    def __init__(self, repository: ArticleRepository, interval_minutes: int = 30) -> None:
        """
        Initialize scheduler.

        Args:
            repository: Article repository
            interval_minutes: Update interval in minutes (default: 30)
        """
        self.repository = repository
        self.interval_minutes = interval_minutes
        self.update_service = UpdateService(repository)
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self) -> None:
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        logger.info(f"Starting scheduler with {self.interval_minutes} minute interval")

        # Add job for periodic updates
        self.scheduler.add_job(
            self._update_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id="update_news",
            name="Update LoL News",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
        )

        # Start scheduler
        self.scheduler.start()
        self.is_running = True

        logger.info("Scheduler started successfully")

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self.is_running:
            return

        logger.info("Stopping scheduler...")
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("Scheduler stopped")

    async def trigger_update_now(self) -> dict[str, Any]:
        """
        Manually trigger an immediate update.

        Returns:
            Update statistics dictionary
        """
        logger.info("Manual update triggered")
        return await self._update_job()

    async def _update_job(self) -> dict[str, Any]:
        """
        Job function for updates.

        Returns:
            Update statistics dictionary
        """
        try:
            stats = await self.update_service.update_all_sources()

            # Trigger GitHub Pages update if new articles found
            if settings.enable_github_pages_sync and stats.get("total_new", 0) > 0:
                try:
                    if settings.github_token:
                        dispatcher = GitHubWorkflowDispatcher(
                            token=settings.github_token,
                            repository=settings.github_repository,
                        )
                        success = await dispatcher.trigger_workflow(
                            workflow_file="publish-news.yml",
                            inputs={
                                "triggered_by": "windows-app",
                                "reason": f"new-articles-found-{stats['total_new']}",
                            },
                        )
                        if success:
                            logger.info(
                                "GitHub Pages update triggered",
                                extra={"new_articles": stats["total_new"]},
                            )
                    else:
                        logger.warning("GitHub Pages sync enabled but GITHUB_TOKEN not configured")
                except Exception as e:
                    # Don't crash scheduler if GitHub API fails
                    logger.error(
                        "Failed to trigger GitHub Pages update",
                        extra={"error": str(e)},
                        exc_info=True,
                    )

            return stats
        except Exception as e:
            logger.error(f"Update job failed: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def get_status(self) -> dict[str, Any]:
        """
        Get scheduler status.

        Returns:
            Status dictionary with job info and update service status
        """
        jobs: list[dict[str, Any]] = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                }
            )

        return {
            "running": self.is_running,
            "interval_minutes": self.interval_minutes,
            "jobs": jobs,
            "update_service": self.update_service.get_status(),
        }
