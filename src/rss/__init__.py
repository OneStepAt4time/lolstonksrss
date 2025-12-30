"""
RSS feed generation module.

This module provides RSS 2.0 feed generation functionality for League of Legends news.
"""

from src.rss.feed_service import FeedService
from src.rss.generator import RSSFeedGenerator

__all__ = ["RSSFeedGenerator", "FeedService"]
